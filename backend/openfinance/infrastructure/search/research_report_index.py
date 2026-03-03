"""
Research report Elasticsearch index configuration.

Defines the index mapping and provides helper functions for research reports.
"""

import logging
from datetime import datetime
from typing import Any, Optional

from .elasticsearch_client import ElasticsearchClient, get_es_client, is_es_available

logger = logging.getLogger(__name__)

RESEARCH_REPORT_INDEX_NAME = "research_reports"

RESEARCH_REPORT_INDEX_MAPPINGS = {
    "properties": {
        "report_id": {
            "type": "keyword",
        },
        "title": {
            "type": "text",
            "analyzer": "ik_max_word",
            "search_analyzer": "ik_smart",
            "fields": {
                "keyword": {
                    "type": "keyword",
                    "ignore_above": 256,
                }
            }
        },
        "summary": {
            "type": "text",
            "analyzer": "ik_max_word",
            "search_analyzer": "ik_smart",
        },
        "content": {
            "type": "text",
            "analyzer": "ik_max_word",
            "search_analyzer": "ik_smart",
        },
        "source": {
            "type": "keyword",
        },
        "source_url": {
            "type": "keyword",
        },
        "related_codes": {
            "type": "keyword",
        },
        "related_names": {
            "type": "keyword",
            "fields": {
                "text": {
                    "type": "text",
                    "analyzer": "ik_max_word",
                }
            }
        },
        "industry": {
            "type": "keyword",
            "fields": {
                "text": {
                    "type": "text",
                    "analyzer": "ik_max_word",
                }
            }
        },
        "institution": {
            "type": "keyword",
            "fields": {
                "text": {
                    "type": "text",
                    "analyzer": "ik_max_word",
                }
            }
        },
        "analyst": {
            "type": "keyword",
            "fields": {
                "text": {
                    "type": "text",
                    "analyzer": "ik_max_word",
                }
            }
        },
        "rating": {
            "type": "keyword",
        },
        "target_price": {
            "type": "float",
        },
        "sentiment_score": {
            "type": "float",
        },
        "sentiment_label": {
            "type": "keyword",
        },
        "extracted_entities": {
            "type": "object",
            "enabled": False,
        },
        "extracted_relations": {
            "type": "object",
            "enabled": False,
        },
        "publish_date": {
            "type": "date",
        },
        "report_date": {
            "type": "date",
        },
        "report_type": {
            "type": "keyword",
        },
        "page_count": {
            "type": "integer",
        },
        "collected_at": {
            "type": "date",
        },
        "updated_at": {
            "type": "date",
        },
    }
}

RESEARCH_REPORT_INDEX_SETTINGS = {
    "number_of_shards": 1,
    "number_of_replicas": 0,
    "analysis": {
        "analyzer": {
            "ik_max_word": {
                "type": "custom",
                "tokenizer": "ik_max_word",
            },
            "ik_smart": {
                "type": "custom",
                "tokenizer": "ik_smart",
            },
        }
    }
}


