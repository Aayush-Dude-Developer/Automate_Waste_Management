import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AlertTriangle, Check, ChevronDown, ChevronRight, RefreshCw, Search } from 'lucide-react';
import { Link } from 'react-router-dom';
import { apiRequest, invalidateApiCache, type PurchaseRecommendation, type PurchaseRecommendationDashboard, type PurchaseRecommendationStatus } from '../lib/api';

const inputClass = 'rounded-md border border-slate-300 bg-white px-3 py-2 text-sm';
const today = new Date().toISOString().slice(0, 10);
const statuses: PurchaseRecommendationStatus[] = ['needs_review', 'approved', 'ordered', 'received', 'no_action'];

function statusLabel(status: PurchaseRecommendationStatus) {
  return ({
    needs_review: 'Needs Review',
    approved: 'Approved',
    ordered: 'Ordered',
    received: 'Received',
    no_action: 'No Action',
  })[status];
}

function dateLabel(value: string | null) {
  return value ? new Date(`${value}T00:00:00`).toLocaleDateString() : '—';
}

function formatQty(value: number, unit: string) {
  return `${value.toLocaleString(undefined, { maximumFractionDigits: 3 })} ${unit}`;
}

export default function PurchaseRecommendationsView() {
  const [period, setPeriod] = useState(7);
  const [dashboard, setDashboard] = useState<PurchaseRecommendationDashboard | null>(null);
  const hasDashboard = useRef(false);
  const [search, setSearch] = useState('');
  const [urgency, setUrgency] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [expandedId, setExpandedId] = useState('');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busyId, setBusyId] = useState('');
  const [orderReference, setOrderReference] = useState('');
  const [deliveryDate, setDeliveryDate] = useState('');
  const [purchaseLineId, setPurchaseLineId] = useState('');
  const [stale, setStale] = useState(false);

  const load = useCallback(async (force = false) => {
    if (force) invalidateApiCache();
    setError('');
    if (force) setRefreshing(true);
    else setLoading(true);
    try {
      const data = await apiRequest<PurchaseRecommendationDashboard>(
        `/api/purchase-recommendations?forecast_period_days=${period}`,
        force ? { cache: 'no-store' } : {},
      );
      setDashboard(data);
      hasDashboard.current = true;
      setStale(false);
      setNotice('');
    } catch (cause) {
      setStale(hasDashboard.current);
      setError(cause instanceof Error ? cause.message : 'Could not load purchase recommendations.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [period]);

  useEffect(() => { void Promise.resolve().then(() => load()); }, [load]);

  const filtered = useMemo(() => (dashboard?.recommendations ?? []).filter((recommendation) => (
    recommendation.ingredient_name.toLowerCase().includes(search.toLowerCase())
    && (urgency === 'all' || recommendation.priority === urgency)
    && (statusFilter === 'all' || recommendation.status === statusFilter)
  )), [dashboard, search, statusFilter, urgency]);

  const mutateRecommendation = async (
    recommendation: PurchaseRecommendation,
    status: Exclude<PurchaseRecommendationStatus, 'needs_review' | 'no_action'>,
  ) => {
    setBusyId(recommendation.recommendation_id);
    setError('');
    setNotice('');
    const payload: {
      status: string;
      ingredient_id: string;
      forecast_start_date: string;
      forecast_period_days: number;
      order_reference?: string;
      expected_delivery_date?: string;
      purchase_line_id?: string;
    } = {
      status,
      ingredient_id: recommendation.ingredient_id,
      forecast_start_date: recommendation.forecast_start_date,
      forecast_period_days: recommendation.forecast_period_days,
    };
    if (status === 'ordered') {
      if (!orderReference.trim() || !deliveryDate) {
        setError('Enter the supplier order reference and expected delivery date before marking Ordered.');
        setBusyId('');
        return;
      }
      payload.order_reference = orderReference.trim();
      payload.expected_delivery_date = deliveryDate;
    }
    if (status === 'received') {
      if (!purchaseLineId.trim()) {
        setError('Enter the verified purchase line ID before marking Received.');
        setBusyId('');
        return;
      }
      payload.purchase_line_id = purchaseLineId.trim();
    }
    try {
      await apiRequest(`/api/purchase-recommendations/${encodeURIComponent(recommendation.recommendation_id)}/status`, {
        method: 'PATCH',
        body: JSON.stringify(payload),
      });
      invalidateApiCache();
      setNotice(`Recommendation for ${recommendation.ingredient_name} updated to ${statusLabel(status)}. No order was sent to the supplier.`);
      setOrderReference('');
      setDeliveryDate('');
      setPurchaseLineId('');
      await load(true);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not update recommendation status.');
    } finally {
      setBusyId('');
    }
  };

  const stockoutInForecast = (recommendation: PurchaseRecommendation) =>
    recommendation.projected_stockout_date !== null
    && recommendation.projected_stockout_date >= (dashboard?.forecast_start_date ?? today);

  if (loading && !dashboard) return <div className="p-8 text-slate-500">Loading purchase recommendations…</div>;

  return <div className="p-6 md:p-8">
    <div className="mb-6 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
      <div>
        <p className="text-sm font-medium text-emerald-700">Demand-led replenishment</p>
        <h1 className="mt-1 text-2xl font-bold text-slate-800">Purchase Recommendations</h1>
        <p className="mt-1 text-sm text-slate-500">Built from recorded sales, active recipes, ingredient yields and current stock.</p>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <label className="text-sm text-slate-600" htmlFor="forecast-period">Forecast period</label>
        <select id="forecast-period" className={inputClass} value={period} onChange={(event) => setPeriod(Number(event.target.value))}>
          {[7, 14, 21, 28].map((days) => <option key={days} value={days}>Next {days} days</option>)}
        </select>
        <button onClick={() => void load(true)} disabled={refreshing} className="inline-flex items-center gap-2 rounded-md bg-emerald-700 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60">
          <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />Refresh Forecast
        </button>
      </div>
    </div>

    {error && <div role="alert" className="mb-4 rounded-md border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">{error}</div>}
    {notice && <div role="status" className="mb-4 rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">{notice}</div>}
    {stale && dashboard && <div role="status" className="mb-4 rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">Could not refresh. Showing the last successful forecast generated {new Date(dashboard.generated_at).toLocaleString()}.</div>}
    {dashboard?.data_warnings.map((warning) => <div key={warning} className="mb-3 flex gap-2 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900"><AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />{warning}</div>)}

    {dashboard && <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
      <SummaryCard label="Ingredients requiring replenishment" value={dashboard.ingredients_requiring_replenishment} tone="text-amber-700" />
      <SummaryCard label="Upcoming stockout risks" value={dashboard.upcoming_stockout_risks} tone="text-rose-700" />
      <SummaryCard label="Awaiting approval" value={dashboard.recommendations_awaiting_approval} tone="text-indigo-700" />
    </div>}

    <section className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
      <div className="flex flex-col gap-3 border-b border-slate-200 p-4 lg:flex-row lg:items-center">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input aria-label="Search ingredients" className={`${inputClass} w-full pl-9`} placeholder="Search ingredients…" value={search} onChange={(event) => setSearch(event.target.value)} />
        </div>
        <select aria-label="Filter by urgency" className={inputClass} value={urgency} onChange={(event) => setUrgency(event.target.value)}>
          <option value="all">All urgency</option><option value="critical">Critical</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option>
        </select>
        <select aria-label="Filter by status" className={inputClass} value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
          <option value="all">All statuses</option>{statuses.map((status) => <option key={status} value={status}>{statusLabel(status)}</option>)}
        </select>
      </div>
      {loading && dashboard && <p className="px-4 py-2 text-xs text-slate-500">Refreshing forecast…</p>}
      {!filtered.length ? <div className="p-10 text-center">
        <h2 className="font-semibold text-slate-800">{dashboard?.recommendations.length ? 'No recommendations match these filters.' : 'No replenishment recommendations yet.'}</h2>
        <p className="mt-2 text-sm text-slate-500">Recommendations use recorded sales and recipes; no manual demand estimate is entered.</p>
      </div> : <div className="overflow-x-auto">
        <table className="w-full min-w-[1500px] text-left text-xs text-slate-600">
          <thead className="bg-slate-50 text-slate-700"><tr>
            <th className="px-3 py-3">Ingredient</th><th className="px-3 py-3">Current usable stock</th><th className="px-3 py-3">Forecast daily consumption</th><th className="px-3 py-3">Reorder threshold</th><th className="px-3 py-3">Safety stock</th><th className="px-3 py-3">Lead time</th><th className="px-3 py-3">Projected stockout</th><th className="px-3 py-3">Recommended order date</th><th className="px-3 py-3">Recommended quantity</th><th className="px-3 py-3">Estimated cost</th><th className="px-3 py-3">Priority / status</th><th className="px-3 py-3">Actions</th>
          </tr></thead>
          <tbody className="divide-y divide-slate-100">{filtered.map((recommendation) => <RecommendationRow
            key={recommendation.recommendation_id}
            recommendation={recommendation}
            expanded={expandedId === recommendation.recommendation_id}
            onToggle={() => setExpandedId((current) => current === recommendation.recommendation_id ? '' : recommendation.recommendation_id)}
            onAction={mutateRecommendation}
            busy={busyId === recommendation.recommendation_id}
            isStockout={stockoutInForecast(recommendation)}
            orderReference={orderReference}
            onOrderReferenceChange={setOrderReference}
            deliveryDate={deliveryDate}
            onDeliveryDateChange={setDeliveryDate}
            purchaseLineId={purchaseLineId}
            onPurchaseLineIdChange={setPurchaseLineId}
          />)}</tbody>
        </table>
      </div>}
    </section>
    <p className="mt-3 text-xs text-slate-500">Forecast quantities and dates are estimates; stock and historical sales are recorded values. Recommendations never send purchase orders automatically.</p>
  </div>;
}

function SummaryCard({ label, value, tone }: { label: string; value: number; tone: string }) {
  return <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
    <p className="text-sm text-slate-500">{label}</p><p className={`mt-2 text-3xl font-bold ${tone}`}>{value}</p>
  </div>;
}

function RecommendationRow({
  recommendation, expanded, onToggle, onAction, busy, isStockout,
  orderReference, onOrderReferenceChange, deliveryDate, onDeliveryDateChange,
  purchaseLineId, onPurchaseLineIdChange,
}: {
  recommendation: PurchaseRecommendation;
  expanded: boolean;
  onToggle: () => void;
  onAction: (recommendation: PurchaseRecommendation, status: Exclude<PurchaseRecommendationStatus, 'needs_review' | 'no_action'>) => Promise<void>;
  busy: boolean;
  isStockout: boolean;
  orderReference: string;
  onOrderReferenceChange: (value: string) => void;
  deliveryDate: string;
  onDeliveryDateChange: (value: string) => void;
  purchaseLineId: string;
  onPurchaseLineIdChange: (value: string) => void;
}) {
  const dateIsOverdue = Boolean(recommendation.recommended_order_date && recommendation.recommended_order_date <= today && recommendation.status === 'needs_review');
  const nextAction: Exclude<PurchaseRecommendationStatus, 'needs_review' | 'no_action'> | null = (
    recommendation.status === 'needs_review' ? 'approved'
      : recommendation.status === 'approved' ? 'ordered'
        : recommendation.status === 'ordered' ? 'received'
          : null
  );
  return <>
    <tr className={isStockout || dateIsOverdue ? 'bg-rose-50/60' : ''}>
      <td className="px-3 py-3"><button onClick={onToggle} className="flex items-center gap-2 text-left font-semibold text-slate-900">{expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}{recommendation.ingredient_name}</button></td>
      <td className="px-3 py-3 font-medium">{formatQty(recommendation.current_usable_stock, recommendation.stock_unit)}</td>
      <td className="px-3 py-3">{formatQty(recommendation.forecast_daily_consumption, recommendation.stock_unit)}</td>
      <td className="px-3 py-3">{formatQty(recommendation.reorder_threshold, recommendation.stock_unit)}</td>
      <td className="px-3 py-3">{formatQty(recommendation.safety_stock, recommendation.stock_unit)}</td>
      <td className="px-3 py-3">{recommendation.supplier_lead_time_days == null ? 'Missing' : `${recommendation.supplier_lead_time_days} days`}</td>
      <td className={`px-3 py-3 ${isStockout ? 'font-semibold text-rose-700' : ''}`}>{dateLabel(recommendation.projected_stockout_date)}</td>
      <td className={`px-3 py-3 ${dateIsOverdue ? 'font-semibold text-rose-700' : ''}`}>{dateLabel(recommendation.recommended_order_date)}</td>
      <td className="px-3 py-3 font-semibold">{formatQty(recommendation.recommended_purchase_quantity, recommendation.stock_unit)}</td>
      <td className="px-3 py-3">{recommendation.estimated_purchase_cost == null ? '—' : `₹${recommendation.estimated_purchase_cost.toLocaleString()}`}</td>
      <td className="px-3 py-3"><span className="block font-semibold capitalize">{recommendation.priority}</span><span>{statusLabel(recommendation.status)}</span></td>
      <td className="px-3 py-3">{nextAction && <button disabled={busy} onClick={() => void onAction(recommendation, nextAction)} className="inline-flex items-center gap-1 whitespace-nowrap rounded bg-emerald-700 px-3 py-2 font-medium text-white disabled:opacity-50">{busy ? 'Saving…' : nextAction === 'approved' ? <><Check className="h-3 w-3" />Approve</> : nextAction === 'ordered' ? 'Mark ordered' : 'Mark received'}</button>}</td>
    </tr>
    {expanded && <tr><td colSpan={12} className="bg-slate-50 px-5 py-4">
      <div className="grid gap-4 lg:grid-cols-2">
        <div><h3 className="font-semibold text-slate-800">Recommendation explanation</h3><p className="mt-2 text-sm text-slate-600">{recommendation.explanation}</p><p className="mt-2 text-xs text-slate-500">{recommendation.stock_source}</p>
          <h4 className="mt-4 text-sm font-semibold text-slate-800">Demand basis</h4>
          {!recommendation.sales_basis.length ? <p className="mt-1 text-sm text-amber-800">No linked recipe/sales data supports a demand estimate.</p> : <ul className="mt-1 space-y-1 text-sm text-slate-600">{recommendation.sales_basis.map((basis) => <li key={basis.recipe_id}>{basis.recipe_name}: {basis.forecast_portions} forecast portions × {formatQty(basis.raw_quantity_per_portion, basis.unit)} raw ingredient per portion; trend factor {basis.trend_factor}×{basis.yield_stages_applied.length ? ` (yield stage ${basis.yield_stages_applied.join(', ')})` : ''}</li>)}</ul>}
          <div className="mt-3"><h4 className="text-sm font-semibold text-slate-800">Daily ingredient forecast</h4><div className="mt-1 flex flex-wrap gap-2">{Object.entries(recommendation.demand_forecast).map(([day, quantity]) => <span key={day} className="rounded bg-white px-2 py-1 text-xs text-slate-600">{day}: {formatQty(quantity, recommendation.stock_unit)}</span>)}</div></div>
        </div>
        <div>
          <h3 className="font-semibold text-slate-800">Incoming purchase orders</h3>
          {recommendation.incoming_orders.length ? <ul className="mt-1 space-y-1 text-sm text-slate-600">{recommendation.incoming_orders.map((order) => <li key={order.recommendation_id}>{order.order_reference}: {formatQty(order.quantity, recommendation.stock_unit)} due {dateLabel(order.expected_delivery_date)}</li>)}</ul> : <p className="mt-1 text-sm text-slate-500">No confirmed incoming orders recorded.</p>}
          <h3 className="mt-4 font-semibold text-slate-800">Upcoming batch expiries</h3>
          {recommendation.expiry_batches.length ? <ul className="mt-1 space-y-1 text-sm text-slate-600">{recommendation.expiry_batches.map((batch) => <li key={`${batch.purchase_id}:${batch.batch_number}:${batch.expiry_date}`} className={batch.expired ? 'text-rose-700' : ''}>{batch.batch_number || batch.purchase_id}: received {formatQty(batch.quantity_received, batch.unit)}, remaining {formatQty(batch.remaining_usable_quantity, batch.unit)}, {batch.expired ? 'expired' : 'expires'} {dateLabel(batch.expiry_date)}</li>)}</ul> : <p className="mt-1 text-sm text-slate-500">No remaining purchase lots expire within 60 days.</p>}
          {recommendation.reliability_warnings.length > 0 && <div className="mt-4 rounded border border-amber-200 bg-amber-50 p-3"><h3 className="font-semibold text-amber-900">Data limitations</h3><ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-amber-900">{recommendation.reliability_warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul></div>}
          {recommendation.status === 'approved' && <div className="mt-4 grid gap-2 sm:grid-cols-2"><label className="text-xs font-medium text-slate-600">Supplier order reference<input value={orderReference} onChange={(event) => onOrderReferenceChange(event.target.value)} className={`${inputClass} mt-1 w-full`} /></label><label className="text-xs font-medium text-slate-600">Expected delivery date<input type="date" value={deliveryDate} onChange={(event) => onDeliveryDateChange(event.target.value)} className={`${inputClass} mt-1 w-full`} /></label></div>}
          {recommendation.status === 'ordered' && <label className="mt-4 block text-xs font-medium text-slate-600">Verified purchase line ID<input value={purchaseLineId} onChange={(event) => onPurchaseLineIdChange(event.target.value)} className={`${inputClass} mt-1 w-full`} /><span className="mt-1 block font-normal">Find this ID on the <Link to="/purchases" className="text-emerald-800 underline">Purchase Invoices</Link> page after verifying the received invoice.</span></label>}
        </div>
      </div>
    </td></tr>}
  </>;
}
