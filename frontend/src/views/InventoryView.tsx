import { useState, useEffect } from 'react';
import { Plus, Search, AlertTriangle, Package, Trash2, ArrowUpRight, ArrowDownRight } from 'lucide-react';

export default function InventoryView() {
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // In a real implementation, we fetch from API. 
  // For demo, we will simulate a fetch delay and show demo data.
  useEffect(() => {
    setTimeout(() => {
      setItems([
        { id: '1', item_name: 'Chinese Noodles 10mm', category: 'Dry Pantry', total_current_quantity: 4.5, base_unit: 'kg', status: 'in_stock' },
        { id: '2', item_name: 'Chicken Leg', category: 'Meat & Poultry', total_current_quantity: 1.2, base_unit: 'kg', status: 'reorder_recommended' },
        { id: '3', item_name: 'Banana Yellow', category: 'Produce', total_current_quantity: 12, base_unit: 'piece', status: 'overstock_risk' },
      ]);
      setLoading(false);
    }, 500);
  }, []);

  return (
    <div className="p-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-slate-800">Inventory Management</h1>
        <button className="bg-restaurant-primary text-white px-4 py-2 rounded-md hover:bg-emerald-700 flex items-center text-sm font-medium transition-colors">
          <Plus className="h-4 w-4 mr-2" />
          Add Item
        </button>
      </div>

      <div className="bg-white rounded-lg shadow-sm border border-slate-200 mb-6">
        <div className="p-4 border-b border-slate-200 flex flex-col sm:flex-row gap-4 justify-between items-center">
          <div className="relative w-full sm:w-96">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 h-4 w-4" />
            <input 
              type="text" 
              placeholder="Search inventory..." 
              className="pl-9 pr-4 py-2 w-full border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-restaurant-primary focus:border-transparent"
            />
          </div>
          <div className="flex gap-2 w-full sm:w-auto">
            <select className="border border-slate-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-restaurant-primary">
              <option>All Categories</option>
              <option>Produce</option>
              <option>Meat & Poultry</option>
              <option>Dry Pantry</option>
            </select>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-600">
            <thead className="bg-slate-50 text-slate-700 border-b border-slate-200">
              <tr>
                <th className="px-6 py-3 font-semibold">Item Name</th>
                <th className="px-6 py-3 font-semibold">Category</th>
                <th className="px-6 py-3 font-semibold text-right">Quantity</th>
                <th className="px-6 py-3 font-semibold">Status</th>
                <th className="px-6 py-3 font-semibold text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {loading ? (
                <tr>
                  <td colSpan={5} className="px-6 py-8 text-center text-slate-500">Loading inventory...</td>
                </tr>
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-8 text-center text-slate-500">No inventory items found.</td>
                </tr>
              ) : (
                items.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-50">
                    <td className="px-6 py-4 font-medium text-slate-900">{item.item_name}</td>
                    <td className="px-6 py-4">{item.category}</td>
                    <td className="px-6 py-4 text-right font-medium">
                      {item.total_current_quantity} {item.base_unit}
                    </td>
                    <td className="px-6 py-4">
                      {item.status === 'in_stock' && <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-100 text-emerald-800">In Stock</span>}
                      {item.status === 'reorder_recommended' && <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-800"><AlertTriangle className="w-3 h-3 mr-1"/> Reorder</span>}
                      {item.status === 'overstock_risk' && <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-rose-100 text-rose-800">Overstock</span>}
                    </td>
                    <td className="px-6 py-4 text-right space-x-2 flex justify-end">
                      <button title="Log Usage" className="p-1.5 text-slate-400 hover:text-restaurant-primary hover:bg-slate-100 rounded">
                        <ArrowDownRight className="w-4 h-4" />
                      </button>
                      <button title="Log Receipt" className="p-1.5 text-slate-400 hover:text-emerald-600 hover:bg-slate-100 rounded">
                        <ArrowUpRight className="w-4 h-4" />
                      </button>
                      <button title="Log Waste" className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-slate-100 rounded">
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
