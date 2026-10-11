import { useEffect, useState } from 'react';
import { Activity, AlertTriangle, Leaf, PackageX, TrendingDown } from 'lucide-react';
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { apiRequest, type DashboardMetrics } from '../lib/api';

interface TrendPoint { day: string; waste: number }

export default function DashboardView() {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [trend, setTrend] = useState<TrendPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    Promise.all([
      apiRequest<DashboardMetrics>('/api/analytics/dashboard'),
      apiRequest<TrendPoint[]>('/api/analytics/waste-trend'),
    ]).then(([dashboard, wasteTrend]) => {
      setMetrics(dashboard);
      setTrend(wasteTrend);
      setError('');
    }).catch((cause: unknown) => {
      setError(cause instanceof Error ? cause.message : 'Could not load dashboard data.');
    }).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-8 text-slate-500">Loading dashboard…</div>;
  if (error || !metrics) return <div role="alert" className="m-8 rounded-md border border-rose-200 bg-rose-50 p-4 text-rose-700">{error || 'Dashboard data is unavailable.'}</div>;

  const cards = [
    { title: 'Waste Loss (7 days)', value: `₹${metrics.financial_loss_week_inr.toLocaleString()}`, caption: 'Recorded inventory cost', Icon: TrendingDown, color: 'text-emerald-600 bg-emerald-100' },
    { title: 'Waste (7 days)', value: `${metrics.total_waste_week_kg.toFixed(2)} kg`, caption: `${Math.abs(metrics.waste_trend_percentage).toFixed(1)}% ${metrics.waste_trend_percentage >= 0 ? 'reduction' : 'increase'} vs prior week`, Icon: PackageX, color: 'text-rose-600 bg-rose-100' },
    { title: 'Pending Interventions', value: String(metrics.pending_interventions), caption: 'Requires manager review', Icon: AlertTriangle, color: 'text-indigo-600 bg-indigo-100' },
    { title: 'Donation Handovers', value: String(metrics.donation_handovers), caption: 'Recorded completed handovers', Icon: Leaf, color: 'text-amber-600 bg-amber-100' },
  ];

  return <div className="p-8">
    <div className="mb-6 flex items-center justify-between"><h1 className="text-2xl font-bold text-slate-800">Operations Dashboard</h1></div>
    <div className="mb-8 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
      {cards.map(({ title, value, caption, Icon, color }) => <div key={title} className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <div className="mb-2 flex items-start justify-between"><h2 className="text-sm font-medium text-slate-500">{title}</h2><div className={`rounded-lg p-2 ${color}`}><Icon className="h-4 w-4" /></div></div>
        <p className="text-2xl font-bold text-slate-800">{value}</p><p className="mt-1 text-xs text-slate-500">{caption}</p>
      </div>)}
    </div>
    <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
      <h2 className="mb-6 flex items-center text-lg font-semibold text-slate-800"><Activity className="mr-2 h-5 w-5 text-slate-400" />Waste Generation Trend (7 Days)</h2>
      {trend.length === 0 ? <p className="py-12 text-center text-sm text-slate-500">No waste has been recorded in the last 7 days.</p> :
        <div className="h-72 w-full"><ResponsiveContainer width="100%" height="100%">
          <AreaChart data={trend} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <defs><linearGradient id="colorWaste" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#f43f5e" stopOpacity={0.3} /><stop offset="95%" stopColor="#f43f5e" stopOpacity={0} /></linearGradient></defs>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" /><XAxis dataKey="day" axisLine={false} tickLine={false} /><YAxis axisLine={false} tickLine={false} /><Tooltip formatter={(value) => [`${value ?? 0} kg`, 'Waste logged']} />
            <Area type="monotone" dataKey="waste" stroke="#f43f5e" strokeWidth={3} fillOpacity={1} fill="url(#colorWaste)" />
          </AreaChart>
        </ResponsiveContainer></div>}
    </div>
  </div>;
}
