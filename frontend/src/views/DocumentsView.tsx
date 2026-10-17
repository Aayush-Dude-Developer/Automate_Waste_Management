import { useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { CheckCircle, FileText, Plus, Send, Trash2, UploadCloud } from 'lucide-react';
import { apiRequest } from '../lib/api';

type ImportTarget = 'waste_records' | 'staff_meal_records' | 'inventory_items';
type EditableRecord = Record<string, unknown>;

interface ExtractionPreview {
  document_id: string;
  document_type_hint: string | null;
  available_fields: string[];
  extracted_records: EditableRecord[];
  confidence_score: number;
  ambiguous_fields: string[];
  duplicate_warning: boolean;
  message: string;
}

interface AmendmentResponse {
  updated_records: EditableRecord[];
  message: string;
}

const fieldClass = 'rounded-md border border-slate-300 px-3 py-2 text-sm';
const DOCUMENT_REQUEST_TIMEOUT_MS = 5 * 60 * 1000;
const jsonArrayFields = new Set(['items', 'yield_stages']);

function cellText(value: unknown): string {
  if (value === null || value === undefined) return '';
  return typeof value === 'string' ? value : JSON.stringify(value);
}

function prepareRecords(records: EditableRecord[]): EditableRecord[] {
  return records.map((record) => {
    const prepared: EditableRecord = {};
    for (const [key, rawValue] of Object.entries(record)) {
      if (rawValue === null || rawValue === undefined || rawValue === '') continue;
      if (jsonArrayFields.has(key) && typeof rawValue === 'string') {
        try {
          prepared[key] = JSON.parse(rawValue) as unknown;
        } catch {
          throw new Error(`${key} must contain valid JSON.`);
        }
      } else {
        prepared[key] = rawValue;
      }
    }
    return prepared;
  });
}

function columnsFor(records: EditableRecord[], availableFields: string[]): string[] {
  const present = new Set(records.flatMap((record) => Object.keys(record)));
  return [
    ...availableFields,
    ...Array.from(present).filter((field) => !availableFields.includes(field)),
  ];
}

export default function DocumentsView() {
  const fileRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [hint, setHint] = useState('waste');
  const [preview, setPreview] = useState<ExtractionPreview | null>(null);
  const [records, setRecords] = useState<EditableRecord[]>([]);
  const [target, setTarget] = useState<ImportTarget>('waste_records');
  const [amendment, setAmendment] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const upload = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!file) {
      setError('Choose a file to upload.');
      return;
    }
    setBusy(true);
    setError('');
    setNotice('');
    setPreview(null);
    setRecords([]);
    const body = new FormData();
    body.append('file', file);
    body.append('document_type_hint', hint);
    try {
      const result = await apiRequest<ExtractionPreview>('/api/documents/upload', {
        method: 'POST',
        body,
        signal: AbortSignal.timeout(DOCUMENT_REQUEST_TIMEOUT_MS),
      });
      setPreview(result);
      setRecords(result.extracted_records);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not upload this document.');
    } finally {
      setBusy(false);
    }
  };

  const importRecords = async () => {
    if (!preview) return;
    if (records.length === 0) {
      setError('Add at least one row before confirming the import.');
      return;
    }
    setBusy(true);
    setError('');
    setNotice('');
    try {
      const confirmedRecords = prepareRecords(records);
      const result = await apiRequest<{ imported_records: number }>('/api/documents/confirm-import', {
        method: 'POST',
        body: JSON.stringify({
          document_id: preview.document_id,
          confirmed_records: confirmedRecords,
          target_entity: target,
        }),
        signal: AbortSignal.timeout(DOCUMENT_REQUEST_TIMEOUT_MS),
      });
      setNotice(`${result.imported_records} record(s) imported.`);
      setPreview(null);
      setRecords([]);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not import the confirmed records.');
    } finally {
      setBusy(false);
    }
  };

  const requestAmendment = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!amendment.trim()) return;
    setBusy(true);
    setError('');
    setNotice('');
    try {
      const result = await apiRequest<AmendmentResponse>('/api/documents/amend-records', {
        method: 'POST',
        body: JSON.stringify({
          target_entity: target,
          current_records: prepareRecords(records),
          amendment: amendment.trim(),
        }),
        signal: AbortSignal.timeout(DOCUMENT_REQUEST_TIMEOUT_MS),
      });
      setRecords(result.updated_records);
      setNotice(`${result.message} Review the updated table before importing.`);
      setAmendment('');
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not apply that amendment.');
    } finally {
      setBusy(false);
    }
  };

  const pickFile = (next: File | null) => {
    if (next) {
      setFile(next);
      setError('');
      setNotice('');
    }
  };

  const changeRecord = (rowIndex: number, field: string, value: string) => {
    setRecords((current) => current.map((record, index) => (
      index === rowIndex ? { ...record, [field]: value } : record
    )));
  };

  const changeDocumentType = (nextHint: string) => {
    setHint(nextHint);
    setTarget(nextHint === 'staff_meals'
      ? 'staff_meal_records'
      : nextHint === 'inventory_items' ? 'inventory_items' : 'waste_records');
    setPreview(null);
    setRecords([]);
    setNotice('');
  };

  const columns = columnsFor(records, preview?.available_fields ?? []);

  return <div className="p-8">
    <div className="mb-6"><h1 className="text-2xl font-bold text-slate-800">Document Ingestion</h1><p className="mt-1 text-sm text-slate-500">Upload a document, review and edit mapped records, then explicitly confirm imports. Extraction uses recent entries as formatting examples when available.</p></div>
    {error && <div role="alert" className="mb-4 rounded-md border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">{error}</div>}
    {notice && <div role="status" className="mb-4 rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">{notice}</div>}
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
      <div className="space-y-6 lg:col-span-2">
        <form onSubmit={upload} className="rounded-lg border border-slate-200 bg-white p-6">
          <div className="mb-4 flex flex-wrap gap-3">
            <label className="text-sm font-medium text-slate-700">Document type<select value={hint} onChange={(event) => changeDocumentType(event.target.value)} className={`${fieldClass} ml-2`}><option value="waste">Waste record</option><option value="staff_meals">Staff meals</option><option value="inventory_items">Inventory items</option></select></label>
          </div>
          <div onDragOver={(event) => { event.preventDefault(); }} onDrop={(event) => { event.preventDefault(); pickFile(event.dataTransfer.files.item(0)); }} className="mb-4 flex flex-col items-center rounded-lg border-2 border-dashed border-slate-300 bg-slate-50 p-10 text-center">
            <UploadCloud className="mb-3 h-10 w-10 text-slate-400" /><p className="mb-2 text-sm text-slate-700">{file ? file.name : 'Drop a supported document here or browse'}</p>
            <input ref={fileRef} type="file" accept=".pdf,.jpg,.jpeg,.png,.csv,.txt" className="hidden" onChange={(event) => pickFile(event.target.files?.item(0) ?? null)} />
            <button type="button" onClick={() => fileRef.current?.click()} className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700">Browse files</button>
            <p className="mt-2 text-xs text-slate-500">PDF, JPG, PNG, CSV, or TXT</p>
          </div>
          <button disabled={busy || !file} className="rounded-md bg-restaurant-primary px-4 py-2 text-sm font-medium text-white disabled:opacity-50">{busy ? 'Uploading…' : 'Upload and extract'}</button>
        </form>

        <section className="rounded-lg border border-slate-200 bg-white p-6">
          <h2 className="mb-4 flex items-center text-base font-semibold text-slate-800"><FileText className="mr-2 h-5 w-5 text-slate-400" />Extraction Preview</h2>
          {!preview ? <p className="rounded border border-dashed bg-slate-50 py-8 text-center text-sm text-slate-500">Upload a document to request a backend preview.</p> : <>
            <p className="mb-2 text-sm text-slate-700">{preview.message}</p>
            {preview.duplicate_warning && <p className="mb-2 text-sm text-amber-700">This file matches a previous upload.</p>}
            <p className="mb-3 text-xs text-slate-500">Confidence: {(preview.confidence_score * 100).toFixed(0)}% · Document ID: {preview.document_id}</p>
            {preview.ambiguous_fields.length > 0 && <ul className="mb-3 list-inside list-disc text-sm text-amber-700">{preview.ambiguous_fields.map((entry, index) => <li key={index}>{entry}</li>)}</ul>}

            <div className="mb-3 flex flex-wrap gap-2">
              <button type="button" onClick={() => setRecords((current) => [...current, {}])} disabled={busy} className="inline-flex items-center rounded-md border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 disabled:opacity-50"><Plus className="mr-1 h-4 w-4" />Add row</button>
              <button type="button" onClick={() => setRecords([])} disabled={busy || records.length === 0} className="inline-flex items-center rounded-md border border-rose-200 px-3 py-2 text-sm font-medium text-rose-700 disabled:opacity-50"><Trash2 className="mr-1 h-4 w-4" />Clear table</button>
            </div>
            {records.length === 0 ? <p className="mb-3 rounded border border-dashed bg-slate-50 py-5 text-center text-sm text-slate-500">No rows to review. Add a row to enter data manually, or clear this preview.</p> : <div className="mb-4 max-h-[28rem] overflow-auto rounded border border-slate-200">
              <table className="min-w-full border-collapse text-left text-sm">
                <thead className="sticky top-0 bg-slate-100 text-xs uppercase text-slate-600"><tr>{columns.map((column) => <th key={column} className="whitespace-nowrap border-b px-3 py-2 font-semibold">{column}</th>)}<th className="border-b px-3 py-2">Row</th></tr></thead>
                <tbody>{records.map((record, rowIndex) => <tr key={rowIndex} className="border-b last:border-b-0">
                  {columns.map((column) => <td key={column} className="min-w-40 px-2 py-2 align-top"><input aria-label={`Row ${rowIndex + 1}, ${column}`} value={cellText(record[column])} onChange={(event) => changeRecord(rowIndex, column, event.target.value)} className="w-full min-w-36 rounded border border-slate-300 px-2 py-1.5 text-sm" /></td>)}
                  <td className="px-2 py-2 align-top"><button type="button" aria-label={`Remove row ${rowIndex + 1}`} onClick={() => setRecords((current) => current.filter((_, index) => index !== rowIndex))} className="rounded p-1 text-rose-600 hover:bg-rose-50"><Trash2 className="h-4 w-4" /></button></td>
                </tr>)}</tbody>
              </table>
            </div>}

            <form onSubmit={(event) => void requestAmendment(event)} className="mb-4 rounded-md border border-slate-200 bg-slate-50 p-4">
              <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="document-amendment">Ask Gemini to amend the table</label>
              <div className="flex flex-col gap-2 sm:flex-row">
                <textarea id="document-amendment" rows={2} value={amendment} onChange={(event) => setAmendment(event.target.value)} placeholder="For example: Set the unit for row 1 to kg and change its quantity to 4." className="min-w-0 flex-1 rounded-md border border-slate-300 p-2 text-sm" />
                <button type="submit" disabled={busy || !amendment.trim() || records.length === 0} className="inline-flex items-center justify-center self-end rounded-md bg-indigo-700 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"><Send className="mr-2 h-4 w-4" />{busy ? 'Working…' : 'Apply amendment'}</button>
              </div>
              <p className="mt-2 text-xs text-slate-500">Gemini applies your instruction to the current rows. Review every change before importing.</p>
            </form>

            <button disabled={busy || records.length === 0} onClick={() => void importRecords()} className="rounded-md bg-slate-800 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"><CheckCircle className="mr-2 inline h-4 w-4" />{busy ? 'Working…' : 'Confirm import'}</button>
          </>}
        </section>
      </div>
      <aside className="h-fit rounded-lg border border-amber-200 bg-amber-50 p-5">
        <h2 className="mb-2 font-semibold text-amber-900">Review and mapping</h2>
        <p className="text-sm text-amber-800">Gemini maps differently named document headings to the selected table’s fields. Missing values are left blank for review, not invented. Edit cells directly, add or remove rows, or ask Gemini to amend the data. Only confirming the reviewed table imports it.</p>
      </aside>
    </div>
  </div>;
}
