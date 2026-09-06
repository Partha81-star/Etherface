import { useCallback, useState } from "react";
import {
  ADMIN_TOKEN_KEY,
  MEMBER_TOKEN_KEY,
  logoutSession,
  type AdminSession,
  type FaceAuthentication,
} from "./api/client";
import { useRoute } from "./hooks/useRoute";
import { AdminDashboardPage } from "./pages/AdminDashboardPage";
import { AdminLoginPage } from "./pages/AdminLoginPage";
import { PortalHome } from "./pages/PortalHome";
import { UserAccountPage } from "./pages/UserAccountPage";
import { UserLoginPage } from "./pages/UserLoginPage";

export default function App() {
  const { path, navigate } = useRoute();
  const [adminToken, setAdminToken] = useState<string | null>(() => sessionStorage.getItem(ADMIN_TOKEN_KEY));
  const [memberToken, setMemberToken] = useState<string | null>(() => sessionStorage.getItem(MEMBER_TOKEN_KEY));

  const adminAuthenticated = useCallback((session: AdminSession) => {
    sessionStorage.setItem(ADMIN_TOKEN_KEY, session.access_token);
    setAdminToken(session.access_token);
    navigate("/admin/dashboard");
  }, [navigate]);

  const memberAuthenticated = useCallback((session: FaceAuthentication) => {
    sessionStorage.setItem(MEMBER_TOKEN_KEY, session.access_token);
    setMemberToken(session.access_token);
    navigate("/account");
  }, [navigate]);

  const logoutAdmin = useCallback(() => {
    const token = sessionStorage.getItem(ADMIN_TOKEN_KEY);
    sessionStorage.removeItem(ADMIN_TOKEN_KEY);
    setAdminToken(null);
    navigate("/admin", true);
    if (token) void logoutSession(token).catch(() => undefined);
  }, [navigate]);

  const logoutMember = useCallback(() => {
    const token = sessionStorage.getItem(MEMBER_TOKEN_KEY);
    sessionStorage.removeItem(MEMBER_TOKEN_KEY);
    setMemberToken(null);
    navigate("/login", true);
    if (token) void logoutSession(token).catch(() => undefined);
  }, [navigate]);

  if (path === "/login") {
    return <UserLoginPage navigate={navigate} onAuthenticated={memberAuthenticated} />;
  }
  if (path === "/account") {
    return memberToken
      ? <UserAccountPage token={memberToken} navigate={navigate} onLogout={logoutMember} />
      : <UserLoginPage navigate={navigate} onAuthenticated={memberAuthenticated} />;
  }
  if (path === "/admin/dashboard") {
    return adminToken
      ? <AdminDashboardPage token={adminToken} navigate={navigate} onLogout={logoutAdmin} />
      : <AdminLoginPage navigate={navigate} onAuthenticated={adminAuthenticated} />;
  }
  if (path === "/admin") {
    return adminToken
      ? <AdminDashboardPage token={adminToken} navigate={navigate} onLogout={logoutAdmin} />
      : <AdminLoginPage navigate={navigate} onAuthenticated={adminAuthenticated} />;
  }
  return <PortalHome navigate={navigate} />;
}
