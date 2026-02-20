"""Tool registry for dynamic tool management.

Adapted from nanobot's tool registry for OpenFinance agents.
"""

import asyncio
from typing import Any, Callable

import logging

logger = logging.getLogger(__name__)

from openfinance.agents.tools.base import Tool


class ToolRegistry:
    """
    Registry for agent tools.
    
    Allows dynamic registration and execution of tools.
    """
    
    def __init__(self):
        self._tools: dict[str, Tool] = {}
        self._handlers: dict[str, Callable] = {}
        self._definitions: dict[str, dict[str, Any]] = {}
    
    def register(self, tool: Tool) -> None:
        """Register a Tool instance."""
        self._tools[tool.name] = tool
        logger.debug(f"Registered tool: {tool.name}")
    
    def register_handler(self, name: str, handler: Callable, definition: dict[str, Any] | None = None) -> None:
        """Register a handler function with optional definition."""
        self._handlers[name] = handler
        if definition:
            self._definitions[name] = definition
        logger.debug(f"Registered tool handler: {name}")
    
    def register_from_definition(self, definition: Any, handler: Callable) -> None:
        """Register a tool from a ToolDefinition and handler."""
        if hasattr(definition, 'name'):
            name = definition.name
            self._definitions[name] = definition.to_openai_tool() if hasattr(definition, 'to_openai_tool') else {
                "type": "function",
                "function": {
                    "name": definition.name,
                    "description": definition.description,
                    "parameters": definition.parameters,
                }
            }
        else:
            name = definition.get("name", handler.__name__)
            self._definitions[name] = definition
        
        self._handlers[name] = handler
        logger.debug(f"Registered tool from definition: {name}")
    
    def unregister(self, name: str) -> None:
        """Unregister a tool by name."""
        self._tools.pop(name, None)
        self._handlers.pop(name, None)
        self._definitions.pop(name, None)
    
    def get(self, name: str) -> Tool | None:
        """Get a tool by name."""
        return self._tools.get(name)
    
    def get_handler(self, name: str) -> Callable | None:
        """Get a tool handler by name."""
        return self._handlers.get(name)
    
    def has(self, name: str) -> bool:
        """Check if a tool is registered."""
        return name in self._tools or name in self._handlers
    
    def get_definitions(self) -> list[dict[str, Any]]:
        """Get all tool definitions in OpenAI format."""
        definitions = []
        
        for tool in self._tools.values():
            definitions.append(tool.to_schema())
        
        for name, definition in self._definitions.items():
            if name not in self._tools:
                definitions.append(definition)
        
        return definitions
    
    async def execute(self, name: str, params: dict[str, Any]) -> str:
        """
        Execute a tool by name with given parameters.
        
        Args:
            name: Tool name.
            params: Tool parameters.
        
        Returns:
            Tool execution result as string.
        """
        tool = self._tools.get(name)
        if tool:
            try:
                errors = tool.validate_params(params)
                if errors:
                    return f"Error: Invalid parameters for tool '{name}': " + "; ".join(errors)
                return await tool.execute(**params)
            except Exception as e:
                return f"Error executing {name}: {str(e)}"
        
        handler = self._handlers.get(name)
        if handler:
            try:
                result = handler(**params)
                if asyncio.iscoroutine(result):
                    result = await result
                return str(result) if result is not None else "Done"
            except Exception as e:
                return f"Error executing {name}: {str(e)}"
        
        return f"Error: Tool '{name}' not found"
    
    @property
    def tool_names(self) -> list[str]:
        """Get list of registered tool names."""
        return list(set(list(self._tools.keys()) + list(self._handlers.keys())))
    
    def __len__(self) -> int:
        return len(self.tool_names)
    
    def __contains__(self, name: str) -> bool:
        return self.has(name)
