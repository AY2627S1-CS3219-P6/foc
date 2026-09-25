import { type PropsWithChildren } from "react";
import { NavLink } from "react-router-dom";
import type { CurrentUser } from "../api/user-service";

function FoCMark() {
  return (
    <span aria-hidden="true" className="foc-mark">
      <span />
      <span />
    </span>
  );
}

function ProfileGlyph() {
  return (
    <svg aria-hidden="true" fill="none" height="18" viewBox="0 0 24 24" width="18">
      <circle cx="12" cy="8" r="4" stroke="currentColor" strokeWidth="1.8" />
      <path d="M4 21c.8-4.2 3.45-6.3 8-6.3s7.2 2.1 8 6.3" stroke="currentColor" strokeLinecap="round" strokeWidth="1.8" />
    </svg>
  );
}

function UsersGlyph() {
  return (
    <svg aria-hidden="true" fill="none" height="18" viewBox="0 0 24 24" width="18">
      <circle cx="9" cy="8" r="3" stroke="currentColor" strokeWidth="1.8" />
      <path d="M3.5 20c.55-3.55 2.36-5.35 5.5-5.35 3.16 0 4.98 1.8 5.5 5.35" stroke="currentColor" strokeLinecap="round" strokeWidth="1.8" />
      <path d="M16.2 5.5a2.75 2.75 0 0 1 0 5.35M17.15 14.9c2.08.2 3.28 1.76 3.65 4.1" stroke="currentColor" strokeLinecap="round" strokeWidth="1.8" />
    </svg>
  );
}

export function DesktopAppShell({ children, user }: PropsWithChildren<{ user: CurrentUser }>) {
  const firstName = user.displayName.split(/\s+/)[0] || user.displayName;
  const canManageUsers = user.systemRole === "ADMIN" || user.systemRole === "SUPER_ADMIN";

  return (
    <div className="desktop-shell">
      <aside className="desktop-rail">
        <div className="rail-brand">
          <FoCMark />
          <div>
            <strong>Friend on Campus</strong>
            <span>NUS student community</span>
          </div>
        </div>
        <nav aria-label="Account navigation" className="rail-navigation">
          <p className="rail-group-label">Account</p>
          <NavLink className={({ isActive }) => `rail-profile-link${isActive ? " rail-profile-link-active" : ""}`} to="/profile">
            <ProfileGlyph />
            <span>Profile</span>
          </NavLink>
          <NavLink className="rail-supplier-link" to="/suppliers">Suppliers</NavLink>
          {canManageUsers ? (
            <>
              <p className="rail-group-label rail-group-label-spaced">Administration</p>
              <NavLink className={({ isActive }) => `rail-profile-link${isActive ? " rail-profile-link-active" : ""}`} to="/admin/users">
                <UsersGlyph />
                <span>Manage users</span>
              </NavLink>
            </>
          ) : null}
        </nav>
        <p className="rail-footnote">Your account is managed by Friend on Campus.</p>
      </aside>
      <main className="desktop-main">
        <header className="desktop-topbar">
          <div>
            <p>Good to see you, {firstName}</p>
            <span>Manage the details connected to your FoC account.</span>
          </div>
          <div aria-label="Current account" className="topbar-user">
            <span className="avatar avatar-small">{user.displayName.slice(0, 1).toUpperCase()}</span>
            <span>{user.displayName}</span>
          </div>
        </header>
        <div className="desktop-content">{children}</div>
      </main>
    </div>
  );
}
