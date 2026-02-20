"""Tests for the agent core system."""

import pytest
from pathlib import Path
import tempfile
import asyncio

from openfinance.agents.core.memory import MemoryStore
from openfinance.agents.core.context import ContextBuilder
from openfinance.agents.bus.events import InboundMessage, OutboundMessage
from openfinance.agents.bus.queue import MessageBus
from openfinance.agents.session.manager import SessionManager, Session


class TestMemoryStore:
    """Tests for MemoryStore."""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def memory(self, temp_workspace):
        """Create a MemoryStore instance."""
        return MemoryStore(temp_workspace)
    
    def test_append_and_read_today(self, memory):
        """Test appending and reading today's notes."""
        memory.append_today("Test note 1")
        memory.append_today("Test note 2")
        
        content = memory.read_today()
        
        assert "Test note 1" in content
        assert "Test note 2" in content
    
    def test_long_term_memory(self, memory):
        """Test long-term memory operations."""
        memory.write_long_term("# Important Notes\n\nThis is important.")
        
        content = memory.read_long_term()
        
        assert "# Important Notes" in content
        assert "This is important." in content
    
    def test_get_recent_memories(self, memory):
        """Test getting recent memories."""
        memory.append_today("Today's note")
        
        recent = memory.get_recent_memories(days=1)
        
        assert "Today's note" in recent
    
    def test_get_memory_context(self, memory):
        """Test getting memory context."""
        memory.write_long_term("Long term memory content")
        memory.append_today("Today's content")
        
        context = memory.get_memory_context()
        
        assert "Long-term Memory" in context
        assert "Today's Notes" in context


class TestContextBuilder:
    """Tests for ContextBuilder."""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def context(self, temp_workspace):
        """Create a ContextBuilder instance."""
        return ContextBuilder(temp_workspace)
    
    def test_build_system_prompt(self, context):
        """Test building system prompt."""
        prompt = context.build_system_prompt()
        
        assert "OpenFinance Agent" in prompt
        assert "workspace" in prompt.lower()
        assert "Skills" in prompt
    
    def test_build_messages(self, context):
        """Test building message list."""
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]
        
        messages = context.build_messages(
            history=history,
            current_message="How are you?",
            channel="test",
            chat_id="user1"
        )
        
        assert len(messages) == 4  # system + 2 history + 1 current
        assert messages[0]["role"] == "system"
        assert messages[-1]["role"] == "user"
        assert messages[-1]["content"] == "How are you?"
    
    def test_add_tool_result(self, context):
        """Test adding tool result to messages."""
        messages = [{"role": "assistant", "content": "Let me check that."}]
        
        updated = context.add_tool_result(
            messages=messages,
            tool_call_id="call_123",
            tool_name="read_file",
            result="File content here"
        )
        
        assert len(updated) == 2
        assert updated[1]["role"] == "tool"
        assert updated[1]["tool_call_id"] == "call_123"
        assert updated[1]["name"] == "read_file"
        assert updated[1]["content"] == "File content here"


class TestMessageBus:
    """Tests for MessageBus."""
    
    @pytest.fixture
    def bus(self):
        """Create a MessageBus instance."""
        return MessageBus()
    
    @pytest.mark.asyncio
    async def test_publish_consume_inbound(self, bus):
        """Test publishing and consuming inbound messages."""
        msg = InboundMessage(
            channel="test",
            sender_id="user1",
            chat_id="chat1",
            content="Hello"
        )
        
        await bus.publish_inbound(msg)
        
        consumed = await bus.consume_inbound()
        
        assert consumed.channel == "test"
        assert consumed.content == "Hello"
    
    @pytest.mark.asyncio
    async def test_publish_consume_outbound(self, bus):
        """Test publishing and consuming outbound messages."""
        msg = OutboundMessage(
            channel="test",
            chat_id="chat1",
            content="Response"
        )
        
        await bus.publish_outbound(msg)
        
        consumed = await bus.consume_outbound()
        
        assert consumed.channel == "test"
        assert consumed.content == "Response"
    
    def test_queue_sizes(self, bus):
        """Test queue size properties."""
        assert bus.inbound_size == 0
        assert bus.outbound_size == 0


class TestSessionManager:
    """Tests for SessionManager."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def manager(self, temp_dir):
        """Create a SessionManager instance."""
        return SessionManager(workspace=temp_dir)
    
    def test_get_or_create(self, manager):
        """Test getting or creating a session."""
        session = manager.get_or_create("test:chat1")
        
        assert session.key == "test:chat1"
        assert len(session.messages) == 0
    
    def test_add_message(self, manager):
        """Test adding messages to session."""
        session = manager.get_or_create("test:chat1")
        session.add_message("user", "Hello")
        session.add_message("assistant", "Hi there!")
        
        assert len(session.messages) == 2
        assert session.messages[0]["role"] == "user"
        assert session.messages[1]["role"] == "assistant"
    
    def test_save_and_load(self, manager):
        """Test saving and loading a session."""
        session = manager.get_or_create("test:chat1")
        session.add_message("user", "Hello")
        session.add_message("assistant", "Hi!")
        
        manager.save(session)
        
        loaded = manager.get_or_create("test:chat1")
        
        assert len(loaded.messages) == 2
        assert loaded.messages[0]["content"] == "Hello"
    
    def test_get_history(self, manager):
        """Test getting message history."""
        session = manager.get_or_create("test:chat1")
        
        for i in range(60):
            session.add_message("user", f"Message {i}")
        
        history = session.get_history(max_messages=50)
        
        assert len(history) == 50
        assert history[0]["content"] == "Message 10"
    
    def test_delete_session(self, manager):
        """Test deleting a session."""
        session = manager.get_or_create("test:chat1")
        session.add_message("user", "Hello")
        manager.save(session)
        
        result = manager.delete("test:chat1")
        
        assert result is True
        
        new_session = manager.get_or_create("test:chat1")
        assert len(new_session.messages) == 0


class TestInboundMessage:
    """Tests for InboundMessage."""
    
    def test_session_key(self):
        """Test session key property."""
        msg = InboundMessage(
            channel="slack",
            sender_id="U123",
            chat_id="C456",
            content="Hello"
        )
        
        assert msg.session_key == "slack:C456"
    
    def test_default_values(self):
        """Test default values."""
        msg = InboundMessage(
            channel="test",
            sender_id="user1",
            chat_id="chat1",
            content="Hello"
        )
        
        assert msg.media == []
        assert msg.metadata == {}


class TestOutboundMessage:
    """Tests for OutboundMessage."""
    
    def test_default_values(self):
        """Test default values."""
        msg = OutboundMessage(
            channel="test",
            chat_id="chat1",
            content="Response"
        )
        
        assert msg.reply_to is None
        assert msg.media == []
        assert msg.metadata == {}
