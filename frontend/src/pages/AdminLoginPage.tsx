import { FormEvent, useState } from "react";
import { ArrowRight, Eye, EyeOff, KeyRound, LoaderCircle, ShieldCheck } from "lucide-react";
import { loginAdmin, type AdminSession } from "../api/client";
import { AppHeader } from "../components/AppHeader";
import { readableError } from "../utils/errors";

type Props = {
  navigate: (path: string) => void;
  onAuthenticated: (session: AdminSession) => void;
};

export function AdminLoginPage({ navigate, onAuthenticated }: Props) {
  const [email, setEmail] = useState("admin@faceverify.local");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      onAuthenticated(await loginAdmin(email, password));
    } catch (caught) {
      setError(readableError(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="app-shell">
      <AppHeader navigate={navigate} currentPortal="admin" />
      <main className="auth-page">
        <section className="auth-context">
          <span className="context-icon"><ShieldCheck size={28} /></span>
          <p className="eyebrow text-mint">Administrator access</p>
          <h1>Manage who can authenticate.</h1>
          <p>Enroll a member’s identity and face template, control active access, and review each login outcome from one private console.</p>
          <ul className="context-list">
            <li><span>01</span> Register member details and consent</li>
            <li><span>02</span> Capture exactly one face</li>
            <li><span>03</span> Activate face-based login</li>
          </ul>
        </section>

        <section className="auth-card" aria-labelledby="admin-login-heading">
          <div className="auth-card-heading">
            <span className="mini-icon"><KeyRound size={19} /></span>
            <div>
              <p className="eyebrow">Secure console</p>
              <h2 id="admin-login-heading">Admin sign in</h2>
            </div>
          </div>
          <form onSubmit={submit} className="form-stack">
            <label className="field-label">
              <span>Email address</span>
              <input className="text-input" type="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="username" required />
            </label>
            <label className="field-label">
              <span>Password</span>
              <span className="password-field">
                <input className="text-input" type={showPassword ? "text" : "password"} value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" required autoFocus />
                <button type="button" onClick={() => setShowPassword((value) => !value)} aria-label={showPassword ? "Hide password" : "Show password"}>
                  {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
                </button>
              </span>
            </label>
            {error && <p className="form-error" role="alert">{error}</p>}
            <button className="button-primary w-full justify-center" type="submit" disabled={busy}>
              {busy ? <LoaderCircle className="animate-spin" size={18} /> : <ArrowRight size={18} />}
              {busy ? "Signing in…" : "Enter admin portal"}
            </button>
          </form>
          <div className="demo-credentials">
            <p>Default local credentials</p>
            <span><code>admin@faceverify.local</code><code>admin123</code></span>
            <small>Change the configured password hash before sharing this environment.</small>
          </div>
        </section>
      </main>
    </div>
  );
}
