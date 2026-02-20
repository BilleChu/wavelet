"""
LLM-based Entity Recognizer.

Enhances entity recognition using Large Language Models for:
- Context-aware entity extraction
- Complex entity types
- Disambiguation
"""

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from openfinance.datacenter.processor.entity.types import (
    BaseEntity,
    EntityType,
    create_entity,
)

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """Configuration for LLM-based recognition."""
    model: str = "gpt-4"
    temperature: float = 0.1
    max_tokens: int = 2000
    api_base: str | None = None
    api_key: str | None = None


class EntityExtractionPrompt:
    """Prompts for entity extraction."""
    
    SYSTEM_PROMPT = """You are an expert entity extraction system for financial documents.
Extract all relevant entities from the given text. Focus on:
- Companies (上市公司)
- Stocks (股票代码)
- People (人物)
- Industries (行业)
- Concepts (概念)
- Products (产品)
- Locations (地点)
- Dates (日期)
- Financial metrics (财务指标)

Return results in JSON format with the following structure:
{
  "entities": [
    {
      "name": "entity name",
      "type": "company|stock|person|industry|concept|product|location|date|metric",
      "confidence": 0.0-1.0,
      "context": "surrounding text",
      "attributes": {}
    }
  ]
}"""

    USER_PROMPT_TEMPLATE = """Extract entities from the following text:

{text}

Return only valid JSON with no additional text."""


@dataclass
class LLMEntity:
    """Entity extracted by LLM."""
    name: str
    type: str
    confidence: float
    context: str = ""
    attributes: dict[str, Any] = field(default_factory=dict)


class LLMEntityRecognizer:
    """
    LLM-based entity recognizer.
    
    Uses LLM for context-aware entity extraction with:
    - Better understanding of context
    - Complex entity types
    - Entity disambiguation
    - Attribute extraction
    """
    
    TYPE_MAPPING = {
        "company": EntityType.COMPANY,
        "stock": EntityType.STOCK,
        "person": EntityType.PERSON,
        "industry": EntityType.INDUSTRY,
        "concept": EntityType.CONCEPT,
        "product": EntityType.PRODUCT,
        "location": EntityType.LOCATION,
        "date": EntityType.DATE,
        "metric": EntityType.METRIC,
    }
    
    def __init__(self, config: LLMConfig | None = None) -> None:
        self.config = config or LLMConfig()
        self._client = None
    
    def _get_client(self) -> Any:
        """Get LLM client (lazy initialization)."""
        if self._client is None:
            try:
                import openai
                self._client = openai.OpenAI(
                    api_key=self.config.api_key,
                    base_url=self.config.api_base,
                )
            except ImportError:
                logger.warning("OpenAI package not installed, LLM recognition disabled")
                return None
        return self._client
    
    async def recognize(
        self,
        text: str,
        entity_types: list[str] | None = None,
    ) -> list[BaseEntity]:
        """
        Recognize entities using LLM.
        
        Args:
            text: Text to analyze
            entity_types: Optional filter for entity types
        
        Returns:
            List of extracted entities
        """
        client = self._get_client()
        if client is None:
            return []
        
        try:
            system_prompt = EntityExtractionPrompt.SYSTEM_PROMPT
            if entity_types:
                system_prompt += f"\n\nFocus only on these entity types: {', '.join(entity_types)}"
            
            user_prompt = EntityExtractionPrompt.USER_PROMPT_TEMPLATE.format(text=text)
            
            response = client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )
            
            content = response.choices[0].message.content
            if not content:
                return []
            
            return self._parse_llm_response(content)
            
        except Exception as e:
            logger.error(f"LLM recognition failed: {e}")
            return []
    
    def _parse_llm_response(self, content: str) -> list[BaseEntity]:
        """Parse LLM response into entities."""
        try:
            # Try to extract JSON from response
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end]
                data = json.loads(json_str)
            else:
                data = json.loads(content)
            
            entities = []
            for item in data.get("entities", []):
                llm_entity = LLMEntity(
                    name=item.get("name", ""),
                    type=item.get("type", ""),
                    confidence=item.get("confidence", 0.5),
                    context=item.get("context", ""),
                    attributes=item.get("attributes", {}),
                )
                
                entity_type = self.TYPE_MAPPING.get(
                    llm_entity.type.lower(),
                    EntityType.CONCEPT,
                )
                
                entity = create_entity(
                    entity_type=entity_type,
                    entity_id=f"llm:{entity_type.value}:{llm_entity.name}",
                    name=llm_entity.name,
                    source="llm",
                    confidence=llm_entity.confidence,
                    attributes=llm_entity.attributes,
                )
                entities.append(entity)
            
            return entities
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return []
    
    async def recognize_batch(
        self,
        texts: list[str],
        entity_types: list[str] | None = None,
    ) -> list[list[BaseEntity]]:
        """Recognize entities in multiple texts."""
        results = []
        for text in texts:
            entities = await self.recognize(text, entity_types)
            results.append(entities)
        return results


class HybridEntityRecognizer:
    """
    Hybrid entity recognizer combining rule-based and LLM approaches.
    
    Strategy:
    1. Use rule-based for high-confidence, simple patterns
    2. Use LLM for complex, context-dependent entities
    3. Merge and deduplicate results
    """
    
    def __init__(
        self,
        llm_config: LLMConfig | None = None,
        use_llm: bool = True,
    ) -> None:
        from openfinance.datacenter.processor.entity.recognizer import (
            EntityRecognizer,
            RecognitionConfig,
        )
        
        self.rule_based = EntityRecognizer(
            RecognitionConfig(
                enable_rule_based=True,
                enable_ml_based=False,
            )
        )
        
        self.llm_based = LLMEntityRecognizer(llm_config) if use_llm else None
        self.use_llm = use_llm
    
    async def recognize(
        self,
        text: str,
        entity_types: list[str] | None = None,
    ) -> list[BaseEntity]:
        """
        Recognize entities using hybrid approach.
        
        Args:
            text: Text to analyze
            entity_types: Optional filter for entity types
        
        Returns:
            Merged list of entities
        """
        # Rule-based recognition (fast, high precision)
        rule_result = self.rule_based.recognize(text)
        entities = list(rule_result.entities)
        
        seen = {f"{e.entity_type.value}:{e.name}" for e in entities}
        
        # LLM-based recognition (context-aware, high recall)
        if self.use_llm and self.llm_based:
            llm_entities = await self.llm_based.recognize(text, entity_types)
            
            for entity in llm_entities:
                key = f"{entity.entity_type.value}:{entity.name}"
                if key not in seen:
                    seen.add(key)
                    entities.append(entity)
        
        return entities
    
    async def recognize_batch(
        self,
        texts: list[str],
        entity_types: list[str] | None = None,
    ) -> list[list[BaseEntity]]:
        """Recognize entities in multiple texts."""
        results = []
        for text in texts:
            entities = await self.recognize(text, entity_types)
            results.append(entities)
        return results
