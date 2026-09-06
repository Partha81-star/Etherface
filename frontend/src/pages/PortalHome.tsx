import { useEffect, useState } from "react";
import { ArrowRight, Camera, Database, LockKeyhole, ShieldCheck, UserPlus, UserRound } from "lucide-react";
import { getPublicSummary, type PublicSummary } from "../api/client";
import { AppHeader } from "../components/AppHeader";

export function PortalHome({ navigate }: { navigate: (path: string) => void }) {
  const [summary, setSummary] = useState<PublicSummary | null>(null);

  useEffect(() => {
    getPublicSummary().then(setSummary).catch(() => setSummary(null));
  }, []);

  return (
    <div className="app-shell">
      <AppHeader navigate={navigate} />
      <main className="portal-home">
        <section className="portal-intro">
          <div className="intro-copy">
            <p className="eyebrow text-mint">Private local access</p>
            <h1>Your face is the key. Your member ID keeps it private.</h1>
            <p className="intro-lede">Administrators enroll approved members once. Members then sign in with their ID and a fresh face scan—without sending images to an outside service.</p>
            <div className="trust-row">
              <span><LockKeyhole size={16} /> Local processing</span>
              <span><Database size={16} /> {summary ? `${summary.active_members} active members` : "Checking directory"}</span>
              <span><ShieldCheck size={16} /> One-to-one matching</span>
            </div>
          </div>
          <div className="biometric-visual" aria-hidden="true">
            <div className="biometric-radar">
              <span className="radar-ring radar-ring-one" />
              <span className="radar-ring radar-ring-two" />
              <span className="radar-ring radar-ring-three" />
              <span className="radar-sweep" />
              <Camera size={42} />
            </div>
            <div className="visual-label"><span className="status-dot" /> Authentication service ready</div>
          </div>
        </section>

        <section className="portal-choices" aria-label="Choose a portal">
          <button type="button" className="portal-choice portal-choice-primary" onClick={() => navigate("/login")}>
            <span className="portal-choice-icon"><UserRound size={25} /></span>
            <span className="portal-choice-copy">
              <small>For registered members</small>
              <strong>Sign in with your face</strong>
              <span>Enter your member ID, capture a fresh image, and continue to your account.</span>
            </span>
            <span className="portal-choice-arrow"><ArrowRight size={20} /></span>
          </button>
          <button type="button" className="portal-choice" onClick={() => navigate("/admin")}>
            <span className="portal-choice-icon"><UserPlus size={25} /></span>
            <span className="portal-choice-copy">
              <small>Restricted access</small>
              <strong>Open the admin portal</strong>
              <span>Enroll members, manage access, and review recent authentication activity.</span>
            </span>
            <span className="portal-choice-arrow"><ArrowRight size={20} /></span>
          </button>
        </section>

        <p className="demo-notice">Local demonstration only. Still-image matching does not provide liveness detection and should be paired with stronger controls before production use.</p>
      </main>
    </div>
  );
}
