import React, { useCallback, useEffect, useState } from 'react'; // eslint-disable-line no-unused-vars
import { withBrokerTranslations } from '../i18n/withBrokerTranslations';

function dateWindow() {
  const to = new Date();
  const from = new Date(to);
  from.setDate(from.getDate() - 29);
  const format = (value) => `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}-${String(value.getDate()).padStart(2, '0')}`;
  return { date_from: format(from), date_to: format(to) };
}

function DashboardOverviewScreen({ token, apiBase }) {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const params = new URLSearchParams(dateWindow());
      const response = await fetch(`${apiBase}/analytics?${params}`, { headers: { Authorization: `Bearer ${token}` } });
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(response.status === 403 ? 'Analytics are unavailable for this account.' : body.detail || 'Unable to load broker analytics.');
      }
      setReport(await response.json());
    } catch (loadError) {
      setError(loadError.message || 'Analytics are offline. Retry when connected.');
    } finally {
      setLoading(false);
    }
  }, [apiBase, token]);

  useEffect(() => { load(); }, [load]);

  if (loading) return <section className="broker-card" role="status">Loading dashboard metrics…</section>;
  if (error) return <section className="broker-card" role="alert"><p>{error}</p><button type="button" onClick={load}>Retry</button></section>;
  if (!report) return <section className="broker-card"><p>No analytics are available yet.</p></section>;

  const values = report.totals;
  const cards = [
    ['Buyer leads', values.leads],
    ['Average first response', values.average_response_seconds == null ? '—' : `${Math.round(values.average_response_seconds / 60)} min`],
    ['Phone reveals', values.phone_reveals],
    ['Qualified conversion', `${(values.conversion_rate * 100).toFixed(1)}%`],
    ['Listing impressions', values.impressions],
    ['Listing views', values.views],
    ['Click-through rate', values.click_through_rate == null ? 'Not tracked' : `${(values.click_through_rate * 100).toFixed(1)}%`],
  ];
  const maxLeads = Math.max(1, ...report.daily.map((day) => day.leads));

  return (
    <section className="broker-card" aria-labelledby="broker-dashboard-title">
      <header className="broker-card-header">
        <span className="broker-badge-pill">Last 30 days</span>
        <h1 className="broker-card-title" id="broker-dashboard-title">Broker Command Center</h1>
        <p className="broker-card-subtitle">Leads, response performance, and buyer contact activity in one place.</p>
      </header>
      <div className="broker-analytics-grid">
        {cards.map(([label, value]) => (
          <article className="broker-analytics-card" key={label}>
            <span>{label}</span><strong>{value}</strong>
          </article>
        ))}
      </div>
      {report.totals.leads === 0 ? <p>No broker leads in this period yet.</p> : (
        <div className="broker-card broker-chart-card">
          <h2>Daily buyer leads</h2>
          <div className="broker-bar-chart" role="img" aria-label="Daily buyer leads for the last 30 days">
            {report.daily.map((day) => (
              <div className="broker-bar-column" key={day.date} title={`${day.date}: ${day.leads} leads`}>
                <div className="broker-bar" style={{ height: `${Math.max(2, (day.leads / maxLeads) * 100)}%` }} />
              </div>
            ))}
          </div>
          <div className="broker-chart-caption"><span>{report.date_from}</span><span>{report.date_to}</span></div>
        </div>
      )}
      <p className="broker-card-subtitle">Listing views count detail opens; impressions count listings seen in the discovery grid.</p>
    </section>
  );
}

export default withBrokerTranslations(DashboardOverviewScreen);
