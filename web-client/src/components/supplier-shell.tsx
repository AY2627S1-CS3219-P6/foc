import type { PropsWithChildren } from "react";
import { Link, NavLink } from "react-router-dom";
import { useAuth } from "../app/auth-provider";

export function SupplierIcon({ size = 20 }: { size?: number }) {
  return <svg aria-hidden="true" fill="none" height={size} viewBox="0 0 24 24" width={size}>
    <path d="M4 9h16v11H4zM7 9V6a5 5 0 0 1 10 0v3" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" />
  </svg>;
}

function ProfileIcon() {
  return <svg aria-hidden="true" fill="none" height="20" viewBox="0 0 24 24" width="20">
    <circle cx="12" cy="8" r="4" stroke="currentColor" strokeWidth="1.8" />
    <path d="M4 21c.8-4.2 3.5-6.3 8-6.3s7.2 2.1 8 6.3" stroke="currentColor" strokeLinecap="round" strokeWidth="1.8" />
  </svg>;
}

export function SupplierShell({ children }: PropsWithChildren) {
  const { user } = useAuth();
  if (!user) return null;
  const firstName = user.displayName.split(/\s+/)[0] || user.displayName;

  return <div className="supplier-shell">
    <aside className="supplier-rail">
      <Link className="supplier-brand" to="/suppliers">
        <span aria-hidden="true" className="supplier-brand-mark"><SupplierIcon size={18} /></span>
        <span><strong>Friends on Campus</strong><small>NUS student community</small></span>
      </Link>
      <span className="supplier-rail-label">Explore</span>
      <NavLink className={({ isActive }) => `supplier-nav-link${isActive ? " active" : ""}`} end to="/suppliers"><SupplierIcon />Suppliers</NavLink>
      <span className="supplier-rail-label supplier-rail-account">Account</span>
      <NavLink className="supplier-nav-link" to="/profile"><ProfileIcon />Profile</NavLink>
    </aside>
    <div className="supplier-app">
      <header className="supplier-topbar">
        <div className="supplier-topbar-greeting"><strong>Good to see you, {firstName}</strong><span>Find what you need around campus.</span></div>
        <Link aria-label="Open your profile" className="supplier-avatar" to="/profile">{user.displayName.slice(0, 1).toUpperCase()}</Link>
      </header>
      <main className="supplier-main">{children}</main>
    </div>
    <nav aria-label="Mobile navigation" className="supplier-bottom-nav">
      <NavLink className={({ isActive }) => isActive ? "active" : ""} end to="/suppliers"><SupplierIcon size={19} /><span>Suppliers</span></NavLink>
      <NavLink className={({ isActive }) => isActive ? "active" : ""} to="/profile"><ProfileIcon /><span>Profile</span></NavLink>
    </nav>
  </div>;
}
