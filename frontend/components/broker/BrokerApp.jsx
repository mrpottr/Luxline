import React, { useEffect, useState } from 'react';
import './BrokerApp.css';

const IS_ENABLED = import.meta.env.VITE_BROKER_PANEL_ENABLED === 'true' || import.meta.env.VITE_BROKER_PANEL_ENABLED === true;
const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
const BROKER_API_BASE = API_BASE.replace('/api/v1', '/api/broker/v1');

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

export default function BrokerApp() {
  const [token] = useState(localStorage.getItem('luxline_token') || '');
  const [role, setRole] = useState(getRoleFromJwt(token));
  const [activeTab, setActiveTab] = useState('dashboard');
  const [brokerHealth, setBrokerHealth] = useState(null);
  const [loading, setLoading] = useState(true);

  // If the feature flag is disabled, show disabled notice
  if (!IS_ENABLED) {
    return (
      <div className="broker-disabled-wrapper">
        <div className="broker-disabled-card">
          <div className="broker-disabled-icon">🔒</div>
          <h2>Broker Panel Offline</h2>
          <p style={{ color: '#9da3af', marginTop: '8px' }}>
            The Broker Panel feature flag is currently disabled on this environment.
          </p>
          <a href="/" className="broker-btn-gold">Return to Marketplace</a>
        </div>
      </div>
    );
  }

  // If unauthenticated or private buyer
  if (!token) {
    return (
      <div className="broker-disabled-wrapper">
        <div className="broker-disabled-card">
          <div className="broker-disabled-icon">🔑</div>
          <h2>Authentication Required</h2>
          <p style={{ color: '#9da3af', marginTop: '8px' }}>
            Please sign in with an approved business account to access the Broker Panel.
          </p>
          <a href="/?login=1" className="broker-btn-gold">Go to Login</a>
        </div>
      </div>
    );
  }

  return (
    <div className="broker-container">
      {/* Sidebar Navigation */}
      <aside className="broker-sidebar">
        <div className="broker-brand">
          <span className="broker-brand-title">Luxline</span>
          <span className="broker-brand-badge">Broker</span>
        </div>

        <nav className="broker-nav">
          <button
            type="button"
            className={`broker-nav-item ${activeTab === 'dashboard' ? 'active' : ''}`}
            onClick={() => setActiveTab('dashboard')}
          >
            📊 Dashboard
          </button>
          <button
            type="button"
            className={`broker-nav-item ${activeTab === 'listings' ? 'active' : ''}`}
            onClick={() => setActiveTab('listings')}
          >
            🏰 Inventory & Listings
          </button>
          <button
            type="button"
            className={`broker-nav-item ${activeTab === 'leads' ? 'active' : ''}`}
            onClick={() => setActiveTab('leads')}
          >
            🎯 Leads & CRM
          </button>
          <button
            type="button"
            className={`broker-nav-item ${activeTab === 'inbox' ? 'active' : ''}`}
            onClick={() => setActiveTab('inbox')}
          >
            💬 Direct Inbox
          </button>
          <button
            type="button"
            className={`broker-nav-item ${activeTab === 'team' ? 'active' : ''}`}
            onClick={() => setActiveTab('team')}
          >
            👥 Team & Branches
          </button>
          <button
            type="button"
            className={`broker-nav-item ${activeTab === 'promotions' ? 'active' : ''}`}
            onClick={() => setActiveTab('promotions')}
          >
            ⚡ Boost & Visibility
          </button>
          <button
            type="button"
            className={`broker-nav-item ${activeTab === 'analytics' ? 'active' : ''}`}
            onClick={() => setActiveTab('analytics')}
          >
            📈 Analytics
          </button>
          <button
            type="button"
            className={`broker-nav-item ${activeTab === 'settings' ? 'active' : ''}`}
            onClick={() => setActiveTab('settings')}
          >
            ⚙️ Organization Settings
          </button>
        </nav>

        <div className="broker-sidebar-footer">
          <a href="/" className="broker-back-link">
            ← Return to Marketplace
          </a>
        </div>
      </aside>

      {/* Main Content Pane */}
      <main className="broker-main">
        <header className="broker-topbar">
          <div className="broker-topbar-title">
            {activeTab.charAt(0).toUpperCase() + activeTab.slice(1)}
          </div>
          <div className="broker-user-pill">
            <span>Logged in as:</span>
            <span className="broker-role-tag">{role || 'Business User'}</span>
          </div>
        </header>

        <div className="broker-content">
          <div className="broker-card">
            <div className="broker-card-header">
              <span className="broker-badge-pill">Milestone 0: Active Scaffold</span>
              <h1 className="broker-card-title" style={{ marginTop: '12px' }}>
                Broker Business Portal
              </h1>
              <p className="broker-card-subtitle">
                Welcome to the Luxline business seller portal. Inventory management, CRM leads routing,
                team allocation, and visibility boosts are managed through this interface.
              </p>
            </div>

            <div className="broker-status-box">
              <div><strong>Feature Flag:</strong> BROKER_PANEL_ENABLED = {String(IS_ENABLED)}</div>
              <div><strong>Active View:</strong> {activeTab}</div>
              <div><strong>Target API:</strong> {BROKER_API_BASE}</div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
