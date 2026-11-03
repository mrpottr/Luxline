import React, { useCallback, useEffect, useState } from 'react'; // eslint-disable-line no-unused-vars
import { withBrokerTranslations } from '../i18n/withBrokerTranslations';

function createIdempotencyKey() {
  return globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function InboxScreen({ token, apiBase }) {
  const [leads, setLeads] = useState([]);
  const [selectedLead, setSelectedLead] = useState(null);
  const [messages, setMessages] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [body, setBody] = useState('');
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const [status, setStatus] = useState('');
  const [offset, setOffset] = useState(0);
  const pageSize = 50;
  const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };

  const loadInbox = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [leadResponse, templateResponse] = await Promise.all([
        fetch(`${apiBase}/leads?limit=${pageSize}&offset=${offset}&sort=-created_at`, { headers }),
        fetch(`${apiBase}/inbox/templates?limit=100`, { headers }),
      ]);
      if (!leadResponse.ok) throw new Error(leadResponse.status === 403 ? 'You do not have permission to view the inbox.' : 'Unable to load the inbox.');
      setLeads(await leadResponse.json());
      setTemplates(templateResponse.ok ? await templateResponse.json() : []);
    } catch (loadError) {
      setError(loadError.message || 'Inbox is offline. Retry when connected.');
    } finally {
      setLoading(false);
    }
  }, [apiBase, offset, token]);

  const loadMessages = useCallback(async (lead) => {
    setSelectedLead(lead);
    setError('');
    try {
      const response = await fetch(`${apiBase}/inbox/${lead.id}/messages`, { headers });
      if (!response.ok) throw new Error('Unable to load this conversation.');
      setMessages(await response.json());
    } catch (loadError) {
      setError(loadError.message);
      setMessages([]);
    }
  }, [apiBase, token]);

  useEffect(() => { loadInbox(); }, [loadInbox]);

  async function sendMessage(event) {
    event.preventDefault();
    if (!selectedLead || !body.trim()) return;
    setSending(true);
    setError('');
    setStatus('');
    try {
      const response = await fetch(`${apiBase}/inbox/${selectedLead.id}/messages`, {
        method: 'POST', headers: { ...headers, 'Idempotency-Key': createIdempotencyKey() },
        body: JSON.stringify({ body: body.trim() }),
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(result.detail || 'Unable to send this message.');
      setMessages((current) => [...current, result]);
      setBody('');
      setStatus('Message sent to the Luxline conversation.');
    } catch (sendError) {
      setError(sendError.message || 'Message could not be sent.');
    } finally {
      setSending(false);
    }
  }

  async function saveTemplate(event) {
    event.preventDefault();
    const title = window.prompt('Template name');
    if (!title?.trim() || !body.trim()) return;
    try {
      const response = await fetch(`${apiBase}/inbox/templates`, {
        method: 'POST', headers: { ...headers, 'Idempotency-Key': createIdempotencyKey() },
        body: JSON.stringify({ title: title.trim(), body: body.trim() }),
      });
      if (!response.ok) throw new Error('Unable to save this reply template.');
      setStatus('Reply template saved.');
      await loadInbox();
    } catch (saveError) {
      setError(saveError.message);
    }
  }

  if (loading) return <div className="broker-card" role="status">Loading inbox…</div>;

  return (
    <section className="broker-card broker-inbox" aria-labelledby="broker-inbox-title">
      <header className="broker-card-header">
        <span className="broker-badge-pill">Buyer conversations</span>
        <h1 className="broker-card-title" id="broker-inbox-title">Direct Inbox</h1>
      </header>
      {error && <p role="alert">{error}</p>}
      {status && <p role="status">{status}</p>}
      <div className="broker-inbox-actions" aria-label="Conversation pagination">
        <button type="button" disabled={offset === 0 || loading} onClick={() => setOffset((value) => Math.max(0, value - pageSize))}>Previous</button>
        <span>Showing {leads.length ? offset + 1 : 0}–{offset + leads.length}</span>
        <button type="button" disabled={leads.length < pageSize || loading} onClick={() => setOffset((value) => value + pageSize)}>Next</button>
      </div>
      {leads.length === 0 ? <p>No buyer conversations yet.</p> : (
        <div className="broker-inbox-layout">
          <nav className="broker-inbox-list" aria-label="Buyer conversations">
            {leads.map((lead) => (
              <button type="button" key={lead.id} className={selectedLead?.id === lead.id ? 'active' : ''} onClick={() => loadMessages(lead)}>
                <strong>{lead.buyer_name}</strong><span>Listing #{lead.listing_id}</span><small>{lead.stage}</small>
              </button>
            ))}
          </nav>
          <div className="broker-inbox-thread">
            {!selectedLead ? <p>Select a conversation to read and reply.</p> : (
              <>
                <h2>{selectedLead.buyer_name}</h2>
                <p>{selectedLead.buyer_email}</p>
                {selectedLead.buyer_id == null && <p>This inquiry has no buyer account, so it cannot receive a platform conversation reply.</p>}
                <div className="broker-message-list" aria-live="polite">
                  {messages.map((message) => (
                    <article key={message.id} className={`broker-message broker-message-${message.sender_type}`}>
                      <p>{message.body}</p><small>{message.sender_type === 'agent' ? 'Your team' : 'Buyer'} · {new Date(message.created_at).toLocaleString()}</small>
                    </article>
                  ))}
                </div>
                <label htmlFor="broker-reply-template">Saved reply</label>
                <select id="broker-reply-template" defaultValue="" onChange={(event) => {
                  const template = templates.find((item) => String(item.id) === event.target.value);
                  if (template) setBody(template.body
                    .replaceAll('{buyer_name}', selectedLead.buyer_name)
                    .replaceAll('{listing_id}', String(selectedLead.listing_id)));
                }}>
                  <option value="">Choose a template</option>
                  {templates.map((template) => <option value={template.id} key={template.id}>{template.title}</option>)}
                </select>
                <form onSubmit={sendMessage}>
                  <label htmlFor="broker-message-body">Message</label>
                  <textarea id="broker-message-body" rows="4" maxLength="5000" required value={body} onChange={(event) => setBody(event.target.value)} />
                  <div className="broker-inbox-actions">
                  <button type="submit" className="broker-btn-gold" disabled={sending || selectedLead.buyer_id == null}>{sending ? 'Sending…' : 'Send message'}</button>
                    <button type="button" onClick={saveTemplate} disabled={!body.trim()}>Save as reply template</button>
                  </div>
                </form>
              </>
            )}
          </div>
        </div>
      )}
    </section>
  );
}

export default withBrokerTranslations(InboxScreen);
