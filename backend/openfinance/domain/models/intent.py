"""
Intent classification models for OpenFinance.

Defines intent types and related data structures for the NLU pipeline.
"""

from enum import Enum
from typing import Annotated, Any

from pydantic import BaseModel, Field


class IntentType(str, Enum):
    """Supported intent types for financial queries."""

    STOCK_SEARCH = "stock_search"
    INDUSTRY_SEARCH = "industry_search"
    MACRO_SEARCH = "macro_search"
    STRATEGY_SEARCH = "strategy_search"
    STOCK_ANALYSIS = "stock_analysis"
    INDUSTRY_ANALYSIS = "industry_analysis"
    MACRO_ANALYSIS = "macro_analysis"
    ROLE_OPINION = "role_opinion"
    STOCK_RANK = "stock_rank"
    UNKNOWN = "unknown"

    @classmethod
    def from_string(cls, value: str) -> "IntentType":
        """Convert string to IntentType, returning UNKNOWN if not found."""
        try:
            return cls(value.lower())
        except ValueError:
            return cls.UNKNOWN

    def is_analysis(self) -> bool:
        """Check if this is an analysis-type intent."""
        return self in (
            IntentType.STOCK_ANALYSIS,
            IntentType.INDUSTRY_ANALYSIS,
            IntentType.MACRO_ANALYSIS,
        )

    def is_search(self) -> bool:
        """Check if this is a search-type intent."""
        return self in (
            IntentType.STOCK_SEARCH,
            IntentType.INDUSTRY_SEARCH,
            IntentType.MACRO_SEARCH,
            IntentType.STRATEGY_SEARCH,
        )


class IntentCategory(str, Enum):
    """Category grouping for intents."""

    STOCK = "stock"
    INDUSTRY = "industry"
    MACRO = "macro"
    STRATEGY = "strategy"
    ROLE = "role"
    UNKNOWN = "unknown"


INTENT_CATEGORY_MAP: dict[IntentType, IntentCategory] = {
    IntentType.STOCK_SEARCH: IntentCategory.STOCK,
    IntentType.STOCK_ANALYSIS: IntentCategory.STOCK,
    IntentType.STOCK_RANK: IntentCategory.STOCK,
    IntentType.INDUSTRY_SEARCH: IntentCategory.INDUSTRY,
    IntentType.INDUSTRY_ANALYSIS: IntentCategory.INDUSTRY,
    IntentType.MACRO_SEARCH: IntentCategory.MACRO,
    IntentType.MACRO_ANALYSIS: IntentCategory.MACRO,
    IntentType.STRATEGY_SEARCH: IntentCategory.STRATEGY,
    IntentType.ROLE_OPINION: IntentCategory.ROLE,
    IntentType.UNKNOWN: IntentCategory.UNKNOWN,
}


class EntityType(str, Enum):
    """Entity types that can be extracted from queries."""

    STOCK_CODE = "stock_code"
    STOCK_NAME = "stock_name"
    INDUSTRY_NAME = "industry_name"
    CONCEPT_NAME = "concept_name"
    INDICATOR_NAME = "indicator_name"
    TIME_EXPRESSION = "time_expression"
    PERSON_NAME = "person_name"
    COMPANY_NAME = "company_name"
    AMOUNT = "amount"
    PERCENTAGE = "percentage"


class Entity(BaseModel):
    """Extracted entity from user query."""

    type: EntityType = Field(..., description="Entity type")
    value: str = Field(..., description="Original entity value")
    normalized_value: str | None = Field(
        default=None,
        description="Normalized/standardized value",
    )
    start: int = Field(..., ge=0, description="Start position in query")
    end: int = Field(..., ge=0, description="End position in query")
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Extraction confidence",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional entity metadata",
    )


class IntentClassificationResult(BaseModel):
    """Result of intent classification."""

    intent_type: IntentType = Field(..., description="Classified intent type")
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Classification confidence",
    )
    entities: list[Entity] = Field(
        default_factory=list,
        description="Extracted entities",
    )
    category: IntentCategory = Field(
        ...,
        description="Intent category",
    )
    sub_intents: list["IntentClassificationResult"] = Field(
        default_factory=list,
        description="Sub-intents for complex queries",
    )
    reasoning: str | None = Field(
        default=None,
        description="LLM reasoning for classification",
    )

    def get_entity_by_type(self, entity_type: EntityType) -> Entity | None:
        """Get first entity of specified type."""
        for entity in self.entities:
            if entity.type == entity_type:
                return entity
        return None

    def get_entities_by_type(self, entity_type: EntityType) -> list[Entity]:
        """Get all entities of specified type."""
        return [e for e in self.entities if e.type == entity_type]


class IntentPromptTemplate(BaseModel):
    """Template for intent classification prompts."""

    system_prompt: str = Field(
        ...,
        description="System prompt for LLM",
    )
    user_prompt_template: str = Field(
        ...,
        description="User prompt template with {query} placeholder",
    )
    examples: list[dict[str, str]] = Field(
        default_factory=list,
        description="Few-shot examples for classification",
    )


DEFAULT_INTENT_PROMPT = IntentPromptTemplate(
    system_prompt="""你是一个金融领域的意图分类专家。请分析用户的查询，识别其意图类型和相关实体。

意图类型包括：
- stock_search: 股票搜索，查询股票基本信息
- industry_search: 行业搜索，查询行业概况
- macro_search: 宏观搜索，查询宏观经济数据
- strategy_search: 策略搜索，查询投资策略
- stock_analysis: 股票分析，深度分析股票
- industry_analysis: 行业分析，深度分析行业
- macro_analysis: 宏观分析，深度分析宏观经济
- role_opinion: 角色观点，投资大师视角
- stock_rank: 股票排名，筛选排名

实体类型包括：
- stock_code: 股票代码（如000001, 600000）
- stock_name: 股票名称（如浦发银行, 贵州茅台）
- industry_name: 行业名称（如银行, 白酒）
- indicator_name: 指标名称（如市盈率, 净利润）
- time_expression: 时间表达式（如最近一年, 2023年）

请以JSON格式返回分类结果。""",
    user_prompt_template="请分析以下用户查询的意图：\n\n{query}",
    examples=[
        {
            "query": "浦发银行的市盈率是多少",
            "result": '{"intent_type": "stock_search", "entities": [{"type": "stock_name", "value": "浦发银行"}, {"type": "indicator_name", "value": "市盈率"}]}',
        },
        {
            "query": "分析一下贵州茅台的投资价值",
            "result": '{"intent_type": "stock_analysis", "entities": [{"type": "stock_name", "value": "贵州茅台"}]}',
        },
        {
            "query": "巴菲特怎么看比亚迪",
            "result": '{"intent_type": "role_opinion", "entities": [{"type": "person_name", "value": "巴菲特"}, {"type": "stock_name", "value": "比亚迪"}]}',
        },
    ],
)
