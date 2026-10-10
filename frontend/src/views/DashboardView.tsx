import { useState, useEffect } from 'react';
import { PackageX, AlertTriangle, TrendingDown, Leaf, Activity } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export default function DashboardView() {
  const [metrics, setMetrics] = useState<any>(null);

  useEffect(() => {
    // Simulate fetching from /api/analytics/dashboard
    setTimeout(() => {
      setMetrics({
        inventory_risk_items: 3,
        pending_interventions: 1,
        total_waste_week_kg: 14.2,
        waste_trend_percentage: -12.5,
        financial_savings_inr: 12500,
        meals_donated: 145
      });
    }, 500);
  }, []);

  const chartData = [
    { day: 'Mon', waste: 4.2 },
    { day: 'Tue', waste: 3.8 },
    { day: 'Wed', waste: 5.1 },
    { day: 'Thu', waste: 3.2 },
    { day: 'Fri', waste: 2.8 },
    { day: 'Sat', waste: 4.5 },
    { day: 'Sun', waste: 2.1 }
  ];

  if (!metrics) return <div className="p-8 flex items-center justify-center h-full text-slate-500">Loading dashboard...</div>;

  return (
    <div className="p-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-slate-800">Operations Dashboard</h1>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="bg-white p-6 rounded-lg shadow-sm border border-slate-200">
          <div className="flex justify-between items-start mb-2">
            <h3 className="text-sm font-medium text-slate-500">Financial Savings</h3>
            <div className="p-2 bg-emerald-100 rounded-lg"><TrendingDown className="w-4 h-4 text-emerald-600" /></div>
          </div>
          <p className="text-2xl font-bold text-slate-800">₹{metrics.financial_savings_inr.toLocaleString()}</p>
          <p className="text-xs text-emerald-600 mt-1 font-medium">This month</p>
        </div>
        
        <div className="bg-white p-6 rounded-lg shadow-sm border border-slate-200">
          <div className="flex justify-between items-start mb-2">
            <h3 className="text-sm font-medium text-slate-500">Total Waste (Week)</h3>
            <div className="p-2 bg-rose-100 rounded-lg"><PackageX className="w-4 h-4 text-rose-600" /></div>
          </div>
          <p className="text-2xl font-bold text-slate-800">{metrics.total_waste_week_kg} kg</p>
          <p className="text-xs text-emerald-600 mt-1 font-medium">{Math.abs(metrics.waste_trend_percentage)}% reduction</p>
        </div>
        
        <div className="bg-white p-6 rounded-lg shadow-sm border border-slate-200">
          <div className="flex justify-between items-start mb-2">
            <h3 className="text-sm font-medium text-slate-500">Pending Interventions</h3>
            <div className="p-2 bg-indigo-100 rounded-lg"><AlertTriangle className="w-4 h-4 text-indigo-600" /></div>
          </div>
          <p className="text-2xl font-bold text-slate-800">{metrics.pending_interventions}</p>
          <p className="text-xs text-slate-500 mt-1">Requires manager approval</p>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-sm border border-slate-200">
          <div className="flex justify-between items-start mb-2">
            <h3 className="text-sm font-medium text-slate-500">Meals Donated</h3>
            <div className="p-2 bg-amber-100 rounded-lg"><Leaf className="w-4 h-4 text-amber-600" /></div>
          </div>
          <p className="text-2xl font-bold text-slate-800">{metrics.meals_donated}</p>
          <p className="text-xs text-slate-500 mt-1">Year to date</p>
        </div>
      </div>
      
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-white rounded-lg shadow-sm border border-slate-200 p-6">
          <h2 className="text-lg font-semibold text-slate-800 mb-6 flex items-center">
            <Activity className="w-5 h-5 mr-2 text-slate-400" />
            Waste Generation Trend (7 Days)
          </h2>
          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorWaste" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#f43f5e" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                <XAxis dataKey="day" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#64748b' }} dy={10} />
                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#64748b' }} />
                <Tooltip 
                  contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                  formatter={(value: number) => [`${value} kg`, 'Waste Logged']}
                />
                <Area type="monotone" dataKey="waste" stroke="#f43f5e" strokeWidth={3} fillOpacity={1} fill="url(#colorWaste)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-slate-200 p-6 flex flex-col">
          <h2 className="text-lg font-semibold text-slate-800 mb-4">Quick Actions</h2>
          <div className="space-y-3 flex-1">
            <button className="w-full text-left px-4 py-3 rounded-md border border-slate-200 hover:border-restaurant-primary hover:bg-emerald-50 transition-colors group">
              <span className="block text-sm font-medium text-slate-800 group-hover:text-restaurant-primary">Upload Physical Forms</span>
              <span className="block text-xs text-slate-500">Scan wastage and staff meal sheets</span>
            </button>
            <button className="w-full text-left px-4 py-3 rounded-md border border-slate-200 hover:border-indigo-400 hover:bg-indigo-50 transition-colors group">
              <span className="block text-sm font-medium text-slate-800 group-hover:text-indigo-600">Review AI Interventions</span>
              <span className="block text-xs text-slate-500">1 pending action requires approval</span>
            </button>
            <button className="w-full text-left px-4 py-3 rounded-md border border-slate-200 hover:border-amber-500 hover:bg-amber-50 transition-colors group">
              <span className="block text-sm font-medium text-slate-800 group-hover:text-amber-600">Find Donation Match</span>
              <span className="block text-xs text-slate-500">Route safe surplus to verified NGOs</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
