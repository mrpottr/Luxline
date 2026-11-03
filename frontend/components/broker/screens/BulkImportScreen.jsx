import React, { useState } from 'react';

function newIdempotencyKey() {
  return globalThis.crypto?.randomUUID?.() || `broker-import-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

export default function BulkImportScreen({ token, apiBase, onDone }) {
  const [csvContent, setCsvContent] = useState('');
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [complete, setComplete] = useState(false);
  const [idempotencyKey, setIdempotencyKey] = useState(newIdempotencyKey);

  async function validate() {
    setLoading(true);
    setError('');
    setReport(null);
    try {
      const response = await fetch(`${apiBase}/listings/bulk/validate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ csv_content: csvContent }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Unable to validate this CSV');
      setReport(data);
    } catch (err) {
      setError(err.message || 'Connection unavailable. Check your connection and retry.');
    } finally {
      setLoading(false);
    }
  }

  async function commitImport() {
    setLoading(true);
    setError('');
    try {
      const response = await fetch(`${apiBase}/listings/bulk/import`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
          'Idempotency-Key': idempotencyKey,
        },
        body: JSON.stringify({ csv_content: csvContent }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Unable to import listings');
      if (!data.is_valid || !data.committed) {
        setReport(data);
        throw new Error('The file did not pass validation. Review the row report and retry.');
      }
      setComplete(true);
      setReport(data);
    } catch (err) {
      setError(err.message || 'Connection unavailable. Check your connection and retry.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="broker-card" aria-labelledby="broker-import-title">
      <h2 id="broker-import-title" className="broker-card-title">CSV Listing Import</h2>
      <p className="broker-card-subtitle">Paste CSV with title, category, price, currency, location_country, and location_city columns.</p>
      <label htmlFor="broker-import-csv" style={{ display: 'block', margin: '16px 0 8px', color: '#9da3af' }}>CSV content</label>
      <textarea
        id="broker-import-csv"
        rows={12}
        value={csvContent}
        onChange={(event) => { setCsvContent(event.target.value); setReport(null); setComplete(false); setIdempotencyKey(newIdempotencyKey()); }}
        style={{ width: '100%', padding: '12px', background: '#1a1d24', color: '#fff', border: '1px solid #262930', borderRadius: '6px' }}
        disabled={loading || complete}
      />
      {error && <p role="alert" style={{ color: '#ef4444' }}>{error}</p>}
      {report && (
        <div role="status" style={{ marginTop: '16px' }}>
          <p>{complete ? `Imported ${report.imported_listing_ids?.length || 0} draft listings.` : `${report.valid_rows} valid, ${report.invalid_rows} invalid of ${report.total_rows} rows.`}</p>
          {report.error && <p role="alert">{report.error}</p>}
          {report.row_reports?.map((row) => (
            <div key={row.row_index} style={{ padding: '8px 0', color: row.is_valid ? '#22c55e' : '#ef4444' }}>
              Row {row.row_index}: {row.title} {row.errors?.length ? `— ${row.errors.join('; ')}` : '— valid'}
            </div>
          ))}
        </div>
      )}
      <div style={{ display: 'flex', gap: '12px', marginTop: '16px' }}>
        <button type="button" onClick={onDone} disabled={loading}>Cancel</button>
        {!complete && <button type="button" onClick={validate} disabled={loading || !csvContent.trim()}>{loading ? 'Working…' : 'Validate CSV'}</button>}
        {report?.is_valid && !complete && <button type="button" onClick={commitImport} disabled={loading}>Import drafts</button>}
        {complete && <button type="button" onClick={onDone}>Back to listings</button>}
      </div>
    </section>
  );
}
