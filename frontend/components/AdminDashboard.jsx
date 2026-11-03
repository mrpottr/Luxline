import React, { useEffect, useMemo, useState } from 'react';
import './AdminDashboard.css';
import { BrokerPlanAdminScreen, isBrokerPanelEnabled, translateBrokerMessage } from './broker';

const BROKER_PANEL_ENABLED = isBrokerPanelEnabled(import.meta.env.VITE_BROKER_PANEL_ENABLED);

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

function getRoleFromJwt(jwtToken) {
  try {
    if (!jwtToken) return null;
    const parts = jwtToken.split('.');
    if (parts.length < 2) return null;
    const payload = JSON.parse(atob(parts[1]));
    return payload.role || null;
  } catch {
    return null;
  }
}

async function callApi(path, token, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {})
  };
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers
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

function formatDate(val) {
  if (!val) return '-';
  try {
    return new Date(val).toLocaleString();
  } catch {
    return String(val);
  }
}

export default function AdminDashboard() {
  const [token, setToken] = useState(localStorage.getItem('luxline_token') || '');
  const [adminUser, setAdminUser] = useState(null);
  const [authStatus, setAuthStatus] = useState('checking'); // 'checking' | 'authorized' | 'unauthorized'
  const [authError, setAuthError] = useState('');
  const [activeTab, setActiveTab] = useState('monitoring'); // 'monitoring' | 'overview' | 'moderation' | 'users' | 'taxonomy' | 'fraud' | 'audit'

  // Tab 1: Monitoring State
  const [health, setHealth] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [monitoringLoading, setMonitoringLoading] = useState(false);
  const [monitoringError, setMonitoringError] = useState('');

  // Tab 2: Overview State
  const [overview, setOverview] = useState(null);
  const [overviewLoading, setOverviewLoading] = useState(false);

  // Tab 3: Moderation Queue State
  const [moderationQueue, setModerationQueue] = useState([]);
  const [moderationLoading, setModerationLoading] = useState(false);
  const [moderationActionStatus, setModerationActionStatus] = useState('');

  // Tab 4: User Management State
  const [usersList, setUsersList] = useState([]);
  const [usersLoading, setUsersLoading] = useState(false);
  const [userSearch, setUserSearch] = useState('');
  const [userRoleFilter, setUserRoleFilter] = useState('');
  const [userActionStatus, setUserActionStatus] = useState('');
  const [passwordResetUserId, setPasswordResetUserId] = useState(null);
  const [newPasswordInput, setNewPasswordInput] = useState('');

  // Tab 5: Taxonomy State
  const [taxonomyTerms, setTaxonomyTerms] = useState([]);
  const [taxonomyLoading, setTaxonomyLoading] = useState(false);
  const [taxonomyType, setTaxonomyType] = useState('brand');
  const [taxonomyName, setTaxonomyName] = useState('');
  const [taxonomyFilter, setTaxonomyFilter] = useState('');
  const [taxonomyActionStatus, setTaxonomyActionStatus] = useState('');

  // Tab 6: Fraud Signals State
  const [fraudSignals, setFraudSignals] = useState([]);
  const [fraudLoading, setFraudLoading] = useState(false);
  const [newSignalType, setNewSignalType] = useState('suspicious_pricing');
  const [newSignalSeverity, setNewSignalSeverity] = useState('medium');
  const [newSignalNotes, setNewSignalNotes] = useState('');
  const [fraudActionStatus, setFraudActionStatus] = useState('');

  // Tab 7: Audit Logs State
  const [auditLogs, setAuditLogs] = useState([]);
  const [auditLoading, setAuditLoading] = useState(false);

  // Verify authentication on mount
  useEffect(() => {
    async function verifyAdminAuth() {
      if (!token) {
        setAuthStatus('unauthorized');
        setAuthError('Authentication required. You must log in as a super administrator to access the admin panel.');
        return;
      }

      const roleFromToken = getRoleFromJwt(token);
      if (roleFromToken && roleFromToken !== 'super_admin') {
        setAuthStatus('unauthorized');
        setAuthError('Access restricted. Your account is logged in as a standard user, not a super administrator.');
        return;
      }

      try {
        const user = await callApi('/auth/me', token);
        if (user.role !== 'super_admin') {
          setAuthStatus('unauthorized');
          setAuthError('Access denied. Super administrator permissions are required.');
          return;
        }

        setAdminUser(user);
        setAuthStatus('authorized');
      } catch (err) {
        setAuthStatus('unauthorized');
        if (err.status === 403) {
          setAuthError('Access denied. Your account is not authorized as a super administrator.');
        } else if (err.status === 401) {
          setAuthError('Your session has expired. Please log in again as an administrator.');
        } else {
          setAuthError(err.message || 'Authentication failed. Please verify credentials.');
        }
      }
    }

    verifyAdminAuth();
  }, [token]);

  // Load active tab data when authorized
  useEffect(() => {
    if (authStatus !== 'authorized' || !token) return;

    if (activeTab === 'monitoring') {
      loadMonitoring();
    } else if (activeTab === 'overview') {
      loadOverview();
    } else if (activeTab === 'moderation') {
      loadModerationQueue();
    } else if (activeTab === 'users') {
      loadUsers();
    } else if (activeTab === 'taxonomy') {
      loadTaxonomy();
    } else if (activeTab === 'fraud') {
      loadFraudSignals();
    } else if (activeTab === 'audit') {
      loadAuditLogs();
    }
  }, [authStatus, activeTab, token]);

  // Initial load of overview for badge numbers
  useEffect(() => {
    if (authStatus === 'authorized' && token) {
      loadModerationQueue();
    }
  }, [authStatus, token]);

  // Tab 1: Load Monitoring
  async function loadMonitoring() {
    setMonitoringLoading(true);
    setMonitoringError('');
    try {
      const [healthData, metricsData] = await Promise.all([
        callApi('/admin/monitoring/health', token),
        callApi('/admin/monitoring/metrics', token)
      ]);

      if (healthData?.error) {
        setMonitoringError(healthData.error);
      }
      setHealth(healthData);
      setMetrics(metricsData);
    } catch (err) {
      setMonitoringError(err.message || 'Unable to load monitoring data.');
    } finally {
      setMonitoringLoading(false);
    }
  }

  // Tab 2: Load Overview
  async function loadOverview() {
    setOverviewLoading(true);
    try {
      const data = await callApi('/admin/overview', token);
      setOverview(data);
    } catch (err) {
      console.error('Failed to load overview:', err);
    } finally {
      setOverviewLoading(false);
    }
  }

  // Tab 3: Moderation Functions
  async function loadModerationQueue() {
    setModerationLoading(true);
    try {
      const data = await callApi('/admin/moderation/queue', token);
      setModerationQueue(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Failed to load moderation queue:', err);
    } finally {
      setModerationLoading(false);
    }
  }

  async function handleModerateListing(listingId, action) {
    const actionLabel = action === 'approve' ? 'Approving' : 'Rejecting';
    setModerationActionStatus(`${actionLabel} listing #${listingId}...`);
    try {
      await callApi(`/admin/moderation/listings/${listingId}/${action}`, token, {
        method: 'POST'
      });
      setModerationActionStatus(`Listing #${listingId} ${action === 'approve' ? 'approved' : 'rejected'} successfully.`);
      loadModerationQueue();
    } catch (err) {
      setModerationActionStatus(`Error: ${err.message}`);
    }
  }

  // Tab 4: User Management Functions
  async function loadUsers() {
    setUsersLoading(true);
    try {
      const data = await callApi('/admin/users', token);
      setUsersList(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Failed to load users:', err);
    } finally {
      setUsersLoading(false);
    }
  }

  async function handleVerifyBusiness(userId) {
    setUserActionStatus(`Verifying business account for user #${userId}...`);
    try {
      await callApi(`/admin/users/${userId}/verify-business`, token, { method: 'POST' });
      setUserActionStatus(`User #${userId} marked as business-verified.`);
      loadUsers();
    } catch (err) {
      setUserActionStatus(`Error: ${err.message}`);
    }
  }

  async function handleChangeUserRole(userId, newRole) {
    setUserActionStatus(`Updating user #${userId} role to ${newRole}...`);
    try {
      await callApi(`/admin/users/${userId}/role`, token, {
        method: 'PATCH',
        body: JSON.stringify({ role: newRole })
      });
      setUserActionStatus(`User #${userId} role updated to ${newRole}.`);
      loadUsers();
    } catch (err) {
      setUserActionStatus(`Error: ${err.message}`);
    }
  }

  async function handleResetPassword(e) {
    e.preventDefault();
    if (!passwordResetUserId || !newPasswordInput) return;
    setUserActionStatus(`Resetting password for user #${passwordResetUserId}...`);
    try {
      await callApi(`/admin/users/${passwordResetUserId}/reset-password`, token, {
        method: 'POST',
        body: JSON.stringify({ new_password: newPasswordInput })
      });
      setUserActionStatus(`Password for user #${passwordResetUserId} reset successfully.`);
      setPasswordResetUserId(null);
      setNewPasswordInput('');
    } catch (err) {
      setUserActionStatus(`Error: ${err.message}`);
    }
  }

  // Tab 5: Taxonomy Functions
  async function loadTaxonomy() {
    setTaxonomyLoading(true);
    try {
      const data = await callApi('/admin/taxonomy?include_inactive=true', token);
      setTaxonomyTerms(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Failed to load taxonomy:', err);
    } finally {
      setTaxonomyLoading(false);
    }
  }

  async function handleCreateTaxonomy(e) {
    e.preventDefault();
    if (!taxonomyName.trim()) return;
    setTaxonomyActionStatus('Creating taxonomy term...');
    try {
      await callApi('/admin/taxonomy', token, {
        method: 'POST',
        body: JSON.stringify({
          taxonomy: taxonomyType,
          name: taxonomyName.trim()
        })
      });
      setTaxonomyActionStatus(`Created ${taxonomyType} term "${taxonomyName.trim()}".`);
      setTaxonomyName('');
      loadTaxonomy();
    } catch (err) {
      setTaxonomyActionStatus(`Error: ${err.message}`);
    }
  }

  // Tab 6: Fraud Signals Functions
  async function loadFraudSignals() {
    setFraudLoading(true);
    try {
      const data = await callApi('/admin/fraud/signals', token);
      setFraudSignals(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Failed to load fraud signals:', err);
    } finally {
      setFraudLoading(false);
    }
  }

  async function handleCreateFraudSignal(e) {
    e.preventDefault();
    setFraudActionStatus('Filing fraud signal...');
    try {
      await callApi('/admin/fraud/signals', token, {
        method: 'POST',
        body: JSON.stringify({
          signal_type: newSignalType,
          severity: newSignalSeverity,
          details: { note: newSignalNotes || 'Manually logged by admin' }
        })
      });
      setFraudActionStatus('Fraud signal logged successfully.');
      setNewSignalNotes('');
      loadFraudSignals();
    } catch (err) {
      setFraudActionStatus(`Error: ${err.message}`);
    }
  }

  async function handleResolveFraudSignal(signalId) {
    setFraudActionStatus(`Resolving signal #${signalId}...`);
    try {
      await callApi(`/admin/fraud/signals/${signalId}/resolve`, token, { method: 'POST' });
      setFraudActionStatus(`Signal #${signalId} marked as resolved.`);
      loadFraudSignals();
    } catch (err) {
      setFraudActionStatus(`Error: ${err.message}`);
    }
  }

  // Tab 7: Audit Logs Functions
  async function loadAuditLogs() {
    setAuditLoading(true);
    try {
      const data = await callApi('/admin/audit-logs?limit=50', token);
      setAuditLogs(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Failed to load audit logs:', err);
    } finally {
      setAuditLoading(false);
    }
  }

  function handleLogout() {
    localStorage.removeItem('luxline_token');
    setToken('');
    setAuthStatus('unauthorized');
    setAuthError('You have been logged out.');
    window.location.href = '/';
  }

  // Filtering users
  const filteredUsers = useMemo(() => {
    return usersList.filter((u) => {
      const matchesSearch =
        !userSearch ||
        `${u.first_name} ${u.last_name}`.toLowerCase().includes(userSearch.toLowerCase()) ||
        u.email.toLowerCase().includes(userSearch.toLowerCase());
      const matchesRole = !userRoleFilter || u.role === userRoleFilter;
      return matchesSearch && matchesRole;
    });
  }, [usersList, userSearch, userRoleFilter]);

  // Filtering taxonomy
  const filteredTaxonomy = useMemo(() => {
    return taxonomyTerms.filter((t) => {
      return !taxonomyFilter || t.taxonomy === taxonomyFilter;
    });
  }, [taxonomyTerms, taxonomyFilter]);

  // Telemetry row calculation
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

  // If unauthorized: NEVER render the admin panel
  if (authStatus === 'checking') {
    return (
      <main className="admin-dashboard-access-denied">
        <div className="access-card">
          <div className="access-spinner" />
          <h2>Verifying Administrator Privileges...</h2>
          <p>Please wait while we validate your security credentials.</p>
        </div>
      </main>
    );
  }

  if (authStatus === 'unauthorized') {
    return (
      <main className="admin-dashboard-access-denied">
        <div className="access-card">
          <div className="access-icon">🔒</div>
          <h2>Admin Access Restricted</h2>
          <p className="access-desc">
            {authError || 'The Luxline Administration Panel is strictly reserved for platform super administrators. Standard users and unauthorized accounts cannot view or access this interface.'}
          </p>
          <div className="access-actions">
            <a className="btn btn-primary" href="/">Return to Marketplace</a>
            <a className="btn btn-secondary" href="/dashboard">Login as Administrator</a>
          </div>
        </div>
      </main>
    );
  }

  // Authorized Admin View
  return (
    <main className="admin-dashboard">
      <header className="admin-header">
        <div className="admin-header-top">
          <div className="admin-identity">
            <span className="admin-badge">Super Admin</span>
            <span className="admin-user-email">{adminUser?.email}</span>
          </div>
          <div className="admin-nav-actions">
            <a className="link-btn" href="/">← Back to Marketplace</a>
            <button className="link-btn btn-danger" type="button" onClick={handleLogout}>Logout</button>
          </div>
        </div>
        <h1>Luxline Administration Console</h1>
        <p className="subtitle">Platform Governance, Moderation, Telemetry & User Operations</p>

        {/* Tab Navigation */}
        <nav className="admin-tab-nav" aria-label="Admin Sections">
          <button
            type="button"
            className={`tab-btn ${activeTab === 'monitoring' ? 'active' : ''}`}
            onClick={() => setActiveTab('monitoring')}
          >
            📊 System & Telemetry
          </button>
          <button
            type="button"
            className={`tab-btn ${activeTab === 'overview' ? 'active' : ''}`}
            onClick={() => setActiveTab('overview')}
          >
            📈 Platform Overview
          </button>
          <button
            type="button"
            className={`tab-btn ${activeTab === 'moderation' ? 'active' : ''}`}
            onClick={() => setActiveTab('moderation')}
          >
            ⚖️ Listing Moderation
            {moderationQueue.length > 0 && (
              <span className="tab-pill">{moderationQueue.length}</span>
            )}
          </button>
          <button
            type="button"
            className={`tab-btn ${activeTab === 'users' ? 'active' : ''}`}
            onClick={() => setActiveTab('users')}
          >
            👥 User Management
          </button>
          <button
            type="button"
            className={`tab-btn ${activeTab === 'taxonomy' ? 'active' : ''}`}
            onClick={() => setActiveTab('taxonomy')}
          >
            🏷️ Taxonomy & Categories
          </button>
          <button
            type="button"
            className={`tab-btn ${activeTab === 'fraud' ? 'active' : ''}`}
            onClick={() => setActiveTab('fraud')}
          >
            🛡️ Fraud Signals
          </button>
          <button
            type="button"
            className={`tab-btn ${activeTab === 'audit' ? 'active' : ''}`}
            onClick={() => setActiveTab('audit')}
          >
            📜 Audit Logs
          </button>
          {BROKER_PANEL_ENABLED && <button
            type="button"
            className={`tab-btn ${activeTab === 'brokerPlans' ? 'active' : ''}`}
            onClick={() => setActiveTab('brokerPlans')}
          >
            {translateBrokerMessage('Broker Plans', localStorage.getItem('luxline_language') || navigator.language)}
          </button>}
        </nav>
      </header>

      {/* Tab 1: System Health & Monitoring */}
      {activeTab === 'monitoring' && (
        <div className="admin-tab-content">
          <section className="health-section">
            <div className="section-header-flex">
              <h2>System Health & Telemetry</h2>
              <button className="btn btn-primary" type="button" onClick={loadMonitoring}>
                {monitoringLoading ? 'Refreshing...' : '↻ Refresh Status'}
              </button>
            </div>
            {monitoringLoading && <p className="loading">Updating telemetry services...</p>}
            {monitoringError && <p className="error">{monitoringError}</p>}
            <div className="health-grid">
              <article className={`health-card ${health?.grafana === 'healthy' ? 'healthy' : 'unhealthy'}`}>
                <h3>Grafana</h3>
                <p className="status">{health ? statusLabel(health.grafana) : 'Checking...'}</p>
                <p className="description">Dashboard visualization service</p>
              </article>
              <article className={`health-card ${health?.prometheus === 'healthy' ? 'healthy' : 'unhealthy'}`}>
                <h3>Prometheus</h3>
                <p className="status">{health ? statusLabel(health.prometheus) : 'Checking...'}</p>
                <p className="description">Metrics scraping & storage</p>
              </article>
              <article className="health-card healthy">
                <h3>Captured Requests</h3>
                <p className="status">{totalRequests}</p>
                <p className="description">Luxline API Telemetry</p>
              </article>
            </div>
          </section>

          <section className="dashboards-section">
            <h2>Live Observability Dashboards</h2>
            <p className="section-desc">Open operational dashboards directly in Grafana and Prometheus.</p>
            <div className="dashboard-grid">
              <article className="dashboard-card primary">
                <div className="card-content">
                  <h3>Luxline API Monitoring</h3>
                  <p>Main API performance dashboard for request volume, throughput, and status codes.</p>
                  <ul className="metrics-list">
                    <li>Request rate by HTTP method</li>
                    <li>P95 latency & active request gauge</li>
                    <li>Endpoint response timing distribution</li>
                  </ul>
                </div>
                <a className="btn btn-primary" href={`${health?.grafana_url || 'http://localhost:3000'}/d/luxline-api-monitoring`} target="_blank" rel="noreferrer">
                  Open API Dashboard ↗
                </a>
              </article>

              <article className="dashboard-card secondary">
                <div className="card-content">
                  <h3>Error Analysis</h3>
                  <p>Troubleshooting dashboard for 4xx client errors, 5xx failures, and slow endpoints.</p>
                  <ul className="metrics-list">
                    <li>Client & server error trends</li>
                    <li>Slowest endpoint analysis</li>
                    <li>Status code breakdown timeline</li>
                  </ul>
                </div>
                <a className="btn btn-secondary" href={`${health?.grafana_url || 'http://localhost:3000'}/d/luxline-error-analysis`} target="_blank" rel="noreferrer">
                  Open Error Dashboard ↗
                </a>
              </article>

              <article className="dashboard-card tertiary">
                <div className="card-content">
                  <h3>Prometheus Query Console</h3>
                  <p>Inspect raw scrape targets, metric registry, and PromQL expressions.</p>
                  <ul className="metrics-list">
                    <li>Backend scraper target health</li>
                    <li>Raw Luxline metrics exploration</li>
                    <li>Direct PromQL ad-hoc queries</li>
                  </ul>
                </div>
                <a className="btn btn-tertiary" href={health?.prometheus_url || 'http://localhost:9090'} target="_blank" rel="noreferrer">
                  Open Prometheus Console ↗
                </a>
              </article>
            </div>
          </section>

          <section className="metrics-section">
            <h2>API Request Telemetry Table</h2>
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
                        <td><span className={`method-badge ${row.method.toLowerCase()}`}>{row.method}</span></td>
                        <td><code>{row.endpoint}</code></td>
                        <td><span className={`status-pill ${row.statusCode.startsWith('2') ? 'success' : 'warn'}`}>{row.statusCode}</span></td>
                        <td><strong>{row.requests}</strong></td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan="4" className="empty-table">No request metrics captured yet. Perform platform actions and refresh.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      )}

      {/* Tab 2: Platform Overview */}
      {activeTab === 'overview' && (
        <div className="admin-tab-content">
          <section className="overview-section">
            <div className="section-header-flex">
              <h2>Platform Activity & Inventory Overview</h2>
              <button className="btn btn-primary" type="button" onClick={loadOverview}>
                {overviewLoading ? 'Refreshing...' : '↻ Refresh Overview'}
              </button>
            </div>
            {overview ? (
              <>
                <div className="stats-grid">
                  <div className="stat-card">
                    <p className="stat-label">Total Users</p>
                    <p className="stat-number">{overview.total_users}</p>
                    <span className="stat-sub">{overview.active_users} active · {overview.suspended_users} suspended</span>
                  </div>
                  <div className="stat-card">
                    <p className="stat-label">Total Listings</p>
                    <p className="stat-number">{overview.total_listings}</p>
                    <span className="stat-sub">{overview.active_listings} active · {overview.pending_listings} pending</span>
                  </div>
                  <div className="stat-card">
                    <p className="stat-label">Business Review</p>
                    <p className="stat-number">{overview.pending_business_verifications}</p>
                    <span className="stat-sub">Pending verification</span>
                  </div>
                  <div className="stat-card">
                    <p className="stat-label">Client Inquiries</p>
                    <p className="stat-number">{overview.inquiry_count}</p>
                    <span className="stat-sub">Across all inventory</span>
                  </div>
                  <div className="stat-card">
                    <p className="stat-label">Saved Searches</p>
                    <p className="stat-number">{overview.saved_search_count}</p>
                    <span className="stat-sub">Client interest monitors</span>
                  </div>
                </div>

                <div className="recent-activity-card">
                  <h3>Recent Administrative Operations</h3>
                  <div className="activity-list">
                    {overview.recent_audit_logs?.length ? (
                      overview.recent_audit_logs.map((log) => (
                        <div key={log.id} className="activity-row">
                          <span className="activity-event">{log.event_type}</span>
                          <span className="activity-details">{JSON.stringify(log.details || {})}</span>
                          <span className="activity-date">{formatDate(log.created_at)}</span>
                        </div>
                      ))
                    ) : (
                      <p className="empty-notice">No administrative operations recorded yet.</p>
                    )}
                  </div>
                </div>
              </>
            ) : (
              <p className="loading">Loading overview data...</p>
            )}
          </section>
        </div>
      )}

      {/* Tab 3: Listing Moderation Queue */}
      {activeTab === 'moderation' && (
        <div className="admin-tab-content">
          <section className="moderation-section">
            <div className="section-header-flex">
              <div>
                <h2>Listing Moderation Queue</h2>
                <p className="section-desc">Review and approve luxury assets before publication on the live marketplace.</p>
              </div>
              <button className="btn btn-primary" type="button" onClick={loadModerationQueue}>
                {moderationLoading ? 'Refreshing...' : '↻ Refresh Queue'}
              </button>
            </div>

            {moderationActionStatus && (
              <div className="action-status-banner">{moderationActionStatus}</div>
            )}

            {moderationLoading ? (
              <p className="loading">Loading moderation queue...</p>
            ) : moderationQueue.length ? (
              <div className="moderation-cards-grid">
                {moderationQueue.map((item) => (
                  <article key={item.id} className="moderation-card">
                    <div className="moderation-card-header">
                      <span className="category-pill">{item.category}</span>
                      <span className="price-pill">${Number(item.price || 0).toLocaleString()} {item.currency}</span>
                    </div>
                    <h3>{item.title}</h3>
                    <p className="item-description">{item.description}</p>
                    <div className="item-meta">
                      <span>📍 {[item.location_city, item.location_country].filter(Boolean).join(', ') || 'Global'}</span>
                      <span>👤 Seller ID: #{item.seller_id}</span>
                      <span>📅 Submitted: {formatDate(item.created_at)}</span>
                    </div>
                    <div className="moderation-actions">
                      <button
                        className="btn btn-secondary"
                        type="button"
                        onClick={() => handleModerateListing(item.id, 'approve')}
                      >
                        ✓ Approve Listing
                      </button>
                      <button
                        className="btn btn-danger"
                        type="button"
                        onClick={() => handleModerateListing(item.id, 'reject')}
                      >
                        ✕ Reject Listing
                      </button>
                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <div className="empty-card">
                <div className="empty-icon">✓</div>
                <h3>Moderation Queue is Clean</h3>
                <p>No listings are currently awaiting administrative review.</p>
              </div>
            )}
          </section>
        </div>
      )}

      {/* Tab 4: User Management */}
      {activeTab === 'users' && (
        <div className="admin-tab-content">
          <section className="users-section">
            <div className="section-header-flex">
              <div>
                <h2>User Governance & Role Management</h2>
                <p className="section-desc">Inspect accounts, modify roles, verify business agencies, and reset credentials.</p>
              </div>
              <button className="btn btn-primary" type="button" onClick={loadUsers}>
                {usersLoading ? 'Refreshing...' : '↻ Refresh Users'}
              </button>
            </div>

            {userActionStatus && (
              <div className="action-status-banner">{userActionStatus}</div>
            )}

            {/* Filter and Search Bar */}
            <div className="table-controls">
              <input
                className="search-input"
                type="text"
                placeholder="Search by name or email..."
                value={userSearch}
                onChange={(e) => setUserSearch(e.target.value)}
              />
              <select
                className="role-select-filter"
                value={userRoleFilter}
                onChange={(e) => setUserRoleFilter(e.target.value)}
              >
                <option value="">All Roles</option>
                <option value="standard_user">Buyer (Standard User)</option>
                <option value="private_seller">Private Seller</option>
                <option value="business_account">Business Account</option>
                <option value="super_admin">Super Administrator</option>
              </select>
            </div>

            {/* Password Reset Modal/Inline Card */}
            {passwordResetUserId && (
              <div className="inline-action-card">
                <h3>Reset Password for User #{passwordResetUserId}</h3>
                <form onSubmit={handleResetPassword} className="inline-form">
                  <input
                    type="password"
                    required
                    placeholder="Enter new strong password (min 8 chars)"
                    value={newPasswordInput}
                    onChange={(e) => setNewPasswordInput(e.target.value)}
                  />
                  <button className="btn btn-primary" type="submit">Confirm Reset</button>
                  <button className="btn btn-tertiary" type="button" onClick={() => setPasswordResetUserId(null)}>Cancel</button>
                </form>
              </div>
            )}

            <div className="metrics-table">
              <table>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Name</th>
                    <th>Email</th>
                    <th>Current Role</th>
                    <th>Status</th>
                    <th>Business Check</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredUsers.length ? (
                    filteredUsers.map((u) => (
                      <tr key={u.id}>
                        <td>#{u.id}</td>
                        <td><strong>{u.first_name} {u.last_name}</strong></td>
                        <td>{u.email}</td>
                        <td>
                          <span className={`role-badge ${u.role}`}>{u.role}</span>
                        </td>
                        <td>
                          <span className={`status-pill ${u.is_active ? 'success' : 'danger'}`}>
                            {u.is_active ? 'Active' : 'Suspended'}
                          </span>
                        </td>
                        <td>
                          <span className={`status-pill ${u.is_verified_business ? 'success' : 'warn'}`}>
                            {u.is_verified_business ? 'Verified' : 'Unverified'}
                          </span>
                        </td>
                        <td className="user-action-cells">
                          {u.role !== 'super_admin' && (
                            <>
                              <select
                                className="inline-role-select"
                                value={u.role}
                                onChange={(e) => handleChangeUserRole(u.id, e.target.value)}
                              >
                                <option value="standard_user">Set: Standard</option>
                                <option value="private_seller">Set: Seller</option>
                                <option value="business_account">Set: Business</option>
                              </select>

                              {!u.is_verified_business && (
                                <button
                                  className="action-btn-sm"
                                  type="button"
                                  onClick={() => handleVerifyBusiness(u.id)}
                                >
                                  Verify Business
                                </button>
                              )}

                              <button
                                className="action-btn-sm"
                                type="button"
                                onClick={() => {
                                  setPasswordResetUserId(u.id);
                                  setNewPasswordInput('');
                                }}
                              >
                                Reset PW
                              </button>
                            </>
                          )}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan="7" className="empty-table">No users found matching filter.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      )}

      {/* Tab 5: Taxonomy Management */}
      {activeTab === 'taxonomy' && (
        <div className="admin-tab-content">
          <section className="taxonomy-section">
            <div className="section-header-flex">
              <div>
                <h2>Taxonomy & Inventory Metadata</h2>
                <p className="section-desc">Manage luxury brands, vehicle models, yacht builders, and materials.</p>
              </div>
              <button className="btn btn-primary" type="button" onClick={loadTaxonomy}>
                {taxonomyLoading ? 'Refreshing...' : '↻ Refresh Taxonomy'}
              </button>
            </div>

            {taxonomyActionStatus && (
              <div className="action-status-banner">{taxonomyActionStatus}</div>
            )}

            <div className="create-term-card">
              <h3>Add New Taxonomy Term</h3>
              <form onSubmit={handleCreateTaxonomy} className="taxonomy-form">
                <select value={taxonomyType} onChange={(e) => setTaxonomyType(e.target.value)}>
                  <option value="brand">Brand</option>
                  <option value="model">Model</option>
                  <option value="builder">Builder</option>
                  <option value="material">Material</option>
                  <option value="movement">Movement</option>
                </select>
                <input
                  type="text"
                  required
                  placeholder="Term name (e.g., Patek Philippe, Bugatti, Carbon Fiber)"
                  value={taxonomyName}
                  onChange={(e) => setTaxonomyName(e.target.value)}
                />
                <button className="btn btn-primary" type="submit">+ Create Term</button>
              </form>
            </div>

            <div className="table-controls">
              <select
                className="role-select-filter"
                value={taxonomyFilter}
                onChange={(e) => setTaxonomyFilter(e.target.value)}
              >
                <option value="">All Categories</option>
                <option value="brand">Brands</option>
                <option value="model">Models</option>
                <option value="builder">Builders</option>
                <option value="material">Materials</option>
                <option value="movement">Movements</option>
              </select>
            </div>

            <div className="metrics-table">
              <table>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Category</th>
                    <th>Name</th>
                    <th>Slug</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredTaxonomy.length ? (
                    filteredTaxonomy.map((term) => (
                      <tr key={term.id}>
                        <td>#{term.id}</td>
                        <td><span className="category-pill">{term.taxonomy}</span></td>
                        <td><strong>{term.name}</strong></td>
                        <td><code>{term.slug}</code></td>
                        <td>
                          <span className={`status-pill ${term.is_active ? 'success' : 'warn'}`}>
                            {term.is_active ? 'Active' : 'Inactive'}
                          </span>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan="5" className="empty-table">No taxonomy terms found.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      )}

      {/* Tab 6: Fraud Signals */}
      {activeTab === 'fraud' && (
        <div className="admin-tab-content">
          <section className="fraud-section">
            <div className="section-header-flex">
              <div>
                <h2>Fraud & Safety Signal Governance</h2>
                <p className="section-desc">Review high-risk activities, reported listings, and resolve flagged signals.</p>
              </div>
              <button className="btn btn-primary" type="button" onClick={loadFraudSignals}>
                {fraudLoading ? 'Refreshing...' : '↻ Refresh Signals'}
              </button>
            </div>

            {fraudActionStatus && (
              <div className="action-status-banner">{fraudActionStatus}</div>
            )}

            <div className="create-term-card">
              <h3>Manually File Safety / Fraud Signal</h3>
              <form onSubmit={handleCreateFraudSignal} className="taxonomy-form">
                <select value={newSignalType} onChange={(e) => setNewSignalType(e.target.value)}>
                  <option value="suspicious_pricing">Suspicious Pricing</option>
                  <option value="unverified_identity">Unverified Identity</option>
                  <option value="counterfeit_risk">Counterfeit Risk</option>
                  <option value="spam_inquiries">Spam Inquiries</option>
                  <option value="policy_violation">Policy Violation</option>
                </select>
                <select value={newSignalSeverity} onChange={(e) => setNewSignalSeverity(e.target.value)}>
                  <option value="low">Low Severity</option>
                  <option value="medium">Medium Severity</option>
                  <option value="high">High Severity</option>
                  <option value="critical">Critical Severity</option>
                </select>
                <input
                  type="text"
                  placeholder="Notes or evidence details"
                  value={newSignalNotes}
                  onChange={(e) => setNewSignalNotes(e.target.value)}
                />
                <button className="btn btn-danger" type="submit">+ File Signal</button>
              </form>
            </div>

            <div className="metrics-table">
              <table>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Signal Type</th>
                    <th>Severity</th>
                    <th>Status</th>
                    <th>Details</th>
                    <th>Logged At</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {fraudSignals.length ? (
                    fraudSignals.map((signal) => (
                      <tr key={signal.id}>
                        <td>#{signal.id}</td>
                        <td><strong>{signal.signal_type}</strong></td>
                        <td>
                          <span className={`severity-badge ${signal.severity}`}>{signal.severity}</span>
                        </td>
                        <td>
                          <span className={`status-pill ${signal.status === 'open' ? 'danger' : 'success'}`}>
                            {signal.status}
                          </span>
                        </td>
                        <td>{JSON.stringify(signal.details || {})}</td>
                        <td>{formatDate(signal.created_at)}</td>
                        <td>
                          {signal.status === 'open' ? (
                            <button
                              className="btn btn-secondary action-btn-sm"
                              type="button"
                              onClick={() => handleResolveFraudSignal(signal.id)}
                            >
                              Resolve
                            </button>
                          ) : (
                            <span className="resolved-text">Resolved</span>
                          )}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan="7" className="empty-table">No open fraud or security signals.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      )}

      {/* Tab 7: Audit Logs */}
      {BROKER_PANEL_ENABLED && activeTab === 'brokerPlans' && <BrokerPlanAdminScreen token={token} />}

      {activeTab === 'audit' && (
        <div className="admin-tab-content">
          <section className="audit-section">
            <div className="section-header-flex">
              <div>
                <h2>Platform Governance Audit Trail</h2>
                <p className="section-desc">Immutable log of privileged administrative actions and system security events.</p>
              </div>
              <button className="btn btn-primary" type="button" onClick={loadAuditLogs}>
                {auditLoading ? 'Refreshing...' : '↻ Refresh Logs'}
              </button>
            </div>

            <div className="metrics-table">
              <table>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Event Type</th>
                    <th>Actor ID</th>
                    <th>Details Payload</th>
                    <th>Timestamp</th>
                  </tr>
                </thead>
                <tbody>
                  {auditLogs.length ? (
                    auditLogs.map((log) => (
                      <tr key={log.id}>
                        <td>#{log.id}</td>
                        <td><code>{log.event_type}</code></td>
                        <td>User #{log.actor_user_id}</td>
                        <td className="details-cell">{JSON.stringify(log.details || {})}</td>
                        <td>{formatDate(log.created_at)}</td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan="5" className="empty-table">No audit logs recorded yet.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      )}
    </main>
  );
}
