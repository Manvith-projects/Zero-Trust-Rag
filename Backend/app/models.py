from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=4000)

    @field_validator("query")
    @classmethod
    def strip_query(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("query must not be empty")
        return cleaned


class SourceItem(BaseModel):
    document_id: str
    source_file: str
    page: int
    score: float
    preview: str
    allowed_roles: list[str]


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceItem]
