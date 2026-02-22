"""Agent loop: the core processing engine.

Adapted from nanobot's agent loop for OpenFinance agents.
"""

import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, AsyncIterator, Optional

import logging

logger = logging.getLogger(__name__)

from openfinance.agents.bus.events import InboundMessage, OutboundMessage
from openfinance.agents.bus.queue import MessageBus
from openfinance.agents.core.context import ContextBuilder
from openfinance.agents.core.memory import MemoryStore
from openfinance.agents.session.manager import SessionManager, Session
from openfinance.agents.tools.registry import ToolRegistry
from openfinance.agents.config import Config, get_config


@dataclass
class LoopEvent:
    """Event emitted during agent loop processing."""
    type: str
    iteration: int = 0
    content: Optional[str] = None
    tool_name: Optional[str] = None
    tool_args: Optional[dict[str, Any]] = None
    tool_result: Optional[str] = None
    tool_call_id: Optional[str] = None
    success: bool = True
    duration_ms: float = 0.0
    has_tool_calls: bool = False
    progress: float = 0.0
    message: Optional[str] = None


@dataclass
class StreamConfig:
    """Configuration for streaming behavior."""
    max_iterations: int = 10
    include_thinking: bool = True
    include_tool_results: bool = True
    max_result_preview: int = 2000
    stream_final_response: bool = True


