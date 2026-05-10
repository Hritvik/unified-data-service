"""prompt_registry models module — slimmed down post-PR2.

Surviving surface:
  - ``entities.py`` — ``TemplateResolutionOutput`` etc. (still used by
    ticket_resolution + business class).
  - ``documents.py`` — ``NamespaceDocument`` / ``PromptComponentDocument`` /
    ``PromptTemplateDocument``.

Legacy standalone Mongo document modules / ``requests.py`` / ``responses.py``
/ ``sync.py`` were dropped along with the legacy controllers and collections.
"""

from .entities import (
    PromptComponentData,
    PromptTemplateData,
    ResolvedComponentData,
    ResolvedTemplateData,
    TemplateResolutionOutput,
)
from .documents import (
    NamespaceDocument,
    PromptComponentDocument,
    PromptTemplateDocument,
)

__all__ = [
    "NamespaceDocument",
    "PromptComponentData",
    "PromptComponentDocument",
    "PromptTemplateData",
    "PromptTemplateDocument",
    "ResolvedComponentData",
    "ResolvedTemplateData",
    "TemplateResolutionOutput",
]
