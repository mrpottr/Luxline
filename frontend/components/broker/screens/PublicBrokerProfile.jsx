import React, { useEffect, useState } from 'react';
import { withBrokerTranslations } from '../i18n/withBrokerTranslations';

function PublicBrokerProfile({ orgId, apiBase }) {
  const [broker, setBroker] = useState(null);
  const [reviews, setReviews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        const res = await fetch(`${apiBase}/public/brokers/${orgId}`);
        if (!res.ok) throw new Error('Broker not found');
        const data = await res.json();
        setBroker(data);
        try {
          const reviewResponse = await fetch(`${apiBase}/public/brokers/${orgId}/reviews?limit=20&offset=0`);
          if (reviewResponse.ok) setReviews(await reviewResponse.json());
        } catch {
          // Reviews are supplementary; a review-service outage must not hide the public profile.
        }
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    if (orgId) load();
  }, [orgId, apiBase]);

  if (loading) return <div style={{ color: '#9da3af', padding: '32px' }}>Loading broker profile...</div>;
  if (error || !broker) {
    return (
      <div style={{ color: '#ef4444', padding: '32px' }}>
        <h3>Broker Unavailable</h3>
        <p>This broker profile is either unverified or not currently active.</p>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: '960px', margin: '0 auto', color: '#f3f4f6' }}>
      {/* Banner */}
      <div
        style={{
          height: '240px',
          borderRadius: '8px 8px 0 0',
          background: broker.banner_url ? `url(${broker.banner_url}) center/cover` : 'linear-gradient(135deg, #121418, #1a1d24)',
          position: 'relative',
          border: '1px solid #262930',
        }}
      >
        {broker.logo_url && (
          <img
            src={broker.logo_url}
            alt={broker.company_name}
            style={{
              position: 'absolute',
              bottom: '-32px',
              left: '32px',
              width: '80px',
              height: '80px',
              borderRadius: '8px',
              border: '2px solid #d4af37',
              backgroundColor: '#121418',
              objectFit: 'cover',
            }}
          />
        )}
      </div>

      <div style={{ padding: '48px 32px 32px', backgroundColor: '#121418', border: '1px solid #262930', borderTop: 'none', borderRadius: '0 0 8px 8px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <h1 style={{ fontSize: '1.75rem', fontWeight: 700, margin: 0 }}>{broker.company_name}</h1>
              {broker.is_verified && (
                <span className="broker-badge-pill">✓ Verified Broker</span>
              )}
            </div>
            <p style={{ color: '#9da3af', margin: '6px 0 0' }}>
              📍 {broker.city}, {broker.country}
            </p>
          </div>

          {broker.whatsapp_number && (
            <a
              href={`https://wa.me/${broker.whatsapp_number.replace(/\D/g, '')}`}
              target="_blank"
              rel="noreferrer"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
                padding: '10px 18px',
                borderRadius: '6px',
                backgroundColor: '#25D366',
                color: '#fff',
                textDecoration: 'none',
                fontWeight: 600,
                fontSize: '0.88rem',
              }}
            >
              💬 WhatsApp Concierge
            </a>
          )}
        </div>

        {broker.about && (
          <div style={{ marginTop: '24px', borderTop: '1px solid #262930', paddingTop: '16px' }}>
            <h3 style={{ fontSize: '1rem', color: '#d4af37', marginBottom: '8px' }}>About the Brokerage</h3>
            <p style={{ color: '#cbd5e1', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>{broker.about}</p>
          </div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '20px', marginTop: '24px', borderTop: '1px solid #262930', paddingTop: '16px' }}>
          {broker.service_areas?.length > 0 && (
            <div>
              <h4 style={{ fontSize: '0.82rem', color: '#9da3af', textTransform: 'uppercase', marginBottom: '6px' }}>Service Areas</h4>
              <p style={{ margin: 0, color: '#f3f4f6' }}>{broker.service_areas.join(', ')}</p>
            </div>
          )}

          {broker.languages?.length > 0 && (
            <div>
              <h4 style={{ fontSize: '0.82rem', color: '#9da3af', textTransform: 'uppercase', marginBottom: '6px' }}>Languages Spoken</h4>
              <p style={{ margin: 0, color: '#f3f4f6' }}>{broker.languages.map((l) => l.toUpperCase()).join(', ')}</p>
            </div>
          )}

          {broker.website && (
            <div>
              <h4 style={{ fontSize: '0.82rem', color: '#9da3af', textTransform: 'uppercase', marginBottom: '6px' }}>Website</h4>
              <a href={broker.website} target="_blank" rel="noreferrer" style={{ color: '#d4af37', textDecoration: 'none' }}>
                {broker.website} ↗
              </a>
            </div>
          )}
        </div>
      </div>
      <section className="broker-card" aria-labelledby="public-broker-reviews-title" style={{ marginTop: '20px' }}>
        <h2 id="public-broker-reviews-title" className="broker-card-title">Buyer reviews</h2>
        {!reviews.length ? <p>No public reviews yet.</p> : <div className="broker-review-list">{reviews.map((review) => <article className="broker-review-card" key={review.id}>
          <strong className="broker-public-review-rating">{'★'.repeat(review.rating)}{'☆'.repeat(5 - review.rating)}</strong>
          <p>{review.body}</p>
          {review.broker_reply && <blockquote>{review.broker_reply}</blockquote>}
          <small>{new Date(review.created_at).toLocaleDateString()}</small>
        </article>)}</div>}
      </section>
    </div>
  );
}

export default withBrokerTranslations(PublicBrokerProfile);
