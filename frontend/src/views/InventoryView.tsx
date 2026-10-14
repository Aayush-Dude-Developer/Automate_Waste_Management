import { useCallback, useEffect, useMemo, useState } from 'react';
import type { FormEvent } from 'react';
import { AlertTriangle, ArrowDownRight, ArrowUpRight, Plus, Search, Trash2 } from 'lucide-react';
import { apiRequest, type InventoryItem } from '../lib/api';

const fieldClass = 'w-full rounded-md border border-slate-300 px-3 py-2 text-sm';
const fieldLabelClass = 'mb-1 block text-sm font-medium text-slate-700';

interface YieldStageInput {
  stage_name: string;
  input_stage: string;
  output_stage: string;
  input_unit: string;
  output_unit: string;
  yield_percentage: string;
}

export default function InventoryView() {
  const [items, setItems] = useState<InventoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [search, setSearch] = useState('');
  const [error, setError] = useState('');
  const [form, setForm] = useState({
    item_name: '', category: '', storage_location: '', base_unit: 'kg', output_unit: 'kg',
    unit_cost_inr: '0', reorder_threshold: '0', safety_stock: '0',
    current_quantity_in_store: '0', current_quantity_in_use: '0', supplier_id: '', lead_time_days: '0',
    minimum_order_quantity: '', pack_size: '',
    yield_percentage: '0', yield_stage: 'prepared',
  });
  const [yieldStages, setYieldStages] = useState<YieldStageInput[]>([]);

  const loadItems = useCallback(async () => {
    try {
      setItems(await apiRequest<InventoryItem[]>('/api/inventory/items'));
      setError('');
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not load inventory.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void Promise.resolve().then(loadItems); }, [loadItems]);

  const filteredItems = useMemo(() => items.filter((item) =>
    `${item.item_name} ${item.category}`.toLowerCase().includes(search.toLowerCase())), [items, search]);

  const updateField = (key: keyof typeof form, value: string) => setForm((current) => ({ ...current, [key]: value }));

  const createItem = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaving(true);
    setError('');
    try {
      await apiRequest<InventoryItem>('/api/inventory/items', {
        method: 'POST',
        body: JSON.stringify({
          ...form,
          unit_cost_inr: Number(form.unit_cost_inr),
          reorder_threshold: Number(form.reorder_threshold),
          safety_stock: Number(form.safety_stock),
          current_quantity_in_store: Number(form.current_quantity_in_store),
          current_quantity_in_use: Number(form.current_quantity_in_use),
          stock_in_store: Number(form.current_quantity_in_store),
          stock_in_use: Number(form.current_quantity_in_use),
          input_unit: form.base_unit,
          output_unit: yieldStages[yieldStages.length - 1]?.output_unit || form.output_unit,
          yield_percentage: Number(yieldStages[0]?.yield_percentage ?? form.yield_percentage),
          yield_stage: yieldStages[yieldStages.length - 1]?.output_stage || form.yield_stage,
          yield_stages: yieldStages.length
            ? yieldStages.map((stage) => ({ ...stage, yield_percentage: Number(stage.yield_percentage) }))
            : Number(form.yield_percentage) === 0
              ? []
              : [{
                  stage_name: form.yield_stage,
                  input_stage: 'raw',
                  output_stage: form.yield_stage,
                  input_unit: form.base_unit,
                  output_unit: form.output_unit,
                  yield_percentage: Number(form.yield_percentage),
                }],
          supplier_id: form.supplier_id || null,
          lead_time_days: Number(form.lead_time_days),
          minimum_order_quantity: form.minimum_order_quantity ? Number(form.minimum_order_quantity) : null,
          pack_size: form.pack_size ? Number(form.pack_size) : null,
          yield_factor: 1,
        }),
      });
      setForm({ item_name: '', category: '', storage_location: '', base_unit: 'kg', output_unit: 'kg', unit_cost_inr: '0', reorder_threshold: '0', safety_stock: '0', current_quantity_in_store: '0', current_quantity_in_use: '0', supplier_id: '', lead_time_days: '0', minimum_order_quantity: '', pack_size: '', yield_percentage: '0', yield_stage: 'prepared' });
      setYieldStages([]);
      setShowForm(false);
      setLoading(true);
      await loadItems();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not create inventory item.');
    } finally {
      setSaving(false);
    }
  };

  const recordMovement = async (item: InventoryItem, movementType: string) => {
    const input = window.prompt(`Quantity to ${movementType === 'RECEIPT_PURCHASE' ? 'receive' : movementType === 'WASTE_RECORDED' ? 'write off' : 'use'} (${item.base_unit}):`);
    if (input === null) return;
    const quantity = Number(input);
    if (!Number.isFinite(quantity) || quantity <= 0) {
      setError('Enter a quantity greater than zero.');
      return;
    }
    const delta = movementType === 'RECEIPT_PURCHASE' ? quantity : -quantity;
    try {
      await apiRequest('/api/inventory/movements', {
        method: 'POST',
        body: JSON.stringify({ item_id: item.id, movement_type: movementType, quantity_delta: delta, unit: item.base_unit }),
      });
      await loadItems();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not record stock movement.');
    }
  };

  const updateYieldStage = (index: number, key: keyof YieldStageInput, value: string) => {
    setYieldStages((current) => current.map((stage, stageIndex) =>
      stageIndex === index ? { ...stage, [key]: value } : stage));
  };

  return (
    <div className="p-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-800">Inventory Management</h1>
        <button onClick={() => setShowForm((visible) => !visible)} className="flex items-center rounded-md bg-restaurant-primary px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700">
          <Plus className="mr-2 h-4 w-4" />{showForm ? 'Close' : 'Add Item'}
        </button>
      </div>

      {error && <div role="alert" className="mb-4 rounded-md border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">{error}</div>}

      {showForm && <form onSubmit={createItem} className="mb-6 grid grid-cols-1 gap-3 rounded-lg border border-slate-200 bg-white p-5 sm:grid-cols-2 lg:grid-cols-3">
        <div><label htmlFor="inventory-item-name" className={fieldLabelClass}>Item name</label><input id="inventory-item-name" required placeholder="e.g. Tomatoes" className={fieldClass} value={form.item_name} onChange={(e) => updateField('item_name', e.target.value)} /></div>
        <div><label htmlFor="inventory-category" className={fieldLabelClass}>Category</label><input id="inventory-category" required placeholder="e.g. Produce" className={fieldClass} value={form.category} onChange={(e) => updateField('category', e.target.value)} /></div>
        <div><label htmlFor="inventory-storage-location" className={fieldLabelClass}>Storage location</label><input id="inventory-storage-location" required placeholder="e.g. Cold Store / Chiller" className={fieldClass} value={form.storage_location} onChange={(e) => updateField('storage_location', e.target.value)} /></div>
        <div><label htmlFor="inventory-base-unit" className={fieldLabelClass}>Unit</label><input id="inventory-base-unit" required placeholder="e.g. kg" className={fieldClass} value={form.base_unit} onChange={(e) => updateField('base_unit', e.target.value)} /></div>
        <div><label htmlFor="inventory-output-unit" className={fieldLabelClass}>Output unit (after preparation)</label><input id="inventory-output-unit" required placeholder="e.g. kg" className={fieldClass} value={form.output_unit} onChange={(e) => updateField('output_unit', e.target.value)} /></div>
        <div><label htmlFor="inventory-yield-percentage" className={fieldLabelClass}>Yield (%)</label><input id="inventory-yield-percentage" required type="number" min="-99.99" step="any" placeholder="Negative for loss, positive for gain" className={fieldClass} value={form.yield_percentage} onChange={(e) => updateField('yield_percentage', e.target.value)} /></div>
        <div><label htmlFor="inventory-yield-stage" className={fieldLabelClass}>Yield stage</label><input id="inventory-yield-stage" required placeholder="e.g. cleaned, cooked" className={fieldClass} value={form.yield_stage} onChange={(e) => updateField('yield_stage', e.target.value)} /></div>
        <div><label htmlFor="inventory-unit-cost" className={fieldLabelClass}>Unit cost (INR)</label><input id="inventory-unit-cost" required type="number" min="0" step="any" placeholder="e.g. 40" className={fieldClass} value={form.unit_cost_inr} onChange={(e) => updateField('unit_cost_inr', e.target.value)} /></div>
        <div><label htmlFor="inventory-reorder-threshold" className={fieldLabelClass}>Reorder threshold</label><input id="inventory-reorder-threshold" required type="number" min="0" step="any" placeholder="e.g. 5" className={fieldClass} value={form.reorder_threshold} onChange={(e) => updateField('reorder_threshold', e.target.value)} /></div>
        <div><label htmlFor="inventory-safety-stock" className={fieldLabelClass}>Safety stock</label><input id="inventory-safety-stock" required type="number" min="0" step="any" placeholder="e.g. 2" className={fieldClass} value={form.safety_stock} onChange={(e) => updateField('safety_stock', e.target.value)} /></div>
        <div><label htmlFor="inventory-quantity-in-store" className={fieldLabelClass}>Quantity in store</label><input id="inventory-quantity-in-store" required type="number" min="0" step="any" placeholder="e.g. 8" className={fieldClass} value={form.current_quantity_in_store} onChange={(e) => updateField('current_quantity_in_store', e.target.value)} /></div>
        <div><label htmlFor="inventory-quantity-in-use" className={fieldLabelClass}>Quantity in use</label><input id="inventory-quantity-in-use" required type="number" min="0" step="any" placeholder="e.g. 0" className={fieldClass} value={form.current_quantity_in_use} onChange={(e) => updateField('current_quantity_in_use', e.target.value)} /></div>
        <div><label htmlFor="inventory-supplier-id" className={fieldLabelClass}>Supplier ID</label><input id="inventory-supplier-id" placeholder="Optional supplier reference" className={fieldClass} value={form.supplier_id} onChange={(e) => updateField('supplier_id', e.target.value)} /></div>
        <div><label htmlFor="inventory-lead-time" className={fieldLabelClass}>Lead time (days)</label><input id="inventory-lead-time" required type="number" min="0" step="1" className={fieldClass} value={form.lead_time_days} onChange={(e) => updateField('lead_time_days', e.target.value)} /></div>
        <div><label htmlFor="inventory-minimum-order" className={fieldLabelClass}>Minimum order quantity (optional, {form.base_unit})</label><input id="inventory-minimum-order" type="number" min="0.001" step="any" className={fieldClass} value={form.minimum_order_quantity} onChange={(e) => updateField('minimum_order_quantity', e.target.value)} /></div>
        <div><label htmlFor="inventory-pack-size" className={fieldLabelClass}>Supplier pack size (optional, {form.base_unit})</label><input id="inventory-pack-size" type="number" min="0.001" step="any" className={fieldClass} value={form.pack_size} onChange={(e) => updateField('pack_size', e.target.value)} /></div>
        <div className="sm:col-span-2 lg:col-span-3">
          <div className="mb-2 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-800">Preparation yield stages (optional)</h2>
            <button type="button" onClick={() => setYieldStages((stages) => [...stages, {
              stage_name: '', input_stage: stages.length ? stages[stages.length - 1].output_stage : 'raw',
              output_stage: '', input_unit: form.base_unit, output_unit: form.base_unit, yield_percentage: '0',
            }])} className="text-sm font-medium text-indigo-700">Add yield stage</button>
          </div>
          {yieldStages.map((stage, index) => <div key={index} className="mb-3 grid grid-cols-1 gap-2 rounded-md border border-slate-200 p-3 sm:grid-cols-2 lg:grid-cols-6">
            <label className="text-xs font-medium text-slate-600">Stage name<input required value={stage.stage_name} onChange={(e) => updateYieldStage(index, 'stage_name', e.target.value)} className={`${fieldClass} mt-1`} placeholder="e.g. Cleaning" /></label>
            <label className="text-xs font-medium text-slate-600">Input stage<input required value={stage.input_stage} onChange={(e) => updateYieldStage(index, 'input_stage', e.target.value)} className={`${fieldClass} mt-1`} placeholder="e.g. raw" /></label>
            <label className="text-xs font-medium text-slate-600">Output stage<input required value={stage.output_stage} onChange={(e) => updateYieldStage(index, 'output_stage', e.target.value)} className={`${fieldClass} mt-1`} placeholder="e.g. cleaned" /></label>
            <label className="text-xs font-medium text-slate-600">Input unit<input required value={stage.input_unit} onChange={(e) => updateYieldStage(index, 'input_unit', e.target.value)} className={`${fieldClass} mt-1`} placeholder="kg" /></label>
            <label className="text-xs font-medium text-slate-600">Output unit<input required value={stage.output_unit} onChange={(e) => updateYieldStage(index, 'output_unit', e.target.value)} className={`${fieldClass} mt-1`} placeholder="kg" /></label>
            <label className="text-xs font-medium text-slate-600">Yield (%)<input required type="number" min="-99.99" step="any" value={stage.yield_percentage} onChange={(e) => updateYieldStage(index, 'yield_percentage', e.target.value)} className={`${fieldClass} mt-1`} /></label>
          </div>)}
        </div>
        <button disabled={saving} className="rounded-md bg-slate-800 px-4 py-2 text-sm font-medium text-white disabled:opacity-50 sm:col-span-2 lg:col-span-3">{saving ? 'Saving…' : 'Save inventory item'}</button>
      </form>}

      <div className="mb-6 rounded-lg border border-slate-200 bg-white">
        <div className="flex flex-col items-center justify-between gap-4 border-b border-slate-200 p-4 sm:flex-row">
          <div className="relative w-full sm:w-96">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
            <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search inventory…" className={`${fieldClass} pl-9`} />
          </div>
          <button onClick={() => { setLoading(true); void loadItems(); }} className="text-sm font-medium text-indigo-700">Refresh</button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-600">
            <thead className="border-b bg-slate-50 text-slate-700"><tr>
              <th className="px-6 py-3">Item Name</th><th className="px-6 py-3">Category</th><th className="px-6 py-3 text-right">Stock in store</th><th className="px-6 py-3 text-right">Stock in use</th><th className="px-6 py-3 text-right">Unit cost</th><th className="px-6 py-3">Input → output units</th><th className="px-6 py-3">Yield</th><th className="px-6 py-3">Reorder threshold</th><th className="px-6 py-3">Safety stock</th><th className="px-6 py-3">Supplier / lead time</th><th className="px-6 py-3">Status</th><th className="px-6 py-3 text-right">Stock actions</th>
            </tr></thead>
            <tbody className="divide-y divide-slate-200">
              {loading ? <tr><td colSpan={12} className="px-6 py-8 text-center">Loading inventory…</td></tr>
                : filteredItems.length === 0 ? <tr><td colSpan={12} className="px-6 py-8 text-center">No inventory items found.</td></tr>
                  : filteredItems.map((item) => <tr key={item.id} className="hover:bg-slate-50">
                    <td className="px-6 py-4 font-medium text-slate-900">{item.item_name}</td>
                    <td className="px-6 py-4">{item.category}</td>
                    <td className="px-6 py-4 text-right font-medium">{item.current_quantity_in_store} {item.base_unit}</td>
                    <td className="px-6 py-4 text-right">{item.current_quantity_in_use} {item.base_unit}</td>
                    <td className="px-6 py-4 text-right">₹{item.unit_cost_inr}/{item.base_unit}</td>
                    <td className="px-6 py-4">{item.input_unit ?? item.base_unit} → {item.output_unit ?? item.input_unit ?? item.base_unit}</td>
                    <td className="px-6 py-4">{item.yield_percentage ?? 0}% {item.yield_stage ? `at ${item.yield_stage}` : ''}{item.yield_stages?.map((stage) => ` · ${stage.stage_name}: ${stage.yield_percentage}%`)}</td>
                    <td className="px-6 py-4">{item.reorder_threshold} {item.base_unit}</td>
                    <td className="px-6 py-4">{item.safety_stock} {item.base_unit}</td>
                    <td className="px-6 py-4">{item.supplier_id || '—'}{item.lead_time_days ? ` · ${item.lead_time_days} days` : ''}</td>
                    <td className="px-6 py-4">{item.status === 'reorder_recommended' || item.total_current_quantity <= item.reorder_threshold
                      ? <span className="inline-flex items-center rounded-full bg-amber-100 px-2.5 py-0.5 text-xs text-amber-800"><AlertTriangle className="mr-1 h-3 w-3" />Reorder</span>
                      : <span className="rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs text-emerald-800">In Stock</span>}</td>
                    <td className="space-x-2 px-6 py-4 text-right">
                      <button title="Record usage" aria-label={`Record usage for ${item.item_name}`} onClick={() => void recordMovement(item, 'USAGE_SALES_RECIPE')} className="rounded p-1.5 text-slate-500 hover:text-restaurant-primary"><ArrowDownRight className="h-4 w-4" /></button>
                      <button title="Record receipt" aria-label={`Record receipt for ${item.item_name}`} onClick={() => void recordMovement(item, 'RECEIPT_PURCHASE')} className="rounded p-1.5 text-slate-500 hover:text-emerald-600"><ArrowUpRight className="h-4 w-4" /></button>
                      <button title="Record waste" aria-label={`Record waste for ${item.item_name}`} onClick={() => void recordMovement(item, 'WASTE_RECORDED')} className="rounded p-1.5 text-slate-500 hover:text-rose-600"><Trash2 className="h-4 w-4" /></button>
                    </td>
                  </tr>)}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
