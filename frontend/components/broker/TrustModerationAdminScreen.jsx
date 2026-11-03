import { useCallback, useEffect, useState } from 'react';
import { withBrokerTranslations } from './i18n/withBrokerTranslations';

function TrustModerationAdminScreen({ token }) {
  const apiBase = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1').replace('/api/v1', '/api/broker/v1');
  const [cases, setCases] = useState([]);
  const [resolutions, setResolutions] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [status, setStatus] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const response = await fetch(`${apiBase}/admin/moderation-cases?status=open&limit=100&offset=0`, { headers: { Authorization: `Bearer ${token}` } });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || 'Unable to load broker moderation cases.');
      setCases(body);
    } catch (loadError) {
      setError(loadError.message || 'Broker moderation service is offline.');
    } finally {
      setLoading(false);
    }
  }, [apiBase, token]);

  useEffect(() => { load(); }, [load]);

  async function resolveCase(caseId, fallbackResolution = '') {
    setError('');
    setStatus('');
    try {
      const response = await fetch(`${apiBase}/admin/moderation-cases/${caseId}/resolve`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ resolution: resolutions[caseId] || fallbackResolution })
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || 'Unable to resolve this case.');
      setStatus(`Case #${caseId} resolved.`);
      await load();
    } catch (actionError) {
      setError(actionError.message || 'Broker moderation service is offline.');
    }
  }

  async function decideReview(caseRow, decision) {
    if (caseRow.resource_type !== 'review') return;
    setError('');
    try {
      const response = await fetch(`${apiBase}/admin/reviews/${caseRow.resource_id}/decision`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ decision, notes: `Moderation case #${caseRow.id}` })
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || 'Unable to moderate this review.');
      const resolutionResponse = await fetch(`${apiBase}/admin/moderation-cases/${caseRow.id}/resolve`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ resolution: `Review ${decision} by platform moderation.` })
      });
      const resolutionBody = await resolutionResponse.json().catch(() => ({}));
      if (!resolutionResponse.ok) throw new Error(resolutionBody.detail || 'Review decision saved, but the case could not be resolved.');
      setStatus(`Review #${caseRow.resource_id} ${decision === 'publish' ? 'published' : 'rejected'} and case #${caseRow.id} resolved.`);
      await load();
    } catch (actionError) {
      setError(actionError.message || 'Broker moderation service is offline.');
    }
  }

  return (
    <section className="admin-tab-content broker-trust-admin" aria-labelledby="broker-trust-admin-title">
      <header className="section-header-flex"><div><h2 id="broker-trust-admin-title">Broker trust moderation</h2><p className="section-desc">Review integrity alerts and broker appeals across organizations.</p></div><button className="btn btn-primary" type="button" disabled={loading} onClick={load}>Refresh</button></header>
      {error && <p className="error" role="alert">{error}</p>}{status && <p role="status">{status}</p>}
      {loading ? <p role="status">Loading cases…</p> : !cases.length ? <p>No open broker trust cases.</p> : <div className="broker-admin-case-list">{cases.map((caseRow) => <article className="broker-admin-case" key={caseRow.id}>
        <header><strong>{caseRow.case_type.replaceAll('_', ' ')}</strong><span>Organization #{caseRow.organization_id} · {caseRow.severity}</span></header>
        <p>{caseRow.reason}</p><p>Resource: {caseRow.resource_type} #{caseRow.resource_id} · Actor #{caseRow.actor_user_id ?? 'system'}</p>
        {caseRow.case_type === 'review_appeal' && <div className="broker-admin-case-actions"><button className="btn btn-primary" type="button" onClick={() => decideReview(caseRow, 'publish')}>Uphold review</button><button className="link-btn" type="button" onClick={() => decideReview(caseRow, 'reject')}>Remove review</button></div>}
        <label htmlFor={`case-resolution-${caseRow.id}`}>Resolution notes<textarea id={`case-resolution-${caseRow.id}`} maxLength="1000" value={resolutions[caseRow.id] || ''} onChange={(event) => setResolutions((current) => ({ ...current, [caseRow.id]: event.target.value }))} /></label>
        <button className="link-btn" type="button" onClick={() => resolveCase(caseRow.id)}>Resolve case</button>
      </article>)}</div>}
    </section>
  );
}

export default withBrokerTranslations(TrustModerationAdminScreen);
