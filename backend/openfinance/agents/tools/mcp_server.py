"""
MCP Server Implementation for OpenFinance Skills.

Provides in-process MCP server for tool execution.
Inspired by Claude Agent SDK MCP server.
"""

import asyncio
import json
import logging
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Callable

from pydantic import BaseModel, Field

from openfinance.agents.types import (
    ToolDefinition,
    ToolInvocation,
    ToolState,
)

logger = logging.getLogger(__name__)


class MCPTool(BaseModel):
    """MCP tool definition."""

    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    input_schema: dict[str, Any] = Field(
        default_factory=dict,
        description="JSON Schema for input",
    )


class MCPToolResult(BaseModel):
    """MCP tool execution result."""

    tool_use_id: str = Field(..., description="Tool use ID")
    content: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Result content blocks",
    )
    is_error: bool = Field(default=False, description="Whether result is error")


class MCPServer(ABC):
    """Abstract base class for MCP servers."""

    @abstractmethod
    async def list_tools(self) -> list[MCPTool]:
        """List available tools."""
        pass

    @abstractmethod
    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any],
    ) -> MCPToolResult:
        """Execute a tool."""
        pass

    @abstractmethod
    async def get_tool_schema(self, name: str) -> dict[str, Any] | None:
        """Get tool schema."""
        pass


class InProcessMCPServer(MCPServer):
    """In-process MCP server that executes tools directly.

    This server runs tools in the same Python process, avoiding
    the overhead of inter-process communication.

    Example:
        @tool("add", "Add two numbers", {"a": int, "b": int})
        async def add(a: int, b: int) -> int:
            return a + b

        server = create_sdk_mcp_server(
            name="calculator",
            version="1.0.0",
            tools=[add],
        )

        result = await server.call_tool("add", {"a": 2, "b": 3})
        print(result)  # 5
    """

    def __init__(
        self,
        name: str,
        version: str,
        tools: list[Callable],
    ) -> None:
        self.name = name
        self.version = version
        self._tools: dict[str, Callable] = {}
        self._definitions: dict[str, ToolDefinition] = {}
        self._invocations: dict[str, ToolInvocation] = {}

        for tool_func in tools:
            self._register_tool(tool_func)

    def _register_tool(self, func: Callable) -> None:
        """Register a tool function."""
        if hasattr(func, "_tool_definition"):
            tool_def = func._tool_definition
            tool_name = func._tool_name
        elif hasattr(func, "__name__"):
            tool_name = func.__name__
            tool_def = ToolDefinition(
                name=tool_name,
                description=func.__doc__ or f"Tool: {tool_name}",
            )
        else:
            raise ValueError(f"Cannot register tool: {func}")

        self._tools[tool_name] = func
        self._definitions[tool_name] = tool_def

        logger.debug(f"Registered MCP tool: {tool_name}")

    async def list_tools(self) -> list[MCPTool]:
        """List available tools."""
        tools = []
        for name, defn in self._definitions.items():
            tools.append(MCPTool(
                name=name,
                description=defn.description,
                input_schema={
                    "type": "object",
                    "properties": defn.parameters,
                    "required": defn.required,
                },
            ))
        return tools

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any],
    ) -> MCPToolResult:
        """Execute a tool."""
        tool_use_id = str(uuid.uuid4())

        handler = self._tools.get(name)
        if not handler:
            return MCPToolResult(
                tool_use_id=tool_use_id,
                content=[{
                    "type": "text",
                    "text": f"Tool not found: {name}",
                }],
                is_error=True,
            )

        invocation = ToolInvocation(
            invocation_id=tool_use_id,
            tool_name=name,
            arguments=arguments,
            state=ToolState.RUNNING,
            started_at=datetime.now(),
        )
        self._invocations[tool_use_id] = invocation

        try:
            result = handler(**arguments)

            if asyncio.iscoroutine(result):
                result = await result

            invocation.result = str(result)
            invocation.state = ToolState.COMPLETED

            return MCPToolResult(
                tool_use_id=tool_use_id,
                content=[{
                    "type": "text",
                    "text": str(result),
                }],
                is_error=False,
            )

        except Exception as e:
            logger.exception(f"Tool execution failed: {name}")

            invocation.state = ToolState.FAILED
            invocation.error = str(e)

            return MCPToolResult(
                tool_use_id=tool_use_id,
                content=[{
                    "type": "text",
                    "text": f"Error: {str(e)}",
                }],
                is_error=True,
            )

        finally:
            invocation.completed_at = datetime.now()
            if invocation.started_at:
                invocation.duration_ms = (
                    invocation.completed_at - invocation.started_at
                ).total_seconds() * 1000

    async def get_tool_schema(self, name: str) -> dict[str, Any] | None:
        """Get tool schema."""
        defn = self._definitions.get(name)
        if not defn:
            return None

        return defn.to_anthropic_tool()

    def get_tool(self, name: str) -> Callable | None:
        """Get a tool handler."""
        return self._tools.get(name)

    def get_invocation(self, invocation_id: str) -> ToolInvocation | None:
        """Get an invocation record."""
        return self._invocations.get(invocation_id)

    def get_stats(self) -> dict[str, Any]:
        """Get server statistics."""
        return {
            "name": self.name,
            "version": self.version,
            "tools_count": len(self._tools),
            "tools": list(self._tools.keys()),
            "total_invocations": len(self._invocations),
        }


