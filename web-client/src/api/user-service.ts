import { requestJson } from "./client";

export type CurrentUser = {
  userId: string;
  username: string;
  email: string;
  displayName: string;
  systemRole: "USER" | "ADMIN" | "SUPER_ADMIN";
  accountStatus: "ACTIVE" | "SUSPENDED" | "DELETED";
};

export type AccessSession = {
  accessToken: string;
  tokenType: "Bearer";
  expiresAt: string;
};

export type VerificationPending = {
  status: "verification_pending";
  email: string;
  expiresAt: string;
};

export type ActivatedAccount = {
  status: "active";
  userId: string;
  username: string;
  email: string;
  displayName: string;
  systemRole: "USER";
  emailVerifiedAt: string;
};

export type RegistrationPayload = {
  username: string;
  email: string;
  password: string;
  displayName?: string;
};

export type ProfileChanges = Pick<CurrentUser, "displayName">;

export const userService = {
  startRegistration: (payload: RegistrationPayload) =>
    requestJson<VerificationPending>("/auth/registrations", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  verifyEmail: (email: string, otp: string) =>
    requestJson<ActivatedAccount>("/auth/email-verifications", {
      method: "POST",
      body: JSON.stringify({ email, otp }),
    }),

  resendVerification: (email: string) =>
    requestJson<VerificationPending>("/auth/email-verifications/resend", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),

  createSession: (email: string, password: string) =>
    requestJson<AccessSession>("/auth/sessions", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  refreshSession: () => requestJson<AccessSession>("/auth/sessions/refresh", { method: "POST" }),

  revokeCurrentSession: (accessToken: string) =>
    requestJson<void>("/auth/sessions/current", { method: "DELETE" }, accessToken),

  getCurrentUser: (accessToken: string) =>
    requestJson<CurrentUser>("/users/me", { method: "GET" }, accessToken),

  updateCurrentUser: (changes: ProfileChanges, accessToken: string) =>
    requestJson<CurrentUser>(
      "/users/me",
      { method: "PATCH", body: JSON.stringify(changes) },
      accessToken,
    ),

  deleteCurrentUser: (currentPassword: string, accessToken: string) =>
    requestJson<void>(
      "/users/me",
      { method: "DELETE", body: JSON.stringify({ currentPassword, acknowledgeDeletion: true }) },
      accessToken,
    ),
};
