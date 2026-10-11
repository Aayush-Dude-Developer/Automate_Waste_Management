import { useCallback, useEffect, useState } from 'react';
import { PackagePlus } from 'lucide-react';
import { apiRequest, type InventoryItem, type ReorderRecommendation } from '../lib/api';

interface PlanningInputs { dailyDemand: string; leadDays: string; packSize: string }

export default function SalesPurchasesView() {
  const [items, setItems] = useState<InventoryItem[]>([]);
  const [inputs, setInputs] = useState<Record<string, PlanningInputs>>({});
  const [recommendations, setRecommendations] = useState<Record<string, ReorderRecommendation>>({});
  const [busyId, setBusyId] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const loadItems = useCallback(async () => {
    try {
      const inventory = await apiRequest<InventoryItem[]>('/api/inventory/items');
      setItems(inventory);
      setInputs((existing) => {
        const next = { ...existing };
        inventory.forEach((item) => {
          next[item.id] ??= { dailyDemand: '', leadDays: '1', packSize: '1' };
        });
        return next;
      });
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not load inventory.');
    }
  }, []);

  useEffect(() => { void Promise.resolve().then(loadItems); }, [loadItems]);

  const updateInput = (itemId: string, field: keyof PlanningInputs, value: string) => {
    setInputs((current) => ({ ...current, [itemId]: { ...current[itemId], [field]: value } }));
  };

  const calculate = async (item: InventoryItem) => {
    const itemInputs = inputs[item.id];
    if (!itemInputs || !itemInputs.dailyDemand || Number(itemInputs.dailyDemand) < 0) {
      setError(`Enter a valid daily demand forecast for ${item.item_name}.`);
      return;
    }
    setBusyId(item.id);
    setError('');
    setNotice('');
    try {
      const result = await apiRequest<ReorderRecommendation>('/api/planning/replenishment', {
        method: 'POST',
        body: JSON.stringify({
          item_id: item.id,
          daily_demand_forecast: Number(itemInputs.dailyDemand),
          lead_time_days: Number(itemInputs.leadDays),
          safety_stock: item.safety_stock,
          pack_size: Number(itemInputs.packSize),
        }),
      });
      setRecommendations((current) => ({ ...current, [item.id]: { ...result, unit: item.base_unit, item_id: item.id, pack_size: Number(itemInputs.packSize) } }));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not calculate a replenishment recommendation.');
    } finally {
      setBusyId('');
    }
  };

  const recordReceipt = async (item: InventoryItem, recommendation: ReorderRecommendation) => {
    if (recommendation.recommended_purchase_quantity <= 0) {
      setNotice('The recommendation is zero; there is no stock to receive.');
      return;
    }
    setBusyId(item.id);
    setError('');
    setNotice('');
    try {
      await apiRequest('/api/inventory/movements', {
        method: 'POST',
        body: JSON.stringify({
          item_id: item.id,
          movement_type: 'RECEIPT_PURCHASE',
          quantity_delta: recommendation.recommended_purchase_quantity,
          unit: item.base_unit,
          notes: 'Stock receipt recorded from replenishment recommendation',
        }),
      });
      setNotice(`Recorded receipt of ${recommendation.recommended_purchase_quantity} ${item.base_unit} for ${item.item_name}.`);
      await loadItems();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not record received stock.');
    } finally {
      setBusyId('');
    }
  };

  return <div className="p-8">
    <div className="mb-6"><h1 className="text-2xl font-bold text-slate-800">Sales & Purchasing</h1><p className="mt-1 text-sm text-slate-500">Generate purchase guidance from live stock and your demand estimates.</p></div>
    {error && <div role="alert" className="mb-4 rounded-md border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">{error}</div>}
    {notice && <div role="status" className="mb-4 rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">{notice}</div>}
    <div className="mb-8 overflow-hidden rounded-lg border border-slate-200 bg-white">
      <div className="flex items-center border-b bg-slate-50 p-4"><PackagePlus className="mr-2 h-5 w-5 text-restaurant-secondary" /><h2 className="text-lg font-semibold text-slate-800">Replenishment Recommendations</h2></div>
      {items.length === 0 ? <p className="p-6 text-sm text-slate-500">No inventory items are available. Add items in Inventory before calculating recommendations.</p> :
        <div className="divide-y divide-slate-200">{items.map((item) => {
          const recommendation = recommendations[item.id];
          const itemInputs = inputs[item.id] ?? { dailyDemand: '', leadDays: '1', packSize: '1' };
          return <section key={item.id} className="p-6">
            <h3 className="mb-4 text-lg font-bold text-slate-900">{item.item_name} <span className="text-sm font-normal text-slate-500">({item.total_current_quantity} {item.base_unit} on hand)</span></h3>
            <div className="mb-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
              <label className="text-xs font-medium text-slate-600">Expected daily demand ({item.base_unit})<input type="number" min="0" step="any" value={itemInputs.dailyDemand} onChange={(e) => updateInput(item.id, 'dailyDemand', e.target.value)} className="mt-1 block w-full rounded border border-slate-300 px-3 py-2 text-sm" /></label>
              <label className="text-xs font-medium text-slate-600">Supplier lead time (days)<input type="number" min="0" step="1" value={itemInputs.leadDays} onChange={(e) => updateInput(item.id, 'leadDays', e.target.value)} className="mt-1 block w-full rounded border border-slate-300 px-3 py-2 text-sm" /></label>
              <label className="text-xs font-medium text-slate-600">Pack size ({item.base_unit})<input type="number" min="0.01" step="any" value={itemInputs.packSize} onChange={(e) => updateInput(item.id, 'packSize', e.target.value)} className="mt-1 block w-full rounded border border-slate-300 px-3 py-2 text-sm" /></label>
            </div>
            <button disabled={busyId === item.id} onClick={() => void calculate(item)} className="rounded-md bg-indigo-700 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">{busyId === item.id ? 'Working…' : 'Calculate recommendation'}</button>
            {recommendation && <div className="mt-4 flex flex-col justify-between gap-4 rounded-lg border border-amber-200 bg-amber-50 p-4 md:flex-row md:items-center">
              <div><p className="font-semibold text-amber-900">Recommended: {recommendation.recommended_purchase_quantity} {item.base_unit} ({recommendation.recommended_packs} packs)</p><p className="mt-1 text-sm text-amber-800">{recommendation.reasoning}</p><p className="mt-1 text-xs text-amber-700">Target: {recommendation.target_stock_level} {item.base_unit} · {recommendation.data_quality_status} data quality</p></div>
              <button disabled={busyId === item.id || recommendation.recommended_purchase_quantity <= 0} onClick={() => void recordReceipt(item, recommendation)} className="shrink-0 rounded-md bg-amber-700 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">Record received stock</button>
            </div>}
          </section>;
        })}</div>}
    </div>
  </div>;
}
