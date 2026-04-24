from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Iterable

from sentence_transformers import SentenceTransformer


@dataclass(slots=True)
class EmbeddingService:
    """Single-process embedding helper backed by sentence-transformers."""

    model_name: str
    _model: SentenceTransformer = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._model = SentenceTransformer(self.model_name)

    def encode(self, text: str) -> list[float]:
        vector = self._model.encode(text, normalize_embeddings=True)
        return [float(value) for value in vector.tolist()]

    def encode_batch(self, texts: Iterable[str]) -> list[list[float]]:
        vectors = self._model.encode(list(texts), normalize_embeddings=True)
        return [[float(value) for value in vector.tolist()] for vector in vectors]


@lru_cache(maxsize=4)
def get_embedding_service(model_name: str) -> EmbeddingService:
    return EmbeddingService(model_name=model_name)
