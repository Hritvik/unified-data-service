from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class MessagePriority(Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class MessageStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


class MessageMetadata(BaseModel):
    """Metadata for a message."""

    message_id: str = Field(..., description="Unique message identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    priority: MessagePriority = Field(default=MessagePriority.NORMAL)
    status: MessageStatus = Field(default=MessageStatus.PENDING)
    retry_count: int = Field(default=0)
    max_retries: int = Field(default=3)
    ttl_seconds: Optional[int] = Field(None, description="Time to live in seconds")
    headers: Dict[str, str] = Field(default_factory=dict)
    correlation_id: Optional[str] = Field(
        None, description="For tracing related messages"
    )
    reply_to: Optional[str] = Field(None, description="Reply topic/queue")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class Message(BaseModel):
    """Generic message structure."""

    topic: str = Field(..., description="Topic/queue name")
    key: Optional[str] = Field(None, description="Message key for partitioning")
    value: Any = Field(..., description="Message payload")
    metadata: MessageMetadata = Field(..., description="Message metadata")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class QueueConfig(BaseModel):
    """Configuration for a message queue."""

    name: str = Field(..., description="Queue/topic name")
    partitions: int = Field(default=1, description="Number of partitions")
    replication_factor: int = Field(default=1, description="Replication factor")
    retention_ms: Optional[int] = Field(None, description="Message retention time")
    max_message_size: int = Field(
        default=1048576, description="Max message size in bytes"
    )
    compression_type: str = Field(default="none", description="Compression type")
    cleanup_policy: str = Field(default="delete", description="Cleanup policy")


class ConsumerConfig(BaseModel):
    """Configuration for a message consumer."""

    group_id: str = Field(..., description="Consumer group ID")
    auto_offset_reset: str = Field(
        default="latest", description="Offset reset strategy"
    )
    max_poll_records: int = Field(default=500, description="Max records per poll")
    session_timeout_ms: int = Field(default=30000, description="Session timeout")
    heartbeat_interval_ms: int = Field(default=3000, description="Heartbeat interval")
    enable_auto_commit: bool = Field(default=True, description="Enable auto commit")
    auto_commit_interval_ms: int = Field(
        default=5000, description="Auto commit interval"
    )
