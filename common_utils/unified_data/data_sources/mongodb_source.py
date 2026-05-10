"""MongoDB data source implementation for the unified data service architecture.

This module provides a MongoDB implementation of the IDataSource interface,
leveraging the existing repository infrastructure.
"""

import inspect
from typing import Any, Dict, List, Optional, Type, TypeVar

from beanie import Document

from common_utils.logger import get_logger
from common_utils.repository import MongoDocumentRepository

from ..interfaces import BulkOperationResult, DataSourceQuery, IDataSource

T = TypeVar("T", bound=Document)
K = TypeVar("K")

logger = get_logger(__name__)


class MongoDBDataSource(IDataSource[T, K]):
    """
    MongoDB data source implementation using existing repository infrastructure.

    This class wraps the existing MongoDocumentRepository to provide the
    IDataSource interface for the unified data service architecture.
    """

    def __init__(
        self,
        document_class: Type[T],
        mongo_client=None,
        key_field: str = "id",
    ):
        """
        Initialize MongoDB data source.

        Args:
            document_class: Beanie document class
            mongo_client: MongoDB client instance
            key_field: Field name to use as the key (default: "id")
        """
        self._document_class = document_class
        self._repository = MongoDocumentRepository(document_class, mongo_client)
        self._key_field = key_field
        self.logger = logger

    def get_entity_type(self) -> Type[T]:
        """Get the entity type this data source handles."""
        return self._document_class

    def get_key_type(self) -> Type[K]:
        """Get the key type this data source uses."""
        # For MongoDB, keys are typically strings (ObjectId as string)
        return str  # type: ignore

    async def get_by_id(self, id: K) -> Optional[T]:
        """Get entity by ID.

        When `key_field` is "id" or "_id" (the default Beanie ObjectId path),
        delegates to the repository which accepts an ObjectId or string _id.
        Otherwise looks the entity up by the configured natural-key field.
        """
        try:
            if self._is_natural_key_field():
                return await self._document_class.find_one(
                    {self._key_field: id}
                )
            return await self._repository.get_by_id(str(id))
        except Exception as e:
            self.logger.error(f"Error getting entity by ID {id}: {e}")
            return None

    async def get_all(self, query: Optional[DataSourceQuery] = None) -> List[T]:
        """Get all entities matching query."""
        try:
            if query is None:
                return await self._repository.get_all()

            # Convert DataSourceQuery to repository pagination
            if query.limit is not None or query.skip is not None:
                return await self._repository.find_with_pagination(
                    query=self._convert_query(query),
                    skip=query.skip if query.skip is not None else 0,
                    limit=query.limit if query.limit is not None else 0,
                    sort_by=query.sort_by,
                    sort_order=query.sort_order,
                )
            else:
                return await self._repository.find(self._convert_query(query))

        except Exception as e:
            self.logger.error(f"Error getting all entities: {e}")
            return []

    async def create(self, data: Dict[str, Any]) -> T:
        """Create new entity."""
        try:
            return await self._repository.create(data)
        except Exception as e:
            self.logger.error(f"Error creating entity: {e}")
            raise

    async def update(self, id: K, data: Dict[str, Any]) -> Optional[T]:
        """Update entity by ID (natural-key aware)."""
        try:
            if self._is_natural_key_field():
                document = await self._document_class.find_one(
                    {self._key_field: id}
                )
                if document is None:
                    return None
                for key, value in data.items():
                    setattr(document, key, value)
                if hasattr(document, "update_timestamp"):
                    maybe_awaitable = document.update_timestamp()
                    if inspect.isawaitable(maybe_awaitable):
                        await maybe_awaitable
                return await document.save()
            return await self._repository.update(str(id), data)
        except Exception as e:
            self.logger.error(f"Error updating entity {id}: {e}")
            return None

    async def delete(self, id: K) -> bool:
        """Delete entity by ID (natural-key aware)."""
        try:
            if self._is_natural_key_field():
                document = await self._document_class.find_one(
                    {self._key_field: id}
                )
                if document is None:
                    return False
                await document.delete()
                return True
            return await self._repository.delete(str(id))
        except Exception as e:
            self.logger.error(f"Error deleting entity {id}: {e}")
            return False

    async def exists(self, id: K) -> bool:
        """Check if entity exists (natural-key aware)."""
        try:
            if self._is_natural_key_field():
                document = await self._document_class.find_one(
                    {self._key_field: id}
                )
                return document is not None
            entity = await self._repository.get_by_id(str(id))
            return entity is not None
        except Exception as e:
            self.logger.error(f"Error checking entity existence {id}: {e}")
            return False

    def _is_natural_key_field(self) -> bool:
        return self._key_field not in ("id", "_id")

    async def distinct(
        self, field: str, filters: Optional[Dict[str, Any]] = None
    ) -> List[Any]:
        """Return distinct values of `field`. Delegates to Beanie's
        ``Document.distinct`` which wraps Mongo's ``collection.distinct``."""
        try:
            return await self._document_class.distinct(field, filter=filters)
        except Exception as e:
            self.logger.error(f"Error computing distinct '{field}': {e}")
            return []

    async def count(self, query: Optional[DataSourceQuery] = None) -> int:
        """Count entities matching query."""
        try:
            if query is None:
                return await self._repository.count()
            else:
                return await self._repository.count(self._convert_query(query))
        except Exception as e:
            self.logger.error(f"Error counting entities: {e}")
            return 0

    # Bulk Operations
    async def bulk_create(self, data_list: List[Dict[str, Any]]) -> BulkOperationResult:
        """Create multiple entities."""
        result = BulkOperationResult(total_count=len(data_list))

        try:
            created_entities = await self._repository.bulk_create(data_list)
            result.success_count = len(created_entities)

        except Exception as e:
            self.logger.error(f"Error in bulk create: {e}")
            result.error_count = len(data_list)
            result.errors.append(str(e))

        return result

    async def bulk_upsert(
        self, data_list: List[Dict[str, Any]], match_fields: List[str]
    ) -> BulkOperationResult:
        """Upsert multiple entities. Match on match_fields, update the rest."""
        result = BulkOperationResult(total_count=len(data_list))

        try:
            upserted = await self._repository.bulk_upsert(data_list, match_fields)
            result.success_count = len(upserted)

        except Exception as e:
            self.logger.error(f"Error in bulk upsert: {e}")
            result.error_count = len(data_list)
            result.errors.append(str(e))

        return result

    async def bulk_update(
        self, updates: Dict[K, Dict[str, Any]]
    ) -> BulkOperationResult:
        """Update multiple entities."""
        result = BulkOperationResult(total_count=len(updates))

        for entity_id, update_data in updates.items():
            try:
                updated_entity = await self.update(entity_id, update_data)
                if updated_entity:
                    result.success_count += 1
                else:
                    result.error_count += 1
                    result.errors.append(f"Failed to update entity {entity_id}")

            except Exception as e:
                result.error_count += 1
                result.errors.append(f"Error updating entity {entity_id}: {str(e)}")

        return result

    async def bulk_delete(self, ids: List[K]) -> BulkOperationResult:
        """Delete multiple entities."""
        result = BulkOperationResult(total_count=len(ids))

        for entity_id in ids:
            try:
                if await self.delete(entity_id):
                    result.success_count += 1
                else:
                    result.error_count += 1
                    result.errors.append(f"Failed to delete entity {entity_id}")

            except Exception as e:
                result.error_count += 1
                result.errors.append(f"Error deleting entity {entity_id}: {str(e)}")

        return result

    async def bulk_get(self, ids: List[K]) -> Dict[K, Optional[T]]:
        """Get multiple entities by IDs."""
        result = {}

        for entity_id in ids:
            try:
                entity = await self.get_by_id(entity_id)
                result[entity_id] = entity
            except Exception as e:
                self.logger.error(f"Error getting entity {entity_id}: {e}")
                result[entity_id] = None

        return result

    async def delete_all(self) -> int:
        """Delete all entities from the data source."""
        try:
            # Get all entities first to count them
            all_entities = await self._repository.get_all()
            total_count = len(all_entities)

            if total_count == 0:
                self.logger.info(
                    f"No entities to delete for {self._document_class.__name__}"
                )
                return 0

            # Delete all entities using the document class directly
            # This is more efficient than deleting one by one
            await self._document_class.delete_all()

            self.logger.info(
                f"Deleted all {total_count} entities from {self._document_class.__name__}"
            )
            return total_count

        except Exception as e:
            self.logger.error(
                f"Error deleting all entities from {self._document_class.__name__}: {e}"
            )
            raise

    # Advanced Operations
    async def find(self, query: DataSourceQuery) -> List[T]:
        """Find entities by complex query."""
        try:
            if query.limit is not None or query.skip is not None:
                return await self._repository.find_with_pagination(
                    query=self._convert_query(query),
                    skip=query.skip if query.skip is not None else 0,
                    limit=query.limit if query.limit is not None else 0,
                    sort_by=query.sort_by,
                    sort_order=query.sort_order,
                )
            repo_query = self._convert_query(query)
            if repo_query is None:
                return await self._repository.get_all()
            return await self._repository.find(repo_query)
        except Exception as e:
            self.logger.error(f"Error finding entities: {e}")
            return []

    async def find_one(self, query: DataSourceQuery) -> Optional[T]:
        """Find one entity by query."""
        try:
            return await self._repository.find_one(self._convert_query(query))
        except Exception as e:
            self.logger.error(f"Error finding entity: {e}")
            return None

    async def aggregate(self, pipeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute aggregation pipeline."""
        try:
            return await self._repository.aggregate(pipeline)
        except Exception as e:
            self.logger.error(f"Error executing aggregation: {e}")
            return []

    async def health_check(self) -> Dict[str, Any]:
        """Check MongoDB data source health."""
        try:
            # Try to count documents to test connection
            count = await self._repository.count()

            return {
                "status": "healthy",
                "backend": "mongodb",
                "document_class": self._document_class.__name__,
                "total_documents": count,
                "connection": "active",
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "backend": "mongodb",
                "document_class": self._document_class.__name__,
                "error": str(e),
                "connection": "failed",
            }

    def _convert_query(self, query: DataSourceQuery):
        """Convert DataSourceQuery to repository query format."""
        if not query:
            return None

        # Import here to avoid circular imports
        from common_utils.models import QueryFilter, RepositoryQuery

        filters = []
        if query.filters:
            for field, value in query.filters.items():
                if isinstance(value, dict):
                    # Handle complex filter operations
                    for op, op_value in value.items():
                        filters.append(
                            QueryFilter(field=field, operator=op, value=op_value)
                        )
                else:
                    # Simple equality filter
                    filters.append(QueryFilter(field=field, operator="eq", value=value))

        # Return RepositoryQuery even if no filters, if there's sorting or pagination
        # This ensures sorting and pagination are preserved
        if filters or query.sort_by or query.limit or query.skip:
            return RepositoryQuery(
                filters=filters if filters else None,
                sort_by=query.sort_by,
                sort_order=query.sort_order,
                skip=query.skip or 0,
                limit=query.limit,
            )

        # Return None only if there are no filters, sorting, or pagination
        return None
