import { createContext } from "react";
import type {
  AdminAccountSummary,
  AdminLookupField,
  AdminUserAccount,
  CurrentUser,
  ProfileChanges,
  SystemRole,
  SystemRoleUpdate,
} from "../api/user-service";

export type AuthStatus = "restoring" | "anonymous" | "authenticated";

export type AuthContextValue = {
  status: AuthStatus;
  user: CurrentUser | null;
  withCurrentAccess: <T,>(operation: (token: string) => Promise<T>) => Promise<T>;
  signIn: (email: string, password: string) => Promise<void>;
  updateProfile: (changes: ProfileChanges) => Promise<CurrentUser>;
  changePassword: (currentPassword: string, newPassword: string) => Promise<void>;
  listAdmins: () => Promise<AdminAccountSummary[]>;
  findUserAccount: (field: AdminLookupField, value: string) => Promise<AdminUserAccount>;
  updateUserSystemRole: (userId: string, systemRole: SystemRole) => Promise<SystemRoleUpdate>;
  signOut: () => Promise<void>;
  deleteAccount: (currentPassword: string) => Promise<void>;
};

export const AuthContext = createContext<AuthContextValue | undefined>(undefined);
