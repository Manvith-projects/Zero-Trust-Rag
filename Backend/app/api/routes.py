from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_current_user, get_rag_service
from app.domain import AuthenticatedUser
from app.models import QueryRequest, QueryResponse, SourceItem
from app.services.rag import SecureRAGService

router = APIRouter(tags=["query"])
logger = logging.getLogger(__name__)


@router.post("/query", response_model=QueryResponse)
def query_documents(
    payload: QueryRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    rag_service: SecureRAGService = Depends(get_rag_service),
) -> QueryResponse:
    try:
        bundle = rag_service.answer_query(query=payload.query, user_roles=user.roles)
        return QueryResponse(
            answer=bundle.answer,
            sources=[
                SourceItem(
                    document_id=chunk.document_id,
                    source_file=chunk.source_file,
                    page=chunk.page,
                    score=chunk.score,
                    preview=chunk.text[:240].replace("\n", " ").strip(),
                    allowed_roles=chunk.allowed_roles,
                )
                for chunk in bundle.sources
            ],
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Query execution failed")
        raise HTTPException(status_code=500, detail="Query execution failed")
