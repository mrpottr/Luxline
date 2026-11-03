import React, { useEffect, useState } from 'react';
import { withBrokerTranslations } from '../i18n/withBrokerTranslations';

function OnboardingScreen({ token, apiBase, onProfileUpdated }) {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [statusMessage, setStatusMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState('');

  const [form, setForm] = useState({
    company_name: '',
    legal_name: '',
    address: '',
    city: '',
    country: '',
    contact_email: '',
    contact_phone: '',
    whatsapp_number: '',
    licence_region: 'LK',
    licence_number: '',
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
          company_name: data.company_name || '',
          legal_name: data.legal_name || '',
          address: data.address || '',
          city: data.city || '',
          country: data.country || '',
          contact_email: data.contact_email || '',
          contact_phone: data.contact_phone || '',
          whatsapp_number: data.whatsapp_number || '',
          licence_region: Object.keys(data.licences || {})[0] || 'LK',
          licence_number: Object.values(data.licences || {})[0] || '',
        });
      }
    } catch (err) {
      setErrorMessage('Failed to load profile');
    } finally {
      setLoading(false);
    }
  }

  async function handleSaveDraft(e) {
    e.preventDefault();
    setErrorMessage('');
    setStatusMessage('');
    try {
      const payload = {
        company_name: form.company_name,
        legal_name: form.legal_name,
        address: form.address,
        city: form.city,
        country: form.country,
        contact_email: form.contact_email,
        contact_phone: form.contact_phone,
        whatsapp_number: form.whatsapp_number,
        licences: form.licence_number ? { [form.licence_region]: form.licence_number } : {},
      };

      const res = await fetch(`${apiBase}/onboarding/profile`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Save failed');
      }

      const updated = await res.json();
      setProfile(updated);
      setStatusMessage('Draft details saved successfully.');
      if (onProfileUpdated) onProfileUpdated(updated);
    } catch (err) {
      setErrorMessage(err.message);
    }
  }

  async function handleSubmitReview() {
    setErrorMessage('');
    setStatusMessage('');
    setSubmitting(true);
    try {
      const res = await fetch(`${apiBase}/onboarding/submit`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Submission failed');
      }
      const updated = await res.json();
      setProfile(updated);
      setStatusMessage('Application submitted for administrative verification.');
      if (onProfileUpdated) onProfileUpdated(updated);
    } catch (err) {
      setErrorMessage(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return <div style={{ color: '#9da3af', padding: '24px' }}>Loading application details...</div>;
  }

  const isApproved = profile?.status === 'approved';
  const isSubmitted = profile?.status === 'submitted';

  return (
    <div style={{ maxWidth: '800px' }}>
      <div className="broker-card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h2 className="broker-card-title">Brokerage Verification & Licencing</h2>
            <p className="broker-card-subtitle">
              Verify your business profile, operating licences, and regional credentials to unlock full inventory publishing and lead distribution.
            </p>
          </div>
          <span
            className="broker-badge-pill"
            style={{
              backgroundColor: isApproved ? 'rgba(34, 197, 94, 0.15)' : 'rgba(234, 179, 8, 0.15)',
              color: isApproved ? '#22c55e' : '#eab308',
              borderColor: isApproved ? '#22c55e' : '#eab308',
            }}
          >
            Status: {profile?.status?.toUpperCase() || 'DRAFT'}
          </span>
        </div>

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

        <form onSubmit={handleSaveDraft} style={{ marginTop: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.82rem', color: '#9da3af', marginBottom: '6px' }}>Operating Company Name</label>
              <input
                type="text"
                value={form.company_name}
                onChange={(e) => setForm({ ...form, company_name: e.target.value })}
                required
                style={{ width: '100%', padding: '10px', background: '#1a1d24', border: '1px solid #262930', borderRadius: '6px', color: '#fff' }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.82rem', color: '#9da3af', marginBottom: '6px' }}>Registered Legal Entity Name</label>
              <input
                type="text"
                value={form.legal_name}
                onChange={(e) => setForm({ ...form, legal_name: e.target.value })}
                required
                style={{ width: '100%', padding: '10px', background: '#1a1d24', border: '1px solid #262930', borderRadius: '6px', color: '#fff' }}
              />
            </div>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.82rem', color: '#9da3af', marginBottom: '6px' }}>Headquarters Address</label>
            <input
              type="text"
              value={form.address}
              onChange={(e) => setForm({ ...form, address: e.target.value })}
              required
              style={{ width: '100%', padding: '10px', background: '#1a1d24', border: '1px solid #262930', borderRadius: '6px', color: '#fff' }}
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.82rem', color: '#9da3af', marginBottom: '6px' }}>City</label>
              <input
                type="text"
                value={form.city}
                onChange={(e) => setForm({ ...form, city: e.target.value })}
                required
                style={{ width: '100%', padding: '10px', background: '#1a1d24', border: '1px solid #262930', borderRadius: '6px', color: '#fff' }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.82rem', color: '#9da3af', marginBottom: '6px' }}>Country</label>
              <input
                type="text"
                value={form.country}
                onChange={(e) => setForm({ ...form, country: e.target.value })}
                required
                style={{ width: '100%', padding: '10px', background: '#1a1d24', border: '1px solid #262930', borderRadius: '6px', color: '#fff' }}
              />
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.82rem', color: '#9da3af', marginBottom: '6px' }}>Business Email</label>
              <input
                type="email"
                value={form.contact_email}
                onChange={(e) => setForm({ ...form, contact_email: e.target.value })}
                required
                style={{ width: '100%', padding: '10px', background: '#1a1d24', border: '1px solid #262930', borderRadius: '6px', color: '#fff' }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.82rem', color: '#9da3af', marginBottom: '6px' }}>Direct Phone</label>
              <input
                type="tel"
                value={form.contact_phone}
                onChange={(e) => setForm({ ...form, contact_phone: e.target.value })}
                required
                style={{ width: '100%', padding: '10px', background: '#1a1d24', border: '1px solid #262930', borderRadius: '6px', color: '#fff' }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.82rem', color: '#9da3af', marginBottom: '6px' }}>WhatsApp (VIP Leads)</label>
              <input
                type="tel"
                value={form.whatsapp_number}
                onChange={(e) => setForm({ ...form, whatsapp_number: e.target.value })}
                style={{ width: '100%', padding: '10px', background: '#1a1d24', border: '1px solid #262930', borderRadius: '6px', color: '#fff' }}
              />
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '120px 1fr', gap: '16px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.82rem', color: '#9da3af', marginBottom: '6px' }}>Licence Region</label>
              <input
                type="text"
                value={form.licence_region}
                onChange={(e) => setForm({ ...form, licence_region: e.target.value })}
                style={{ width: '100%', padding: '10px', background: '#1a1d24', border: '1px solid #262930', borderRadius: '6px', color: '#fff' }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.82rem', color: '#9da3af', marginBottom: '6px' }}>Brokerage / Realtor Licence Number</label>
              <input
                type="text"
                value={form.licence_number}
                onChange={(e) => setForm({ ...form, licence_number: e.target.value })}
                placeholder="e.g. REA-2026-9921"
                required
                style={{ width: '100%', padding: '10px', background: '#1a1d24', border: '1px solid #262930', borderRadius: '6px', color: '#fff' }}
              />
            </div>
          </div>

          <div style={{ display: 'flex', gap: '12px', marginTop: '16px' }}>
            <button
              type="submit"
              disabled={isSubmitted || isApproved}
              style={{
                padding: '10px 20px',
                background: '#1a1d24',
                color: '#fff',
                border: '1px solid #262930',
                borderRadius: '6px',
                cursor: isSubmitted || isApproved ? 'not-allowed' : 'pointer'
              }}
            >
              💾 Save Draft
            </button>

            {!isApproved && !isSubmitted && (
              <button
                type="button"
                onClick={handleSubmitReview}
                disabled={submitting}
                className="broker-btn-gold"
                style={{ margin: 0 }}
              >
                {submitting ? 'Submitting...' : '🚀 Submit for Verification'}
              </button>
            )}

            {isSubmitted && (
              <span style={{ color: '#eab308', alignSelf: 'center', fontSize: '0.88rem' }}>
                ⏳ Application is under review by Luxline compliance officers.
              </span>
            )}
          </div>
        </form>
      </div>
    </div>
  );
}

export default withBrokerTranslations(OnboardingScreen);
