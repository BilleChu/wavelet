"""
LLM-based Relation Extractor.

Extracts relations between entities using Large Language Models.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from openfinance.domain.models.enums import RelationType

logger = logging.getLogger(__name__)


@dataclass
class Relation:
    """A relation between two entities."""
    relation_id: str
    source_entity: str
    target_entity: str
    relation_type: RelationType
    confidence: float
    evidence: str = ""
    attributes: dict[str, Any] = field(default_factory=dict)
    extracted_at: datetime = field(default_factory=datetime.now)
    source: str = "unknown"


class RelationExtractionPrompt:
    """Prompts for relation extraction."""
    
    SYSTEM_PROMPT = """You are an expert relation extraction system for financial documents.
Extract all meaningful relations between the given entities from the text.

Focus on these relation types:
- invests_in: Investment relationships
- owns: Ownership relationships
- partners_with: Partnership agreements
- competes_with: Competitive relationships
- supplies: Supply chain relationships
- customer_of: Customer relationships
- subsidiary_of: Subsidiary relationships
- parent_of: Parent company relationships
- ceo_of: CEO/leadership relationships
- director_of: Board membership
- founded: Founding relationships
- acquired: Acquisition relationships
- merged_with: Merger relationships
- operates_in: Geographic/industry operations
- produces: Product relationships
- regulated_by: Regulatory relationships
- analyzed_by: Analyst coverage
- reported_by: News/reporting relationships
- related_to: General associations

Return results in JSON format:
{
  "relations": [
    {
      "source": "source entity name",
      "target": "target entity name",
      "relation_type": "relation type",
      "confidence": 0.0-1.0,
      "evidence": "text evidence"
    }
  ]
}"""

    USER_PROMPT_TEMPLATE = """Extract relations between these entities:
{entities}

From the following text:
{text}

