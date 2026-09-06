import { useEffect, useState } from "react";
import { BadgeCheck, Building2, CalendarClock, Check, Fingerprint, LoaderCircle, Mail, ShieldCheck } from "lucide-react";
import { getCurrentMember, type CurrentMember } from "../api/client";
import { AppHeader } from "../components/AppHeader";

type Props = {
  token: string;
  navigate: (path: string) => void;
  onLogout: () => void;
};

export function UserAccountPage({ token, navigate, onLogout }: Props) {
  const [account, setAccount] = useState<CurrentMember | null>(null);
  const [invalid, setInvalid] = useState(false);

  useEffect(() => {
    getCurrentMember(token).then(setAccount).catch(() => setInvalid(true));
  }, [token]);

  useEffect(() => {
    if (invalid) onLogout();
  }, [invalid, onLogout]);

  if (!account) {
    return (
      <div className="app-shell">
        <AppHeader navigate={navigate} currentPortal="user" />
        <main className="page-loader"><LoaderCircle className="animate-spin text-mint" size={32} /><p>Opening your account…</p></main>
      </div>
    );
  }

  const { member } = account;
  const firstName = member.full_name.split(" ")[0];
  return (
    <div className="app-shell">
      <AppHeader navigate={navigate} currentPortal="user" identity={member.full_name} onLogout={onLogout} />
      <main className="account-page">
        <section className="success-hero">
          <div className="success-seal" aria-hidden="true"><span><Check size={32} /></span></div>
          <p className="eyebrow text-mint">Identity confirmed</p>
          <h1>Welcome, {firstName}.</h1>
          <p>Your face matched the active enrollment for <strong>{member.member_code}</strong>. You are now signed in.</p>
          <div className="success-time"><ShieldCheck size={17} /> Verified locally just now</div>
        </section>

        <section className="account-grid">
          <article className="account-card account-card-profile">
            <div className="member-avatar"><Fingerprint size={28} /></div>
            <div><p className="eyebrow">Member profile</p><h2>{member.full_name}</h2><span className="active-pill"><span /> Active member</span></div>
            <dl className="profile-list">
              <div><dt><BadgeCheck size={16} /> Member ID</dt><dd>{member.member_code}</dd></div>
              <div><dt><Mail size={16} /> Email</dt><dd>{member.email}</dd></div>
              <div><dt><Building2 size={16} /> Department</dt><dd>{member.department || "Not specified"}</dd></div>
            </dl>
          </article>

          <article className="account-card">
            <p className="eyebrow">Session details</p>
            <h2>Access granted</h2>
            <div className="session-metric"><strong>{member.successful_auth_count}</strong><span>successful sign-ins</span></div>
            <div className="session-expiry"><CalendarClock size={18} /><div><span>Session expires</span><strong>{new Date(account.session_expires_at).toLocaleString()}</strong></div></div>
            <button type="button" className="button-secondary w-full justify-center" onClick={onLogout}>Sign out securely</button>
          </article>
        </section>
      </main>
    </div>
  );
}
