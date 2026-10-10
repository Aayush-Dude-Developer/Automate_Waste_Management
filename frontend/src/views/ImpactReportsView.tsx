import { Download, BarChart2 } from 'lucide-react';

export default function ImpactReportsView() {
  return (
    <div className="p-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-slate-800">Impact & Sustainability Reports</h1>
        <button className="bg-white border border-slate-300 text-slate-700 px-4 py-2 rounded-md hover:bg-slate-50 font-medium text-sm transition-colors flex items-center">
          <Download className="w-4 h-4 mr-2" />
          Export CSV
        </button>
      </div>

      <div className="h-[500px] border-2 border-dashed border-slate-200 rounded-lg flex flex-col items-center justify-center text-center p-8 bg-slate-50">
        <BarChart2 className="w-16 h-16 text-slate-300 mb-4" />
        <h3 className="text-xl font-medium text-slate-900 mb-2">Detailed Analytics Engine</h3>
        <p className="text-slate-500 max-w-md mb-6">
          The core metrics are available on the main Dashboard. This section is reserved for deep-dive historical reports, predictive financial modelling, and regulatory sustainability compliance exports.
        </p>
      </div>
    </div>
  );
}
