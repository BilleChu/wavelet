"""
Tool definition models for OpenFinance.

Defines the structure for tool registration and invocation.
"""

from typing import Annotated, Any, Callable, Literal
from enum import Enum

from pydantic import BaseModel, Field


class ToolCategory(str, Enum):
    """Categories for tool organization."""

    STOCK = "stock"
    MARKET = "market"
    INDUSTRY = "industry"
    MACRO = "macro"
    NEWS = "news"
    ANALYSIS = "analysis"
    SYSTEM = "system"


class ParameterType(str, Enum):
    """JSON Schema parameter types."""

    STRING = "string"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


class ToolParameter(BaseModel):
    """Definition of a tool parameter."""

    type: ParameterType = Field(..., description="Parameter type")
    description: str = Field(..., description="Parameter description")
    required: bool = Field(default=True, description="Whether parameter is required")
    default: Any | None = Field(default=None, description="Default value")
    enum: list[str] | None = Field(default=None, description="Allowed values")
    min_value: float | None = Field(default=None, description="Minimum value for numbers")
    max_value: float | None = Field(default=None, description="Maximum value for numbers")
    pattern: str | None = Field(default=None, description="Regex pattern for strings")
    items: "ToolParameter | None" = Field(default=None, description="Item schema for arrays")
    properties: dict[str, "ToolParameter"] | None = Field(
        default=None,
        description="Property schemas for objects",
    )


