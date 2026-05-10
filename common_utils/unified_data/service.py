"""Core unified data service implementation.

This module provides the main UnifiedDataService class that combines
data sources and caching into a single, reusable service pattern.
"""

import asyncio
import time
from typing import Any, Dict, List, Optional, TypeVar

from common_utils.cache import ICacheRepository
from common_utils.work_in_progress.events import EventBroadcastService, EventType
from common_utils.logger import get_logger

from .interfaces import (
    BulkOperationResult,
    DataSourceQuery,
    IDataSource,
    IUnifiedService,
    PaginatedResult,
    ServiceConfig,
)

T = TypeVar("T")  # Entity type
K = TypeVar("K")  # Key type

logger = get_logger(__name__)


class UnifiedDataService(IUnifiedService[T, K]):
    """
    Complete unified data service with CRUD operations + business logic optimization.

    This service provides:
    - Data operations with automatic caching
    - Automatic gauge metrics on all operations
    - Event-driven cache invalidation across pods
    - Business logic optimization framework with high-performance lookups
    - Bulk operations with performance optimization
    """

    def __init__(
        self,
        data_source: IDataSource[T, K],
        cache_repository: ICacheRepository[T],
        config: ServiceConfig,
        event_service: Optional[EventBroadcastService] = None,
        key_extractor: Optional[callable] = None,
    ):
        """
        Initialize unified data service.

        Args:
            data_source: Data source implementation (MongoDB, API, etc.)
            cache_repository: Enhanced cache repository
            config: Service configuration
            event_service: Event broadcast service for cache invalidation
            key_extractor: Function to extract cache key from entity
        """
        # Data operations infrastructure
        self._data_source = data_source
        self._cache = cache_repository
        self._config = config
        self._event_service = event_service
        self._key_extractor = key_extractor or self._default_key_extractor

        # Business logic optimization (built-in)
        self._lookups_built = False
        self._lookups_dirty = True
        self._lookup_structures: Dict[str, Any] = {}
        self._rebuild_lock = asyncio.Lock()  # Lock to prevent concurrent rebuilds

        # Business logic integration
        self.business: Optional[Any] = None  # Will be injected by ServiceFactory
        self._lookup_builder_method: Optional[str] = None
        self._rebuild_on_operations: List[str] = []

        # Configure lookup optimization
        if config.lookup_optimization:
            self._lookup_builder_method = config.lookup_optimization.get(
                "builder_method"
            )
            self._rebuild_on_operations = config.lookup_optimization.get(
                "rebuild_on", []
            )

        self.logger = logger

        # Metric module name (data_service label value). Kebab-case service
        # name → snake_case so it's a valid Prometheus label.
        self._metric_service_label = self._config.name.replace("-", "_")

        # In-memory entity count + cache-gauge throttle. Avoids a per-write
        # ``count()`` DB roundtrip and per-write cache-stats fetch.
        self._entity_count: Optional[int] = None
        self._cache_gauge_last_update: float = 0.0
        self._cache_gauge_min_interval_seconds: float = 30.0

        # Auto-register the shared metric set. Idempotent across services.
        self._register_standard_metrics()

    # Shared module name for all unified data services. The data_service
    # label disambiguates per-service series — see Grafana recipes that
    # group/filter on ``data_service``.
    _METRICS_MODULE = "unified_data"

    def _register_standard_metrics(self) -> None:
        """Register the shared unified-data metric set under module
        ``unified_data``. ``register_module_metrics`` is idempotent across
        UDS instances so all services share one definition."""
        from common_utils.metrics import register_module_metrics

        register_module_metrics(
            self._METRICS_MODULE,
            {
                # Operation counter — labels distinguish service / op /
                # success-vs-error.
                "operations_total": {
                    "type": "counter",
                    "description": "Total unified-data operations",
                    "labels": ["data_service", "operation", "status"],
                },
                # Operation latency histogram — same labels as the counter
                # so success / error latencies are separable.
                "operation_duration_seconds": {
                    "type": "histogram",
                    "description": "Unified-data operation duration (seconds)",
                    "labels": ["data_service", "operation", "status"],
                },
                # Entities processed — counts items, not calls. For bulk_*
                # this is the success_count; for single ops it's 1.
                "entities_processed_total": {
                    "type": "counter",
                    "description": (
                        "Total entities processed by unified-data ops "
                        "(bulk_* counts items, not calls)"
                    ),
                    "labels": ["data_service", "operation"],
                },
                # Live entity count per service — maintained in-memory off
                # the success path (initial seed + delta), so write paths
                # don't trigger a count() roundtrip.
                "total_entities": {
                    "type": "gauge",
                    "description": "Total entities in the data source",
                    "labels": ["data_service"],
                },
                "cache_hit_ratio": {
                    "type": "gauge",
                    "description": "Cache hit ratio (0..1)",
                    "labels": ["data_service"],
                },
                "cache_total_keys": {
                    "type": "gauge",
                    "description": "Total keys in the cache backend",
                    "labels": ["data_service"],
                },
                # In-flight HTTP requests handled by this service's
                # controller. Incremented at request entry, decremented at
                # exit (incl. exceptions). Allows alerting on stuck
                # requests.
                "inflight_requests": {
                    "type": "gauge",
                    "description": "In-flight HTTP requests by data service / op",
                    "labels": ["data_service", "operation"],
                },
            },
        )

    def _default_key_extractor(self, entity: T) -> str:
        """Default key extractor using entity ID."""
        if hasattr(entity, "id"):
            return f"{self._config.cache_key_prefix}{entity.id}"
        elif hasattr(entity, "_id"):
            return f"{self._config.cache_key_prefix}{entity._id}"
        else:
            return f"{self._config.cache_key_prefix}{hash(str(entity))}"

    def _get_cache_key(self, id: K) -> str:
        """Get cache key for entity ID."""
        return f"{self._config.cache_key_prefix}{id}"

    # Basic CRUD Operations
    async def get_by_id(self, id: K) -> Optional[T]:
        """Get entity by ID with caching."""
        cache_key = self._get_cache_key(id)

        # Try cache first
        cached_entity = await self._cache.get_by_key(cache_key)
        if cached_entity is not None:
            return cached_entity

        # Cache miss - get from data source
        entity = await self._data_source.get_by_id(id)
        if entity is not None:
            # Cache the result
            await self._cache.set_by_key(cache_key, entity, self._config.cache_ttl)

        return entity

    async def get_all(self, query: Optional[DataSourceQuery] = None) -> List[T]:
        """Get all entities with caching."""
        # For get_all operations, we typically don't cache the full result
        # as it can be large and change frequently. Instead, we warm the cache
        # with individual entities.
        entities = await self._data_source.get_all(query)

        # Optionally warm cache with individual entities
        if (
            self._config.enable_cache_warming
            and len(entities) <= self._config.max_bulk_size
        ):
            cache_items = {}
            for entity in entities:
                cache_key = self._key_extractor(entity)
                cache_items[cache_key] = entity

            await self._cache.set_many(cache_items, self._config.cache_ttl)

        return entities

    def _apply_pagination_defaults(
        self, query: Optional[DataSourceQuery]
    ) -> DataSourceQuery:
        """Apply default limit/skip and clamp to max limit."""
        if query is None:
            return DataSourceQuery(limit=self._config.default_limit, skip=0)

        updates = {}
        if query.limit is None:
            updates["limit"] = self._config.default_limit
        if query.skip is None:
            updates["skip"] = 0
        if updates:
            query = query.model_copy(update=updates)

        if query.limit > self._config.max_limit:
            query = query.model_copy(update={"limit": self._config.max_limit})

        return query

    async def _fetch_paginated(
        self, fetch_coro, query: DataSourceQuery
    ) -> PaginatedResult:
        """Fetch items and total count in parallel, return PaginatedResult."""
        count_query = DataSourceQuery(filters=query.filters) if query.filters else None
        items, total = await asyncio.gather(
            fetch_coro,
            self.count(count_query),
        )

        return PaginatedResult(
            items=items,
            total=total,
            limit=query.limit,
            skip=query.skip,
            has_more=query.skip + query.limit < total,
        )

    async def get_paginated(
        self, query: Optional[DataSourceQuery] = None
    ) -> PaginatedResult:
        """Get entities with pagination metadata. Applies default limit if none specified."""
        query = self._apply_pagination_defaults(query)
        return await self._fetch_paginated(self._data_source.get_all(query), query)

    async def search_paginated(self, query: DataSourceQuery) -> PaginatedResult:
        """Search entities with pagination metadata. Applies default limit if none specified."""
        query = self._apply_pagination_defaults(query)
        return await self._fetch_paginated(self._data_source.find(query), query)

    async def _invalidate_count_cache(self) -> None:
        """Invalidate all cached count results so paginated responses reflect current state."""
        pattern = f"{self._config.cache_key_prefix}count:*"
        await self._cache.delete_by_pattern(pattern)

    async def create(self, data: Dict[str, Any]) -> T:
        """Create entity with cache invalidation, metrics, and business logic notification."""
        started = time.monotonic()
        try:
            entity = await self._data_source.create(data)
        except Exception:
            await self._record_op("create", "error", started)
            raise

        cache_key = self._key_extractor(entity)
        await self._cache.set_by_key(cache_key, entity, self._config.cache_ttl)

        if self._config.enable_event_invalidation and self._event_service:
            await self._broadcast_cache_invalidation([cache_key])

        await self._record_op("create", "success", started, items=1, count_delta=+1)
        await self._invalidate_count_cache()
        self._mark_lookups_dirty()

        return entity

    async def update(self, id: K, data: Dict[str, Any]) -> Optional[T]:
        """Update entity with cache invalidation, metrics, and business logic notification."""
        started = time.monotonic()
        try:
            entity = await self._data_source.update(id, data)
        except Exception:
            await self._record_op("update", "error", started)
            raise

        if entity is not None:
            cache_key = self._get_cache_key(id)
            await self._cache.set_by_key(cache_key, entity, self._config.cache_ttl)

            if self._config.enable_event_invalidation and self._event_service:
                await self._broadcast_cache_invalidation([cache_key])

            await self._record_op("update", "success", started, items=1)
            self._mark_lookups_dirty()
        else:
            # Target row didn't exist — record a no-op success with 0 items
            await self._record_op("update", "success", started, items=0)

        return entity

    async def delete(self, id: K) -> bool:
        """Delete entity with cache invalidation, metrics, and business logic notification."""
        started = time.monotonic()
        try:
            success = await self._data_source.delete(id)
        except Exception:
            await self._record_op("delete", "error", started)
            raise

        if success:
            cache_key = self._get_cache_key(id)
            await self._cache.delete_by_key(cache_key)

            if self._config.enable_event_invalidation and self._event_service:
                await self._broadcast_cache_invalidation([cache_key])

            await self._record_op("delete", "success", started, items=1, count_delta=-1)
            await self._invalidate_count_cache()
            self._mark_lookups_dirty()
        else:
            await self._record_op("delete", "success", started, items=0)

        return success

    async def exists(self, id: K) -> bool:
        """Check if entity exists without fetching the full document."""
        # Check cache first — if it's cached, it exists
        cache_key = self._get_cache_key(id)
        cached = await self._cache.get_by_key(cache_key)
        if cached is not None:
            return True

        # Fall back to data source
        return await self._data_source.exists(id)

    # Bulk Operations
    async def bulk_create(self, data_list: List[Dict[str, Any]]) -> BulkOperationResult:
        """Bulk create with cache warming."""
        started = time.monotonic()
        if not self._config.enable_bulk_operations:
            # Fall back to individual operations — children record their own
            # metrics; this branch only records the bulk wrapper itself.
            result = BulkOperationResult(total_count=len(data_list))
            for data in data_list:
                try:
                    await self.create(data)
                    result.success_count += 1
                except Exception as e:
                    result.error_count += 1
                    result.errors.append(str(e))
            await self._record_op(
                "bulk_create",
                "success" if result.error_count == 0 else "partial",
                started,
                items=result.success_count,
                count_delta=result.success_count,
            )
            return result

        try:
            result = await self._data_source.bulk_create(data_list)
        except Exception:
            await self._record_op("bulk_create", "error", started, items=0)
            raise

        await self._record_op(
            "bulk_create",
            "success" if result.error_count == 0 else "partial",
            started,
            items=result.success_count,
            count_delta=result.success_count,
        )

        if result.success_count > 0:
            await self._invalidate_count_cache()
            self._mark_lookups_dirty()

        return result

    async def bulk_upsert(self, data_list: List[Dict[str, Any]]) -> BulkOperationResult:
        """Bulk upsert — insert new entities, update existing ones based on upsert_fields config."""
        if not self._config.upsert_fields:
            raise ValueError(
                f"upsert_fields not configured for service '{self._config.name}'. "
                "Add upsert_fields to the service YAML config."
            )

        started = time.monotonic()
        try:
            result = await self._data_source.bulk_upsert(
                data_list, self._config.upsert_fields
            )
        except Exception:
            await self._record_op("bulk_upsert", "error", started, items=0)
            raise

        # bulk_upsert blends inserts + updates; we don't know how many of each
        # without an extra roundtrip, so the count_delta gauge is intentionally
        # invalidated rather than updated incrementally.
        if result.success_count > 0:
            self._entity_count = None  # force re-seed on next op
            await self._invalidate_count_cache()
            self._mark_lookups_dirty()

        await self._record_op(
            "bulk_upsert",
            "success" if result.error_count == 0 else "partial",
            started,
            items=result.success_count,
        )
        return result

    async def bulk_update(
        self, updates: Dict[K, Dict[str, Any]]
    ) -> BulkOperationResult:
        """Bulk update with cache invalidation."""
        started = time.monotonic()
        if not self._config.enable_bulk_operations:
            result = BulkOperationResult(total_count=len(updates))
            for entity_id, update_data in updates.items():
                try:
                    await self.update(entity_id, update_data)
                    result.success_count += 1
                except Exception as e:
                    result.error_count += 1
                    result.errors.append(str(e))
            await self._record_op(
                "bulk_update",
                "success" if result.error_count == 0 else "partial",
                started,
                items=result.success_count,
            )
            return result

        try:
            result = await self._data_source.bulk_update(updates)
        except Exception:
            await self._record_op("bulk_update", "error", started, items=0)
            raise

        if result.success_count > 0:
            cache_keys = [
                self._get_cache_key(entity_id) for entity_id in updates.keys()
            ]
            await self._cache.delete_many(cache_keys)

            if self._config.enable_event_invalidation and self._event_service:
                await self._broadcast_cache_invalidation(cache_keys)

            self._mark_lookups_dirty()

        await self._record_op(
            "bulk_update",
            "success" if result.error_count == 0 else "partial",
            started,
            items=result.success_count,
        )
        return result

    async def bulk_delete(self, ids: List[K]) -> BulkOperationResult:
        """Bulk delete with cache invalidation."""
        started = time.monotonic()
        if not self._config.enable_bulk_operations:
            result = BulkOperationResult(total_count=len(ids))
            for entity_id in ids:
                try:
                    await self.delete(entity_id)
                    result.success_count += 1
                except Exception as e:
                    result.error_count += 1
                    result.errors.append(str(e))
            await self._record_op(
                "bulk_delete",
                "success" if result.error_count == 0 else "partial",
                started,
                items=result.success_count,
                count_delta=-result.success_count,
            )
            return result

        try:
            result = await self._data_source.bulk_delete(ids)
        except Exception:
            await self._record_op("bulk_delete", "error", started, items=0)
            raise

        if result.success_count > 0:
            cache_keys = [self._get_cache_key(entity_id) for entity_id in ids]
            await self._cache.delete_many(cache_keys)

            if self._config.enable_event_invalidation and self._event_service:
                await self._broadcast_cache_invalidation(cache_keys)

            await self._invalidate_count_cache()
            self._mark_lookups_dirty()

        await self._record_op(
            "bulk_delete",
            "success" if result.error_count == 0 else "partial",
            started,
            items=result.success_count,
            count_delta=-result.success_count,
        )
        return result

    # Cache Management
    async def warm_cache(self) -> int:
        """
        Warm cache with all data from source and build lookup structures.

        This method both warms the cache and builds lookup structures in a single
        operation to avoid redundant data fetching. Lookup structures are built
        if lookup optimization is enabled for this service.
        """
        if not self._config.enable_cache_warming:
            return 0

        try:
            # Get all entities from data source
            entities = await self._data_source.get_all()

            # Prepare cache items
            cache_items = {}
            for entity in entities:
                cache_key = self._key_extractor(entity)
                cache_items[cache_key] = entity

            # Bulk set in cache
            await self._cache.set_many(cache_items, self._config.cache_ttl)

            # Seed the in-memory entity count + publish the gauge — saves
            # the lazy ``count()`` roundtrip that ``_publish_total_entities_gauge``
            # would otherwise do on the first write.
            self._entity_count = len(entities)
            try:
                from common_utils.metrics import track_metric_async

                await track_metric_async(
                    module_name=self._METRICS_MODULE,
                    metric_type="gauge",
                    metric_name="total_entities",
                    value=float(self._entity_count),
                    labels={"data_service": self._metric_service_label},
                )
            except Exception as e:
                self.logger.debug(f"Could not publish total_entities at warm: {e}")

            # Build lookup structures if optimization is enabled
            # This avoids redundant get_all() calls during ensure_lookups_ready()
            if self._lookup_builder_method:
                async with self._rebuild_lock:
                    await self._build_lookup_structures(entities)
                    self._lookups_built = True
                    self._lookups_dirty = False
                    self.logger.debug(
                        f"Built lookup structures during cache warm for service {self._config.name}"
                    )

            self.logger.info(
                f"Cache warmed with {len(cache_items)} entities for service {self._config.name}"
            )
            return len(cache_items)

        except Exception as e:
            self.logger.error(
                f"Error warming cache for service {self._config.name}: {e}"
            )
            return 0

    async def invalidate_cache(self, keys: Optional[List[str]] = None) -> None:
        """Invalidate cache (all or specific keys)."""
        if keys:
            await self._cache.delete_many(keys)
            self.logger.debug(
                f"Invalidated {len(keys)} cache keys for service {self._config.name}"
            )
        else:
            # Clear all cache entries for this service
            pattern = f"{self._config.cache_key_prefix}*"
            deleted_count = await self._cache.delete_by_pattern(pattern)
            self.logger.info(
                f"Invalidated {deleted_count} cache entries for service {self._config.name}"
            )

    async def refresh_cache(self) -> int:
        """Refresh cache by clearing and reloading.

        Returns:
            Number of items cached after refresh.
        """
        await self.invalidate_cache()
        return await self.warm_cache()

    # Advanced Operations
    async def delete_all(self) -> int:
        """Delete all entities for this service."""
        started = time.monotonic()
        try:
            all_entities = await self._data_source.get_all()
            total_count = len(all_entities)

            if total_count == 0:
                await self._record_op("delete_all", "success", started, items=0)
                self.logger.info(
                    f"No entities to delete for service {self._config.name}"
                )
                return 0

            deleted_count = await self._data_source.delete_all()

            pattern = f"{self._config.cache_key_prefix}*"
            cache_deleted_count = await self._cache.delete_by_pattern(pattern)

            self._mark_lookups_dirty()

            # Reset in-memory entity count to 0 and publish the gauge.
            # ``_record_op`` only publishes when count_delta != 0, so we set
            # the gauge directly here.
            self._entity_count = 0
            from common_utils.metrics import track_metric_async

            await track_metric_async(
                module_name=self._METRICS_MODULE,
                metric_type="gauge",
                metric_name="total_entities",
                value=0.0,
                labels={"data_service": self._metric_service_label},
            )

            await self._record_op(
                "delete_all", "success", started, items=deleted_count
            )

            self.logger.info(
                f"Deleted all {deleted_count} entities and {cache_deleted_count} cache entries for service {self._config.name}"
            )

            return deleted_count

        except Exception as e:
            await self._record_op("delete_all", "error", started, items=0)
            self.logger.error(
                f"Error deleting all entities for service {self._config.name}: {e}"
            )
            raise

    async def search(self, query: DataSourceQuery) -> List[T]:
        """Search entities with caching."""
        # For search operations, we typically don't cache results
        # as they can be highly variable
        return await self._data_source.find(query)

    async def count(self, query: Optional[DataSourceQuery] = None) -> int:
        """Count entities with caching."""
        # Count operations can be cached with a shorter TTL
        cache_key = f"{self._config.cache_key_prefix}count:{hash(str(query))}"

        # Try cache first
        cached_count = await self._cache.get_by_key(cache_key)
        if cached_count is not None:
            return cached_count

        # Cache miss - get from data source
        count = await self._data_source.count(query)

        # Cache with shorter TTL (counts change more frequently)
        count_ttl = min(self._config.cache_ttl or 300, 60)  # Max 1 minute for counts
        await self._cache.set_by_key(cache_key, count, count_ttl)

        return count

    async def distinct(
        self, field: str, filters: Optional[Dict[str, Any]] = None
    ) -> List[Any]:
        """Return distinct values of `field`. Pass-through to data source;
        not cached since the result depends on the entire collection."""
        return await self._data_source.distinct(field, filters)

    # Statistics and Monitoring
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        return await self._cache.get_cache_stats()

    def get_cache_info(self) -> Dict[str, Any]:
        """Get cache configuration and capabilities."""
        return self._cache.get_cache_info()

    async def get_service_stats(self) -> Dict[str, Any]:
        """Get overall service statistics."""
        cache_stats = await self.get_cache_stats()
        data_source_health = await self._data_source.health_check()

        return {
            "service_name": self._config.name,
            "entity_type": self._config.entity_type,
            "cache_backend": self._config.cache_backend,
            "cache_strategy": self._config.cache_strategy,
            "cache_stats": cache_stats,
            "data_source_health": data_source_health,
            "config": {
                "cache_ttl": self._config.cache_ttl,
                "bulk_operations_enabled": self._config.enable_bulk_operations,
                "cache_warming_enabled": self._config.enable_cache_warming,
                "event_invalidation_enabled": self._config.enable_event_invalidation,
            },
        }

    async def health_check(self) -> Dict[str, Any]:
        """Check service health (cache + data source)."""
        try:
            # Check data source health
            data_source_health = await self._data_source.health_check()

            # Check cache health
            cache_info = self._cache.get_cache_info()

            # Overall health status
            is_healthy = (
                data_source_health.get("status") == "healthy"
                and cache_info.get("backend") is not None
            )

            return {
                "status": "healthy" if is_healthy else "unhealthy",
                "service_name": self._config.name,
                "data_source": data_source_health,
                "cache": cache_info,
                "timestamp": None,  # Will be set by monitoring system
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "service_name": self._config.name,
                "error": str(e),
                "timestamp": None,
            }

    async def _broadcast_cache_invalidation(self, cache_keys: List[str]) -> None:
        """Broadcast cache invalidation event to other pods."""
        if not self._event_service:
            return

        try:
            await self._event_service.broadcast_event_by_type(
                EventType.CACHE_REFRESH_PATTERN,
                {
                    "service_name": self._config.name,
                    "cache_keys": cache_keys,
                    "action": "invalidate",
                },
            )
        except Exception as e:
            self.logger.error(f"Error broadcasting cache invalidation: {e}")

    async def _record_op(
        self,
        operation: str,
        status: str,
        started_at: float,
        items: int = 1,
        count_delta: int = 0,
    ) -> None:
        """Emit the operation counter, latency histogram and entities-processed
        counter for ``operation``. ``count_delta`` updates the in-memory
        ``total_entities`` gauge without triggering a ``count()`` roundtrip;
        cache gauges piggyback at most once per ``_cache_gauge_min_interval_seconds``.

        Errors swallowed so metric failures never disrupt business logic.
        """
        try:
            from common_utils.metrics import track_metric_async

            duration = max(0.0, time.monotonic() - started_at)
            base_labels = {
                "data_service": self._metric_service_label,
                "operation": operation,
            }
            op_labels = {**base_labels, "status": status}

            await track_metric_async(
                module_name=self._METRICS_MODULE,
                metric_type="counter",
                metric_name="operations_total",
                value=1.0,
                labels=op_labels,
            )
            await track_metric_async(
                module_name=self._METRICS_MODULE,
                metric_type="histogram",
                metric_name="operation_duration_seconds",
                value=duration,
                labels=op_labels,
            )
            if items:
                await track_metric_async(
                    module_name=self._METRICS_MODULE,
                    metric_type="counter",
                    metric_name="entities_processed_total",
                    value=float(items),
                    labels=base_labels,
                )

            if status == "success" and count_delta:
                await self._publish_total_entities_gauge(count_delta)

            await self._maybe_update_cache_gauges()

        except Exception as e:
            self.logger.error(f"Error recording op metric: {e}")

    async def _publish_total_entities_gauge(self, delta: int) -> None:
        """Update the cached entity count by ``delta`` and publish the
        gauge. Seeds the cached value lazily from the data source on the
        first call (one-time count(); after that the gauge is maintained
        purely off the success path)."""
        from common_utils.metrics import track_metric_async

        if self._entity_count is None:
            try:
                self._entity_count = max(0, await self._data_source.count())
            except Exception:
                # If the seed fails (e.g. data source not reachable),
                # skip the gauge update — we'll retry on the next op.
                return
        else:
            self._entity_count = max(0, self._entity_count + delta)

        await track_metric_async(
            module_name=self._METRICS_MODULE,
            metric_type="gauge",
            metric_name="total_entities",
            value=float(self._entity_count),
            labels={"data_service": self._metric_service_label},
        )

    async def _maybe_update_cache_gauges(self) -> None:
        """Refresh cache hit-ratio + total-keys gauges, throttled to at
        most once per ``_cache_gauge_min_interval_seconds``."""
        now = time.monotonic()
        if now - self._cache_gauge_last_update < self._cache_gauge_min_interval_seconds:
            return
        self._cache_gauge_last_update = now

        try:
            from common_utils.metrics import track_metric_async

            cache_stats = await self._cache.get_cache_stats()
            labels = {"data_service": self._metric_service_label}
            await track_metric_async(
                module_name=self._METRICS_MODULE,
                metric_type="gauge",
                metric_name="cache_hit_ratio",
                value=float(cache_stats.get("hit_ratio", 0.0)),
                labels=labels,
            )
            await track_metric_async(
                module_name=self._METRICS_MODULE,
                metric_type="gauge",
                metric_name="cache_total_keys",
                value=float(cache_stats.get("total_keys", 0)),
                labels=labels,
            )
        except Exception as e:
            self.logger.error(f"Error updating cache gauges: {e}")

    # ===== BUSINESS LOGIC OPTIMIZATION =====

    async def ensure_lookups_ready(self) -> None:
        """
        Ensure lookup structures are built and ready for high-speed access.

        Uses a lock to prevent concurrent rebuilds when multiple coroutines
        call this method simultaneously. If lookups are already built and not
        dirty, this method returns immediately without acquiring the lock.
        """
        # Fast path: if lookups are already built and not dirty, return immediately
        if self._lookups_built and not self._lookups_dirty:
            return

        # Acquire lock to prevent concurrent rebuilds
        async with self._rebuild_lock:
            # Double-check after acquiring lock - another coroutine may have
            # already rebuilt while we were waiting
            if self._lookups_built and not self._lookups_dirty:
                return

            # Rebuild lookups
            await self.rebuild_lookups()

    async def rebuild_lookups(self) -> None:
        """
        Rebuild in-memory lookup structures from current data.

        This method calls the service-specific _build_lookup_structures method
        to create optimized lookup structures for high-performance business methods.
        """
        try:
            self.logger.info("Rebuilding business logic lookup structures...")

            # Get all entities from the data source
            all_entities = await self.get_all()

            # Call service-specific lookup building
            await self._build_lookup_structures(all_entities)

            self._lookups_built = True
            self._lookups_dirty = False
            self.logger.info(
                f"Built lookup structures for {len(all_entities)} entities"
            )

        except Exception as e:
            self.logger.error(f"Error rebuilding lookup structures: {e}")
            raise

    async def _build_lookup_structures(self, entities: List[T]) -> None:
        """
        Build service-specific lookup structures.

        Delegates to business logic if available, otherwise uses default implementation.

        Args:
            entities: List of all entities to build lookups from
        """
        # Delegate to business logic if available
        if self.business and self._lookup_builder_method:
            builder = getattr(self.business, self._lookup_builder_method, None)
            if builder:
                await builder(entities)
                self.logger.debug(
                    f"Built lookup structures using business logic method: {self._lookup_builder_method}"
                )
                return

        # Default implementation - subclasses should override
        self.logger.debug("Using default lookup structure building")
        self._lookup_structures["entity_count"] = len(entities)

    def _mark_lookups_dirty(self) -> None:
        """Mark lookups as dirty after data changes (called automatically)."""
        self._lookups_dirty = True
        self.logger.debug("Marked business logic lookups as dirty")

    async def _should_rebuild_lookups(self, operation: str) -> bool:
        """Check if lookups should be rebuilt after this operation."""
        return operation in self._rebuild_on_operations

    async def invalidate_lookups(self) -> None:
        """Invalidate lookup structures to force rebuild on next access."""
        self._lookups_built = False
        self._lookups_dirty = True
        self._lookup_structures.clear()
        self.logger.debug("Invalidated business logic lookup structures")

    def get_lookup_stats(self) -> Dict[str, Any]:
        """Get statistics about lookup structures."""
        return {
            "lookups_built": self._lookups_built,
            "lookups_dirty": self._lookups_dirty,
            "lookup_structures": list(self._lookup_structures.keys()),
            "entity_count": self._lookup_structures.get("entity_count", 0),
        }

    # Helper methods for common business logic patterns

    async def get_field_from_entity(
        self, entity_id: K, field_name: str
    ) -> Optional[Any]:
        """Get a specific field from an entity by ID."""
        entity = await self.get_by_id(entity_id)
        return getattr(entity, field_name, None) if entity else None

    async def get_entities_by_field_value(
        self, field_name: str, field_value: Any
    ) -> List[T]:
        """Get all entities where a field matches a specific value."""
        query = DataSourceQuery(filters={field_name: field_value})
        return await self.search(query)

    async def count_entities_by_field_value(
        self, field_name: str, field_value: Any
    ) -> int:
        """Count entities where a field matches a specific value."""
        query = DataSourceQuery(filters={field_name: field_value})
        return await self.count(query)

    async def search_entities_by_field_contains(
        self, field_name: str, search_term: str, case_sensitive: bool = False
    ) -> List[T]:
        """Search entities where a field contains a search term."""
        # For large datasets, this should use database queries
        # For small datasets, in-memory search can be faster
        all_entities = await self.get_all()

        if case_sensitive:
            return [
                entity
                for entity in all_entities
                if hasattr(entity, field_name)
                and search_term in str(getattr(entity, field_name, ""))
            ]
        else:
            search_lower = search_term.lower()
            return [
                entity
                for entity in all_entities
                if hasattr(entity, field_name)
                and search_lower in str(getattr(entity, field_name, "")).lower()
            ]

    async def get_distinct_field_values(self, field_name: str) -> List[Any]:
        """Get all distinct values for a specific field."""
        all_entities = await self.get_all()
        values = set()

        for entity in all_entities:
            if hasattr(entity, field_name):
                value = getattr(entity, field_name)
                if value is not None:
                    values.add(value)

        return list(values)

    # Performance monitoring for business logic
    async def get_business_logic_stats(self) -> Dict[str, Any]:
        """Get performance statistics for business logic operations."""
        service_stats = await self.get_service_stats()
        lookup_stats = self.get_lookup_stats()

        return {
            "service_stats": service_stats,
            "lookup_stats": lookup_stats,
            "business_logic_ready": self._lookups_built and not self._lookups_dirty,
        }
