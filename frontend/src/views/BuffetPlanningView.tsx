import { useState } from 'react';
import type { FormEvent } from 'react';
import { AlertCircle, Calculator, Calendar, ChefHat } from 'lucide-react';
import { apiRequest, type BuffetRecommendation } from '../lib/api';

const fieldClass = 'w-full rounded-md border border-slate-300 px-3 py-2 text-sm';

export default function BuffetPlanningView() {
  const [dishName, setDishName] = useState('');
  const [covers, setCovers] = useState('120');
  const [buffer, setBuffer] = useState('10');
  const [consumption, setConsumption] = useState('');
  const [batchYield, setBatchYield] = useState('');
  const [unit, setUnit] = useState('kg');
  const [plan, setPlan] = useState<BuffetRecommendation | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const calculate = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLoading(true);
    setError('');
    try {
      const result = await apiRequest<BuffetRecommendation>('/api/planning/buffet', {
        method: 'POST',
        body: JSON.stringify({
          dish_name: dishName,
          expected_covers: Number(covers),
          historical_consumption_per_cover: Number(consumption),
          buffer_percentage: Number(buffer),
          standard_batch_yield: Number(batchYield),
          unit,
        }),
      });
      setPlan(result);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not calculate the buffet plan.');
    } finally {
      setLoading(false);
    }
  };

  return <div className="p-8">
    <div className="mb-6"><h1 className="text-2xl font-bold text-slate-800">Buffet Production Planning</h1></div>
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-4">
      <form onSubmit={calculate} className="flex h-fit flex-col rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="mb-4 flex items-center text-lg font-semibold text-slate-800"><Calendar className="mr-2 h-5 w-5 text-restaurant-secondary" />Service Parameters</h2>
        <div className="flex-1 space-y-4">
          <label className="block text-sm font-medium text-slate-700">Dish name<input required value={dishName} onChange={(e) => setDishName(e.target.value)} className={`${fieldClass} mt-1`} placeholder="e.g. Vegetable pulao" /></label>
          <label className="block text-sm font-medium text-slate-700">Expected covers<input required type="number" min="1" value={covers} onChange={(e) => setCovers(e.target.value)} className={`${fieldClass} mt-1`} /></label>
          <label className="block text-sm font-medium text-slate-700">Historical consumption per cover<input required type="number" min="0.001" step="any" value={consumption} onChange={(e) => setConsumption(e.target.value)} className={`${fieldClass} mt-1`} /></label>
          <label className="block text-sm font-medium text-slate-700">Safety buffer (%)<input required type="number" min="0" step="any" value={buffer} onChange={(e) => setBuffer(e.target.value)} className={`${fieldClass} mt-1`} /></label>
          <label className="block text-sm font-medium text-slate-700">Standard batch yield<input required type="number" min="0.001" step="any" value={batchYield} onChange={(e) => setBatchYield(e.target.value)} className={`${fieldClass} mt-1`} /></label>
          <label className="block text-sm font-medium text-slate-700">Measurement unit<input required value={unit} onChange={(e) => setUnit(e.target.value)} className={`${fieldClass} mt-1`} placeholder="kg, L, portions…" /></label>
        </div>
        {error && <p role="alert" className="mt-4 text-sm text-rose-700">{error}</p>}
        <button disabled={loading} className="mt-6 flex w-full items-center justify-center rounded-md bg-restaurant-primary py-2 font-medium text-white disabled:opacity-50"><Calculator className="mr-2 h-4 w-4" />{loading ? 'Calculating…' : 'Calculate Batches'}</button>
      </form>

      <div className="lg:col-span-3">
        {!plan ? <div className="flex min-h-[400px] flex-col items-center justify-center rounded-lg border-2 border-dashed border-slate-200 bg-slate-50 p-8 text-center">
          <ChefHat className="mb-4 h-12 w-12 text-slate-300" /><h3 className="mb-2 text-lg font-medium text-slate-900">No Plan Generated</h3><p className="max-w-md text-slate-500">Enter actual consumption and batch yield values, then ask the backend to calculate the production plan.</p>
        </div> : <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
          <div className="flex items-center justify-between border-b bg-slate-50 p-4"><h3 className="font-semibold text-slate-800">Recommended Production Schedule</h3><span className="text-sm text-slate-500">For {plan.expected_covers} covers</span></div>
          <div className="grid grid-cols-1 gap-4 p-6 sm:grid-cols-2">
            <div><p className="text-sm text-slate-500">Dish</p><p className="font-semibold">{plan.dish_name}</p></div>
            <div><p className="text-sm text-slate-500">Base demand</p><p className="font-semibold">{plan.base_requirement.toFixed(2)} {plan.unit}</p></div>
            <div><p className="text-sm text-slate-500">Target production</p><p className="font-semibold">{plan.target_production.toFixed(2)} {plan.unit}</p></div>
            <div><p className="text-sm text-slate-500">Recommended batches</p><p className="font-semibold">{plan.recommended_batches}</p></div>
            <div><p className="text-sm text-slate-500">Planned production</p><p className="font-semibold">{plan.actual_planned_production.toFixed(2)} {plan.unit}</p></div>
            <div><p className="text-sm text-slate-500">Predicted surplus</p><p className="flex items-center font-semibold text-amber-700"><AlertCircle className="mr-1 h-4 w-4" />{plan.predicted_surplus_portions.toFixed(2)} {plan.unit}</p></div>
          </div>
          <div className="border-t bg-slate-50 p-4 text-sm text-slate-600"><strong>Reasoning:</strong> {plan.reasoning} <span className="ml-2 text-xs">Confidence: {plan.confidence}</span></div>
        </div>}
      </div>
    </div>
  </div>;
}
