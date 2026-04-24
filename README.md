# Zero-Trust RAG with Document-Level Access Control

This repository implements a secure retrieval-augmented generation platform where the backend is the only enforcement layer.

## Architecture

- Auth0 authenticates the user and emits an access token with a namespaced roles claim.
- The React SPA only obtains the token and submits a query.
- FastAPI validates the JWT using Auth0 JWKS before doing anything else.
- The backend extracts user roles from `https://mycorp.example/roles`.
- The backend embeds the query and searches Qdrant with a role filter.
- Only authorized chunks are passed to the LLM.
- If nothing matches, the API returns `No information available for your role.`

## Folder Structure

- `Backend/` - FastAPI service, JWT validation, retrieval, and answer generation.
- `Frontend/` - React + Vite SPA with Auth0 login.
- `ingestion/` - PDF ingestion pipeline.
- `auth/` - Auth0 Action and setup guide.
- `rag/` - Retrieval pipeline notes.
- `Qdrant/` - Qdrant deployment compose file.

## Backend

The backend contains the zero-trust enforcement points:

1. JWT validation against Auth0 JWKS.
2. Role extraction from the namespaced claim.
3. Qdrant filtering using `allowed_roles`.
4. Top-k capped at 5.
5. Safe fallback when nothing matches.

### Run locally

```bash
cd Backend
copy .env.example .env
uvicorn app.main:app --reload --port 8000
```

## Frontend

The SPA uses Auth0 for login and sends the access token in the `Authorization` header.

```bash
cd Frontend
npm install
npm run dev
```

## Ingestion

PDFs can be ingested with per-file sidecar manifests:

- `policy.pdf`
- `policy.json` with `{"allowed_roles": ["HR_Manager"]}`

If a document does not resolve to a non-empty role list, it is denied by default.

```bash
python ingestion/ingest_pdfs.py --input-dir ./documents --default-roles HR_Manager
```

## Auth0 Setup

See [auth/README.md](auth/README.md).

## Security Checklist

- Validate JWTs with JWKS, not by decoding alone.
- Keep all retrieval filtering in the backend.
- Deny documents without `allowed_roles`.
- Cap retrieval to 5 chunks.
- Never expose unauthorized content to the browser.
- Never let the LLM access the vector database directly.
# Zero-Trust-Rag
