export type Post = {
  id: number;
  caption: string;
  author: string;
  source_url: string;
  timestamp: string;
  image_url: string;
};

export type FaceBox = {
  top: number;
  right: number;
  bottom: number;
  left: number;
  image_width: number;
  image_height: number;
};

export type ScanResult = {
  match: Post;
  distance: number;
  tolerance: number;
  face_box: FaceBox;
  face_provider: string;
};

export type ChainRegistration = {
  post_id: number;
  content_hash: string;
  tx_hash: string;
  block_number: number;
  contract_address: string;
  explorer_url: string | null;
};

export type OnChainRecord = {
  submitter: string;
  timestamp: number;
  metadata_uri: string;
  content_hash: string;
};

export type VerificationStatus = {
  post_id: number;
  verified: boolean;
  local_hash: string;
  on_chain_hash: string | null;
  on_chain_record: OnChainRecord | null;
  status: "verified" | "mismatch" | "not_registered";
};

export type Member = {
  id: number;
  member_code: string;
  full_name: string;
  email: string;
  department: string | null;
  is_active: boolean;
  face_provider: string;
  encoding_version: string;
  consent_confirmed_at: string;
  enrolled_at: string;
  last_authenticated_at: string | null;
  successful_auth_count: number;
};

export type AdminSession = {
  access_token: string;
  token_type: "bearer";
  expires_at: string;
  admin_name: string;
  admin_email: string;
};

export type AdminProfile = {
  name: string;
  email: string;
  role: "admin";
};

export type MemberList = { items: Member[]; total: number };

export type AuthenticationAttempt = {
  id: number;
  status: "success" | "failed";
  member_code: string | null;
  member_name: string | null;
  attempted_at: string;
};

export type AdminOverview = {
  total_members: number;
  active_members: number;
  authentications_today: number;
  successful_today: number;
  recent_attempts: AuthenticationAttempt[];
};

export type FaceAuthentication = {
  access_token: string;
  token_type: "bearer";
  expires_at: string;
  authenticated: true;
  member: Member;
  authenticated_at: string;
  match_score: number;
};

export type CurrentMember = {
  member: Member;
  session_expires_at: string;
};

export type PublicSummary = {
  active_members: number;
  face_backend: string;
  authentication_mode: "member_id_and_face";
};

export type EnrollmentInput = {
  memberCode: string;
  fullName: string;
  email: string;
  department: string;
  consentConfirmed: boolean;
  image: File;
};

type ApiErrorBody = { detail?: string; code?: string };

export class ApiError extends Error {
  status: number;
  code: string;

  constructor(status: number, body: ApiErrorBody) {
    super(body.detail || "The request could not be completed.");
    this.status = status;
    this.code = body.code || "UNKNOWN_ERROR";
  }
}

const baseUrl = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");
export const ADMIN_TOKEN_KEY = "etherface_admin_session";
export const MEMBER_TOKEN_KEY = "etherface_member_session";

async function request<T>(path: string, options?: RequestInit, token?: string | null): Promise<T> {
  const headers = new Headers(options?.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${baseUrl}${path}`, { ...options, headers });
  if (!response.ok) {
    let body: ApiErrorBody = {};
    try {
      body = (await response.json()) as ApiErrorBody;
    } catch {
      body = { detail: response.statusText };
    }
    throw new ApiError(response.status, body);
  }
  return response.json() as Promise<T>;
}

export function resolveApiUrl(path: string): string {
  return path.startsWith("http") ? path : `${baseUrl}${path}`;
}

export async function scanFace(file: File): Promise<ScanResult> {
  const form = new FormData();
  form.append("image", file);
  return request<ScanResult>("/api/scan", { method: "POST", body: form });
}

export async function registerPost(postId: number): Promise<ChainRegistration> {
  return request<ChainRegistration>(`/api/verify/${postId}`, { method: "POST" });
}

export async function verifyPost(postId: number): Promise<VerificationStatus> {
  return request<VerificationStatus>(`/api/verify/${postId}/status`);
}

export async function listPosts(): Promise<Post[]> {
  return request<Post[]>("/api/posts");
}

export async function getPublicSummary(): Promise<PublicSummary> {
  return request<PublicSummary>("/api/public/summary");
}

export async function loginAdmin(email: string, password: string): Promise<AdminSession> {
  return request<AdminSession>("/api/admin/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
}

export async function getAdminProfile(token: string): Promise<AdminProfile> {
  return request<AdminProfile>("/api/admin/me", undefined, token);
}

export async function getAdminOverview(token: string): Promise<AdminOverview> {
  return request<AdminOverview>("/api/admin/overview", undefined, token);
}

export async function listMembers(
  token: string,
  search = "",
  status: "all" | "active" | "inactive" = "all",
): Promise<MemberList> {
  const query = new URLSearchParams({ status });
  if (search.trim()) query.set("search", search.trim());
  return request<MemberList>(`/api/admin/members?${query.toString()}`, undefined, token);
}

export async function enrollMember(token: string, input: EnrollmentInput): Promise<Member> {
  const form = new FormData();
  form.append("member_code", input.memberCode);
  form.append("full_name", input.fullName);
  form.append("email", input.email);
  form.append("department", input.department);
  form.append("consent_confirmed", String(input.consentConfirmed));
  form.append("image", input.image);
  return request<Member>("/api/admin/members", { method: "POST", body: form }, token);
}

export async function setMemberStatus(
  token: string,
  memberId: number,
  isActive: boolean,
): Promise<Member> {
  return request<Member>(`/api/admin/members/${memberId}/status`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ is_active: isActive }),
  }, token);
}

export async function authenticateMember(memberCode: string, image: File): Promise<FaceAuthentication> {
  const form = new FormData();
  form.append("member_code", memberCode);
  form.append("image", image);
  return request<FaceAuthentication>("/api/auth/face", { method: "POST", body: form });
}

export async function getCurrentMember(token: string): Promise<CurrentMember> {
  return request<CurrentMember>("/api/auth/me", undefined, token);
}

export async function logoutSession(token: string): Promise<void> {
  await request<{ detail: string }>("/api/auth/logout", { method: "POST" }, token);
}
