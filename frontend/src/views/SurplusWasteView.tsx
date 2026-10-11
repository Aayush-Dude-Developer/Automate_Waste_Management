import { useCallback, useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { AlertTriangle, CheckCircle, Search, Sparkles, Trash2 } from 'lucide-react';
import { apiRequest, type Investigation, type InventoryItem, type WasteRecord } from '../lib/api';

const fieldClass = 'w-full rounded-md border border-slate-300 px-3 py-2 text-sm';

export default function SurplusWasteView() {
  const [wasteLogs, setWasteLogs] = useState<WasteRecord[]>([]);
  const [items, setItems] = useState<InventoryItem[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [investigatingId, setInvestigatingId] = useState('');
  const [investigationResult, setInvestigationResult] = useState<Investigation | null>(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [form, setForm] = useState({ inventory_item_id: '', date: '', quantity: '', reason: '', checked_by: '' });

  const refresh = useCallback(async () => {
    try {
      const [logs, inventory] = await Promise.all([
        apiRequest<WasteRecord[]>('/api/waste'),
        apiRequest<InventoryItem[]>('/api/inventory/items'),
      ]);
      setWasteLogs(logs);
      setItems(inventory);
      setError('');
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not load waste records.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void Promise.resolve().then(refresh); }, [refresh]);

  const selectedItem = items.find((item) => item.id === form.inventory_item_id);
  const createWaste = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaving(true);
    setError('');
    setNotice('');
    try {
      await apiRequest<WasteRecord>('/api/waste', {
        method: 'POST',
        body: JSON.stringify({
          date: form.date,
          item_name: selectedItem?.item_name ?? '',
          inventory_item_id: form.inventory_item_id || null,
          quantity: Number(form.quantity),
          unit: selectedItem?.base_unit ?? 'kg',
          reason: form.reason,
          checked_by: form.checked_by,
        }),
      });
      setNotice('Waste record saved.');
      setForm({ inventory_item_id: '', date: '', quantity: '', reason: '', checked_by: '' });
      setShowForm(false);
      setLoading(true);
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not save waste record.');
    } finally {
      setSaving(false);
    }
  };

  const investigate = async (item: InventoryItem, serviceDate: string) => {
    setInvestigatingId(item.id);
    setError('');
    setNotice('');
    try {
      setInvestigationResult(await apiRequest<Investigation>('/api/ai/investigate-surplus', {
        method: 'POST',
        body: JSON.stringify({ target_item_id: item.id, target_item_name: item.item_name, service_date: serviceDate }),
      }));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not analyze surplus risk.');
    } finally {
      setInvestigatingId('');
    }
  };

  const approve = async (interventionId: string) => {
    if (!investigationResult) return;
    try {
      await apiRequest(`/api/ai/investigations/${encodeURIComponent(investigationResult.id)}/approve-action`, {
        method: 'POST',
        body: JSON.stringify({ selected_intervention_id: interventionId, notes: null }),
      });
      setNotice('Intervention approval recorded. The backend records approval; it does not execute the proposed action.');
      setInvestigationResult(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not record approval.');
    }
  };

  return <div className="p-8">
    <div className="mb-6 flex items-center justify-between"><h1 className="text-2xl font-bold text-slate-800">Surplus & Waste Records</h1><button onClick={() => setShowForm((value) => !value)} className="flex items-center rounded-md bg-rose-600 px-4 py-2 text-sm font-medium text-white hover:bg-rose-700"><Trash2 className="mr-2 h-4 w-4" />{showForm ? 'Close' : 'Log Waste'}</button></div>
    {error && <div role="alert" className="mb-4 rounded-md border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">{error}</div>}
    {notice && <div role="status" className="mb-4 rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">{notice}</div>}
    {showForm && <form onSubmit={createWaste} className="mb-6 grid grid-cols-1 gap-3 rounded-lg border border-slate-200 bg-white p-5 sm:grid-cols-2 lg:grid-cols-5">
      <select required value={form.inventory_item_id} onChange={(e) => setForm({ ...form, inventory_item_id: e.target.value })} className={fieldClass}><option value="">Select inventory item</option>{items.map((item) => <option key={item.id} value={item.id}>{item.item_name} ({item.base_unit})</option>)}</select>
      <input required type="date" value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} className={fieldClass} />
      <input required type="number" min="0.001" step="any" placeholder={`Quantity${selectedItem ? ` (${selectedItem.base_unit})` : ''}`} value={form.quantity} onChange={(e) => setForm({ ...form, quantity: e.target.value })} className={fieldClass} />
      <input required placeholder="Waste reason" value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })} className={fieldClass} />
      <input required placeholder="Checked by" value={form.checked_by} onChange={(e) => setForm({ ...form, checked_by: e.target.value })} className={fieldClass} />
      <button disabled={saving || !items.length} className="rounded-md bg-slate-800 px-4 py-2 text-sm font-medium text-white disabled:opacity-50 sm:col-span-2 lg:col-span-5">{saving ? 'Saving…' : 'Save waste record and deduct stock'}</button>
    </form>}

    <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
      <section className="h-fit overflow-hidden rounded-lg border border-slate-200 bg-white lg:col-span-2">
        <div className="flex items-center justify-between border-b p-4"><h2 className="text-lg font-semibold text-slate-800">Recent Waste Logs</h2><button onClick={() => void refresh()} className="text-sm font-medium text-indigo-700">Refresh</button></div>
        <div className="overflow-x-auto"><table className="w-full text-left text-sm text-slate-600">
          <thead className="border-b bg-slate-50 text-slate-700"><tr><th className="px-5 py-3">Date</th><th className="px-5 py-3">Item</th><th className="px-5 py-3">Qty</th><th className="px-5 py-3">Reason / Loss</th><th className="px-5 py-3 text-right">Analyze</th></tr></thead>
          <tbody className="divide-y divide-slate-200">{loading ? <tr><td colSpan={5} className="p-8 text-center">Loading waste records…</td></tr>
            : wasteLogs.length === 0 ? <tr><td colSpan={5} className="p-8 text-center">No waste records have been logged.</td></tr>
              : wasteLogs.map((log) => {
                const item = items.find((entry) => entry.id === log.inventory_item_id);
                return <tr key={log.id}><td className="whitespace-nowrap px-5 py-4">{log.date}</td><td className="px-5 py-4 font-medium text-slate-900">{log.item_name}</td><td className="px-5 py-4">{log.quantity} {log.unit}</td><td className="px-5 py-4">{log.reason}<div className="text-xs text-slate-500">₹{log.financial_loss_inr.toLocaleString()} loss</div></td><td className="px-5 py-4 text-right"><button disabled={!item || !!investigatingId} onClick={() => item && void investigate(item, log.date)} className="inline-flex items-center text-xs font-medium text-indigo-700 disabled:text-slate-400"><Sparkles className="mr-1 h-3 w-3" />{investigatingId === item?.id ? 'Analyzing…' : 'Analyze Risk'}</button></td></tr>;
              })}</tbody>
        </table></div>
      </section>

      <section className="flex h-fit flex-col overflow-hidden rounded-lg border border-slate-200 bg-white">
        <div className="flex items-center border-b bg-indigo-50 p-4"><Sparkles className="mr-2 h-5 w-5 text-indigo-600" /><h2 className="text-lg font-semibold text-indigo-900">Investigation</h2></div>
        {!investigationResult ? <div className="p-6 text-center text-sm text-slate-500"><Search className="mx-auto mb-3 h-6 w-6" />Analyze a waste entry linked to an inventory item to get a backend investigation.</div> :
          <div className="space-y-4 p-5">
            <div><h3 className="font-bold text-slate-800">{investigationResult.target_item_name}</h3><p className="text-sm text-slate-600">{investigationResult.investigation_summary}</p><p className="mt-1 text-sm font-medium">Risk: ₹{investigationResult.financial_risk_inr.toLocaleString()}</p></div>
            <div className="rounded bg-slate-50 p-3"><h4 className="mb-1 flex items-center text-sm font-semibold"><CheckCircle className="mr-1 h-4 w-4 text-emerald-600" />Verified facts</h4><ul className="list-inside list-disc text-sm text-slate-600">{investigationResult.verified_facts.map((fact, index) => <li key={index}>{fact}</li>)}</ul></div>
            <div className="rounded bg-amber-50 p-3"><h4 className="mb-1 flex items-center text-sm font-semibold text-amber-900"><AlertTriangle className="mr-1 h-4 w-4 text-amber-600" />Hypotheses</h4><ul className="list-inside list-disc text-sm text-amber-800">{investigationResult.hypotheses.map((hypothesis, index) => <li key={index}>{hypothesis}</li>)}</ul></div>
            {investigationResult.data_gaps.length > 0 && <p className="text-xs text-slate-500">Data gaps: {investigationResult.data_gaps.join('; ')}</p>}
            <div><h4 className="mb-2 text-sm font-semibold">Proposed interventions</h4><div className="space-y-2">{investigationResult.recommended_interventions.map((intervention) => <div key={intervention.intervention_id} className="rounded border p-3"><p className="text-sm font-medium">{intervention.title}</p><p className="my-1 text-xs text-slate-500">{intervention.details}</p><button onClick={() => void approve(intervention.intervention_id)} className="w-full rounded bg-slate-800 py-1.5 text-xs font-medium text-white">Record approval</button></div>)}</div></div>
          </div>}
      </section>
    </div>
  </div>;
}
