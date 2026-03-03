"""
Elasticsearch client configuration and management.

Provides a singleton Elasticsearch client for the application.
"""

import logging
import os
from typing import Any, Optional

from elasticsearch import AsyncElasticsearch
from elasticsearch.exceptions import ConnectionError as ESConnectionError

logger = logging.getLogger(__name__)

ES_HOST = os.getenv("ES_HOST", "localhost")
ES_PORT = os.getenv("ES_PORT", "9200")
ES_URL = os.getenv("ES_URL", f"http://{ES_HOST}:{ES_PORT}")

_es_client: Optional[AsyncElasticsearch] = None
_es_available = False


async def init_es_client() -> Optional[AsyncElasticsearch]:
    """
    Initialize Elasticsearch client.
    
    Returns:
        AsyncElasticsearch client or None if connection fails
    """
    global _es_client, _es_available
    
    if _es_client is not None:
        return _es_client
    
    try:
        _es_client = AsyncElasticsearch(
            [ES_URL],
            request_timeout=30,
            max_retries=3,
            retry_on_timeout=True,
        )
        
        await _es_client.ping()
        _es_available = True
        logger.info(f"Elasticsearch client initialized: {ES_URL}")
        return _es_client
        
    except ESConnectionError as e:
        logger.warning(f"Elasticsearch connection failed: {e}")
        _es_available = False
        return None
    except Exception as e:
        logger.warning(f"Elasticsearch initialization error: {e}")
        _es_available = False
        return None


async def close_es_client() -> None:
    """Close Elasticsearch client connection."""
    global _es_client, _es_available
    
    if _es_client is not None:
        try:
            await _es_client.close()
            logger.info("Elasticsearch client closed")
        except Exception as e:
            logger.warning(f"Error closing Elasticsearch client: {e}")
        finally:
            _es_client = None
            _es_available = False


def get_es_client() -> Optional[AsyncElasticsearch]:
    """
    Get the Elasticsearch client instance.
    
    Returns:
        AsyncElasticsearch client or None if not initialized
    """
    return _es_client


def is_es_available() -> bool:
    """
    Check if Elasticsearch is available.
    
    Returns:
        True if Elasticsearch is available, False otherwise
    """
    return _es_available


