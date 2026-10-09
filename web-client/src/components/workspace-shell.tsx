import type { PropsWithChildren } from "react";
import { useAuth } from "../app/use-auth";
import { useWorkspaceMode } from "../app/use-workspace-mode";
import { AppMobileNavigation, AppSidebar } from "./app-navigation";
import { WorkspaceTopbar } from "./workspace-topbar";

export function WorkspaceShell({ children, className = "", userDescription, adminDescription }: PropsWithChildren<{
  className?: string; userDescription: string; adminDescription?: string;
}>) {
  const { user } = useAuth();
  const { mode } = useWorkspaceMode(user);
  if (!user) return null;
  return <div className={`workspace-shell ${className}`}>
    <AppSidebar mode={mode} user={user} />
    <div className="workspace-app">
      <WorkspaceTopbar user={user} userDescription={userDescription} adminDescription={adminDescription} />
      <main className="workspace-main">{children}</main>
    </div>
    <AppMobileNavigation mode={mode} user={user} />
  </div>;
}
