"""
Skill Types for OpenFinance.

Defines message types and data structures for the agentic system.
Inspired by Claude Agent SDK type system.
"""

from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    """Message roles."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class PermissionDecision(str, Enum):
    """Permission decision for tool use."""

    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"


class ToolState(str, Enum):
    """Tool execution state."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ContentBlock(BaseModel):
    """Base class for content blocks."""

    type: str = Field(..., description="Block type")


class TextBlock(ContentBlock):
    """Text content block."""

    type: Literal["text"] = "text"
    text: str = Field(..., description="Text content")


class ToolUseBlock(ContentBlock):
    """Tool use request block."""

    type: Literal["tool_use"] = "tool_use"
    id: str = Field(..., description="Unique tool use ID")
    name: str = Field(..., description="Tool name")
    input: dict[str, Any] = Field(
        default_factory=dict,
        description="Tool input arguments",
    )


class ToolResultBlock(ContentBlock):
    """Tool execution result block."""

    type: Literal["tool_result"] = "tool_result"
    tool_use_id: str = Field(..., description="Corresponding tool use ID")
    content: str = Field(..., description="Result content")
    is_error: bool = Field(default=False, description="Whether result is an error")
    duration_ms: float | None = Field(default=None, description="Execution duration")


class ImageBlock(ContentBlock):
    """Image content block."""

    type: Literal["image"] = "image"
    source: dict[str, Any] = Field(..., description="Image source")
    alt_text: str | None = Field(default=None, description="Alt text")


class ResourceBlock(ContentBlock):
    """Resource reference block."""

    type: Literal["resource"] = "resource"
    uri: str = Field(..., description="Resource URI")
    mime_type: str | None = Field(default=None, description="MIME type")
    name: str | None = Field(default=None, description="Resource name")


ContentBlockUnion = Union[
    TextBlock,
    ToolUseBlock,
    ToolResultBlock,
    ImageBlock,
    ResourceBlock,
]


class BaseMessage(BaseModel):
    """Base class for all messages."""

    id: str | None = Field(default=None, description="Message ID")
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Message timestamp",
    )


class UserMessage(BaseMessage):
    """User message."""

    role: Literal["user"] = "user"
    content: list[ContentBlockUnion] = Field(
        default_factory=list,
        description="Message content blocks",
    )

    @classmethod
    def from_text(cls, text: str, **kwargs: Any) -> "UserMessage":
        """Create a user message from text."""
        return cls(content=[TextBlock(text=text)], **kwargs)


class AssistantMessage(BaseMessage):
    """Assistant message."""

    role: Literal["assistant"] = "assistant"
    content: list[ContentBlockUnion] = Field(
        default_factory=list,
        description="Message content blocks",
    )
    model: str | None = Field(default=None, description="Model used")
    stop_reason: str | None = Field(default=None, description="Stop reason")
    usage: dict[str, int] | None = Field(default=None, description="Token usage")

    @classmethod
    def from_text(cls, text: str, **kwargs: Any) -> "AssistantMessage":
        """Create an assistant message from text."""
        return cls(content=[TextBlock(text=text)], **kwargs)


class SystemMessage(BaseMessage):
    """System message."""

    role: Literal["system"] = "system"
    content: str = Field(..., description="System message content")
    level: str = Field(default="info", description="Message level")


class ResultMessage(BaseMessage):
    """Result message indicating task completion."""

    type: Literal["result"] = "result"
    result: str = Field(..., description="Final result")
    success: bool = Field(default=True, description="Whether task succeeded")
    cost_usd: float = Field(default=0.0, description="Total cost in USD")
    duration_ms: float = Field(..., description="Total duration")
    iterations: int = Field(default=1, description="Number of iterations")
    tool_calls: int = Field(default=0, description="Number of tool calls")
    tokens_used: int = Field(default=0, description="Total tokens used")


MessageUnion = Union[
    UserMessage,
    AssistantMessage,
    SystemMessage,
    ResultMessage,
]


class ToolDefinition(BaseModel):
    """Definition of a tool."""

    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="JSON Schema for parameters",
    )
    required: list[str] = Field(
        default_factory=list,
        description="Required parameters",
    )
    category: str = Field(default="general", description="Tool category")
    dangerous: bool = Field(default=False, description="Whether tool is dangerous")
    timeout_seconds: float = Field(default=30.0, description="Execution timeout")

    def to_openai_tool(self) -> dict[str, Any]:
        """Convert to OpenAI tool format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": self.parameters,
                    "required": self.required,
                },
            },
        }

    def to_anthropic_tool(self) -> dict[str, Any]:
        """Convert to Anthropic tool format."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": self.parameters,
                "required": self.required,
            },
        }


class ToolInvocation(BaseModel):
    """Tool invocation record."""

    invocation_id: str = Field(..., description="Unique invocation ID")
    tool_name: str = Field(..., description="Tool name")
    arguments: dict[str, Any] = Field(
        default_factory=dict,
        description="Tool arguments",
    )
    state: ToolState = Field(default=ToolState.PENDING, description="Execution state")
    result: str | None = Field(default=None, description="Execution result")
    error: str | None = Field(default=None, description="Error message")
    duration_ms: float = Field(default=0.0, description="Execution duration")
    started_at: datetime | None = Field(default=None, description="Start time")
    completed_at: datetime | None = Field(default=None, description="Completion time")


