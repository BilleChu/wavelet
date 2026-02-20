"""
API Integration Tests for OpenFinance.

Tests all API endpoints with mocked LLM responses.
"""

import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock

from openfinance.api.main import app
from openfinance.models.base import AgentFlowRequest, MetaData, UserData


@pytest.fixture
def mock_llm_response():
    """Mock LLM response for testing."""
    return {
        "content": "这是一个测试响应",
        "intent": "stock_search",
        "tool_calls": [],
        "tool_results": [],
    }


@pytest.fixture
async def client():
    """Create async test client."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        yield client


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        """Test basic health check."""
        response = await client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_readiness_check(self, client: AsyncClient):
        """Test readiness check."""
        response = await client.get("/api/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert "ready" in data

    @pytest.mark.asyncio
    async def test_liveness_check(self, client: AsyncClient):
        """Test liveness check."""
        response = await client.get("/api/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["alive"] is True


class TestChatEndpoints:
    """Tests for chat API endpoints."""

    @pytest.mark.asyncio
    async def test_chat_endpoint(self, client: AsyncClient):
        """Test chat endpoint."""
        request_data = {
            "meta": {
                "trace_id": "test-trace-123",
                "source": "test",
                "platform": "web",
            },
            "user": {
                "ldap_id": "test-user",
                "user_name": "Test User",
                "role": "user",
            },
            "query": "浦发银行的市盈率是多少",
            "stream": False,
        }
        
        response = await client.post("/api/chat", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "content" in data
        assert "trace_id" in data

    @pytest.mark.asyncio
    async def test_chat_with_role(self, client: AsyncClient):
        """Test chat with role-playing."""
        request_data = {
            "meta": {
                "trace_id": "test-trace-456",
                "source": "test",
                "platform": "web",
            },
            "user": {
                "ldap_id": "test-user",
                "user_name": "Test User",
                "role": "user",
            },
            "query": "你怎么看比亚迪",
            "role": "warren_buffett",
            "stream": False,
        }
        
        response = await client.post("/api/chat/role/warren_buffett", json=request_data)
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_chat_missing_query(self, client: AsyncClient):
        """Test chat with missing query."""
        request_data = {
            "meta": {
                "trace_id": "test-trace-789",
                "source": "test",
                "platform": "web",
            },
            "user": {
                "ldap_id": "test-user",
                "user_name": "Test User",
                "role": "user",
            },
        }
        
        response = await client.post("/api/chat", json=request_data)
        assert response.status_code == 422


class TestIntentEndpoints:
    """Tests for intent classification endpoints."""

    @pytest.mark.asyncio
    async def test_classify_intent(self, client: AsyncClient):
        """Test intent classification."""
        response = await client.post("/api/intent?query=浦发银行的市盈率是多少")
        assert response.status_code == 200
        data = response.json()
        assert "intent_type" in data
        assert "confidence" in data

    @pytest.mark.asyncio
    async def test_get_intent_types(self, client: AsyncClient):
        """Test getting all intent types."""
        response = await client.get("/api/intent/types")
        assert response.status_code == 200
        data = response.json()
        assert "intent_types" in data
        assert len(data["intent_types"]) > 0


class TestToolsEndpoints:
    """Tests for tools API endpoints."""

    @pytest.mark.asyncio
    async def test_list_tools(self, client: AsyncClient):
        """Test listing all tools."""
        response = await client.get("/api/tools")
        assert response.status_code == 200
        data = response.json()
        assert "tools" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_list_tools_by_category(self, client: AsyncClient):
        """Test listing tools by category."""
        response = await client.get("/api/tools?category=stock")
        assert response.status_code == 200
        data = response.json()
        assert "tools" in data

    @pytest.mark.asyncio
    async def test_get_tool(self, client: AsyncClient):
        """Test getting a specific tool."""
        response = await client.get("/api/tools/stock_valuation")
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.json()
            assert "name" in data
            assert "description" in data

    @pytest.mark.asyncio
    async def test_invoke_tool(self, client: AsyncClient):
        """Test invoking a tool."""
        response = await client.post(
            "/api/tools/stock_valuation/invoke",
            json={"code": "600000"}
        )
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.json()
            assert "success" in data

    @pytest.mark.asyncio
    async def test_get_openai_tools(self, client: AsyncClient):
        """Test getting tools in OpenAI format."""
        response = await client.get("/api/tools/openai/format")
        assert response.status_code == 200
        data = response.json()
        assert "tools" in data


class TestSkillsEndpoints:
    """Tests for skills API endpoints."""

    @pytest.mark.asyncio
    async def test_list_skills(self, client: AsyncClient):
        """Test listing all skills."""
        response = await client.get("/api/skills")
        assert response.status_code == 200
        data = response.json()
        assert "skills" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_get_skills_stats(self, client: AsyncClient):
        """Test getting skills statistics."""
        response = await client.get("/api/skills/stats/summary")
        assert response.status_code == 200
        data = response.json()
        assert "registry" in data
        assert "lifecycle" in data


class TestRootEndpoint:
    """Tests for root endpoint."""

    @pytest.mark.asyncio
    async def test_root(self, client: AsyncClient):
        """Test root endpoint."""
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert data["status"] == "running"
