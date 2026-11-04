import React, { useEffect, useRef, useState } from 'react';
import { withBrokerTranslations } from '../i18n/withBrokerTranslations';

function newIdempotencyKey() {
  return globalThis.crypto?.randomUUID?.() || `broker-listing-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function ListingEditorScreen({ token, apiBase, onDone, listing = null, requiresCommissionTerms = false }) {
  const [saving, setSaving] = useState(false);
  const [uploadingMedia, setUploadingMedia] = useState(false);
  const [uploadAltText, setUploadAltText] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [categories, setCategories] = useState([]);
  const [categoriesLoading, setCategoriesLoading] = useState(true);
  const [revisions, setRevisions] = useState([]);
  const idempotencyKey = useRef(newIdempotencyKey());
  const previousPayload = useRef(null);

  useEffect(() => {
    fetch(`${apiBase}/listings/categories`, { headers: { Authorization: `Bearer ${token}` } })
      .then(async (response) => {
        if (!response.ok) throw new Error('Unable to load listing categories');
        setCategories(await response.json());
      })
      .catch((error) => setErrorMessage(error.message || 'Unable to load listing categories'))
      .finally(() => setCategoriesLoading(false));
  }, [apiBase, token]);

  useEffect(() => {
    if (!listing?.listing_id) return;
    fetch(`${apiBase}/listings/${listing.listing_id}/revisions`, { headers: { Authorization: `Bearer ${token}` } })
      .then((response) => response.ok ? response.json() : Promise.reject(new Error('Unable to load listing history')))
      .then(setRevisions)
      .catch(() => setRevisions([]));
  }, [apiBase, token, listing?.listing_id]);

  const [form, setForm] = useState({
    title: listing?.title || '',
    category: listing?.category || '',
    price: listing?.price || '',
    currency: listing?.currency || '',
    location_country: listing?.location_country || '',
    location_city: listing?.location_city || '',
    description: listing?.description || '',
    media: listing?.media || (listing?.photos || []).map((url, sort_order) => ({ url, media_type: 'image', sort_order, alt_text: '' })),
    owner_name: listing?.owner_name || '',
    owner_mandate_reference: listing?.owner_mandate_reference || '',
    owner_consent: listing?.owner_consent || false,
    commission_terms: listing?.commission_terms || '',
    urgent_flag: listing?.urgent_flag || false,
  });

  // Calculate live quality estimation
  const mediaItems = form.media.filter((item) => item.url.trim());
  const estimatedScore =
    (form.title.length >= 15 ? 10 : 0) +
    (mediaItems.length >= 5 ? 25 : mediaItems.length >= 1 ? 10 : 0) +
    (form.description.length >= 250 ? 20 : form.description.length >= 80 ? 10 : 0) +
    (Number(form.price) > 0 ? 15 : 0) +
    (form.location_country && form.location_city ? 10 : 0) +
    (form.owner_consent ? 10 : 0) +
    10; // base attributes

  const estimatedRating = estimatedScore >= 80 ? 'green' : estimatedScore >= 50 ? 'orange' : 'red';
  const scoreColor = estimatedRating === 'green' ? '#22c55e' : estimatedRating === 'orange' ? '#eab308' : '#ef4444';

  async function handleSubmit(e) {
    e.preventDefault();
    setSaving(true);
    setErrorMessage('');
    try {
      const payload = {
        title: form.title,
        category: form.category,
        price: Number(form.price),
        currency: form.currency,
        location_country: form.location_country,
        location_city: form.location_city,
        description: form.description,
        media: mediaItems.map((item, sort_order) => ({ ...item, sort_order })),
        owner_consent: form.owner_consent,
        urgent_flag: form.urgent_flag,
        attributes: {
          submitted_via: 'broker_portal',
        },
      };
      if (requiresCommissionTerms) {
        payload.owner_name = form.owner_name.trim();
        payload.owner_mandate_reference = form.owner_mandate_reference.trim();
        payload.commission_terms = form.commission_terms.trim();
      }
      const serializedPayload = JSON.stringify(payload);
      if (previousPayload.current !== serializedPayload) {
        previousPayload.current = serializedPayload;
        idempotencyKey.current = newIdempotencyKey();
      }

      const res = await fetch(listing ? `${apiBase}/listings/${listing.listing_id}` : `${apiBase}/listings`, {
        method: listing ? 'PATCH' : 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
          ...(listing ? {} : { 'Idempotency-Key': idempotencyKey.current }),
        },
        body: serializedPayload,
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to create listing');
      }

      onDone();
    } catch (err) {
      setErrorMessage(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleMediaUpload(event) {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;
    if (file.size > 8 * 1024 * 1024) {
      setErrorMessage('Files must be 8 MiB or smaller.');
      return;
    }
    setUploadingMedia(true);
    setErrorMessage('');
    try {
      const dataUrl = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(String(reader.result));
        reader.onerror = () => reject(new Error('Unable to read this file.'));
        reader.readAsDataURL(file);
      });
      const response = await fetch(`${apiBase}/media/upload`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          content_base64: dataUrl.split(',')[1],
          content_type: file.type,
          media_type: file.type === 'application/pdf' ? 'floor_plan' : 'image',
          alt_text: uploadAltText,
        }),
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(result.detail || 'Media upload failed.');
      setForm((current) => ({
        ...current,
        media: [...current.media, {
          url: result.url,
          media_type: result.media_type,
          sort_order: current.media.length,
          alt_text: result.alt_text,
        }],
      }));
      setUploadAltText('');
    } catch (error) {
      setErrorMessage(error.message || 'Media upload failed.');
    } finally {
      setUploadingMedia(false);
    }
  }

  return (
    <div style={{ maxWidth: '840px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <h2 className="broker-card-title">{listing ? 'Edit Listing' : 'Create Luxury Listing'}</h2>
          <p className="broker-card-subtitle">
            Publish verified high-end inventory to global HNWI buyers.
          </p>
        </div>
        <button
          type="button"
          onClick={onDone}
          style={{ background: 'transparent', border: 'none', color: '#9da3af', cursor: 'pointer' }}
        >
          ← Cancel
        </button>
      </div>

      {errorMessage && (
        <div style={{ padding: '12px', background: 'rgba(239,68,68,0.1)', color: '#ef4444', borderRadius: '6px', marginBottom: '16px' }}>
          ✗ {errorMessage}
        </div>
      )}

      {/* Quality Score Bar */}
      <div className="broker-card" style={{ padding: '16px 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <span style={{ fontSize: '0.82rem', color: '#9da3af', textTransform: 'uppercase' }}>Live Quality Readiness</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px' }}>
            <span style={{ fontSize: '1.25rem', fontWeight: 700, color: scoreColor }}>{estimatedScore}/100</span>
            <span className="broker-badge-pill" style={{ color: scoreColor, borderColor: scoreColor }}>
              {estimatedRating.toUpperCase()}
            </span>
          </div>
        </div>
        <p style={{ margin: 0, fontSize: '0.82rem', color: '#9da3af', maxWidth: '380px' }}>
          Listings scoring 80+ receive priority indexing and up to 3.5× higher buyer inquiry rates.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="broker-card" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <div>
          <label style={{ display: 'block', fontSize: '0.82rem', color: '#9da3af', marginBottom: '6px' }}>Listing Title</label>
          <input
            type="text"
            required
            placeholder="e.g. The Sapphire Beachfront Villa - Mirissa Bay"
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
            style={{ width: '100%', padding: '10px', background: '#1a1d24', border: '1px solid #262930', borderRadius: '6px', color: '#fff' }}
          />
        </div>

        <div className="broker-listing-form-grid broker-listing-form-grid--price">
          <div>
            <label style={{ display: 'block', fontSize: '0.82rem', color: '#9da3af', marginBottom: '6px' }}>Category</label>
            <select
              value={form.category}
              onChange={(e) => setForm({ ...form, category: e.target.value })}
              style={{ width: '100%', padding: '10px', background: '#1a1d24', border: '1px solid #262930', borderRadius: '6px', color: '#fff' }}
            >
              <option value="">Select category</option>
              {categories.map((category) => <option key={category} value={category}>{category.replaceAll('_', ' ')}</option>)}
            </select>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.82rem', color: '#9da3af', marginBottom: '6px' }}>Price</label>
            <input
              type="number"
              required
              min="1"
              placeholder="e.g. 1500000"
              value={form.price}
              onChange={(e) => setForm({ ...form, price: e.target.value })}
              style={{ width: '100%', padding: '10px', background: '#1a1d24', border: '1px solid #262930', borderRadius: '6px', color: '#fff' }}
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.82rem', color: '#9da3af', marginBottom: '6px' }}>Currency</label>
            <input
              type="text"
              required
              minLength={3}
              maxLength={3}
              pattern="[A-Z]{3}"
              aria-label="Currency ISO code"
              value={form.currency}
              onChange={(e) => setForm({ ...form, currency: e.target.value.toUpperCase() })}
              placeholder="ISO code"
              style={{ width: '100%', padding: '10px', background: '#1a1d24', border: '1px solid #262930', borderRadius: '6px', color: '#fff' }}
            />
          </div>
        </div>

        <div className="broker-listing-form-grid">
          <div>
            <label style={{ display: 'block', fontSize: '0.82rem', color: '#9da3af', marginBottom: '6px' }}>Country</label>
            <input
              type="text"
              required
              placeholder="e.g. Sri Lanka"
              value={form.location_country}
              onChange={(e) => setForm({ ...form, location_country: e.target.value })}
              style={{ width: '100%', padding: '10px', background: '#1a1d24', border: '1px solid #262930', borderRadius: '6px', color: '#fff' }}
            />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: '0.82rem', color: '#9da3af', marginBottom: '6px' }}>City / Locality</label>
            <input
              type="text"
              required
              placeholder="e.g. Galle / Mirissa"
              value={form.location_city}
              onChange={(e) => setForm({ ...form, location_city: e.target.value })}
              style={{ width: '100%', padding: '10px', background: '#1a1d24', border: '1px solid #262930', borderRadius: '6px', color: '#fff' }}
            />
          </div>
        </div>

        <div>
          <label style={{ display: 'block', fontSize: '0.82rem', color: '#9da3af', marginBottom: '6px' }}>Description</label>
          <textarea
            rows={5}
            required
            placeholder="Describe architectural features, provenance, private beach frontage, specs..."
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            style={{ width: '100%', padding: '10px', background: '#1a1d24', border: '1px solid #262930', borderRadius: '6px', color: '#fff' }}
          />
        </div>

        <div>
          <label style={{ display: 'block', fontSize: '0.82rem', color: '#9da3af', marginBottom: '6px' }}>Listing media (HTTPS references)</label>
          {form.media.map((item, index) => (
            <div key={`${index}-${item.url}`} className="broker-listing-form-grid" style={{ marginBottom: '8px' }}>
              <input aria-label={`Media URL ${index + 1}`} type="url" required value={item.url} placeholder="https://..." onChange={(event) => setForm({ ...form, media: form.media.map((current, row) => row === index ? { ...current, url: event.target.value } : current) })} />
              <select aria-label={`Media type ${index + 1}`} value={item.media_type} onChange={(event) => setForm({ ...form, media: form.media.map((current, row) => row === index ? { ...current, media_type: event.target.value } : current) })}>
                <option value="image">Image</option><option value="floor_plan">Floor plan</option><option value="video">Video</option>
              </select>
              <input aria-label={`Alt text ${index + 1}`} required={item.media_type !== 'video'} value={item.alt_text || ''} placeholder="Describe the image" onChange={(event) => setForm({ ...form, media: form.media.map((current, row) => row === index ? { ...current, alt_text: event.target.value } : current) })} />
              <button type="button" disabled={index === 0} onClick={() => { const next = [...form.media]; [next[index - 1], next[index]] = [next[index], next[index - 1]]; setForm({ ...form, media: next }); }}>Move up</button>
              <button type="button" disabled={index === form.media.length - 1} onClick={() => { const next = [...form.media]; [next[index + 1], next[index]] = [next[index], next[index + 1]]; setForm({ ...form, media: next }); }}>Move down</button>
              <button type="button" onClick={() => setForm({ ...form, media: form.media.filter((_, row) => row !== index) })}>Remove</button>
            </div>
          ))}
          <button type="button" onClick={() => setForm({ ...form, media: [...form.media, { url: '', media_type: 'image', sort_order: form.media.length, alt_text: '' }] })}>Add media</button>
          <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '8px', marginTop: '12px' }}>
            <label htmlFor="broker-media-alt">Upload description</label>
            <input id="broker-media-alt" value={uploadAltText} onChange={(event) => setUploadAltText(event.target.value)} maxLength={300} placeholder="Describe the image or floor plan" />
            <label htmlFor="broker-media-upload">Upload image or PDF floor plan (max 8 MiB)</label>
            <input id="broker-media-upload" type="file" accept="image/jpeg,image/png,image/webp,application/pdf" disabled={uploadingMedia || !uploadAltText.trim()} onChange={handleMediaUpload} />
            {uploadingMedia && <span role="status">Uploading and scanning…</span>}
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', padding: '12px', background: '#1a1d24', borderRadius: '6px' }}>
          {requiresCommissionTerms && (
            <div>
              <label htmlFor="broker-owner-name" style={{ display: 'block', fontSize: '0.85rem', color: '#fff', marginBottom: '6px' }}>
                Property owner's legal name
              </label>
              <input
                id="broker-owner-name"
                maxLength={200}
                required
                value={form.owner_name}
                onChange={(event) => setForm({ ...form, owner_name: event.target.value })}
              />
              <label htmlFor="broker-owner-mandate" style={{ display: 'block', fontSize: '0.85rem', color: '#fff', margin: '10px 0 6px' }}>
                Owner mandate or consent reference
              </label>
              <input
                id="broker-owner-mandate"
                maxLength={200}
                required
                value={form.owner_mandate_reference}
                onChange={(event) => setForm({ ...form, owner_mandate_reference: event.target.value })}
                placeholder="Reference or identifier for the signed mandate"
              />
              <label htmlFor="broker-commission-terms" style={{ display: 'block', fontSize: '0.85rem', color: '#fff', marginBottom: '6px' }}>
                Commission agreement with the owner
              </label>
              <textarea
                id="broker-commission-terms"
                maxLength={2000}
                required
                rows={3}
                value={form.commission_terms}
                onChange={(event) => setForm({ ...form, commission_terms: event.target.value })}
                placeholder="Record the agreed commission terms. Luxline does not calculate or pay commissions."
                aria-describedby="broker-commission-note"
              />
              <small id="broker-commission-note">Record the agreed commission terms. Luxline does not calculate or pay commissions.</small>
            </div>
          )}
          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.85rem', color: '#fff', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={form.owner_consent}
              onChange={(e) => setForm({ ...form, owner_consent: e.target.checked })}
            />
            I confirm direct representation consent or mandate from the legal asset owner.
          </label>
          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.85rem', color: '#fff', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={form.urgent_flag}
              onChange={(e) => setForm({ ...form, urgent_flag: e.target.checked })}
            />
            Mark as Urgent / Motivated Seller
          </label>
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '12px' }}>
          <button
            type="button"
            onClick={onDone}
            style={{ padding: '10px 20px', background: '#1a1d24', border: '1px solid #262930', color: '#fff', borderRadius: '6px', cursor: 'pointer' }}
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={saving || categoriesLoading || !categories.length}
            className="broker-btn-gold"
            style={{ margin: 0, padding: '10px 24px' }}
          >
            {saving ? 'Creating...' : '💾 Save Draft Listing'}
          </button>
        </div>
      </form>
      {listing && revisions.length > 0 && (
        <details className="broker-card">
          <summary>Revision history ({revisions.length})</summary>
          {revisions.map((revision) => (
            <div key={revision.id} style={{ padding: '10px 0', borderBottom: '1px solid #262930' }}>
              Version {revision.version} · {new Date(revision.created_at).toLocaleString()}
              <p>{revision.snapshot.title} — {revision.snapshot.currency} {revision.snapshot.price}</p>
            </div>
          ))}
        </details>
      )}
    </div>
  );
}

export default withBrokerTranslations(ListingEditorScreen);
