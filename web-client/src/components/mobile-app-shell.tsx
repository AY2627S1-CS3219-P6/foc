import { type PropsWithChildren } from "react";
import type { CurrentUser } from "../api/user-service";

export function MobileAppShell({ children, user }: PropsWithChildren<{ user: CurrentUser }>) {
  return (
    <div className="mobile-shell">
      <header className="mobile-topbar">
        <div className="mobile-brand">
          <span aria-hidden="true" className="foc-mark foc-mark-small"><span /><span /></span>
          <span>Friend on Campus</span>
        </div>
        <span aria-label="Current user" className="avatar avatar-small">{user.displayName.slice(0, 1).toUpperCase()}</span>
      </header>
      <main className="mobile-content">{children}</main>
    </div>
  );
}
