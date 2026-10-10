import { useState } from 'react';
import { Plus, Trash2, Search, Filter, Sparkles, AlertTriangle, CheckCircle } from 'lucide-react';

export default function SurplusWasteView() {
  const [wasteLogs, setWasteLogs] = useState<any[]>([
    { id: 'w1', date: '2026-08-02', item_name: 'Chinese Noodles', quantity: 400, unit: 'gm', reason: 'Broken', checked_by: 'Ritesh' },
    { id: 'w2', date: '2026-08-04', item_name: 'Banana Yellow', quantity: 6, unit: 'piece', reason: 'Spoiled', checked_by: 'Ritesh' },
    { id: 'w3', date: '2026-08-05', item_name: 'Chicken Leg', quantity: 150, unit: 'gm', reason: 'Scrap', checked_by: 'Alicia Ho' },
  ]);

  const [investigating, setInvestigating] = useState(false);
  const [investigationResult, setInvestigationResult] = useState<any>(null);

  const handleInvestigate = () => {
    setInvestigating(true);
    // Simulate API Call to /api/ai/investigate-surplus
    setTimeout(() => {
      setInvestigationResult({
        target_item_name: 'Chinese Noodles 10mm',
        investigation_summary: 'Analysis complete. A significant surplus and wastage trend has been detected over the last 14 days, specifically linked to physical prep damage.',
        verified_facts: [
          'Current inventory is 4.5 kg.',
          'Item was logged as waste 3 times in August due to being "Broken".',
          'Total financial risk in current stock is ₹1,120.'
        ],
        hypotheses: [
          'Prep cooks may be using excessive pressure when unpacking dried noodle bundles.',
          'Supplier packaging might be brittle or damaged during transit.'
        ],
        recommended_interventions: [
          {
            intervention_id: 'act_1',
            action_type: 'RECIPE_AUDIT',
            title: 'Brief Prep Staff on Handling',
            details: 'Schedule a 5-minute training on safely unpacking noodles to prevent breakage.',
            expected_impact_inr: 850.0,
            feasibility_rating: 'High'
          },
          {
            intervention_id: 'act_2',
            action_type: 'REDUCE_PURCHASE_ORDER',
            title: 'Contact Supplier regarding Packaging',
            details: 'Request extra bubble wrap or switch to a less brittle brand.',
            expected_impact_inr: 1120.0,
            feasibility_rating: 'Medium'
          }
        ]
      });
      setInvestigating(false);
    }, 2000);
  };

  return (
    <div className="p-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-slate-800">Surplus & Waste Records</h1>
        <button className="bg-rose-600 text-white px-4 py-2 rounded-md hover:bg-rose-700 flex items-center text-sm font-medium transition-colors">
          <Trash2 className="h-4 w-4 mr-2" />
          Log Waste
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <div className="lg:col-span-2 bg-white rounded-lg shadow-sm border border-slate-200 h-fit">
          <div className="p-4 border-b border-slate-200 flex justify-between items-center">
            <h2 className="text-lg font-semibold text-slate-800">Recent Waste Logs</h2>
            <div className="flex gap-2">
              <button className="p-2 text-slate-400 hover:text-slate-600 rounded bg-slate-50 border border-slate-200"><Filter className="w-4 h-4"/></button>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-600">
              <thead className="bg-slate-50 text-slate-700 border-b border-slate-200">
                <tr>
                  <th className="px-6 py-3 font-semibold">Date</th>
                  <th className="px-6 py-3 font-semibold">Item</th>
                  <th className="px-6 py-3 font-semibold">Qty</th>
                  <th className="px-6 py-3 font-semibold">Reason</th>
                  <th className="px-6 py-3 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {wasteLogs.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-50">
                    <td className="px-6 py-4 whitespace-nowrap">{log.date}</td>
                    <td className="px-6 py-4 font-medium text-slate-900">{log.item_name}</td>
                    <td className="px-6 py-4">{log.quantity} {log.unit}</td>
                    <td className="px-6 py-4">
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-800">
                        {log.reason}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button 
                        onClick={handleInvestigate}
                        className="text-indigo-600 hover:text-indigo-800 font-medium text-xs flex items-center justify-end w-full"
                      >
                        <Sparkles className="w-3 h-3 mr-1" />
                        Analyze Risk
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-slate-200 p-0 flex flex-col h-full overflow-hidden">
          <div className="p-4 bg-indigo-50 border-b border-indigo-100 flex items-center">
            <Sparkles className="w-5 h-5 text-indigo-600 mr-2" />
            <h2 className="text-lg font-semibold text-indigo-900">Agentic Investigation</h2>
          </div>
          
          <div className="p-6 flex-1 overflow-y-auto">
            {!investigationResult && !investigating ? (
              <div className="h-full flex flex-col items-center justify-center text-center">
                <div className="w-12 h-12 bg-indigo-100 text-indigo-600 rounded-full flex items-center justify-center mb-3">
                  <Search className="w-6 h-6" />
                </div>
                <h3 className="font-medium text-slate-900 mb-1">No Active Investigations</h3>
                <p className="text-sm text-slate-500 mb-4">Click "Analyze Risk" on a high-waste item to run a Gemini root-cause analysis.</p>
              </div>
            ) : investigating ? (
              <div className="h-full flex flex-col items-center justify-center text-center">
                <div className="animate-spin w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full mb-4"></div>
                <p className="text-sm font-medium text-indigo-600">Gemini is calling tools & querying history...</p>
              </div>
            ) : (
              <div className="space-y-6 animate-in fade-in duration-500">
                <div>
                  <h3 className="font-bold text-slate-800 mb-2">Target: {investigationResult.target_item_name}</h3>
                  <p className="text-sm text-slate-600">{investigationResult.investigation_summary}</p>
                </div>
                
                <div className="bg-slate-50 p-4 rounded-lg border border-slate-200">
                  <h4 className="text-sm font-semibold text-slate-800 mb-2 flex items-center">
                    <CheckCircle className="w-4 h-4 text-emerald-600 mr-2" />
                    Verified Facts
                  </h4>
                  <ul className="list-disc list-inside text-sm text-slate-600 space-y-1">
                    {investigationResult.verified_facts.map((fact: string, idx: number) => (
                      <li key={idx}>{fact}</li>
                    ))}
                  </ul>
                </div>
                
                <div className="bg-amber-50 p-4 rounded-lg border border-amber-200">
                  <h4 className="text-sm font-semibold text-amber-900 mb-2 flex items-center">
                    <AlertTriangle className="w-4 h-4 text-amber-600 mr-2" />
                    AI Hypotheses
                  </h4>
                  <ul className="list-disc list-inside text-sm text-amber-800 space-y-1">
                    {investigationResult.hypotheses.map((hyp: string, idx: number) => (
                      <li key={idx}>{hyp}</li>
                    ))}
                  </ul>
                </div>

                <div>
                  <h4 className="text-sm font-semibold text-slate-800 mb-3">Proposed Interventions</h4>
                  <div className="space-y-3">
                    {investigationResult.recommended_interventions.map((intervention: any) => (
                      <div key={intervention.intervention_id} className="border border-slate-200 rounded-lg p-3 hover:border-indigo-300 transition-colors cursor-pointer">
                        <div className="flex justify-between items-start mb-1">
                          <span className="font-medium text-sm text-slate-900">{intervention.title}</span>
                          <span className="px-2 py-0.5 rounded text-[10px] font-medium uppercase tracking-wider bg-indigo-100 text-indigo-800">
                            {intervention.action_type}
                          </span>
                        </div>
                        <p className="text-xs text-slate-500 mb-3">{intervention.details}</p>
                        <button className="w-full bg-slate-800 text-white text-xs font-medium py-1.5 rounded hover:bg-slate-700">
                          Approve Action
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
