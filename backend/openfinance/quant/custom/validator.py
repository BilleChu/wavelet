"""
Factor Validator for Quantitative Analysis.

Provides validation tools for custom factor code.
"""

import ast
import logging
import re
from typing import Any

import numpy as np
import pandas as pd

from openfinance.domain.models.quant import (
    FactorValidationRequest,
    FactorValidationResult,
)

logger = logging.getLogger(__name__)


class FactorValidator:
    """Validator for custom factor code.

    Provides:
    - Syntax validation
    - Import validation
    - Logic validation
    - Performance validation
    """

    REQUIRED_INPUTS = ["df", "close", "high", "low", "volume"]
    ALLOWED_OUTPUTS = ["factor", "value", "result", "signal"]

    def __init__(self) -> None:
        pass

    def validate(
        self,
        request: FactorValidationRequest,
    ) -> FactorValidationResult:
        """Validate factor code.

        Args:
            request: Validation request with code and parameters.

        Returns:
            FactorValidationResult with validation status.
        """
        errors: list[str] = []
        warnings: list[str] = []

        syntax_valid, syntax_errors = self._validate_syntax(request.python_code)
        errors.extend(syntax_errors)

        imports_valid, import_errors = self._validate_imports(request.python_code)
        errors.extend(import_errors)

        logic_valid, logic_errors, logic_warnings = self._validate_logic(
            request.python_code,
            request.parameters,
        )
        errors.extend(logic_errors)
        warnings.extend(logic_warnings)

        test_output = None
        if syntax_valid and imports_valid and request.test_data:
            try:
                test_output = self._run_test(
                    request.python_code,
                    request.test_data,
                    request.parameters,
                )
            except Exception as e:
                errors.append(f"Test execution failed: {str(e)}")

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

    def _validate_syntax(self, code: str) -> tuple[bool, list[str]]:
        """Validate Python syntax."""
        errors = []
        try:
            ast.parse(code)
            return True, []
        except SyntaxError as e:
            errors.append(f"Syntax error at line {e.lineno}: {e.msg}")
            return False, errors

    def _validate_imports(self, code: str) -> tuple[bool, list[str]]:
        """Validate imports."""
        errors = []
        allowed_modules = {
            "numpy", "np",
            "pandas", "pd",
            "math",
            "statistics",
        }

        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module = alias.name.split(".")[0]
                        if module not in allowed_modules:
                            errors.append(f"Disallowed import: {alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        module = node.module.split(".")[0]
                        if module not in allowed_modules:
                            errors.append(f"Disallowed import from: {node.module}")
        except Exception:
            pass

        return len(errors) == 0, errors

    def _validate_logic(
        self,
        code: str,
        parameters: dict[str, Any],
    ) -> tuple[bool, list[str], list[str]]:
        """Validate factor logic."""
        errors = []
        warnings = []

        dangerous_patterns = [
            (r"\bexec\s*\(", "exec() is not allowed"),
            (r"\beval\s*\(", "eval() is not allowed"),
            (r"\bcompile\s*\(", "compile() is not allowed"),
            (r"\bopen\s*\(", "open() is not allowed"),
            (r"__import__", "__import__ is not allowed"),
            (r"\bos\.", "os module is not allowed"),
            (r"\bsys\.", "sys module is not allowed"),
            (r"\bsubprocess", "subprocess is not allowed"),
            (r"\bsocket", "socket is not allowed"),
            (r"\bpickle", "pickle is not allowed"),
            (r"\bmarshal", "marshal is not allowed"),
        ]

        for pattern, message in dangerous_patterns:
            if re.search(pattern, code):
                errors.append(message)

        has_output = any(
            re.search(rf"\b{output}\s*=", code)
            for output in self.ALLOWED_OUTPUTS
        )
        if not has_output:
            warnings.append(
                "No output variable found. Define 'factor', 'value', 'result', or 'signal'."
            )

        has_input = any(
            re.search(rf"\b{inp}\b", code)
            for inp in self.REQUIRED_INPUTS
        )
        if not has_input:
            warnings.append(
                "No input data usage found. Consider using 'df', 'close', 'high', 'low', or 'volume'."
            )

        if "return" not in code and "factor" not in code and "result" not in code:
            warnings.append(
                "No return statement or output assignment found."
            )

        return len(errors) == 0, errors, warnings

    def _run_test(
        self,
        code: str,
        test_data: dict[str, Any],
        parameters: dict[str, Any],
    ) -> Any:
        """Run test execution."""
        safe_globals = {
            "__builtins__": {
                "abs": abs,
                "max": max,
                "min": min,
                "sum": sum,
                "len": len,
                "round": round,
                "sorted": sorted,
                "list": list,
                "dict": dict,
                "range": range,
                "enumerate": enumerate,
                "zip": zip,
            },
            "np": np,
            "numpy": np,
            "pd": pd,
            "pandas": pd,
        }

        local_vars = {
            **test_data,
            **parameters,
        }

        exec(code, safe_globals, local_vars)

        for output in self.ALLOWED_OUTPUTS:
            if output in local_vars:
                return local_vars[output]

        return None

    def validate_parameters(
        self,
        parameters: dict[str, Any],
        schema: dict[str, dict[str, Any]],
    ) -> tuple[bool, list[str]]:
        """Validate parameters against schema."""
        errors = []

        for name, config in schema.items():
            if config.get("required", False) and name not in parameters:
                errors.append(f"Required parameter '{name}' is missing")
                continue

            if name in parameters:
                value = parameters[name]

                if "type" in config:
                    expected_type = config["type"]
                    if expected_type == "int" and not isinstance(value, int):
                        errors.append(f"Parameter '{name}' must be int")
                    elif expected_type == "float" and not isinstance(value, (int, float)):
                        errors.append(f"Parameter '{name}' must be float")
                    elif expected_type == "str" and not isinstance(value, str):
                        errors.append(f"Parameter '{name}' must be str")
                    elif expected_type == "bool" and not isinstance(value, bool):
                        errors.append(f"Parameter '{name}' must be bool")

                if "min" in config and isinstance(value, (int, float)):
                    if value < config["min"]:
                        errors.append(
                            f"Parameter '{name}' must be >= {config['min']}"
                        )

                if "max" in config and isinstance(value, (int, float)):
                    if value > config["max"]:
                        errors.append(
                            f"Parameter '{name}' must be <= {config['max']}"
                        )

                if "options" in config:
                    if value not in config["options"]:
                        errors.append(
                            f"Parameter '{name}' must be one of {config['options']}"
                        )

        return len(errors) == 0, errors
