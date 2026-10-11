import { useEffect, useState } from 'react';
import { GoogleAuthProvider, onAuthStateChanged, signInWithPopup, signOut } from 'firebase/auth';
import type { User } from 'firebase/auth';
import type { ReactNode } from 'react';
import { firebaseAuth, firebaseConfigured, localDevelopment } from '../lib/firebase';
import { apiRequest } from '../lib/api';

interface AuthProfile { email: string; restaurant_id: string }

export default function AuthGate({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [profile, setProfile] = useState<AuthProfile | null>(null);
  const [loading, setLoading] = useState(firebaseConfigured);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!firebaseAuth) return;
    return onAuthStateChanged(firebaseAuth, (nextUser) => {
      setUser(nextUser);
      setProfile(null);
      setError('');
      setLoading(false);
    }, () => {
      setError('Could not read the Firebase sign-in state.');
      setLoading(false);
    });
  }, []);

  useEffect(() => {
    if (!user) return;
    let active = true;
    apiRequest<AuthProfile>('/api/auth/me')
      .then((result) => { if (active) setProfile(result); })
      .catch((cause: unknown) => {
        if (active) setError(cause instanceof Error ? cause.message : 'This account is not authorized.');
      });
    return () => { active = false; };
  }, [user]);

  const signIn = async () => {
    if (!firebaseAuth) return;
    setError('');
    try {
      await signInWithPopup(firebaseAuth, new GoogleAuthProvider());
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Google sign-in failed.');
    }
  };

  const signOutUser = async () => {
    if (firebaseAuth) await signOut(firebaseAuth);
    setProfile(null);
    setError('');
  };

  if (localDevelopment) return <>{children}</>;
  if (!firebaseConfigured) {
    return <AuthMessage title="Firebase sign-in is not configured" detail="Set the VITE_FIREBASE_* values in frontend/.env.local (local) or in the production build environment, then rebuild." />;
  }
  if (loading || (user && !profile && !error)) {
    return <div className="flex min-h-screen items-center justify-center text-slate-600">Checking sign-in…</div>;
  }
  if (!user) {
    return <div className="flex min-h-screen items-center justify-center bg-slate-50 p-6">
      <div className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-8 text-center shadow-sm">
        <h1 className="mb-2 text-2xl font-bold text-slate-800">SustainBite</h1>
        <p className="mb-6 text-sm text-slate-600">Sign in with an authorized Google account to continue.</p>
        {error && <p role="alert" className="mb-4 text-sm text-rose-700">{error}</p>}
        <button onClick={() => void signIn()} className="w-full rounded-md bg-slate-900 px-4 py-3 font-medium text-white hover:bg-slate-700">Continue with Google</button>
      </div>
    </div>;
  }
  if (error) {
    return <div className="flex min-h-screen items-center justify-center bg-slate-50 p-6">
      <div className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-8 text-center shadow-sm">
        <h1 className="mb-2 text-xl font-bold text-slate-800">Access not granted</h1>
        <p role="alert" className="mb-6 text-sm text-rose-700">{error}</p>
        <button onClick={() => void signOutUser()} className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white">Sign out</button>
      </div>
    </div>;
  }
  return <>{children}</>;
}

function AuthMessage({ title, detail }: { title: string; detail: string }) {
  return <div className="flex min-h-screen items-center justify-center bg-slate-50 p-6">
    <div className="max-w-lg rounded-xl border border-amber-200 bg-white p-8 text-center shadow-sm">
      <h1 className="mb-2 text-xl font-bold text-slate-800">{title}</h1><p className="text-sm text-slate-600">{detail}</p>
    </div>
  </div>;
}
