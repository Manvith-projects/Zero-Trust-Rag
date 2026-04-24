from __future__ import annotations

from dataclasses import dataclass
import logging

from app.domain import AnswerBundle, RetrievedChunk
from app.services.embeddings import EmbeddingService
from app.services.llm import SecureLLMClient
from app.services.vector_store import QdrantVectorStore


SAFE_NO_INFO = "No information available for your role."
logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SecureRAGService:
    """End-to-end retrieval layer that enforces authorization before the LLM call."""

    embeddings: EmbeddingService
    vector_store: QdrantVectorStore
    llm_client: SecureLLMClient
    max_top_k: int = 5

    def answer_query(self, query: str, user_roles: list[str], top_k: int | None = None) -> AnswerBundle:
        if not user_roles:
            return AnswerBundle(answer=SAFE_NO_INFO, sources=[])

        requested_top_k = top_k if top_k is not None else self.max_top_k
        capped_top_k = max(1, min(requested_top_k, self.max_top_k))

        query_vector = self.embeddings.encode(query)
        sources = self.vector_store.search(query_vector=query_vector, user_roles=user_roles, top_k=capped_top_k)
        authorized_sources = [chunk for chunk in sources if set(chunk.allowed_roles).intersection(user_roles)]
        if not authorized_sources:
            return AnswerBundle(answer=SAFE_NO_INFO, sources=[])

        context = self._build_context(authorized_sources)
        try:
            answer = self.llm_client.generate_answer(question=query, context=context).strip()
            if not answer:
                answer = SAFE_NO_INFO
        except Exception:
            logger.exception("LLM generation failed; returning retrieval-only fallback")
            answer = "LLM is temporarily unavailable, but authorized sources were retrieved successfully."

        return AnswerBundle(answer=answer, sources=authorized_sources)

    @staticmethod
    def _build_context(chunks: list[RetrievedChunk]) -> str:
        sections: list[str] = []
        for index, chunk in enumerate(chunks, start=1):
            sections.append(
                f"[Source {index}]\n"
                f"Document: {chunk.document_id}\n"
                f"File: {chunk.source_file}\n"
                f"Page: {chunk.page}\n"
                f"Allowed roles: {', '.join(chunk.allowed_roles)}\n"
                f"Text: {chunk.text}"
            )
        return "\n\n".join(sections)
