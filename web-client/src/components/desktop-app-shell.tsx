import { type PropsWithChildren } from "react";
import type { CurrentUser } from "../api/user-service";
import { useWorkspaceMode } from "../app/use-workspace-mode";
import { AppSidebar } from "./app-navigation";
import { WorkspaceTopbar } from "./workspace-topbar";

export function DesktopAppShell({ children, user }: PropsWithChildren<{ user: CurrentUser }>) {
  const { mode } = useWorkspaceMode(user);

  return (
    <div className="desktop-shell">
      <AppSidebar mode={mode} user={user} />
      <main className="desktop-main">
        <WorkspaceTopbar user={user} />
        <div className="desktop-content">{children}</div>
      </main>
    </div>
  );
}
