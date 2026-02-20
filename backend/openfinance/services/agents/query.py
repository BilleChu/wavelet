"""
Query interface for OpenFinance Agent.

Provides a simple async interface for querying the agent.
Inspired by Claude Agent SDK query() function.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, AsyncIterator, Callable

from openfinance.agents.types import (
    AgentOptions,
    AssistantMessage,
    MessageUnion,
    ResultMessage,
    TextBlock,
    UserMessage,
)
from openfinance.agents.client import AgentClient

logger = logging.getLogger(__name__)


async def query(
    prompt: str,
    options: AgentOptions | None = None,
    on_message: Callable[[MessageUnion], None] | None = None,
    on_tool_use: Callable[[str, dict[str, Any]], None] | None = None,
    on_tool_result: Callable[[str, str, bool], None] | None = None,
) -> AsyncIterator[MessageUnion]:
    """Query the agent with a prompt.

    This is the simplest way to interact with the agent. It handles
    the full agent loop including tool calls and returns a stream
    of messages.

    Args:
        prompt: The user prompt to send to the agent.
        options: Optional agent configuration options.
        on_message: Optional callback for each message.
        on_tool_use: Optional callback when a tool is used.
        on_tool_result: Optional callback when a tool result is received.

    Yields:
        MessageUnion: Messages from the agent (AssistantMessage, ResultMessage, etc.)

    Example:
        async for message in query("What is 2 + 2?"):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        print(block.text)
            elif isinstance(message, ResultMessage):
                print(f"Task completed: {message.result}")
    """
    options = options or AgentOptions()

    async with AgentClient(options=options) as client:
        await client.query(prompt)

        async for message in client.receive_response():
            if on_message:
                on_message(message)

            if on_tool_use and isinstance(message, AssistantMessage):
                from openfinance.agents.types import ToolUseBlock
                for block in message.content:
                    if isinstance(block, ToolUseBlock):
                        on_tool_use(block.name, block.input)

            if on_tool_result:
                from openfinance.agents.types import ToolResultBlock
                if hasattr(message, "content") and isinstance(message.content, list):
                    for block in message.content:
                        if isinstance(block, ToolResultBlock):
                            on_tool_result(
                                block.tool_use_id,
                                block.content,
                                block.is_error,
                            )

            yield message


async def query_simple(
    prompt: str,
    options: AgentOptions | None = None,
) -> str:
    """Simple query that returns only the final result.

    This is a convenience function for cases where you only need
    the final result and don't care about intermediate messages.

    Args:
        prompt: The user prompt to send to the agent.
        options: Optional agent configuration options.

    Returns:
        str: The final result from the agent.

    Example:
        result = await query_simple("What is 2 + 2?")
        print(result)  # "4"
    """
    final_result = ""
    async for message in query(prompt, options):
        if isinstance(message, ResultMessage):
            final_result = message.result
        elif isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    final_result = block.text
    return final_result


async def query_with_tools(
    prompt: str,
    tools: list[Callable],
    options: AgentOptions | None = None,
) -> AsyncIterator[MessageUnion]:
    """Query the agent with custom tools.

    This is a convenience function for registering tools and
    querying in one step.

    Args:
        prompt: The user prompt to send to the agent.
        tools: List of tool functions (decorated with @tool).
        options: Optional agent configuration options.

    Yields:
        MessageUnion: Messages from the agent.

    Example:
        @tool("add", "Add two numbers", {"a": int, "b": int})
        async def add(a: int, b: int) -> int:
            return a + b

        async for message in query_with_tools("What is 2 + 3?", [add]):
            print(message)
    """
    options = options or AgentOptions()

    async with AgentClient(options=options) as client:
        for tool_func in tools:
            client.register_tool(tool_func)

        await client.query(prompt)

        async for message in client.receive_response():
            yield message


async def query_streaming(
    prompt: str,
    options: AgentOptions | None = None,
) -> AsyncIterator[str]:
    """Query the agent with streaming text output.

    This yields text chunks as they are generated, useful for
    real-time display of agent responses.

    Args:
        prompt: The user prompt to send to the agent.
        options: Optional agent configuration options.

    Yields:
        str: Text chunks from the agent.

    Example:
        async for chunk in query_streaming("Tell me a story"):
            print(chunk, end="", flush=True)
    """
    async for message in query(prompt, options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    yield block.text
        elif isinstance(message, ResultMessage):
            if message.result:
                yield message.result


class QueryBuilder:
    """Builder for creating queries with fluent interface.

    Example:
        result = await (
            QueryBuilder()
            .with_prompt("Analyze AAPL stock")
            .with_model("claude-sonnet-4-20250514")
            .with_tools([stock_price, company_info])
            .with_timeout(60.0)
            .execute()
        )
    """

    def __init__(self) -> None:
        self._prompt: str = ""
        self._options: AgentOptions = AgentOptions()
        self._tools: list[Callable] = []
        self._hooks: dict[str, list[Callable]] = {}

    def with_prompt(self, prompt: str) -> "QueryBuilder":
        """Set the prompt."""
        self._prompt = prompt
        return self

    def with_model(self, model: str) -> "QueryBuilder":
        """Set the model."""
        self._options.model = model
        return self

    def with_system_prompt(self, system_prompt: str) -> "QueryBuilder":
        """Set the system prompt."""
        self._options.system_prompt = system_prompt
        return self

    def with_tools(self, tools: list[Callable]) -> "QueryBuilder":
        """Set the tools."""
        self._tools = tools
        return self

    def with_timeout(self, timeout_seconds: float) -> "QueryBuilder":
        """Set the timeout."""
        self._options.timeout_seconds = timeout_seconds
        return self

    def with_max_turns(self, max_turns: int) -> "QueryBuilder":
        """Set the maximum turns."""
        self._options.max_turns = max_turns
        return self

    def with_permission_mode(self, mode: str) -> "QueryBuilder":
        """Set the permission mode."""
        self._options.permission_mode = mode
        return self

    def with_working_directory(self, directory: str) -> "QueryBuilder":
        """Set the working directory."""
        self._options.working_directory = directory
        return self

    def with_hook(self, event: str, handler: Callable) -> "QueryBuilder":
        """Add a hook handler."""
        if event not in self._hooks:
            self._hooks[event] = []
        self._hooks[event].append(handler)
        return self

    def with_option(self, key: str, value: Any) -> "QueryBuilder":
        """Set a custom option."""
        setattr(self._options, key, value)
        return self

    async def execute(self) -> str:
        """Execute the query and return the final result."""
        self._options.hooks = self._hooks

        async with AgentClient(options=self._options) as client:
            for tool_func in self._tools:
                client.register_tool(tool_func)

            await client.query(self._prompt)

            final_result = ""
            async for message in client.receive_response():
                if isinstance(message, ResultMessage):
                    final_result = message.result
                elif isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            final_result = block.text

            return final_result

    async def execute_streaming(self) -> AsyncIterator[str]:
        """Execute the query and yield streaming text."""
        self._options.hooks = self._hooks

        async with AgentClient(options=self._options) as client:
            for tool_func in self._tools:
                client.register_tool(tool_func)

            await client.query(self._prompt)

            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            yield block.text
                elif isinstance(message, ResultMessage):
                    if message.result:
                        yield message.result

    def build(self) -> tuple[str, AgentOptions, list[Callable]]:
        """Build and return the query components."""
        return self._prompt, self._options, self._tools
