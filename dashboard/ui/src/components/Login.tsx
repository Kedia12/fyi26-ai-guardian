import { FormEvent, useState } from 'react';
import { useAuth } from '../context/AuthContext';

interface LoginProps {
  onBack?: () => void;
}

export default function Login({ onBack }: LoginProps) {
  const { login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError('');
    const err = await login(username, password);
    setBusy(false);
    if (err) {
      setError(err);
    }
  }

  return (
    <div className="min-h-screen relative overflow-hidden bg-guardian-bg text-guardian-text font-sans flex items-center justify-center p-5">
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            'radial-gradient(circle at 18% 15%, rgba(99,179,237,0.16), transparent 42%), radial-gradient(circle at 82% 85%, rgba(99,179,237,0.10), transparent 45%)',
        }}
      />
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.04]"
        style={{
          backgroundImage:
            'linear-gradient(#e2e8f0 1px, transparent 1px), linear-gradient(90deg, #e2e8f0 1px, transparent 1px)',
          backgroundSize: '48px 48px',
        }}
      />

      {onBack && (
        <button
          type="button"
          onClick={onBack}
          aria-label="Back to home"
          className="absolute top-6 left-6 sm:top-8 sm:left-8 flex items-center gap-2 text-guardian-text hover:opacity-80 transition-opacity"
        >
          <span className="text-guardian-accent text-xl">▷</span>
          <span className="font-bold text-base tracking-wide">AI Guardian</span>
          <span className="bg-blue-800/60 text-blue-200 text-[10px] px-2.5 py-0.5 rounded-full font-bold tracking-widest uppercase border border-blue-700/50">
            FYI26
          </span>
        </button>
      )}

      <div className="relative w-full max-w-sm">
        <div className="flex flex-col items-center mb-7">
          <div className="relative mb-4">
            <div className="absolute inset-0 rounded-full bg-guardian-accent/20 blur-xl" />
            <div className="relative w-14 h-14 rounded-full bg-guardian-card border border-guardian-border flex items-center justify-center shadow-lg shadow-black/30">
              <svg
                width="26"
                height="26"
                viewBox="0 0 24 24"
                fill="none"
                stroke="#63b3ed"
                strokeWidth="1.75"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M12 3l7 3v5c0 4.5-3 8.5-7 10-4-1.5-7-5.5-7-10V6l7-3z" />
                <path d="M9.5 12l1.8 1.8L14.8 10" />
              </svg>
            </div>
          </div>
          <h1 className="text-guardian-text font-bold text-2xl tracking-wide">
            AI Guardian
          </h1>
          <p className="text-guardian-muted text-xs mt-1.5 tracking-wide">
            Autonomous Flight Monitoring &amp; Threat Detection
          </p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="bg-guardian-card/90 backdrop-blur border border-guardian-border rounded-2xl shadow-2xl shadow-black/40 p-7"
        >
          <label className="block text-guardian-muted text-[11px] font-semibold uppercase tracking-wider mb-1.5">
            Username
          </label>
          <div className="relative mb-4">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-guardian-dim">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                <circle cx="12" cy="7" r="4" />
              </svg>
            </span>
            <input
              autoFocus
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full pl-9 pr-3 py-2.5 rounded-lg bg-guardian-header border border-guardian-border text-guardian-text text-sm
                transition-colors focus:outline-none focus:border-guardian-accent focus:ring-1 focus:ring-guardian-accent/50"
              placeholder="Enter your username"
            />
          </div>

          <label className="block text-guardian-muted text-[11px] font-semibold uppercase tracking-wider mb-1.5">
            Password
          </label>
          <div className="relative mb-5">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-guardian-dim">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="4" y="10" width="16" height="10" rx="2" />
                <path d="M8 10V7a4 4 0 0 1 8 0v3" />
              </svg>
            </span>
            <input
              type={showPassword ? 'text' : 'password'}
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full pl-9 pr-10 py-2.5 rounded-lg bg-guardian-header border border-guardian-border text-guardian-text text-sm
                transition-colors focus:outline-none focus:border-guardian-accent focus:ring-1 focus:ring-guardian-accent/50"
              placeholder="Enter your password"
            />
            <button
              type="button"
              onClick={() => setShowPassword((v) => !v)}
              tabIndex={-1}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-guardian-dim hover:text-guardian-muted transition-colors"
              aria-label={showPassword ? 'Hide password' : 'Show password'}
            >
              {showPassword ? (
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M17.94 17.94A10.94 10.94 0 0 1 12 20c-5.5 0-9.5-4-11-8 .68-1.9 1.86-3.6 3.36-5" />
                  <path d="M9.9 4.24A10.4 10.4 0 0 1 12 4c5.5 0 9.5 4 11 8-.5 1.4-1.3 2.7-2.3 3.8" />
                  <path d="M14.12 14.12a3 3 0 1 1-4.24-4.24" />
                  <path d="M1 1l22 22" />
                </svg>
              ) : (
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                  <circle cx="12" cy="12" r="3" />
                </svg>
              )}
            </button>
          </div>

          {error && (
            <div className="flex items-start gap-2 bg-red-950/40 border border-red-800/50 text-red-400 text-[12px] rounded-lg px-3 py-2.5 mb-4">
              <svg className="shrink-0 mt-0.5" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
              <span>{error}</span>
            </div>
          )}

          <button
            type="submit"
            disabled={busy || !username || !password}
            className="w-full flex items-center justify-center gap-2 px-3 py-2.5 rounded-lg text-sm font-semibold transition-colors
              bg-[#2b6cb0] hover:bg-[#2c5282] disabled:opacity-50 disabled:cursor-not-allowed
              text-white shadow-lg shadow-blue-950/40"
          >
            {busy && (
              <svg className="animate-spin" width="14" height="14" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            )}
            {busy ? 'Signing in…' : 'Sign In'}
          </button>
        </form>

        <p className="text-center text-guardian-dim text-[11px] mt-6 tracking-wide">
          Secured access &middot; FYI26 Guardian Systems
        </p>
      </div>
    </div>
  );
}
