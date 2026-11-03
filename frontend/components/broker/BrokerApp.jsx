import React, { useEffect, useState } from 'react';
import { withBrokerTranslations } from './i18n/withBrokerTranslations';
import { resolveBrokerLocale } from './i18n/catalog.mjs';
import './BrokerApp.css';
import OnboardingScreen from './screens/OnboardingScreen';
import PublicProfileEditor from './screens/PublicProfileEditor';
import TeamScreen from './screens/TeamScreen';
import BranchesScreen from './screens/BranchesScreen';
import ListingsListScreen from './screens/ListingsListScreen';
import ListingEditorScreen from './screens/ListingEditorScreen';
import BulkImportScreen from './screens/BulkImportScreen';

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

function BrokerApp() {
  const [token] = useState(localStorage.getItem('luxline_token') || '');
  const [role, setRole] = useState(getRoleFromJwt(token));
  const [, setLocaleRefresh] = useState(0);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [brokerHealth, setBrokerHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [listingEditor, setListingEditor] = useState(null);
  const [showBulkImport, setShowBulkImport] = useState(false);

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
            className={`broker-nav-item ${activeTab === 'onboarding' ? 'active' : ''}`}
            onClick={() => setActiveTab('onboarding')}
          >
            📜 Verification & Licence
          </button>
          <button
            type="button"
            className={`broker-nav-item ${activeTab === 'profile' ? 'active' : ''}`}
            onClick={() => setActiveTab('profile')}
          >
            🎨 Branded Showcase
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
            👥 Team Members
          </button>
          <button
            type="button"
            className={`broker-nav-item ${activeTab === 'branches' ? 'active' : ''}`}
            onClick={() => setActiveTab('branches')}
          >
            🏢 Regional Branches
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
            <label htmlFor="broker-locale" className="sr-only">Language</label>
            <select
              id="broker-locale"
              value={resolveBrokerLocale(localStorage.getItem('luxline_language') || navigator.language)}
              onChange={(event) => {
                localStorage.setItem('luxline_language', event.target.value);
                setLocaleRefresh((value) => value + 1);
              }}
            >
              <option value="en">English</option>
              <option value="si">Sinhala</option>
              <option value="ta">Tamil</option>
            </select>
          </div>
        </header>

        <div className="broker-content">
          {activeTab === 'onboarding' && (
            <OnboardingScreen token={token} apiBase={BROKER_API_BASE} />
          )}
          {activeTab === 'profile' && (
            <PublicProfileEditor token={token} apiBase={BROKER_API_BASE} />
          )}
          {activeTab === 'team' && (
            <TeamScreen token={token} apiBase={BROKER_API_BASE} />
          )}
          {activeTab === 'branches' && (
            <BranchesScreen token={token} apiBase={BROKER_API_BASE} />
          )}
          {activeTab === 'listings' && !listingEditor && !showBulkImport && (
            <ListingsListScreen
              token={token}
              apiBase={BROKER_API_BASE}
              onNewListing={() => setListingEditor({})}
              onEditListing={(listing) => setListingEditor(listing)}
              onOpenImport={() => setShowBulkImport(true)}
            />
          )}
          {activeTab === 'listings' && showBulkImport && (
            <BulkImportScreen token={token} apiBase={BROKER_API_BASE} onDone={() => setShowBulkImport(false)} />
          )}
          {activeTab === 'listings' && listingEditor && (
            <ListingEditorScreen
              token={token}
              apiBase={BROKER_API_BASE}
              listing={listingEditor.listing_id ? listingEditor : null}
              onDone={() => setListingEditor(null)}
            />
          )}
          {activeTab === 'dashboard' && (
            <div className="broker-card">
              <div className="broker-card-header">
                <span className="broker-badge-pill">Operational Dashboard</span>
                <h1 className="broker-card-title" style={{ marginTop: '12px' }}>
                  Broker Command Center
                </h1>
                <p className="broker-card-subtitle">
                  Manage inventory, respond to inquiries, monitor lead routing, and allocate visibility boosts.
                </p>
              </div>

              <div className="broker-status-box">
                <div><strong>Feature Flag:</strong> BROKER_PANEL_ENABLED = {String(IS_ENABLED)}</div>
                <div><strong>Target API:</strong> {BROKER_API_BASE}</div>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

export default withBrokerTranslations(BrokerApp);
