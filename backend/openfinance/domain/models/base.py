"""
Base models and protocol definitions for OpenFinance.

This module defines the core data structures that are used throughout the system,
following the protocol specification for agent communication.
"""

from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, EmailStr, Field


PlatformType = Literal["web", "mobile", "desktop"]
UserRole = Literal["user", "assistant", "system"]
IntentTypeLiteral = Literal[
    "stock_search",
    "industry_search",
    "macro_search",
    "strategy_search",
    "stock_analysis",
    "industry_analysis",
    "macro_analysis",
    "role_opinion",
    "stock_rank",
    "unknown",
]


class MetaData(BaseModel):
    """Metadata for request tracing and observability."""

    trace_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique trace ID for observability",
    )
    timestamp: float = Field(
        default_factory=lambda: datetime.now().timestamp(),
        description="Request timestamp in Unix epoch",
    )
    source: str = Field(
        ...,
        description="Request source system, e.g., hr_system, web_client",
    )
    platform: PlatformType = Field(
        default="web",
        description="Client platform type",
    )
    extended_info: dict[str, Any] | None = Field(
        default=None,
        description="Extended metadata for custom use cases",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "trace_id": "550e8400-e29b-41d4-a716-446655440000",
                    "timestamp": 1707830400.0,
                    "source": "web_client",
                    "platform": "web",
                    "extended_info": {"session_id": "abc123"},
                }
            ]
        }
    }


class OrgData(BaseModel):
    """Organization data for user context."""

    org_id: str = Field(..., description="Organization ID")
    org_name: str = Field(..., description="Organization name")
    position: str = Field(..., description="User position in organization")
    permissions: dict[str, Any] = Field(
        default_factory=dict,
        description="User permissions within organization",
    )
    extended_info: dict[str, Any] | None = Field(
        default=None,
        description="Extended organization data",
    )


class UserData(BaseModel):
    """User data for authentication and authorization."""

    ldap_id: str = Field(..., description="LDAP user ID")
    user_name: str = Field(..., description="User display name")
    email: EmailStr | None = Field(default=None, description="User email address")
    employee_id: str | None = Field(default=None, description="Employee ID")
    role: UserRole = Field(default="user", description="User role")
    org: OrgData | None = Field(default=None, description="Organization data")
    extended_info: dict[str, Any] | None = Field(
        default=None,
        description="Extended user data",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "ldap_id": "user001",
                    "user_name": "John Doe",
                    "email": "john.doe@example.com",
                    "employee_id": "EMP001",
                    "role": "user",
                    "org": {
                        "org_id": "org001",
                        "org_name": "Finance Department",
                        "position": "Analyst",
                        "permissions": {"read": True, "write": False},
                    },
                }
            ]
        }
    }


class NLUIntent(BaseModel):
    """NLU intent classification result."""

    intent_id: str = Field(..., description="Intent unique identifier")
    intent_name: str = Field(..., description="Intent name")
    intent_type: str = Field(
        ...,
        description="Intent type: chatflow, agent, or tool",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Classification confidence score",
    )
    description: str = Field(..., description="Intent description")


class NLUSlot(BaseModel):
    """NLU slot (entity) extraction result."""

    value: str | None = Field(default=None, description="Extracted slot value")
    type: str = Field(..., description="Slot type, e.g., stock_code, date")
    standard_value: str | None = Field(
        default=None,
        description="Standardized slot value",
    )
    format: str | None = Field(
        default=None,
        description="Value format specification",
    )
    start_position: int = Field(
        ...,
        ge=0,
        description="Start position in original text",
    )
    end_position: int = Field(
        ...,
        ge=0,
        description="End position in original text",
    )


class NLUData(BaseModel):
    """NLU processing results including intents and slots."""

    intents: list[NLUIntent] = Field(
        default_factory=list,
        description="List of classified intents",
    )
    slots: list[NLUSlot] = Field(
        default_factory=list,
        description="List of extracted slots/entities",
    )
    extended_info: dict[str, Any] | None = Field(
        default=None,
        description="Extended NLU data",
    )


class AgentFlowRequest(BaseModel):
    """Root request object for AgentFlow processing."""

    meta: MetaData = Field(..., description="Request metadata")
    user: UserData = Field(..., description="User data")
    nlu_data: NLUData | None = Field(
        default=None,
        description="NLU processing results",
    )
    query: str = Field(..., description="User query text")
    stream: bool = Field(
        default=False,
        description="Whether to stream the response",
    )
    role: str | None = Field(
        default=None,
        description="Role to use for role-playing mode",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "meta": {
                        "trace_id": "550e8400-e29b-41d4-a716-446655440000",
                        "source": "web_client",
                        "platform": "web",
                    },
                    "user": {
                        "ldap_id": "user001",
                        "user_name": "John Doe",
                        "role": "user",
                    },
                    "query": "浦发银行的市盈率是多少",
                    "stream": False,
                }
            ]
        }
    }


class ToolCall(BaseModel):
    """Record of a tool invocation."""

    tool_name: str = Field(..., description="Name of the tool called")
    arguments: dict[str, Any] = Field(
        default_factory=dict,
        description="Arguments passed to the tool",
    )
    timestamp: float = Field(
        default_factory=lambda: datetime.now().timestamp(),
        description="Call timestamp",
    )


class ToolResult(BaseModel):
    """Result from a tool execution."""

    tool_name: str = Field(..., description="Name of the tool")
    success: bool = Field(..., description="Whether execution succeeded")
    result: Any = Field(..., description="Tool execution result")
    error: str | None = Field(default=None, description="Error message if failed")
    duration_ms: float = Field(..., description="Execution duration in milliseconds")


class AgentFlowResponse(BaseModel):
    """Response from AgentFlow processing."""

    success: bool = Field(..., description="Whether processing succeeded")
    content: str = Field(..., description="Generated response content")
    intent: IntentTypeLiteral | None = Field(
        default=None,
        description="Classified intent type",
    )
    tool_calls: list[ToolCall] = Field(
        default_factory=list,
        description="List of tool calls made",
    )
    tool_results: list[ToolResult] = Field(
        default_factory=list,
        description="List of tool results",
    )
    trace_id: str = Field(..., description="Trace ID for correlation")
    error: str | None = Field(default=None, description="Error message if failed")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "success": True,
                    "content": "浦发银行当前市盈率为5.2倍...",
                    "intent": "stock_search",
                    "tool_calls": [
                        {
                            "tool_name": "stock_valuation",
                            "arguments": {"code": "600000"},
                        }
                    ],
                    "tool_results": [
                        {
                            "tool_name": "stock_valuation",
                            "success": True,
                            "result": {"pe_ratio": 5.2},
                            "duration_ms": 150.5,
                        }
                    ],
                    "trace_id": "550e8400-e29b-41d4-a716-446655440000",
                }
            ]
        }
    }
