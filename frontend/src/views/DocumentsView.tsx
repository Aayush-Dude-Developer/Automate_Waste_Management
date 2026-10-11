import { useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { CheckCircle, FileText, UploadCloud } from 'lucide-react';
import { apiRequest } from '../lib/api';

interface ExtractionPreview {
  document_id: string;
  document_type_hint: string | null;
  extracted_records: Record<string, unknown>[];
  confidence_score: number;
  ambiguous_fields: string[];
  duplicate_warning: boolean;
  message: string;
}

const fieldClass = 'rounded-md border border-slate-300 px-3 py-2 text-sm';

export default function DocumentsView() {
  const fileRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [hint, setHint] = useState('waste');
  const [preview, setPreview] = useState<ExtractionPreview | null>(null);
  const [recordsJson, setRecordsJson] = useState('[]');
  const [target, setTarget] = useState('waste_records');
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
    const body = new FormData();
    body.append('file', file);
    body.append('document_type_hint', hint);
    try {
      const result = await apiRequest<ExtractionPreview>('/api/documents/upload', { method: 'POST', body });
      setPreview(result);
      setRecordsJson(JSON.stringify(result.extracted_records, null, 2));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not upload this document.');
    } finally {
      setBusy(false);
    }
  };

  const importRecords = async () => {
    if (!preview) return;
    setBusy(true);
    setError('');
    setNotice('');
    try {
      const records: unknown = JSON.parse(recordsJson);
      if (!Array.isArray(records) || records.some((record) => !record || typeof record !== 'object' || Array.isArray(record))) {
        throw new Error('Records must be a JSON array of objects.');
      }
      const result = await apiRequest<{ imported_records: number }>('/api/documents/confirm-import', {
        method: 'POST',
        body: JSON.stringify({ document_id: preview.document_id, confirmed_records: records, target_entity: target }),
      });
      setNotice(`${result.imported_records} record(s) imported.`);
      setPreview(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not import the confirmed records.');
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

  return <div className="p-8">
    <div className="mb-6"><h1 className="text-2xl font-bold text-slate-800">Document Ingestion</h1><p className="mt-1 text-sm text-slate-500">Upload to the backend, review extracted records, and explicitly confirm imports.</p></div>
    {error && <div role="alert" className="mb-4 rounded-md border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">{error}</div>}
    {notice && <div role="status" className="mb-4 rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">{notice}</div>}
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
      <div className="space-y-6 lg:col-span-2">
        <form onSubmit={upload} className="rounded-lg border border-slate-200 bg-white p-6">
          <div className="mb-4 flex flex-wrap gap-3">
            <label className="text-sm font-medium text-slate-700">Document type<select value={hint} onChange={(e) => setHint(e.target.value)} className={`${fieldClass} ml-2`}><option value="waste">Waste record</option><option value="staff_meals">Staff meals</option><option value="inventory_items">Inventory items</option></select></label>
          </div>
          <div onDragOver={(e) => { e.preventDefault(); }} onDrop={(e) => { e.preventDefault(); pickFile(e.dataTransfer.files.item(0)); }} className="mb-4 flex flex-col items-center rounded-lg border-2 border-dashed border-slate-300 bg-slate-50 p-10 text-center">
            <UploadCloud className="mb-3 h-10 w-10 text-slate-400" /><p className="mb-2 text-sm text-slate-700">{file ? file.name : 'Drop a supported document here or browse'}</p>
            <input ref={fileRef} type="file" accept=".pdf,.jpg,.jpeg,.png,.csv,.txt" className="hidden" onChange={(e) => pickFile(e.target.files?.item(0) ?? null)} />
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
            <label className="mb-2 block text-sm font-medium text-slate-700">Confirmed records (JSON array)<textarea rows={8} value={recordsJson} onChange={(e) => setRecordsJson(e.target.value)} className="mt-1 w-full rounded-md border border-slate-300 p-3 font-mono text-xs" /></label>
            <label className="mb-3 block text-sm font-medium text-slate-700">Import as<select value={target} onChange={(e) => setTarget(e.target.value)} className={`${fieldClass} ml-2`}><option value="waste_records">Waste records</option><option value="staff_meal_records">Staff meal records</option><option value="inventory_items">Inventory items</option></select></label>
            <button disabled={busy} onClick={() => void importRecords()} className="rounded-md bg-slate-800 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"><CheckCircle className="mr-2 inline h-4 w-4" />{busy ? 'Importing…' : 'Confirm import'}</button>
          </>}
        </section>
      </div>
      <aside className="h-fit rounded-lg border border-amber-200 bg-amber-50 p-5">
        <h2 className="mb-2 font-semibold text-amber-900">OCR availability</h2>
        <p className="text-sm text-amber-800">The backend currently accepts and records uploads but does not run OCR. It returns no extracted sample records. You can edit the JSON preview and confirm valid records manually; the app will report validation errors from the backend.</p>
      </aside>
    </div>
  </div>;
}
