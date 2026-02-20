"""
Agent state models for LangGraph workflow.

Defines the state structure that flows through the agent graph.
"""

from typing import Annotated, Any
from datetime import datetime

from pydantic import BaseModel, Field
from typing_extensions import TypedDict

from openfinance.models.base import ToolCall, ToolResult
from openfinance.models.intent import IntentType, Entity, IntentClassificationResult


class AgentState(TypedDict, total=False):
    """State that flows through the LangGraph agent workflow.

    This TypedDict defines all possible state fields that can be
    read or modified by nodes in the agent graph.
    """

    query: str
    """Original user query"""

    intent_type: IntentType | None
    """Classified intent type"""

    intent_result: IntentClassificationResult | None
    """Full intent classification result"""

    entities: list[Entity]
    """Extracted entities from query"""

    tool_calls: list[ToolCall]
    """List of tool calls to make or made"""

    tool_results: list[ToolResult]
    """Results from tool executions"""

    content: str
    """Generated response content"""

    error: str | None
    """Error message if any"""

    trace_id: str
    """Trace ID for observability"""

    user_id: str
    """User identifier"""

    role: str | None
    """Role for role-playing mode"""

    iteration_count: int
    """Number of iterations in the loop"""

    max_iterations: int
    """Maximum allowed iterations"""

    should_continue: bool
    """Whether to continue the agent loop"""

    metadata: dict[str, Any]
    """Additional metadata"""


class AgentStateModel(BaseModel):
    """Pydantic model wrapper for AgentState validation."""

    query: str = Field(..., description="Original user query")
    intent_type: IntentType | None = Field(
        default=None,
        description="Classified intent type",
    )
    intent_result: IntentClassificationResult | None = Field(
        default=None,
        description="Full intent classification result",
    )
    entities: list[Entity] = Field(
        default_factory=list,
        description="Extracted entities",
    )
    tool_calls: list[ToolCall] = Field(
        default_factory=list,
        description="Tool calls made",
    )
    tool_results: list[ToolResult] = Field(
        default_factory=list,
        description="Tool execution results",
    )
    content: str = Field(default="", description="Generated response")
    error: str | None = Field(default=None, description="Error message")
    trace_id: str = Field(
        default_factory=lambda: str(datetime.now().timestamp()),
        description="Trace ID",
    )
    user_id: str = Field(default="", description="User identifier")
    role: str | None = Field(default=None, description="Role for role-playing")
    iteration_count: int = Field(default=0, description="Iteration counter")
    max_iterations: int = Field(default=5, description="Max iterations")
    should_continue: bool = Field(default=True, description="Continue flag")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata",
    )

    def to_state(self) -> AgentState:
        """Convert to TypedDict state."""
        return AgentState(
            query=self.query,
            intent_type=self.intent_type,
            intent_result=self.intent_result,
            entities=self.entities,
            tool_calls=self.tool_calls,
            tool_results=self.tool_results,
            content=self.content,
            error=self.error,
            trace_id=self.trace_id,
            user_id=self.user_id,
            role=self.role,
            iteration_count=self.iteration_count,
            max_iterations=self.max_iterations,
            should_continue=self.should_continue,
            metadata=self.metadata,
        )

    @classmethod
    def from_state(cls, state: AgentState) -> "AgentStateModel":
        """Create from TypedDict state."""
        return cls(**state)


class NodeResult(BaseModel):
    """Result from a node execution."""

    success: bool = Field(..., description="Whether execution succeeded")
    next_node: str | None = Field(
        default=None,
        description="Next node to route to",
    )
    state_updates: dict[str, Any] = Field(
        default_factory=dict,
        description="State updates to apply",
    )
    error: str | None = Field(default=None, description="Error message")


class GraphConfig(BaseModel):
    """Configuration for the agent graph."""

    max_iterations: int = Field(default=5, description="Maximum loop iterations")
    timeout_seconds: float = Field(default=30.0, description="Execution timeout")
    enable_streaming: bool = Field(default=False, description="Enable streaming")
    default_llm_model: str = Field(
        default="gpt-4",
        description="Default LLM model",
    )
    fallback_llm_model: str = Field(
        default="gpt-3.5-turbo",
        description="Fallback LLM model",
    )
    enable_caching: bool = Field(default=True, description="Enable response caching")
    cache_ttl_seconds: int = Field(
        default=3600,
        description="Cache TTL in seconds",
    )
