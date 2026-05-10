"""Repository-specific models for query operations."""

from typing import Any, Dict, List

from pydantic import BaseModel, Field

# Import query models from the dedicated query_models module


class AggregationStage(BaseModel):
    """Model for aggregation pipeline stages."""

    stage_type: str = Field(..., description="Aggregation stage type")
    stage_data: Dict[str, Any] = Field(..., description="Stage-specific data")


class AggregationPipeline(BaseModel):
    """Model for aggregation pipeline operations."""

    stages: List[AggregationStage] = Field(
        ..., description="Aggregation pipeline stages"
    )
