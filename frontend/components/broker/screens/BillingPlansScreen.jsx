import { useCallback, useEffect, useState } from 'react';
import { withBrokerTranslations } from '../i18n/withBrokerTranslations';

function BillingPlansScreen({ token, apiBase }) {
  const [plans, setPlans] = useState([]);
  const [subscription, setSubscription] = useState(null);
  const [wallet, setWallet] = useState({ balance: 0, ledger: [] });
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState('');
  const [error, setError] = useState('');
  const [status, setStatus] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const [planResponse, subscriptionResponse, walletResponse] = await Promise.all([
        fetch(`${apiBase}/plans?limit=100&offset=0`, { headers }),
        fetch(`${apiBase}/billing/subscription`, { headers }),
        fetch(`${apiBase}/credits?limit=50&offset=0`, { headers })
      ]);
      const [planBody, subscriptionBody, walletBody] = await Promise.all([
        planResponse.json().catch(() => ({})), subscriptionResponse.json().catch(() => ({})), walletResponse.json().catch(() => ({}))
      ]);
      if (!planResponse.ok || !subscriptionResponse.ok || !walletResponse.ok) {
        throw new Error(planBody.detail || subscriptionBody.detail || walletBody.detail || 'Unable to load billing information.');
      }
      setPlans(planBody);
      setSubscription(subscriptionBody);
      setWallet(walletBody);
    } catch (loadError) {
      setError(loadError.message || 'Billing is offline. Retry when connected.');
    } finally {
      setLoading(false);
    }
  }, [apiBase, token]);

  useEffect(() => { load(); }, [load]);

  async function runBillingAction(key, path) {
    setPending(key);
    setError('');
    setStatus('');
    try {
      const response = await fetch(path, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Idempotency-Key': crypto.randomUUID() }
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || 'Billing request failed.');
      setStatus('Request completed using the configured mock payment provider.');
      await load();
    } catch (requestError) {
      setError(requestError.message || 'Billing service is offline.');
    } finally {
      setPending('');
    }
  }

  const money = (amount, currency) => {
    const value = Number(amount);
    try { return new Intl.NumberFormat(undefined, { style: 'currency', currency }).format(value); }
    catch { return `${currency} ${amount}`; }
  };

  return (
    <section className="broker-card" aria-labelledby="broker-billing-title">
      <header className="broker-card-header">
        <span className="broker-badge-pill">Account</span>
        <h1 id="broker-billing-title" className="broker-card-title">Billing and plans</h1>
        <p className="broker-card-subtitle">Plan purchases and credit packs use the environment-selected payment adapter.</p>
      </header>
      {error && <p className="broker-form-error" role="alert">{error}</p>}
      {status && <p className="broker-form-success" role="status">{status}</p>}
      {loading ? <p role="status">Loading billing information…</p> : (
        <>
          <div className="broker-billing-summary"><article><span>Current plan</span><strong>{subscription?.plan_code || 'No active broker plan'}</strong></article><article><span>Credit balance</span><strong>{wallet.balance ?? 0}</strong></article><article><span>Renews or ends</span><strong>{subscription?.ends_at ? new Date(subscription.ends_at).toLocaleDateString() : '—'}</strong></article></div>
          <h2 className="broker-section-heading">Available plans</h2>
          {!plans.length ? <p>No plans are available. Platform administrators can configure plans after the panel is enabled.</p> : <div className="broker-plan-grid">
            {plans.map((plan) => <article className="broker-plan-card" key={plan.code}>
              <h3>{plan.name}</h3><p>{plan.description}</p><strong>{money(plan.price_amount, plan.currency)}</strong><span>per {plan.billing_period_days} days</span>
              <ul><li>{plan.listing_limit ? `${plan.listing_limit} active listings` : 'No listing limit'}</li>{Object.entries(plan.entitlements || {}).filter(([, enabled]) => enabled === true).map(([name]) => <li key={name}>{name.replaceAll('_', ' ')}</li>)}</ul>
              <button className="broker-btn-gold" type="button" disabled={Boolean(pending) || !plan.is_active} onClick={() => runBillingAction(`plan:${plan.code}`, `${apiBase}/billing/subscribe?plan_code=${encodeURIComponent(plan.code)}`)}>{pending === `plan:${plan.code}` ? 'Processing…' : subscription?.plan_code === plan.code ? 'Renew plan' : 'Choose plan'}</button>
              {plan.credit_packs?.length > 0 && <div className="broker-credit-packs"><h4>Credit packs</h4>{plan.credit_packs.map((pack) => <button className="broker-btn-secondary" type="button" key={pack.code} disabled={Boolean(pending)} onClick={() => runBillingAction(`pack:${pack.code}`, `${apiBase}/credits/purchase?plan_code=${encodeURIComponent(plan.code)}&pack_code=${encodeURIComponent(pack.code)}`)}>{pending === `pack:${pack.code}` ? 'Processing…' : `${pack.credits} credits · ${money(pack.price_amount, pack.currency)}`}</button>)}</div>}
            </article>)}
          </div>}
          <h2 className="broker-section-heading">Credit ledger</h2>
          {!wallet.ledger?.length ? <p>No credit movements recorded.</p> : <div className="broker-table-scroll"><table className="broker-analytics-table"><thead><tr><th>Date</th><th>Type</th><th>Change</th><th>Balance</th><th>Reference</th></tr></thead><tbody>{wallet.ledger.map((row) => <tr key={row.id}><td>{new Date(row.created_at).toLocaleString()}</td><td>{row.entry_type}</td><td>{row.amount}</td><td>{row.balance_after}</td><td>{row.reference || '—'}</td></tr>)}</tbody></table></div>}
        </>
      )}
    </section>
  );
}

export default withBrokerTranslations(BillingPlansScreen);
