"""
Agents Module for OpenFinance.

Provides a comprehensive agentic system with tools, hooks, and skills management.
Inspired by Claude Agent SDK and nanobot architecture.
"""

from openfinance.agents.types import (
    AgentOptions,
    AssistantMessage,
    ContentBlock,
    ContentBlockUnion,
    HookInput,
    HookMatcher,
    HookOutput,
    ImageBlock,
    MessageRole,
    MessageUnion,
    PermissionDecision,
    ResourceBlock,
    ResultMessage,
    SessionState,
    SkillContext,
    SkillResult,
    SystemMessage,
    TextBlock,
    ToolDefinition,
    ToolInvocation,
    ToolResultBlock,
    ToolState,
    ToolUseBlock,
    UserMessage,
)

from openfinance.agents.config import Config, get_config

from openfinance.agents.bus import MessageBus, InboundMessage, OutboundMessage
from openfinance.agents.session import SessionManager, Session
from openfinance.agents.core import AgentLoop, ContextBuilder, MemoryStore
from openfinance.agents.skills import SkillsLoader, SkillRegistry
from openfinance.agents.tools import (
    tool,
    tool_function,
    MCPServer,
    create_sdk_mcp_server,
    InProcessMCPServer,
    register_builtin_tools,
    get_builtin_tools,
)
from openfinance.agents.tools.base import Tool
from openfinance.agents.tools.registry import ToolRegistry

from openfinance.agents.hooks import HookRegistry, HookEvent, hook
from openfinance.agents.lifecycle.manager import SkillLifecycleManager
from openfinance.agents.priority.sorter import SkillPrioritySorter
from openfinance.agents.error.handler import SkillErrorHandler

from openfinance.agents.component import (
    SkillComponent,
    SkillDefinition,
    SkillLoader,
    ScriptExecutor,
    ScriptInfo,
    ReferenceInfo,
    AssetInfo,
    ScriptType,
    SkillStatus,
    SkillComponentType,
)

from openfinance.agents.client import AgentClient
from openfinance.agents.query import (
    query,
    query_simple,
    query_streaming,
    query_with_tools,
    QueryBuilder,
)

__all__ = [
    "AgentClient",
    "AgentLoop",
    "AgentOptions",
    "AssistantMessage",
    "Config",
    "ContentBlock",
    "ContentBlockUnion",
    "ContextBuilder",
    "HookEvent",
    "HookInput",
    "HookMatcher",
    "HookOutput",
    "HookRegistry",
    "InProcessMCPServer",
    "InboundMessage",
    "MCPServer",
    "MemoryStore",
    "MessageBus",
    "MessageRole",
    "MessageUnion",
    "OutboundMessage",
    "PermissionDecision",
    "QueryBuilder",
    "ResourceBlock",
    "ResultMessage",
    "Session",
    "SessionManager",
    "SessionState",
    "SkillComponent",
    "SkillContext",
    "SkillDefinition",
    "SkillErrorHandler",
    "SkillLifecycleManager",
    "SkillLoader",
    "SkillPrioritySorter",
    "SkillRegistry",
    "SkillResult",
    "SystemMessage",
    "TextBlock",
    "Tool",
    "ToolDefinition",
    "ToolInvocation",
    "ToolRegistry",
    "ToolResultBlock",
    "ToolState",
    "ToolUseBlock",
    "UserMessage",
    "create_sdk_mcp_server",
    "get_builtin_tools",
    "get_config",
    "hook",
    "query",
    "query_simple",
    "query_streaming",
    "query_with_tools",
    "register_builtin_tools",
    "tool",
    "tool_function",
    "ScriptExecutor",
    "ScriptInfo",
    "ReferenceInfo",
    "AssetInfo",
    "ScriptType",
    "SkillStatus",
    "SkillComponentType",
]
