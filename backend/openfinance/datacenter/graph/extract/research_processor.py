"""
Research Report Processor Module.

Provides processing capabilities for research reports including:
- Entity extraction
- Sentiment analysis
- Content summarization
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


@dataclass
class ExtractedEntity:
    """An extracted entity from research report."""
    
    entity_type: str
    entity_name: str
    entity_code: str | None = None
    confidence: float = 1.0
    mentions: int = 1
    context: str | None = None
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_type": self.entity_type,
            "entity_name": self.entity_name,
            "entity_code": self.entity_code,
            "confidence": self.confidence,
            "mentions": self.mentions,
            "context": self.context,
        }


@dataclass
class ExtractedRelation:
    """An extracted relation between entities."""
    
    source_entity: str
    target_entity: str
    relation_type: str
    confidence: float = 1.0
    evidence: str | None = None
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "source_entity": self.source_entity,
            "target_entity": self.target_entity,
            "relation_type": self.relation_type,
            "confidence": self.confidence,
            "evidence": self.evidence,
        }


@dataclass
class SentimentResult:
    """Sentiment analysis result."""
    
    score: float
    label: str
    confidence: float = 1.0
    aspects: dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "label": self.label,
            "confidence": self.confidence,
            "aspects": self.aspects,
        }


class ResearchReportProcessor:
    """
    Processor for research reports.
    
    Features:
    - Entity extraction (companies, industries, concepts)
    - Relation extraction
    - Sentiment analysis
    - Content summarization
    
    Usage:
        processor = ResearchReportProcessor()
        
        # Extract entities
        entities = processor.extract_entities(report)
        
        # Analyze sentiment
        sentiment = processor.analyze_sentiment(report)
    """
    
    def __init__(self) -> None:
        self._company_patterns = [
            r"([\u4e00-\u9fa5]{2,})(?:股份|集团|公司|科技|电子|医药|银行|证券)",
            r"([\u4e00-\u9fa5]{2,})(?:A股|H股)",
        ]
        
        self._industry_patterns = [
            r"([\u4e00-\u9fa5]{2,})(?:行业|产业|板块)",
            r"([\u4e00-\u9fa5]{2,})(?:产业链|供应链)",
        ]
        
        self._concept_patterns = [
            r"([\u4e00-\u9fa5]{2,})(?:概念|题材)",
        ]
        
        self._positive_words = [
            "增持", "买入", "推荐", "看好", "增长", "上涨", "突破",
            "利好", "优化", "提升", "领先", "优势", "机遇",
        ]
        
        self._negative_words = [
            "减持", "卖出", "风险", "下降", "下跌", "亏损",
            "利空", "压力", "挑战", "下滑", "萎缩", "恶化",
        ]
    
    def extract_entities(
        self,
        report: dict[str, Any],
    ) -> list[ExtractedEntity]:
        """
        Extract entities from research report.
        
        Args:
            report: Research report data
        
        Returns:
            List of extracted entities
        """
        entities: list[ExtractedEntity] = []
        seen_entities: dict[str, ExtractedEntity] = {}
        
        title = report.get("title", "")
        summary = report.get("summary", "")
        content = report.get("content", "")
        
        text = f"{title} {summary} {content}"
        
        for pattern in self._company_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                entity_key = f"company_{match}"
                if entity_key in seen_entities:
                    seen_entities[entity_key].mentions += 1
                else:
                    entity = ExtractedEntity(
                        entity_type="company",
                        entity_name=match,
                        confidence=0.8,
                    )
                    entities.append(entity)
                    seen_entities[entity_key] = entity
        
        for pattern in self._industry_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                entity_key = f"industry_{match}"
                if entity_key in seen_entities:
                    seen_entities[entity_key].mentions += 1
                else:
                    entity = ExtractedEntity(
                        entity_type="industry",
                        entity_name=match,
                        confidence=0.9,
                    )
                    entities.append(entity)
                    seen_entities[entity_key] = entity
        
        for pattern in self._concept_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                entity_key = f"concept_{match}"
                if entity_key in seen_entities:
                    seen_entities[entity_key].mentions += 1
                else:
                    entity = ExtractedEntity(
                        entity_type="concept",
                        entity_name=match,
                        confidence=0.7,
                    )
                    entities.append(entity)
                    seen_entities[entity_key] = entity
        
        for code in report.get("related_codes", []):
            entity_key = f"stock_{code}"
            if entity_key not in seen_entities:
                entity = ExtractedEntity(
                    entity_type="stock",
                    entity_name=report.get("related_names", [""])[0] if report.get("related_names") else code,
                    entity_code=code,
                    confidence=1.0,
                )
                entities.append(entity)
                seen_entities[entity_key] = entity
        
        entities.sort(key=lambda e: e.mentions, reverse=True)
        
        return entities[:20]
    
    def extract_relations(
        self,
        report: dict[str, Any],
        entities: list[ExtractedEntity],
    ) -> list[ExtractedRelation]:
        """
        Extract relations between entities.
        
        Args:
            report: Research report data
            entities: Extracted entities
        
        Returns:
            List of extracted relations
        """
        relations: list[ExtractedRelation] = []
        
        title = report.get("title", "")
        summary = report.get("summary", "")
        content = f"{title} {summary}"
        
        rating = report.get("rating", "")
        related_codes = report.get("related_codes", [])
        
        if related_codes and rating:
            for code in related_codes:
                relations.append(ExtractedRelation(
                    source_entity=f"report_{report.get('report_id', '')}",
                    target_entity=f"stock_{code}",
                    relation_type="recommends",
                    confidence=0.9,
                    evidence=f"Rating: {rating}",
                ))
        
        entity_names = [e.entity_name for e in entities if e.entity_type == "company"]
        industry_names = [e.entity_name for e in entities if e.entity_type == "industry"]
        
        for company in entity_names:
            for industry in industry_names:
                if industry in content:
                    relations.append(ExtractedRelation(
                        source_entity=f"company_{company}",
                        target_entity=f"industry_{industry}",
                        relation_type="belongs_to",
                        confidence=0.7,
                    ))
        
        return relations[:10]
    
    def analyze_sentiment(
        self,
        report: dict[str, Any],
    ) -> SentimentResult:
        """
        Analyze sentiment of research report.
        
        Args:
            report: Research report data
        
        Returns:
            Sentiment analysis result
        """
        title = report.get("title", "")
        summary = report.get("summary", "")
        content = report.get("content", "")
        
        text = f"{title} {summary} {content[:5000]}"
        
        positive_count = 0
        negative_count = 0
        
        for word in self._positive_words:
            positive_count += text.count(word)
        
        for word in self._negative_words:
            negative_count += text.count(word)
        
        total = positive_count + negative_count
        if total == 0:
            score = 0.5
        else:
            score = (positive_count - negative_count) / total
            score = (score + 1) / 2
        
        rating = report.get("rating", "")
        rating_boost = 0
        if rating in ["买入", "增持", "强烈推荐"]:
            rating_boost = 0.2
        elif rating in ["卖出", "减持"]:
            rating_boost = -0.2
        
        final_score = min(1.0, max(0.0, score + rating_boost))
        
        if final_score >= 0.7:
            label = "positive"
        elif final_score <= 0.3:
            label = "negative"
        else:
            label = "neutral"
        
        aspects = {
            "rating": self._analyze_rating_sentiment(rating),
            "outlook": self._analyze_text_sentiment(text, ["前景", "展望", "预期"]),
            "performance": self._analyze_text_sentiment(text, ["业绩", "营收", "利润"]),
        }
        
        return SentimentResult(
            score=final_score,
            label=label,
            confidence=0.8 if total > 5 else 0.5,
            aspects=aspects,
        )
    
    def _analyze_rating_sentiment(self, rating: str) -> float:
        """Analyze sentiment from rating."""
        rating_scores = {
            "强烈推荐": 1.0,
            "买入": 0.9,
            "增持": 0.7,
            "持有": 0.5,
            "中性": 0.5,
            "减持": 0.3,
            "卖出": 0.1,
        }
        return rating_scores.get(rating, 0.5)
    
    def _analyze_text_sentiment(
        self,
        text: str,
        keywords: list[str],
    ) -> float:
        """Analyze sentiment for specific aspects."""
        for keyword in keywords:
            if keyword in text:
                pos = sum(1 for w in self._positive_words if w in text)
                neg = sum(1 for w in self._negative_words if w in text)
                total = pos + neg
                if total > 0:
                    return pos / total
        return 0.5
    
    def summarize(
        self,
        report: dict[str, Any],
        max_length: int = 200,
    ) -> str:
        """
        Generate summary of research report.
        
        Args:
            report: Research report data
            max_length: Maximum summary length
        
        Returns:
            Summary string
        """
        summary = report.get("summary", "")
        
        if summary and len(summary) <= max_length:
            return summary
        
        content = report.get("content", "")
        if not content:
            return summary[:max_length] if summary else ""
        
        sentences = re.split(r"[。！？]", content)
        
        important_sentences = []
        for sentence in sentences:
            if any(word in sentence for word in ["建议", "观点", "认为", "预计", "看好"]):
                important_sentences.append(sentence)
        
        if important_sentences:
            result = "。".join(important_sentences[:3]) + "。"
            return result[:max_length]
        
        return content[:max_length]


class ResearchReportPipeline:
    """
    Complete processing pipeline for research reports.
    
    Usage:
        pipeline = ResearchReportPipeline()
        
        result = await pipeline.process(report)
        print(f"Entities: {len(result['entities'])}")
        print(f"Sentiment: {result['sentiment'].label}")
    """
    
    def __init__(self) -> None:
        self._processor = ResearchReportProcessor()
    
    async def process(
        self,
        report: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Process a research report through the complete pipeline.
        
        Args:
            report: Research report data
        
        Returns:
            Processing result with entities, relations, and sentiment
        """
        entities = self._processor.extract_entities(report)
        relations = self._processor.extract_relations(report, entities)
        sentiment = self._processor.analyze_sentiment(report)
        summary = self._processor.summarize(report)
        
        return {
            "report_id": report.get("report_id"),
            "entities": [e.to_dict() for e in entities],
            "relations": [r.to_dict() for r in relations],
            "sentiment": sentiment.to_dict(),
            "summary": summary,
            "processed_at": datetime.now().isoformat(),
        }
    
    async def process_batch(
        self,
        reports: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Process multiple research reports."""
        results = []
        for report in reports:
            result = await self.process(report)
            results.append(result)
        return results