Return only valid JSON with no additional text."""


class LLMRelationExtractor:
    """
    LLM-based relation extractor.
    
    Uses LLM for:
    - Context-aware relation extraction
    - Complex relation types
    - Evidence extraction
    - Confidence scoring
    """
    
    def __init__(self, llm_config: dict[str, Any] | None = None) -> None:
        self.config = llm_config or {}
        self._client = None
    
    def _get_client(self) -> Any:
        """Get LLM client (lazy initialization)."""
        if self._client is None:
            try:
                import openai
                self._client = openai.OpenAI(
                    api_key=self.config.get("api_key"),
                    base_url=self.config.get("api_base"),
                )
            except ImportError:
                logger.warning("OpenAI package not installed, LLM extraction disabled")
                return None
        return self._client
    
    async def extract(
        self,
        text: str,
        entities: list[dict[str, Any]],
    ) -> list[Relation]:
        """
        Extract relations between entities.
        
        Args:
            text: Source text
            entities: List of entities with 'name' and 'type' fields
        
        Returns:
            List of extracted relations
        """
        client = self._get_client()
        if client is None:
            return []
        
        if not entities or len(entities) < 2:
            return []
        
        try:
            entity_list = "\n".join([
                f"- {e.get('name', '')} ({e.get('type', 'unknown')})"
                for e in entities
            ])
            
            user_prompt = RelationExtractionPrompt.USER_PROMPT_TEMPLATE.format(
                entities=entity_list,
                text=text,
            )
            
            response = client.chat.completions.create(
                model=self.config.get("model", "gpt-4"),
                messages=[
                    {"role": "system", "content": RelationExtractionPrompt.SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=self.config.get("temperature", 0.1),
                max_tokens=self.config.get("max_tokens", 2000),
            )
            
            content = response.choices[0].message.content
            if not content:
                return []
            
            return self._parse_llm_response(content)
            
        except Exception as e:
            logger.error(f"LLM relation extraction failed: {e}")
            return []
    
    def _parse_llm_response(self, content: str) -> list[Relation]:
        """Parse LLM response into relations."""
        try:
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end]
                data = json.loads(json_str)
            else:
                data = json.loads(content)
            
            relations = []
            for item in data.get("relations", []):
                try:
                    relation_type = RelationType(
                        item.get("relation_type", "related_to").lower()
                    )
                except ValueError:
                    relation_type = RelationType.RELATED_TO
                
                relation = Relation(
                    relation_id=f"rel_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(relations)}",
                    source_entity=item.get("source", ""),
                    target_entity=item.get("target", ""),
                    relation_type=relation_type,
                    confidence=item.get("confidence", 0.5),
                    evidence=item.get("evidence", ""),
                    source="llm",
                )
                relations.append(relation)
            
            return relations
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return []
    
    async def extract_batch(
        self,
        texts: list[str],
        entities_list: list[list[dict[str, Any]]],
    ) -> list[list[Relation]]:
        """Extract relations from multiple texts."""
        results = []
        for text, entities in zip(texts, entities_list):
            relations = await self.extract(text, entities)
            results.append(relations)
        return results


class RuleBasedRelationExtractor:
    """
    Rule-based relation extractor for common patterns.
    
    Uses regex patterns and heuristics for:
    - Stock ownership
    - Company affiliations
    - Person-company relationships
    """
    
    def __init__(self) -> None:
        self._patterns: list[dict[str, Any]] = []
        self._initialize_patterns()
    
    def _initialize_patterns(self) -> None:
        """Initialize default patterns."""
        import re
        
        self._patterns = [
            {
                "pattern": re.compile(r"([\u4e00-\u9fa5]{2,4})[是担任](.*?)(CEO|总裁|董事长|总经理)"),
                "relation_type": RelationType.CEO_OF,
                "source_group": 1,
                "target_group": 2,
            },
            {
                "pattern": re.compile(r"(.*?)持有(.*?)(\d+\.?\d*%)?股份"),
                "relation_type": RelationType.OWNS,
                "source_group": 1,
                "target_group": 2,
            },
            {
                "pattern": re.compile(r"(.*?)是(.*?)的子公司"),
                "relation_type": RelationType.SUBSIDIARY_OF,
                "source_group": 1,
                "target_group": 2,
            },
            {
                "pattern": re.compile(r"(.*?)收购了(.*?)"),
                "relation_type": RelationType.ACQUIRED,
                "source_group": 1,
                "target_group": 2,
            },
        ]
    
    def extract(
        self,
        text: str,
        entities: list[dict[str, Any]],
    ) -> list[Relation]:
        """Extract relations using rules."""
        relations = []
        entity_names = {e.get("name", "") for e in entities}
        
        for pattern_info in self._patterns:
            pattern = pattern_info["pattern"]
            for match in pattern.finditer(text):
                source = match.group(pattern_info["source_group"]).strip()
                target = match.group(pattern_info["target_group"]).strip()
                
                # Validate entities exist
                if source in entity_names or target in entity_names:
                    relation = Relation(
                        relation_id=f"rule_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(relations)}",
                        source_entity=source,
                        target_entity=target,
                        relation_type=pattern_info["relation_type"],
                        confidence=0.85,
                        evidence=match.group(0),
                        source="rule",
                    )
                    relations.append(relation)
        
        return relations


class HybridRelationExtractor:
    """
    Hybrid relation extractor combining rule-based and LLM approaches.
    """
    
    def __init__(
        self,
        llm_config: dict[str, Any] | None = None,
        use_llm: bool = True,
    ) -> None:
        self.rule_based = RuleBasedRelationExtractor()
        self.llm_based = LLMRelationExtractor(llm_config) if use_llm else None
        self.use_llm = use_llm
    
    async def extract(
        self,
        text: str,
        entities: list[dict[str, Any]],
    ) -> list[Relation]:
        """
        Extract relations using hybrid approach.
        
        Args:
            text: Source text
            entities: List of entities
        
        Returns:
            Merged list of relations
        """
        # Rule-based extraction (fast, high precision)
        relations = self.rule_based.extract(text, entities)
        
        seen = {(r.source_entity, r.target_entity, r.relation_type) for r in relations}
        
        # LLM-based extraction (context-aware, high recall)
        if self.use_llm and self.llm_based:
            llm_relations = await self.llm_based.extract(text, entities)
            
            for relation in llm_relations:
                key = (relation.source_entity, relation.target_entity, relation.relation_type)
                if key not in seen:
                    seen.add(key)
                    relations.append(relation)
        
        return relations
    
    async def extract_batch(
        self,
        texts: list[str],
        entities_list: list[list[dict[str, Any]]],
    ) -> list[list[Relation]]:
        """Extract relations from multiple texts."""
        results = []
        for text, entities in zip(texts, entities_list):
            relations = await self.extract(text, entities)
            results.append(relations)
        return results
