"""Business logic base class for unified data services.

This module provides the base class for business logic that works with
UnifiedDataService, enabling clean separation between infrastructure
and domain-specific business operations.
"""

from abc import ABC, abstractmethod
from typing import Generic, List, TypeVar

from common_utils.unified_data.service import UnifiedDataService

T = TypeVar("T")
K = TypeVar("K")


class BusinessLogicBase(ABC, Generic[T, K]):
    """
    Base class for business logic that works with UnifiedDataService.

    Provides access to the underlying service and defines the contract
    for lookup structure building.
    """

    def __init__(self, service: UnifiedDataService[T, K]):
        """
        Initialize business logic with reference to unified service.

        Args:
            service: The unified data service this business logic operates on
        """
        self.service = service
        self.logger = service.logger

    @abstractmethod
    async def _build_lookup_structures(self, entities: List[T]) -> None:
        """
        Build lookup structures from entities.

        This method is called by the framework when lookups need to be rebuilt.
        Implement this to create your custom lookup structures.

        Args:
            entities: List of all entities to build lookups from
        """
        pass
