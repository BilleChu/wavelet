"""Tests for the agent tools system."""

import pytest
from openfinance.agents.tools.base import Tool
from openfinance.agents.tools.registry import ToolRegistry


class MockTool(Tool):
    """Mock tool for testing."""
    
    @property
    def name(self) -> str:
        return "mock_tool"
    
    @property
    def description(self) -> str:
        return "A mock tool for testing"
    
    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "input": {
                    "type": "string",
                    "description": "Input string"
                },
                "count": {
                    "type": "integer",
                    "description": "Count",
                    "minimum": 1,
                    "maximum": 10
                }
            },
            "required": ["input"]
        }
    
    async def execute(self, input: str, count: int = 1) -> str:
        return f"Processed '{input}' {count} times"


class TestToolBase:
    """Tests for Tool base class."""
    
    @pytest.fixture
    def tool(self):
        """Create a MockTool instance."""
        return MockTool()
    
    def test_name(self, tool):
        """Test tool name."""
        assert tool.name == "mock_tool"
    
    def test_description(self, tool):
        """Test tool description."""
        assert tool.description == "A mock tool for testing"
    
    def test_parameters(self, tool):
        """Test tool parameters schema."""
        params = tool.parameters
        
        assert params["type"] == "object"
        assert "input" in params["properties"]
        assert "count" in params["properties"]
    
    def test_to_schema(self, tool):
        """Test converting to OpenAI schema."""
        schema = tool.to_schema()
        
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "mock_tool"
        assert schema["function"]["description"] == "A mock tool for testing"
    
    def test_validate_params_valid(self, tool):
        """Test validating valid parameters."""
        errors = tool.validate_params({"input": "test", "count": 5})
        
        assert len(errors) == 0
    
    def test_validate_params_missing_required(self, tool):
        """Test validating missing required parameter."""
        errors = tool.validate_params({"count": 5})
        
        assert len(errors) > 0
        assert any("missing required" in e for e in errors)
    
    def test_validate_params_wrong_type(self, tool):
        """Test validating wrong parameter type."""
        errors = tool.validate_params({"input": 123})
        
        assert len(errors) > 0
        assert any("should be string" in e for e in errors)
    
    def test_validate_params_out_of_range(self, tool):
        """Test validating out of range parameter."""
        errors = tool.validate_params({"input": "test", "count": 20})
        
        assert len(errors) > 0
        assert any("must be <=" in e for e in errors)
    
    @pytest.mark.asyncio
    async def test_execute(self, tool):
        """Test tool execution."""
        result = await tool.execute(input="hello", count=3)
        
        assert result == "Processed 'hello' 3 times"


class TestToolRegistry:
    """Tests for ToolRegistry."""
    
    @pytest.fixture
    def registry(self):
        """Create a ToolRegistry instance."""
        return ToolRegistry()
    
    @pytest.fixture
    def mock_tool(self):
        """Create a MockTool instance."""
        return MockTool()
    
    def test_register_tool(self, registry, mock_tool):
        """Test registering a tool."""
        registry.register(mock_tool)
        
        assert registry.has("mock_tool")
        assert registry.get("mock_tool") == mock_tool
    
    def test_register_handler(self, registry):
        """Test registering a handler."""
        def handler(input: str) -> str:
            return f"Handled: {input}"
        
        registry.register_handler("custom_tool", handler)
        
        assert registry.has("custom_tool")
        assert registry.get_handler("custom_tool") == handler
    
    def test_unregister(self, registry, mock_tool):
        """Test unregistering a tool."""
        registry.register(mock_tool)
        registry.unregister("mock_tool")
        
        assert not registry.has("mock_tool")
    
    def test_get_definitions(self, registry, mock_tool):
        """Test getting tool definitions."""
        registry.register(mock_tool)
        
        definitions = registry.get_definitions()
        
        assert len(definitions) == 1
        assert definitions[0]["function"]["name"] == "mock_tool"
    
    def test_tool_names(self, registry, mock_tool):
        """Test getting tool names."""
        registry.register(mock_tool)
        registry.register_handler("handler_tool", lambda x: x)
        
        names = registry.tool_names
        
        assert "mock_tool" in names
        assert "handler_tool" in names
    
    @pytest.mark.asyncio
    async def test_execute_tool(self, registry, mock_tool):
        """Test executing a tool."""
        registry.register(mock_tool)
        
        result = await registry.execute("mock_tool", {"input": "test", "count": 2})
        
        assert "Processed 'test' 2 times" in result
    
    @pytest.mark.asyncio
    async def test_execute_handler(self, registry):
        """Test executing a handler."""
        def handler(name: str) -> str:
            return f"Hello, {name}!"
        
        registry.register_handler("greet", handler)
        
        result = await registry.execute("greet", {"name": "World"})
        
        assert result == "Hello, World!"
    
    @pytest.mark.asyncio
    async def test_execute_nonexistent(self, registry):
        """Test executing a nonexistent tool."""
        result = await registry.execute("nonexistent", {})
        
        assert "not found" in result
    
    @pytest.mark.asyncio
    async def test_execute_with_error(self, registry):
        """Test executing a tool that raises an error."""
        def error_handler():
            raise ValueError("Test error")
        
        registry.register_handler("error_tool", error_handler)
        
        result = await registry.execute("error_tool", {})
        
        assert "Error" in result
    
    def test_len(self, registry, mock_tool):
        """Test registry length."""
        assert len(registry) == 0
        
        registry.register(mock_tool)
        assert len(registry) == 1
    
    def test_contains(self, registry, mock_tool):
        """Test contains check."""
        registry.register(mock_tool)
        
        assert "mock_tool" in registry
        assert "nonexistent" not in registry
