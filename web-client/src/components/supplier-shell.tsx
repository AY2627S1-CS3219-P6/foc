import type { PropsWithChildren } from "react";
import { WorkspaceShell } from "./workspace-shell";

export function SupplierShell({ children }: PropsWithChildren) {
  return <WorkspaceShell className="supplier-shell" userDescription="Find what you need around campus." adminDescription="Manage the suppliers available to your campus.">{children}</WorkspaceShell>;
}
