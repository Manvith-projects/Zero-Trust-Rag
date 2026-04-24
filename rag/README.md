# RAG Pipeline

The retrieval pipeline is intentionally constrained:

1. The backend validates the Auth0 access token with JWKS.
2. The backend extracts the namespaced roles claim.
3. The backend embeds the user query.
4. Qdrant is queried with an `allowed_roles` filter.
5. Only authorized chunks are passed to the LLM.
6. If nothing matches, the backend returns `No information available for your role.`

The LLM never talks to Qdrant directly.
