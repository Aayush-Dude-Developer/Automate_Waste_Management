import { useCallback, useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { Plus, RefreshCw } from 'lucide-react';
import { apiRequest, type InventoryItem, type PurchaseInvoice } from '../lib/api';

const fieldClass = 'w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm';
const labelClass = 'mb-1 block text-xs font-medium text-slate-600';
const today = new Date().toISOString().slice(0, 10);

interface PurchaseLineForm {
  ingredient_id: string;
  quantity_purchased: string;
  purchase_unit: string;
  unit_price: string;
  quantity_received: string;
  expiry_date: string;
  batch_number: string;
}

const emptyLine = (): PurchaseLineForm => ({
  ingredient_id: '',
  quantity_purchased: '',
  purchase_unit: '',
  unit_price: '',
  quantity_received: '0',
  expiry_date: '',
  batch_number: '',
});

export default function PurchaseInvoicesView() {
  const [invoices, setInvoices] = useState<PurchaseInvoice[]>([]);
  const [inventory, setInventory] = useState<InventoryItem[]>([]);
  const [lines, setLines] = useState<PurchaseLineForm[]>([emptyLine()]);
  const [supplierId, setSupplierId] = useState('');
  const [invoiceNumber, setInvoiceNumber] = useState('');
  const [invoiceDate, setInvoiceDate] = useState(today);
  const [receivedDate, setReceivedDate] = useState(today);
  const [totalAmount, setTotalAmount] = useState('');
  const [billUrl, setBillUrl] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [busyId, setBusyId] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const load = useCallback(async () => {
    setError('');
    try {
      const [purchaseRows, inventoryRows] = await Promise.all([
        apiRequest<PurchaseInvoice[]>('/api/purchases?limit=100'),
        apiRequest<InventoryItem[]>('/api/inventory/items'),
      ]);
      setInvoices(purchaseRows);
      setInventory(inventoryRows);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not load purchase invoices.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void Promise.resolve().then(load); }, [load]);

  const updateLine = (index: number, key: keyof PurchaseLineForm, value: string) => {
    setLines((current) => current.map((line, lineIndex) => {
      if (lineIndex !== index) return line;
      if (key === 'ingredient_id') {
        const item = inventory.find((candidate) => candidate.ingredient_id === value || candidate.id === value);
        return { ...line, ingredient_id: value, purchase_unit: item?.input_unit || item?.base_unit || line.purchase_unit };
      }
      return { ...line, [key]: value };
    }));
  };

  const createInvoice = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaving(true);
    setError('');
    setNotice('');
    try {
      await apiRequest<PurchaseInvoice>('/api/purchases', {
        method: 'POST',
        body: JSON.stringify({
          supplier_id: supplierId.trim(),
          invoice_number: invoiceNumber.trim(),
          invoice_date: invoiceDate,
          received_date: receivedDate,
          total_amount: Number(totalAmount),
          bill_document_url: billUrl.trim() || null,
          verification_status: 'pending',
          line_items: lines.map((line) => ({
            ingredient_id: line.ingredient_id,
            quantity_purchased: Number(line.quantity_purchased),
            purchase_unit: line.purchase_unit.trim(),
            unit_price: Number(line.unit_price),
            quantity_received: Number(line.quantity_received),
            expiry_date: line.expiry_date || null,
            batch_number: line.batch_number.trim() || null,
          })),
        }),
      });
      setSupplierId('');
      setInvoiceNumber('');
      setInvoiceDate(today);
      setReceivedDate(today);
      setTotalAmount('');
      setBillUrl('');
      setLines([emptyLine()]);
      setNotice('Invoice saved as pending. Verify it after checking its lines to post received stock.');
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not save purchase invoice.');
    } finally {
      setSaving(false);
    }
  };

  const verifyInvoice = async (invoice: PurchaseInvoice) => {
    setBusyId(invoice.purchase_id);
    setError('');
    setNotice('');
    try {
      await apiRequest<PurchaseInvoice>(`/api/purchases/${encodeURIComponent(invoice.purchase_id)}/verify`, { method: 'POST' });
      setNotice(`Invoice ${invoice.invoice_number} verified. Received quantities have been posted to inventory.`);
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not verify purchase invoice.');
    } finally {
      setBusyId('');
    }
  };

  return <div className="p-6 md:p-8">
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div>
        <p className="text-sm font-medium text-emerald-700">Verified receiving workflow</p>
        <h1 className="mt-1 text-2xl font-bold text-slate-800">Purchase Invoices</h1>
        <p className="mt-1 text-sm text-slate-500">Record invoices and verify received lines before stock is updated.</p>
      </div>
      <Link to="/sales-purchases" className="text-sm font-semibold text-emerald-800 underline">View Purchase Recommendations</Link>
    </div>
    {error && <div role="alert" className="mb-4 rounded-md border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">{error}</div>}
    {notice && <div role="status" className="mb-4 rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">{notice}</div>}

    <form onSubmit={createInvoice} className="mb-6 rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="mb-4 text-lg font-semibold text-slate-800">Record purchase invoice</h2>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <label className={labelClass}>Supplier ID<input required value={supplierId} onChange={(event) => setSupplierId(event.target.value)} className={`${fieldClass} mt-1`} /></label>
        <label className={labelClass}>Invoice number<input required value={invoiceNumber} onChange={(event) => setInvoiceNumber(event.target.value)} className={`${fieldClass} mt-1`} /></label>
        <label className={labelClass}>Invoice date<input required type="date" value={invoiceDate} onChange={(event) => setInvoiceDate(event.target.value)} className={`${fieldClass} mt-1`} /></label>
        <label className={labelClass}>Received date<input required type="date" value={receivedDate} onChange={(event) => setReceivedDate(event.target.value)} className={`${fieldClass} mt-1`} /></label>
        <label className={labelClass}>Invoice total<input required type="number" min="0" step="0.01" value={totalAmount} onChange={(event) => setTotalAmount(event.target.value)} className={`${fieldClass} mt-1`} /></label>
        <label className={labelClass}>Bill document URL (optional)<input type="url" value={billUrl} onChange={(event) => setBillUrl(event.target.value)} className={`${fieldClass} mt-1`} /></label>
      </div>

      <div className="mt-5 flex items-center justify-between gap-3">
        <h3 className="font-semibold text-slate-800">Received ingredient lines</h3>
        <button type="button" onClick={() => setLines((current) => [...current, emptyLine()])} className="inline-flex items-center gap-1 rounded border border-slate-300 px-3 py-2 text-xs font-medium text-slate-700"><Plus className="h-3 w-3" />Add line</button>
      </div>
      <div className="mt-3 space-y-3">
        {lines.map((line, index) => <div key={index} className="grid gap-3 rounded-md border border-slate-200 p-3 sm:grid-cols-2 lg:grid-cols-4">
          <label className={labelClass}>Ingredient<select required value={line.ingredient_id} onChange={(event) => updateLine(index, 'ingredient_id', event.target.value)} className={`${fieldClass} mt-1`}><option value="">Select ingredient</option>{inventory.map((item) => <option key={item.ingredient_id || item.id} value={item.ingredient_id || item.id}>{item.item_name}</option>)}</select></label>
          <label className={labelClass}>Purchased quantity<input required type="number" min="0.001" step="any" value={line.quantity_purchased} onChange={(event) => updateLine(index, 'quantity_purchased', event.target.value)} className={`${fieldClass} mt-1`} /></label>
          <label className={labelClass}>Purchase unit<input required value={line.purchase_unit} onChange={(event) => updateLine(index, 'purchase_unit', event.target.value)} className={`${fieldClass} mt-1`} /></label>
          <label className={labelClass}>Unit price<input required type="number" min="0" step="any" value={line.unit_price} onChange={(event) => updateLine(index, 'unit_price', event.target.value)} className={`${fieldClass} mt-1`} /></label>
          <label className={labelClass}>Quantity received<input required type="number" min="0" step="any" value={line.quantity_received} onChange={(event) => updateLine(index, 'quantity_received', event.target.value)} className={`${fieldClass} mt-1`} /></label>
          <label className={labelClass}>Expiry date<input type="date" value={line.expiry_date} onChange={(event) => updateLine(index, 'expiry_date', event.target.value)} className={`${fieldClass} mt-1`} /></label>
          <label className={labelClass}>Batch number<input value={line.batch_number} onChange={(event) => updateLine(index, 'batch_number', event.target.value)} className={`${fieldClass} mt-1`} /></label>
          {lines.length > 1 && <button type="button" onClick={() => setLines((current) => current.filter((_, lineIndex) => lineIndex !== index))} className="self-end text-left text-xs text-rose-700 underline">Remove line</button>}
        </div>)}
      </div>
      <button disabled={saving || !inventory.length} className="mt-4 rounded-md bg-emerald-700 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">{saving ? 'Saving…' : 'Save pending invoice'}</button>
      {!inventory.length && !loading && <p className="mt-2 text-xs text-amber-800">Add inventory items before recording invoice lines.</p>}
    </form>

    <section className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
      <div className="flex items-center justify-between border-b border-slate-200 p-4"><h2 className="font-semibold text-slate-800">Recent invoices</h2><button onClick={() => void load()} className="inline-flex items-center gap-2 text-sm text-slate-600"><RefreshCw className="h-4 w-4" />Refresh</button></div>
      {loading ? <p className="p-6 text-sm text-slate-500">Loading invoices…</p> : !invoices.length ? <p className="p-8 text-center text-sm text-slate-500">No purchase invoices recorded.</p> : <div className="overflow-x-auto"><table className="w-full min-w-[800px] text-left text-sm"><thead className="bg-slate-50 text-xs text-slate-600"><tr><th className="p-3">Invoice</th><th className="p-3">Supplier</th><th className="p-3">Dates</th><th className="p-3">Total</th><th className="p-3">Lines</th><th className="p-3">Status / action</th></tr></thead><tbody className="divide-y divide-slate-100">{invoices.map((invoice) => <tr key={invoice.purchase_id} className="align-top"><td className="p-3"><strong>{invoice.invoice_number}</strong><div className="mt-1 text-xs text-slate-500">{invoice.purchase_id}</div></td><td className="p-3">{invoice.supplier_id}</td><td className="p-3">Invoice: {invoice.invoice_date}<div>Received: {invoice.received_date || 'Not entered'}</div></td><td className="p-3">{invoice.total_amount.toLocaleString()}</td><td className="max-w-sm p-3">{invoice.line_items.map((line) => <div key={line.purchase_line_id} className="mb-2 text-xs"><strong>{inventory.find((item) => (item.ingredient_id || item.id) === line.ingredient_id)?.item_name || line.ingredient_id}</strong>: {line.quantity_received} {line.purchase_unit}<span className="block text-slate-500">Purchase line ID: {line.purchase_line_id}</span></div>)}</td><td className="p-3"><span className="font-medium capitalize">{invoice.verification_status}</span>{invoice.verification_status === 'pending' && <button disabled={busyId === invoice.purchase_id || !invoice.received_date} onClick={() => void verifyInvoice(invoice)} className="mt-2 block rounded bg-emerald-700 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50">{busyId === invoice.purchase_id ? 'Verifying…' : 'Verify & post stock'}</button>}</td></tr>)}</tbody></table></div>}
    </section>
  </div>;
}
