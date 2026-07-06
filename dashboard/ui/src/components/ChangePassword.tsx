import { FormEvent, useState } from 'react';
import { createPortal } from 'react-dom';

function EyeToggle({
  shown,
  onClick,
}: {
  shown: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      tabIndex={-1}
      className="absolute right-3 top-1/2 -translate-y-1/2 text-guardian-dim hover:text-guardian-muted transition-colors"
      aria-label={shown ? 'Hide password' : 'Show password'}
    >
      {shown ? (
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
  );
}

export default function ChangePassword({ onClose }: { onClose: () => void }) {
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showCurrent, setShowCurrent] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [error, setError] = useState('');
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError('');

    if (newPassword !== confirmPassword) {
      setError('New password and confirmation do not match.');
      return;
    }

    setBusy(true);
    const r = await fetch('/api/me/password', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        current_password: currentPassword,
        new_password: newPassword,
      }),
    });
    const data = await r.json();
    setBusy(false);
    if (!r.ok) {
      setError(data.error || 'Could not change password.');
      return;
    }
    setDone(true);
  }

  return createPortal(
    <div
      className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/70"
      onClick={onClose}
    >
      <div
        className="bg-guardian-card border border-guardian-border rounded-lg w-full max-w-sm"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="bg-guardian-header px-4 py-2.5 border-b border-guardian-border flex items-center justify-between rounded-t-lg">
          <span className="text-[#90cdf4] text-xs font-bold uppercase tracking-widest">
            Change Password
          </span>
          <button
            onClick={onClose}
            className="text-guardian-muted hover:text-guardian-text text-lg leading-none"
          >
            ✕
          </button>
        </div>

        {done ? (
          <div className="p-5">
            <p className="text-green-400 text-sm mb-4">Password changed successfully.</p>
            <button
              onClick={onClose}
              className="w-full px-3 py-2 rounded text-sm font-semibold transition-colors
                bg-[#2b6cb0] hover:bg-[#2c5282] text-white"
            >
              Close
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="p-5">
            <label className="block text-guardian-muted text-[11px] font-semibold uppercase tracking-wider mb-1">
              Current Password
            </label>
            <div className="relative mb-4">
              <input
                type={showCurrent ? 'text' : 'password'}
                autoFocus
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                className="w-full pr-10 px-3 py-2 rounded bg-guardian-header border border-guardian-border text-guardian-text text-sm focus:outline-none focus:border-guardian-accent"
              />
              <EyeToggle shown={showCurrent} onClick={() => setShowCurrent((v) => !v)} />
            </div>

            <label className="block text-guardian-muted text-[11px] font-semibold uppercase tracking-wider mb-1">
              New Password
            </label>
            <div className="relative mb-4">
              <input
                type={showNew ? 'text' : 'password'}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="w-full pr-10 px-3 py-2 rounded bg-guardian-header border border-guardian-border text-guardian-text text-sm focus:outline-none focus:border-guardian-accent"
              />
              <EyeToggle shown={showNew} onClick={() => setShowNew((v) => !v)} />
            </div>

            <label className="block text-guardian-muted text-[11px] font-semibold uppercase tracking-wider mb-1">
              Confirm New Password
            </label>
            <div className="relative mb-4">
              <input
                type={showConfirm ? 'text' : 'password'}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full pr-10 px-3 py-2 rounded bg-guardian-header border border-guardian-border text-guardian-text text-sm focus:outline-none focus:border-guardian-accent"
              />
              <EyeToggle shown={showConfirm} onClick={() => setShowConfirm((v) => !v)} />
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
              disabled={busy || !currentPassword || newPassword.length < 8}
              className="w-full px-3 py-2 rounded text-sm font-semibold transition-colors
                bg-[#2b6cb0] hover:bg-[#2c5282] disabled:opacity-50 disabled:cursor-not-allowed
                text-white"
            >
              {busy ? 'Saving…' : 'Save New Password'}
            </button>
          </form>
        )}
      </div>
    </div>,
    document.body,
  );
}
