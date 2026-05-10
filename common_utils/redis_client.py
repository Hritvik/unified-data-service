"""
Centralized Redis client management.

This module provides a centralized Redis client with configurable serialization
strategies for different use cases, similar to how MongoDB is managed.
"""

import json
from abc import ABC, abstractmethod
from typing import (
    Any,
    AsyncIterator,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
)

from common_utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class ISerializationStrategy(ABC):
    """Interface for Redis serialization strategies."""

    @abstractmethod
    def serialize(self, data: Any) -> bytes:
        """Serialize data to bytes for Redis storage."""
        pass

    @abstractmethod
    def deserialize(self, data: bytes, target_type: Optional[Type[T]] = None) -> T:
        """Deserialize bytes from Redis to target type."""
        pass


class JsonSerializationStrategy(ISerializationStrategy):
    """JSON-based serialization strategy for general use cases."""

    def serialize(self, data: Any) -> bytes:
        """Serialize data to JSON bytes."""
        return json.dumps(data, default=str).encode("utf-8")

    def deserialize(self, data: bytes, target_type: Optional[Type[T]] = None) -> T:
        """Deserialize JSON bytes to target type."""
        json_data = json.loads(data.decode("utf-8"))
        if target_type and hasattr(target_type, "model_validate"):
            # Pydantic model
            return target_type.model_validate(json_data)
        return json_data


class PydanticSerializationStrategy(ISerializationStrategy):
    """Pydantic-specific serialization strategy for model objects."""

    def serialize(self, data: Any) -> bytes:
        """Serialize Pydantic model to JSON bytes."""
        if hasattr(data, "model_dump"):
            return data.model_dump_json().encode("utf-8")
        return json.dumps(data, default=str).encode("utf-8")

    def deserialize(self, data: bytes, target_type: Optional[Type[T]] = None) -> T:
        """Deserialize JSON bytes to Pydantic model."""
        json_data = json.loads(data.decode("utf-8"))
        if target_type and hasattr(target_type, "model_validate"):
            return target_type.model_validate(json_data)
        return json_data


