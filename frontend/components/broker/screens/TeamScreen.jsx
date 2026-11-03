import React, { useEffect, useState } from 'react';

export default function TeamScreen({ token, apiBase }) {
  const [members, setMembers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [statusMessage, setStatusMessage] = useState('');

  const [form, setForm] = useState({
    user_id: '',
    role: 'broker_agent',
    display_name: '',
    title: '',
    email: '',
    phone: '',
    whatsapp: '',
  });

  useEffect(() => {
    fetchMembers();
  }, []);

  async function fetchMembers() {
    try {
      setLoading(true);
      const res = await fetch(`${apiBase}/team/members`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setMembers(data);
      } else {
        const err = await res.json();
        setErrorMessage(err.detail || 'Failed to fetch team members');
      }
    } catch {
      setErrorMessage('Connection failed');
    } finally {
      setLoading(false);
    }
  }

  async function handleAddMember(e) {
    e.preventDefault();
    setErrorMessage('');
    setStatusMessage('');
    try {
      const payload = {
        user_id: Number(form.user_id),
        role: form.role,
        display_name: form.display_name,
        title: form.title,
        email: form.email,
        phone: form.phone,
        whatsapp: form.whatsapp,
      };

      const res = await fetch(`${apiBase}/team/members`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to add member');
      }

      setStatusMessage('Team member added successfully.');
      setShowAddModal(false);
      setForm({ user_id: '', role: 'broker_agent', display_name: '', title: '', email: '', phone: '', whatsapp: '' });
      fetchMembers();
    } catch (err) {
      setErrorMessage(err.message);
    }
  }

  async function handleRemoveMember(memberId) {
    if (!window.confirm('Are you sure you want to remove this member from the organization?')) return;
    setErrorMessage('');
    setStatusMessage('');
    try {
      const res = await fetch(`${apiBase}/team/members/${memberId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to remove member');
      }
      setStatusMessage('Member removed.');
      fetchMembers();
    } catch (err) {
      setErrorMessage(err.message);
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h2 className="broker-card-title">Team & Agent Roster</h2>
          <p className="broker-card-subtitle">
            Manage agency partners, branch managers, and listing agents with fine-grained access control.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setShowAddModal(true)}
          className="broker-btn-gold"
          style={{ margin: 0 }}
        >
          + Add Team Member
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
        <div style={{ color: '#9da3af', padding: '24px' }}>Loading team members...</div>
      ) : members.length === 0 ? (
        <div className="broker-card" style={{ textAlign: 'center', padding: '40px' }}>
          <p style={{ color: '#9da3af' }}>No team members registered yet.</p>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '20px' }}>
          {members.map((m) => (
            <div key={m.id} className="broker-card" style={{ marginBottom: 0, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <h3 style={{ fontSize: '1.1rem', margin: '0 0 4px', color: '#fff' }}>{m.display_name}</h3>
                  <span
                    className="broker-badge-pill"
                    style={{
                      background: m.role === 'broker_owner' ? 'rgba(212,175,55,0.15)' : 'rgba(59,130,246,0.15)',
                      color: m.role === 'broker_owner' ? '#d4af37' : '#3b82f6',
                      borderColor: m.role === 'broker_owner' ? '#d4af37' : '#3b82f6',
                    }}
                  >
                    {m.role.replace('broker_', '').toUpperCase()}
                  </span>
                </div>
                <p style={{ color: '#d4af37', fontSize: '0.82rem', margin: '0 0 12px' }}>{m.title || 'Agent'}</p>

                <div style={{ fontSize: '0.82rem', color: '#9da3af', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  {m.email && <div>✉️ {m.email}</div>}
                  {m.phone && <div>📞 {m.phone}</div>}
                  {m.whatsapp && <div>💬 WA: {m.whatsapp}</div>}
                  <div>🆔 User ID: {m.user_id}</div>
                </div>
              </div>

              <div style={{ marginTop: '16px', borderTop: '1px solid #262930', paddingTop: '12px', display: 'flex', justifyContent: 'flex-end' }}>
                <button
                  type="button"
                  onClick={() => handleRemoveMember(m.id)}
                  style={{ background: 'transparent', border: 'none', color: '#ef4444', cursor: 'pointer', fontSize: '0.8rem' }}
                >
                  Remove Member
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add Member Modal */}
      {showAddModal && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000
        }}>
          <div className="broker-card" style={{ width: '480px', maxWidth: '90vw' }}>
            <h3 className="broker-card-title">Add Team Member</h3>
            <p className="broker-card-subtitle">Connect an existing user ID to your broker organization.</p>

            <form onSubmit={handleAddMember} style={{ marginTop: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', color: '#9da3af', marginBottom: '4px' }}>User ID</label>
                <input
                  type="number"
                  required
                  value={form.user_id}
                  onChange={(e) => setForm({ ...form, user_id: e.target.value })}
                  placeholder="e.g. 102"
                  style={{ width: '100%', padding: '8px', background: '#1a1d24', border: '1px solid #262930', borderRadius: '4px', color: '#fff' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', color: '#9da3af', marginBottom: '4px' }}>Display Name</label>
                <input
                  type="text"
                  required
                  value={form.display_name}
                  onChange={(e) => setForm({ ...form, display_name: e.target.value })}
                  placeholder="e.g. Sarah Jenkins"
                  style={{ width: '100%', padding: '8px', background: '#1a1d24', border: '1px solid #262930', borderRadius: '4px', color: '#fff' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', color: '#9da3af', marginBottom: '4px' }}>Assigned Role</label>
                <select
                  value={form.role}
                  onChange={(e) => setForm({ ...form, role: e.target.value })}
                  style={{ width: '100%', padding: '8px', background: '#1a1d24', border: '1px solid #262930', borderRadius: '4px', color: '#fff' }}
                >
                  <option value="broker_agent">Agent (Own listings & leads)</option>
                  <option value="broker_manager">Manager (All listings & team leads)</option>
                  <option value="broker_viewer">Viewer (Read-only analytics)</option>
                  <option value="broker_owner">Owner (Full admin & billing)</option>
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', color: '#9da3af', marginBottom: '4px' }}>Professional Title</label>
                <input
                  type="text"
                  value={form.title}
                  onChange={(e) => setForm({ ...form, title: e.target.value })}
                  placeholder="e.g. Senior Luxury Villa Partner"
                  style={{ width: '100%', padding: '8px', background: '#1a1d24', border: '1px solid #262930', borderRadius: '4px', color: '#fff' }}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', color: '#9da3af', marginBottom: '4px' }}>Email</label>
                  <input
                    type="email"
                    value={form.email}
                    onChange={(e) => setForm({ ...form, email: e.target.value })}
                    style={{ width: '100%', padding: '8px', background: '#1a1d24', border: '1px solid #262930', borderRadius: '4px', color: '#fff' }}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', color: '#9da3af', marginBottom: '4px' }}>Phone</label>
                  <input
                    type="tel"
                    value={form.phone}
                    onChange={(e) => setForm({ ...form, phone: e.target.value })}
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
                  Save Member
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
