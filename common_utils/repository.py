"""
Repository pattern implementation for MongoDB with Beanie ODM.

This module provides a generic repository pattern implementation that can be used
with any Beanie document class, providing type-safe database operations.
"""

import traceback
from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Optional, TypeVar

from beanie import Document

from common_utils.logger import get_logger
from common_utils.models import AggregationPipeline, RepositoryQuery

logger = get_logger(__name__)

T = TypeVar("T", bound=Document)
U = TypeVar("U")  # Generic type for any entity


class IMongoDocumentRepository(ABC, Generic[T]):
    """Repository interface for MongoDB documents with query operations."""

    @abstractmethod
    async def create(self, data: Dict[str, Any]) -> T:
        """Create a new document."""
        pass

    @abstractmethod
    async def get_by_id(self, document_id: str) -> Optional[T]:
        """Get document by ID."""
        pass

    @abstractmethod
    async def get_all(self) -> List[T]:
        """Get all documents."""
        pass

    @abstractmethod
    async def update(self, document_id: str, data: Dict[str, Any]) -> Optional[T]:
        """Update document by ID."""
        pass

    @abstractmethod
    async def delete(self, document_id: str) -> bool:
        """Delete document by ID."""
        pass

    @abstractmethod
    async def find(self, query: RepositoryQuery) -> List[T]:
        """Find documents by query."""
        pass

    @abstractmethod
    async def find_one(self, query: RepositoryQuery) -> Optional[T]:
        """Find one document by query."""
        pass

    @abstractmethod
    async def count(self, query: Optional[RepositoryQuery] = None) -> int:
        """Count documents by query."""
        pass

    @abstractmethod
    async def distinct(
        self, field: str, query: Optional[RepositoryQuery] = None
    ) -> List[str]:
        """Get distinct values for a field."""
        pass


