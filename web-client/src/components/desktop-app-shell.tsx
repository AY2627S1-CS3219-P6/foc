import { type PropsWithChildren } from "react";
import type { CurrentUser } from "../api/user-service";
import { AppSidebar } from "./app-navigation";

export function DesktopAppShell({ children, user }: PropsWithChildren<{ user: CurrentUser }>) {
  const firstName = user.displayName.split(/\s+/)[0] || user.displayName;

  return (
    <div className="desktop-shell">
      <AppSidebar user={user} />
      <main className="desktop-main">
        <header className="desktop-topbar">
          <div className="desktop-topbar-greeting">
            <p>Good to see you, {firstName}</p>
            <span>Manage the details connected to your FoC account.</span>
          </div>
          <div className="workspace-header-actions">
            <div aria-label="Current account" className="topbar-user">
              <span className="avatar avatar-small">{user.displayName.slice(0, 1).toUpperCase()}</span>
              <span>{user.displayName}</span>
            </div>
          </div>
        </header>
        <div className="desktop-content">{children}</div>
      </main>
    </div>
  );
}
