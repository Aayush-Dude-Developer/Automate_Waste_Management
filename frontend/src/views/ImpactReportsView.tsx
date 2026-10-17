import { useEffect, useState } from 'react';
import { Download } from 'lucide-react';
import { apiRequest, type WasteRecord } from '../lib/api';

interface Handover { id: string; item_name: string; quantity_kg: number; centre_id: string; status: string; timestamp: string }

function downloadCsv(rows: string[][]) {
  const csv = rows.map((row) => row.map((cell) => `"${cell.replaceAll('"', '""')}"`).join(',')).join('\r\n');
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
  const link = document.createElement('a');
  link.href = url;
  link.download = 'sustainbite-impact-report.csv';
  link.click();
  URL.revokeObjectURL(url);
}

export default function ImpactReportsView() {
  const [waste, setWaste] = useState<WasteRecord[]>([]);
  const [handovers, setHandovers] = useState<Handover[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    Promise.all([
      apiRequest<WasteRecord[]>('/api/waste?limit=100'),
      apiRequest<Handover[]>('/api/donations/handovers?limit=100'),
    ]).then(([wasteRecords, donationHandovers]) => {
      setWaste(wasteRecords);
      setHandovers(donationHandovers);
    }).catch((cause: unknown) => {
      setError(cause instanceof Error ? cause.message : 'Could not load impact records.');
    }).finally(() => setLoading(false));
  }, []);

  const reportRows = (wasteRecords: WasteRecord[], donationHandovers: Handover[]) => [
    ['Record Type', 'Date', 'Item', 'Quantity', 'Unit', 'Reason / Recipient', 'Financial Loss (INR)', 'Status'],
    ...wasteRecords.map((record) => ['Waste', record.date, record.item_name, String(record.quantity), record.unit, record.reason, String(record.financial_loss_inr), 'RECORDED']),
    ...donationHandovers.map((record) => ['Donation handover', record.timestamp, record.item_name, String(record.quantity_kg), 'kg', record.centre_id, '', record.status]),
  ];

  const rows = reportRows(waste, handovers);
  const exportFullReport = async () => {
    setLoading(true);
    setError('');
    try {
      const [allWaste, allHandovers] = await Promise.all([
        apiRequest<WasteRecord[]>('/api/waste'),
        apiRequest<Handover[]>('/api/donations/handovers'),
      ]);
      setWaste(allWaste);
      setHandovers(allHandovers);
      downloadCsv(reportRows(allWaste, allHandovers));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not export the complete impact report.');
    } finally {
      setLoading(false);
    }
  };

  return <div className="p-8">
    <div className="mb-6 flex items-center justify-between"><div><h1 className="text-2xl font-bold text-slate-800">Impact & Sustainability Reports</h1><p className="mt-1 text-sm text-slate-500">Latest 100 waste and donation records. Export loads all history.</p></div><button disabled={loading || !!error} onClick={() => void exportFullReport()} className="flex items-center rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"><Download className="mr-2 h-4 w-4" />Export CSV</button></div>
    {error && <div role="alert" className="mb-4 rounded-md border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">{error}</div>}
    {loading ? <p className="text-slate-500">Loading report data…</p> :
      <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
        <table className="w-full text-left text-sm"><thead className="border-b bg-slate-50 text-slate-700"><tr>{rows[0].map((header) => <th key={header} className="px-4 py-3 font-semibold">{header}</th>)}</tr></thead>
          <tbody className="divide-y divide-slate-200">{rows.slice(1).length === 0 ? <tr><td colSpan={8} className="p-8 text-center text-slate-500">No waste or donation records are available yet.</td></tr> : rows.slice(1).map((row, index) => <tr key={index}>{row.map((cell, cellIndex) => <td key={cellIndex} className="px-4 py-3 text-slate-600">{cell}</td>)}</tr>)}</tbody>
        </table>
      </div>}
    <p className="mt-3 text-xs text-slate-500">Exports include only records returned by the backend; no estimates are added.</p>
  </div>;
}