class ResearchReportIndex:
    """
    Research report Elasticsearch index manager.
    
    Provides methods for indexing, searching, and managing research reports.
    
    Usage:
        index = ResearchReportIndex()
        await index.create_index()
        await index.index_report(report)
        results = await index.search_reports("人工智能", size=10)
    """
    
    def __init__(self) -> None:
        self._client = ElasticsearchClient()
        self._index_name = RESEARCH_REPORT_INDEX_NAME
    
    async def create_index(self) -> bool:
        """
        Create the research report index.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            result = await self._client.create_index(
                index_name=self._index_name,
                mappings=RESEARCH_REPORT_INDEX_MAPPINGS,
                settings=RESEARCH_REPORT_INDEX_SETTINGS,
            )
            
            if result:
                logger.info(f"Created research report index: {self._index_name}")
            return result
            
        except Exception as e:
            logger.warning(f"Failed to create index with IK analyzer, using standard: {e}")
            simple_mappings = {
                "properties": {
                    "report_id": {"type": "keyword"},
                    "title": {"type": "text"},
                    "summary": {"type": "text"},
                    "content": {"type": "text"},
                    "source": {"type": "keyword"},
                    "source_url": {"type": "keyword"},
                    "related_codes": {"type": "keyword"},
                    "related_names": {"type": "keyword"},
                    "industry": {"type": "keyword"},
                    "institution": {"type": "keyword"},
                    "analyst": {"type": "keyword"},
                    "rating": {"type": "keyword"},
                    "target_price": {"type": "float"},
                    "sentiment_score": {"type": "float"},
                    "sentiment_label": {"type": "keyword"},
                    "extracted_entities": {"type": "object", "enabled": False},
                    "extracted_relations": {"type": "object", "enabled": False},
                    "publish_date": {"type": "date"},
                    "report_date": {"type": "date"},
                    "report_type": {"type": "keyword"},
                    "page_count": {"type": "integer"},
                    "collected_at": {"type": "date"},
                    "updated_at": {"type": "date"},
                }
            }
            
            return await self._client.create_index(
                index_name=self._index_name,
                mappings=simple_mappings,
                settings={"number_of_shards": 1, "number_of_replicas": 0},
            )
    
    async def index_report(self, report: dict[str, Any]) -> bool:
        """
        Index a single research report.
        
        Args:
            report: Research report document
        
        Returns:
            True if successful, False otherwise
        """
        doc = self._prepare_document(report)
        return await self._client.index_document(
            index_name=self._index_name,
            document=doc,
            doc_id=doc.get("report_id"),
        )
    
    async def bulk_index_reports(
        self,
        reports: list[dict[str, Any]],
    ) -> tuple[int, int]:
        """
        Bulk index research reports.
        
        Args:
            reports: List of research report documents
        
        Returns:
            Tuple of (success_count, failure_count)
        """
        documents = [self._prepare_document(r) for r in reports]
        return await self._client.bulk_index(
            index_name=self._index_name,
            documents=documents,
            id_field="report_id",
        )
    
    def _prepare_document(self, report: dict[str, Any]) -> dict[str, Any]:
        """Prepare a report document for indexing."""
        doc = dict(report)
        
        if "collected_at" not in doc:
            doc["collected_at"] = datetime.utcnow().isoformat()
        doc["updated_at"] = datetime.utcnow().isoformat()
        
        if doc.get("publish_date") and isinstance(doc["publish_date"], str):
            pass
        elif doc.get("publish_date"):
            doc["publish_date"] = doc["publish_date"].isoformat()
        
        if doc.get("report_date") and isinstance(doc["report_date"], str):
            pass
        elif doc.get("report_date"):
            doc["report_date"] = doc["report_date"].isoformat()
        
        return doc
    
    async def search_reports(
        self,
        query: str,
        fields: list[str] | None = None,
        filters: dict[str, Any] | None = None,
        size: int = 10,
        from_: int = 0,
        sort_by: str = "publish_date",
        sort_order: str = "desc",
    ) -> dict[str, Any]:
        """
        Search research reports.
        
        Args:
            query: Search query string
            fields: Fields to search in (default: title, summary, content)
            filters: Additional filters (e.g., {"rating": "买入"})
            size: Number of results
            from_: Offset for pagination
            sort_by: Field to sort by
            sort_order: Sort order (asc/desc)
        
        Returns:
            Search results with hits and total count
        """
        if fields is None:
            fields = ["title", "summary", "content"]
        
        must_queries = []
        
        if query:
            multi_match = {
                "query": query,
                "fields": fields,
                "type": "best_fields",
                "operator": "or",
                "minimum_should_match": "30%",
            }
            must_queries.append({"multi_match": multi_match})
        
        filter_queries = []
        if filters:
            for field, value in filters.items():
                if isinstance(value, list):
                    filter_queries.append({"terms": {field: value}})
                else:
                    filter_queries.append({"term": {field: value}})
        
        es_query = {
            "bool": {
                "must": must_queries if must_queries else [{"match_all": {}}],
                "filter": filter_queries,
            }
        }
        
        sort = [{sort_by: {"order": sort_order}}]
        
        highlight = {
            "fields": {
                "title": {},
                "summary": {},
                "content": {"fragment_size": 150, "number_of_fragments": 3},
            }
        }
        
        response = await self._client.search(
            index_name=self._index_name,
            query=es_query,
            size=size,
            from_=from_,
            sort=sort,
            highlight=highlight,
        )
        
        return self._format_search_response(response)
    
    async def search_by_code(
        self,
        code: str,
        size: int = 10,
        from_: int = 0,
    ) -> dict[str, Any]:
        """
        Search reports by stock code.
        
        Args:
            code: Stock code
            size: Number of results
            from_: Offset for pagination
        
        Returns:
            Search results
        """
        query = {
            "bool": {
                "filter": [
                    {"term": {"related_codes": code}}
                ]
            }
        }
        
        sort = [{"publish_date": {"order": "desc"}}]
        
        response = await self._client.search(
            index_name=self._index_name,
            query=query,
            size=size,
            from_=from_,
            sort=sort,
        )
        
        return self._format_search_response(response)
    
    async def search_by_institution(
        self,
        institution: str,
        size: int = 10,
        from_: int = 0,
    ) -> dict[str, Any]:
        """
        Search reports by institution.
        
        Args:
            institution: Institution name
            size: Number of results
            from_: Offset for pagination
        
        Returns:
            Search results
        """
        query = {
            "bool": {
                "filter": [
                    {"term": {"institution": institution}}
                ]
            }
        }
        
        sort = [{"publish_date": {"order": "desc"}}]
        
        response = await self._client.search(
            index_name=self._index_name,
            query=query,
            size=size,
            from_=from_,
            sort=sort,
        )
        
        return self._format_search_response(response)
    
    async def get_report(self, report_id: str) -> dict[str, Any] | None:
        """
        Get a report by ID.
        
        Args:
            report_id: Report ID
        
        Returns:
            Report document or None
        """
        return await self._client.get_document(
            index_name=self._index_name,
            doc_id=report_id,
        )
    
    async def delete_report(self, report_id: str) -> bool:
        """
        Delete a report by ID.
        
        Args:
            report_id: Report ID
        
        Returns:
            True if successful, False otherwise
        """
        return await self._client.delete_document(
            index_name=self._index_name,
            doc_id=report_id,
        )
    
    async def count_reports(
        self,
        filters: dict[str, Any] | None = None,
    ) -> int:
        """
        Count reports matching filters.
        
        Args:
            filters: Optional filters
        
        Returns:
            Number of matching reports
        """
        if not filters:
            return await self._client.count(index_name=self._index_name)
        
        filter_queries = []
        for field, value in filters.items():
            if isinstance(value, list):
                filter_queries.append({"terms": {field: value}})
            else:
                filter_queries.append({"term": {field: value}})
        
        query = {"bool": {"filter": filter_queries}}
        return await self._client.count(index_name=self._index_name, query=query)
    
    async def get_recent_reports(
        self,
        days: int = 7,
        size: int = 100,
    ) -> dict[str, Any]:
        """
        Get recent reports within specified days.
        
        Args:
            days: Number of days to look back
            size: Maximum number of results
        
        Returns:
            Search results
        """
        from datetime import datetime, timedelta
        
        start_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
        
        query = {
            "bool": {
                "filter": [
                    {"range": {"publish_date": {"gte": start_date}}}
                ]
            }
        }
        
        sort = [{"publish_date": {"order": "desc"}}]
        
        response = await self._client.search(
            index_name=self._index_name,
            query=query,
            size=size,
            sort=sort,
        )
        
        return self._format_search_response(response)
    
    def _format_search_response(self, response: dict[str, Any]) -> dict[str, Any]:
        """Format Elasticsearch response."""
        hits = []
        for hit in response.get("hits", {}).get("hits", []):
            doc = hit.get("_source", {})
            doc["_id"] = hit.get("_id")
            doc["_score"] = hit.get("_score")
            if "highlight" in hit:
                doc["_highlight"] = hit["highlight"]
            hits.append(doc)
        
        total = response.get("hits", {}).get("total", {}).get("value", 0)
        
        return {
            "total": total,
            "hits": hits,
        }


_research_report_index: Optional[ResearchReportIndex] = None


def get_research_report_index() -> ResearchReportIndex:
    """
    Get the research report index instance.
    
    Returns:
        ResearchReportIndex instance
    """
    global _research_report_index
    
    if _research_report_index is None:
        _research_report_index = ResearchReportIndex()
    
    return _research_report_index
