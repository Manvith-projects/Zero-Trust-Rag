from __future__ import annotations

from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient
from jwt import InvalidTokenError

from app.core.config import Settings
from app.core.security import Auth0Verifier
from app.domain import AnswerBundle, AuthenticatedUser, RetrievedChunk
from app.main import create_app
from app.services.rag import SAFE_NO_INFO, SecureRAGService


@dataclass(slots=True)
class FakeEmbeddingService:
    def encode(self, text: str) -> list[float]:
        return [0.1, 0.2, 0.3]


@dataclass(slots=True)
class FakeVectorStore:
    chunks: list[RetrievedChunk]

    def search(self, query_vector: list[float], user_roles: list[str], top_k: int) -> list[RetrievedChunk]:
        authorized: list[RetrievedChunk] = []
        for chunk in self.chunks:
            if set(chunk.allowed_roles).intersection(user_roles):
                authorized.append(chunk)
        return authorized[:top_k]


@dataclass(slots=True)
class FakeLLMClient:
    def generate_answer(self, question: str, context: str) -> str:
        if "salary" in context.lower():
            return "Salary data is 120000."
        return "No information available for your role."


class FakeAuthVerifier:
    def verify(self, token: str) -> AuthenticatedUser:
        if token == "invalid":
            raise InvalidTokenError("bad token")
        return AuthenticatedUser(sub="auth0|user123", roles=[token], claims={})


def build_test_service() -> SecureRAGService:
    chunks = [
        RetrievedChunk(
            chunk_id="1",
            document_id="salary-policy",
            source_file="salary.pdf",
            page=1,
            text="Salary policy states annual compensation is 120000.",
            allowed_roles=["HR_Manager"],
            score=0.95,
        ),
        RetrievedChunk(
            chunk_id="2",
            document_id="intern-guide",
            source_file="intern.pdf",
            page=2,
            text="Intern onboarding information.",
            allowed_roles=["Intern", "HR_Manager", "Admin"],
            score=0.88,
        ),
    ]
    return SecureRAGService(
        embeddings=FakeEmbeddingService(),
        vector_store=FakeVectorStore(chunks=chunks),
        llm_client=FakeLLMClient(),
    )


def build_app() -> TestClient:
    settings = Settings(
        AUTH0_DOMAIN="tenant.example.com",
        AUTH0_AUDIENCE="https://api.example.com",
    )
    app = create_app(settings=settings, rag_service=build_test_service(), auth_verifier=FakeAuthVerifier())
    return TestClient(app)


def test_intern_cannot_access_salary_data() -> None:
    client = build_app()
    response = client.post(
        "/query",
        headers={"Authorization": "Bearer Intern"},
        json={"query": "What is the salary policy?"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == SAFE_NO_INFO
    source_ids = [item["document_id"] for item in body["sources"]]
    assert "salary-policy" not in source_ids


def test_hr_can_access_salary_data() -> None:
    client = build_app()

    class HRAuthVerifier(FakeAuthVerifier):
        def verify(self, token: str) -> AuthenticatedUser:
            return AuthenticatedUser(sub="auth0|hr", roles=["HR_Manager"], claims={})

    app = create_app(settings=Settings(AUTH0_DOMAIN="tenant.example.com", AUTH0_AUDIENCE="https://api.example.com"), rag_service=build_test_service(), auth_verifier=HRAuthVerifier())
    client = TestClient(app)
    response = client.post(
        "/query",
        headers={"Authorization": "Bearer hr"},
        json={"query": "What is the salary policy?"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "Salary data is 120000."
    assert body["sources"]
    assert body["sources"][0]["allowed_roles"] == ["HR_Manager"]


def test_invalid_token_rejected() -> None:
    client = build_app()
    response = client.post(
        "/query",
        headers={"Authorization": "Bearer invalid"},
        json={"query": "Any confidential data?"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid token"


def test_no_matching_roles_returns_safe_response() -> None:
    chunks = [
        RetrievedChunk(
            chunk_id="3",
            document_id="admin-only",
            source_file="admin.pdf",
            page=1,
            text="Admin-only incident report.",
            allowed_roles=["Admin"],
            score=0.9,
        )
    ]
    service = SecureRAGService(
        embeddings=FakeEmbeddingService(),
        vector_store=FakeVectorStore(chunks=chunks),
        llm_client=FakeLLMClient(),
    )
    result = service.answer_query(query="Show me the incident report", user_roles=["Intern"])
    assert result.answer == SAFE_NO_INFO
    assert result.sources == []
