import { useCallback, useEffect, useState } from 'react';
import { withBrokerTranslations } from '../i18n/withBrokerTranslations';
import { responseList, responseRecord } from './responseUtils.mjs';

function PromotionsScreen({ token, apiBase }) {
  const [listings, setListings] = useState([]);
  const [promotions, setPromotions] = useState([]);
  const [balance, setBalance] = useState(null);
  const [form, setForm] = useState({ listing_id: '', scope: 'city', location_code: '', placement_type: 'featured', starts_at: '', ends_at: '' });
  const [estimate, setEstimate] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [status, setStatus] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const [listingResponse, promotionResponse, balanceResponse] = await Promise.all([
        fetch(`${apiBase}/listings?limit=100&offset=0`, { headers }),
        fetch(`${apiBase}/promotions?limit=50&offset=0`, { headers }),
        fetch(`${apiBase}/credits/balance`, { headers })
      ]);
      const [listingBody, promotionBody, balanceBody] = await Promise.all([
        listingResponse.json().catch(() => ({})), promotionResponse.json().catch(() => ({})), balanceResponse.json().catch(() => ({}))
      ]);
      if (!listingResponse.ok || !promotionResponse.ok || !balanceResponse.ok) {
        throw new Error(listingBody.detail || promotionBody.detail || balanceBody.detail || 'Unable to load promotions.');
      }
      setListings(responseList(listingBody, 'listings'));
      setPromotions(responseList(promotionBody, 'promotions'));
      setBalance(responseRecord(balanceBody, 'wallet').balance ?? 0);
    } catch (loadError) {
      setError(loadError.message || 'Promotions are offline. Retry when connected.');
    } finally {
      setLoading(false);
    }
  }, [apiBase, token]);

  useEffect(() => { load(); }, [load]);

  function update(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
    setEstimate(null);
    setStatus('');
  }

  function payload() {
    return {
      ...form,
      listing_id: Number(form.listing_id),
      starts_at: new Date(form.starts_at).toISOString(),
      ends_at: new Date(form.ends_at).toISOString()
    };
  }

  async function estimateCost(event) {
    event.preventDefault();
    setError('');
    setStatus('');
    try {
      const response = await fetch(`${apiBase}/promotions/estimate`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }, body: JSON.stringify(payload())
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || 'Unable to estimate promotion cost.');
      setEstimate(body.credits);
    } catch (requestError) {
      setError(requestError.message || 'Promotion estimate is offline.');
    }
  }

  async function createPromotion(event) {
    event.preventDefault();
    if (estimate === null) {
      setError('Estimate the credit cost before creating a promotion.');
      return;
    }
    setSaving(true);
    setError('');
    setStatus('');
    try {
      const response = await fetch(`${apiBase}/promotions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}`, 'Idempotency-Key': crypto.randomUUID() },
        body: JSON.stringify(payload())
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || 'Unable to create promotion.');
      setStatus('Promotion created and credits reserved.');
      setEstimate(null);
      await load();
    } catch (requestError) {
      setError(requestError.message || 'Promotion service is offline.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="broker-card" aria-labelledby="broker-promotions-title">
      <header className="broker-card-header">
        <span className="broker-badge-pill">Visibility</span>
        <h1 id="broker-promotions-title" className="broker-card-title">Promotions</h1>
        <p className="broker-card-subtitle">Schedule paid placements by geography and period. Placements never override listing moderation.</p>
      </header>
      {error && <p className="broker-form-error" role="alert">{error}</p>}
      {status && <p className="broker-form-success" role="status">{status}</p>}
      {loading ? <p role="status">Loading promotion details…</p> : (
        <>
          <p className="broker-credit-balance">Available credits: <strong>{balance ?? '—'}</strong></p>
          <form className="broker-promotion-form" onSubmit={estimateCost}>
            <label>Live listing
              <select required value={form.listing_id} onChange={(event) => update('listing_id', event.target.value)}>
                <option value="">Select a listing</option>
                {listings.filter((listing) => listing.status === 'active' || listing.status === 'live').map((listing) => (
                  <option key={listing.listing_id || listing.id} value={listing.listing_id || listing.id}>{listing.title}</option>
                ))}
              </select>
            </label>
            <label>Geography level
              <select value={form.scope} onChange={(event) => update('scope', event.target.value)}>
                <option value="city">City</option><option value="locality">Locality</option><option value="province">Province</option><option value="country">Country</option>
              </select>
            </label>
            <label>Geography code
              <input required maxLength="120" value={form.location_code} onChange={(event) => update('location_code', event.target.value)} placeholder="Configured area code" />
            </label>
            <label>Placement
              <select value={form.placement_type} onChange={(event) => update('placement_type', event.target.value)}>
                <option value="featured">Featured</option><option value="premium">Premium</option><option value="urgent">Urgent</option>
              </select>
            </label>
            <label>Starts at
              <input required type="datetime-local" value={form.starts_at} onChange={(event) => update('starts_at', event.target.value)} />
            </label>
            <label>Ends at
              <input required type="datetime-local" value={form.ends_at} onChange={(event) => update('ends_at', event.target.value)} />
            </label>
            <div className="broker-promotion-actions">
              <button className="broker-btn-secondary" type="submit">Preview credit cost</button>
              {estimate !== null && <button className="broker-btn-gold" type="button" disabled={saving || balance < estimate} onClick={createPromotion}>{saving ? 'Creating…' : `Create promotion · ${estimate} credits`}</button>}
            </div>
            {estimate !== null && <p className="broker-promotion-estimate" role="status">Estimated cost: {estimate} credits. Current balance: {balance}.</p>}
          </form>
          <h2 className="broker-section-heading">Scheduled and active promotions</h2>
          {!promotions.length ? <p>No promotions yet.</p> : <div className="broker-table-scroll"><table className="broker-analytics-table"><thead><tr><th>Listing</th><th>Placement</th><th>Area</th><th>Period</th><th>Credits</th><th>Status</th></tr></thead><tbody>
            {promotions.map((promotion) => <tr key={promotion.id}><td>#{promotion.listing_id}</td><td>{promotion.placement_type}</td><td>{promotion.location_code} ({promotion.scope})</td><td>{new Date(promotion.starts_at).toLocaleDateString()} – {new Date(promotion.ends_at).toLocaleDateString()}</td><td>{promotion.credits_spent}</td><td>{promotion.status}</td></tr>)}
          </tbody></table></div>}
        </>
      )}
    </section>
  );
}

export default withBrokerTranslations(PromotionsScreen);
