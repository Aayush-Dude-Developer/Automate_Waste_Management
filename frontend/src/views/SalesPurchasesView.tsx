import { useState, useEffect } from 'react';
import { ShoppingCart, TrendingUp, PackagePlus, AlertTriangle } from 'lucide-react';

export default function SalesPurchasesView() {
  const [recommendations, setRecommendations] = useState<any[]>([]);

  useEffect(() => {
    // Simulated API response from /api/planning/replenishment
    setRecommendations([
      {
        item_name: 'Chicken Leg',
        current_stock: 1.2,
        target_stock_level: 15.0,
        recommended_purchase_quantity: 14.0,
        recommended_packs: 2,
        pack_size: 7,
        unit: 'kg',
        data_quality_status: 'HIGH',
        reasoning: 'Target stock is 15.0 kg based on lead time. On hand is 1.2 kg. Ordering 2 packs of 7 kg yields 14.0 kg.'
      },
      {
        item_name: 'Sona Masoori Rice',
        current_stock: 8.0,
        target_stock_level: 25.0,
        recommended_purchase_quantity: 20.0,
        recommended_packs: 1,
        pack_size: 20,
        unit: 'kg',
        data_quality_status: 'HIGH',
        reasoning: 'Target stock is 25.0 kg. On hand is 8.0 kg. Ordering 1 pack of 20 kg yields 20.0 kg.'
      }
    ]);
  }, []);

  return (
    <div className="p-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-slate-800">Sales & Purchasing</h1>
      </div>

      <div className="bg-white rounded-lg shadow-sm border border-slate-200 mb-8 overflow-hidden">
        <div className="p-4 border-b border-slate-200 flex items-center bg-slate-50">
          <PackagePlus className="w-5 h-5 text-restaurant-secondary mr-2" />
          <h2 className="text-lg font-semibold text-slate-800">Automated Restocking Recommendations</h2>
        </div>
        
        <div className="divide-y divide-slate-200">
          {recommendations.map((rec, idx) => (
            <div key={idx} className="p-6 hover:bg-slate-50 transition-colors flex flex-col md:flex-row gap-6">
              <div className="flex-1">
                <div className="flex items-center mb-2">
                  <h3 className="text-lg font-bold text-slate-900 mr-3">{rec.item_name}</h3>
                  {rec.data_quality_status === 'HIGH' && (
                    <span className="px-2 py-0.5 rounded text-xs font-medium bg-emerald-100 text-emerald-800">High Confidence</span>
                  )}
                </div>
                <p className="text-sm text-slate-600 mb-4">{rec.reasoning}</p>
                <div className="flex gap-6 text-sm">
                  <div>
                    <span className="text-slate-500 block mb-1">Current Stock</span>
                    <span className="font-semibold text-slate-700">{rec.current_stock} {rec.unit}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block mb-1">Target Stock</span>
                    <span className="font-semibold text-slate-700">{rec.target_stock_level} {rec.unit}</span>
                  </div>
                </div>
              </div>
              
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 w-full md:w-64 flex flex-col justify-center items-center text-center">
                <span className="text-sm font-medium text-amber-800 mb-1">Recommended Order</span>
                <span className="text-3xl font-bold text-amber-600 mb-1">{rec.recommended_purchase_quantity} <span className="text-lg">{rec.unit}</span></span>
                <span className="text-xs text-amber-700 mb-4">({rec.recommended_packs} packs of {rec.pack_size}{rec.unit})</span>
                <button className="w-full bg-amber-600 text-white px-4 py-2 rounded-md hover:bg-amber-700 font-medium text-sm transition-colors">
                  Add to Purchase Order
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
