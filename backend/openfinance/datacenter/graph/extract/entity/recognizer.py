"""
Entity Recognizer for Data Processing Center.

Extracts entities from text using rule-based and ML-based approaches.
"""

import logging
import re
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from openfinance.datacenter.graph.extract.entity.types import (
    BaseEntity,
    EntityType,
    create_entity,
)

logger = logging.getLogger(__name__)


class RecognitionConfig(BaseModel):
    """Configuration for entity recognition."""

    min_confidence: float = Field(default=0.5, description="Minimum confidence threshold")
    enable_rule_based: bool = Field(default=True, description="Enable rule-based recognition")
    enable_ml_based: bool = Field(default=False, description="Enable ML-based recognition")
    max_entities: int = Field(default=100, description="Maximum entities to extract")


class RecognitionResult(BaseModel):
    """Result of entity recognition."""

    text: str = Field(..., description="Original text")
    entities: list[BaseEntity] = Field(default_factory=list, description="Extracted entities")
    processing_time_ms: float = Field(..., description="Processing time")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class EntityRecognizer:
    """Entity recognizer for extracting entities from text.

    Supports:
    - Rule-based recognition (regex patterns, dictionaries)
    - ML-based recognition (NER models)
    - Custom entity types
    """

    def __init__(self, config: RecognitionConfig | None = None) -> None:
        self.config = config or RecognitionConfig()
        self._patterns: dict[EntityType, list[re.Pattern]] = {}
        self._dictionaries: dict[EntityType, set[str]] = {}
        self._initialize_defaults()

    def _initialize_defaults(self) -> None:
        """Initialize default patterns and dictionaries."""
        self._patterns[EntityType.STOCK] = [
            re.compile(r"\b([036]\d{5})\b"),
            re.compile(r"\b(688\d{3})\b"),
        ]
        
        self._patterns[EntityType.COMPANY] = [
            re.compile(r"([\u4e00-\u9fa5]{2,10})(股份|集团|公司|银行|证券|保险)"),
        ]
        
        self._patterns[EntityType.PERSON] = [
            re.compile(r"([\u4e00-\u9fa5]{2,4})(说|表示|认为|指出)"),
        ]
        
        self._dictionaries[EntityType.INDUSTRY] = {
            "银行", "保险", "证券", "房地产", "医药", "白酒",
            "新能源", "半导体", "人工智能", "互联网", "汽车",
            "食品饮料", "家电", "建材", "化工", "机械",
        }
        
        self._dictionaries[EntityType.CONCEPT] = {
            "人工智能", "新能源", "碳中和", "数字经济", "元宇宙",
            "区块链", "物联网", "云计算", "大数据", "芯片",
        }

    def register_pattern(
        self,
        entity_type: EntityType,
        pattern: str | re.Pattern,
    ) -> None:
        """Register a pattern for entity recognition."""
        if isinstance(pattern, str):
            pattern = re.compile(pattern)
        
        if entity_type not in self._patterns:
            self._patterns[entity_type] = []
        self._patterns[entity_type].append(pattern)

    def register_dictionary(
        self,
        entity_type: EntityType,
        terms: set[str],
    ) -> None:
        """Register a dictionary for entity recognition."""
        if entity_type not in self._dictionaries:
            self._dictionaries[entity_type] = set()
        self._dictionaries[entity_type].update(terms)

    def recognize(self, text: str) -> RecognitionResult:
        """Recognize entities in text."""
        start_time = datetime.now()
        entities: list[BaseEntity] = []
        seen: set[str] = set()

        if self.config.enable_rule_based:
            entities.extend(self._rule_based_recognition(text, seen))

        entities = [
            e for e in entities
            if e.confidence >= self.config.min_confidence
        ][:self.config.max_entities]

        processing_time = (datetime.now() - start_time).total_seconds() * 1000

        return RecognitionResult(
            text=text,
            entities=entities,
            processing_time_ms=processing_time,
            metadata={
                "total_found": len(entities),
                "config": self.config.model_dump(),
            },
        )

    def _rule_based_recognition(
        self,
        text: str,
        seen: set[str],
    ) -> list[BaseEntity]:
        """Perform rule-based entity recognition."""
        entities: list[BaseEntity] = []

        for entity_type, patterns in self._patterns.items():
            for pattern in patterns:
                for match in pattern.finditer(text):
                    value = match.group(1) if match.groups() else match.group(0)
                    entity_key = f"{entity_type.value}:{value}"
                    
                    if entity_key not in seen:
                        seen.add(entity_key)
                        entity = create_entity(
                            entity_type=entity_type,
                            entity_id=entity_key,
                            name=value,
                            source="rule_based",
                            confidence=0.9,
                        )
                        entities.append(entity)

        for entity_type, dictionary in self._dictionaries.items():
            for term in dictionary:
                if term in text:
                    entity_key = f"{entity_type.value}:{term}"
                    if entity_key not in seen:
                        seen.add(entity_key)
                        entity = create_entity(
                            entity_type=entity_type,
                            entity_id=entity_key,
                            name=term,
                            source="dictionary",
                            confidence=0.85,
                        )
                        entities.append(entity)

        return entities

    async def recognize_batch(
        self,
        texts: list[str],
    ) -> list[RecognitionResult]:
        """Recognize entities in multiple texts."""
        return [self.recognize(text) for text in texts]

    def get_supported_types(self) -> list[EntityType]:
        """Get supported entity types."""
        types = set(self._patterns.keys())
        types.update(self._dictionaries.keys())
        return list(types)
