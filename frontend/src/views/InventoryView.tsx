import { useCallback, useEffect, useMemo, useState } from 'react';
import type { FormEvent } from 'react';
import { AlertTriangle, ArrowDownRight, ArrowUpRight, Plus, Search, Trash2 } from 'lucide-react';
import { apiRequest, type InventoryItem } from '../lib/api';

const fieldClass = 'w-full rounded-md border border-slate-300 px-3 py-2 text-sm';

export default function InventoryView() {
  const [items, setItems] = useState<InventoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [search, setSearch] = useState('');
  const [error, setError] = useState('');
  const [form, setForm] = useState({
    item_name: '', category: '', storage_location: '', base_unit: 'kg',
    unit_cost_inr: '0', reorder_threshold: '0', safety_stock: '0',
    current_quantity_in_store: '0', current_quantity_in_use: '0',
  });

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
          yield_factor: 1,
        }),
      });
      setForm({ item_name: '', category: '', storage_location: '', base_unit: 'kg', unit_cost_inr: '0', reorder_threshold: '0', safety_stock: '0', current_quantity_in_store: '0', current_quantity_in_use: '0' });
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
        <input required placeholder="Item name" className={fieldClass} value={form.item_name} onChange={(e) => updateField('item_name', e.target.value)} />
        <input required placeholder="Category" className={fieldClass} value={form.category} onChange={(e) => updateField('category', e.target.value)} />
        <input required placeholder="Storage location" className={fieldClass} value={form.storage_location} onChange={(e) => updateField('storage_location', e.target.value)} />
        <input required placeholder="Unit (e.g. kg)" className={fieldClass} value={form.base_unit} onChange={(e) => updateField('base_unit', e.target.value)} />
        <input required type="number" min="0" step="any" placeholder="Unit cost (INR)" className={fieldClass} value={form.unit_cost_inr} onChange={(e) => updateField('unit_cost_inr', e.target.value)} />
        <input required type="number" min="0" step="any" placeholder="Reorder threshold" className={fieldClass} value={form.reorder_threshold} onChange={(e) => updateField('reorder_threshold', e.target.value)} />
        <input required type="number" min="0" step="any" placeholder="Safety stock" className={fieldClass} value={form.safety_stock} onChange={(e) => updateField('safety_stock', e.target.value)} />
        <input required type="number" min="0" step="any" placeholder="Quantity in store" className={fieldClass} value={form.current_quantity_in_store} onChange={(e) => updateField('current_quantity_in_store', e.target.value)} />
        <input required type="number" min="0" step="any" placeholder="Quantity in use" className={fieldClass} value={form.current_quantity_in_use} onChange={(e) => updateField('current_quantity_in_use', e.target.value)} />
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
              <th className="px-6 py-3">Item Name</th><th className="px-6 py-3">Category</th><th className="px-6 py-3 text-right">Quantity</th><th className="px-6 py-3">Status</th><th className="px-6 py-3 text-right">Stock actions</th>
            </tr></thead>
            <tbody className="divide-y divide-slate-200">
              {loading ? <tr><td colSpan={5} className="px-6 py-8 text-center">Loading inventory…</td></tr>
                : filteredItems.length === 0 ? <tr><td colSpan={5} className="px-6 py-8 text-center">No inventory items found.</td></tr>
                  : filteredItems.map((item) => <tr key={item.id} className="hover:bg-slate-50">
                    <td className="px-6 py-4 font-medium text-slate-900">{item.item_name}</td>
                    <td className="px-6 py-4">{item.category}</td>
                    <td className="px-6 py-4 text-right font-medium">{item.total_current_quantity} {item.base_unit}</td>
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
