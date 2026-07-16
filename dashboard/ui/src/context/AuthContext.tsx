import { createContext, useCallback, useContext, useEffect, useState, ReactNode } from 'react';
import { User } from '../types';

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<string | null>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

// Explicitly tells the browser's password manager to offer saving these
// credentials, via the Credential Management API. This is on top of (not a
// replacement for) the browser's own heuristic form detection — it works
// even though we submit via fetch() instead of a native form POST, and
// degrades silently on browsers that don't support the API (e.g. Safari).
async function storeCredentialForBrowser(username: string, password: string) {
  const PasswordCredentialCtor = (window as unknown as {
    PasswordCredential?: new (data: { id: string; password: string; name?: string }) => Credential;
  }).PasswordCredential;

  if (!navigator.credentials?.store || !PasswordCredentialCtor) {
    return;
  }
  try {
    const credential = new PasswordCredentialCtor({ id: username, password, name: username });
    await navigator.credentials.store(credential);
  } catch {
    // User dismissed the browser's save-password prompt, or the API
    // rejected the call for some other reason — nothing to do either way.
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      const r = await fetch('/api/me');
      if (r.ok) {
        setUser(await r.json());
      }
      setLoading(false);
    })();
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const r = await fetch('/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    const data = await r.json();
    if (!r.ok) {
      return data.error || 'Login failed';
    }
    setUser(data);
    await storeCredentialForBrowser(username, password);
    return null;
  }, []);

  const logout = useCallback(async () => {
    await fetch('/api/logout', { method: 'POST' });
    setUser(null);
    // Stops the browser from silently re-authenticating with a saved
    // credential right after an explicit logout.
    if (navigator.credentials?.preventSilentAccess) {
      navigator.credentials.preventSilentAccess().catch(() => {});
    }
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return ctx;
}
