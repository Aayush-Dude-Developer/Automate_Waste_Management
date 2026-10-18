import { useCallback, useEffect, useState } from 'react';
import { apiRequest, type InventoryItem, type MonthlyStockBalance, type TheoreticalConsumption } from '../lib/api';

const currentMonth = new Date().toISOString().slice(0, 7);
const inputClass = 'w-28 rounded border border-slate-300 px-2 py-1.5 text-sm';

export default function MonthlyStockView() {
  const [month, setMonth] = useState(currentMonth);
  const [items, setItems] = useState<InventoryItem[]>([]);
  const [balances, setBalances] = useState<MonthlyStockBalance[]>([]);
  const [theoretical, setTheoretical] = useState<TheoreticalConsumption[]>([]);
  const [counts, setCounts] = useState<Record<string, { actual: string; verifier: string }>>({});
  const [busyId, setBusyId] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const refresh = useCallback(async () => {
    try {
      const [inventory, monthly, consumption] = await Promise.all([
        apiRequest<InventoryItem[]>('/api/inventory/items'),
        apiRequest<MonthlyStockBalance[]>(`/api/stock-balances/${month}`),
        apiRequest<TheoreticalConsumption[]>(`/api/theoretical-consumption/${month}`),
      ]);
      setItems(inventory);
      setBalances(monthly);
      setTheoretical(consumption);
      setError('');
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not load monthly stock balances.');
    }
  }, [month]);

  useEffect(() => { void Promise.resolve().then(refresh); }, [refresh]);

  const saveStocktake = async (ingredientId: string) => {
    const count = counts[ingredientId];
    if (!count?.actual || Number(count.actual) < 0 || !count.verifier.trim()) {
      setError('Enter a non-negative actual closing stock and the verifier name.');
      return;
    }
    setBusyId(ingredientId);
    setError('');
    setNotice('');
    try {
      await apiRequest(`/api/stock-balances/${month}/${encodeURIComponent(ingredientId)}/stocktake`, {
        method: 'POST',
        body: JSON.stringify({ actual_closing_stock: Number(count.actual), verified_by: count.verifier }),
      });
      setNotice('Physical stock count verified. Calculated closing stock remains unchanged.');
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not save physical stock count.');
    } finally {
      setBusyId('');
    }
  };

  const setCount = (ingredientId: string, key: 'actual' | 'verifier', value: string) => {
    setCounts((current) => {
      const previous = current[ingredientId] ?? { actual: '', verifier: '' };
      return { ...current, [ingredientId]: { ...previous, [key]: value } };
    });
  };

  const itemById = new Map(items.map((item) => [item.ingredient_id ?? item.id, item]));
  return <div className="p-8">
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div><h1 className="text-2xl font-bold text-slate-800">Monthly Stock Balance</h1><p className="mt-1 text-sm text-slate-500">Calculated movement totals and independently verified physical counts.</p></div>
      <label className="text-sm font-medium text-slate-600">Month<input type="month" value={month} onChange={(e) => setMonth(e.target.value)} className="ml-2 rounded-md border border-slate-300 px-3 py-2" /></label>
    </div>
    {error && <div role="alert" className="mb-4 rounded-md border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">{error}</div>}
    {notice && <div role="status" className="mb-4 rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">{notice}</div>}
    <section className="mb-8 overflow-x-auto rounded-lg border border-slate-200 bg-white">
      <table className="w-full min-w-[1550px] text-left text-sm text-slate-600">
        <thead className="border-b bg-slate-50 text-slate-700"><tr>
          <th className="px-4 py-3">Ingredient</th><th className="px-4 py-3">Opening Stock</th><th className="px-4 py-3">Total Purchased Stock</th><th className="px-4 py-3">Total Recipe Consumption</th><th className="px-4 py-3">Total Staff Consumption</th><th className="px-4 py-3">Total Wasted Stock</th><th className="px-4 py-3">Other Stock Inflows</th><th className="px-4 py-3">Other Stock Outflows</th><th className="px-4 py-3">Calculated Closing Stock</th><th className="px-4 py-3">Actual Closing Stock</th><th className="px-4 py-3">Stock Variance</th><th className="px-4 py-3">Physical count</th>
        </tr></thead>
        <tbody className="divide-y divide-slate-200">{balances.length ? balances.map((balance) => {
          const item = itemById.get(balance.ingredient_id);
          const count = counts[balance.ingredient_id] ?? { actual: '', verifier: '' };
          const unit = item?.input_unit ?? item?.base_unit ?? '';
          return <tr key={balance.ingredient_id} className="align-top">
            <td className="px-4 py-4 font-medium text-slate-900">{item?.item_name ?? balance.ingredient_id}<div className="text-xs text-slate-500">{unit}{balance.provisional ? ' · provisional' : ''}</div></td>
            <td className="px-4 py-4">{balance.opening_stock} {unit}</td><td className="px-4 py-4">{balance.total_purchased_stock} {unit}</td><td className="px-4 py-4">{balance.total_recipe_consumption} {unit}</td><td className="px-4 py-4">{balance.total_staff_consumption} {unit}</td><td className="px-4 py-4">{balance.total_wasted_stock} {unit}</td><td className="px-4 py-4">{balance.other_stock_inflows} {unit}</td><td className="px-4 py-4">{balance.other_stock_outflows} {unit}</td>
            <td className="px-4 py-4 font-semibold text-slate-900">{balance.calculated_closing_stock} {unit}</td>
            <td className="px-4 py-4">{balance.actual_closing_stock === null ? 'Not counted' : `${balance.actual_closing_stock} ${unit}`}</td>
            <td className="px-4 py-4">{balance.stock_variance === null ? '—' : `${balance.stock_variance} ${unit}`}</td>
            <td className="space-y-2 px-4 py-3">
              <input aria-label={`Actual closing stock for ${item?.item_name ?? balance.ingredient_id}`} type="number" min="0" step="any" placeholder={`Count (${unit})`} value={count.actual} onChange={(e) => setCount(balance.ingredient_id, 'actual', e.target.value)} className={inputClass} />
              <input aria-label={`Count verified by for ${item?.item_name ?? balance.ingredient_id}`} placeholder="Verified by" value={count.verifier} onChange={(e) => setCount(balance.ingredient_id, 'verifier', e.target.value)} className={`${inputClass} w-32`} />
              <button disabled={busyId === balance.ingredient_id} onClick={() => void saveStocktake(balance.ingredient_id)} className="rounded bg-slate-800 px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50">{busyId === balance.ingredient_id ? 'Saving…' : 'Verify count'}</button>
            </td>
          </tr>;
        }) : <tr><td colSpan={12} className="p-8 text-center">No inventory items are available for this month.</td></tr>}</tbody>
      </table>
    </section>
    <section className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
      <div className="border-b p-4"><h2 className="font-semibold text-slate-800">Monthly Theoretical Ingredient Consumption</h2><p className="mt-1 text-xs text-slate-500">Computed from net menu portions sold and recipe yields; this is distinct from stock movements.</p></div>
      <table className="w-full text-left text-sm text-slate-600">
        <thead className="border-b bg-slate-50 text-slate-700"><tr><th className="px-5 py-3">Ingredient</th><th className="px-5 py-3">Month</th><th className="px-5 py-3">Theoretical raw consumption</th></tr></thead>
        <tbody className="divide-y divide-slate-200">{theoretical.length ? theoretical.map((row) => <tr key={row.ingredient_id}><td className="px-5 py-3 font-medium text-slate-900">{row.item_name}</td><td className="px-5 py-3">{row.month}</td><td className="px-5 py-3">{row.theoretical_raw_consumption} {row.unit}</td></tr>) : <tr><td colSpan={3} className="p-6 text-center">No recipe sales are recorded for this month.</td></tr>}</tbody>
      </table>
    </section>
  </div>;
}
