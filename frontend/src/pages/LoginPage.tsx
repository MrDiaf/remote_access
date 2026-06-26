import { LockKeyhole } from 'lucide-react';
import { FormEvent, useState } from 'react';

import { ApiError, api, type AuthUser } from '../api/client';

type LoginPageProps = {
  onLogin: (user: AuthUser) => void;
};

export function LoginPage({ onLogin }: LoginPageProps) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const user = await api.login(username, password);
      onLogin(user);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to sign in');
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="loginScreen">
      <form className="loginPanel" onSubmit={handleSubmit}>
        <div className="loginMark">
          <LockKeyhole size={26} aria-hidden="true" />
        </div>
        <h1>server-control-panel</h1>
        <label>
          <span>Username</span>
          <input value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" />
        </label>
        <label>
          <span>Password</span>
          <input
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            type="password"
            autoComplete="current-password"
          />
        </label>
        {error ? <p className="formError">{error}</p> : null}
        <button className="button primary fullWidth" type="submit" disabled={busy}>
          {busy ? 'Signing in' : 'Sign in'}
        </button>
      </form>
    </main>
  );
}

