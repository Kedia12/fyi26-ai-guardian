import { FormEvent, useCallback, useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { useAuth } from '../context/AuthContext';

interface UserRow {
  id: number;
  username: string;
  role: 'admin' | 'user';
  disabled: number;
  email: string | null;
  created_at: string;
  password_changed_at: string | null;
}

const inputClass =
  'px-3 py-1.5 rounded bg-guardian-header border border-guardian-border text-guardian-text text-xs focus:outline-none focus:border-guardian-accent';
const labelClass =
  'block text-guardian-muted text-[10px] font-semibold uppercase tracking-wider mb-1';

function EyeToggle({ shown, onClick }: { shown: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      tabIndex={-1}
      className="absolute right-2.5 top-1/2 -translate-y-1/2 text-guardian-dim hover:text-guardian-muted transition-colors"
      aria-label={shown ? 'Hide password' : 'Show password'}
    >
      {shown ? (
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M17.94 17.94A10.94 10.94 0 0 1 12 20c-5.5 0-9.5-4-11-8 .68-1.9 1.86-3.6 3.36-5" />
          <path d="M9.9 4.24A10.4 10.4 0 0 1 12 4c5.5 0 9.5 4 11 8-.5 1.4-1.3 2.7-2.3 3.8" />
          <path d="M14.12 14.12a3 3 0 1 1-4.24-4.24" />
          <path d="M1 1l22 22" />
        </svg>
      ) : (
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
          <circle cx="12" cy="12" r="3" />
        </svg>
      )}
    </button>
  );
}

function EditUserModal({
  user,
  onClose,
  onSaved,
}: {
  user: UserRow;
  onClose: () => void;
  onSaved: () => Promise<void>;
}) {
  const [username, setUsername] = useState(user.username);
  const [email, setEmail] = useState(user.email || '');
  const [role, setRole] = useState<'admin' | 'user'>(user.role);
  const [newPassword, setNewPassword] = useState('');
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function handleSaveProfile() {
    setBusy(true);
    setError('');
    const r = await fetch(`/api/users/${user.id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, email, role }),
    });
    const data = await r.json();
    setBusy(false);
    if (!r.ok) {
      setError(data.error || 'Could not update user.');
      return;
    }
    await onSaved();
    onClose();
  }

  async function handleResetPassword() {
    setBusy(true);
    setError('');
    const r = await fetch(`/api/users/${user.id}/password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ new_password: newPassword }),
    });
    const data = await r.json();
    setBusy(false);
    if (!r.ok) {
      setError(data.error || 'Could not reset password.');
      return;
    }
    setNewPassword('');
  }

  return createPortal(
    <div
      className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/70"
      onClick={onClose}
    >
      <div
        className="bg-guardian-card border border-guardian-border rounded-lg w-full max-w-md"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="bg-guardian-header px-4 py-2.5 border-b border-guardian-border flex items-center justify-between rounded-t-lg">
          <span className="text-[#90cdf4] text-xs font-bold uppercase tracking-widest">
            Modify User: {user.username}
          </span>
          <button
            onClick={onClose}
            className="text-guardian-muted hover:text-guardian-text text-lg leading-none"
          >
            ✕
          </button>
        </div>

        <div className="p-4 space-y-4">
          {error && (
            <div className="flex items-start gap-2 bg-red-950/40 border border-red-800/50 text-red-400 text-[12px] rounded-lg px-3 py-2.5">
              <svg className="shrink-0 mt-0.5" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
              <span>{error}</span>
            </div>
          )}

          <div className="grid grid-cols-1 gap-3">
            <div>
              <label className={labelClass}>Username</label>
              <input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className={`${inputClass} w-full`}
              />
            </div>
            <div>
              <label className={labelClass}>Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="user@example.com"
                className={`${inputClass} w-full`}
              />
            </div>
            <div>
              <label className={labelClass}>Role</label>
              <select
                value={role}
                onChange={(e) => setRole(e.target.value as 'admin' | 'user')}
                className={`${inputClass} w-full`}
              >
                <option value="user">User</option>
                <option value="admin">Admin</option>
              </select>
            </div>
            <button
              type="button"
              disabled={busy || !username}
              onClick={handleSaveProfile}
              className="px-3 py-1.5 rounded text-xs font-semibold transition-colors
                bg-[#2b6cb0] hover:bg-[#2c5282] disabled:opacity-50 disabled:cursor-not-allowed
                text-white"
            >
              Save Changes
            </button>
          </div>

          <div className="border-t border-guardian-border pt-4">
            <label className={labelClass}>Reset Password</label>
            <div className="flex gap-2">
              <div className="relative flex-1">
                <input
                  type={showNewPassword ? 'text' : 'password'}
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="New password (min 8 chars)"
                  className={`${inputClass} w-full pr-8`}
                />
                <EyeToggle shown={showNewPassword} onClick={() => setShowNewPassword((v) => !v)} />
              </div>
              <button
                type="button"
                disabled={busy || newPassword.length < 8}
                onClick={handleResetPassword}
                className="px-3 py-1.5 rounded text-xs font-semibold transition-colors
                  bg-guardian-header border border-guardian-border text-guardian-text
                  hover:border-guardian-accent disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Set Password
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>,
    document.body,
  );
}