def create_sdk_mcp_server(
    name: str,
    version: str,
    tools: list[Callable],
) -> InProcessMCPServer:
    """Create an in-process SDK MCP server.

    Args:
        name: Server name.
        version: Server version.
        tools: List of tool functions.

    Returns:
        InProcessMCPServer instance.

    Example:
        @tool("greet", "Greet a user", {"name": str})
        async def greet(name: str) -> str:
            return f"Hello, {name}!"

        server = create_sdk_mcp_server(
            name="my-tools",
            version="1.0.0",
            tools=[greet],
        )
    """
    return InProcessMCPServer(
        name=name,
        version=version,
        tools=tools,
    )


class MCPServerRegistry:
    """Registry for managing multiple MCP servers."""

    def __init__(self) -> None:
        self._servers: dict[str, MCPServer] = {}

    def register(
        self,
        name: str,
        server: MCPServer,
    ) -> None:
        """Register an MCP server."""
        self._servers[name] = server
        logger.info(f"Registered MCP server: {name}")

    def unregister(self, name: str) -> bool:
        """Unregister an MCP server."""
        if name in self._servers:
            del self._servers[name]
            return True
        return False

    def get(self, name: str) -> MCPServer | None:
        """Get an MCP server."""
        return self._servers.get(name)

    def list_servers(self) -> list[str]:
        """List registered server names."""
        return list(self._servers.keys())

    async def list_all_tools(self) -> dict[str, list[MCPTool]]:
        """List tools from all servers."""
        all_tools = {}
        for name, server in self._servers.items():
            tools = await server.list_tools()
            all_tools[name] = tools
        return all_tools

    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> MCPToolResult:
        """Call a tool on a specific server."""
        server = self._servers.get(server_name)
        if not server:
            return MCPToolResult(
                tool_use_id=str(uuid.uuid4()),
                content=[{
                    "type": "text",
                    "text": f"Server not found: {server_name}",
                }],
                is_error=True,
            )

        return await server.call_tool(tool_name, arguments)

    def get_stats(self) -> dict[str, Any]:
        """Get registry statistics."""
        return {
            "servers_count": len(self._servers),
            "servers": {
                name: server.get_stats() if hasattr(server, "get_stats") else {}
                for name, server in self._servers.items()
            },
        }


_default_registry = MCPServerRegistry()


def get_mcp_registry() -> MCPServerRegistry:
    """Get the default MCP server registry."""
    return _default_registry
