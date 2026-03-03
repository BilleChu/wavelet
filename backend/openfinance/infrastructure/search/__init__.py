"""
Search infrastructure module.

Provides Elasticsearch client and search services.
"""

from .elasticsearch_client import (
    ElasticsearchClient,
    get_es_client,
    init_es_client,
    is_es_available,
)
from .research_report_index import (
    ResearchReportIndex,
    get_research_report_index,
)

__all__ = [
    "ElasticsearchClient",
    "get_es_client",
    "init_es_client",
    "is_es_available",
    "ResearchReportIndex",
    "get_research_report_index",
]
