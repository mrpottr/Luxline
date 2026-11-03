import React, { useCallback, useEffect, useState } from 'react'; // eslint-disable-line no-unused-vars
import { withBrokerTranslations } from '../i18n/withBrokerTranslations';

function defaultRange() {
  const to = new Date();
  const from = new Date(to);
  from.setDate(from.getDate() - 29);
  const format = (value) => `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}-${String(value.getDate()).padStart(2, '0')}`;
  return { date_from: format(from), date_to: format(to) };
}

function AnalyticsScreen({ token, apiBase }) {
  const [range, setRange] = useState(defaultRange);
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [status, setStatus] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const params = new URLSearchParams(range);
      const response = await fetch(`${apiBase}/analytics?${params}`, { headers: { Authorization: `Bearer ${token}` } });
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(response.status === 403 ? 'You do not have permission to view this analytics report.' : body.detail || 'Unable to load analytics.');
      }
      setReport(await response.json());
    } catch (loadError) {
      setError(loadError.message || 'Analytics are offline. Retry when connected.');
    } finally {
      setLoading(false);
    }
  }, [apiBase, range, token]);

  useEffect(() => { load(); }, [load]);

  async function exportCsv(dimension) {
    setError('');
    setStatus('');
    try {
      const params = new URLSearchParams({ ...range, dimension, limit: '500', offset: '0' });
      const response = await fetch(`${apiBase}/analytics/export.csv?${params}`, { headers: { Authorization: `Bearer ${token}` } });
      if (!response.ok) throw new Error(response.status === 403 ? 'You do not have permission to export analytics.' : 'Unable to export analytics.');
      const url = URL.createObjectURL(await response.blob());
      const link = document.createElement('a');
      link.href = url;
      link.download = `broker-${dimension}-analytics.csv`;
      link.click();
      URL.revokeObjectURL(url);
      setStatus('Analytics export downloaded.');
    } catch (exportError) {
      setError(exportError.message || 'Export is offline. Retry when connected.');
    }
  }

  return (
    <section className="broker-card" aria-labelledby="broker-analytics-title">
      <header className="broker-card-header">
        <span className="broker-badge-pill">Performance</span>
        <h1 id="broker-analytics-title" className="broker-card-title">Analytics</h1>
        <p className="broker-card-subtitle">Lead, response, and phone-reveal performance for your broker organization.</p>
      </header>
      <form className="broker-analytics-filters" onSubmit={(event) => { event.preventDefault(); load(); }}>
        <label>From<input type="date" required value={range.date_from} onChange={(event) => setRange({ ...range, date_from: event.target.value })} /></label>
        <label>To<input type="date" required value={range.date_to} onChange={(event) => setRange({ ...range, date_to: event.target.value })} /></label>
        <button type="submit" disabled={loading}>Apply range</button>
        <button type="button" onClick={() => exportCsv('listing')}>Export listings CSV</button>
        <button type="button" onClick={() => exportCsv('agent')}>Export agents CSV</button>
      </form>
      {error && <p role="alert">{error}</p>}
      {status && <p role="status">{status}</p>}
      {loading && <p role="status">Loading analytics…</p>}
      {!loading && report && (
        <>
          <div className="broker-analytics-grid">
            <article className="broker-analytics-card"><span>Leads</span><strong>{report.totals.leads}</strong></article>
            <article className="broker-analytics-card"><span>Broker replies</span><strong>{report.totals.replies}</strong></article>
            <article className="broker-analytics-card"><span>Phone reveals</span><strong>{report.totals.phone_reveals}</strong></article>
            <article className="broker-analytics-card"><span>Mean first response</span><strong>{report.totals.average_response_seconds == null ? '—' : `${Math.round(report.totals.average_response_seconds / 60)} min`}</strong></article>
            <article className="broker-analytics-card"><span>Qualified conversion</span><strong>{(report.totals.conversion_rate * 100).toFixed(1)}%</strong></article>
            <article className="broker-analytics-card"><span>Listing views</span><strong>{report.totals.views}</strong></article>
            <article className="broker-analytics-card"><span>Click-through rate</span><strong>{report.totals.click_through_rate == null ? 'Not tracked' : `${(report.totals.click_through_rate * 100).toFixed(1)}%`}</strong></article>
          </div>
          <AnalyticsTable title="Per listing" rows={report.by_listing} idKey="listing_id" empty="No listing activity in this date range." />
          <AnalyticsTable title="Per agent" rows={report.by_agent} idKey="agent_id" empty="No assigned-agent activity in this date range." />
        </>
      )}
    </section>
  );
}

function AnalyticsTable({ title, rows, idKey, empty }) {
  return (
    <section className="broker-analytics-table-section" aria-label={title}>
      <h2>{title}</h2>
      {!rows.length ? <p>{empty}</p> : (
        <div className="broker-table-scroll">
          <table className="broker-analytics-table">
            <thead><tr><th>{idKey === 'listing_id' ? 'Listing' : 'Agent'}</th><th>Impressions</th><th>Views</th><th>CTR</th><th>Leads</th><th>Replies</th><th>Phone reveals</th><th>Avg response</th><th>Conversion</th></tr></thead>
            <tbody>{rows.map((row) => (
              <tr key={row[idKey]}>
                <th scope="row">#{row[idKey]}</th><td>{row.impressions}</td><td>{row.views}</td><td>{row.click_through_rate == null ? '—' : `${(row.click_through_rate * 100).toFixed(1)}%`}</td><td>{row.leads}</td><td>{row.replies}</td><td>{row.phone_reveals}</td>
                <td>{row.average_response_seconds == null ? '—' : `${Math.round(row.average_response_seconds / 60)} min`}</td>
                <td>{(row.conversion_rate * 100).toFixed(1)}%</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      )}
    </section>
  );
}

export default withBrokerTranslations(AnalyticsScreen);
