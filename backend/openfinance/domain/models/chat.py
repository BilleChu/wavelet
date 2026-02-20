"""
Chat message models for OpenFinance.

Defines message structures for chat interactions.
"""

from datetime import datetime
from enum import Enum
from typing import Annotated, Any

from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    """Role of message sender."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class MessageType(str, Enum):
    """Type of message content."""

    TEXT = "text"
    MARKDOWN = "markdown"
    JSON = "json"
    CHART = "chart"
    TABLE = "table"
    CARD = "card"
    ERROR = "error"
    STREAM = "stream"


class ChatMessage(BaseModel):
    """A single chat message."""

    message_id: str = Field(..., description="Unique message ID")
    role: MessageRole = Field(..., description="Sender role")
    content: str = Field(..., description="Message content")
    content_type: MessageType = Field(
        default=MessageType.TEXT,
        description="Content type",
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Message timestamp",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata",
    )

    def to_openai_format(self) -> dict[str, str]:
        """Convert to OpenAI message format."""
        return {
            "role": self.role.value,
            "content": self.content,
        }


class ChatSession(BaseModel):
    """A chat session containing multiple messages."""

    session_id: str = Field(..., description="Unique session ID")
    user_id: str = Field(..., description="User ID")
    title: str | None = Field(default=None, description="Session title")
    messages: list[ChatMessage] = Field(
        default_factory=list,
        description="List of messages",
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Session creation time",
    )
    updated_at: datetime = Field(
        default_factory=datetime.now,
        description="Last update time",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Session metadata",
    )

    def add_message(self, message: ChatMessage) -> None:
        """Add a message to the session."""
        self.messages.append(message)
        self.updated_at = datetime.now()

    def get_context_window(self, max_messages: int = 10) -> list[ChatMessage]:
        """Get recent messages for context window."""
        return self.messages[-max_messages:]

    def to_openai_messages(self, max_messages: int = 10) -> list[dict[str, str]]:
        """Convert to OpenAI messages format."""
        return [
            msg.to_openai_format()
            for msg in self.get_context_window(max_messages)
        ]


class StreamingChunk(BaseModel):
    """A chunk of streaming response."""

    chunk_id: str = Field(..., description="Chunk ID")
    session_id: str = Field(..., description="Session ID")
    content: str = Field(..., description="Chunk content")
    is_final: bool = Field(default=False, description="Whether this is the final chunk")
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Chunk timestamp",
    )


class ChatRequest(BaseModel):
    """Request to send a chat message."""

    session_id: str | None = Field(
        default=None,
        description="Session ID (create new if None)",
    )
    message: str = Field(..., description="User message")
    role: str | None = Field(default=None, description="Role for role-playing")
    stream: bool = Field(default=False, description="Enable streaming")
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context",
    )


class ChatResponse(BaseModel):
    """Response to a chat request."""

    session_id: str = Field(..., description="Session ID")
    message: ChatMessage = Field(..., description="Assistant message")
    success: bool = Field(..., description="Whether request succeeded")
    error: str | None = Field(default=None, description="Error message")


class ConversationHistory(BaseModel):
    """Conversation history for a user."""

    user_id: str = Field(..., description="User ID")
    sessions: list[ChatSession] = Field(
        default_factory=list,
        description="List of sessions",
    )
    total_sessions: int = Field(default=0, description="Total session count")
    last_active: datetime | None = Field(
        default=None,
        description="Last activity time",
    )
