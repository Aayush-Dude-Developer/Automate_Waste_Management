import { useEffect, useState } from 'react';
import { signOut } from 'firebase/auth';
import { firebaseAuth } from '../lib/firebase';
import { apiRequest } from '../lib/api';

interface HealthStatus { status: string; database: string; gemini_ready: boolean }
interface AuthProfile { email: string; restaurant_id: string }

export default function SettingsView() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [profile, setProfile] = useState<AuthProfile | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    Promise.all([
      apiRequest<HealthStatus>('/api/health'),
      apiRequest<AuthProfile>('/api/auth/me'),
    ]).then(([status, user]) => {
      setHealth(status);
      setProfile(user);
    }).catch((cause: unknown) => {
      setError(cause instanceof Error ? cause.message : 'Could not reach the backend.');
    });
  }, []);

  return <div className="max-w-3xl p-8">
    <h1 className="mb-6 text-2xl font-bold text-slate-800">Settings</h1>
    {error && <div role="alert" className="mb-4 rounded-md border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">{error}</div>}
    <section className="mb-6 rounded-lg border border-slate-200 bg-white p-6">
      <h2 className="mb-2 text-lg font-semibold text-slate-800">Signed-in account</h2>
      <p className="text-sm text-slate-600">{profile?.email ?? 'Loading account…'}</p>
      <p className="mt-1 text-xs text-slate-500">Authorized workspace: {profile?.restaurant_id ?? 'Loading…'}</p>
      <button onClick={() => firebaseAuth && void signOut(firebaseAuth)} className="mt-4 rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700">Sign out</button>
    </section>
    <section className="rounded-lg border border-slate-200 bg-white p-6">
      <h2 className="mb-3 text-lg font-semibold text-slate-800">Backend status</h2>
      {health ? <dl className="grid grid-cols-1 gap-2 text-sm sm:grid-cols-2">
        <dt className="text-slate-500">API process</dt><dd className="font-medium">{health.status}</dd>
        <dt className="text-slate-500">Configured database</dt><dd className="font-medium">{health.database}</dd>
        <dt className="text-slate-500">Gemini key configured</dt><dd className="font-medium">{health.gemini_ready ? 'Yes' : 'No'}</dd>
      </dl> : !error ? <p className="text-sm text-slate-500">Checking backend…</p> : null}
      <p className="mt-4 text-xs text-amber-700">The health check confirms configuration/process status, not successful Firestore or Gemini requests. Do not enter API keys in the frontend.</p>
    </section>
  </div>;
}
