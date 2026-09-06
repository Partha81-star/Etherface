import { Fingerprint, LogOut, ShieldCheck, UserRound } from "lucide-react";

type Props = {
  navigate: (path: string) => void;
  currentPortal?: "user" | "admin";
  identity?: string | null;
  onLogout?: () => void;
};

export function AppHeader({ navigate, currentPortal, identity, onLogout }: Props) {
  return (
    <header className="app-header">
      <div className="app-header-inner">
        <button type="button" className="brand" onClick={() => navigate("/")} aria-label="EtherFace home">
          <span className="brand-mark"><Fingerprint size={21} /></span>
          <span>
            <strong>EtherFace</strong>
            <small>Identity access</small>
          </span>
        </button>

        <nav className="portal-nav" aria-label="Portal navigation">
          <button
            type="button"
            className={currentPortal === "user" ? "portal-link portal-link-active" : "portal-link"}
            onClick={() => navigate("/login")}
          >
            <UserRound size={16} /> <span>User login</span>
          </button>
          <button
            type="button"
            className={currentPortal === "admin" ? "portal-link portal-link-active" : "portal-link"}
            onClick={() => navigate("/admin")}
          >
            <ShieldCheck size={16} /> <span>Admin</span>
          </button>
        </nav>

        {identity && (
          <div className="header-identity">
            <span className="header-identity-name">{identity}</span>
            {onLogout && (
              <button type="button" className="icon-button" onClick={onLogout} aria-label="Sign out">
                <LogOut size={17} />
              </button>
            )}
          </div>
        )}
      </div>
    </header>
  );
}
