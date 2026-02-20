"""
Skill definition models for OpenFinance.

Defines the structure for skill management and Agentic Loop support.
"""

from datetime import datetime
from enum import Enum
from typing import Annotated, Any

from pydantic import BaseModel, Field


class SkillState(str, Enum):
    """Skill lifecycle states."""

    IDLE = "idle"
    LOADING = "loading"
    READY = "ready"
    EXECUTING = "executing"
    PAUSED = "paused"
    ERROR = "error"
    TERMINATED = "terminated"


class SkillPriority(str, Enum):
    """Skill priority levels."""

    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    BACKGROUND = "background"


class SkillType(str, Enum):
    """Types of skills."""

    ANALYSIS = "analysis"
    SEARCH = "search"
    GENERATION = "generation"
    TRANSFORMATION = "transformation"
    ORCHESTRATION = "orchestration"
    COMMUNICATION = "communication"


class SkillCapability(BaseModel):
    """Capability descriptor for a skill."""

    name: str = Field(..., description="Capability name")
    description: str = Field(..., description="Capability description")
    input_types: list[str] = Field(
        default_factory=list,
        description="Accepted input types",
    )
    output_types: list[str] = Field(
        default_factory=list,
        description="Produced output types",
    )
    prerequisites: list[str] = Field(
        default_factory=list,
        description="Required prerequisite capabilities",
    )


class SkillMetadata(BaseModel):
    """Metadata for skill registration and discovery."""

    skill_id: str = Field(..., description="Unique skill identifier")
    name: str = Field(..., description="Skill display name")
    version: str = Field(default="1.0.0", description="Skill version")
    description: str = Field(..., description="Skill description")
    author: str | None = Field(default=None, description="Skill author")
    tags: list[str] = Field(default_factory=list, description="Search tags")
    category: str = Field(..., description="Skill category")
    capabilities: list[SkillCapability] = Field(
        default_factory=list,
        description="Skill capabilities",
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description="Required skill dependencies",
    )
    conflicts: list[str] = Field(
        default_factory=list,
        description="Conflicting skills",
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Creation timestamp",
    )
    updated_at: datetime = Field(
        default_factory=datetime.now,
        description="Last update timestamp",
    )


class SkillConfig(BaseModel):
    """Configuration for skill execution."""

    timeout_seconds: float = Field(default=60.0, description="Execution timeout")
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    retry_delay_seconds: float = Field(default=1.0, description="Base retry delay")
    retry_backoff_factor: float = Field(default=2.0, description="Exponential backoff factor")
    enable_caching: bool = Field(default=True, description="Enable result caching")
    cache_ttl_seconds: int = Field(default=300, description="Cache TTL")
    max_concurrent_executions: int = Field(
        default=5,
        description="Max concurrent executions",
    )
    priority: SkillPriority = Field(
        default=SkillPriority.NORMAL,
        description="Default priority",
    )
    auto_recovery: bool = Field(default=True, description="Enable auto recovery")
    health_check_interval_seconds: int = Field(
        default=30,
        description="Health check interval",
    )


class SkillExecutionContext(BaseModel):
    """Context for skill execution."""

    execution_id: str = Field(..., description="Unique execution ID")
    trace_id: str = Field(..., description="Trace ID for correlation")
    user_id: str = Field(..., description="User ID")
    session_id: str | None = Field(default=None, description="Session ID")
    parent_execution_id: str | None = Field(
        default=None,
        description="Parent execution ID for nested calls",
    )
    environment: dict[str, Any] = Field(
        default_factory=dict,
        description="Execution environment variables",
    )
    shared_state: dict[str, Any] = Field(
        default_factory=dict,
        description="Shared state across skills",
    )
    started_at: datetime = Field(
        default_factory=datetime.now,
        description="Execution start time",
    )
    deadline: datetime | None = Field(
        default=None,
        description="Execution deadline",
    )


class SkillExecutionRequest(BaseModel):
    """Request to execute a skill."""

    skill_id: str = Field(..., description="Skill to execute")
    input_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Input data for skill",
    )
    context: SkillExecutionContext = Field(..., description="Execution context")
    config_overrides: SkillConfig | None = Field(
        default=None,
        description="Config overrides",
    )
    callback_url: str | None = Field(
        default=None,
        description="Callback URL for async completion",
    )


