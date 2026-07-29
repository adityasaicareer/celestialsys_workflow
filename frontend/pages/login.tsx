import { FormEvent, useState } from 'react';
import { useAuth } from '../lib/auth';
import { ApiError } from '../lib/api';

export default function Login() {
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!email || !password) return setError('Enter your email and password.');
    setBusy(true);
    setError('');
    try {
      await login(email, password);
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 401) {
          setError('Invalid email or password.');
        } else if (err.status === 403) {
          setError('Your account is not approved yet.');
        } else {
          setError(err.message || 'Unable to sign in. Please try again.');
        }
      } else {
        setError('Unable to sign in. Please check your connection.');
      }
      setBusy(false);
    }
  }

  return (
    <main className="auth-page">
      <div className="auth-brand">
        <span className="brand-mark">G</span>
        <span>gatekeeper</span>
      </div>
      <section className="auth-card">
        <div className="auth-intro">
          <span className="eyebrow">WELCOME BACK</span>
          <h1>Sign in to your workspace</h1>
          <p>Manage secure access across every location.</p>
        </div>
        <form onSubmit={submit} noValidate>
          <label>
            Email address
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@company.com"
              autoComplete="email"
              required
            />
          </label>
          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </label>
          {error && (
            <div className="form-error" role="alert">
              {error}
            </div>
          )}
          <button className="button primary full" disabled={busy}>
            {busy ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
        <div className="auth-hint">
          🎭 <strong>Demo Mode:</strong> Enter any email and password to access the dashboard
        </div>
      </section>
      <span className="copyright">© 2024 Gatekeeper Security Systems</span>
    </main>
  );
}
