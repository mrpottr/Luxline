import React, { useEffect, useState } from 'react';
import { withBrokerTranslations } from '../i18n/withBrokerTranslations';

function BranchesScreen({ token, apiBase }) {
  const [branches, setBranches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [statusMessage, setStatusMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState('');

  const [form, setForm] = useState({
    name: '',
    code: '',
    city: '',
    country: '',
    address: '',
    phone: '',
    email: '',
  });

  useEffect(() => {
    fetchBranches();
  }, []);

  async function fetchBranches() {
    try {
      setLoading(true);
      const res = await fetch(`${apiBase}/branches`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setBranches(data);
      }
    } catch {
      setErrorMessage('Failed to load branch offices');
    } finally {
      setLoading(false);
    }
  }

  async function handleCreateBranch(e) {
    e.preventDefault();
    setErrorMessage('');
    setStatusMessage('');
    try {
      const res = await fetch(`${apiBase}/branches`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify(form)
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to create branch');
      }
      setStatusMessage('Branch office added successfully.');
      setShowAddModal(false);
      setForm({ name: '', code: '', city: '', country: '', address: '', phone: '', email: '' });
      fetchBranches();
    } catch (err) {
      setErrorMessage(err.message);
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h2 className="broker-card-title">Regional Offices & Branches</h2>
          <p className="broker-card-subtitle">
            Manage physical office locations and geographical hubs for lead distribution.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setShowAddModal(true)}
          className="broker-btn-gold"
          style={{ margin: 0 }}
        >
          + Add Branch
        </button>
      </div>

      {statusMessage && (
        <div style={{ padding: '12px', background: 'rgba(34,197,94,0.1)', color: '#22c55e', borderRadius: '6px', marginBottom: '16px' }}>
          ✓ {statusMessage}
        </div>
      )}
      {errorMessage && (
        <div style={{ padding: '12px', background: 'rgba(239,68,68,0.1)', color: '#ef4444', borderRadius: '6px', marginBottom: '16px' }}>
          ✗ {errorMessage}
        </div>
      )}

      {loading ? (
        <div style={{ color: '#9da3af', padding: '24px' }}>Loading branches...</div>
      ) : branches.length === 0 ? (
        <div className="broker-card" style={{ textAlign: 'center', padding: '40px' }}>
          <p style={{ color: '#9da3af' }}>No regional branch offices registered yet.</p>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '20px' }}>
          {branches.map((b) => (
            <div key={b.id} className="broker-card" style={{ marginBottom: 0 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <h3 style={{ fontSize: '1.1rem', margin: 0, color: '#fff' }}>{b.name}</h3>
                <span className="broker-badge-pill">{b.code}</span>
              </div>
              <p style={{ color: '#d4af37', fontSize: '0.85rem', margin: '0 0 10px' }}>
                📍 {b.city || 'City'}, {b.country || 'Country'}
              </p>
              <div style={{ fontSize: '0.82rem', color: '#9da3af', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                {b.address && <div>🏢 {b.address}</div>}
                {b.phone && <div>📞 {b.phone}</div>}
                {b.email && <div>✉️ {b.email}</div>}
              </div>
            </div>
          ))}
        </div>
      )}

      {showAddModal && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000
        }}>
          <div className="broker-card" style={{ width: '480px', maxWidth: '90vw' }}>
            <h3 className="broker-card-title">Add Regional Branch</h3>
            <form onSubmit={handleCreateBranch} style={{ marginTop: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', color: '#9da3af', marginBottom: '4px' }}>Branch Name</label>
                <input
                  type="text"
                  required
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="e.g. Galle Fort Gallery"
                  style={{ width: '100%', padding: '8px', background: '#1a1d24', border: '1px solid #262930', borderRadius: '4px', color: '#fff' }}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', color: '#9da3af', marginBottom: '4px' }}>Branch Code</label>
                  <input
                    type="text"
                    required
                    value={form.code}
                    onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })}
                    placeholder="e.g. GLL-01"
                    style={{ width: '100%', padding: '8px', background: '#1a1d24', border: '1px solid #262930', borderRadius: '4px', color: '#fff' }}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', color: '#9da3af', marginBottom: '4px' }}>City</label>
                  <input
                    type="text"
                    value={form.city}
                    onChange={(e) => setForm({ ...form, city: e.target.value })}
                    placeholder="e.g. Galle"
                    style={{ width: '100%', padding: '8px', background: '#1a1d24', border: '1px solid #262930', borderRadius: '4px', color: '#fff' }}
                  />
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '16px' }}>
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  style={{ padding: '8px 16px', background: '#1a1d24', border: '1px solid #262930', color: '#fff', borderRadius: '4px', cursor: 'pointer' }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="broker-btn-gold"
                  style={{ margin: 0, padding: '8px 18px' }}
                >
                  Save Branch
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default withBrokerTranslations(BranchesScreen);
