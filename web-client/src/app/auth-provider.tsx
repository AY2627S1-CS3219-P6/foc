import {
  createContext,
  type PropsWithChildren,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { ApiRequestError, isApiRequestError } from "../api/client";
import {
  type AccessSession,
  type AdminLookupField,
  type AdminUserAccount,
  type CurrentUser,
  type ProfileChanges,
  type SystemRole,
  type SystemRoleUpdate,
  userService,
} from "../api/user-service";

type AuthStatus = "restoring" | "anonymous" | "authenticated";

type AuthContextValue = {
  status: AuthStatus;
  user: CurrentUser | null;
  withCurrentAccess: <T,>(operation: (token: string) => Promise<T>) => Promise<T>;
  signIn: (email: string, password: string) => Promise<void>;
  updateProfile: (changes: ProfileChanges) => Promise<CurrentUser>;
  changePassword: (currentPassword: string, newPassword: string) => Promise<void>;
  findUserAccount: (field: AdminLookupField, value: string) => Promise<AdminUserAccount>;
  updateUserSystemRole: (userId: string, systemRole: SystemRole) => Promise<SystemRoleUpdate>;
  signOut: () => Promise<void>;
  deleteAccount: (currentPassword: string) => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function isUnauthorized(error: unknown): boolean {
  return isApiRequestError(error) && error.status === 401;
}

export function AuthProvider({ children }: PropsWithChildren) {
  const [status, setStatus] = useState<AuthStatus>("restoring");
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);

  const clearSession = useCallback(() => {
    setAccessToken(null);
    setUser(null);
    setStatus("anonymous");
  }, []);

  const acceptSession = useCallback(async (session: AccessSession): Promise<CurrentUser> => {
    const currentUser = await userService.getCurrentUser(session.accessToken);
    setAccessToken(session.accessToken);
    setUser(currentUser);
    setStatus("authenticated");
    return currentUser;
  }, []);

  useEffect(() => {
    let active = true;
    void userService
      .refreshSession()
      .then(async (session) => {
        const currentUser = await userService.getCurrentUser(session.accessToken);
        if (!active) return;
        setAccessToken(session.accessToken);
        setUser(currentUser);
        setStatus("authenticated");
      })
      .catch(() => {
        if (active) clearSession();
      });
    return () => {
      active = false;
    };
  }, [clearSession]);

  const withCurrentAccess = useCallback(
    async <T,>(operation: (token: string) => Promise<T>): Promise<T> => {
      if (!accessToken) throw new ApiRequestError(401, "Sign in to continue.", { code: "AUTH_REQUIRED" });
      try {
        return await operation(accessToken);
      } catch (error) {
        if (!isUnauthorized(error)) throw error;
      }

      try {
        const refreshed = await userService.refreshSession();
        const refreshedUser = await userService.getCurrentUser(refreshed.accessToken);
        setAccessToken(refreshed.accessToken);
        setUser(refreshedUser);
        return await operation(refreshed.accessToken);
      } catch (error) {
        clearSession();
        throw error;
      }
    },
    [accessToken, clearSession],
  );

  const signIn = useCallback(
    async (email: string, password: string) => {
      const session = await userService.createSession(email, password);
      await acceptSession(session);
    },
    [acceptSession],
  );

  const updateProfile = useCallback(
    async (changes: ProfileChanges) => {
      const updated = await withCurrentAccess((token) => userService.updateCurrentUser(changes, token));
      setUser(updated);
      return updated;
    },
    [withCurrentAccess],
  );

  const changePassword = useCallback(
    async (currentPassword: string, newPassword: string) => {
      await withCurrentAccess((token) => userService.changeCurrentPassword(currentPassword, newPassword, token));
      clearSession();
    },
    [clearSession, withCurrentAccess],
  );

  const findUserAccount = useCallback(
    (field: AdminLookupField, value: string) =>
      withCurrentAccess((token) => userService.findUserAccount(field, value, token)),
    [withCurrentAccess],
  );

  const updateUserSystemRole = useCallback(
    (userId: string, systemRole: SystemRole) =>
      withCurrentAccess((token) => userService.updateUserSystemRole(userId, systemRole, token)),
    [withCurrentAccess],
  );

  const signOut = useCallback(async () => {
    try {
      await withCurrentAccess((token) => userService.revokeCurrentSession(token));
    } finally {
      clearSession();
    }
  }, [clearSession, withCurrentAccess]);

  const deleteAccount = useCallback(
    async (currentPassword: string) => {
      await withCurrentAccess((token) => userService.deleteCurrentUser(currentPassword, token));
      clearSession();
    },
    [clearSession, withCurrentAccess],
  );

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      user,
      withCurrentAccess,
      signIn,
      updateProfile,
      changePassword,
      findUserAccount,
      updateUserSystemRole,
      signOut,
      deleteAccount,
    }),
    [
      changePassword,
      deleteAccount,
      findUserAccount,
      signIn,
      signOut,
      status,
      updateProfile,
      updateUserSystemRole,
      user,
      withCurrentAccess,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider.");
  return context;
}
