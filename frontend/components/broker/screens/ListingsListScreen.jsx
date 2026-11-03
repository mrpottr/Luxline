import React, { useEffect, useState } from 'react';

function formatMoney(amount, currency) {
  try {
    return new Intl.NumberFormat(undefined, { style: 'currency', currency, maximumFractionDigits: 0 }).format(Number(amount));
  } catch {
    return `${currency} ${Number(amount).toLocaleString()}`;
  }
}

export default function ListingsListScreen({ token, apiBase, onNewListing, onEditListing, onOpenImport }) {
  const [listings, setListings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusMessage, setStatusMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [category, setCategory] = useState('');
  const [categories, setCategories] = useState([]);
  const [offset, setOffset] = useState(0);
  const pageSize = 25;

  useEffect(() => {
    fetchListings();
  }, [category, offset]);

  useEffect(() => {
    fetch(`${apiBase}/listings/categories`, { headers: { Authorization: `Bearer ${token}` } })
      .then((response) => response.ok ? response.json() : Promise.reject(new Error('Unable to load listing categories')))
      .then(setCategories)
      .catch((error) => setErrorMessage(error.message));
  }, [apiBase, token]);

  async function fetchListings() {
    try {
      setLoading(true);
      const params = new URLSearchParams({ limit: String(pageSize), offset: String(offset), sort: '-created_at' });
      if (category) params.set('category', category);
      const res = await fetch(`${apiBase}/listings?${params}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(res.status === 403 ? 'You do not have permission to view these listings.' : err.detail || 'Failed to load listings');
      }
      setListings(await res.json());
    } catch (err) {
      setErrorMessage(err.message || 'Connection unavailable. Check your connection and retry.');
    } finally {
      setLoading(false);
    }
  }

  async function handleTogglePublish(listing) {
    const isDraft = listing.status === 'draft';
    const endpoint = isDraft ? `${apiBase}/listings/${listing.listing_id}/publish` : `${apiBase}/listings/${listing.listing_id}/pause`;
    setErrorMessage('');
    setStatusMessage('');
    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` }
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Action failed');
      }
      setStatusMessage(isDraft ? 'Listing published to marketplace!' : 'Listing paused.');
      fetchListings();
    } catch (err) {
      setErrorMessage(err.message);
    }
  }

  async function handleArchive(listing) {
    try {
      const res = await fetch(`${apiBase}/listings/${listing.listing_id}`, {
        method: 'DELETE', headers: { Authorization: `Bearer ${token}` }
      });
      if (!res.ok) throw new Error('Unable to archive this listing');
      fetchListings();
    } catch (err) {
      setErrorMessage(err.message);
    }
  }

  async function handleExport() {
    try {
      const res = await fetch(`${apiBase}/listings/export.csv?limit=500`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (!res.ok) throw new Error('Unable to export listings');
      const url = URL.createObjectURL(await res.blob());
      const link = document.createElement('a');
      link.href = url;
      link.download = 'broker-listings.csv';
      link.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setErrorMessage(err.message || 'Connection unavailable. Check your connection and retry.');
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h2 className="broker-card-title">Inventory Management</h2>
          <p className="broker-card-subtitle">
            Manage your firm's luxury listings, review quality scores, and publish to the global marketplace.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '12px' }}>
          <button
            type="button"
            onClick={onOpenImport}
            style={{
              padding: '10px 18px',
              background: '#1a1d24',
              color: '#fff',
              border: '1px solid #262930',
              borderRadius: '6px',
              cursor: 'pointer'
            }}
          >
            📥 CSV Bulk Import
          </button>
          <button type="button" onClick={handleExport} style={{ padding: '10px 18px', background: '#1a1d24', color: '#fff', border: '1px solid #262930', borderRadius: '6px', cursor: 'pointer' }}>
            Export CSV
          </button>
          <button
            type="button"
            onClick={onNewListing}
            className="broker-btn-gold"
            style={{ margin: 0 }}
          >
            + Create New Listing
          </button>
        </div>
      </div>

      {statusMessage && (
        <div style={{ padding: '12px', background: 'rgba(34,197,94,0.1)', color: '#22c55e', borderRadius: '6px', marginBottom: '16px' }}>
          ✓ {statusMessage}
        </div>
      )}
      {errorMessage && (
        <div role="alert" style={{ padding: '12px', background: 'rgba(239,68,68,0.1)', color: '#ef4444', borderRadius: '6px', marginBottom: '16px' }}>
          ✗ {errorMessage}
          <button type="button" onClick={fetchListings} style={{ marginLeft: '12px' }}>Retry</button>
        </div>
      )}

      {loading ? (
        <div style={{ color: '#9da3af', padding: '24px' }}>Loading inventory...</div>
      ) : listings.length === 0 ? (
        <div className="broker-card" style={{ textAlign: 'center', padding: '48px' }}>
          <div style={{ fontSize: '2rem', marginBottom: '12px' }}>🏰</div>
          <h3 style={{ color: '#fff', margin: '0 0 8px' }}>No Listings Added Yet</h3>
          <p style={{ color: '#9da3af', maxWidth: '400px', margin: '0 auto 20px' }}>
            Add your first luxury villa, supercar, or yacht to start receiving verified buyer leads.
          </p>
          <button type="button" onClick={onNewListing} className="broker-btn-gold">
            + Create First Listing
          </button>
        </div>
      ) : (
        <>
        <label style={{ display: 'inline-flex', gap: '8px', alignItems: 'center', marginBottom: '16px', color: '#9da3af' }}>
          Category
          <select aria-label="Filter listings by category" value={category} onChange={(event) => { setOffset(0); setCategory(event.target.value); }}>
            <option value="">All categories</option>
            {categories.map((value) => <option key={value} value={value}>{value.replaceAll('_', ' ')}</option>)}
          </select>
        </label>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {listings.map((item) => {
            const isGreen = item.quality_rating === 'green';
            const isOrange = item.quality_rating === 'orange';
            const badgeColor = isGreen ? '#22c55e' : isOrange ? '#eab308' : '#ef4444';
            const badgeBg = isGreen ? 'rgba(34,197,94,0.15)' : isOrange ? 'rgba(234,179,8,0.15)' : 'rgba(239,68,68,0.15)';

            return (
              <div key={item.id} className="broker-card broker-listing-row" style={{ marginBottom: 0, display: 'flex', gap: '20px', alignItems: 'center' }}>
                <div
                  style={{
                    width: '120px',
                    height: '84px',
                    borderRadius: '6px',
                    background: item.photos?.length ? `url(${item.photos[0]}) center/cover` : '#1a1d24',
                    border: '1px solid #262930',
                    flexShrink: 0,
                  }}
                />

                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <h3 style={{ margin: 0, fontSize: '1.1rem', color: '#fff' }}>{item.title}</h3>
                    <span
                      className="broker-badge-pill"
                      style={{ background: badgeBg, color: badgeColor, borderColor: badgeColor }}
                    >
                      Score: {item.quality_score}/100 ({item.quality_rating.toUpperCase()})
                    </span>
                    <span
                      className="broker-badge-pill"
                      style={{
                        background: item.status === 'active' ? 'rgba(34,197,94,0.15)' : 'rgba(156,163,175,0.15)',
                        color: item.status === 'active' ? '#22c55e' : '#9ca3af',
                      }}
                    >
                      {item.status.toUpperCase()}
                    </span>
                  </div>

                  <p style={{ margin: '4px 0 0', color: '#d4af37', fontWeight: 600 }}>
                    {formatMoney(item.price, item.currency)} • {item.category.replaceAll('_', ' ').toUpperCase()}
                  </p>
                  <p style={{ margin: '2px 0 0', fontSize: '0.82rem', color: '#9da3af' }}>
                    📍 {item.location_city}, {item.location_country}
                  </p>

                  {item.quality_suggestions?.length > 0 && item.quality_rating !== 'green' && (
                    <div style={{ marginTop: '8px', fontSize: '0.78rem', color: '#eab308' }}>
                      💡 Fix tip: {item.quality_suggestions[0]}
                    </div>
                  )}
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', flexShrink: 0 }}>
                  <button type="button" onClick={() => onEditListing(item)}>Edit</button>
                  <button
                    type="button"
                    onClick={() => handleTogglePublish(item)}
                    style={{
                      padding: '8px 16px',
                      borderRadius: '4px',
                      border: '1px solid #262930',
                      background: item.status === 'active' ? '#1a1d24' : '#d4af37',
                      color: item.status === 'active' ? '#fff' : '#0a0b0d',
                      fontWeight: 600,
                      cursor: 'pointer',
                    }}
                  >
                    {item.status === 'active' ? '⏸ Pause' : '🚀 Publish'}
                  </button>
                  <button type="button" onClick={() => handleArchive(item)}>Archive</button>
                </div>
              </div>
            );
          })}
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '16px' }}>
          <button type="button" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - pageSize))}>Previous</button>
          <button type="button" disabled={listings.length < pageSize} onClick={() => setOffset(offset + pageSize)}>Next</button>
        </div>
        </>
      )}
    </div>
  );
}

