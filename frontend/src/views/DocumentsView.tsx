import { useState } from 'react';
import { UploadCloud, FileText, CheckCircle, AlertCircle } from 'lucide-react';

export default function DocumentsView() {
  const [isDragging, setIsDragging] = useState(false);

  return (
    <div className="p-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-slate-800">Document Ingestion & OCR</h1>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          {/* Upload Area */}
          <div 
            className={`border-2 border-dashed rounded-lg p-10 flex flex-col items-center justify-center text-center transition-colors mb-6
              ${isDragging ? 'border-restaurant-primary bg-emerald-50' : 'border-slate-300 bg-white hover:bg-slate-50'}`}
            onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={(e) => { e.preventDefault(); setIsDragging(false); }}
          >
            <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mb-4">
              <UploadCloud className="w-8 h-8 text-slate-500" />
            </div>
            <h3 className="text-lg font-medium text-slate-900 mb-2">Upload Physical Forms</h3>
            <p className="text-slate-500 text-sm mb-6 max-w-sm">
              Drag and drop scanned Wastage Records, Staff Meal sheets, or Invoices. Supported formats: PDF, JPG, PNG, Excel.
            </p>
            <button className="bg-white border border-slate-300 text-slate-700 px-4 py-2 rounded-md hover:bg-slate-50 font-medium text-sm transition-colors">
              Browse Files
            </button>
          </div>

          {/* Extraction Preview Placeholder */}
          <div className="bg-white rounded-lg shadow-sm border border-slate-200 p-6">
            <h3 className="text-base font-semibold text-slate-800 mb-4 flex items-center">
              <FileText className="w-5 h-5 mr-2 text-slate-400" />
              Extraction Preview
            </h3>
            <div className="py-8 text-center text-slate-500 text-sm bg-slate-50 rounded border border-dashed border-slate-200">
              Upload a document to see AI-extracted records here before committing to the database.
            </div>
          </div>
        </div>

        <div>
          {/* History / Status Panel */}
          <div className="bg-white rounded-lg shadow-sm border border-slate-200 p-6">
            <h3 className="text-base font-semibold text-slate-800 mb-4">Recent Uploads</h3>
            <div className="space-y-4">
              <div className="flex items-start">
                <CheckCircle className="w-5 h-5 text-emerald-500 mr-3 mt-0.5 shrink-0" />
                <div>
                  <p className="text-sm font-medium text-slate-900">staff_meals_sept29.jpg</p>
                  <p className="text-xs text-slate-500">Imported 16 records • 2 days ago</p>
                </div>
              </div>
              <div className="flex items-start">
                <CheckCircle className="w-5 h-5 text-emerald-500 mr-3 mt-0.5 shrink-0" />
                <div>
                  <p className="text-sm font-medium text-slate-900">wastage_august.jpg</p>
                  <p className="text-xs text-slate-500">Imported 22 records • 5 days ago</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
