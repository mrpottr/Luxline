import { useCallback, useEffect, useState } from 'react';
import { withBrokerTranslations } from '../i18n/withBrokerTranslations';
import { responseList } from './responseUtils.mjs';

function ReviewsScreen({ token, apiBase }) {
  const [reviews, setReviews] = useState([]);
  const [badges, setBadges] = useState([]);
  const [replies, setReplies] = useState({});
  const [appeals, setAppeals] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [status, setStatus] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const [reviewResponse, badgeResponse] = await Promise.all([
        fetch(`${apiBase}/reviews?limit=50&offset=0`, { headers }),
        fetch(`${apiBase}/badges`, { headers })
      ]);
      const [reviewBody, badgeBody] = await Promise.all([
        reviewResponse.json().catch(() => ({})), badgeResponse.json().catch(() => ({}))
      ]);
      if (!reviewResponse.ok || !badgeResponse.ok) {
        throw new Error(reviewBody.detail || badgeBody.detail || 'Unable to load trust information.');
      }
      setReviews(responseList(reviewBody, 'reviews'));
      setBadges(responseList(badgeBody, 'badges'));
    } catch (loadError) {
      setError(loadError.message || 'Trust services are offline. Retry when connected.');
    } finally {
      setLoading(false);
    }
  }, [apiBase, token]);

  useEffect(() => { load(); }, [load]);

  async function mutate(review, action, body) {
    setError('');
    setStatus('');
    try {
      const response = await fetch(`${apiBase}/reviews/${review.id}/${action}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify(body)
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(result.detail || 'Unable to update this review.');
      setStatus(action === 'reply' ? 'Reply saved.' : 'Appeal sent to platform review.');
      await load();
    } catch (actionError) {
      setError(actionError.message || 'Trust service is offline.');
    }
  }

  return (
    <section className="broker-card" aria-labelledby="broker-reviews-title">
      <header className="broker-card-header">
        <span className="broker-badge-pill">Trust</span>
        <h1 id="broker-reviews-title" className="broker-card-title">Reviews and badges</h1>
        <p className="broker-card-subtitle">Review status and badge criteria are visible so your team can understand each result.</p>
      </header>
      {error && <p className="broker-form-error" role="alert">{error}</p>}
      {status && <p className="broker-form-success" role="status">{status}</p>}
      {loading ? <p role="status">Loading reviews and badge results…</p> : (
        <>
          <h2 className="broker-section-heading">Badge criteria</h2>
          <div className="broker-badge-grid">{badges.map((badge) => <article className="broker-badge-card" key={`${badge.subject_type}-${badge.subject_id}-${badge.badge_code}`}>
            <strong>{badge.badge_code.replaceAll('_', ' ')} · {badge.awarded ? 'Awarded' : 'Not yet awarded'}</strong>
            <p>{badge.explanation}</p><small>Rule version {badge.rule_version}</small>
          </article>)}</div>
          {!badges.length && <p>No badge evaluations are available.</p>}
          <h2 className="broker-section-heading">Buyer reviews</h2>
          {!reviews.length ? <p>No reviews have been submitted.</p> : <div className="broker-review-list">{reviews.map((review) => <article className="broker-review-card" key={review.id}>
            <div className="broker-review-heading"><strong>{'★'.repeat(review.rating)}{'☆'.repeat(5 - review.rating)}</strong><span>Listing #{review.listing_id}</span><span>{review.status}</span></div>
            <p>{review.body}</p>
            {review.broker_reply && <blockquote>{review.broker_reply}</blockquote>}
            {review.status === 'published' && <form className="broker-trust-form" onSubmit={(event) => { event.preventDefault(); mutate(review, 'reply', { body: replies[review.id] || '' }); }}>
              <label htmlFor={`review-reply-${review.id}`}>Public reply</label>
              <textarea id={`review-reply-${review.id}`} maxLength="2000" required value={replies[review.id] || ''} onChange={(event) => setReplies((current) => ({ ...current, [review.id]: event.target.value }))} />
              <button className="broker-btn-secondary" type="submit">Save reply</button>
            </form>}
            {review.status === 'published' && review.appeal_state === 'none' && <form className="broker-trust-form" onSubmit={(event) => { event.preventDefault(); mutate(review, 'appeal', { reason: appeals[review.id] || '' }); }}>
              <label htmlFor={`review-appeal-${review.id}`}>Appeal reason</label>
              <textarea id={`review-appeal-${review.id}`} maxLength="1000" required value={appeals[review.id] || ''} onChange={(event) => setAppeals((current) => ({ ...current, [review.id]: event.target.value }))} />
              <button className="broker-btn-secondary" type="submit">Request review</button>
            </form>}
            {review.appeal_state !== 'none' && <p>Appeal status: {review.appeal_state}</p>}
          </article>)}</div>}
        </>
      )}
    </section>
  );
}

export default withBrokerTranslations(ReviewsScreen);
