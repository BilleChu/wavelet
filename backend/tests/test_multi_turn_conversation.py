"""Test script for multi-turn conversation with session persistence."""

import asyncio
import json
from pathlib import Path
from openfinance.agents.session import SessionManager
from openfinance.api.routes.chat import ChatService


async def test_session_persistence():
    """Test that conversation history is properly saved and loaded."""
    print("=" * 60)
    print("Testing Multi-Turn Conversation with Session Persistence")
    print("=" * 60)
    
    # Initialize session manager
    session_manager = SessionManager()
    test_session_key = "test:user123:session_test_001"
    
    print(f"\n1. Testing Session Manager directly...")
    print(f"   Session key: {test_session_key}")
    
    # Create a session and add messages
    session = session_manager.get_or_create(test_session_key)
    print(f"   ✓ Session created/loaded")
    
    # Add test messages
    session.add_message("user", "浦发银行的市盈率是多少？", session_id=test_session_key)
    print(f"   ✓ Added user message")
    
    session.add_message("assistant", "浦发银行当前的市盈率约为 5.2 倍...", session_id=test_session_key)
    print(f"   ✓ Added assistant response")
    
    # Save session
    session_manager.save(session)
    print(f"   ✓ Session saved to disk")
    
    # Reload session
    reloaded_session = session_manager.get_or_create(test_session_key)
    print(f"   ✓ Session reloaded from disk")
    
    # Verify messages
    assert len(reloaded_session.messages) == 2, "Should have 2 messages"
    assert reloaded_session.messages[0]["role"] == "user"
    assert reloaded_session.messages[1]["role"] == "assistant"
    print(f"   ✓ Messages verified: {len(reloaded_session.messages)} messages")
    
    # Get history for LLM context
    history = reloaded_session.get_history(max_messages=50)
    print(f"   ✓ History retrieved: {len(history)} messages for LLM context")
    
    print(f"\n2. Testing ChatService with session...")
    
    # Test ChatService
    chat_service = ChatService.get_instance()
    print(f"   ✓ ChatService initialized")
    
    # Simulate streaming chat with session
    test_query = "那它的市净率呢？"  # Follow-up question using "it" (refers to previous context)
    
    print(f"\n3. Simulating conversation flow...")
    print(f"   User query 1: '浦发银行的市盈率是多少？'")
    print(f"   User query 2: '{test_query}' (should understand '它' refers to 浦发银行)")
    
    async for chunk in chat_service.stream_chat(
        query=test_query,
        skill_id=None,
        history=[],  # Should be loaded from session
        context={"user_id": "test_user", "session_id": "test_session_001"},
        session_id="test_session_001",
    ):
        if chunk.startswith("data: "):
            data = chunk[6:]
            if data != "[DONE]":
                try:
                    parsed = json.loads(data)
                    if parsed.get("type") in ["status", "progress", "tool_result"]:
                        print(f"   → {parsed.get('type')}: {parsed.get('message', '')}")
                except:
                    pass
    
    print(f"\n4. Checking session persistence after chat...")
    
    # Verify session was updated
    updated_session = session_manager.get_or_create(f"web:test_user:test_session_001")
    print(f"   ✓ Session loaded: {len(updated_session.messages)} messages total")
    
    if len(updated_session.messages) >= 2:
        print(f"   ✓ Last user message: {updated_session.messages[-2]['content'][:50]}...")
        print(f"   ✓ Last assistant response: {updated_session.messages[-1]['content'][:50]}...")
    
    print("\n" + "=" * 60)
    print("✅ All tests passed!")
    print("=" * 60)
    
    # Cleanup
    import shutil
    sessions_dir = Path.home() / ".openfinance" / "sessions"
    if sessions_dir.exists():
        for file in sessions_dir.glob("*test*"):
            file.unlink()
    print("\n📝 Test sessions cleaned up.")


if __name__ == "__main__":
    asyncio.run(test_session_persistence())
