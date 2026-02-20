"""
Agent Client for OpenFinance.

Provides bidirectional, interactive conversations with the agent.
Inspired by Claude Agent SDK ClaudeSDKClient.
"""

import asyncio
import logging
import uuid
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any, Callable

from pydantic import BaseModel

from openfinance.agents.types import (
    AgentOptions,
    AssistantMessage,
    HookInput,
    HookOutput,
    MessageUnion,
    PermissionDecision,
    ResultMessage,
    SessionState,
    TextBlock,
    ToolDefinition,
    ToolInvocation,
    ToolResultBlock,
    ToolState,
    ToolUseBlock,
    UserMessage,
)
from openfinance.agents.registry.registration import SkillRegistry
from openfinance.agents.lifecycle.manager import SkillLifecycleManager

logger = logging.getLogger(__name__)


class AgentClient:
    """Bidirectional interactive agent client.

    This class provides a rich interface for interacting with the agent,
    including tool registration, hooks, and streaming responses.

    Example:
        async with AgentClient(options=options) as client:
            client.register_tool(my_tool)
            client.register_hook("PreToolUse", my_hook)

            await client.query("Hello!")

            async for message in client.receive_response():
                print(message)
    """

    def __init__(
        self,
        options: AgentOptions | None = None,
        llm_provider: Any = None,
    ) -> None:
        self.options = options or AgentOptions()
        self.llm_provider = llm_provider

        self._session: SessionState | None = None
        self._tools: dict[str, ToolDefinition] = {}
        self._tool_handlers: dict[str, Callable] = {}
        self._hooks: dict[str, list[Callable]] = {}
        self._message_queue: asyncio.Queue[MessageUnion] = asyncio.Queue()
        self._is_connected = False
        self._is_processing = False

        self._registry = SkillRegistry()
        self._lifecycle = SkillLifecycleManager()

    async def __aenter__(self) -> "AgentClient":
        """Enter the async context."""
        await self._initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the async context."""
        await self._cleanup()

    async def _initialize(self) -> None:
        """Initialize the client."""
        self._session = SessionState(
            session_id=f"session_{uuid.uuid4().hex[:12]}",
        )
        self._is_connected = True
        self._is_processing = False

        for event, handlers in self.options.hooks.items():
            for handler in handlers:
                self.register_hook(event, handler)

        logger.info(f"AgentClient initialized: {self._session.session_id}")

    async def _cleanup(self) -> None:
        """Cleanup resources."""
        self._is_connected = False
        self._is_processing = False
        logger.info(f"AgentClient cleanup: {self._session.session_id if self._session else 'unknown'}")

    @property
    def session(self) -> SessionState | None:
        """Get the current session state."""
        return self._session

    @property
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._is_connected

    def register_tool(
        self,
        func: Callable,
        name: str | None = None,
        description: str | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> None:
        """Register a tool function.

        Args:
            func: The tool function.
            name: Optional tool name (defaults to function name).
            description: Optional tool description.
            parameters: Optional parameter schema.

        Example:
            @client.register_tool
            async def get_stock_price(symbol: str) -> float:
                return 150.0
        """
        tool_name = name or func.__name__
        tool_description = description or func.__doc__ or f"Tool: {tool_name}"

        tool_def = ToolDefinition(
            name=tool_name,
            description=tool_description,
            parameters=parameters or {},
        )

        self._tools[tool_name] = tool_def
        self._tool_handlers[tool_name] = func

        logger.debug(f"Registered tool: {tool_name}")

    def register_hook(
        self,
        event: str,
        handler: Callable,
    ) -> None:
        """Register a hook handler for an event.

        Args:
            event: The hook event name.
            handler: The hook handler function.

        Example:
            async def check_bash(input: HookInput) -> HookOutput:
                if "rm -rf" in input.tool_input.get("command", ""):
                    return HookOutput(
                        permission_decision=PermissionDecision.DENY,
                        permission_decision_reason="Dangerous command",
                    )
                return HookOutput()

            client.register_hook("PreToolUse", check_bash)
        """
        if event not in self._hooks:
            self._hooks[event] = []
        self._hooks[event].append(handler)
        logger.debug(f"Registered hook: {event}")

    def get_tools(self) -> list[ToolDefinition]:
        """Get all registered tools."""
        return list(self._tools.values())

    def get_openai_tools(self) -> list[dict[str, Any]]:
        """Get tools in OpenAI format."""
        return [t.to_openai_tool() for t in self._tools.values()]

    def get_anthropic_tools(self) -> list[dict[str, Any]]:
        """Get tools in Anthropic format."""
        return [t.to_anthropic_tool() for t in self._tools.values()]

    async def query(self, prompt: str) -> None:
        """Send a query to the agent.

        Args:
            prompt: The user prompt.
        """
        if not self._session:
            raise RuntimeError("Client not initialized. Use async context manager.")

        user_message = UserMessage.from_text(prompt)
        self._session.add_message(user_message)

        self._is_processing = True
        asyncio.create_task(self._process_query())

    async def send_message(self, message: UserMessage) -> None:
        """Send a user message to the agent.

        Args:
            message: The user message to send.
        """
        if not self._session:
            raise RuntimeError("Client not initialized. Use async context manager.")

        self._session.add_message(message)

        if not self._is_processing:
            self._is_processing = True
            asyncio.create_task(self._process_query())

    async def receive_response(self) -> AsyncIterator[MessageUnion]:
        """Receive messages from the agent.

        Yields:
            MessageUnion: Messages from the agent.
        """
        while True:
            message = await self._message_queue.get()

            yield message

            if isinstance(message, ResultMessage):
                break

    async def _process_query(self) -> None:
        """Process the current query."""
        try:
            if not self._session:
                return

            turn_count = 0
            should_continue = True

            while should_continue and turn_count < self.options.max_turns:
                turn_count += 1
                self._session.current_turn = turn_count

                response = await self._generate_response()

                if response:
                    self._session.add_message(response)
                    await self._message_queue.put(response)

                    tool_uses = [
                        block for block in response.content
                        if isinstance(block, ToolUseBlock)
                    ]

                    if tool_uses:
                        for tool_use in tool_uses:
                            result = await self._execute_tool(tool_use)
                            result_message = UserMessage(
                                content=[result],
                            )
                            self._session.add_message(result_message)
                            await self._message_queue.put(result_message)
                    else:
                        should_continue = False
                else:
                    should_continue = False

            duration_ms = (
                datetime.now() - self._session.created_at
            ).total_seconds() * 1000

            result_message = ResultMessage(
                result=self._extract_final_result(),
                success=True,
                duration_ms=duration_ms,
                iterations=turn_count,
                tool_calls=len(self._session.tool_invocations),
            )

            self._session.add_message(result_message)
            await self._message_queue.put(result_message)

            self._session.is_complete = True

        except Exception as e:
            logger.exception("Error processing query")

            error_result = ResultMessage(
                result="",
                success=False,
                duration_ms=0,
            )
            error_result.error = str(e)

            await self._message_queue.put(error_result)

        finally:
            self._is_processing = False

    async def _generate_response(self) -> AssistantMessage | None:
        """Generate a response using the LLM."""
        if not self._session:
            return None

        if self.llm_provider:
            return await self._call_llm()
        else:
            return await self._mock_response()

    async def _call_llm(self) -> AssistantMessage | None:
        """Call the LLM provider."""
        if hasattr(self.llm_provider, "agenerate"):
            messages = self._build_message_history()
            response = await self.llm_provider.agenerate(
                messages,
                tools=self.get_anthropic_tools() if self._tools else None,
            )
            return self._parse_llm_response(response)
        elif hasattr(self.llm_provider, "generate"):
            messages = self._build_message_history()
            response = self.llm_provider.generate(
                messages,
                tools=self.get_anthropic_tools() if self._tools else None,
            )
            return self._parse_llm_response(response)

        return await self._mock_response()

    def _build_message_history(self) -> list[dict[str, Any]]:
        """Build message history for LLM."""
        messages = []

        if self.options.system_prompt:
            messages.append({
                "role": "system",
                "content": self.options.system_prompt,
            })

        if self._session:
            for msg in self._session.messages:
                messages.append({
                    "role": msg.role,
                    "content": self._serialize_content(msg.content),
                })

        return messages

    def _serialize_content(self, content: list[Any]) -> str:
        """Serialize content blocks to string."""
        parts = []
        for block in content:
            if isinstance(block, TextBlock):
                parts.append(block.text)
            elif isinstance(block, ToolResultBlock):
                parts.append(f"[Tool Result: {block.content}]")
        return "\n".join(parts)

    def _parse_llm_response(self, response: Any) -> AssistantMessage:
        """Parse LLM response into AssistantMessage."""
        if isinstance(response, dict):
            content = response.get("content", "")
            tool_calls = response.get("tool_calls", [])

            blocks: list[Any] = []

            if content:
                blocks.append(TextBlock(text=content))

            for tc in tool_calls:
                blocks.append(ToolUseBlock(
                    id=tc.get("id", str(uuid.uuid4())),
                    name=tc.get("name", ""),
                    input=tc.get("arguments", {}),
                ))

            return AssistantMessage(content=blocks)

        return AssistantMessage(content=[TextBlock(text=str(response))])

    async def _mock_response(self) -> AssistantMessage:
        """Generate a mock response for testing."""
        if not self._session:
            return AssistantMessage(content=[TextBlock(text="")])

        last_message = self._session.messages[-1] if self._session.messages else None
        query_text = ""

        if isinstance(last_message, UserMessage):
            for block in last_message.content:
                if isinstance(block, TextBlock):
                    query_text = block.text
                    break

        if self._tools and not any(
            isinstance(block, ToolUseBlock)
            for msg in self._session.messages
            if isinstance(msg, AssistantMessage)
            for block in msg.content
        ):
            tool_name = list(self._tools.keys())[0]
            return AssistantMessage(
                content=[
                    TextBlock(text=f"Processing: {query_text}"),
                    ToolUseBlock(
                        id=str(uuid.uuid4()),
                        name=tool_name,
                        input={"query": query_text},
                    ),
                ],
            )

        return AssistantMessage(
            content=[TextBlock(text=f"Response to: {query_text}")],
        )

    async def _execute_tool(self, tool_use: ToolUseBlock) -> ToolResultBlock:
        """Execute a tool and return the result."""
        tool_name = tool_use.name
        tool_input = tool_use.input

        invocation = ToolInvocation(
            invocation_id=tool_use.id,
            tool_name=tool_name,
            arguments=tool_input,
            state=ToolState.RUNNING,
            started_at=datetime.now(),
        )

        if self._session:
            self._session.tool_invocations.append(invocation)

        hook_result = await self._run_hooks("PreToolUse", HookInput(
            hook_event_name="PreToolUse",
            tool_name=tool_name,
            tool_input=tool_input,
            tool_use_id=tool_use.id,
        ))

        if hook_result.permission_decision == PermissionDecision.DENY:
            invocation.state = ToolState.CANCELLED
            invocation.error = hook_result.permission_decision_reason or "Denied by hook"
            return ToolResultBlock(
                tool_use_id=tool_use.id,
                content=invocation.error,
                is_error=True,
            )

        if hook_result.modified_input:
            tool_input = hook_result.modified_input
            invocation.arguments = tool_input

        handler = self._tool_handlers.get(tool_name)

        try:
            if handler:
                result = handler(**tool_input)
                if asyncio.iscoroutine(result):
                    result = await result

                invocation.result = str(result)
                invocation.state = ToolState.COMPLETED
            else:
                result = f"Tool '{tool_name}' not found"
                invocation.result = result
                invocation.state = ToolState.FAILED
                invocation.error = result

        except Exception as e:
            result = f"Error executing {tool_name}: {str(e)}"
            invocation.state = ToolState.FAILED
            invocation.error = str(e)
            invocation.result = result

        finally:
            invocation.completed_at = datetime.now()
            if invocation.started_at:
                invocation.duration_ms = (
                    invocation.completed_at - invocation.started_at
                ).total_seconds() * 1000

        post_hook_result = await self._run_hooks("PostToolUse", HookInput(
            hook_event_name="PostToolUse",
            tool_name=tool_name,
            tool_input=tool_input,
            tool_use_id=tool_use.id,
            tool_result=invocation.result,
        ))

        final_result = post_hook_result.modified_result or invocation.result or ""

        return ToolResultBlock(
            tool_use_id=tool_use.id,
            content=final_result,
            is_error=invocation.state == ToolState.FAILED,
            duration_ms=invocation.duration_ms,
        )

    async def _run_hooks(
        self,
        event: str,
        input_data: HookInput,
    ) -> HookOutput:
        """Run all hooks for an event."""
        handlers = self._hooks.get(event, [])
        result = HookOutput()

        for handler in handlers:
            try:
                output = handler(input_data)
                if asyncio.iscoroutine(output):
                    output = await output

                if isinstance(output, HookOutput):
                    if output.permission_decision is not None:
                        result.permission_decision = output.permission_decision
                    if output.permission_decision_reason is not None:
                        result.permission_decision_reason = output.permission_decision_reason
                    if output.modified_input is not None:
                        result.modified_input = output.modified_input
                    if output.modified_result is not None:
                        result.modified_result = output.modified_result
                    if not output.continue_:
                        break

            except Exception as e:
                logger.exception(f"Hook failed: {event}")

        return result

    def _extract_final_result(self) -> str:
        """Extract the final result from the session."""
        if not self._session:
            return ""

        for message in reversed(self._session.messages):
            if isinstance(message, AssistantMessage):
                for block in reversed(message.content):
                    if isinstance(block, TextBlock):
                        return block.text

        return ""

    async def stop(self) -> None:
        """Stop the current processing."""
        self._is_processing = False

    def get_stats(self) -> dict[str, Any]:
        """Get client statistics."""
        if not self._session:
            return {"status": "not_initialized"}

        return {
            "session_id": self._session.session_id,
            "is_connected": self._is_connected,
            "is_processing": self._is_processing,
            "turn": self._session.current_turn,
            "messages": len(self._session.messages),
            "tool_invocations": len(self._session.tool_invocations),
            "tools_registered": len(self._tools),
            "hooks_registered": sum(len(v) for v in self._hooks.values()),
        }
