"""rest_client_registry models module — slimmed down post-PR2.

The legacy ``ServiceDocument`` / ``EndpointDocument`` Beanie classes were
dropped along with the legacy ``services`` / ``endpoints`` Mongo
collections; their accompanying request/response/sync/native shapes are
also gone now that the legacy controllers no longer exist.

Surviving surface:
  - ``embedded_documents.py`` — BaseModel sub-docs that ``ServiceDocument`` /
    ``EndpointDocument`` still embed (ConnectionPoolConfigDocument,
    AuthConfigDocument, etc.).
  - ``responses.py`` — Info / Response shapes consumed by the
    registry source (``ServiceConfigInfo``, ``ServiceConfigListResponse``,
    ``EndpointConfigInfo`` …).
  - ``documents.py`` — Beanie ``ServiceDocument`` / ``EndpointDocument``.
"""

from .embedded_documents import (
    AuthConfigDocument,
    CircuitBreakerConfigDocument,
    ConnectionPoolConfigDocument,
    CredentialsConfigDocument,
    RetryConfigDocument,
    TimeoutConfigDocument,
)
from .responses import (
    AuthConfigInfo,
    CircuitBreakerConfigInfo,
    ConnectionPoolConfigInfo,
    CredentialsConfigInfo,
    EndpointConfigInfo,
    RetryConfigInfo,
    ServiceConfigInfo,
    ServiceConfigListResponse,
    ServiceConfigResponse,
    TimeoutConfigInfo,
)
from .documents import EndpointDocument, ServiceDocument

__all__ = [
    "AuthConfigDocument",
    "AuthConfigInfo",
    "CircuitBreakerConfigDocument",
    "CircuitBreakerConfigInfo",
    "ConnectionPoolConfigDocument",
    "ConnectionPoolConfigInfo",
    "CredentialsConfigDocument",
    "CredentialsConfigInfo",
    "EndpointConfigInfo",
    "EndpointDocument",
    "RetryConfigDocument",
    "RetryConfigInfo",
    "ServiceConfigInfo",
    "ServiceConfigListResponse",
    "ServiceConfigResponse",
    "ServiceDocument",
    "TimeoutConfigDocument",
    "TimeoutConfigInfo",
]