class SkillExecutionResult(BaseModel):
    """Result of skill execution."""

    execution_id: str = Field(..., description="Execution ID")
    skill_id: str = Field(..., description="Skill ID")
    success: bool = Field(..., description="Whether execution succeeded")
    output_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Output data from skill",
    )
    error: str | None = Field(default=None, description="Error message")
    error_code: str | None = Field(default=None, description="Error code")
    retry_count: int = Field(default=0, description="Number of retries")
    duration_ms: float = Field(..., description="Execution duration")
    from_cache: bool = Field(default=False, description="Whether from cache")
    metrics: dict[str, Any] = Field(
        default_factory=dict,
        description="Execution metrics",
    )
    completed_at: datetime = Field(
        default_factory=datetime.now,
        description="Completion timestamp",
    )


class PriorityRule(BaseModel):
    """Rule for skill priority calculation."""

    name: str = Field(..., description="Rule name")
    condition: str = Field(..., description="Condition expression")
    priority_adjustment: int = Field(
        ...,
        description="Priority adjustment value",
    )
    weight: float = Field(default=1.0, description="Rule weight")
    enabled: bool = Field(default=True, description="Whether rule is enabled")


class PriorityContext(BaseModel):
    """Context for priority calculation."""

    intent_type: str | None = Field(default=None, description="Current intent")
    user_preferences: dict[str, Any] = Field(
        default_factory=dict,
        description="User preferences",
    )
    historical_usage: dict[str, int] = Field(
        default_factory=dict,
        description="Historical skill usage counts",
    )
    current_load: dict[str, float] = Field(
        default_factory=dict,
        description="Current system load metrics",
    )
    time_context: dict[str, Any] = Field(
        default_factory=dict,
        description="Time-based context",
    )


class ValidationResult(BaseModel):
    """Result of skill output validation."""

    valid: bool = Field(..., description="Whether validation passed")
    errors: list[str] = Field(
        default_factory=list,
        description="Validation errors",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Validation warnings",
    )
    normalized_output: dict[str, Any] | None = Field(
        default=None,
        description="Normalized output if valid",
    )


class FeedbackRecord(BaseModel):
    """Feedback record for skill learning."""

    execution_id: str = Field(..., description="Related execution ID")
    skill_id: str = Field(..., description="Skill ID")
    feedback_type: str = Field(..., description="Type of feedback")
    rating: int | None = Field(
        default=None,
        ge=1,
        le=5,
        description="User rating 1-5",
    )
    comment: str | None = Field(default=None, description="Feedback comment")
    outcome: str = Field(..., description="Observed outcome")
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Feedback timestamp",
    )


class AgenticLoopState(BaseModel):
    """State for Agentic Loop execution."""

    loop_id: str = Field(..., description="Loop instance ID")
    current_iteration: int = Field(default=0, description="Current iteration")
    max_iterations: int = Field(default=10, description="Maximum iterations")
    goal: str = Field(..., description="Goal to achieve")
    sub_goals: list[str] = Field(
        default_factory=list,
        description="Decomposed sub-goals",
    )
    completed_goals: list[str] = Field(
        default_factory=list,
        description="Completed goals",
    )
    active_skills: list[str] = Field(
        default_factory=list,
        description="Currently active skills",
    )
    skill_history: list[SkillExecutionResult] = Field(
        default_factory=list,
        description="Skill execution history",
    )
    accumulated_context: dict[str, Any] = Field(
        default_factory=dict,
        description="Accumulated context",
    )
    should_continue: bool = Field(default=True, description="Continue flag")
    termination_reason: str | None = Field(
        default=None,
        description="Reason for termination",
    )
    started_at: datetime = Field(
        default_factory=datetime.now,
        description="Loop start time",
    )


class SkillPlan(BaseModel):
    """Plan for skill orchestration."""

    plan_id: str = Field(..., description="Plan ID")
    goal: str = Field(..., description="Goal to achieve")
    steps: list["PlannedStep"] = Field(
        default_factory=list,
        description="Planned execution steps",
    )
    dependencies: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Step dependencies",
    )
    estimated_duration_seconds: float | None = Field(
        default=None,
        description="Estimated duration",
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Plan creation time",
    )


class PlannedStep(BaseModel):
    """A planned step in skill orchestration."""

    step_id: str = Field(..., description="Step ID")
    skill_id: str = Field(..., description="Skill to execute")
    input_mapping: dict[str, str] = Field(
        default_factory=dict,
        description="Input parameter mapping",
    )
    output_mapping: dict[str, str] = Field(
        default_factory=dict,
        description="Output parameter mapping",
    )
    condition: str | None = Field(
        default=None,
        description="Execution condition",
    )
    fallback_skill_id: str | None = Field(
        default=None,
        description="Fallback skill if main fails",
    )
    priority: SkillPriority = Field(
        default=SkillPriority.NORMAL,
        description="Step priority",
    )
