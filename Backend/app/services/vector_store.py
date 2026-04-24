from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable
from uuid import NAMESPACE_URL, uuid5

from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.http import models as qmodels

from app.domain import RetrievedChunk


EMBEDDING_DIMENSION = 384


@dataclass(slots=True)
class DocumentChunk:
    chunk_id: str
    document_id: str
    source_file: str
    page: int
    text: str
    allowed_roles: list[str]


class QdrantVectorStore:
    """Writes and queries vectors only from the backend security layer."""

    def __init__(self, url: str, api_key: str | None, collection_name: str) -> None:
        self.collection_name = collection_name
        self.client = QdrantClient(url=url, api_key=api_key)

    def ensure_collection(self) -> None:
        if not self.client.collection_exists(self.collection_name):
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=qmodels.VectorParams(size=EMBEDDING_DIMENSION, distance=qmodels.Distance.COSINE),
            )

        self._ensure_allowed_roles_index()

    def _ensure_allowed_roles_index(self) -> None:
        # Needed for filtering with MatchAny on allowed_roles.
        self.client.create_payload_index(
            collection_name=self.collection_name,
            field_name="allowed_roles",
            field_schema=qmodels.PayloadSchemaType.KEYWORD,
            wait=True,
        )

    @staticmethod
    def build_chunk_id(source_file: str, page: int, chunk_index: int, text: str) -> str:
        basis = f"{Path(source_file).as_posix()}::{page}::{chunk_index}::{text}"
        return str(uuid5(NAMESPACE_URL, basis))

    def upsert_chunks(self, chunks: Iterable[DocumentChunk], embeddings: Iterable[list[float]]) -> None:
        points: list[qmodels.PointStruct] = []
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            points.append(
                qmodels.PointStruct(
                    id=chunk.chunk_id,
                    vector=embedding,
                    payload={
                        "document_id": chunk.document_id,
                        "source_file": chunk.source_file,
                        "page": chunk.page,
                        "text": chunk.text,
                        "allowed_roles": chunk.allowed_roles,
                    },
                )
            )

        if points:
            self.client.upsert(collection_name=self.collection_name, points=points)

    @staticmethod
    def _role_variants(role: str) -> set[str]:
        cleaned = role.strip()
        if not cleaned:
            return set()

        variants = {cleaned, cleaned.lower(), cleaned.upper(), cleaned.title()}
        if "_" in cleaned:
            parts = cleaned.split("_")
            smart = "_".join(part.upper() if len(part) <= 2 else part.capitalize() for part in parts)
            variants.add(smart)
        return variants

    def search(self, query_vector: list[float], user_roles: list[str], top_k: int) -> list[RetrievedChunk]:
        if not user_roles:
            return []

        expanded_roles: set[str] = set()
        for role in user_roles:
            if isinstance(role, str):
                expanded_roles.update(self._role_variants(role))

        if not expanded_roles:
            return []

        search_filter = qmodels.Filter(
            must=[
                qmodels.FieldCondition(
                    key="allowed_roles",
                    match=qmodels.MatchAny(any=sorted(expanded_roles)),
                )
            ]
        )

        try:
            hits = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                query_filter=search_filter,
                limit=top_k,
                with_payload=True,
            )
        except UnexpectedResponse as exc:
            # Some existing collections can miss the payload index; create it and retry once.
            response_text = str(exc)
            if "Index required but not found" in response_text and '"allowed_roles"' in response_text:
                self._ensure_allowed_roles_index()
                hits = self.client.search(
                    collection_name=self.collection_name,
                    query_vector=query_vector,
                    query_filter=search_filter,
                    limit=top_k,
                    with_payload=True,
                )
            else:
                raise

        results: list[RetrievedChunk] = []
        for hit in hits:
            payload = hit.payload or {}
            results.append(
                RetrievedChunk(
                    chunk_id=str(hit.id),
                    document_id=str(payload.get("document_id", "")),
                    source_file=str(payload.get("source_file", "")),
                    page=int(payload.get("page", 0)),
                    text=str(payload.get("text", "")),
                    allowed_roles=[role for role in payload.get("allowed_roles", []) if isinstance(role, str)],
                    score=float(hit.score or 0.0),
                )
            )
        return results
