from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as query_router
from app.core.config import Settings, get_settings
from app.core.security import Auth0Verifier
from app.services.embeddings import get_embedding_service
from app.services.llm import build_llm_client
from app.services.rag import SecureRAGService
from app.services.vector_store import QdrantVectorStore


def build_rag_service(settings: Settings) -> SecureRAGService:
    embeddings = get_embedding_service(settings.embedding_model)
    vector_store = QdrantVectorStore(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        collection_name=settings.qdrant_collection,
    )
    vector_store.ensure_collection()
    llm_client = build_llm_client(settings)
    return SecureRAGService(embeddings=embeddings, vector_store=vector_store, llm_client=llm_client)


def create_app(settings: Settings | None = None, rag_service: SecureRAGService | None = None, auth_verifier: Auth0Verifier | None = None) -> FastAPI:
    runtime_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.settings = runtime_settings
        app.state.auth_verifier = auth_verifier or Auth0Verifier(
            domain=runtime_settings.auth0_domain,
            audience=runtime_settings.auth0_audience,
            role_claim=runtime_settings.auth0_role_claim,
        )
        app.state.rag_service = rag_service or build_rag_service(runtime_settings)
        yield

    app = FastAPI(
        title="Zero-Trust RAG API",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Ensure dependencies are available even before lifespan startup hooks run.
    if auth_verifier is not None:
        app.state.auth_verifier = auth_verifier
    if rag_service is not None:
        app.state.rag_service = rag_service
    app.state.settings = runtime_settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=runtime_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(query_router)
    return app


app = create_app()
