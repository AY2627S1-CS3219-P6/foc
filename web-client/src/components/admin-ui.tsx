import type { PropsWithChildren, ReactNode } from "react";
import { Link } from "react-router-dom";
import type { DisputeStatus, DisputeSummary } from "../api/admin-service";
import type { Settlement } from "../api/credit-service";
import { adminError, disputeStatusLabels, shortId, updatedAt } from "../app/admin-presentation";
import { orderTime } from "../app/order-presentation";

type PanelResource = { loading: boolean; error: unknown; retrievedAt: Date | null; reload: () => void };

/**
 * One independently loaded dashboard panel: loading, failure with retry, stale data and the
 * retrieval time are explicit, and no values are shown until data has arrived (N2NFR4.4, N2NFR5.2).
 */
export function AdminPanel({ title, resource, wide = false, intro, children }: PropsWithChildren<{
  title: string; resource: PanelResource; wide?: boolean; intro?: ReactNode;
}>) {
  const headingId = `admin-panel-${title.toLowerCase().replaceAll(/[^a-z0-9]+/g, "-")}`;
  return <section aria-labelledby={headingId} className={`order-panel admin-panel${wide ? " admin-wide" : ""}`}>
    <div className="admin-panel-heading">
      <h2 id={headingId}>{title}</h2>
      {resource.retrievedAt ? <span className="admin-updated">{updatedAt(resource.retrievedAt)}</span> : null}
    </div>
    {intro}
    {resource.error ? <div className="admin-panel-error" role="alert">
      <p>{resource.retrievedAt ? `Showing earlier data. ${adminError(resource.error)}` : adminError(resource.error)}</p>
      <button className="order-button order-secondary" onClick={resource.reload} type="button">Try again</button>
    </div> : null}
    {resource.loading && !resource.retrievedAt ? <p aria-live="polite" className="order-muted">Loading…</p> : null}
    {resource.retrievedAt ? children : null}
  </section>;
}

export function DisputeBadge({ status }: { status: DisputeStatus }) {
  return <span className={`order-badge dispute-badge-${status.toLowerCase()}`}>{disputeStatusLabels[status]}</span>;
}

export function OverdueFlag() {
  return <span className="admin-flag">Overdue</span>;
}

export function AdminFact({ label, children }: PropsWithChildren<{ label: string }>) {
  return <div><dt>{label}</dt><dd>{children}</dd></div>;
}

const settlementLabels: Record<Settlement["state"], string> = {
  RESERVED: "Reserved until the errand ends",
  RELEASED: "Released back to the requester",
  TRANSFERRED: "Transferred to the courier",
  CLOSED: "Closed without a reservation",
};

// N2F3.4.3: the credit outcome is shown apart from the errand state.
export function SettlementFacts({ settlement }: { settlement: Settlement | null }) {
  if (!settlement) return <p className="order-muted">No credit reservation is recorded for this errand.</p>;
  return <>
    <dl className="order-facts">
      <AdminFact label="Credit state">{settlementLabels[settlement.state]}</AdminFact>
      <AdminFact label="Amount">{settlement.amount} credits</AdminFact>
      <AdminFact label="Last change">{orderTime(settlement.updatedAt)} SGT</AdminFact>
    </dl>
    <p className="order-muted">Dispute decisions never move credits.</p>
  </>;
}

export function DisputeList({ items }: { items: DisputeSummary[] }) {
  return <ul className="admin-list">
    {items.map((dispute) => <li key={dispute.disputeId}>
      <Link className="admin-list-item" to={`/admin/disputes/${dispute.disputeId}`}>
        <span className="admin-row-title"><strong className="admin-clamp">{dispute.description}</strong><DisputeBadge status={dispute.status} /></span>
        <span className="admin-row-meta">
          <span>Dispute #{shortId(dispute.disputeId)}</span>
          <span>Errand #{shortId(dispute.orderId)}</span>
          <span>Recorded {orderTime(dispute.createdAt)} SGT</span>
        </span>
      </Link>
    </li>)}
  </ul>;
}
