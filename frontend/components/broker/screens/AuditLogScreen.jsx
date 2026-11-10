import { useCallback, useEffect, useState } from 'react';
import { withBrokerTranslations } from '../i18n/withBrokerTranslations';
import { responseList } from './responseUtils.mjs';

function AuditLogScreen({ token, apiBase }) {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const response = await fetch(`${apiBase}/audit?limit=50&offset=0`, { headers: { Authorization: `Bearer ${token}` } });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || 'Unable to load the audit log.');
      setRows(responseList(body, 'entries'));
    } catch (loadError) {
      setError(loadError.message || 'Audit log is offline. Retry when connected.');
    } finally {
      setLoading(false);
    }
  }, [apiBase, token]);

  useEffect(() => { load(); }, [load]);

  return (
    <section className="broker-card" aria-labelledby="broker-audit-title">
      <header className="broker-card-header"><span className="broker-badge-pill">Governance</span><h1 id="broker-audit-title" className="broker-card-title">Audit log</h1><p className="broker-card-subtitle">Append-only history of broker approvals, role changes, trust decisions, credit movements, and exports.</p></header>
      {error && <p className="broker-form-error" role="alert">{error}</p>}
      {loading ? <p role="status">Loading audit records…</p> : !rows.length ? <p>No audit records are available.</p> : <div className="broker-table-scroll"><table className="broker-analytics-table"><thead><tr><th>When</th><th>Actor</th><th>Action</th><th>Resource</th><th>From</th><th>Change</th></tr></thead><tbody>{rows.map((row) => <tr key={row.id}><td>{new Date(row.created_at).toLocaleString()}</td><td>{row.actor_user_id ?? 'System'} · {row.actor_role || 'system'}</td><td>{row.action}</td><td>{row.resource_type} #{row.resource_id ?? '—'}</td><td>{row.source_ip || '—'}</td><td><details><summary>View details</summary><pre>{JSON.stringify({ before: row.before_state, after: row.after_state, metadata: row.metadata }, null, 2)}</pre></details></td></tr>)}</tbody></table></div>}
    </section>
  );
}

export default withBrokerTranslations(AuditLogScreen);