export default function CreateUser() {
  const { user: currentUser } = useAuth();
  const [users, setUsers] = useState<UserRow[]>([]);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState<'admin' | 'user'>('user');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [rowBusyId, setRowBusyId] = useState<number | null>(null);
  const [editingUser, setEditingUser] = useState<UserRow | null>(null);

  const fetchUsers = useCallback(async () => {
    const r = await fetch('/api/users');
    if (r.ok) {
      setUsers(await r.json());
    }
  }, []);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError('');
    const r = await fetch('/api/users', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password, role }),
    });
    const data = await r.json();
    setBusy(false);
    if (!r.ok) {
      setError(data.error || 'Could not create user.');
      return;
    }
    setUsername('');
    setPassword('');
    setRole('user');
    await fetchUsers();
  }

  async function handleToggleDisabled(u: UserRow) {
    setError('');
    setRowBusyId(u.id);
    const r = await fetch(`/api/users/${u.id}/disabled`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ disabled: !u.disabled }),
    });
    const data = await r.json();
    setRowBusyId(null);
    if (!r.ok) {
      setError(data.error || 'Could not update user.');
      return;
    }
    await fetchUsers();
  }

  async function handleDelete(u: UserRow) {
    if (!window.confirm(`Delete user "${u.username}"? This cannot be undone.`)) {
      return;
    }
    setError('');
    setRowBusyId(u.id);
    const r = await fetch(`/api/users/${u.id}`, { method: 'DELETE' });
    const data = await r.json().catch(() => ({}));
    setRowBusyId(null);
    if (!r.ok) {
      setError(data.error || 'Could not delete user.');
      return;
    }
    await fetchUsers();
  }

  return (
    <div className="bg-guardian-card border border-guardian-border rounded-lg overflow-hidden">
      <div className="bg-guardian-header px-4 py-2.5 border-b border-guardian-border">
        <span className="text-[#90cdf4] text-xs font-bold uppercase tracking-widest">
          Manage Users
        </span>
      </div>

      <div className="p-4">
        <form onSubmit={handleSubmit} className="flex flex-wrap items-end gap-3 mb-5">
          <div>
            <label className={labelClass}>Username</label>
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className={inputClass}
            />
          </div>
          <div>
            <label className={labelClass}>Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className={inputClass}
            />
          </div>
          <div>
            <label className={labelClass}>Role</label>
            <select
              value={role}
              onChange={(e) => setRole(e.target.value as 'admin' | 'user')}
              className={inputClass}
            >
              <option value="user">User</option>
              <option value="admin">Admin</option>
            </select>
          </div>
          <button
            type="submit"
            disabled={busy || !username || password.length < 8}
            className="px-3 py-1.5 rounded text-xs font-semibold transition-colors
              bg-[#2b6cb0] hover:bg-[#2c5282] disabled:opacity-50 disabled:cursor-not-allowed
              text-white"
          >
            {busy ? 'Creating…' : 'Create User'}
          </button>
        </form>

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

        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-guardian-border">
              {['ID', 'Username', 'Email', 'Role', 'Status', 'Created', 'Password Changed', 'Actions'].map((h) => (
                <th
                  key={h}
                  className="text-left text-guardian-muted font-semibold uppercase tracking-wider text-[10px] px-3 py-2"
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {users.map((u) => {
              const isSelf = u.id === currentUser?.id;
              const rowBusy = rowBusyId === u.id;
              return (
                <tr key={u.id} className="border-b border-guardian-border/50">
                  <td className="px-3 py-2 font-mono text-guardian-muted">#{u.id}</td>
                  <td className="px-3 py-2 text-guardian-text">
                    {u.username}
                    {isSelf && <span className="text-guardian-muted"> (you)</span>}
                  </td>
                  <td className="px-3 py-2 text-guardian-muted">{u.email || '—'}</td>
                  <td className="px-3 py-2 text-guardian-muted uppercase">{u.role}</td>
                  <td className="px-3 py-2 uppercase">
                    <span className={u.disabled ? 'text-red-400' : 'text-green-400'}>
                      {u.disabled ? 'Disabled' : 'Active'}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-guardian-muted">{u.created_at}</td>
                  <td className="px-3 py-2 text-guardian-muted">
                    {u.password_changed_at || 'Never'}
                  </td>
                  <td className="px-3 py-2">
                    <div className="flex gap-2">
                      <button
                        type="button"
                        disabled={rowBusy}
                        onClick={() => setEditingUser(u)}
                        className="px-2 py-1 rounded text-[10px] font-semibold uppercase tracking-wider transition-colors
                          bg-guardian-header border border-guardian-border text-guardian-text
                          hover:border-guardian-accent disabled:opacity-40 disabled:cursor-not-allowed"
                      >
                        Modify
                      </button>
                      <button
                        type="button"
                        disabled={isSelf || rowBusy}
                        onClick={() => handleToggleDisabled(u)}
                        className="px-2 py-1 rounded text-[10px] font-semibold uppercase tracking-wider transition-colors
                          bg-guardian-header border border-guardian-border text-guardian-text
                          hover:border-guardian-accent disabled:opacity-40 disabled:cursor-not-allowed"
                      >
                        {u.disabled ? 'Enable' : 'Disable'}
                      </button>
                      <button
                        type="button"
                        disabled={isSelf || rowBusy}
                        onClick={() => handleDelete(u)}
                        className="px-2 py-1 rounded text-[10px] font-semibold uppercase tracking-wider transition-colors
                          bg-red-900/40 border border-red-800 text-red-300
                          hover:bg-red-900/70 disabled:opacity-40 disabled:cursor-not-allowed"
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {editingUser && (
        <EditUserModal
          user={editingUser}
          onClose={() => setEditingUser(null)}
          onSaved={fetchUsers}
        />
      )}
    </div>
  );
}
