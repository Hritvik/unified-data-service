"""Service for managing deployment health status caching.

This service provides a unified interface for caching deployment health statuses
using the generic cache infrastructure.
"""

from typing import Optional

from common_utils.cache import ICacheRepository
from common_utils.logger import get_logger
from common_utils.models.model_bridge.native import DeploymentHealthStatus

logger = get_logger(__name__)


class DeploymentHealthCacheService:
    """
    Service for managing deployment health status caching.

    This service uses the generic cache infrastructure and can switch between
    in-memory and Redis storage based on configuration.
    """

    def __init__(
        self,
        repository: ICacheRepository[DeploymentHealthStatus],
        default_ttl_seconds: Optional[int] = 3600,
    ) -> None:
        """
        Initialize the deployment health cache service.

        Args:
            repository: Cache repository instance
            default_ttl_seconds: Default TTL in seconds for cached entries
        """
        self.logger = logger
        self._default_ttl = default_ttl_seconds

        # Use cache repository directly
        self._cache_repo = repository

    # Delegate to generic cache service
    async def get_health_status(
        self, deployment_name: str
    ) -> Optional[DeploymentHealthStatus]:
        """Get deployment health status by deployment name."""
        return await self._cache_repo.get_by_key(deployment_name)

    async def set_health_status(
        self, deployment_name: str, health_status: DeploymentHealthStatus
    ) -> DeploymentHealthStatus:
        """Set deployment health status by deployment name."""
        # Ensure the identity matches the deployment name
        health_status.identity.model = deployment_name
        return await self._cache_repo.set_by_key(deployment_name, health_status)

    async def set_health_status_with_ttl(
        self,
        deployment_name: str,
        health_status: DeploymentHealthStatus,
        ttl_seconds: int,
    ) -> DeploymentHealthStatus:
        """Set deployment health status by deployment name with TTL."""
        # Ensure the identity matches the deployment name
        health_status.identity.model = deployment_name
        return await self._cache_repo.set_by_key_with_ttl(
            deployment_name, health_status, ttl_seconds
        )

    async def get_all_health_statuses(self) -> dict[str, DeploymentHealthStatus]:
        """Get all deployment health statuses."""
        return await self._cache_repo.get_by_key_all()

    async def delete_health_status(self, deployment_name: str) -> bool:
        """Delete deployment health status by deployment name."""
        return await self._cache_repo.delete_by_key(deployment_name)

    async def health_status_exists(self, deployment_name: str) -> bool:
        """Check if deployment health status exists for deployment name."""
        return await self._cache_repo.exists_by_key(deployment_name)

    async def count_health_statuses(self) -> int:
        """Count total deployment health statuses."""
        return await self._cache_repo.count()

    async def clear_all_health_statuses(self) -> None:
        """Clear all deployment health statuses."""
        await self._cache_repo.clear()

    async def cleanup_expired(self) -> int:
        """Clean up expired entries and return count of cleaned entries."""
        return await self._cache_repo.cleanup_expired()

    # Use case specific methods
    async def get_healthy_deployments(self) -> list[str]:
        """Get deployment names that are healthy overall."""
        all_statuses = await self.get_all_health_statuses()
        return [
            deployment_name
            for deployment_name, status in all_statuses.items()
            if status.is_healthy_overall
        ]

    async def get_unhealthy_deployments(self) -> list[str]:
        """Get deployment names that are unhealthy overall."""
        all_statuses = await self.get_all_health_statuses()
        return [
            deployment_name
            for deployment_name, status in all_statuses.items()
            if not status.is_healthy_overall
        ]

    async def get_deployments_with_critical_issues(self) -> list[str]:
        """Get deployment names that have critical issues."""
        all_statuses = await self.get_all_health_statuses()
        return [
            deployment_name
            for deployment_name, status in all_statuses.items()
            if status.is_critical_issues
        ]

    # Convenience methods using generic cache service
    async def get_or_set_health_status(
        self,
        deployment_name: str,
        factory: callable[[], DeploymentHealthStatus],
        ttl_seconds: Optional[int] = None,
    ) -> DeploymentHealthStatus:
        """Get health status or create and set it using factory if not found."""
        # Get or set pattern
        status = await self._cache_repo.get_by_key(deployment_name)
        if status is None:
            status = factory()
            await self._cache_repo.set_by_key(deployment_name, status, ttl_seconds)
        return status

    async def get_or_set_health_status_async(
        self,
        deployment_name: str,
        factory: callable[[], DeploymentHealthStatus],
        ttl_seconds: Optional[int] = None,
    ) -> DeploymentHealthStatus:
        """Get health status or create and set it using async factory if not found."""
        # Get or set pattern with async factory
        status = await self._cache_repo.get_by_key(deployment_name)
        if status is None:
            status = await factory()
            await self._cache_repo.set_by_key(deployment_name, status, ttl_seconds)
        return status

    async def update_health_status_if_exists(
        self,
        deployment_name: str,
        updater: callable[[DeploymentHealthStatus], DeploymentHealthStatus],
    ) -> bool:
        """Update health status if it exists in cache."""
        # Check if exists, then update
        if await self._cache_repo.exists_by_key(deployment_name):
            current_status = await self._cache_repo.get_by_key(deployment_name)
            if current_status:
                updated_status = updater(current_status)
                await self._cache_repo.set_by_key(deployment_name, updated_status)
                return updated_status
        return None

    async def get_many_health_statuses(
        self, deployment_names: list[str]
    ) -> dict[str, Optional[DeploymentHealthStatus]]:
        """Get multiple health statuses by deployment names."""
        # Get many pattern
        result = {}
        for deployment_name in deployment_names:
            result[deployment_name] = await self._cache_repo.get_by_key(deployment_name)
        return result

    async def set_many_health_statuses(
        self,
        health_statuses: dict[str, DeploymentHealthStatus],
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """Set multiple health statuses."""
        # Ensure identities match deployment names
        for deployment_name, status in health_statuses.items():
            status.identity.model = deployment_name
        # Set many pattern
        for deployment_name, status in health_statuses.items():
            await self._cache_repo.set_by_key(deployment_name, status, ttl_seconds)

    async def delete_many_health_statuses(self, deployment_names: list[str]) -> int:
        """Delete multiple health statuses by deployment names."""
        # Delete many pattern
        deleted_count = 0
        for deployment_name in deployment_names:
            if await self._cache_repo.delete_by_key(deployment_name):
                deleted_count += 1
        return deleted_count

    def get_cache_info(self) -> dict[str, any]:
        """Get detailed cache information."""
        info = self._cache_repo.get_cache_info()
        info["use_case"] = "deployment_health_status"
        info["use_redis"] = self._use_redis
        return info

    def refresh_cache(self) -> None:
        """Force a cache refresh by clearing the cache."""
        # This integrates with the existing cache registry
        self.logger.info("Cache refresh requested for deployment health status service")
