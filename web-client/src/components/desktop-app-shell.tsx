import { type PropsWithChildren } from "react";
import type { CurrentUser } from "../api/user-service";
import { Link } from "react-router-dom";

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

export function DesktopAppShell({ children, user }: PropsWithChildren<{ user: CurrentUser }>) {
  const firstName = user.displayName.split(/\s+/)[0] || user.displayName;

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
        <p className="rail-group-label">Account</p>
        <Link className="rail-supplier-link" to="/suppliers">Suppliers</Link>
        <div aria-current="page" className="rail-profile-link">
          <ProfileGlyph />
          <span>Profile</span>
        </div>
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
