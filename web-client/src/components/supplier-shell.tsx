import type { PropsWithChildren } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../app/use-auth";
import { useWorkspaceMode } from "../app/use-workspace-mode";
import { AppBrand } from "./app-brand";
import { AppMobileNavigation, AppSidebar } from "./app-navigation";
import { WorkspaceModeSwitch } from "./workspace-mode-switch";

export function SupplierShell({ children }: PropsWithChildren) {
  const { user } = useAuth();
  const { mode } = useWorkspaceMode(user);
  if (!user) return null;
  const isAdminMode = mode === "admin";
  const firstName = user.displayName.split(/\s+/)[0] || user.displayName;

  return <div className="supplier-shell">
    <AppSidebar mode={mode} user={user} />
    <div className="supplier-app">
      <header className="supplier-topbar">
        <div className="supplier-mobile-brand"><AppBrand variant="mobile" /></div>
        <div className="supplier-topbar-greeting"><strong>{isAdminMode ? "Admin workspace" : `Good to see you, ${firstName}`}</strong><span>{isAdminMode ? "Manage the suppliers available to your campus." : "Find what you need around campus."}</span></div>
        <div className="workspace-header-actions">
          <WorkspaceModeSwitch user={user} />
          <Link aria-label="Open your profile" className="supplier-avatar" to="/profile">{user.displayName.slice(0, 1).toUpperCase()}</Link>
        </div>
      </header>
      <main className="supplier-main">{children}</main>
    </div>
    <AppMobileNavigation mode={mode} user={user} />
  </div>;
}
