# Zero-Trust RAG

Backend-enforced Retrieval-Augmented Generation (RAG) with document-level authorization.

This project demonstrates a zero-trust pattern where the frontend is untrusted for authorization decisions and the backend is the only enforcement point for access control.

## Table of Contents

1. [What This Project Solves](#what-this-project-solves)
2. [System Architecture](#system-architecture)
3. [Repository Structure](#repository-structure)
4. [Security Model](#security-model)
5. [Prerequisites](#prerequisites)
6. [Local Setup](#local-setup)
7. [Configuration](#configuration)
8. [Running the System](#running-the-system)
9. [Data Ingestion](#data-ingestion)
10. [API Contract](#api-contract)
11. [Detailed Use Cases](#detailed-use-cases)
12. [Testing](#testing)
13. [Troubleshooting](#troubleshooting)

## What This Project Solves

Traditional RAG demos often leak private information because retrieval and filtering are weak or done in the client.

This repository enforces:

- Identity verification via Auth0-issued JWTs.
- Role extraction from a namespaced claim.
- Retrieval filtering inside the backend only.
- Role-aware source inclusion before LLM generation.
- Safe fallback responses when no authorized evidence exists.

## System Architecture

High-level request flow:

1. User signs in through Auth0 in the React SPA.
2. SPA requests an access token and sends `POST /query` with `Authorization: Bearer <token>`.
3. FastAPI backend validates the JWT using Auth0 JWKS.
4. Backend extracts roles from `AUTH0_ROLE_CLAIM` (default: `https://mycorp.example/roles`).
5. Backend embeds the query and performs role-filtered retrieval from Qdrant.
6. Only authorized chunks are passed to the LLM context builder.
7. Backend returns answer + authorized source metadata.
8. If no authorized chunks exist, returns: `No information available for your role.`

Core components:

- `Frontend/`: React + Auth0 login and token acquisition.
- `Backend/`: FastAPI API, JWT verification, secure retrieval, LLM orchestration.
- `Qdrant/`: Vector database runtime via Docker Compose.
- `ingestion/`: PDF ingestion and role-tagging pipeline.
- `auth/`: Auth0 action and setup instructions.

## Repository Structure

```text
Zero-trust-RAG/
|-- Backend/
|   |-- app/
|   |   |-- api/              # /query route and dependency wiring
|   |   |-- core/             # settings + security (JWT verifier)
|   |   |-- services/         # embeddings, vector store, RAG, LLM
|   |   |-- models.py         # request/response schemas
|   |   \-- main.py           # FastAPI app factory
|   \-- tests/                # security and access-control tests
|-- Frontend/                 # Vite + React + Auth0 SPA
|-- Qdrant/                   # docker-compose for vector DB
|-- ingestion/                # PDF chunk + embed + upsert pipeline
|-- auth/                     # Auth0 Action code + setup notes
\-- documents/                # sample policy docs/manifests
```

## Security Model

### Trust boundaries

- Trusted: backend service (`Backend/app/*`).
- Untrusted: browser, frontend code, user-provided token until validated.

### Enforced controls

1. JWT validation is mandatory before query execution.
2. Roles are read from a controlled namespaced claim.
3. Qdrant retrieval is filtered by role.
4. Retrieved chunks are re-checked for role intersection before LLM call.
5. Unauthorized or empty retrieval path returns a safe non-disclosure answer.
6. Retrieval count is capped (`max_top_k = 5`) to reduce overexposure.

## Prerequisites

- Python 3.10+
- Node.js 18+
- Docker Desktop (for Qdrant)
- Auth0 tenant with:
	- SPA application
	- API configured with RS256
	- roles and role-injection action

## Local Setup

### 1) Start Qdrant

```bash
cd Qdrant
docker compose up -d
```

### 2) Configure Backend

```bash
cd Backend
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create `Backend/.env`:

```env
AUTH0_DOMAIN=your-tenant.us.auth0.com
AUTH0_AUDIENCE=https://api.mycorp.example
AUTH0_ROLE_CLAIM=https://mycorp.example/roles

QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
QDRANT_COLLECTION=zero_trust_rag

EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

LLM_PROVIDER=openai
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o-mini

# Optional if you switch providers
HUGGINGFACE_API_TOKEN=
HUGGINGFACE_MODEL=meta-llama/Meta-Llama-3.1-8B-Instruct
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash

CORS_ORIGINS=["http://localhost:5173","http://127.0.0.1:5173"]
REQUEST_TIMEOUT_SECONDS=30
```

### 3) Configure Frontend

```bash
cd Frontend
npm install
```

Create `Frontend/.env`:

```env
VITE_AUTH0_DOMAIN=your-tenant.us.auth0.com
VITE_AUTH0_CLIENT_ID=your_spa_client_id
VITE_AUTH0_AUDIENCE=https://api.mycorp.example
VITE_API_BASE_URL=http://localhost:8000
```

### 4) Configure Auth0

Follow `auth/README.md` and ensure:

- Roles exist (`HR_Manager`, `Intern`, `Admin`).
- Auth0 action injects roles into `https://mycorp.example/roles`.
- SPA callback/logout/origin includes `http://localhost:5173`.

## Configuration

Important backend settings (`Backend/app/core/config.py`):

- `AUTH0_DOMAIN`, `AUTH0_AUDIENCE`: token issuer + audience checks.
- `AUTH0_ROLE_CLAIM`: where roles are read from the JWT.
- `QDRANT_*`: vector DB location and collection.
- `EMBEDDING_MODEL`: sentence-transformers model for query/doc embeddings.
- `LLM_PROVIDER`: one of `openai`, `huggingface`, or `gemini` (based on configured client).
- `CORS_ORIGINS`: must include your frontend origin.

## Running the System

Start backend:

```bash
cd Backend
uvicorn app.main:app --reload --port 8000
```

Start frontend:

```bash
cd Frontend
npm run dev
```

Health check:

```bash
curl http://localhost:8000/healthz
```

Expected:

```json
{"status":"ok"}
```

## Data Ingestion

The ingestion script reads PDFs, chunks text, embeds chunks, and upserts to Qdrant with `allowed_roles` metadata.

### Role assignment options

1. Sidecar manifest per PDF (recommended)
2. CLI fallback via `--default-roles`

Example sidecar:

- `salary-policy.pdf`
- `salary-policy.json`

```json
{
	"allowed_roles": ["HR_Manager", "Admin"]
}
```

Run ingestion:

```bash
python ingestion/ingest_pdfs.py --input-dir ./documents --default-roles HR_Manager
```

Hardening behavior:

- If no roles resolve for a document, ingestion denies by default.
- Empty pages/chunks are skipped.

## API Contract

### `POST /query`

Headers:

- `Authorization: Bearer <access_token>`
- `Content-Type: application/json`

Request body:

```json
{
	"query": "What is the salary policy for HR managers?"
}
```

Success response:

```json
{
	"answer": "...",
	"sources": [
		{
			"document_id": "salary-policy",
			"source_file": "salary-policy.pdf",
			"page": 1,
			"score": 0.95,
			"preview": "Salary policy states annual compensation...",
			"allowed_roles": ["HR_Manager"]
		}
	]
}
```

Common error cases:

- `401` invalid/missing token
- `500` query execution failure

## Detailed Use Cases

### Use Case 1: Intern asks for confidential salary data

- Actor: `Intern`
- Query: "What is the salary policy?"
- Data classification: restricted to `HR_Manager`
- Expected result:
	- `answer = "No information available for your role."`
	- no salary document in `sources`
- Security value: prevents privilege escalation by prompt wording.

### Use Case 2: HR manager asks the same salary question

- Actor: `HR_Manager`
- Query: "What is the salary policy?"
- Expected result:
	- salary policy chunks are retrieved
	- answer generated from authorized context
	- `sources[].allowed_roles` includes `HR_Manager`
- Security value: least privilege still allows legitimate access.

### Use Case 3: User with invalid token calls API

- Actor: any user with malformed/invalid JWT
- Query: any
- Expected result:
	- backend returns `401` with `Invalid token`
	- no retrieval, no LLM call
- Security value: blocks unauthenticated data paths early.

### Use Case 4: Authorized role has no matching documents

- Actor: `Intern`
- Query: "Show me incident reports"
- Data in store: only `Admin` chunks match
- Expected result:
	- safe fallback answer
	- empty source list
- Security value: avoids accidental disclosure by similarity search drift.

### Use Case 5: LLM provider outage during authorized retrieval

- Actor: authorized user
- Query: any authorized question
- Failure mode: LLM call throws exception
- Expected result:
	- backend returns fallback: `LLM is temporarily unavailable, but authorized sources were retrieved successfully.`
	- source evidence is still role-safe
- Security value: graceful degradation without bypassing authorization.

## Testing

Run backend tests:

```bash
cd Backend
pytest -q
```

Current test coverage in `Backend/tests/test_query_security.py` verifies:

- intern cannot access salary data
- HR can access salary data
- invalid token is rejected
- no matching roles returns safe response

## Troubleshooting

- `401 Invalid token`:
	- verify `AUTH0_DOMAIN` and `AUTH0_AUDIENCE`
	- ensure frontend uses the same `VITE_AUTH0_AUDIENCE`
- Empty answers for valid users:
	- check role claim namespace in token payload
	- verify document `allowed_roles` in ingestion manifests
- CORS errors:
	- ensure frontend origin is included in `CORS_ORIGINS`
- No retrieval results:
	- confirm Qdrant is running and collection exists
	- re-run ingestion against the correct documents directory

## Additional Notes

- Auth0 setup details: `auth/README.md`
- Retrieval notes: `rag/README.md`

This project is designed as a secure baseline. You can extend it with tenant isolation, attribute-based access control (ABAC), and audit trails while preserving the same backend-enforced trust model.
# Zero-Trust-Rag
# Zero-Trust-Rag