class ElasticsearchClient:
    """
    Elasticsearch client wrapper with common operations.
    
    Usage:
        client = ElasticsearchClient()
        await client.create_index("my_index", mappings={...})
        await client.index_document("my_index", {"title": "test"})
        results = await client.search("my_index", {"query": {...}})
    """
    
    def __init__(self) -> None:
        self._client = _es_client
    
    @property
    def client(self) -> Optional[AsyncElasticsearch]:
        """Get the underlying Elasticsearch client."""
        return self._client
    
    async def ensure_client(self) -> AsyncElasticsearch:
        """Ensure client is available and return it."""
        if self._client is None:
            self._client = await init_es_client()
        if self._client is None:
            raise RuntimeError("Elasticsearch client not available")
        return self._client
    
    async def create_index(
        self,
        index_name: str,
        mappings: dict[str, Any],
        settings: dict[str, Any] | None = None,
    ) -> bool:
        """
        Create an index with mappings.
        
        Args:
            index_name: Name of the index
            mappings: Index mappings
            settings: Index settings
        
        Returns:
            True if successful, False otherwise
        """
        client = await self.ensure_client()
        
        try:
            if await client.indices.exists(index=index_name):
                logger.debug(f"Index {index_name} already exists")
                return True
            
            body: dict[str, Any] = {"mappings": mappings}
            if settings:
                body["settings"] = settings
            
            await client.indices.create(index=index_name, body=body)
            logger.info(f"Created index: {index_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create index {index_name}: {e}")
            return False
    
    async def delete_index(self, index_name: str) -> bool:
        """
        Delete an index.
        
        Args:
            index_name: Name of the index
        
        Returns:
            True if successful, False otherwise
        """
        client = await self.ensure_client()
        
        try:
            if await client.indices.exists(index=index_name):
                await client.indices.delete(index=index_name)
                logger.info(f"Deleted index: {index_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete index {index_name}: {e}")
            return False
    
    async def index_document(
        self,
        index_name: str,
        document: dict[str, Any],
        doc_id: str | None = None,
    ) -> bool:
        """
        Index a document.
        
        Args:
            index_name: Name of the index
            document: Document to index
            doc_id: Optional document ID
        
        Returns:
            True if successful, False otherwise
        """
        client = await self.ensure_client()
        
        try:
            await client.index(
                index=index_name,
                document=document,
                id=doc_id,
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to index document: {e}")
            return False
    
    async def bulk_index(
        self,
        index_name: str,
        documents: list[dict[str, Any]],
        id_field: str = "id",
    ) -> tuple[int, int]:
        """
        Bulk index documents.
        
        Args:
            index_name: Name of the index
            documents: List of documents to index
            id_field: Field to use as document ID
        
        Returns:
            Tuple of (success_count, failure_count)
        """
        if not documents:
            return (0, 0)
        
        client = await self.ensure_client()
        
        actions = []
        for doc in documents:
            doc_id = doc.get(id_field) or doc.get("report_id")
            action = {
                "_index": index_name,
                "_source": doc,
            }
            if doc_id:
                action["_id"] = str(doc_id)
            actions.append(action)
        
        try:
            from elasticsearch.helpers import async_bulk
            
            success, failed = await async_bulk(
                client,
                actions,
                raise_on_error=False,
            )
            
            if failed:
                logger.warning(f"Bulk index completed with {len(failed)} failures")
            
            return (success, len(failed))
            
        except Exception as e:
            logger.error(f"Bulk index failed: {e}")
            return (0, len(documents))
    
    async def search(
        self,
        index_name: str,
        query: dict[str, Any],
        size: int = 10,
        from_: int = 0,
        sort: list[dict[str, Any]] | None = None,
        highlight: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Search documents.
        
        Args:
            index_name: Name of the index
            query: Elasticsearch query
            size: Number of results
            from_: Offset for pagination
            sort: Sort criteria
            highlight: Highlight configuration
        
        Returns:
            Search results
        """
        client = await self.ensure_client()
        
        try:
            body: dict[str, Any] = {
                "query": query,
                "size": size,
                "from": from_,
            }
            
            if sort:
                body["sort"] = sort
            
            if highlight:
                body["highlight"] = highlight
            
            response = await client.search(index=index_name, body=body)
            return response
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return {"hits": {"hits": [], "total": {"value": 0}}}
    
    async def get_document(
        self,
        index_name: str,
        doc_id: str,
    ) -> dict[str, Any] | None:
        """
        Get a document by ID.
        
        Args:
            index_name: Name of the index
            doc_id: Document ID
        
        Returns:
            Document or None if not found
        """
        client = await self.ensure_client()
        
        try:
            response = await client.get(index=index_name, id=doc_id)
            return response.get("_source")
            
        except Exception as e:
            logger.debug(f"Document not found: {doc_id}")
            return None
    
    async def delete_document(
        self,
        index_name: str,
        doc_id: str,
    ) -> bool:
        """
        Delete a document by ID.
        
        Args:
            index_name: Name of the index
            doc_id: Document ID
        
        Returns:
            True if successful, False otherwise
        """
        client = await self.ensure_client()
        
        try:
            await client.delete(index=index_name, id=doc_id)
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete document {doc_id}: {e}")
            return False
    
    async def count(
        self,
        index_name: str,
        query: dict[str, Any] | None = None,
    ) -> int:
        """
        Count documents in an index.
        
        Args:
            index_name: Name of the index
            query: Optional query to filter documents
        
        Returns:
            Document count
        """
        client = await self.ensure_client()
        
        try:
            body = {"query": query} if query else None
            response = await client.count(index=index_name, body=body)
            return response.get("count", 0)
            
        except Exception as e:
            logger.error(f"Count failed: {e}")
            return 0
    
    async def update_document(
        self,
        index_name: str,
        doc_id: str,
        document: dict[str, Any],
        upsert: bool = False,
    ) -> bool:
        """
        Update a document.
        
        Args:
            index_name: Name of the index
            doc_id: Document ID
            document: Document fields to update
            upsert: Create document if it doesn't exist
        
        Returns:
            True if successful, False otherwise
        """
        client = await self.ensure_client()
        
        try:
            body: dict[str, Any] = {"doc": document}
            if upsert:
                body["doc_as_upsert"] = True
            
            await client.update(index=index_name, id=doc_id, body=body)
            return True
            
        except Exception as e:
            logger.error(f"Failed to update document {doc_id}: {e}")
            return False
