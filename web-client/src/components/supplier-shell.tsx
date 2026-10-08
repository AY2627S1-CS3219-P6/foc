import type { PropsWithChildren } from "react";
import { useAuth } from "../app/use-auth";
import { useWorkspaceMode } from "../app/use-workspace-mode";
import { AppMobileNavigation, AppSidebar } from "./app-navigation";
import { WorkspaceTopbar } from "./workspace-topbar";

export function SupplierShell({ children }: PropsWithChildren) {
  const { user } = useAuth();
  const { mode } = useWorkspaceMode(user);
  if (!user) return null;

  return <div className="supplier-shell">
    <AppSidebar mode={mode} user={user} />
    <div className="supplier-app">
      <WorkspaceTopbar
        user={user}
        userDescription="Find what you need around campus."
        adminDescription="Manage the suppliers available to your campus."
      />
      <main className="supplier-main">{children}</main>
    </div>
    <AppMobileNavigation mode={mode} user={user} />
  </div>;
}
