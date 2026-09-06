import { useCallback, useEffect, useState } from "react";
import { Activity, ArrowRight, CheckCircle2, Fingerprint, LayoutDashboard, LoaderCircle, ShieldCheck, UserPlus, UsersRound, XCircle } from "lucide-react";
import { getAdminOverview, getAdminProfile, listMembers, setMemberStatus, type AdminOverview, type AdminProfile, type Member } from "../api/client";
import { AppHeader } from "../components/AppHeader";
import { MemberDirectory } from "../components/admin/MemberDirectory";
import { MemberEnrollmentForm } from "../components/admin/MemberEnrollmentForm";
import { readableError } from "../utils/errors";

type View = "overview" | "members" | "enroll";

type Props = {
  token: string;
  navigate: (path: string) => void;
  onLogout: () => void;
};

export function AdminDashboardPage({ token, navigate, onLogout }: Props) {
  const [view, setView] = useState<View>("overview");
  const [profile, setProfile] = useState<AdminProfile | null>(null);
  const [overview, setOverview] = useState<AdminOverview | null>(null);
  const [members, setMembers] = useState<Member[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [nextProfile, nextOverview, nextMembers] = await Promise.all([
        getAdminProfile(token),
        getAdminOverview(token),
        listMembers(token),
      ]);
      setProfile(nextProfile);
      setOverview(nextOverview);
      setMembers(nextMembers.items);
    } catch (caught) {
      setError(readableError(caught));
      if (caught instanceof Error && "status" in caught && (caught as { status?: number }).status === 401) onLogout();
    } finally {
      setLoading(false);
    }
  }, [token, onLogout]);

  useEffect(() => { void refresh(); }, [refresh]);

  async function toggleMember(member: Member) {
    try {
      const updated = await setMemberStatus(token, member.id, !member.is_active);
      setMembers((items) => items.map((item) => item.id === updated.id ? updated : item));
      setOverview(await getAdminOverview(token));
    } catch (caught) {
      setError(readableError(caught));
    }
  }

  function memberEnrolled(member: Member) {
    setMembers((items) => [member, ...items]);
    void getAdminOverview(token).then(setOverview);
  }

  return (
    <div className="app-shell">
      <AppHeader navigate={navigate} currentPortal="admin" identity={profile?.name || "Administrator"} onLogout={onLogout} />
      <div className="admin-layout">
        <aside className="admin-sidebar">
          <div className="admin-sidebar-label"><ShieldCheck size={18} /><span>Admin console</span></div>
          <nav aria-label="Admin sections">
            <button type="button" className={view === "overview" ? "active" : ""} onClick={() => setView("overview")}><LayoutDashboard size={18} /> Overview</button>
            <button type="button" className={view === "members" ? "active" : ""} onClick={() => setView("members")}><UsersRound size={18} /> Members <span>{members.length}</span></button>
            <button type="button" className={view === "enroll" ? "active" : ""} onClick={() => setView("enroll")}><UserPlus size={18} /> Register member</button>
          </nav>
          <div className="admin-sidebar-foot"><Fingerprint size={18} /><p><strong>Local biometric store</strong><span>Templates stay on this machine.</span></p></div>
        </aside>

        <main className="admin-main">
          {error && <div className="admin-error" role="alert"><XCircle size={18} /><span>{error}</span><button type="button" onClick={() => setError(null)}>Dismiss</button></div>}
          {loading && !overview ? (
            <div className="page-loader"><LoaderCircle className="animate-spin text-mint" size={32} /><p>Loading the admin console…</p></div>
          ) : view === "enroll" ? (
            <MemberEnrollmentForm token={token} onEnrolled={memberEnrolled} />
          ) : view === "members" ? (
            <MemberDirectory members={members} loading={loading} onToggle={toggleMember} />
          ) : (
            <section className="admin-section">
              <div className="section-heading overview-heading">
                <div><p className="eyebrow text-mint">Today’s access</p><h1>Good to see you, {profile?.name.split(" ")[0] || "Admin"}.</h1><p>Enrollment and authentication activity from this local installation.</p></div>
                <button type="button" className="button-primary" onClick={() => setView("enroll")}><UserPlus size={17} /> Register member</button>
              </div>

              <div className="stat-grid">
                <article><span className="stat-icon mint"><UsersRound size={19} /></span><p>Active members</p><strong>{overview?.active_members ?? 0}</strong><small>{overview?.total_members ?? 0} total enrolled</small></article>
                <article><span className="stat-icon cyan"><Activity size={19} /></span><p>Attempts today</p><strong>{overview?.authentications_today ?? 0}</strong><small>successful and failed</small></article>
                <article><span className="stat-icon green"><CheckCircle2 size={19} /></span><p>Successful today</p><strong>{overview?.successful_today ?? 0}</strong><small>verified face logins</small></article>
              </div>

              <div className="overview-grid">
                <article className="activity-panel">
                  <div className="card-heading"><div><p className="eyebrow">Audit activity</p><h2>Recent authentication</h2></div><button type="button" onClick={() => void refresh()}>Refresh</button></div>
                  {overview?.recent_attempts.length ? (
                    <ol className="activity-list">
                      {overview.recent_attempts.map((attempt) => (
                        <li key={attempt.id}>
                          <span className={attempt.status === "success" ? "activity-icon success" : "activity-icon failed"}>{attempt.status === "success" ? <CheckCircle2 size={17} /> : <XCircle size={17} />}</span>
                          <div><strong>{attempt.status === "success" ? attempt.member_name : "Unrecognized attempt"}</strong><small>{attempt.status === "success" ? attempt.member_code : "No member session created"}</small></div>
                          <time>{new Date(attempt.attempted_at).toLocaleString()}</time>
                        </li>
                      ))}
                    </ol>
                  ) : (
                    <div className="activity-empty"><Activity size={27} /><strong>No authentication attempts yet</strong><p>Member login results will appear here.</p></div>
                  )}
                </article>

                <article className="quick-panel">
                  <p className="eyebrow">Enrollment flow</p><h2>Ready for a new member?</h2><p>Create the member identity, confirm consent, and capture one face sample. They can sign in immediately with the assigned ID.</p>
                  <ol><li><span>1</span> Member details</li><li><span>2</span> Consent and face capture</li><li><span>3</span> Immediate activation</li></ol>
                  <button type="button" className="text-action" onClick={() => setView("enroll")}>Start registration <ArrowRight size={17} /></button>
                </article>
              </div>
            </section>
          )}
        </main>
      </div>
    </div>
  );
}
