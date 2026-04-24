from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class AuthenticatedUser:
    """Authenticated caller resolved from an Auth0 access token."""

    sub: str
    roles: list[str]
    claims: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class RetrievedChunk:
    """Chunk returned from Qdrant after backend-side authorization filtering."""

    chunk_id: str
    document_id: str
    source_file: str
    page: int
    text: str
    allowed_roles: list[str]
    score: float


@dataclass(slots=True)
class AnswerBundle:
    """Answer and the authorized source snippets used to generate it."""

    answer: str
    sources: list[RetrievedChunk]