class MongoDocumentRepository(IMongoDocumentRepository[T]):
    """Base repository implementation using Beanie ODM."""

    def __init__(self, document_class: type[T], mongo_client=None):
        self.document_class = document_class
        self._mongo_client = mongo_client

    def _get_mongo_database(self):
        """Get MongoDB database instance from injected client."""
        if self._mongo_client and hasattr(self._mongo_client, "database"):
            return self._mongo_client.database

        raise RuntimeError(
            "MongoDB client not injected. Please provide mongo_client parameter."
        )

    async def create(self, data: Dict[str, Any]) -> T:
        """Create a new document."""
        try:
            document = self.document_class(**data)
            await document.insert()
            return document
        except Exception as e:
            logger.error(f"MongoDocumentRepository: Error creating document: {e}")
            logger.error(f"BaseRepository: Full traceback: {traceback.format_exc()}")
            raise

    async def get_by_id(self, document_id: str) -> Optional[T]:
        """Get document by ID."""
        # Convert string ID to PydanticObjectId if needed
        from bson import ObjectId

        if isinstance(document_id, str):
            try:
                # Try to convert string to ObjectId
                object_id = ObjectId(document_id)
                result = await self.document_class.get(object_id)
            except Exception:
                # If conversion fails, try to find by string ID using find_one
                result = await self.document_class.find_one({"_id": document_id})
        else:
            result = await self.document_class.get(document_id)
        return result

    async def get_all(self) -> List[T]:
        """Get all documents."""
        result = await self.document_class.find_all().to_list()
        return result

    async def update(self, document_id: str, data: Dict[str, Any]) -> Optional[T]:
        """Update document by ID."""
        # Convert string ID to PydanticObjectId if needed
        from bson import ObjectId

        if isinstance(document_id, str):
            try:
                # Try to convert string to ObjectId
                object_id = ObjectId(document_id)
                document = await self.document_class.get(object_id)
            except Exception:
                # If conversion fails, try to find by string ID using find_one
                document = await self.document_class.find_one({"_id": document_id})
        else:
            document = await self.document_class.get(document_id)
        if document:
            for key, value in data.items():
                setattr(document, key, value)
            if hasattr(document, "update_timestamp"):
                await document.update_timestamp()
            result = await document.save()
            return result
        return None

    async def delete(self, document_id: str) -> bool:
        """Delete document by ID."""
        try:
            # Convert string ID to PydanticObjectId if needed
            from bson import ObjectId

            if isinstance(document_id, str):
                try:
                    # Try to convert string to ObjectId
                    object_id = ObjectId(document_id)
                    document = await self.document_class.get(object_id)
                except Exception:
                    # If conversion fails, try to find by string ID using find_one
                    document = await self.document_class.find_one({"_id": document_id})
            else:
                document = await self.document_class.get(document_id)
            if document:
                logger.debug(
                    f"MongoDocumentRepository: Found document with ID {document_id}, attempting deletion"
                )
                await document.delete()
                logger.debug(
                    f"MongoDocumentRepository: Document with ID {document_id} deleted successfully"
                )
                return True
            else:
                logger.warning(
                    f"MongoDocumentRepository: Document with ID {document_id} not found for deletion"
                )
                return False
        except Exception as e:
            logger.error(
                f"MongoDocumentRepository: Error deleting document with ID {document_id}: {e}"
            )
            logger.exception(
                "MongoDocumentRepository: Full traceback for delete error:"
            )
            return False

    async def find(self, query: RepositoryQuery) -> List[T]:
        """Find documents by query."""
        # Convert RepositoryQuery to MongoDB query
        mongo_query = self._convert_query_to_mongo(query)
        cursor = self.document_class.find(mongo_query)

        # Apply sorting if specified
        # Beanie sort expects a list of tuples: [(field, direction)]
        if query.sort_by:
            sort_direction = 1 if query.sort_order >= 0 else -1
            cursor = cursor.sort([(query.sort_by, sort_direction)])

        result = await cursor.to_list()
        return result

    async def find_one(self, query: RepositoryQuery) -> Optional[T]:
        """Find one document by query."""
        # Convert RepositoryQuery to MongoDB query
        mongo_query = self._convert_query_to_mongo(query)
        result = await self.document_class.find_one(mongo_query)
        return result

    async def count(self, query: Optional[RepositoryQuery] = None) -> int:
        """Count documents by query."""
        if query:
            mongo_query = self._convert_query_to_mongo(query)
            result = await self.document_class.find(mongo_query).count()
            return result
        result = await self.document_class.find_all().count()
        return result

    async def distinct(
        self, field: str, query: Optional[RepositoryQuery] = None
    ) -> List[str]:
        """Get distinct values for a field."""
        if query:
            mongo_query = self._convert_query_to_mongo(query)
            result = await self.document_class.distinct(field, mongo_query)
            return result
        result = await self.document_class.distinct(field)
        return result

    async def exists(self, query: RepositoryQuery) -> bool:
        """Check if document exists."""
        mongo_query = self._convert_query_to_mongo(query)
        return await self.document_class.find_one(mongo_query) is not None

    async def bulk_create(self, data_list: List[Dict[str, Any]]) -> List[T]:
        """Create multiple documents."""
        documents = [self.document_class(**data) for data in data_list]
        await self.document_class.insert_many(documents)
        return documents

    async def bulk_upsert(
        self, data_list: List[Dict[str, Any]], match_fields: List[str]
    ) -> List[T]:
        """Upsert multiple documents. Match on match_fields, update the rest."""
        from pymongo import UpdateOne

        operations = []
        documents = []
        for data in data_list:
            doc = self.document_class(**data)
            documents.append(doc)
            filter_query = {field: data[field] for field in match_fields}
            # $set all fields except _id
            update_data = doc.model_dump(by_alias=True)
            update_data.pop("_id", None)
            operations.append(
                UpdateOne(filter_query, {"$set": update_data}, upsert=True)
            )

        if operations:
            collection = self.document_class.get_pymongo_collection()
            await collection.bulk_write(operations, ordered=False)

        return documents

    async def bulk_insert(self, documents: List[T]) -> List[str]:
        """Insert multiple documents and return their IDs."""
        await self.document_class.insert_many(documents)
        return [str(doc.id) for doc in documents]

    async def find_with_pagination(
        self,
        query: Optional[RepositoryQuery] = None,
        skip: int = 0,
        limit: int = 10,
        sort_by: Optional[str] = None,
        sort_order: int = 1,
    ) -> List[T]:
        """Find documents with pagination."""
        mongo_query = self._convert_query_to_mongo(query) if query else {}

        cursor = self.document_class.find(mongo_query).skip(skip).limit(limit)

        if sort_by:
            # MongoDB sort expects a list of tuples: [(field, direction)]
            # Convert sort_order to 1 (ascending) or -1 (descending)
            sort_direction = 1 if sort_order >= 0 else -1
            cursor = cursor.sort([(sort_by, sort_direction)])

        result = await cursor.to_list()
        return result

    async def aggregate(
        self, pipeline: AggregationPipeline | List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Execute aggregation pipeline."""
        # Handle both AggregationPipeline objects and raw MongoDB pipeline lists
        if isinstance(pipeline, list):
            # Raw MongoDB pipeline - use directly
            mongo_pipeline = pipeline
        else:
            # AggregationPipeline object - convert to MongoDB format
            mongo_pipeline = self._convert_pipeline_to_mongo(pipeline)

        # Execute aggregation using the underlying Motor collection
        # In Beanie, we need to access the collection through the injected MongoDB client

        # Get the database and collection
        if self._mongo_client and hasattr(self._mongo_client, "database"):
            database = self._mongo_client.database
        else:
            raise RuntimeError(
                "MongoDB client not injected. Please provide mongo_client parameter."
            )

        collection_name = self.document_class.Settings.name
        collection = database[collection_name]

        # Execute aggregation and convert cursor to list
        cursor = collection.aggregate(mongo_pipeline)
        result = await cursor.to_list(length=None)
        return result

    def _convert_query_to_mongo(self, query: RepositoryQuery) -> Dict[str, Any]:
        """Convert RepositoryQuery to MongoDB query format."""
        mongo_query = {}

        if query.filters:
            for filter_item in query.filters:
                field = filter_item.field
                operator = filter_item.operator
                value = filter_item.value

                if operator == "eq":
                    mongo_query[field] = value
                elif operator == "ne":
                    mongo_query[field] = {"$ne": value}
                elif operator == "gt":
                    mongo_query[field] = {"$gt": value}
                elif operator == "lt":
                    mongo_query[field] = {"$lt": value}
                elif operator == "gte":
                    mongo_query[field] = {"$gte": value}
                elif operator == "lte":
                    mongo_query[field] = {"$lte": value}
                elif operator == "in":
                    mongo_query[field] = {"$in": value}
                elif operator == "nin":
                    mongo_query[field] = {"$nin": value}
                elif operator == "exists":
                    mongo_query[field] = {"$exists": value}
                elif operator == "regex":
                    if isinstance(value, dict) and "pattern" in value:
                        # Handle regex filter with pattern and options
                        mongo_query[field] = {
                            "$regex": value["pattern"],
                            "$options": value.get("options", "i"),
                        }
                    else:
                        # Handle simple regex pattern
                        mongo_query[field] = {"$regex": value}

        return mongo_query

    def _convert_pipeline_to_mongo(
        self, pipeline: AggregationPipeline
    ) -> List[Dict[str, Any]]:
        """Convert AggregationPipeline to MongoDB pipeline format."""
        mongo_pipeline = []

        for stage in pipeline.stages:
            stage_dict = {f"${stage.stage_type}": stage.stage_data}
            mongo_pipeline.append(stage_dict)

        return mongo_pipeline


class RepositoryFactory:
    """Factory for creating repository instances."""

    _repositories: Dict[str, MongoDocumentRepository] = {}

    @classmethod
    def get_repository(cls, document_class: type[T]) -> MongoDocumentRepository[T]:
        """Get or create a repository instance for the given document class."""
        class_name = document_class.__name__
        if class_name not in cls._repositories:
            cls._repositories[class_name] = MongoDocumentRepository(document_class)
        return cls._repositories[class_name]

    @classmethod
    def clear_cache(cls) -> None:
        """Clear the repository cache."""
        cls._repositories.clear()
