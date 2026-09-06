import { useMemo, useState } from "react";
import { BadgeCheck, Power, Search, ShieldOff, UsersRound } from "lucide-react";
import type { Member } from "../../api/client";

type Props = {
  members: Member[];
  loading: boolean;
  onToggle: (member: Member) => Promise<void>;
};

export function MemberDirectory({ members, loading, onToggle }: Props) {
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<"all" | "active" | "inactive">("all");
  const [updating, setUpdating] = useState<number | null>(null);

  const visible = useMemo(() => {
    const term = search.trim().toLowerCase();
    return members.filter((member) => {
      const statusMatch = filter === "all" || (filter === "active" ? member.is_active : !member.is_active);
      const textMatch = !term || [member.member_code, member.full_name, member.email, member.department || ""].some((value) => value.toLowerCase().includes(term));
      return statusMatch && textMatch;
    });
  }, [members, search, filter]);

  async function toggle(member: Member) {
    setUpdating(member.id);
    try { await onToggle(member); } finally { setUpdating(null); }
  }

  return (
    <section className="admin-section">
      <div className="section-heading">
        <div><p className="eyebrow text-mint">Access directory</p><h1>Registered members</h1><p>Search identities, review activity, and pause or restore access.</p></div>
        <span className="section-icon"><UsersRound size={24} /></span>
      </div>
      <div className="directory-toolbar">
        <label className="directory-search"><Search size={18} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search name, ID, email, or department" aria-label="Search members" /></label>
        <div className="filter-tabs" role="group" aria-label="Member status filter">
          {(["all", "active", "inactive"] as const).map((item) => (
            <button type="button" key={item} className={filter === item ? "active" : ""} onClick={() => setFilter(item)}>{item[0].toUpperCase() + item.slice(1)}</button>
          ))}
        </div>
      </div>

      <div className="directory-panel">
        {loading ? (
          <div className="directory-empty"><span className="skeleton-line" /><span className="skeleton-line short" /><p>Loading member directory…</p></div>
        ) : visible.length === 0 ? (
          <div className="directory-empty"><UsersRound size={30} /><strong>{members.length ? "No members match this view" : "No members enrolled yet"}</strong><p>{members.length ? "Try a different search or status filter." : "Use Register member to add the first person."}</p></div>
        ) : (
          <>
            <div className="member-table-wrap">
              <table className="member-table">
                <thead><tr><th>Member</th><th>Department</th><th>Enrolled</th><th>Last sign-in</th><th>Status</th><th><span className="sr-only">Actions</span></th></tr></thead>
                <tbody>
                  {visible.map((member) => (
                    <tr key={member.id}>
                      <td><div className="member-cell"><span>{member.full_name.split(" ").slice(0, 2).map((part) => part[0]).join("")}</span><div><strong>{member.full_name}</strong><small>{member.member_code} · {member.email}</small></div></div></td>
                      <td>{member.department || "—"}</td>
                      <td>{new Date(member.enrolled_at).toLocaleDateString()}</td>
                      <td>{member.last_authenticated_at ? new Date(member.last_authenticated_at).toLocaleString() : "Never"}</td>
                      <td><span className={member.is_active ? "member-status active" : "member-status inactive"}><i />{member.is_active ? "Active" : "Inactive"}</span></td>
                      <td><button type="button" className="table-action" disabled={updating === member.id} onClick={() => toggle(member)}>{member.is_active ? <ShieldOff size={16} /> : <Power size={16} />}{updating === member.id ? "Updating…" : member.is_active ? "Deactivate" : "Reactivate"}</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="member-card-list">
              {visible.map((member) => (
                <article className="member-mobile-card" key={member.id}>
                  <div className="member-cell"><span>{member.full_name.split(" ").slice(0, 2).map((part) => part[0]).join("")}</span><div><strong>{member.full_name}</strong><small>{member.member_code}</small></div></div>
                  <span className={member.is_active ? "member-status active" : "member-status inactive"}><i />{member.is_active ? "Active" : "Inactive"}</span>
                  <dl><div><dt>Email</dt><dd>{member.email}</dd></div><div><dt>Department</dt><dd>{member.department || "—"}</dd></div><div><dt>Sign-ins</dt><dd>{member.successful_auth_count}</dd></div></dl>
                  <button type="button" className="button-secondary w-full justify-center" disabled={updating === member.id} onClick={() => toggle(member)}><BadgeCheck size={16} />{member.is_active ? "Deactivate member" : "Reactivate member"}</button>
                </article>
              ))}
            </div>
          </>
        )}
      </div>
      <p className="directory-count">Showing {visible.length} of {members.length} registered members</p>
    </section>
  );
}
