import { type FormEvent, useEffect, useState } from "react";
import { isApiRequestError } from "../api/client";
import type { AdminLookupField, AdminUserAccount, SystemRole } from "../api/user-service";
import { useAuth } from "../app/auth-provider";
import { canManageSystemRole } from "../app/role-access";
import { DesktopAppShell } from "../components/desktop-app-shell";
import { FormField } from "../components/form-field";
import { MobileAppShell } from "../components/mobile-app-shell";
import { RoleManagementControls } from "../components/role-management-controls";

const fieldLabels: Record<AdminLookupField, string> = {
  username: "Username",
  email: "NUS email",
};

function humanize(value: string): string {
  return value.split("_").map((part) => part[0] + part.slice(1).toLowerCase()).join(" ");
}

function formattedTimestamp(value: string): string {
  return new Intl.DateTimeFormat("en-SG", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function UserManagementContent() {
  const { user, findUserAccount, updateUserSystemRole } = useAuth();
  const [field, setField] = useState<AdminLookupField>("username");
  const [value, setValue] = useState("");
  const [result, setResult] = useState<AdminUserAccount>();
  const [error, setError] = useState<string>();
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setValue("");
    setResult(undefined);
    setError(undefined);
  }, [field]);

  if (!user) return null;

  async function search(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const query = value.trim();
    setError(undefined);
    setResult(undefined);
    if (!query) {
      setError(`Enter the ${fieldLabels[field].toLowerCase()} to search.`);
      return;
    }

    setBusy(true);
    try {
      setResult(await findUserAccount(field, query));
    } catch (requestError) {
      setError(isApiRequestError(requestError) ? requestError.message : "We could not load that account. Try again.");
    } finally {
      setBusy(false);
    }
  }

  async function changeRole(requestedRole: SystemRole) {
    if (!result) return;
    const targetUserId = result.userId;
    const updated = await updateUserSystemRole(targetUserId, requestedRole);
    setResult((currentResult) => (
      currentResult?.userId === targetUserId
        ? { ...currentResult, systemRole: updated.systemRole }
        : currentResult
    ));
  }

  return (
    <>
      <header className="profile-heading management-heading">
        <p className="section-label">Administration</p>
        <h1>Manage user accounts</h1>
        <p>Find one FoC account by its unique username or NUS email address.</p>
      </header>
      <section className="management-search-card">
        <form className="management-search-form" onSubmit={search}>
          <div className="search-field-select">
            <label htmlFor="lookup-field">Search by</label>
            <select id="lookup-field" onChange={(event) => setField(event.target.value as AdminLookupField)} value={field}>
              <option value="username">Username</option>
              <option value="email">NUS email</option>
            </select>
          </div>
          <FormField
            autoComplete="off"
            label={fieldLabels[field]}
            onChange={(event) => setValue(event.target.value)}
            placeholder={field === "username" ? "e.g. CampusHelper" : "e.g. student@u.nus.edu"}
            required
            type={field === "email" ? "email" : "text"}
            value={value}
          />
          <button className="button button-primary management-search-button" disabled={busy} type="submit">
            {busy ? "Searching…" : "Search account"}
          </button>
        </form>
        {error ? <p className="form-error" role="alert">{error}</p> : null}
      </section>
      {result ? (
        <section aria-live="polite" className="admin-account-result">
          <div className="admin-account-result-heading">
            <div>
              <p className="section-label">Account found</p>
              <h2>{result.displayName}</h2>
              <p>{result.username}</p>
            </div>
            <span className={`account-status account-status-${result.accountStatus.toLowerCase()}`}>
              {result.accountStatus === "ACTIVE" ? "Active" : humanize(result.accountStatus)}
            </span>
          </div>
          <dl className="admin-identity-list">
            <div><dt>User ID</dt><dd>{result.userId}</dd></div>
            <div><dt>NUS email</dt><dd>{result.email}</dd></div>
            <div><dt>Email verification</dt><dd>{result.emailVerified ? "Verified" : "Not verified"}</dd></div>
            <div><dt>System role</dt><dd>{humanize(result.systemRole)}</dd></div>
            <div><dt>Registered</dt><dd>{formattedTimestamp(result.createdAt)}</dd></div>
          </dl>
          <RoleManagementControls
            accountName={result.displayName}
            canManage={canManageSystemRole(user.systemRole, user.userId, result.userId)}
            currentRole={result.systemRole}
            onChangeRole={changeRole}
          />
        </section>
      ) : null}
    </>
  );
}

export function AdminUserManagementPage() {
  const { user } = useAuth();
  const isDesktop = useDesktopLayout();
  if (!user) return null;

  return isDesktop ? (
    <DesktopAppShell user={user}><UserManagementContent /></DesktopAppShell>
  ) : (
    <MobileAppShell user={user}><UserManagementContent /></MobileAppShell>
  );
}

function useDesktopLayout() {
  const [isDesktop, setIsDesktop] = useState(() => window.matchMedia("(min-width: 1024px)").matches);

  useEffect(() => {
    const mediaQuery = window.matchMedia("(min-width: 1024px)");
    const update = () => setIsDesktop(mediaQuery.matches);
    mediaQuery.addEventListener("change", update);
    return () => mediaQuery.removeEventListener("change", update);
  }, []);

  return isDesktop;
}