class AgentLoop:
    """
    The agent loop is the core processing engine.
    
    It:
    1. Receives messages from the bus
    2. Builds context with history, memory, skills
    3. Calls the LLM
    4. Executes tool calls
    5. Sends responses back
    
    Supports both synchronous and streaming modes.
    """
    
    def __init__(
        self,
        bus: MessageBus | None = None,
        llm_client: Any = None,
        workspace: Path | None = None,
        model: str | None = None,
        max_iterations: int = 10,
        config: Config | None = None,
        session_manager: SessionManager | None = None,
    ):
        self.bus = bus
        self.llm_client = llm_client
        self.workspace = workspace or Path.home() / ".openfinance" / "workspace"
        self.config = config or get_config()
        self.model = model or self.config.agents.defaults.model
        self.max_iterations = max_iterations
        
        self.context = ContextBuilder(self.workspace)
        self.sessions = session_manager or SessionManager(self.workspace)
        self.tools = ToolRegistry()
        
        self._running = False
        self._register_default_tools()
    
    def _register_default_tools(self) -> None:
        """Register the default set of tools."""
        from openfinance.agents.tools.builtin import get_builtin_tools
        
        for tool_func in get_builtin_tools():
            if hasattr(tool_func, "_tool_definition"):
                self.tools.register_from_definition(tool_func._tool_definition, tool_func)
    
    def register_tool(self, name: str, handler: Callable, definition: dict[str, Any] | None = None) -> None:
        """Register a custom tool."""
        self.tools.register(name, handler, definition)
    
    def get_tool_definitions(self) -> list[dict[str, Any]]:
        """Get all registered tool definitions."""
        return self.tools.get_definitions()
    
    async def run(self) -> None:
        """Run the agent loop, processing messages from the bus."""
        if not self.bus:
            logger.error("No message bus configured")
            return
            
        self._running = True
        logger.info("Agent loop started")
        
        while self._running:
            try:
                msg = await asyncio.wait_for(
                    self.bus.consume_inbound(),
                    timeout=1.0
                )
                
                try:
                    response = await self._process_message(msg)
                    if response:
                        await self.bus.publish_outbound(response)
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    await self.bus.publish_outbound(OutboundMessage(
                        channel=msg.channel,
                        chat_id=msg.chat_id,
                        content=f"Sorry, I encountered an error: {str(e)}"
                    ))
            except asyncio.TimeoutError:
                continue
    
    def stop(self) -> None:
        """Stop the agent loop."""
        self._running = False
        logger.info("Agent loop stopping")
    
    async def _process_message(self, msg: InboundMessage) -> OutboundMessage | None:
        """Process a single inbound message."""
        preview = msg.content[:80] + "..." if len(msg.content) > 80 else msg.content
        logger.info(f"Processing message from {msg.channel}:{msg.sender_id}: {preview}")
        
        final_content = None
        async for event in self.stream_process(msg.content, msg.session_key, msg.channel, msg.chat_id):
            if event.type == "final":
                final_content = event.content
        
        if final_content is None:
            final_content = "I've completed processing but have no response to give."
        
        return OutboundMessage(
            channel=msg.channel,
            chat_id=msg.chat_id,
            content=final_content
        )
    
    async def stream_process(
        self,
        content: str,
        session_key: str = "web:default",
        channel: str = "web",
        chat_id: str = "default",
        history: list[dict[str, Any]] | None = None,
        system_prompt: str | None = None,
        stream_config: StreamConfig | None = None,
    ) -> AsyncIterator[LoopEvent]:
        """
        Process a message with streaming events.
        
        This is the main entry point for streaming processing.
        Yields LoopEvent objects for each step of the process.
        """
        start_time = time.time()
        config = stream_config or StreamConfig(max_iterations=self.max_iterations)
        
        self._running = True
        
        session = self.sessions.get_or_create(session_key)
        
        if history is None:
            history = session.get_history(max_messages=50)
        
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        else:
            messages.append({"role": "system", "content": self.context.build_system_prompt()})
        
        if history:
            messages.extend(history)
        
        messages.append({"role": "user", "content": content})
        print(f"messages: {messages}")
        session.add_message("user", content)
        
        yield LoopEvent(
            type="status",
            message="正在分析您的问题...",
            progress=0.1,
        )
        
        tools = self.get_tool_definitions()
        iteration = 0
        final_content = None
        total_tool_calls = 0
        
        while iteration < config.max_iterations and self._running:
            iteration += 1
            
            yield LoopEvent(
                type="status",
                iteration=iteration,
                message=f"思考中 (第{iteration}轮)...",
                progress=0.1 + (iteration * 0.05),
            )
            
            if not self._running:
                logger.info("Processing stopped by user request")
                break
            
            try:
                response = await self._call_llm(messages, tools)
            except Exception as e:
                logger.error(f"LLM call failed: {e}")
                yield LoopEvent(
                    type="error",
                    message=f"LLM 调用失败：{str(e)}",
                )
                break
            
            tool_calls = response.get("tool_calls", [])
            response_content = response.get("content")
            
            if config.include_thinking and response_content:
                yield LoopEvent(
                    type="thinking",
                    iteration=iteration,
                    content=response_content,
                    has_tool_calls=len(tool_calls) > 0,
                )
            
            if not tool_calls:
                if response_content:
                    final_content = response_content
                    break
                else:
                    if iteration >= config.max_iterations - 1:
                        final_content = "抱歉，我没有生成有效的回复。请尝试重新提问。"
                        break
                    continue
            
            total_tool_calls += len(tool_calls)
            
            tool_call_dicts = [
                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {
                        "name": tc["function"]["name"],
                        "arguments": tc["function"]["arguments"]
                    }
                }
                for tc in tool_calls
            ]
            messages.append({
                "role": "assistant",
                "content": response_content,
                "tool_calls": tool_call_dicts
            })
            
            for tool_call in tool_calls:
                tool_name = tool_call["function"]["name"]
                tool_call_id = tool_call.get("id", f"{tool_name}-{time.time()}")
                args_str = tool_call["function"]["arguments"]
                
                try:
                    args = json.loads(args_str)
                except json.JSONDecodeError:
                    args = {}
                
                args_summary = self._summarize_args(tool_name, args)
                
                yield LoopEvent(
                    type="progress",
                    iteration=iteration,
                    message=f"正在执行 {tool_name}: {args_summary}" if args_summary else f"正在调用工具：{tool_name}...",
                    progress=0.3 + (iteration * 0.1),
                    tool_name=tool_name,
                    tool_args=args,
                    tool_call_id=tool_call_id,
                )
                
                tool_start_time = time.time()
                try:
                    result = await self.tools.execute(tool_name, args)
                    duration_ms = (time.time() - tool_start_time) * 1000
                    
                    result_str = str(result)
                    if len(result_str) > config.max_result_preview:
                        result_preview = result_str[:config.max_result_preview] + "..."
                    else:
                        result_preview = result_str
                    
                    if config.include_tool_results:
                        yield LoopEvent(
                            type="tool_result",
                            iteration=iteration,
                            tool_name=tool_name,
                            tool_args=args,
                            tool_call_id=tool_call_id,
                            success=True,
                            duration_ms=duration_ms,
                            tool_result=result_preview,
                            message=f"{tool_name} 执行完成",
                        )
                    
                except Exception as e:
                    result = f"Error executing {tool_name}: {str(e)}"
                    duration_ms = (time.time() - tool_start_time) * 1000
                    
                    yield LoopEvent(
                        type="tool_result",
                        iteration=iteration,
                        tool_name=tool_name,
                        tool_args=args,
                        tool_call_id=tool_call_id,
                        success=False,
                        duration_ms=duration_ms,
                        message=f"工具 {tool_name} 执行失败",
                    )
                
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "name": tool_name,
                    "content": result
                })
        
        total_duration = (time.time() - start_time) * 1000
        
        if final_content is None:
            final_content = "处理完成，但没有生成回复内容。"
        
        yield LoopEvent(
            type="status",
            message="正在生成回复...",
            progress=0.9,
        )
        
        if config.stream_final_response and self.llm_client and hasattr(self.llm_client, 'stream'):
            yield LoopEvent(type="content_start")
            
            streamed_content = []
            summary_prompt = f"请用专业的分析视角依旧以下内容：\n\n{final_content} \n\n 回复用户问题：{content}"
            
            try:
                async for chunk in self.llm_client.stream([{"role": "user", "content": summary_prompt}]):
                    if not self._running:
                        logger.info("Stream stopped by user request")
                        break
                    if chunk and isinstance(chunk, str):
                        streamed_content.append(chunk)
                        yield LoopEvent(type="content", content=chunk)
            except Exception as e:
                logger.warning(f"Stream failed, using original content: {e}")
                if self._running:
                    yield LoopEvent(type="content", content=final_content)
                    streamed_content = [final_content]
            
            final_content = "".join(streamed_content) if streamed_content else final_content
        else:
            yield LoopEvent(type="content", content=final_content)
        
        session.add_message("assistant", final_content)
        self.sessions.save(session)
        
        yield LoopEvent(
            type="status",
            message="处理完成",
            progress=1.0,
        )
        
        yield LoopEvent(
            type="final",
            content=final_content,
            duration_ms=total_duration,
        )
    
    def _summarize_args(self, tool_name: str, args: dict[str, Any]) -> str:
        """Create a brief summary of tool arguments."""
        if not args:
            return ""
        
        key_values = []
        for key, value in args.items():
            if key.startswith('_') or key in ['context', 'metadata', 'options']:
                continue
            
            str_value = str(value)
            if len(str_value) > 60:
                str_value = str_value[:60] + "..."
            
            key_values.append(f"{key}={str_value}")
        
        if len(key_values) == 1:
            return key_values[0]
        elif len(key_values) <= 3:
            return ", ".join(key_values)
        else:
            return ", ".join(key_values[:2]) + f" (+{len(key_values) - 2} more)"
    
    async def _call_llm(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Call the LLM with messages."""
        if not self.llm_client:
            return {"content": "LLM client not configured", "tool_calls": []}
        
        try:
            if hasattr(self.llm_client, "_get_async_client"):
                client = self.llm_client._get_async_client()
                if client is None:
                    return {"content": "LLM client not available", "tool_calls": []}
                
                response = await client.chat.completions.create(
                    model=self.llm_client.model if hasattr(self.llm_client, "model") else self.model,
                    messages=messages,
                    tools=tools if tools else None,
                    tool_choice="auto" if tools else None,
                    temperature=0.7,
                    max_tokens=4096,
                )
                
                choice = response.choices[0]
                return {
                    "content": choice.message.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        }
                        for tc in (choice.message.tool_calls or [])
                    ]
                }
            elif hasattr(self.llm_client, "chat"):
                response = await self.llm_client.chat(
                    messages=messages,
                    tools=tools if tools else None,
                    model=self.model
                )
                if hasattr(response, "__dict__"):
                    return {
                        "content": response.content,
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "function": {
                                    "name": tc.name,
                                    "arguments": json.dumps(tc.arguments)
                                }
                            }
                            for tc in (response.tool_calls or [])
                        ]
                    }
                return response
            else:
                response = self.llm_client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=tools if tools else None,
                    tool_choice="auto" if tools else None,
                )
                choice = response.choices[0]
                return {
                    "content": choice.message.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        }
                        for tc in (choice.message.tool_calls or [])
                    ]
                }
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return {"content": f"Error: {str(e)}", "tool_calls": []}
    
    async def process_direct(
        self,
        content: str,
        session_key: str = "cli:direct",
        channel: str = "cli",
        chat_id: str = "direct",
    ) -> str:
        """
        Process a message directly (for CLI or direct usage).
        
        Args:
            content: The message content.
            session_key: Session identifier.
            channel: Source channel.
            chat_id: Source chat ID.
        
        Returns:
            The agent's response.
        """
        final_content = None
        async for event in self.stream_process(content, session_key, channel, chat_id):
            if event.type == "final":
                final_content = event.content
        
        return final_content or ""


_agent_loop_instance: AgentLoop | None = None


def get_agent_loop(
    llm_client: Any = None,
    workspace: Path | None = None,
    session_manager: SessionManager | None = None,
) -> AgentLoop:
    """Get or create the global agent loop instance."""
    global _agent_loop_instance
    
    if _agent_loop_instance is None:
        from openfinance.agents.llm.client import get_llm_client
        _agent_loop_instance = AgentLoop(
            llm_client=llm_client or get_llm_client(),
            workspace=workspace,
            session_manager=session_manager,
        )
    
    return _agent_loop_instance
