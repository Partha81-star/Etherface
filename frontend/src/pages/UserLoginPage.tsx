import { FormEvent, useEffect, useState } from "react";
import { ArrowRight, BadgeCheck, Fingerprint, LoaderCircle, LockKeyhole, ScanFace, ShieldAlert } from "lucide-react";
import { authenticateMember, getPublicSummary, type FaceAuthentication, type PublicSummary } from "../api/client";
import { AppHeader } from "../components/AppHeader";
import { FaceCapture } from "../components/FaceCapture";
import { readableError } from "../utils/errors";

type Props = {
  navigate: (path: string) => void;
  onAuthenticated: (result: FaceAuthentication) => void;
};

export function UserLoginPage({ navigate, onAuthenticated }: Props) {
  const [memberCode, setMemberCode] = useState("");
  const [image, setImage] = useState<File | null>(null);
  const [summary, setSummary] = useState<PublicSummary | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getPublicSummary().then(setSummary).catch(() => setSummary(null));
  }, []);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!image || !memberCode.trim()) return;
    setBusy(true);
    setError(null);
    try {
      onAuthenticated(await authenticateMember(memberCode, image));
    } catch (caught) {
      setError(readableError(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="app-shell">
      <AppHeader navigate={navigate} currentPortal="user" />
      <main className="login-workspace">
        <section className="login-heading">
          <div>
            <p className="eyebrow text-mint">Member authentication</p>
            <h1>Welcome back. Let’s verify it’s you.</h1>
            <p>Enter the member ID provided by your administrator, then take a fresh face photo.</p>
          </div>
          <div className="service-state">
            <span className="status-dot" />
            <div><strong>Service ready</strong><small>{summary ? `${summary.active_members} active members` : "Connecting locally"}</small></div>
          </div>
        </section>

        <form onSubmit={submit} className="login-grid">
          <aside className="login-details">
            <div className="step-heading"><span>1</span><div><strong>Identify your account</strong><small>This narrows the scan to your enrolled template.</small></div></div>
            <label className="field-label mt-6">
              <span>Member ID</span>
              <span className="input-with-icon">
                <BadgeCheck size={18} />
                <input className="text-input" value={memberCode} onChange={(event) => setMemberCode(event.target.value.toUpperCase())} placeholder="e.g. EMP-1042" autoComplete="username" maxLength={40} required />
              </span>
            </label>
            <div className="privacy-card">
              <LockKeyhole size={19} />
              <div><strong>Your image is temporary</strong><p>The login capture is compared in memory and discarded. It is never written to the blockchain or saved as a photo.</p></div>
            </div>
            <div className="security-note">
              <ShieldAlert size={18} />
              <p>This demo checks facial similarity but does not detect liveness. Do not use it alone for high-security access.</p>
            </div>
          </aside>

          <section className="login-capture">
            <div className="step-heading"><span>2</span><div><strong>Scan your face</strong><small>Use even lighting and remove anything covering your face.</small></div></div>
            <div className="mt-6">
              <FaceCapture value={image} onChange={(file) => { setImage(file); setError(null); }} disabled={busy} title="Take a fresh face photo" description="Keep one face centered and look directly at the camera." />
            </div>
            {busy && (
              <div className="scan-progress" aria-live="polite">
                <span className="scan-progress-icon"><ScanFace size={24} /></span>
                <div><strong>Checking your face…</strong><p>Comparing this capture only with the template for {memberCode || "your member ID"}.</p></div>
              </div>
            )}
            {error && (
              <div className="auth-error" role="alert">
                <Fingerprint size={20} />
                <div><strong>We couldn’t verify your identity</strong><p>{error}</p></div>
              </div>
            )}
            <button className="button-primary login-submit" type="submit" disabled={busy || !image || !memberCode.trim()}>
              {busy ? <LoaderCircle className="animate-spin" size={18} /> : <Fingerprint size={18} />}
              {busy ? "Authenticating…" : "Authenticate and sign in"}
              {!busy && <ArrowRight size={18} />}
            </button>
          </section>
        </form>
      </main>
    </div>
  );
}
