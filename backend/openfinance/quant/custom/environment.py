"""
Factor Development Environment for Quantitative Analysis.

Provides a safe environment for developing and testing custom factors.
"""

import ast
import logging
import time
from datetime import datetime
from typing import Any, Callable

import numpy as np
import pandas as pd

from openfinance.domain.models.quant import (
    CustomFactor,
    FactorValidationResult,
    FactorTestResult,
    FactorStatus,
)

logger = logging.getLogger(__name__)


class FactorEnvironment:
    """Safe environment for factor development.

    Provides:
    - Sandboxed code execution
    - Pre-defined safe functions
    - Data access control
    """

    SAFE_MODULES = {
        "numpy": np,
        "np": np,
        "pandas": pd,
        "pd": pd,
    }

    SAFE_FUNCTIONS = {
        "abs": abs,
        "max": max,
        "min": min,
        "sum": sum,
        "len": len,
        "round": round,
        "sorted": sorted,
        "list": list,
        "dict": dict,
        "zip": zip,
        "range": range,
        "enumerate": enumerate,
    }

    def __init__(self) -> None:
        self._custom_factors: dict[str, CustomFactor] = {}

    def validate_code(
        self,
        python_code: str,
    ) -> FactorValidationResult:
        """Validate factor code for safety and correctness.

        Args:
            python_code: Python code to validate.

        Returns:
            FactorValidationResult with validation status.
        """
        errors: list[str] = []
        warnings: list[str] = []

        syntax_valid = True
        imports_valid = True
        logic_valid = True

        try:
            ast.parse(python_code)
        except SyntaxError as e:
            syntax_valid = False
            errors.append(f"Syntax error: {str(e)}")

        import_errors = self._check_imports(python_code)
        if import_errors:
            imports_valid = False
            errors.extend(import_errors)

        dangerous_patterns = self._check_dangerous_patterns(python_code)
        if dangerous_patterns:
            logic_valid = False
            errors.extend(dangerous_patterns)

        test_output = None
        if syntax_valid and imports_valid:
            try:
                test_output = self._test_execution(python_code)
            except Exception as e:
                warnings.append(f"Test execution warning: {str(e)}")

        is_valid = len(errors) == 0

        return FactorValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            syntax_valid=syntax_valid,
            imports_valid=imports_valid,
            logic_valid=logic_valid,
            test_output=test_output,
        )

    def _check_imports(self, code: str) -> list[str]:
        """Check for disallowed imports."""
        errors = []
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module = alias.name.split(".")[0]
                        if module not in self.SAFE_MODULES:
                            errors.append(f"Disallowed import: {alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        module = node.module.split(".")[0]
                        if module not in self.SAFE_MODULES:
                            errors.append(f"Disallowed import from: {node.module}")
        except Exception:
            pass
        return errors

    def _check_dangerous_patterns(self, code: str) -> list[str]:
        """Check for dangerous code patterns."""
        errors = []
        dangerous = [
            "exec(",
            "eval(",
            "compile(",
            "open(",
            "__import__",
            "os.",
            "sys.",
            "subprocess",
            "socket",
            "pickle",
            "marshal",
            "shelve",
        ]
        code_lower = code.lower()
        for pattern in dangerous:
            if pattern.lower() in code_lower:
                errors.append(f"Potentially dangerous pattern: {pattern}")
        return errors

    def _test_execution(self, code: str) -> Any:
        """Test execute the factor code."""
        safe_globals = {
            "__builtins__": self.SAFE_FUNCTIONS,
            **self.SAFE_MODULES,
        }

        test_data = pd.DataFrame({
            "close": [100, 101, 102, 101, 103],
            "high": [102, 103, 104, 103, 105],
            "low": [99, 100, 101, 100, 102],
            "volume": [1000, 1100, 1200, 1050, 1150],
        })

        local_vars = {
            "df": test_data,
            "close": test_data["close"].values,
            "high": test_data["high"].values,
            "low": test_data["low"].values,
            "volume": test_data["volume"].values,
        }

        try:
            exec(code, safe_globals, local_vars)
            if "factor" in local_vars:
                return local_vars["factor"]
            return "Code executed successfully"
        except Exception as e:
            raise RuntimeError(f"Execution failed: {str(e)}")

    def compile_factor(
        self,
        python_code: str,
        parameters: dict[str, Any] | None = None,
    ) -> Callable | None:
        """Compile factor code into a callable function.

        Args:
            python_code: Python code to compile.
            parameters: Default parameters for the factor.

        Returns:
            Callable factor function or None if compilation fails.
        """
        try:
            safe_globals = {
                "__builtins__": self.SAFE_FUNCTIONS,
                **self.SAFE_MODULES,
            }

            code_obj = compile(python_code, "<factor>", "exec")

            local_vars: dict[str, Any] = {}
            exec(code_obj, safe_globals, local_vars)

            if "factor" in local_vars and callable(local_vars["factor"]):
                return local_vars["factor"]
            elif "calculate" in local_vars and callable(local_vars["calculate"]):
                return local_vars["calculate"]
            else:

                def wrapped_factor(df: pd.DataFrame, **kwargs) -> float:
                    local_vars = {
                        "df": df,
                        "close": df["close"].values if "close" in df.columns else None,
                        "high": df["high"].values if "high" in df.columns else None,
                        "low": df["low"].values if "low" in df.columns else None,
                        "volume": df["volume"].values if "volume" in df.columns else None,
                        **(parameters or {}),
                        **kwargs,
                    }
                    exec(code_obj, safe_globals, local_vars)
                    return local_vars.get("result", local_vars.get("value", 0.0))

                return wrapped_factor

        except Exception as e:
            logger.error(f"Failed to compile factor: {e}")
            return None

    def save_factor(
        self,
        name: str,
        code: str,
        python_code: str,
        description: str = "",
        parameters: dict[str, Any] | None = None,
    ) -> CustomFactor:
        """Save a custom factor.

        Args:
            name: Factor name.
            code: Factor code (unique identifier).
            python_code: Python implementation.
            description: Factor description.
            parameters: Factor parameters.

        Returns:
            Saved CustomFactor.
        """
        validation = self.validate_code(python_code)

        factor = CustomFactor(
            name=name,
            code=code,
            description=description,
            python_code=python_code,
            parameters=parameters or {},
            is_validated=validation.is_valid,
            validation_errors=validation.errors,
            status=FactorStatus.ACTIVE if validation.is_valid else FactorStatus.DRAFT,
        )

        self._custom_factors[factor.custom_id] = factor
        logger.info(f"Saved custom factor: {factor.custom_id}")

        return factor

    def get_factor(self, factor_id: str) -> CustomFactor | None:
        """Get a saved custom factor."""
        return self._custom_factors.get(factor_id)

    def list_factors(self) -> list[CustomFactor]:
        """List all saved custom factors."""
        return list(self._custom_factors.values())

    def delete_factor(self, factor_id: str) -> bool:
        """Delete a custom factor."""
        if factor_id in self._custom_factors:
            del self._custom_factors[factor_id]
            return True
        return False
