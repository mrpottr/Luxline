import React, { useEffect, useState } from 'react';

export default function PublicProfileEditor({ token, apiBase }) {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [statusMessage, setStatusMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState('');

  const [form, setForm] = useState({
    logo_url: '',
    banner_url: '',
    about: '',
    website: '',
    languages: 'en',
    service_areas: '',
  });

  useEffect(() => {
    fetchProfile();
  }, []);

  async function fetchProfile() {
    try {
      setLoading(true);
      const res = await fetch(`${apiBase}/onboarding/profile`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setProfile(data);
        setForm({
          logo_url: data.logo_url || '',
          banner_url: data.banner_url || '',
          about: data.about || '',
          website: data.website || '',
          languages: (data.languages || []).join(', ') || 'en',
          service_areas: (data.service_areas || []).join(', '),
        });
      }
    } catch {
      setErrorMessage('Failed to load profile');
    } finally {
      setLoading(false);
    }
  }

  async function handleSave(e) {
    e.preventDefault();
    setSaving(true);
    setStatusMessage('');
    setErrorMessage('');
    try {
      const payload = {
        logo_url: form.logo_url,
        banner_url: form.banner_url,
        about: form.about,
        website: form.website,
        languages: form.languages.split(',').map((s) => s.trim()).filter(Boolean),
        service_areas: form.service_areas.split(',').map((s) => s.trim()).filter(Boolean),
      };

      const res = await fetch(`${apiBase}/onboarding/profile`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Save failed');
      }

      const updated = await res.json();
      setProfile(updated);
      setStatusMessage('Branded profile updated successfully.');
    } catch (err) {
      setErrorMessage(err.message);
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return <div style={{ color: '#9da3af', padding: '24px' }}>Loading branded profile...</div>;
  }

  return (
    <div style={{ maxWidth: '800px' }}>
      <div className="broker-card">
        <h2 className="broker-card-title">Branded Public Profile & Showcase</h2>
        <p className="broker-card-subtitle">
          Customize your public presence on the Luxline global directory.
        </p>

        {statusMessage && (
          <div style={{ padding: '12px', background: 'rgba(34,197,94,0.1)', color: '#22c55e', borderRadius: '6px', marginTop: '16px' }}>
            ✓ {statusMessage}
          </div>
        )}
        {errorMessage && (
          <div style={{ padding: '12px', background: 'rgba(239,68,68,0.1)', color: '#ef4444', borderRadius: '6px', marginTop: '16px' }}>
            ✗ {errorMessage}
          </div>
        )}

        <form onSubmit={handleSave} style={{ marginTop: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div>
            <label style={{ display: 'block', fontSize: '0.82rem', color: '#9da3af', marginBottom: '6px' }}>Brokerage Logo URL</label>
            <input
              type="url"
              value={form.logo_url}
              onChange={(e) => setForm({ ...form, logo_url: e.target.value })}
              placeholder="https://.../logo.png"
              style={{ width: '100%', padding: '10px', background: '#1a1d24', border: '1px solid #262930', borderRadius: '6px', color: '#fff' }}
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.82rem', color: '#9da3af', marginBottom: '6px' }}>Hero Banner Image URL</label>
            <input
              type="url"
              value={form.banner_url}
              onChange={(e) => setForm({ ...form, banner_url: e.target.value })}
              placeholder="https://.../banner.jpg"
              style={{ width: '100%', padding: '10px', background: '#1a1d24', border: '1px solid #262930', borderRadius: '6px', color: '#fff' }}
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.82rem', color: '#9da3af', marginBottom: '6px' }}>Official Website</label>
            <input
              type="url"
              value={form.website}
              onChange={(e) => setForm({ ...form, website: e.target.value })}
              placeholder="https://youragency.com"
              style={{ width: '100%', padding: '10px', background: '#1a1d24', border: '1px solid #262930', borderRadius: '6px', color: '#fff' }}
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.82rem', color: '#9da3af', marginBottom: '6px' }}>About & Brand Story</label>
            <textarea
              rows={4}
              value={form.about}
              onChange={(e) => setForm({ ...form, about: e.target.value })}
              placeholder="Describe your firm's heritage, asset specialties, and track record..."
              style={{ width: '100%', padding: '10px', background: '#1a1d24', border: '1px solid #262930', borderRadius: '6px', color: '#fff' }}
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.82rem', color: '#9da3af', marginBottom: '6px' }}>Languages Spoken (comma-separated)</label>
              <input
                type="text"
                value={form.languages}
                onChange={(e) => setForm({ ...form, languages: e.target.value })}
                placeholder="en, si, ta, ar, fr"
                style={{ width: '100%', padding: '10px', background: '#1a1d24', border: '1px solid #262930', borderRadius: '6px', color: '#fff' }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.82rem', color: '#9da3af', marginBottom: '6px' }}>Service Areas (comma-separated)</label>
              <input
                type="text"
                value={form.service_areas}
                onChange={(e) => setForm({ ...form, service_areas: e.target.value })}
                placeholder="Colombo, Galle, Kandy, London, Dubai"
                style={{ width: '100%', padding: '10px', background: '#1a1d24', border: '1px solid #262930', borderRadius: '6px', color: '#fff' }}
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={saving}
            className="broker-btn-gold"
            style={{ width: '200px' }}
          >
            {saving ? 'Saving...' : '💾 Save Branded Profile'}
          </button>
        </form>
      </div>
    </div>
  );
}

