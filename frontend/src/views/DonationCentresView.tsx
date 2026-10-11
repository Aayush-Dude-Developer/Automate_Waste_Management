import { useState } from 'react';
import type { FormEvent } from 'react';
import { CheckCircle2, FileText, HeartHandshake, MapPin, Sparkles, ThermometerSnowflake, Truck, XCircle } from 'lucide-react';
import { apiRequest, type DonationMatch } from '../lib/api';

const fieldClass = 'w-full rounded-md border border-slate-300 px-3 py-2 text-sm';

export default function DonationCentresView() {
  const [itemName, setItemName] = useState('');
  const [quantity, setQuantity] = useState('');
  const [isCooked, setIsCooked] = useState(true);
  const [requiresColdChain, setRequiresColdChain] = useState(false);
  const [useAI, setUseAI] = useState(false);
  const [matches, setMatches] = useState<DonationMatch[]>([]);
  const [searched, setSearched] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState('');
  const [selectedMatch, setSelectedMatch] = useState<DonationMatch | null>(null);
  const [driverName, setDriverName] = useState('');
  const [temperature, setTemperature] = useState('');
  const [handoverBusy, setHandoverBusy] = useState(false);
  const [notice, setNotice] = useState('');

  const handleMatch = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsSearching(true);
    setError('');
    setNotice('');
    setSearched(false);
    try {
      const query = new URLSearchParams({ use_ai: String(useAI), location_name: 'Pune' });
      const result = await apiRequest<DonationMatch[]>(`/api/donations/match?${query}`, {
        method: 'POST',
        body: JSON.stringify({ item_name: itemName, quantity_kg: Number(quantity), is_cooked: isCooked, requires_cold_chain: requiresColdChain }),
      });
      setMatches(result);
      setSearched(true);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not find donation matches.');
    } finally {
      setIsSearching(false);
    }
  };

  const saveHandover = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selectedMatch) return;
    setHandoverBusy(true);
    setError('');
    try {
      await apiRequest('/api/donations/handover', {
        method: 'POST',
        body: JSON.stringify({
          item_name: itemName,
          quantity_kg: Number(quantity),
          centre_id: selectedMatch.centre.id,
          driver_name: driverName || null,
          temperature_at_handover: temperature ? Number(temperature) : null,
          notes: null,
        }),
      });
      setSelectedMatch(null);
      setDriverName('');
      setTemperature('');
      setNotice('Handover record saved.');
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not save handover.');
    } finally {
      setHandoverBusy(false);
    }
  };

  return <div className="p-8">
    <div className="mb-6"><h1 className="text-2xl font-bold text-slate-800">Donation Centre Matching</h1></div>
    {error && <div role="alert" className="mb-4 rounded-md border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">{error}</div>}
    {notice && <div role="status" className="mb-4 rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">{notice}</div>}
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
      <form onSubmit={handleMatch} className="flex h-fit flex-col rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="mb-4 text-lg font-semibold text-slate-800">Surplus Details</h2>
        <div className="space-y-4">
          <label className="block text-sm font-medium text-slate-700">Item name<input required value={itemName} onChange={(e) => setItemName(e.target.value)} className={`${fieldClass} mt-1`} /></label>
          <label className="block text-sm font-medium text-slate-700">Quantity (kg)<input required type="number" min="0.01" step="any" value={quantity} onChange={(e) => setQuantity(e.target.value)} className={`${fieldClass} mt-1`} /></label>
          <label className="flex items-center gap-2 text-sm text-slate-700"><input type="checkbox" checked={isCooked} onChange={(e) => setIsCooked(e.target.checked)} />Prepared/cooked food</label>
          <label className="flex items-center gap-2 text-sm text-slate-700"><input type="checkbox" checked={requiresColdChain} onChange={(e) => setRequiresColdChain(e.target.checked)} /><ThermometerSnowflake className="h-4 w-4 text-sky-500" />Requires strict cold-chain</label>
        </div>
        <div className="my-5 border-t pt-4">
          <label className="flex items-center justify-between text-sm font-medium text-indigo-900"><span className="flex items-center"><Sparkles className="mr-2 h-4 w-4 text-indigo-600" />AI discovery</span><input type="checkbox" checked={useAI} onChange={(e) => setUseAI(e.target.checked)} /></label>
          <p className="mt-2 text-xs text-slate-500">AI-sourced centre details are unverified and must be independently checked. The backend may return its configured fallback dataset.</p>
        </div>
        <button disabled={isSearching} className="flex w-full items-center justify-center rounded-md bg-restaurant-primary py-2 font-medium text-white disabled:opacity-50">{isSearching ? 'Searching…' : <><HeartHandshake className="mr-2 h-4 w-4" />Find Matches</>}</button>
      </form>

      <div className="space-y-4 lg:col-span-2">
        {isSearching ? <div className="rounded-lg border border-slate-200 bg-slate-50 p-12 text-center text-slate-600">Requesting matches from the backend…</div>
          : !searched ? <div className="rounded-lg border-2 border-dashed border-slate-200 bg-slate-50 p-12 text-center"><HeartHandshake className="mx-auto mb-4 h-12 w-12 text-slate-300" /><p className="font-medium text-slate-800">Ready to find a match</p><p className="mt-1 text-sm text-slate-500">Enter surplus details to request eligible centres.</p></div>
            : matches.length === 0 ? <div className="rounded-lg border border-slate-200 bg-white p-8 text-center text-slate-500">No centres matched this surplus.</div>
              : matches.map((match) => <article key={match.centre.id} className={`rounded-lg border bg-white p-6 shadow-sm ${match.is_eligible ? 'border-emerald-200' : 'border-slate-200 opacity-75'}`}>
                <div className="mb-2 flex flex-wrap items-center gap-2"><h3 className="text-lg font-bold text-slate-900">{match.centre.name}</h3>{match.is_eligible ? <span className="flex items-center rounded bg-emerald-100 px-2 py-0.5 text-xs text-emerald-800"><CheckCircle2 className="mr-1 h-3 w-3" />Eligible</span> : <span className="flex items-center rounded bg-rose-100 px-2 py-0.5 text-xs text-rose-800"><XCircle className="mr-1 h-3 w-3" />Not eligible</span>}{!match.centre.verified && <span className="rounded bg-indigo-100 px-2 py-0.5 text-xs text-indigo-800">Unverified</span>}</div>
                <div className="space-y-2 text-sm text-slate-600"><p className="flex items-center"><MapPin className="mr-2 h-4 w-4 text-slate-400" />{match.centre.address} · {match.distance_km} km</p><p className="flex items-center"><Truck className="mr-2 h-4 w-4 text-slate-400" />{match.centre.pickup_service_available ? 'Pickup available' : 'Drop-off required'} · Score {match.match_score}</p>{match.eligibility_notes.map((note, index) => <p key={index}>{note}</p>)}</div>
                {match.is_eligible && <button onClick={() => setSelectedMatch(match)} className="mt-4 flex items-center rounded-md bg-restaurant-secondary px-4 py-2 text-sm font-medium text-white"><FileText className="mr-2 h-4 w-4" />Record Handover</button>}
              </article>)}
      </div>
    </div>
    {selectedMatch && <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4"><form onSubmit={saveHandover} className="w-full max-w-md rounded-lg bg-white p-6">
      <h2 className="mb-4 text-xl font-bold text-slate-800">Record Handover</h2><p className="mb-4 text-sm text-slate-600">Recipient: {selectedMatch.centre.name} · {quantity} kg {itemName}</p>
      <label className="mb-3 block text-sm">Driver / receiver<input value={driverName} onChange={(e) => setDriverName(e.target.value)} className={`${fieldClass} mt-1`} /></label>
      <label className="mb-5 block text-sm">Temperature at handover (°C)<input type="number" step="any" value={temperature} onChange={(e) => setTemperature(e.target.value)} className={`${fieldClass} mt-1`} /></label>
      <div className="flex justify-end gap-3"><button type="button" onClick={() => setSelectedMatch(null)} className="rounded px-4 py-2 text-sm text-slate-600 hover:bg-slate-100">Cancel</button><button disabled={handoverBusy} className="rounded bg-restaurant-primary px-4 py-2 text-sm font-medium text-white disabled:opacity-50">{handoverBusy ? 'Saving…' : 'Confirm Handover'}</button></div>
    </form></div>}
  </div>;
}
