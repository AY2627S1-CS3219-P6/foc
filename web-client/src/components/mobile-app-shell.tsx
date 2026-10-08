import { type PropsWithChildren } from "react";
import type { CurrentUser } from "../api/user-service";
import { useWorkspaceMode } from "../app/use-workspace-mode";
import { AppMobileNavigation } from "./app-navigation";
import { WorkspaceTopbar } from "./workspace-topbar";

export function MobileAppShell({ children, user }: PropsWithChildren<{ user: CurrentUser }>) {
  const { mode } = useWorkspaceMode(user);
  return (
    <div className="mobile-shell">
      <WorkspaceTopbar user={user} />
      <main className="mobile-content">{children}</main>
      <AppMobileNavigation mode={mode} user={user} />
    </div>
  );
}
