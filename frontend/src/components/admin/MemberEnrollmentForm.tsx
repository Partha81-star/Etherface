import { FormEvent, useState } from "react";
import { BadgeCheck, CheckCircle2, LoaderCircle, ShieldCheck, UserPlus } from "lucide-react";
import { enrollMember, type Member } from "../../api/client";
import { readableError } from "../../utils/errors";
import { FaceCapture } from "../FaceCapture";

export function MemberEnrollmentForm({ token, onEnrolled }: { token: string; onEnrolled: (member: Member) => void }) {
  const [memberCode, setMemberCode] = useState("");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [department, setDepartment] = useState("");
  const [image, setImage] = useState<File | null>(null);
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [created, setCreated] = useState<Member | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!image) return;
    setBusy(true);
    setError(null);
    setCreated(null);
    try {
      const member = await enrollMember(token, {
        memberCode,
        fullName,
        email,
        department,
        consentConfirmed: consent,
        image,
      });
      setCreated(member);
      setMemberCode("");
      setFullName("");
      setEmail("");
      setDepartment("");
      setImage(null);
      setConsent(false);
      onEnrolled(member);
    } catch (caught) {
      setError(readableError(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="admin-section">
      <div className="section-heading">
        <div><p className="eyebrow text-mint">New enrollment</p><h1>Register a member</h1><p>Create the identity record first, then capture one clear face sample.</p></div>
        <span className="section-icon"><UserPlus size={24} /></span>
      </div>

      {created && (
        <div className="enrollment-success" role="status">
          <CheckCircle2 size={22} />
          <div><strong>{created.full_name} is ready to sign in</strong><p>Member ID <b>{created.member_code}</b> is active. Share that ID with the member.</p></div>
        </div>
      )}

      <form onSubmit={submit} className="enrollment-form">
        <div className="form-panel">
          <div className="form-panel-heading"><span>1</span><div><h2>Member information</h2><p>Used to identify and manage this account.</p></div></div>
          <div className="form-grid">
            <label className="field-label">
              <span>Member ID</span>
              <span className="input-with-icon"><BadgeCheck size={17} /><input className="text-input" value={memberCode} onChange={(event) => setMemberCode(event.target.value.toUpperCase())} placeholder="EMP-1042" maxLength={40} required /></span>
              <small>Letters, numbers, hyphens, or underscores.</small>
            </label>
            <label className="field-label">
              <span>Full name</span>
              <input className="text-input" value={fullName} onChange={(event) => setFullName(event.target.value)} placeholder="Aarav Sharma" maxLength={160} required />
            </label>
            <label className="field-label">
              <span>Email address</span>
              <input className="text-input" type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="aarav@example.com" maxLength={320} required />
            </label>
            <label className="field-label">
              <span>Department <em>optional</em></span>
              <input className="text-input" value={department} onChange={(event) => setDepartment(event.target.value)} placeholder="Product & Design" maxLength={120} />
            </label>
          </div>
        </div>

        <div className="form-panel">
          <div className="form-panel-heading"><span>2</span><div><h2>Face enrollment</h2><p>The original photo is discarded after its template is created.</p></div></div>
          <FaceCapture value={image} onChange={setImage} disabled={busy} title="Capture the member’s face" description="Use a front-facing portrait with one person, even lighting, and no face covering." />
          <label className="consent-check">
            <input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} required />
            <span><strong>Consent confirmed</strong><small>The member has agreed to biometric processing for this local authentication system.</small></span>
          </label>
        </div>

        {error && <p className="form-error" role="alert">{error}</p>}
        <div className="enrollment-actions">
          <div className="privacy-inline"><ShieldCheck size={17} /><span>No login photos, raw face images, or personal details are written on-chain.</span></div>
          <button type="submit" className="button-primary" disabled={busy || !image || !consent}>
            {busy ? <LoaderCircle className="animate-spin" size={18} /> : <UserPlus size={18} />}
            {busy ? "Creating face template…" : "Register member"}
          </button>
        </div>
      </form>
    </section>
  );
}
