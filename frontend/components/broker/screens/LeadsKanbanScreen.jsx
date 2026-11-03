import React, { useCallback, useEffect, useState } from 'react'; // eslint-disable-line no-unused-vars
import { withBrokerTranslations } from '../i18n/withBrokerTranslations';

const stages = ['new', 'contacted', 'qualified', 'lost', 'closed'];

function createIdempotencyKey() {
  return globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function LeadsKanbanScreen({ token, apiBase }) {
  const [leads, setLeads] = useState([]);
  const [members, setMembers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [status, setStatus] = useState('');
  const [offset, setOffset] = useState(0);
  const pageSize = 50;

  const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };
  const loadLeads = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const response = await fetch(`${apiBase}/leads?limit=${pageSize}&offset=${offset}&sort=-created_at`, { headers });
      if (!response.ok) throw new Error(response.status === 403 ? 'You do not have permission to view these leads.' : 'Unable to load leads.');
      setLeads(await response.json());
    } catch (loadError) {
      setError(loadError.message || 'Broker leads are offline. Retry when connected.');
    } finally {
      setLoading(false);
    }
  }, [apiBase, offset, token]);

  useEffect(() => {
    loadLeads();
    fetch(`${apiBase}/team/members`, { headers })
      .then((response) => response.ok ? response.json() : [])
      .then(setMembers)
      .catch(() => setMembers([]));
  }, [apiBase, loadLeads, token]);

  async function updateLead(leadId, path, payload, successMessage) {
    setError('');
    setStatus('');
    try {
      const response = await fetch(`${apiBase}/leads/${leadId}/${path}`, {
        method: 'PATCH', headers, body: JSON.stringify(payload),
      });
      if (!response.ok) {
        const detail = await response.json().catch(() => ({}));
        throw new Error(detail.detail || 'Unable to update this lead.');
      }
      setStatus(successMessage);
      await loadLeads();
    } catch (updateError) {
      setError(updateError.message || 'The update could not be saved.');
    }
  }

  async function addNote(leadId) {
    const body = window.prompt('Add an internal note');
    if (!body?.trim()) return;
    try {
      const response = await fetch(`${apiBase}/leads/${leadId}/activities`, {
        method: 'POST', headers: { ...headers, 'Idempotency-Key': createIdempotencyKey() },
        body: JSON.stringify({ activity_type: 'note', body: body.trim() }),
      });
      if (!response.ok) throw new Error('Unable to add the note.');
      setStatus('Note added.');
    } catch (noteError) {
      setError(noteError.message);
    }
  }

  if (loading) return <div className="broker-card" role="status">Loading leads…</div>;
  if (error && !leads.length) return <div className="broker-card" role="alert"><p>{error}</p><button type="button" className="broker-btn-gold" onClick={loadLeads}>Retry</button></div>;

  return (
    <section aria-labelledby="broker-leads-title">
      <div className="broker-card">
        <div className="broker-card-header">
          <span className="broker-badge-pill">Buyer pipeline</span>
          <h1 className="broker-card-title" id="broker-leads-title">Leads &amp; CRM</h1>
          <p className="broker-card-subtitle">New seller inquiries are imported into this organization when the lead list refreshes.</p>
          <button type="button" onClick={loadLeads}>Refresh leads</button>
        </div>
        {error && <p role="alert">{error}</p>}
        {status && <p role="status">{status}</p>}
        <div className="broker-inbox-actions" aria-label="Lead pagination">
          <button type="button" disabled={offset === 0 || loading} onClick={() => setOffset((value) => Math.max(0, value - pageSize))}>Previous</button>
          <span>Showing {leads.length ? offset + 1 : 0}–{offset + leads.length}</span>
          <button type="button" disabled={leads.length < pageSize || loading} onClick={() => setOffset((value) => value + pageSize)}>Next</button>
        </div>
        {!leads.length ? <p>No buyer leads yet. New listing inquiries will appear here.</p> : (
          <div className="broker-lead-grid">
            {leads.map((lead) => (
              <article className="broker-card broker-lead-card" key={lead.id}>
                <div className="broker-lead-heading">
                  <h2>{lead.buyer_name}</h2>
                  <span>{lead.score} / 100</span>
                </div>
                <p><a href={`mailto:${lead.buyer_email}`}>{lead.buyer_email}</a>{lead.buyer_phone ? ` · ${lead.buyer_phone}` : ''}</p>
                <p>{lead.initial_message}</p>
                <p className="broker-card-subtitle">Listing #{lead.listing_id} · {new Date(lead.created_at).toLocaleString()}</p>
                <div className="broker-lead-actions">
                  <label>Stage
                    <select value={lead.stage} onChange={(event) => updateLead(lead.id, 'stage', { stage: event.target.value }, 'Lead stage updated.')}>
                      {stages.map((stage) => <option key={stage} value={stage}>{stage}</option>)}
                    </select>
                  </label>
                  <label>Assigned agent
                    <select
                      value={lead.assigned_member_id || ''}
                      onChange={(event) => updateLead(lead.id, 'assign', { member_user_id: Number(event.target.value) }, 'Lead assigned.')}
                    >
                      <option value="" disabled>Select an agent</option>
                      {members.filter((member) => member.is_active).map((member) => (
                        <option value={member.user_id} key={member.user_id}>{member.display_name || member.email || member.user_id}</option>
                      ))}
                    </select>
                  </label>
                  <button type="button" className="broker-btn-gold" onClick={() => addNote(lead.id)}>Add note</button>
                  <button type="button" onClick={() => updateLead(lead.id, 'spam', { spam_flag: !lead.spam_flag }, lead.spam_flag ? 'Lead marked as legitimate.' : 'Lead marked as spam')}>
                    {lead.spam_flag ? 'Mark legitimate' : 'Mark spam'}
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

export default withBrokerTranslations(LeadsKanbanScreen);
