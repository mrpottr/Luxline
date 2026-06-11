import React, { useEffect, useMemo, useState } from 'react';
import './AdminDashboard.css';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

async function callApi(path, token) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    }
  });
  const text = await response.text();
  const data = text ? JSON.parse(text) : null;

  if (!response.ok) {
    const error = new Error(data?.detail || 'Request failed');
    error.status = response.status;
    throw error;
  }

  return data;
}

function statusLabel(value) {
  return value === 'healthy' ? 'Healthy' : 'Unhealthy';
}

export default function AdminDashboard() {
  const [health, setHealth] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const token = localStorage.getItem('luxline_token') || '';

  async function loadMonitoring() {
    if (!token) {
      setLoading(false);
      setError('Login as a super admin first, then open the admin dashboard.');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const [healthData, metricsData] = await Promise.all([
        callApi('/admin/monitoring/health', token),
        callApi('/admin/monitoring/metrics', token)
      ]);

      if (healthData?.error) {
        setError(healthData.error);
      }

      setHealth(healthData);
      setMetrics(metricsData);
    } catch (err) {
      if (err.status === 403) {
        setError('Your account is logged in, but it is not a super admin account.');
      } else if (err.status === 401) {
        setError('Your admin session expired. Login again and retry.');
      } else {
        setError(err.message || 'Unable to load monitoring data.');
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadMonitoring();
  }, []);

  const requestRows = useMemo(() => {
    const rows = metrics?.data?.data?.result;
    if (!Array.isArray(rows)) return [];

    return rows.map((row, index) => ({
      id: `${row.metric?.method || 'unknown'}-${row.metric?.endpoint || 'unknown'}-${row.metric?.status_code || index}`,
      method: row.metric?.method || '-',
      endpoint: row.metric?.endpoint || '-',
      statusCode: row.metric?.status_code || '-',
      requests: Number(row.value?.[1] || 0)
    }));
  }, [metrics]);

  const totalRequests = requestRows.reduce((sum, row) => sum + row.requests, 0);

  return (
    <main className="admin-dashboard">
      <header className="admin-header">
        <h1>Luxline Admin Monitoring</h1>
        <p className="subtitle">Grafana, Prometheus, and API request telemetry</p>
        <div className="admin-actions">
          <a className="btn btn-primary" href={health?.grafana_url || 'http://localhost:3000'} target="_blank" rel="noreferrer">
            Open Grafana
          </a>
          <a className="btn btn-secondary" href={`${health?.grafana_url || 'http://localhost:3000'}/d/luxline-api-monitoring`} target="_blank" rel="noreferrer">
            API Dashboard
          </a>
          <a className="btn btn-tertiary" href={health?.prometheus_url || 'http://localhost:9090'} target="_blank" rel="noreferrer">
            Open Prometheus
          </a>
          <a className="link-btn" href="/">Back to Luxline</a>
        </div>
      </header>

      <section className="health-section">
        <h2>System Health</h2>
        {loading ? <p className="loading">Loading monitoring status...</p> : null}
        {error ? <p className="error">{error}</p> : null}
        <div className="health-grid">
          <article className={`health-card ${health?.grafana === 'healthy' ? 'healthy' : 'unhealthy'}`}>
            <h3>Grafana</h3>
            <p className="status">{health ? statusLabel(health.grafana) : 'Unknown'}</p>
            <p className="description">Dashboard visualization service</p>
          </article>
          <article className={`health-card ${health?.prometheus === 'healthy' ? 'healthy' : 'unhealthy'}`}>
            <h3>Prometheus</h3>
            <p className="status">{health ? statusLabel(health.prometheus) : 'Unknown'}</p>
            <p className="description">Metrics scraping and storage service</p>
          </article>
          <article className="health-card healthy">
            <h3>API Metrics</h3>
            <p className="status">{totalRequests}</p>
            <p className="description">Captured Luxline requests</p>
          </article>
        </div>
      </section>

      <section className="dashboards-section">
        <h2>Grafana Dashboards</h2>
        <p className="section-desc">Open the provisioned Grafana dashboards in a new tab.</p>
        <div className="dashboard-grid">
          <article className="dashboard-card primary">
            <div className="card-content">
              <h3>Luxline API Monitoring</h3>
              <p>Main API monitoring dashboard for request volume, latency, and status codes.</p>
              <ul className="metrics-list">
                <li>Request rate by method</li>
                <li>P95 latency and active requests</li>
                <li>Endpoint response timing</li>
              </ul>
            </div>
            <a className="btn btn-primary" href={`${health?.grafana_url || 'http://localhost:3000'}/d/luxline-api-monitoring`} target="_blank" rel="noreferrer">
              Open Main Dashboard
            </a>
          </article>

          <article className="dashboard-card secondary">
            <div className="card-content">
              <h3>Error Analysis</h3>
              <p>Troubleshooting dashboard for 4xx, 5xx, slow endpoints, and error trends.</p>
              <ul className="metrics-list">
                <li>Client and server error rates</li>
                <li>Slowest endpoints</li>
                <li>Status code timeline</li>
              </ul>
            </div>
            <a className="btn btn-secondary" href={`${health?.grafana_url || 'http://localhost:3000'}/d/luxline-error-analysis`} target="_blank" rel="noreferrer">
              Open Error Dashboard
            </a>
          </article>

          <article className="dashboard-card tertiary">
            <div className="card-content">
              <h3>Prometheus</h3>
              <p>Inspect raw targets, scrape status, and PromQL queries directly.</p>
              <ul className="metrics-list">
                <li>Backend scrape target</li>
                <li>Raw Luxline metrics</li>
                <li>PromQL query console</li>
              </ul>
            </div>
            <a className="btn btn-tertiary" href={health?.prometheus_url || 'http://localhost:9090'} target="_blank" rel="noreferrer">
              Open Prometheus
            </a>
          </article>
        </div>
      </section>

      <section className="metrics-section">
        <h2>Request Metrics</h2>
        <div className="metrics-table">
          <table>
            <thead>
              <tr>
                <th>Method</th>
                <th>Endpoint</th>
                <th>Status</th>
                <th>Total Requests</th>
              </tr>
            </thead>
            <tbody>
              {requestRows.length ? (
                requestRows.map((row) => (
                  <tr key={row.id}>
                    <td>{row.method}</td>
                    <td>{row.endpoint}</td>
                    <td>{row.statusCode}</td>
                    <td>{row.requests}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="4">No request metrics yet. Hit a few API endpoints and refresh.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <button className="btn btn-primary" type="button" onClick={loadMonitoring}>Refresh Monitoring</button>
      </section>
    </main>
  );
}