class RedisClient:
    """
    Centralized Redis client with configurable serialization strategies.

    This client provides a unified interface for Redis operations with support
    for different serialization strategies based on use case requirements.
    """

    def __init__(
        self,
        redis_client: Any,
        serialization_strategy: Optional[ISerializationStrategy] = None,
        key_prefix: str = "",
    ):
        """
        Initialize the Redis client.

        Args:
            redis_client: The underlying Redis client instance
            serialization_strategy: Serialization strategy to use
            key_prefix: Prefix for all keys
        """
        self._redis_client = redis_client
        self._serialization_strategy = (
            serialization_strategy or JsonSerializationStrategy()
        )
        self._key_prefix = key_prefix
        self.logger = logger

    def _get_key(self, key: str) -> str:
        """Get the full Redis key with prefix."""
        return f"{self._key_prefix}{key}" if self._key_prefix else key

    async def get(self, key: str, target_type: Optional[Type[T]] = None) -> Optional[T]:
        """Get value by key."""
        try:
            redis_key = self._get_key(key)
            data = await self._redis_client.get(redis_key)
            if data is None:
                return None
            return self._serialization_strategy.deserialize(data, target_type)
        except Exception as e:
            self.logger.error(f"Error getting key {key}: {e}")
            return None

    async def set(
        self, key: str, value: Any, ttl_seconds: Optional[int] = None
    ) -> bool:
        """Set value by key with optional TTL."""
        try:
            redis_key = self._get_key(key)
            data = self._serialization_strategy.serialize(value)

            if ttl_seconds:
                await self._redis_client.set(redis_key, data, ex=ttl_seconds)
            else:
                await self._redis_client.set(redis_key, data)
            return True
        except Exception as e:
            self.logger.error(f"Error setting key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key."""
        try:
            redis_key = self._get_key(key)
            result = await self._redis_client.delete(redis_key)
            return result > 0
        except Exception as e:
            self.logger.error(f"Error deleting key {key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        try:
            redis_key = self._get_key(key)
            result = await self._redis_client.exists(redis_key)
            return result > 0
        except Exception as e:
            self.logger.error(f"Error checking existence of key {key}: {e}")
            return False

    async def keys(self, pattern: str = "*") -> list[str]:
        """Get all keys matching pattern."""
        try:
            search_pattern = (
                f"{self._key_prefix}{pattern}" if self._key_prefix else pattern
            )
            keys = await self._redis_client.keys(search_pattern)
            # Remove prefix from returned keys
            if self._key_prefix:
                return [
                    key.decode("utf-8").replace(self._key_prefix, "") for key in keys
                ]
            return [key.decode("utf-8") for key in keys]
        except Exception as e:
            self.logger.error(f"Error getting keys with pattern {pattern}: {e}")
            return []

    async def get_all(
        self, pattern: str = "*", target_type: Optional[Type[T]] = None
    ) -> Dict[str, T]:
        """Get all key-value pairs matching pattern."""
        try:
            keys = await self.keys(pattern)
            result = {}
            for key in keys:
                value = await self.get(key, target_type)
                if value is not None:
                    result[key] = value
            return result
        except Exception as e:
            self.logger.error(f"Error getting all values with pattern {pattern}: {e}")
            return {}

    async def count(self, pattern: str = "*") -> int:
        """Count keys matching pattern."""
        try:
            keys = await self.keys(pattern)
            return len(keys)
        except Exception as e:
            self.logger.error(f"Error counting keys with pattern {pattern}: {e}")
            return 0

    async def clear(self, pattern: str = "*") -> int:
        """Clear all keys matching pattern."""
        try:
            keys = await self.keys(pattern)
            if not keys:
                return 0

            # Convert back to full keys for deletion
            full_keys = [self._get_key(key) for key in keys]
            result = await self._redis_client.delete(*full_keys)
            self.logger.info(f"Cleared {result} keys from Redis")
            return result
        except Exception as e:
            self.logger.error(f"Error clearing keys with pattern {pattern}: {e}")
            return 0

    async def ping(self) -> bool:
        """Test Redis connection."""
        try:
            result = await self._redis_client.ping()
            return result is True
        except Exception as e:
            self.logger.error(f"Redis ping failed: {e}")
            return False

    def get_info(self) -> Dict[str, Any]:
        """Get Redis client information."""
        return {
            "key_prefix": self._key_prefix,
            "serialization_strategy": self._serialization_strategy.__class__.__name__,
            "connected": True,  # We'll implement proper connection checking
        }

    # === PHASE 1: CORE REDIS DATA TYPES ===

    # === HASH OPERATIONS ===
    async def hset(self, key: str, field: str, value: Any) -> bool:
        """Set field in hash."""
        try:
            redis_key = self._get_key(key)
            serialized_value = self._serialization_strategy.serialize(value)
            result = await self._redis_client.hset(redis_key, field, serialized_value)
            return result == 1
        except Exception as e:
            self.logger.error(f"Error setting hash field {key}:{field}: {e}")
            return False

    async def hget(
        self, key: str, field: str, target_type: Optional[Type[T]] = None
    ) -> Optional[T]:
        """Get field from hash."""
        try:
            redis_key = self._get_key(key)
            data = await self._redis_client.hget(redis_key, field)
            if data is None:
                return None
            return self._serialization_strategy.deserialize(data, target_type)
        except Exception as e:
            self.logger.error(f"Error getting hash field {key}:{field}: {e}")
            return None

    async def hgetall(
        self, key: str, target_type: Optional[Type[T]] = None
    ) -> Dict[str, T]:
        """Get all fields from hash."""
        try:
            redis_key = self._get_key(key)
            data = await self._redis_client.hgetall(redis_key)
            result = {}
            for field, value in data.items():
                if isinstance(field, bytes):
                    field = field.decode("utf-8")
                deserialized_value = self._serialization_strategy.deserialize(
                    value, target_type
                )
                result[field] = deserialized_value
            return result
        except Exception as e:
            self.logger.error(f"Error getting all hash fields {key}: {e}")
            return {}

    async def hdel(self, key: str, *fields: str) -> int:
        """Delete fields from hash."""
        try:
            redis_key = self._get_key(key)
            return await self._redis_client.hdel(redis_key, *fields)
        except Exception as e:
            self.logger.error(f"Error deleting hash fields {key}: {e}")
            return 0

    async def hexists(self, key: str, field: str) -> bool:
        """Check if field exists in hash."""
        try:
            redis_key = self._get_key(key)
            result = await self._redis_client.hexists(redis_key, field)
            return result == 1
        except Exception as e:
            self.logger.error(f"Error checking hash field existence {key}:{field}: {e}")
            return False

    async def hkeys(self, key: str) -> List[str]:
        """Get all field names from hash."""
        try:
            redis_key = self._get_key(key)
            keys = await self._redis_client.hkeys(redis_key)
            return [
                key.decode("utf-8") if isinstance(key, bytes) else key for key in keys
            ]
        except Exception as e:
            self.logger.error(f"Error getting hash keys {key}: {e}")
            return []

    async def hlen(self, key: str) -> int:
        """Get number of fields in hash."""
        try:
            redis_key = self._get_key(key)
            return await self._redis_client.hlen(redis_key)
        except Exception as e:
            self.logger.error(f"Error getting hash length {key}: {e}")
            return 0

    # === LIST OPERATIONS ===
    async def lpush(self, key: str, *values: Any) -> int:
        """Push values to left of list."""
        try:
            redis_key = self._get_key(key)
            serialized_values = [
                self._serialization_strategy.serialize(value) for value in values
            ]
            return await self._redis_client.lpush(redis_key, *serialized_values)
        except Exception as e:
            self.logger.error(f"Error pushing to list {key}: {e}")
            return 0

    async def rpush(self, key: str, *values: Any) -> int:
        """Push values to right of list."""
        try:
            redis_key = self._get_key(key)
            serialized_values = [
                self._serialization_strategy.serialize(value) for value in values
            ]
            return await self._redis_client.rpush(redis_key, *serialized_values)
        except Exception as e:
            self.logger.error(f"Error pushing to list {key}: {e}")
            return 0

    async def lpop(
        self, key: str, target_type: Optional[Type[T]] = None
    ) -> Optional[T]:
        """Pop value from left of list."""
        try:
            redis_key = self._get_key(key)
            data = await self._redis_client.lpop(redis_key)
            if data is None:
                return None
            return self._serialization_strategy.deserialize(data, target_type)
        except Exception as e:
            self.logger.error(f"Error popping from list {key}: {e}")
            return None

    async def rpop(
        self, key: str, target_type: Optional[Type[T]] = None
    ) -> Optional[T]:
        """Pop value from right of list."""
        try:
            redis_key = self._get_key(key)
            data = await self._redis_client.rpop(redis_key)
            if data is None:
                return None
            return self._serialization_strategy.deserialize(data, target_type)
        except Exception as e:
            self.logger.error(f"Error popping from list {key}: {e}")
            return None

    async def lrange(
        self, key: str, start: int, end: int, target_type: Optional[Type[T]] = None
    ) -> List[T]:
        """Get range of values from list."""
        try:
            redis_key = self._get_key(key)
            data = await self._redis_client.lrange(redis_key, start, end)
            return [
                self._serialization_strategy.deserialize(item, target_type)
                for item in data
            ]
        except Exception as e:
            self.logger.error(f"Error getting list range {key}: {e}")
            return []

    async def llen(self, key: str) -> int:
        """Get length of list."""
        try:
            redis_key = self._get_key(key)
            return await self._redis_client.llen(redis_key)
        except Exception as e:
            self.logger.error(f"Error getting list length {key}: {e}")
            return 0

    async def lrem(self, key: str, count: int, value: Any) -> int:
        """Remove occurrences of value from list."""
        try:
            redis_key = self._get_key(key)
            serialized_value = self._serialization_strategy.serialize(value)
            return await self._redis_client.lrem(redis_key, count, serialized_value)
        except Exception as e:
            self.logger.error(f"Error removing from list {key}: {e}")
            return 0

    # === SET OPERATIONS ===
    async def sadd(self, key: str, *values: Any) -> int:
        """Add values to set."""
        try:
            redis_key = self._get_key(key)
            serialized_values = [
                self._serialization_strategy.serialize(value) for value in values
            ]
            return await self._redis_client.sadd(redis_key, *serialized_values)
        except Exception as e:
            self.logger.error(f"Error adding to set {key}: {e}")
            return 0

    async def srem(self, key: str, *values: Any) -> int:
        """Remove values from set."""
        try:
            redis_key = self._get_key(key)
            serialized_values = [
                self._serialization_strategy.serialize(value) for value in values
            ]
            return await self._redis_client.srem(redis_key, *serialized_values)
        except Exception as e:
            self.logger.error(f"Error removing from set {key}: {e}")
            return 0

    async def smembers(self, key: str, target_type: Optional[Type[T]] = None) -> Set[T]:
        """Get all members of set."""
        try:
            redis_key = self._get_key(key)
            data = await self._redis_client.smembers(redis_key)
            return {
                self._serialization_strategy.deserialize(item, target_type)
                for item in data
            }
        except Exception as e:
            self.logger.error(f"Error getting set members {key}: {e}")
            return set()

    async def sismember(self, key: str, value: Any) -> bool:
        """Check if value is member of set."""
        try:
            redis_key = self._get_key(key)
            serialized_value = self._serialization_strategy.serialize(value)
            result = await self._redis_client.sismember(redis_key, serialized_value)
            return result == 1
        except Exception as e:
            self.logger.error(f"Error checking set membership {key}: {e}")
            return False

    async def scard(self, key: str) -> int:
        """Get cardinality of set."""
        try:
            redis_key = self._get_key(key)
            return await self._redis_client.scard(redis_key)
        except Exception as e:
            self.logger.error(f"Error getting set cardinality {key}: {e}")
            return 0

    async def spop(
        self, key: str, count: int = 1, target_type: Optional[Type[T]] = None
    ) -> Union[T, Set[T], None]:
        """Pop random members from set."""
        try:
            redis_key = self._get_key(key)
            if count == 1:
                data = await self._redis_client.spop(redis_key)
                if data is None:
                    return None
                return self._serialization_strategy.deserialize(data, target_type)
            else:
                data = await self._redis_client.spop(redis_key, count)
                if not data:
                    return set()
                return {
                    self._serialization_strategy.deserialize(item, target_type)
                    for item in data
                }
        except Exception as e:
            self.logger.error(f"Error popping from set {key}: {e}")
            return None if count == 1 else set()

    # === SORTED SET OPERATIONS ===
    async def zadd(self, key: str, mapping: Dict[Any, float]) -> int:
        """Add members to sorted set with scores."""
        try:
            redis_key = self._get_key(key)
            serialized_mapping = {
                self._serialization_strategy.serialize(member): score
                for member, score in mapping.items()
            }
            return await self._redis_client.zadd(redis_key, serialized_mapping)
        except Exception as e:
            self.logger.error(f"Error adding to sorted set {key}: {e}")
            return 0

    async def zrange(
        self,
        key: str,
        start: int,
        end: int,
        withscores: bool = False,
        target_type: Optional[Type[T]] = None,
    ) -> Union[List[T], List[Tuple[T, float]]]:
        """Get range of members from sorted set."""
        try:
            redis_key = self._get_key(key)
            if withscores:
                data = await self._redis_client.zrange(
                    redis_key, start, end, withscores=True
                )
                return [
                    (
                        self._serialization_strategy.deserialize(member, target_type),
                        score,
                    )
                    for member, score in data
                ]
            else:
                data = await self._redis_client.zrange(redis_key, start, end)
                return [
                    self._serialization_strategy.deserialize(member, target_type)
                    for member in data
                ]
        except Exception as e:
            self.logger.error(f"Error getting sorted set range {key}: {e}")
            return [] if not withscores else []

    async def zrevrange(
        self,
        key: str,
        start: int,
        end: int,
        withscores: bool = False,
        target_type: Optional[Type[T]] = None,
    ) -> Union[List[T], List[Tuple[T, float]]]:
        """Get reverse range of members from sorted set."""
        try:
            redis_key = self._get_key(key)
            if withscores:
                data = await self._redis_client.zrevrange(
                    redis_key, start, end, withscores=True
                )
                return [
                    (
                        self._serialization_strategy.deserialize(member, target_type),
                        score,
                    )
                    for member, score in data
                ]
            else:
                data = await self._redis_client.zrevrange(redis_key, start, end)
                return [
                    self._serialization_strategy.deserialize(member, target_type)
                    for member in data
                ]
        except Exception as e:
            self.logger.error(f"Error getting reverse sorted set range {key}: {e}")
            return [] if not withscores else []

    async def zrank(self, key: str, member: Any) -> Optional[int]:
        """Get rank of member in sorted set."""
        try:
            redis_key = self._get_key(key)
            serialized_member = self._serialization_strategy.serialize(member)
            result = await self._redis_client.zrank(redis_key, serialized_member)
            return result
        except Exception as e:
            self.logger.error(f"Error getting sorted set rank {key}: {e}")
            return None

    async def zrem(self, key: str, *members: Any) -> int:
        """Remove members from sorted set."""
        try:
            redis_key = self._get_key(key)
            serialized_members = [
                self._serialization_strategy.serialize(member) for member in members
            ]
            return await self._redis_client.zrem(redis_key, *serialized_members)
        except Exception as e:
            self.logger.error(f"Error removing from sorted set {key}: {e}")
            return 0

    async def zcard(self, key: str) -> int:
        """Get cardinality of sorted set."""
        try:
            redis_key = self._get_key(key)
            return await self._redis_client.zcard(redis_key)
        except Exception as e:
            self.logger.error(f"Error getting sorted set cardinality {key}: {e}")
            return 0

    async def zscore(self, key: str, member: Any) -> Optional[float]:
        """Get score of member in sorted set."""
        try:
            redis_key = self._get_key(key)
            serialized_member = self._serialization_strategy.serialize(member)
            result = await self._redis_client.zscore(redis_key, serialized_member)
            return result
        except Exception as e:
            self.logger.error(f"Error getting sorted set score {key}: {e}")
            return None

    # === PHASE 2: ADVANCED REDIS OPERATIONS ===

    # === ATOMIC OPERATIONS (PIPELINE) ===
    async def pipeline(self) -> "RedisPipeline":
        """Create a Redis pipeline for atomic operations."""
        return RedisPipeline(
            self._redis_client, self._serialization_strategy, self._key_prefix
        )

    async def multi_exec(self, commands: List[Tuple[str, List[Any]]]) -> List[Any]:
        """
        Execute multiple commands atomically.

        Args:
            commands: List of (command, args) tuples

        Returns:
            List of results from each command
        """
        try:
            pipe = self._redis_client.pipeline()
            for command, args in commands:
                getattr(pipe, command)(*args)
            return await pipe.execute()
        except Exception as e:
            self.logger.error(f"Error executing atomic operations: {e}")
            return []

    # === LUA SCRIPT EXECUTION ===
    async def eval(self, script: str, keys: List[str], args: List[Any]) -> Any:
        """
        Execute Lua script.

        Args:
            script: Lua script to execute
            keys: List of keys used in script
            args: List of arguments for script

        Returns:
            Result of script execution
        """
        try:
            # Serialize arguments
            serialized_args = [
                self._serialization_strategy.serialize(arg) for arg in args
            ]

            # Add key prefix to keys
            prefixed_keys = [self._get_key(key) for key in keys]

            result = await self._redis_client.eval(
                script, len(prefixed_keys), *prefixed_keys, *serialized_args
            )

            # Deserialize result if it's a string
            if isinstance(result, bytes):
                try:
                    return self._serialization_strategy.deserialize(result)
                except Exception:
                    return result.decode("utf-8")
            return result
        except Exception as e:
            self.logger.error(f"Error executing Lua script: {e}")
            return None

    async def evalsha(self, sha: str, keys: List[str], args: List[Any]) -> Any:
        """
        Execute Lua script by SHA.

        Args:
            sha: SHA hash of the script
            keys: List of keys used in script
            args: List of arguments for script

        Returns:
            Result of script execution
        """
        try:
            # Serialize arguments
            serialized_args = [
                self._serialization_strategy.serialize(arg) for arg in args
            ]

            # Add key prefix to keys
            prefixed_keys = [self._get_key(key) for key in keys]

            result = await self._redis_client.evalsha(
                sha, len(prefixed_keys), *prefixed_keys, *serialized_args
            )

            # Deserialize result if it's a string
            if isinstance(result, bytes):
                try:
                    return self._serialization_strategy.deserialize(result)
                except Exception:
                    return result.decode("utf-8")
            return result
        except Exception as e:
            self.logger.error(f"Error executing Lua script by SHA: {e}")
            return None

    async def script_load(self, script: str) -> str:
        """Load Lua script and return SHA."""
        try:
            return await self._redis_client.script_load(script)
        except Exception as e:
            self.logger.error(f"Error loading Lua script: {e}")
            return ""

    # === PUB/SUB OPERATIONS ===
    async def publish(self, channel: str, message: Any) -> int:
        """
        Publish message to channel.

        Args:
            channel: Channel name
            message: Message to publish

        Returns:
            Number of subscribers that received the message
        """
        try:
            serialized_message = self._serialization_strategy.serialize(message)
            return await self._redis_client.publish(channel, serialized_message)
        except Exception as e:
            self.logger.error(f"Error publishing to channel {channel}: {e}")
            return 0

    async def subscribe(self, *channels: str) -> "RedisPubSub":
        """
        Subscribe to channels.

        Args:
            channels: Channel names to subscribe to

        Returns:
            RedisPubSub instance for handling messages
        """
        try:
            pubsub = self._redis_client.pubsub()
            await pubsub.subscribe(*channels)
            return RedisPubSub(pubsub, self._serialization_strategy)
        except Exception as e:
            self.logger.error(f"Error subscribing to channels {channels}: {e}")
            return None

    async def psubscribe(self, *patterns: str) -> "RedisPubSub":
        """
        Subscribe to channel patterns.

        Args:
            patterns: Channel patterns to subscribe to

        Returns:
            RedisPubSub instance for handling messages
        """
        try:
            pubsub = self._redis_client.pubsub()
            await pubsub.psubscribe(*patterns)
            return RedisPubSub(pubsub, self._serialization_strategy)
        except Exception as e:
            self.logger.error(f"Error subscribing to patterns {patterns}: {e}")
            return None

    # === MONITORING AND METRICS ===
    async def info(self, section: Optional[str] = None) -> Dict[str, Any]:
        """
        Get Redis server information.

        Args:
            section: Optional section to get info for

        Returns:
            Dictionary of Redis server information
        """
        try:
            if section:
                info = await self._redis_client.info(section)
            else:
                info = await self._redis_client.info()

            # Convert bytes to strings if needed
            if isinstance(info, dict):
                result = {}
                for key, value in info.items():
                    if isinstance(key, bytes):
                        key = key.decode("utf-8")
                    if isinstance(value, bytes):
                        value = value.decode("utf-8")
                    result[key] = value
                return result
            return info
        except Exception as e:
            self.logger.error(f"Error getting Redis info: {e}")
            return {}

    async def memory_usage(self, key: str) -> int:
        """Get memory usage of a key in bytes."""
        try:
            redis_key = self._get_key(key)
            return await self._redis_client.memory_usage(redis_key)
        except Exception as e:
            self.logger.error(f"Error getting memory usage for key {key}: {e}")
            return 0

    async def slowlog_get(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get Redis slow log entries."""
        try:
            return await self._redis_client.slowlog_get(count)
        except Exception as e:
            self.logger.error(f"Error getting slow log: {e}")
            return []

    async def config_get(self, pattern: str = "*") -> Dict[str, str]:
        """Get Redis configuration parameters."""
        try:
            config = await self._redis_client.config_get(pattern)
            # Convert bytes to strings
            result = {}
            for key, value in config.items():
                if isinstance(key, bytes):
                    key = key.decode("utf-8")
                if isinstance(value, bytes):
                    value = value.decode("utf-8")
                result[key] = value
            return result
        except Exception as e:
            self.logger.error(f"Error getting Redis config: {e}")
            return {}

    async def dbsize(self) -> int:
        """Get number of keys in current database."""
        try:
            return await self._redis_client.dbsize()
        except Exception as e:
            self.logger.error(f"Error getting database size: {e}")
            return 0

    # === CONNECTION MANAGEMENT ===
    async def flushdb(self) -> bool:
        """Flush current database."""
        try:
            await self._redis_client.flushdb()
            return True
        except Exception as e:
            self.logger.error(f"Error flushing database: {e}")
            return False

    async def flushall(self) -> bool:
        """Flush all databases."""
        try:
            await self._redis_client.flushall()
            return True
        except Exception as e:
            self.logger.error(f"Error flushing all databases: {e}")
            return False

    async def save(self) -> bool:
        """Save Redis database to disk."""
        try:
            await self._redis_client.save()
            return True
        except Exception as e:
            self.logger.error(f"Error saving database: {e}")
            return False

    async def bgsave(self) -> bool:
        """Save Redis database to disk in background."""
        try:
            await self._redis_client.bgsave()
            return True
        except Exception as e:
            self.logger.error(f"Error background saving database: {e}")
            return False

    async def lastsave(self) -> int:
        """Get timestamp of last save."""
        try:
            return await self._redis_client.lastsave()
        except Exception as e:
            self.logger.error(f"Error getting last save time: {e}")
            return 0

    async def close(self) -> None:
        """Close Redis connection."""
        try:
            if hasattr(self._redis_client, "close"):
                await self._redis_client.close()
            elif hasattr(self._redis_client, "aclose"):
                await self._redis_client.aclose()
            self.logger.info("Redis connection closed")
        except Exception as e:
            self.logger.error(f"Error closing Redis connection: {e}")


class RedisPipeline:
    """Redis pipeline for atomic operations."""

    def __init__(
        self,
        redis_client: Any,
        serialization_strategy: ISerializationStrategy,
        key_prefix: str = "",
    ):
        self._redis_client = redis_client
        self._serialization_strategy = serialization_strategy
        self._key_prefix = key_prefix
        self._pipeline = redis_client.pipeline()
        self.logger = logger

    def _get_key(self, key: str) -> str:
        """Get the full Redis key with prefix."""
        return f"{self._key_prefix}{key}" if self._key_prefix else key

    def set(
        self, key: str, value: Any, ttl_seconds: Optional[int] = None
    ) -> "RedisPipeline":
        """Add SET command to pipeline."""
        redis_key = self._get_key(key)
        serialized_value = self._serialization_strategy.serialize(value)
        if ttl_seconds:
            self._pipeline.set(redis_key, serialized_value, ex=ttl_seconds)
        else:
            self._pipeline.set(redis_key, serialized_value)
        return self

    def get(self, key: str) -> "RedisPipeline":
        """Add GET command to pipeline."""
        redis_key = self._get_key(key)
        self._pipeline.get(redis_key)
        return self

    def delete(self, key: str) -> "RedisPipeline":
        """Add DELETE command to pipeline."""
        redis_key = self._get_key(key)
        self._pipeline.delete(redis_key)
        return self

    def hset(self, key: str, field: str, value: Any) -> "RedisPipeline":
        """Add HSET command to pipeline."""
        redis_key = self._get_key(key)
        serialized_value = self._serialization_strategy.serialize(value)
        self._pipeline.hset(redis_key, field, serialized_value)
        return self

    def hget(self, key: str, field: str) -> "RedisPipeline":
        """Add HGET command to pipeline."""
        redis_key = self._get_key(key)
        self._pipeline.hget(redis_key, field)
        return self

    def lpush(self, key: str, *values: Any) -> "RedisPipeline":
        """Add LPUSH command to pipeline."""
        redis_key = self._get_key(key)
        serialized_values = [
            self._serialization_strategy.serialize(value) for value in values
        ]
        self._pipeline.lpush(redis_key, *serialized_values)
        return self

    def rpush(self, key: str, *values: Any) -> "RedisPipeline":
        """Add RPUSH command to pipeline."""
        redis_key = self._get_key(key)
        serialized_values = [
            self._serialization_strategy.serialize(value) for value in values
        ]
        self._pipeline.rpush(redis_key, *serialized_values)
        return self

    def sadd(self, key: str, *values: Any) -> "RedisPipeline":
        """Add SADD command to pipeline."""
        redis_key = self._get_key(key)
        serialized_values = [
            self._serialization_strategy.serialize(value) for value in values
        ]
        self._pipeline.sadd(redis_key, *serialized_values)
        return self

    def zadd(self, key: str, mapping: Dict[Any, float]) -> "RedisPipeline":
        """Add ZADD command to pipeline."""
        redis_key = self._get_key(key)
        serialized_mapping = {
            self._serialization_strategy.serialize(member): score
            for member, score in mapping.items()
        }
        self._pipeline.zadd(redis_key, serialized_mapping)
        return self

    async def execute(self) -> List[Any]:
        """Execute all commands in pipeline."""
        try:
            results = await self._pipeline.execute()
            # Deserialize results
            deserialized_results = []
            for result in results:
                if isinstance(result, bytes):
                    try:
                        deserialized = self._serialization_strategy.deserialize(result)
                        deserialized_results.append(deserialized)
                    except Exception:
                        deserialized_results.append(result.decode("utf-8"))
                else:
                    deserialized_results.append(result)
            return deserialized_results
        except Exception as e:
            self.logger.error(f"Error executing pipeline: {e}")
            return []


class RedisPubSub:
    """Redis Pub/Sub handler."""

    def __init__(self, pubsub: Any, serialization_strategy: ISerializationStrategy):
        self._pubsub = pubsub
        self._serialization_strategy = serialization_strategy
        self.logger = logger

    async def get_message(
        self, timeout: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """Get next message from subscription."""
        try:
            message = await self._pubsub.get_message(timeout=timeout)
            if message is None:
                return None

            # Deserialize message data
            if message.get("data") and isinstance(message["data"], bytes):
                try:
                    message["data"] = self._serialization_strategy.deserialize(
                        message["data"]
                    )
                except Exception:
                    message["data"] = message["data"].decode("utf-8")

            return message
        except Exception as e:
            self.logger.error(f"Error getting pub/sub message: {e}")
            return None

    async def listen(self) -> AsyncIterator[Dict[str, Any]]:
        """Async iterator for listening to messages."""
        try:
            async for message in self._pubsub.listen():
                # Deserialize message data
                if message.get("data") and isinstance(message["data"], bytes):
                    try:
                        message["data"] = self._serialization_strategy.deserialize(
                            message["data"]
                        )
                    except Exception:
                        message["data"] = message["data"].decode("utf-8")
                yield message
        except Exception as e:
            self.logger.error(f"Error listening to pub/sub messages: {e}")

    async def unsubscribe(self, *channels: str) -> None:
        """Unsubscribe from channels."""
        try:
            await self._pubsub.unsubscribe(*channels)
        except Exception as e:
            self.logger.error(f"Error unsubscribing from channels {channels}: {e}")

    async def punsubscribe(self, *patterns: str) -> None:
        """Unsubscribe from channel patterns."""
        try:
            await self._pubsub.punsubscribe(*patterns)
        except Exception as e:
            self.logger.error(f"Error unsubscribing from patterns {patterns}: {e}")

    async def close(self) -> None:
        """Close pub/sub connection."""
        try:
            await self._pubsub.close()
        except Exception as e:
            self.logger.error(f"Error closing pub/sub connection: {e}")


class RedisClientFactory:
    """Factory for creating Redis clients with different configurations."""

    @staticmethod
    def create_redis_client(
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        ssl: bool = False,
        key_prefix: str = "",
        serialization_strategy: Optional[ISerializationStrategy] = None,
    ) -> RedisClient:
        """
        Create a Redis client with specified configuration.

        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            password: Redis password
            ssl: Whether to use SSL
            key_prefix: Prefix for all keys
            serialization_strategy: Serialization strategy to use

        Returns:
            Configured Redis client instance

        Raises:
            ImportError: If redis package is not installed
            Exception: If Redis connection fails
        """
        try:
            import redis.asyncio as redis
        except ImportError:
            raise ImportError(
                "redis package is required for Redis backend. Install with: pip install redis"
            )

        logger.info(f"Creating Redis client for {host}:{port} (db={db})")

        # Create underlying Redis client
        underlying_client = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            ssl=ssl,
            decode_responses=False,  # We'll handle encoding ourselves
        )

        # Create our wrapper client
        return RedisClient(
            redis_client=underlying_client,
            serialization_strategy=serialization_strategy,
            key_prefix=key_prefix,
        )

    @staticmethod
    def create_json_client(
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        ssl: bool = False,
        key_prefix: str = "",
    ) -> RedisClient:
        """Create Redis client with JSON serialization."""
        return RedisClientFactory.create_redis_client(
            host=host,
            port=port,
            db=db,
            password=password,
            ssl=ssl,
            key_prefix=key_prefix,
            serialization_strategy=JsonSerializationStrategy(),
        )

    @staticmethod
    def create_pydantic_client(
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        ssl: bool = False,
        key_prefix: str = "",
    ) -> RedisClient:
        """Create Redis client with Pydantic serialization."""
        return RedisClientFactory.create_redis_client(
            host=host,
            port=port,
            db=db,
            password=password,
            ssl=ssl,
            key_prefix=key_prefix,
            serialization_strategy=PydanticSerializationStrategy(),
        )
