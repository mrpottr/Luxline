import React, { useCallback, useEffect, useState } from 'react'; // eslint-disable-line no-unused-vars
import { withBrokerTranslations } from '../i18n/withBrokerTranslations';

const stages = ['new', 'contacted', 'qualified', 'lost', 'closed'];

function createIdempotencyKey() {
  return globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function leadAge(lead) {
  const elapsedMinutes = Math.max(0, Math.floor((Date.now() - new Date(lead.created_at).getTime()) / 60000));
  if (lead.stage === 'new' && elapsedMinutes >= 60) return { label: `Overdue · ${Math.floor(elapsedMinutes / 60)}h`, urgent: true };
  if (lead.stage === 'new' && elapsedMinutes >= 15) return { label: `Waiting ${elapsedMinutes}m`, urgent: false };
  if (elapsedMinutes >= 1440) return { label: `${Math.floor(elapsedMinutes / 1440)}d old`, urgent: false };
  return { label: 'Fresh lead', urgent: false };
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

  async function scheduleViewing(leadId) {
    const when = window.prompt('Viewing date and time (for example: 2026-11-14 14:30)');
    if (!when?.trim()) return;
    const dueAt = new Date(when);
    if (Number.isNaN(dueAt.getTime())) {
      setError('Enter a valid viewing date and time.');
      return;
    }
    const details = window.prompt('Viewing details (location, meeting point, or note)') || 'Viewing appointment requested';
    try {
      const response = await fetch(`${apiBase}/leads/${leadId}/activities`, {
        method: 'POST', headers: { ...headers, 'Idempotency-Key': createIdempotencyKey() },
        body: JSON.stringify({ activity_type: 'viewing', body: details.trim(), due_at: dueAt.toISOString() }),
      });
      if (!response.ok) throw new Error('Unable to schedule the viewing.');
      setStatus(`Viewing scheduled for ${dueAt.toLocaleString()}.`);
    } catch (viewingError) {
      setError(viewingError.message);
    }
  }

  const workload = members.filter((member) => member.is_active).map((member) => ({
    member,
    leads: leads.filter((lead) => lead.assigned_member_id === member.user_id),
  })).filter(({ leads: assigned }) => assigned.length);

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
        {workload.length > 0 && (
          <div className="broker-analytics-grid" aria-label="Current agent workload">
            {workload.map(({ member, leads: assigned }) => {
              const overdue = assigned.filter((lead) => leadAge(lead).urgent).length;
              return <article className="broker-analytics-card" key={member.user_id}>
                <span>{member.display_name || member.email || `Agent ${member.user_id}`}</span>
                <strong>{assigned.length} leads{overdue ? ` · ${overdue} overdue` : ''}</strong>
              </article>;
            })}
          </div>
        )}
        <div className="broker-inbox-actions" aria-label="Lead pagination">
          <button type="button" disabled={offset === 0 || loading} onClick={() => setOffset((value) => Math.max(0, value - pageSize))}>Previous</button>
          <span>Showing {leads.length ? offset + 1 : 0}–{offset + leads.length}</span>
          <button type="button" disabled={leads.length < pageSize || loading} onClick={() => setOffset((value) => value + pageSize)}>Next</button>
        </div>
        {!leads.length ? <p>No buyer leads yet. New listing inquiries will appear here.</p> : (
          <div className="broker-lead-grid">
            {leads.map((lead) => (
              <article className="broker-card broker-lead-card" key={lead.id}>
                {(() => {
                  const age = leadAge(lead);
                  return <span className="broker-badge-pill" style={age.urgent ? { color: '#ff8b8b', borderColor: '#b54b4b' } : undefined}>{age.label}</span>;
                })()}
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
                  <button type="button" onClick={() => scheduleViewing(lead.id)}>Schedule viewing</button>
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
