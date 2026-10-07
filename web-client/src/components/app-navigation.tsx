import type { ComponentType } from "react";
import { Link, NavLink } from "react-router-dom";
import type { CurrentUser } from "../api/user-service";
import { APP_NAME } from "../app/branding";
import type { WorkspaceMode } from "../app/use-workspace-mode";
import { AppBrand } from "./app-brand";
import { ProfileIcon, SupplierNavigationIcon, UsersIcon } from "./navigation-icons";

type NavigationProps = { user: CurrentUser; mode?: WorkspaceMode };
type NavigationItem = { label: string; to: string; Icon: ComponentType };
type NavigationGroup = { label: string; items: NavigationItem[] };

function navigationGroups(user: CurrentUser, mode: WorkspaceMode): NavigationGroup[] {
  const groups: NavigationGroup[] = [];
  const administration: NavigationItem[] = [];
  const isAdminMode = mode === "admin" && (user.systemRole === "ADMIN" || user.systemRole === "SUPER_ADMIN");

  if (isAdminMode) {
    administration.push({ label: "Manage suppliers", to: "/admin/suppliers", Icon: SupplierNavigationIcon });
  } else {
    groups.push({ label: "Account", items: [
      { label: "Profile", to: "/profile", Icon: ProfileIcon },
      { label: "Suppliers", to: "/suppliers", Icon: SupplierNavigationIcon },
    ] });
  }

  if (!isAdminMode && user.systemRole === "SUPER_ADMIN") {
    administration.push({ label: "Manage admins", to: "/admin/users", Icon: UsersIcon });
  }
  if (administration.length) groups.push({ label: "Administration", items: administration });
  return groups;
}

export function AppSidebar({ user, mode = "user" }: NavigationProps) {
  const groups = navigationGroups(user, mode);

  return <aside className="app-sidebar">
    <Link className="app-sidebar-brand" to={groups[0].items[0].to}><AppBrand /></Link>
    <nav aria-label="Main navigation" className="app-sidebar-navigation">
      {groups.map((group) => <div className="app-navigation-group" key={group.label}>
        <p className="app-navigation-heading">{group.label}</p>
        {group.items.map(({ label, to, Icon }) => <NavLink className={({ isActive }) => `app-navigation-link${isActive ? " active" : ""}`} key={to} to={to}>
          <Icon /><span>{label}</span>
        </NavLink>)}
      </div>)}
    </nav>
    <p className="app-sidebar-footnote">Your account is managed by {APP_NAME}.</p>
  </aside>;
}

export function AppMobileNavigation({ user, mode = "user" }: NavigationProps) {
  return <nav aria-label="Mobile navigation" className="app-mobile-navigation">
    {navigationGroups(user, mode).flatMap((group) => group.items).map(({ label, to, Icon }) => <NavLink className={({ isActive }) => isActive ? "active" : ""} key={to} to={to}>
      <Icon /><span>{label}</span>
    </NavLink>)}
  </nav>;
}
