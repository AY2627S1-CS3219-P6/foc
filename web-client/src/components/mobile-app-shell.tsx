import { type PropsWithChildren } from "react";
import type { CurrentUser } from "../api/user-service";
import { Link } from "react-router-dom";

export function MobileAppShell({ children, user }: PropsWithChildren<{ user: CurrentUser }>) {
  return (
    <div className="mobile-shell">
      <header className="mobile-topbar">
        <div className="mobile-brand">
          <span aria-hidden="true" className="foc-mark foc-mark-small"><span /><span /></span>
          <span>Friend on Campus</span>
        </div>
        <span aria-label="Current user" className="avatar avatar-small">{user.displayName.slice(0, 1).toUpperCase()}</span>
      </header>
      <main className="mobile-content">{children}</main>
      <nav aria-label="Mobile navigation" className="profile-mobile-nav"><Link to="/suppliers">Suppliers</Link><span aria-current="page">Profile</span></nav>
    </div>
  );
}
