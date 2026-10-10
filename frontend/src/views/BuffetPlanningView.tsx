import { useState } from 'react';
import { Calculator, ChefHat, AlertCircle, Calendar } from 'lucide-react';

export default function BuffetPlanningView() {
  const [covers, setCovers] = useState(120);
  const [buffer, setBuffer] = useState(10);
  const [calculated, setCalculated] = useState(false);

  const [plan, setPlan] = useState<any[]>([]);

  const handleCalculate = () => {
    // In production, this hits /api/planning/buffet
    setPlan([
      {
        dish_name: 'Pan Asian Fried Rice',
        base_requirement: covers * 0.2, // 200g per person
        target_production: covers * 0.2 * (1 + buffer / 100),
        recommended_batches: Math.ceil((covers * 0.2 * (1 + buffer / 100)) / 5),
        actual_planned: Math.ceil((covers * 0.2 * (1 + buffer / 100)) / 5) * 5,
        predicted_surplus: (Math.ceil((covers * 0.2 * (1 + buffer / 100)) / 5) * 5) - (covers * 0.2),
        unit: 'kg'
      },
      {
        dish_name: 'Thai Green Curry',
        base_requirement: covers * 0.25, // 250ml per person
        target_production: covers * 0.25 * (1 + buffer / 100),
        recommended_batches: Math.ceil((covers * 0.25 * (1 + buffer / 100)) / 8),
        actual_planned: Math.ceil((covers * 0.25 * (1 + buffer / 100)) / 8) * 8,
        predicted_surplus: (Math.ceil((covers * 0.25 * (1 + buffer / 100)) / 8) * 8) - (covers * 0.25),
        unit: 'L'
      }
    ]);
    setCalculated(true);
  };

  return (
    <div className="p-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-slate-800">Buffet Production Planning</h1>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Settings Panel */}
        <div className="bg-white rounded-lg shadow-sm border border-slate-200 p-6 flex flex-col">
          <h2 className="text-lg font-semibold text-slate-800 mb-4 flex items-center">
            <Calendar className="w-5 h-5 mr-2 text-restaurant-secondary" />
            Service Parameters
          </h2>
          
          <div className="space-y-4 flex-1">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Expected Covers (Guests)</label>
              <input 
                type="number" 
                value={covers}
                onChange={(e) => setCovers(Number(e.target.value))}
                className="w-full border border-slate-300 rounded-md px-3 py-2 focus:ring-restaurant-primary focus:border-restaurant-primary"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Safety Buffer (%)</label>
              <input 
                type="number" 
                value={buffer}
                onChange={(e) => setBuffer(Number(e.target.value))}
                className="w-full border border-slate-300 rounded-md px-3 py-2 focus:ring-restaurant-primary focus:border-restaurant-primary"
              />
              <p className="text-xs text-slate-500 mt-1">Prevents mid-service shortages.</p>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Meal Period</label>
              <select className="w-full border border-slate-300 rounded-md px-3 py-2 focus:ring-restaurant-primary focus:border-restaurant-primary">
                <option>Dinner Buffet</option>
                <option>Sunday Brunch</option>
              </select>
            </div>
          </div>
          
          <button 
            onClick={handleCalculate}
            className="mt-6 w-full bg-restaurant-primary text-white py-2 rounded-md hover:bg-emerald-700 font-medium transition-colors flex justify-center items-center">
            <Calculator className="w-4 h-4 mr-2" />
            Calculate Batches
          </button>
        </div>

        {/* Results Panel */}
        <div className="lg:col-span-3">
          {!calculated ? (
            <div className="h-full min-h-[400px] border-2 border-dashed border-slate-200 rounded-lg flex flex-col items-center justify-center text-center p-8 bg-slate-50">
              <ChefHat className="w-12 h-12 text-slate-300 mb-4" />
              <h3 className="text-lg font-medium text-slate-900 mb-2">No Plan Generated</h3>
              <p className="text-slate-500 max-w-md">Enter your expected covers and safety buffer on the left, then calculate the optimal batch production for this service.</p>
            </div>
          ) : (
            <div className="bg-white rounded-lg shadow-sm border border-slate-200 overflow-hidden">
              <div className="p-4 border-b border-slate-200 bg-slate-50 flex justify-between items-center">
                <h3 className="font-semibold text-slate-800">Recommended Production Schedule</h3>
                <span className="text-sm text-slate-500">Based on {covers} covers</span>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm text-slate-600">
                  <thead className="bg-white text-slate-700 border-b border-slate-200">
                    <tr>
                      <th className="px-6 py-3 font-semibold">Menu Item</th>
                      <th className="px-6 py-3 font-semibold text-right">Base Demand</th>
                      <th className="px-6 py-3 font-semibold text-right text-restaurant-primary">Cook Batches</th>
                      <th className="px-6 py-3 font-semibold text-right">Total Prep</th>
                      <th className="px-6 py-3 font-semibold text-right text-amber-600">Predicted Surplus</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200">
                    {plan.map((item, idx) => (
                      <tr key={idx} className="hover:bg-slate-50">
                        <td className="px-6 py-4 font-medium text-slate-900">{item.dish_name}</td>
                        <td className="px-6 py-4 text-right">{item.base_requirement.toFixed(1)} {item.unit}</td>
                        <td className="px-6 py-4 text-right font-bold text-restaurant-primary">
                          {item.recommended_batches} <span className="text-xs font-normal text-slate-500">batches</span>
                        </td>
                        <td className="px-6 py-4 text-right font-medium text-slate-700">
                          {item.actual_planned.toFixed(1)} {item.unit}
                        </td>
                        <td className="px-6 py-4 text-right">
                          <span className="inline-flex items-center text-amber-600 font-medium">
                            {item.predicted_surplus > 0 && <AlertCircle className="w-3 h-3 mr-1" />}
                            {item.predicted_surplus.toFixed(1)} {item.unit}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="p-4 bg-slate-50 border-t border-slate-200 flex justify-end">
                <button className="bg-slate-800 text-white px-4 py-2 rounded-md hover:bg-slate-900 font-medium text-sm transition-colors">
                  Approve & Send to Kitchen
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
