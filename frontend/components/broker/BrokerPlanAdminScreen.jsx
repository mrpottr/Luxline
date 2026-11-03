import { useCallback, useEffect, useState } from 'react';
import { withBrokerTranslations } from './i18n/withBrokerTranslations';

const EMPTY_PLAN = {
  code: '', name: '', description: '', price_amount: '', currency: '', billing_period_days: 30,
  listing_limit: '', entitlements: '{}', credit_packs: '[]', promotion_prices: '{}', is_active: true
};

function newIdempotencyKey() {
  return globalThis.crypto?.randomUUID?.() || `broker-plan-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function BrokerPlanAdminScreen({ token }) {
  const apiBase = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1').replace('/api/v1', '/api/broker/v1');
  const [plans, setPlans] = useState([]);
  const [form, setForm] = useState(EMPTY_PLAN);
  const [editingCode, setEditingCode] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [status, setStatus] = useState('');
  const [createKey, setCreateKey] = useState(newIdempotencyKey);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const response = await fetch(`${apiBase}/admin/plans?limit=100&offset=0&sort=code`, { headers: { Authorization: `Bearer ${token}` } });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || 'Unable to load broker plans.');
      setPlans(body);
    } catch (loadError) {
      setError(loadError.message || 'Broker plan service is offline.');
    } finally {
      setLoading(false);
    }
  }, [apiBase, token]);

  useEffect(() => { load(); }, [load]);

  function beginEdit(plan) {
    setEditingCode(plan.code);
    setForm({
      code: plan.code, name: plan.name, description: plan.description || '', price_amount: plan.price_amount,
      currency: plan.currency, billing_period_days: plan.billing_period_days, listing_limit: plan.listing_limit ?? '',
      entitlements: JSON.stringify(plan.entitlements || {}, null, 2), credit_packs: JSON.stringify(plan.credit_packs || [], null, 2),
      promotion_prices: JSON.stringify(plan.promotion_prices || {}, null, 2), is_active: plan.is_active
    });
    setStatus('');
  }

  function resetForm() { setEditingCode(''); setForm(EMPTY_PLAN); }
  function setField(name, value) { setForm((current) => ({ ...current, [name]: value })); }

  async function savePlan(event) {
    event.preventDefault();
    setSaving(true);
    setError('');
    setStatus('');
    try {
      let entitlements;
      let credit_packs;
      let promotion_prices;
      try {
        entitlements = JSON.parse(form.entitlements);
        credit_packs = JSON.parse(form.credit_packs);
        promotion_prices = JSON.parse(form.promotion_prices);
      } catch {
        throw new Error('Entitlements, credit packs, and promotion prices must be valid JSON.');
      }
      const payload = {
        ...form,
        billing_period_days: Number(form.billing_period_days),
        listing_limit: form.listing_limit === '' ? null : Number(form.listing_limit),
        entitlements, credit_packs, promotion_prices
      };
      const response = await fetch(`${apiBase}/admin/plans${editingCode ? `/${encodeURIComponent(editingCode)}` : ''}`, {
        method: editingCode ? 'PUT' : 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
          ...(!editingCode ? { 'Idempotency-Key': createKey } : {})
        },
        body: JSON.stringify(payload)
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || 'Unable to save broker plan.');
      setStatus(`Plan ${body.code} saved.`);
      resetForm();
      if (!editingCode) setCreateKey(newIdempotencyKey());
      await load();
    } catch (saveError) {
      setError(saveError.message || 'Broker plan service is offline.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="admin-tab-content broker-admin-plans" aria-labelledby="broker-plan-admin-title">
      <header className="section-header-flex"><div><h2 id="broker-plan-admin-title">Broker plans and entitlements</h2><p className="section-desc">Configure plan prices, listing limits, credit packages, and promotion prices.</p></div><button className="btn btn-primary" type="button" onClick={load} disabled={loading}>Refresh</button></header>
      {error && <p className="error" role="alert">{error}</p>}{status && <p role="status">{status}</p>}
      <form className="broker-plan-admin-form" onSubmit={savePlan}>
        <h3>{editingCode ? `Edit ${editingCode}` : 'Create a broker plan'}</h3>
        <div className="broker-plan-admin-fields">
          <label>Code<input required maxLength="50" pattern="[a-z0-9_-]+" value={form.code} disabled={Boolean(editingCode)} onChange={(event) => setField('code', event.target.value)} /></label>
          <label>Name<input required maxLength="120" value={form.name} onChange={(event) => setField('name', event.target.value)} /></label>
          <label>Description<input maxLength="2000" value={form.description} onChange={(event) => setField('description', event.target.value)} /></label>
          <label>Price amount<input required inputMode="decimal" value={form.price_amount} onChange={(event) => setField('price_amount', event.target.value)} /></label>
          <label>ISO currency<input required minLength="3" maxLength="3" pattern="[A-Z]{3}" value={form.currency} onChange={(event) => setField('currency', event.target.value.toUpperCase())} /></label>
          <label>Billing period (days)<input required type="number" min="1" value={form.billing_period_days} onChange={(event) => setField('billing_period_days', event.target.value)} /></label>
          <label>Active listing limit<input type="number" min="1" value={form.listing_limit} onChange={(event) => setField('listing_limit', event.target.value)} placeholder="No limit" /></label>
          <label className="broker-admin-checkbox"><input type="checkbox" checked={form.is_active} onChange={(event) => setField('is_active', event.target.checked)} /> Available to brokers</label>
        </div>
        <label>Entitlements JSON<textarea required rows="5" value={form.entitlements} onChange={(event) => setField('entitlements', event.target.value)} /></label>
        <label>Credit packs JSON<textarea required rows="5" value={form.credit_packs} onChange={(event) => setField('credit_packs', event.target.value)} /></label>
        <label>Promotion prices JSON<textarea required rows="5" value={form.promotion_prices} onChange={(event) => setField('promotion_prices', event.target.value)} /></label>
        <div className="broker-admin-form-actions"><button className="btn btn-primary" type="submit" disabled={saving}>{saving ? 'Saving…' : editingCode ? 'Save changes' : 'Create plan'}</button>{editingCode && <button className="link-btn" type="button" onClick={resetForm}>Cancel edit</button>}</div>
      </form>
      <h3>Configured plans</h3>
      {loading ? <p role="status">Loading plans…</p> : !plans.length ? <p>No broker plans configured.</p> : <div className="metrics-table"><table><thead><tr><th>Code</th><th>Name</th><th>Price</th><th>Period</th><th>Listing limit</th><th>Status</th><th /></tr></thead><tbody>{plans.map((plan) => <tr key={plan.code}><td><code>{plan.code}</code></td><td>{plan.name}</td><td>{plan.currency} {plan.price_amount}</td><td>{plan.billing_period_days} days</td><td>{plan.listing_limit ?? 'Unlimited'}</td><td>{plan.is_active ? 'Active' : 'Inactive'}</td><td><button className="link-btn" type="button" onClick={() => beginEdit(plan)}>Edit</button></td></tr>)}</tbody></table></div>}
    </section>
  );
}

export default withBrokerTranslations(BrokerPlanAdminScreen);