class AgentOptions(BaseModel):
    """Configuration options for the agent."""

    model: str = Field(default="claude-sonnet-4-20250514", description="Model to use")
    system_prompt: str | None = Field(default=None, description="System prompt")
    max_turns: int = Field(default=10, description="Maximum conversation turns")
    max_tokens: int = Field(default=4096, description="Maximum output tokens")
    temperature: float = Field(default=0.7, description="Temperature")

    allowed_tools: list[str] = Field(
        default_factory=lambda: ["*"],
        description="Allowed tools (* for all)",
    )
    disallowed_tools: list[str] = Field(
        default_factory=list,
        description="Disallowed tools",
    )
    permission_mode: str = Field(
        default="default",
        description="Permission mode: default, acceptEdits, bypassPermissions",
    )

    working_directory: str | None = Field(
        default=None,
        description="Working directory for file operations",
    )
    timeout_seconds: float = Field(default=300.0, description="Total timeout")
    max_budget_usd: float | None = Field(
        default=None,
        description="Maximum budget in USD",
    )

    enable_caching: bool = Field(default=True, description="Enable response caching")
    enable_streaming: bool = Field(default=True, description="Enable streaming")
    enable_file_checkpointing: bool = Field(
        default=False,
        description="Enable file checkpointing for rollback",
    )

    mcp_servers: dict[str, Any] = Field(
        default_factory=dict,
        description="MCP server configurations",
    )
    hooks: dict[str, list[Any]] = Field(
        default_factory=dict,
        description="Hook configurations",
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata",
    )


class HookInput(BaseModel):
    """Input for a hook handler."""

    hook_event_name: str = Field(..., description="Hook event name")
    tool_name: str | None = Field(default=None, description="Tool name if applicable")
    tool_input: dict[str, Any] | None = Field(default=None, description="Tool input")
    tool_use_id: str | None = Field(default=None, description="Tool use ID")
    tool_result: str | None = Field(default=None, description="Tool result")
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context",
    )


class HookOutput(BaseModel):
    """Output from a hook handler."""

    permission_decision: PermissionDecision | None = Field(
        default=None,
        description="Permission decision",
    )
    permission_decision_reason: str | None = Field(
        default=None,
        description="Reason for decision",
    )
    modified_input: dict[str, Any] | None = Field(
        default=None,
        description="Modified tool input",
    )
    modified_result: str | None = Field(
        default=None,
        description="Modified tool result",
    )
    additional_output: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional output",
    )
    continue_: bool = Field(default=True, description="Whether to continue")


class HookMatcher(BaseModel):
    """Matcher for hook routing."""

    matcher: str = Field(..., description="Tool name pattern to match")
    hooks: list[str] = Field(
        default_factory=list,
        description="Hook handler names",
    )
    priority: int = Field(default=0, description="Matcher priority")


class SessionState(BaseModel):
    """State of an agent session."""

    session_id: str = Field(..., description="Session ID")
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Creation time",
    )
    updated_at: datetime = Field(
        default_factory=datetime.now,
        description="Last update time",
    )

    messages: list[MessageUnion] = Field(
        default_factory=list,
        description="Conversation history",
    )
    tool_invocations: list[ToolInvocation] = Field(
        default_factory=list,
        description="Tool invocation history",
    )

    total_cost_usd: float = Field(default=0.0, description="Total cost")
    total_tokens: int = Field(default=0, description="Total tokens used")
    total_duration_ms: float = Field(default=0.0, description="Total duration")

    current_turn: int = Field(default=0, description="Current turn number")
    is_complete: bool = Field(default=False, description="Whether session is complete")
    error: str | None = Field(default=None, description="Error if failed")

    def add_message(self, message: MessageUnion) -> None:
        """Add a message to the history."""
        self.messages.append(message)
        self.updated_at = datetime.now()

    def add_invocation(self, invocation: ToolInvocation) -> None:
        """Add a tool invocation to the history."""
        self.tool_invocations.append(invocation)
        self.updated_at = datetime.now()


class SkillContext(BaseModel):
    """Context for skill execution."""

    skill_id: str = Field(..., description="Skill ID")
    skill_name: str = Field(..., description="Skill name")
    skill_description: str = Field(..., description="Skill description")

    user_query: str = Field(..., description="Original user query")
    session_state: SessionState | None = Field(
        default=None,
        description="Current session state",
    )

    available_tools: list[ToolDefinition] = Field(
        default_factory=list,
        description="Available tools",
    )
    allowed_tools: list[str] = Field(
        default_factory=list,
        description="Allowed tools for this skill",
    )

    environment: dict[str, Any] = Field(
        default_factory=dict,
        description="Environment variables",
    )
    shared_state: dict[str, Any] = Field(
        default_factory=dict,
        description="Shared state across skills",
    )

    trace_id: str = Field(..., description="Trace ID for logging")
    user_id: str | None = Field(default=None, description="User ID")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata",
    )


class SkillResult(BaseModel):
    """Result of skill execution."""

    skill_id: str = Field(..., description="Skill ID")
    success: bool = Field(..., description="Whether execution succeeded")
    content: str = Field(default="", description="Generated content")
    tool_calls: list[ToolInvocation] = Field(
        default_factory=list,
        description="Tool calls made",
    )
    error: str | None = Field(default=None, description="Error message")
    duration_ms: float = Field(..., description="Execution duration")
    tokens_used: int = Field(default=0, description="Tokens used")
    cost_usd: float = Field(default=0.0, description="Cost in USD")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata",
    )
