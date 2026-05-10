"""HTTP Client for Unified Data Service.

This module provides a client SDK that mimics the UnifiedDataService interface
but communicates with the separate unified-data-service microservice via HTTP.
"""

import asyncio
from typing import Any, Dict, List, Optional, TypeVar
import httpx
from pydantic import BaseModel

from .logger import get_logger

T = TypeVar("T")  # Entity type
K = TypeVar("K")  # Key type

logger = get_logger(__name__)


class UnifiedDataClient:
    """HTTP client for Unified Data Service microservice."""
    
    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        timeout: int = 30,
        max_retries: int = 3,
    ):
        """
        Initialize the HTTP client.
        
        Args:
            base_url: Base URL of the unified-data-service
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
        )
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    def _make_url(self, path: str) -> str:
        """Construct full URL from path."""
        return f"{self.base_url}{path}"
    
    async def _request_with_retry(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Make HTTP request with retry logic."""
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                response = await self.client.request(method, url, **kwargs)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                last_exception = e
                if e.response.status_code < 500:
                    # Don't retry client errors
                    break
                logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
            except Exception as e:
                last_exception = e
                logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
            
            if attempt < self.max_retries - 1:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        raise last_exception
    
    # Service Management
    async def register_service(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Register a new service."""
        return await self._request_with_retry(
            "POST",
            self._make_url("/api/v1/services"),
            json=config
        )
    
    async def get_service_info(self, service_name: str) -> Dict[str, Any]:
        """Get service information."""
        return await self._request_with_retry(
            "GET",
            self._make_url(f"/api/v1/services/{service_name}")
        )
    
    async def list_services(self) -> Dict[str, Any]:
        """List all services."""
        return await self._request_with_retry(
            "GET",
            self._make_url("/api/v1/services")
        )
    
    async def unregister_service(self, service_name: str) -> Dict[str, Any]:
        """Unregister a service."""
        return await self._request_with_retry(
            "DELETE",
            self._make_url(f"/api/v1/services/{service_name}")
        )
    
    # CRUD Operations
    async def create_entity(
        self,
        service_name: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create an entity."""
        return await self._request_with_retry(
            "POST",
            self._make_url(f"/api/v1/services/{service_name}/entities"),
            json=data
        )
    
    async def get_entity(
        self,
        service_name: str,
        entity_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get an entity by ID."""
        try:
            return await self._request_with_retry(
                "GET",
                self._make_url(f"/api/v1/services/{service_name}/entities/{entity_id}")
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise
    
    async def update_entity(
        self,
        service_name: str,
        entity_id: str,
        data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update an entity."""
        try:
            return await self._request_with_retry(
                "PUT",
                self._make_url(f"/api/v1/services/{service_name}/entities/{entity_id}"),
                json=data
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise
    
    async def delete_entity(
        self,
        service_name: str,
        entity_id: str
    ) -> bool:
        """Delete an entity."""
        try:
            await self._request_with_retry(
                "DELETE",
                self._make_url(f"/api/v1/services/{service_name}/entities/{entity_id}")
            )
            return True
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return False
            raise
    
    async def list_entities(
        self,
        service_name: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        skip: Optional[int] = None,
        sort_by: Optional[str] = None,
        sort_order: int = 1
    ) -> Dict[str, Any]:
        """List entities."""
        params = {}
        if filters:
            import json
            params["filters"] = json.dumps(filters)
        if limit is not None:
            params["limit"] = limit
        if skip is not None:
            params["skip"] = skip
        if sort_by:
            params["sort_by"] = sort_by
        if sort_order != 1:
            params["sort_order"] = sort_order
        
        return await self._request_with_retry(
            "GET",
            self._make_url(f"/api/v1/services/{service_name}/entities"),
            params=params
        )
    
    async def search_entities(
        self,
        service_name: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        skip: Optional[int] = None,
        sort_by: Optional[str] = None,
        sort_order: int = 1
    ) -> Dict[str, Any]:
        """Search entities."""
        params = {}
        if filters:
            import json
            params["filters"] = json.dumps(filters)
        if limit is not None:
            params["limit"] = limit
        if skip is not None:
            params["skip"] = skip
        if sort_by:
            params["sort_by"] = sort_by
        if sort_order != 1:
            params["sort_order"] = sort_order
        
        return await self._request_with_retry(
            "GET",
            self._make_url(f"/api/v1/services/{service_name}/search"),
            params=params
        )
    
    async def count_entities(
        self,
        service_name: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """Count entities."""
        params = {}
        if filters:
            import json
            params["filters"] = json.dumps(filters)
        
        result = await self._request_with_retry(
            "GET",
            self._make_url(f"/api/v1/services/{service_name}/count"),
            params=params
        )
        return result["count"]
    
    # Bulk Operations
    async def bulk_create_entities(
        self,
        service_name: str,
        data_list: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Bulk create entities."""
        return await self._request_with_retry(
            "POST",
            self._make_url(f"/api/v1/services/{service_name}/entities/bulk"),
            json=data_list
        )
    
    async def bulk_update_entities(
        self,
        service_name: str,
        updates: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Bulk update entities."""
        return await self._request_with_retry(
            "PUT",
            self._make_url(f"/api/v1/services/{service_name}/entities/bulk"),
            json=updates
        )
    
    async def bulk_delete_entities(
        self,
        service_name: str,
        ids: List[str]
    ) -> Dict[str, Any]:
        """Bulk delete entities."""
        return await self._request_with_retry(
            "DELETE",
            self._make_url(f"/api/v1/services/{service_name}/entities/bulk"),
            json=ids
        )
    
    # Cache Management
    async def warm_cache(self, service_name: str) -> Dict[str, Any]:
        """Warm cache for a service."""
        return await self._request_with_retry(
            "POST",
            self._make_url(f"/api/v1/services/{service_name}/cache/warm")
        )
    
    async def invalidate_cache(
        self,
        service_name: str,
        keys: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Invalidate cache for a service."""
        return await self._request_with_retry(
            "DELETE",
            self._make_url(f"/api/v1/services/{service_name}/cache"),
            json=keys
        )
    
    # Health and Stats
    async def health_check(self) -> Dict[str, Any]:
        """Get overall service health."""
        return await self._request_with_retry(
            "GET",
            self._make_url("/health")
        )
    
    async def get_service_stats(self, service_name: str) -> Dict[str, Any]:
        """Get service statistics."""
        return await self._request_with_retry(
            "GET",
            self._make_url(f"/api/v1/services/{service_name}/stats")
        )
    
    async def get_cache_stats(self, service_name: str) -> Dict[str, Any]:
        """Get cache statistics."""
        return await self._request_with_retry(
            "GET",
            self._make_url(f"/api/v1/services/{service_name}/cache/stats")
        )


# Compatibility layer for existing code
class UnifiedDataServiceAdapter:
    """Adapter to make UnifiedDataClient compatible with existing UnifiedDataService interface."""
    
    def __init__(
        self,
        service_name: str,
        client: UnifiedDataClient,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize adapter.
        
        Args:
            service_name: Name of the service to interact with
            client: UnifiedDataClient instance
            config: Service configuration (optional)
        """
        self.service_name = service_name
        self.client = client
        self.config = config or {}
        self.logger = get_logger(__name__)
    
    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create entity."""
        return await self.client.create_entity(self.service_name, data)
    
    async def get_by_id(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get entity by ID."""
        return await self.client.get_entity(self.service_name, entity_id)
    
    async def update(self, entity_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update entity."""
        return await self.client.update_entity(self.service_name, entity_id, data)
    
    async def delete(self, entity_id: str) -> bool:
        """Delete entity."""
        return await self.client.delete_entity(self.service_name, entity_id)
    
    async def get_all(self, query: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Get all entities."""
        if query is None:
            query = {}
        
        result = await self.client.list_entities(
            self.service_name,
            filters=query.get("filters"),
            limit=query.get("limit"),
            skip=query.get("skip"),
            sort_by=query.get("sort_by"),
            sort_order=query.get("sort_order", 1)
        )
        return result.get("items", [])
    
    async def search(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search entities."""
        result = await self.client.search_entities(
            self.service_name,
            filters=query.get("filters"),
            limit=query.get("limit"),
            skip=query.get("skip"),
            sort_by=query.get("sort_by"),
            sort_order=query.get("sort_order", 1)
        )
        return result.get("items", [])
    
    async def count(self, query: Optional[Dict[str, Any]] = None) -> int:
        """Count entities."""
        return await self.client.count_entities(
            self.service_name,
            filters=query.get("filters") if query else None
        )
    
    async def bulk_create(self, data_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Bulk create entities."""
        return await self.client.bulk_create_entities(self.service_name, data_list)
    
    async def bulk_update(self, updates: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Bulk update entities."""
        return await self.client.bulk_update_entities(self.service_name, updates)
    
    async def bulk_delete(self, ids: List[str]) -> Dict[str, Any]:
        """Bulk delete entities."""
        return await self.client.bulk_delete_entities(self.service_name, ids)
    
    async def warm_cache(self) -> int:
        """Warm cache."""
        result = await self.client.warm_cache(self.service_name)
        return result.get("count", 0)
    
    async def invalidate_cache(self, keys: Optional[List[str]] = None) -> None:
        """Invalidate cache."""
        await self.client.invalidate_cache(self.service_name, keys)
    
    async def get_service_stats(self) -> Dict[str, Any]:
        """Get service statistics."""
        return await self.client.get_service_stats(self.service_name)
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return await self.client.get_cache_stats(self.service_name)
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check."""
        # Get overall health and filter for this service
        overall_health = await self.client.health_check()
        service_health = overall_health.get("services", {}).get(self.service_name)
        return service_health or {"status": "unknown"}
