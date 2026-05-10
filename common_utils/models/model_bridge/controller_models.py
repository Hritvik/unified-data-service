"""
Controller request/response models for Model Bridge endpoints.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DryRunRequest(BaseModel):
    """Request to preview route plan selections without invoking."""

    route_plan_name: str = Field(..., description="Name of the route plan to evaluate")


class DryRunLevelResult(BaseModel):
    """Result of evaluating a single route plan level."""

    level: int
    model_selection_strategy: str
    deployment_selection_strategy: str
    selected_deployment: Optional[str] = None
    selected_model: Optional[str] = None
    success: bool
    error: Optional[str] = None
    duration_seconds: float = 0.0


class DryRunResponse(BaseModel):
    """Response from route plan dry-run evaluation."""

    success: bool
    route_plan_name: str
    total_levels: int
    levels: List[DryRunLevelResult]
    message: str


class HealthCheckResponse(BaseModel):
    """Response from model bridge health check."""

    status: str = Field(..., description="healthy, degraded, or unhealthy")
    registry_data_loaded: bool
    total_models: int = 0
    total_deployments: int = 0
    total_route_plans: int = 0
    details: Optional[Dict[str, Any]] = None


class CacheInfoResponse(BaseModel):
    """Response with cache information."""

    success: bool
    cache_info: Dict[str, Any]


class CacheRefreshResponse(BaseModel):
    """Response after cache refresh."""

    success: bool
    message: str
    metadata: Optional[Dict[str, Any]] = None


class ModelCapabilityResponse(BaseModel):
    """Response listing available models."""

    success: bool
    models: List[Dict[str, Any]]
    total: int
