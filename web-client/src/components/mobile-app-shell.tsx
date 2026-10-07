import { type PropsWithChildren } from "react";
import { NavLink } from "react-router-dom";
import type { CurrentUser } from "../api/user-service";
import { Link } from "react-router-dom";
import { AppBrand } from "./app-brand";

export function MobileAppShell({ children, user }: PropsWithChildren<{ user: CurrentUser }>) {
  const canManageAdmins = user.systemRole === "SUPER_ADMIN";

  return (
    <div className="mobile-shell">
      <header className="mobile-topbar">
        <AppBrand variant="mobile" />
        <span aria-label="Current user" className="avatar avatar-small">{user.displayName.slice(0, 1).toUpperCase()}</span>
      </header>
      <nav aria-label="Account navigation" className="mobile-account-nav">
        <NavLink to="/profile">Profile</NavLink>
        {canManageAdmins ? <NavLink to="/admin/users">Manage admins</NavLink> : null}
      </nav>
      <main className="mobile-content">{children}</main>
      <nav aria-label="Mobile navigation" className="profile-mobile-nav"><Link to="/suppliers">Suppliers</Link><span aria-current="page">Profile</span></nav>
    </div>
  );
}
