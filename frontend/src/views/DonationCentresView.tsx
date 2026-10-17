import { useState } from 'react';
import type { FormEvent } from 'react';
import { HeartHandshake, MapPin, Search } from 'lucide-react';
import { apiRequest, type DonationCentreSuggestion } from '../lib/api';

const fieldClass = 'w-full rounded-md border border-slate-300 px-3 py-2 text-sm';

export default function DonationCentresView() {
  const [keywords, setKeywords] = useState('');
  const [suggestions, setSuggestions] = useState<DonationCentreSuggestion[]>([]);
  const [searched, setSearched] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState('');

  const search = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsSearching(true);
    setError('');
    setSearched(false);
    try {
      const result = await apiRequest<DonationCentreSuggestion[]>('/api/donations/search', {
        method: 'POST',
        body: JSON.stringify({ query: keywords.trim() }),
      });
      setSuggestions(result);
      setSearched(true);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not search with Gemini.');
    } finally {
      setIsSearching(false);
    }
  };

  return <div className="p-8">
    <div className="mb-6">
      <h1 className="text-2xl font-bold text-slate-800">Donation Centre Search</h1>
      <p className="mt-1 text-sm text-slate-500">Ask Gemini for nearby donation centres from its existing knowledge.</p>
    </div>
    {error && <div role="alert" className="mb-4 rounded-md border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">{error}</div>}
    <form onSubmit={search} className="mb-6 flex max-w-3xl gap-3 rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <label className="flex-1 text-sm font-medium text-slate-700">
        Donation centre and location
        <input
          required
          minLength={3}
          maxLength={200}
          value={keywords}
          onChange={(event) => setKeywords(event.target.value)}
          className={`${fieldClass} mt-1`}
          placeholder="food donation centres near Kharadi, Pune"
        />
      </label>
      <button disabled={isSearching} className="mt-6 flex items-center self-start rounded-md bg-restaurant-primary px-4 py-2 text-sm font-medium text-white disabled:opacity-50">
        <Search className="mr-2 h-4 w-4" />{isSearching ? 'Asking Gemini…' : 'Ask Gemini'}
      </button>
    </form>

    {isSearching
      ? <div role="status" className="rounded-lg border border-slate-200 bg-slate-50 p-12 text-center text-slate-600">Asking Gemini for suggestions…</div>
      : !searched
        ? <div className="rounded-lg border-2 border-dashed border-slate-200 bg-slate-50 p-12 text-center">
          <HeartHandshake className="mx-auto mb-4 h-12 w-12 text-slate-300" />
          <p className="font-medium text-slate-800">Find donation centres with Gemini</p>
          <p className="mt-1 text-sm text-slate-500">Enter a location. Gemini will omit centres it cannot confidently identify.</p>
        </div>
        : suggestions.length === 0
          ? <div className="rounded-lg border border-slate-200 bg-white p-8 text-center text-slate-500">Gemini could not confidently identify any donation centres for this location.</div>
          : <section className="max-w-3xl space-y-3">
            <h2 className="text-lg font-semibold text-slate-800">Gemini suggestions</h2>
            {suggestions.map((suggestion, index) => <article key={`${suggestion.name}-${index}`} className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
              <div className="mb-2 flex items-start gap-3">
                <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-emerald-50 text-sm font-semibold text-emerald-800">{index + 1}</span>
                <div className="min-w-0 flex-1">
                  <h3 className="font-semibold text-slate-900">{suggestion.name}</h3>
                  <p className="mt-1 flex items-start text-sm text-slate-600"><MapPin className="mr-1.5 mt-0.5 h-4 w-4 shrink-0 text-slate-400" />{suggestion.location}</p>
                </div>
              </div>
            </article>)}
          </section>}
    <p className="mt-8 text-xs text-slate-500">Live Google Maps data will be added in a future update.</p>
  </div>;
}
