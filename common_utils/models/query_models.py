"""
Query models for repository operations.

This module contains Pydantic models for building structured queries
used by the BaseRepository and other repository implementations.
"""

from typing import Any, List, Optional

from pydantic import BaseModel, Field


class QueryFilter(BaseModel):
    """
    Represents a single filter condition for database queries.

    This model provides a structured way to define filter conditions
    that can be used with the BaseRepository and other query operations.
    """

    field: str = Field(..., description="The field name to filter on")
    operator: str = Field(
        ..., description="The comparison operator (eq, in, regex, etc.)"
    )
    value: Any = Field(..., description="The value to compare against")

    class Config:
        """Pydantic configuration."""

        json_encoders = {
            # Add any custom JSON encoders if needed
        }


class RepositoryQuery(BaseModel):
    """
    Represents a complete query for repository operations.

    This model encapsulates all the filtering, sorting, and pagination
    parameters needed for database queries.
    """

    filters: Optional[List[QueryFilter]] = Field(
        default=None, description="List of filter conditions to apply"
    )
    sort_by: Optional[str] = Field(default=None, description="Field name to sort by")
    sort_order: int = Field(
        default=1, description="Sort order: 1 for ascending, -1 for descending"
    )
    skip: int = Field(
        default=0, description="Number of documents to skip (for pagination)"
    )
    limit: Optional[int] = Field(
        default=None, description="Maximum number of documents to return"
    )

    class Config:
        """Pydantic configuration."""

        json_encoders = {
            # Add any custom JSON encoders if needed
        }

    def add_filter(self, field: str, operator: str, value: Any) -> None:
        """
        Add a filter condition to the query.

        Args:
            field: The field name to filter on
            operator: The comparison operator
            value: The value to compare against
        """
        if self.filters is None:
            self.filters = []

        self.filters.append(QueryFilter(field=field, operator=operator, value=value))

    def add_equality_filter(self, field: str, value: Any) -> None:
        """
        Add an equality filter condition.

        Args:
            field: The field name to filter on
            value: The value to match
        """
        self.add_filter(field, "eq", value)

    def add_in_filter(self, field: str, values: List[Any]) -> None:
        """
        Add an 'in' filter condition.

        Args:
            field: The field name to filter on
            values: List of values to match against
        """
        self.add_filter(field, "in", values)

    def add_regex_filter(self, field: str, pattern: str, options: str = "i") -> None:
        """
        Add a regex filter condition.

        Args:
            field: The field name to filter on
            pattern: The regex pattern
            options: Regex options (default: "i" for case-insensitive)
        """
        self.add_filter(field, "regex", {"pattern": pattern, "options": options})


class QueryBuilder:
    """
    Builder class for constructing RepositoryQuery objects.

    This class provides a fluent interface for building complex queries
    with multiple filters and conditions.
    """

    def __init__(self) -> None:
        """Initialize a new query builder."""
        self._query = RepositoryQuery()

    def filter(self, field: str, operator: str, value: Any) -> "QueryBuilder":
        """
        Add a filter condition.

        Args:
            field: The field name to filter on
            operator: The comparison operator
            value: The value to compare against

        Returns:
            Self for method chaining
        """
        self._query.add_filter(field, operator, value)
        return self

    def eq(self, field: str, value: Any) -> "QueryBuilder":
        """
        Add an equality filter.

        Args:
            field: The field name to filter on
            value: The value to match

        Returns:
            Self for method chaining
        """
        self._query.add_equality_filter(field, value)
        return self

    def in_(self, field: str, values: List[Any]) -> "QueryBuilder":
        """
        Add an 'in' filter.

        Args:
            field: The field name to filter on
            values: List of values to match against

        Returns:
            Self for method chaining
        """
        self._query.add_in_filter(field, values)
        return self

    def regex(self, field: str, pattern: str, options: str = "i") -> "QueryBuilder":
        """
        Add a regex filter.

        Args:
            field: The field name to filter on
            pattern: The regex pattern
            options: Regex options (default: "i" for case-insensitive)

        Returns:
            Self for method chaining
        """
        self._query.add_regex_filter(field, pattern, options)
        return self

    def sort(self, field: str, order: int = 1) -> "QueryBuilder":
        """
        Set sorting parameters.

        Args:
            field: The field name to sort by
            order: Sort order (1 for ascending, -1 for descending)

        Returns:
            Self for method chaining
        """
        self._query.sort_by = field
        self._query.sort_order = order
        return self

    def paginate(self, skip: int = 0, limit: Optional[int] = None) -> "QueryBuilder":
        """
        Set pagination parameters.

        Args:
            skip: Number of documents to skip
            limit: Maximum number of documents to return

        Returns:
            Self for method chaining
        """
        self._query.skip = skip
        self._query.limit = limit
        return self

    def build(self) -> RepositoryQuery:
        """
        Build and return the final RepositoryQuery object.

        Returns:
            The constructed RepositoryQuery
        """
        return self._query


# Convenience function for creating queries
def create_query() -> QueryBuilder:
    """
    Create a new query builder instance.

    Returns:
        A new QueryBuilder instance
    """
    return QueryBuilder()


# Example usage:
# query = create_query().eq("status", "active").in_("category", ["A", "B"]).sort("created_at", -1).paginate(0, 10).build()
