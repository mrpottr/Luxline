import { useCallback, useEffect, useState } from 'react';
import { withBrokerTranslations } from './i18n/withBrokerTranslations';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
const BROKER_API_BASE = API_BASE.replace('/api/v1', '/api/broker/v1');

function BuyerReviewScreen() {
  const token = localStorage.getItem('luxline_token') || '';
  const queryOrganization = new URLSearchParams(window.location.search).get('organization_id') || '';
  const [organizationId, setOrganizationId] = useState(queryOrganization);
  const [leads, setLeads] = useState([]);
  const [drafts, setDrafts] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [status, setStatus] = useState('');

  const loadLeads = useCallback(async () => {
    if (!organizationId) return;
    setLoading(true);
    setError('');
    try {
      const response = await fetch(`${BROKER_API_BASE}/buyer/inbox?organization_id=${encodeURIComponent(organizationId)}&limit=100&offset=0`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || 'Unable to load your completed inquiries.');
      setLeads(body);
    } catch (loadError) {
      setError(loadError.message || 'Buyer review service is offline.');
    } finally {
      setLoading(false);
    }
  }, [organizationId, token]);

  useEffect(() => { if (queryOrganization && token) loadLeads(); }, [loadLeads, queryOrganization, token]);

  async function submitReview(leadId) {
    const draft = drafts[leadId] || {};
    setError('');
    setStatus('');
    try {
      const response = await fetch(`${BROKER_API_BASE}/buyer/reviews?organization_id=${encodeURIComponent(organizationId)}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json', Authorization: `Bearer ${token}`,
          'Idempotency-Key': globalThis.crypto?.randomUUID?.() || `review-${Date.now()}-${leadId}`
        },
        body: JSON.stringify({ lead_id: leadId, rating: Number(draft.rating), body: draft.body || '', public_consent: Boolean(draft.public_consent) })
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || 'Unable to submit your review.');
      setStatus('Your review was submitted for moderation.');
      setLeads((current) => current.filter((lead) => lead.id !== leadId));
    } catch (submitError) {
      setError(submitError.message || 'Buyer review service is offline.');
    }
  }

  function setDraft(leadId, values) {
    setDrafts((current) => ({ ...current, [leadId]: { ...current[leadId], ...values } }));
  }

  if (!token) return <main className="broker-card"><h1>Sign in to review a broker</h1><p>You must be signed in as the buyer who completed the inquiry.</p><a href="/?login=1" className="broker-btn-gold">Sign in</a></main>;

  return (
    <main className="broker-card broker-buyer-review-page" aria-labelledby="buyer-review-title">
      <header className="broker-card-header"><span className="broker-badge-pill">Buyer feedback</span><h1 id="buyer-review-title" className="broker-card-title">Review a completed purchase</h1><p className="broker-card-subtitle">Only your closed, consented broker inquiries are eligible. Reviews are checked before public display.</p></header>
      {error && <p className="broker-form-error" role="alert">{error}</p>}{status && <p className="broker-form-success" role="status">{status}</p>}
      <form className="broker-trust-form" onSubmit={(event) => { event.preventDefault(); loadLeads(); }}>
        <label htmlFor="buyer-review-organization">Broker organization ID</label>
        <input id="buyer-review-organization" type="number" min="1" required value={organizationId} onChange={(event) => setOrganizationId(event.target.value)} />
        <button className="broker-btn-secondary" type="submit" disabled={loading}>{loading ? 'Loading…' : 'Load eligible inquiries'}</button>
      </form>
      {loading ? <p role="status">Loading completed inquiries…</p> : !leads.length ? <p>No eligible completed inquiries were found for this organization.</p> : <div className="broker-review-list">{leads.filter((lead) => lead.stage === 'closed').map((lead) => {
        const draft = drafts[lead.id] || {};
        return <article className="broker-review-card" key={lead.id}>
          <h2>Listing #{lead.listing_id}</h2><p>Inquiry completed {new Date(lead.created_at).toLocaleDateString()}</p>
          <label htmlFor={`buyer-rating-${lead.id}`}>Rating</label>
          <select id={`buyer-rating-${lead.id}`} value={draft.rating || ''} onChange={(event) => setDraft(lead.id, { rating: event.target.value })}>
            <option value="">Choose a rating</option><option value="5">5 · Excellent</option><option value="4">4 · Good</option><option value="3">3 · Average</option><option value="2">2 · Poor</option><option value="1">1 · Very poor</option>
          </select>
          <label htmlFor={`buyer-review-body-${lead.id}`}>Your review</label>
          <textarea id={`buyer-review-body-${lead.id}`} minLength="10" maxLength="3000" value={draft.body || ''} onChange={(event) => setDraft(lead.id, { body: event.target.value })} />
          <label className="broker-review-consent"><input type="checkbox" checked={Boolean(draft.public_consent)} onChange={(event) => setDraft(lead.id, { public_consent: event.target.checked })} /> I agree that this review can be displayed publicly after moderation.</label>
          <button className="broker-btn-gold" type="button" disabled={!draft.rating || (draft.body || '').trim().length < 10 || !draft.public_consent} onClick={() => submitReview(lead.id)}>Submit review</button>
        </article>;
      })}</div>}
    </main>
  );
}

export default withBrokerTranslations(BuyerReviewScreen);
