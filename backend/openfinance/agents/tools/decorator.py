"""
Tool Decorator for OpenFinance Skills.

Provides decorators for defining tools as Python functions.
Inspired by Claude Agent SDK @tool decorator.
"""

import asyncio
import inspect
import logging
from typing import Any, Callable, get_type_hints

from openfinance.agents.types import ToolDefinition

logger = logging.getLogger(__name__)

_tool_registry: dict[str, Callable] = {}
_tool_definitions: dict[str, ToolDefinition] = {}


def tool(
    name: str,
    description: str,
    parameters: dict[str, type] | None = None,
    required: list[str] | None = None,
    category: str = "general",
    dangerous: bool = False,
    timeout_seconds: float = 30.0,
) -> Callable:
    """Decorator to define a tool function.

    Args:
        name: Tool name.
        description: Tool description.
        parameters: Parameter types (name -> type).
        required: Required parameter names.
        category: Tool category.
        dangerous: Whether tool is dangerous.
        timeout_seconds: Execution timeout.

    Returns:
        Decorator function.

    Example:
        @tool(
            name="get_stock_price",
            description="Get current stock price",
            parameters={"symbol": str},
            required=["symbol"],
        )
        async def get_stock_price(symbol: str) -> float:
            return 150.0
    """
    def decorator(func: Callable) -> Callable:
        param_schema = _build_parameter_schema(func, parameters)
        required_params = required or _get_required_params(func)

        tool_def = ToolDefinition(
            name=name,
            description=description,
            parameters=param_schema,
            required=required_params,
            category=category,
            dangerous=dangerous,
            timeout_seconds=timeout_seconds,
        )

        _tool_registry[name] = func
        _tool_definitions[name] = func

        func._tool_definition = tool_def
        func._tool_name = name

        logger.debug(f"Registered tool: {name}")

        return func

    return decorator


def tool_function(func: Callable) -> Callable:
    """Decorator to automatically register a function as a tool.

    Uses function name, docstring, and type hints to infer tool definition.

    Example:
        @tool_function
        async def add(a: int, b: int) -> int:
            '''Add two numbers together.'''
            return a + b
    """
    name = func.__name__
    description = func.__doc__ or f"Tool: {name}"

    type_hints = get_type_hints(func)
    sig = inspect.signature(func)

    parameters = {}
    required = []

    for param_name, param in sig.parameters.items():
        if param_name == "self":
            continue

        param_type = type_hints.get(param_name, str)
        parameters[param_name] = param_type

        if param.default is inspect.Parameter.empty:
            required.append(param_name)

    return tool(
        name=name,
        description=description,
        parameters=parameters,
        required=required,
    )(func)


def _build_parameter_schema(
    func: Callable,
    parameters: dict[str, type] | None,
) -> dict[str, Any]:
    """Build JSON Schema for parameters."""
    if parameters:
        return _types_to_schema(parameters)

    type_hints = get_type_hints(func)
    sig = inspect.signature(func)

    schema = {}
    for param_name, param in sig.parameters.items():
        if param_name == "self":
            continue

        param_type = type_hints.get(param_name, str)
        param_schema = _type_to_schema(param_type)

        if param.default is not inspect.Parameter.empty:
            param_schema["default"] = param.default

        schema[param_name] = param_schema

    return schema


def _get_required_params(func: Callable) -> list[str]:
    """Get required parameter names."""
    sig = inspect.signature(func)
    required = []

    for param_name, param in sig.parameters.items():
        if param_name == "self":
            continue
        if param.default is inspect.Parameter.empty:
            required.append(param_name)

    return required


def _types_to_schema(types: dict[str, type]) -> dict[str, Any]:
    """Convert type dict to JSON Schema."""
    return {name: _type_to_schema(t) for name, t in types.items()}


