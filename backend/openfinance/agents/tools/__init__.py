"""
Tools Module for OpenFinance Agents.

Provides tool decorators, base classes, and MCP server implementation.
"""

from openfinance.agents.tools.decorator import tool, tool_function, register_tool
from openfinance.agents.tools.mcp_server import (
    MCPServer,
    create_sdk_mcp_server,
    InProcessMCPServer,
)
from openfinance.agents.tools.builtin import (
    register_builtin_tools,
    get_builtin_tools,
    get_builtin_tool_names,
)
from openfinance.agents.tools.base import Tool
from openfinance.agents.tools.registry import ToolRegistry
from openfinance.agents.utils.web_fetch import (
    web_fetch,
    web_fetch_simple,
    FetchMethod,
    FetchResult,
)

__all__ = [
    "tool",
    "tool_function",
    "register_tool",
    "Tool",
    "ToolRegistry",
    "MCPServer",
    "create_sdk_mcp_server",
    "InProcessMCPServer",
    "register_builtin_tools",
    "get_builtin_tools",
    "get_builtin_tool_names",
    "web_fetch",
    "web_fetch_simple",
    "FetchMethod",
    "FetchResult",
]
