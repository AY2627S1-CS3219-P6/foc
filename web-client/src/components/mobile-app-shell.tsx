import { type PropsWithChildren } from "react";
import type { CurrentUser } from "../api/user-service";
import { AppBrand } from "./app-brand";
import { AppMobileNavigation } from "./app-navigation";

export function MobileAppShell({ children, user }: PropsWithChildren<{ user: CurrentUser }>) {
  return (
    <div className="mobile-shell">
      <header className="mobile-topbar">
        <AppBrand variant="mobile" />
        <div className="workspace-header-actions">
          <span aria-label="Current user" className="avatar avatar-small">{user.displayName.slice(0, 1).toUpperCase()}</span>
        </div>
      </header>
      <main className="mobile-content">{children}</main>
      <AppMobileNavigation user={user} />
    </div>
  );
}