def _type_to_schema(t: type) -> dict[str, Any]:
    """Convert a Python type to JSON Schema."""
    type_map = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object",
    }

    json_type = type_map.get(t, "string")

    schema = {"type": json_type}

    if t == list:
        schema["items"] = {"type": "string"}
    elif t == dict:
        schema["additionalProperties"] = {"type": "string"}

    return schema


def get_tool(name: str) -> Callable | None:
    """Get a registered tool function."""
    return _tool_registry.get(name)


def get_tool_definition(name: str) -> ToolDefinition | None:
    """Get a tool definition."""
    if name in _tool_definitions:
        func = _tool_definitions[name]
        if hasattr(func, "_tool_definition"):
            return func._tool_definition
    return None


def list_tools() -> list[str]:
    """List all registered tool names."""
    return list(_tool_registry.keys())


def list_tool_definitions() -> list[ToolDefinition]:
    """List all tool definitions."""
    definitions = []
    for func in _tool_definitions.values():
        if hasattr(func, "_tool_definition"):
            definitions.append(func._tool_definition)
    return definitions


def clear_tools() -> None:
    """Clear all registered tools."""
    _tool_registry.clear()
    _tool_definitions.clear()


def register_tool(func: Callable, name: str | None = None) -> None:
    """Register a tool function directly."""
    tool_name = name or func.__name__

    if hasattr(func, "_tool_definition"):
        _tool_registry[tool_name] = func
        _tool_definitions[tool_name] = func
    else:
        decorated = tool_function(func)
        _tool_registry[tool_name] = decorated
        _tool_definitions[tool_name] = decorated


class ToolBuilder:
    """Builder for creating tools programmatically.

    Example:
        tool = (
            ToolBuilder()
            .name("calculate")
            .description("Perform calculation")
            .param("expression", str, required=True)
            .param("precision", int, default=2)
            .handler(lambda expr, precision: round(eval(expr), precision))
            .build()
        )
    """

    def __init__(self) -> None:
        self._name: str = ""
        self._description: str = ""
        self._parameters: dict[str, dict[str, Any]] = {}
        self._required: list[str] = []
        self._handler: Callable | None = None
        self._category: str = "general"
        self._dangerous: bool = False
        self._timeout: float = 30.0

    def name(self, name: str) -> "ToolBuilder":
        """Set the tool name."""
        self._name = name
        return self

    def description(self, description: str) -> "ToolBuilder":
        """Set the tool description."""
        self._description = description
        return self

    def param(
        self,
        name: str,
        type_: type,
        description: str = "",
        required: bool = True,
        default: Any = None,
    ) -> "ToolBuilder":
        """Add a parameter."""
        schema = _type_to_schema(type_)
        if description:
            schema["description"] = description
        if default is not None:
            schema["default"] = default

        self._parameters[name] = schema
        if required:
            self._required.append(name)

        return self

    def handler(self, handler: Callable) -> "ToolBuilder":
        """Set the handler function."""
        self._handler = handler
        return self

    def category(self, category: str) -> "ToolBuilder":
        """Set the category."""
        self._category = category
        return self

    def dangerous(self, dangerous: bool = True) -> "ToolBuilder":
        """Mark as dangerous."""
        self._dangerous = dangerous
        return self

    def timeout(self, seconds: float) -> "ToolBuilder":
        """Set the timeout."""
        self._timeout = seconds
        return self

    def build(self) -> Callable:
        """Build and register the tool."""
        if not self._name:
            raise ValueError("Tool name is required")
        if not self._handler:
            raise ValueError("Handler is required")

        tool_def = ToolDefinition(
            name=self._name,
            description=self._description,
            parameters=self._parameters,
            required=self._required,
            category=self._category,
            dangerous=self._dangerous,
            timeout_seconds=self._timeout,
        )

        handler = self._handler
        handler._tool_definition = tool_def
        handler._tool_name = self._name

        _tool_registry[self._name] = handler
        _tool_definitions[self._name] = handler

        return handler