class ToolSchema(BaseModel):
    """JSON Schema for a tool definition."""

    name: str = Field(..., description="Tool name (unique identifier)")
    description: str = Field(..., description="Tool description for LLM")
    category: ToolCategory = Field(..., description="Tool category")
    parameters: dict[str, ToolParameter] = Field(
        default_factory=dict,
        description="Tool parameters",
    )
    returns: str = Field(..., description="Description of return value")
    examples: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Usage examples",
    )
    version: str = Field(default="1.0.0", description="Tool version")
    deprecated: bool = Field(default=False, description="Whether tool is deprecated")
    tags: list[str] = Field(default_factory=list, description="Tags for search")

    def to_openai_tool(self) -> dict[str, Any]:
        """Convert to OpenAI tool format."""
        properties = {}
        required = []

        for name, param in self.parameters.items():
            prop = {"type": param.type.value, "description": param.description}
            if param.enum:
                prop["enum"] = param.enum
            if param.min_value is not None:
                prop["minimum"] = param.min_value
            if param.max_value is not None:
                prop["maximum"] = param.max_value
            if param.pattern:
                prop["pattern"] = param.pattern
            properties[name] = prop
            if param.required:
                required.append(name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }

    def to_langchain_tool(self) -> dict[str, Any]:
        """Convert to LangChain tool format."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.to_openai_tool()["function"]["parameters"],
        }


class ToolDefinition(BaseModel):
    """Complete tool definition including implementation metadata."""

    schema: ToolSchema = Field(..., description="Tool schema")
    module_path: str = Field(..., description="Python module path")
    function_name: str = Field(..., description="Function name in module")
    timeout_seconds: float = Field(default=10.0, description="Execution timeout")
    retry_count: int = Field(default=2, description="Number of retries on failure")
    cache_enabled: bool = Field(default=True, description="Enable result caching")
    cache_ttl_seconds: int = Field(default=300, description="Cache TTL")
    rate_limit: int | None = Field(
        default=None,
        description="Max calls per minute",
    )
    priority: int = Field(default=0, description="Execution priority (higher = more important)")

    @property
    def name(self) -> str:
        """Get tool name."""
        return self.schema.name

    @property
    def category(self) -> ToolCategory:
        """Get tool category."""
        return self.schema.category


class ToolExecutionConfig(BaseModel):
    """Configuration for tool execution."""

    timeout_seconds: float = Field(default=30.0, description="Default timeout")
    max_concurrent: int = Field(default=5, description="Max concurrent executions")
    retry_count: int = Field(default=2, description="Default retry count")
    retry_delay_seconds: float = Field(default=1.0, description="Delay between retries")
    enable_caching: bool = Field(default=True, description="Enable result caching")
    default_cache_ttl: int = Field(default=300, description="Default cache TTL")


class ToolInvocation(BaseModel):
    """Record of a tool invocation."""

    tool_name: str = Field(..., description="Tool name")
    arguments: dict[str, Any] = Field(
        default_factory=dict,
        description="Invocation arguments",
    )
    invocation_id: str = Field(..., description="Unique invocation ID")
    trace_id: str = Field(..., description="Trace ID for correlation")
    timestamp: float = Field(..., description="Invocation timestamp")
    caller: str | None = Field(default=None, description="Caller identifier")


class ToolExecutionResult(BaseModel):
    """Result of tool execution."""

    invocation_id: str = Field(..., description="Corresponding invocation ID")
    tool_name: str = Field(..., description="Tool name")
    success: bool = Field(..., description="Whether execution succeeded")
    result: Any = Field(..., description="Execution result")
    error: str | None = Field(default=None, description="Error message")
    error_type: str | None = Field(default=None, description="Error type/exception class")
    duration_ms: float = Field(..., description="Execution duration in milliseconds")
    from_cache: bool = Field(default=False, description="Whether result came from cache")
    retry_count: int = Field(default=0, description="Number of retries performed")


STOCK_VALUATION_SCHEMA = ToolSchema(
    name="stock_valuation",
    description="获取股票估值指标，包括市盈率、市净率、市销率等",
    category=ToolCategory.STOCK,
    parameters={
        "code": ToolParameter(
            type=ParameterType.STRING,
            description="股票代码，如600000、000001",
            required=True,
            pattern=r"^\d{6}$",
        ),
    },
    returns="包含pe_ratio、pb_ratio、ps_ratio等估值指标的字典",
    examples=[
        {"code": "600000"},
        {"code": "000001"},
    ],
    tags=["股票", "估值", "基本面"],
)

STOCK_FUNDAMENTAL_SCHEMA = ToolSchema(
    name="stock_fundamental",
    description="获取股票基本面数据，包括营收、利润、ROE等财务指标",
    category=ToolCategory.STOCK,
    parameters={
        "code": ToolParameter(
            type=ParameterType.STRING,
            description="股票代码",
            required=True,
            pattern=r"^\d{6}$",
        ),
        "period": ToolParameter(
            type=ParameterType.STRING,
            description="报告期，如2023Q3、2023年报",
            required=False,
            default="latest",
        ),
    },
    returns="包含营收、净利润、ROE等基本面指标的字典",
    examples=[
        {"code": "600000"},
        {"code": "000001", "period": "2023Q3"},
    ],
    tags=["股票", "基本面", "财务"],
)

MARKET_NEWS_SCHEMA = ToolSchema(
    name="market_news",
    description="获取市场新闻资讯",
    category=ToolCategory.NEWS,
    parameters={
        "keywords": ToolParameter(
            type=ParameterType.STRING,
            description="搜索关键词",
            required=False,
        ),
        "limit": ToolParameter(
            type=ParameterType.INTEGER,
            description="返回条数",
            required=False,
            default=10,
            min_value=1,
            max_value=50,
        ),
    },
    returns="新闻列表，每条包含标题、内容、时间、来源",
    examples=[
        {"limit": 10},
        {"keywords": "银行", "limit": 5},
    ],
    tags=["新闻", "资讯", "市场"],
)

INDUSTRY_INFO_SCHEMA = ToolSchema(
    name="industry_info",
    description="获取行业信息，包括行业概况、龙头公司、发展趋势等",
    category=ToolCategory.INDUSTRY,
    parameters={
        "name": ToolParameter(
            type=ParameterType.STRING,
            description="行业名称，如银行、白酒、新能源",
            required=True,
        ),
    },
    returns="行业信息字典，包含概况、龙头公司、趋势分析",
    examples=[
        {"name": "银行"},
        {"name": "白酒"},
    ],
    tags=["行业", "概况", "分析"],
)
