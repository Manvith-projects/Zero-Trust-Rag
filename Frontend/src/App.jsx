import { useState, useEffect } from 'react';
import { useAuth0 } from '@auth0/auth0-react';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

function SourceCard({ source }) {
  return (
    <article className="source-card">
      <div className="source-card__meta">
        <span>{source.document_id}</span>
        <span>Page {source.page}</span>
        <span>Score {source.score.toFixed(3)}</span>
      </div>
      <p className="source-card__preview">{source.preview}</p>
      <div className="source-card__roles">
        {source.allowed_roles.map((role) => (
          <span key={role}>{role}</span>
        ))}
      </div>
    </article>
  );
}

export default function App() {
  const { isLoading, isAuthenticated, user, loginWithRedirect, logout, getAccessTokenSilently } = useAuth0();
  const [roles, setRoles] = useState([]);

  // Must match Backend AUTH0_ROLE_CLAIM.
  const ROLES_CLAIM = 'https://mycorp.example/roles';

  const decodeJwtPayload = (token) => {
    const [, payloadSegment] = token.split('.');
    if (!payloadSegment) {
      return {};
    }

    // JWT uses base64url, convert to standard base64 before atob.
    const base64 = payloadSegment.replace(/-/g, '+').replace(/_/g, '/');
    const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), '=');
    return JSON.parse(atob(padded));
  };

  useEffect(() => {
    async function fetchRoles() {
      if (isAuthenticated) {
        try {
          const token = await getAccessTokenSilently({
            authorizationParams: { audience: import.meta.env.VITE_AUTH0_AUDIENCE },
          });
          const payload = decodeJwtPayload(token);
          const extractedRoles = Array.isArray(payload[ROLES_CLAIM]) ? payload[ROLES_CLAIM] : [];
          setRoles(extractedRoles);
        } catch (e) {
          setRoles([]);
        }
      } else {
        setRoles([]);
      }
    }
    fetchRoles();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated]);
  const [query, setQuery] = useState('');
  const [answer, setAnswer] = useState('');
  const [sources, setSources] = useState([]);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setSubmitting(true);
    setError('');
    setAnswer('');
    setSources([]);

    try {
      const token = await getAccessTokenSilently({ authorizationParams: { audience: import.meta.env.VITE_AUTH0_AUDIENCE } });
      const response = await fetch(`${API_BASE_URL}/query`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query }),
      });

      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail || 'Request failed');
      }

      setAnswer(payload.answer);
      setSources(payload.sources || []);
    } catch (submissionError) {
      setError(submissionError.message);
    } finally {
      setSubmitting(false);
    }
  };

  if (isLoading) {
    return <main className="shell shell--centered">Loading secure session...</main>;
  }

  return (
    <main className="shell">
      <section className="hero-panel">
        <div className="hero-copy">
          <p className="eyebrow">Zero-trust RAG</p>
          <h1>Backend-enforced document access for every retrieval.</h1>
          <p className="lede">
            Auth0 authenticates the user, the backend validates the JWT with JWKS, filters Qdrant by role, and only then calls the LLM.
          </p>
        </div>

        <div className="session-card">
          {isAuthenticated ? (
            <>
              <p className="session-card__label">Signed in as</p>
              <h2>{user?.name || user?.email || 'Authenticated user'}</h2>
              <div style={{ margin: '8px 0' }}>
                <strong>Roles:</strong> {roles.length > 0 ? roles.join(', ') : <span style={{color: '#aaa'}}>None found</span>}
              </div>
              <button type="button" className="button button--ghost" onClick={() => logout({ logoutParams: { returnTo: window.location.origin } })}>
                Log out
              </button>
            </>
          ) : (
            <>
              <p className="session-card__label">Authentication required</p>
              <h2>Sign in to query authorized documents.</h2>
              <button type="button" className="button" onClick={() => loginWithRedirect()}>
                Log in with Auth0
              </button>
            </>
          )}
        </div>
      </section>

      <section className="query-panel">
        <form onSubmit={handleSubmit} className="query-form">
          <label htmlFor="query">Ask a question</label>
          <textarea
            id="query"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Example: What is the salary policy for HR managers?"
            rows={6}
            disabled={!isAuthenticated || submitting}
          />
          <div className="query-form__actions">
            <button type="submit" className="button" disabled={!isAuthenticated || submitting || !query.trim()}>
              {submitting ? 'Retrieving...' : 'Query secure RAG'}
            </button>
          </div>
        </form>

        {error ? <p className="error-banner">{error}</p> : null}

        {answer ? (
          <article className="answer-card">
            <h3>Answer</h3>
            <p>{answer}</p>
          </article>
        ) : null}

        {sources.length > 0 ? (
          <section className="sources-panel">
            <h3>Sources</h3>
            <div className="sources-grid">
              {sources.map((source) => (
                <SourceCard key={`${source.document_id}-${source.page}-${source.score}`} source={source} />
              ))}
            </div>
          </section>
        ) : null}
      </section>
    </main>
  );
}
