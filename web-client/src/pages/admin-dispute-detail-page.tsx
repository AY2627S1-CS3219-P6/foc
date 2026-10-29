import { type FormEvent, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { adminService, NEXT_STATUSES, type Dispute, type DisputeTarget } from "../api/admin-service";
import { adminCreditService } from "../api/credit-service";
import { adminOrderService, failureReasons } from "../api/order-service";
import { adminError, clearDraft, disputeOrigin, disputeStatusLabels, isVersionConflict, noReservation, readDraft, shortId, writeDraft } from "../app/admin-presentation";
import { orderTime } from "../app/order-presentation";
import { useAdminResource } from "../app/use-admin-resource";
import { useAuth } from "../app/use-auth";
import { AdminFact, AdminPanel, DisputeBadge, OverdueFlag, SettlementFacts } from "../components/admin-ui";
import { OrderBadge } from "../components/order-ui";
import { WorkspaceShell } from "../components/workspace-shell";

const DESCRIPTION = "Oversee errands, disputes and platform analytics.";

function StatusForm({ dispute, onChanged }: { dispute: Dispute; onChanged: () => void }) {
  const { withCurrentAccess } = useAuth();
  const options = NEXT_STATUSES[dispute.status];
  const draftKey = `admin-dispute-reason:${dispute.disputeId}`;
  const [target, setTarget] = useState<DisputeTarget | undefined>(options[0]);
  const [reason, setReason] = useState(() => readDraft(draftKey, ""));
  const [error, setError] = useState<{ message: string; conflict: boolean } | null>(null);
  const [saving, setSaving] = useState(false);

  if (!target) {
    return <section aria-labelledby="admin-update-status" className="order-panel admin-wide">
      <h2 id="admin-update-status">Update status</h2>
      <p>This dispute is {disputeStatusLabels[dispute.status].toLowerCase()} and cannot change further.</p>
    </section>;
  }
  const chosen = target;
  const closing = chosen === "RESOLVED" || chosen === "REJECTED";

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (closing && !reason.trim()) {
      setError({ message: "Give a reason to resolve or reject this dispute.", conflict: false });
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await withCurrentAccess((token) => adminService.transition(dispute.disputeId, {
        toStatus: chosen, reason: reason.trim() || null, expectedVersion: dispute.version,
      }, token));
      clearDraft(draftKey);
      onChanged();
    } catch (failure) {
      setError({ message: adminError(failure), conflict: isVersionConflict(failure) });
    } finally {
      setSaving(false);
    }
  }

  return <section aria-labelledby="admin-update-status" className="order-panel admin-wide">
    <h2 id="admin-update-status">Update status</h2>
    <p className="order-muted">Resolving or rejecting records your decision only. It does not change the errand or move credits.</p>
    {error ? <div className="admin-panel-error" role="alert">
      <p>{error.message}</p>
      {error.conflict ? <button className="order-button order-secondary" onClick={onChanged} type="button">Refresh dispute</button> : null}
    </div> : null}
    <form onSubmit={submit}>
      <fieldset className="admin-choices">
        <legend>New status</legend>
        {options.map((option) => <label key={option}>
          <input checked={chosen === option} name="status" onChange={() => setTarget(option)} type="radio" value={option} />
          {disputeStatusLabels[option]}
        </label>)}
      </fieldset>
      <label className="order-label">{closing ? "Reason (required)" : "Note (optional)"}
        <textarea maxLength={1000} onChange={(event) => { setReason(event.target.value); writeDraft(draftKey, event.target.value); }} rows={3} value={reason} />
      </label>
      <button className="order-button" disabled={saving} type="submit">{saving ? "Saving…" : `Mark as ${disputeStatusLabels[chosen].toLowerCase()}`}</button>
    </form>
  </section>;
}

export function AdminDisputeDetailPage() {
  const { disputeId = "" } = useParams();
  const dispute = useAdminResource((token) => adminService.dispute(disputeId, token), `dispute:${disputeId}`);
  const orderId = dispute.data?.orderId ?? null;
  const order = useAdminResource(orderId ? (token) => adminOrderService.detail(orderId, token) : null, `order:${orderId}`);
  const settlement = useAdminResource(
    orderId ? (token) => adminCreditService.settlement(orderId, token).catch(noReservation) : null,
    `settlement:${orderId}`,
  );
  const data = dispute.data;
  const errand = order.data;

  return <WorkspaceShell adminDescription={DESCRIPTION} className="order-shell admin-shell" userDescription={DESCRIPTION}>
    <Link className="order-back" to="/admin/disputes">← Disputes</Link>
    <header className="order-heading">
      <div>
        <h1>Dispute #{shortId(disputeId)}</h1>
        <p>{data ? `About errand #${shortId(data.orderId)}` : "Dispute case"}</p>
      </div>
      {data ? <DisputeBadge status={data.status} /> : null}
    </header>

    <div className="admin-grid">
      <AdminPanel resource={dispute} title="Case">
        {data ? <>
          <p className="order-description">{data.description}</p>
          <dl className="order-facts">
            {/* Participant reports carry everything in the description; only admin records add evidence. */}
            {data.reporterRole ? null : <AdminFact label="Evidence">{data.evidenceRefs.length
              ? <ul className="admin-evidence">{data.evidenceRefs.map((reference) => <li key={reference}>{reference}</li>)}</ul>
              : "None recorded"}</AdminFact>}
            <AdminFact label={disputeOrigin(data).verb}>{disputeOrigin(data).who} {shortId(data.createdBy)}</AdminFact>
            <AdminFact label="Raised at">{orderTime(data.createdAt)} SGT</AdminFact>
            {data.resolutionReason ? <AdminFact label="Decision reason">{data.resolutionReason}</AdminFact> : null}
          </dl>
        </> : null}
      </AdminPanel>

      <AdminPanel resource={dispute} title="Case history">
        {data ? <ol className="order-history">
          {data.history.map((entry) => <li key={entry.sequence}>
            <strong>{entry.fromStatus ? `${disputeStatusLabels[entry.fromStatus]} → ` : ""}{disputeStatusLabels[entry.toStatus]}</strong>
            {entry.reason ? <small>{entry.reason}</small> : null}
            <small>Admin {shortId(entry.actorId)}</small>
            <time dateTime={entry.occurredAt}>{orderTime(entry.occurredAt)} SGT</time>
          </li>)}
        </ol> : null}
      </AdminPanel>

      <AdminPanel resource={order} title="Errand state">
        {errand ? <>
          <p className="admin-badges"><OrderBadge state={errand.state} />{errand.overdueAt ? <OverdueFlag /> : null}</p>
          <p>{errand.itemDescription}</p>
          {errand.failureReason ? <p className="order-muted">Failure reported: {failureReasons[errand.failureReason]}</p> : null}
          <Link to={`/admin/orders/${errand.orderId}`}>View errand and its history</Link>
        </> : null}
      </AdminPanel>

      <AdminPanel resource={settlement} title="Credit settlement">
        <SettlementFacts settlement={settlement.data} />
      </AdminPanel>

      {data ? <StatusForm dispute={data} key={`${data.disputeId}:${data.version}`} onChanged={dispute.reload} /> : null}
    </div>
  </WorkspaceShell>;
}
