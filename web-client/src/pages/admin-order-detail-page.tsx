import { type FormEvent, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { adminService, type Dispute } from "../api/admin-service";
import { adminCreditService } from "../api/credit-service";
import { adminOrderService, failureReasons, type OrderParticipant } from "../api/order-service";
import { adminError, clearDraft, noReservation, readDraft, shortId, stateLabel, writeDraft } from "../app/admin-presentation";
import { orderTime } from "../app/order-presentation";
import { useAdminResource } from "../app/use-admin-resource";
import { useAuth } from "../app/use-auth";
import { AdminFact, AdminPanel, DisputeList, OverdueFlag, SettlementFacts } from "../components/admin-ui";
import { OrderBadge, OrderSummary } from "../components/order-ui";
import { WorkspaceShell } from "../components/workspace-shell";

const DESCRIPTION = "Oversee errands, disputes and platform analytics.";
const TIMESTAMPS: [keyof OrderParticipant, string][] = [
  ["createdAt", "Created"],
  ["acceptedAt", "Accepted"],
  ["pickedUpAt", "Picked up"],
  ["deliveredAt", "Delivered"],
  ["completedAt", "Completed"],
  ["cancelledAt", "Cancelled"],
  ["expiredAt", "Expired"],
  ["failedAt", "Failed"],
  ["overdueAt", "Overdue since"],
];

function DisputeForm({ orderId, onCreated }: { orderId: string; onCreated: (dispute: Dispute) => void }) {
  const { withCurrentAccess } = useAuth();
  const draftKey = `admin-dispute-draft:${orderId}`;
  const [draft, setDraft] = useState(() => readDraft(draftKey, { description: "", evidence: "" }));
  // One key per dispute: retrying after an ambiguous failure returns the original (N2NFR3.3).
  const [idempotencyKey, setIdempotencyKey] = useState(() => crypto.randomUUID());
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  function update(next: typeof draft) {
    setDraft(next);
    writeDraft(draftKey, next);
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const evidenceRefs = draft.evidence.split("\n").map((line) => line.trim()).filter(Boolean);
      const dispute = await withCurrentAccess((token) => adminService.createDispute(
        { orderId, description: draft.description.trim(), evidenceRefs }, idempotencyKey, token,
      ));
      clearDraft(draftKey);
      setIdempotencyKey(crypto.randomUUID());
      onCreated(dispute);
    } catch (failure) {
      setError(adminError(failure));
    } finally {
      setSaving(false);
    }
  }

  return <section aria-labelledby="admin-record-dispute" className="order-panel admin-wide">
    <h2 id="admin-record-dispute">Record a dispute</h2>
    <p className="order-muted">Recording a dispute does not change the errand or move credits.</p>
    {error ? <p className="admin-form-error" role="alert">{error}</p> : null}
    <form onSubmit={submit}>
      <label className="order-label">Issue description<textarea maxLength={2000} onChange={(event) => update({ ...draft, description: event.target.value })} required rows={4} value={draft.description} /></label>
      <label className="order-label">Evidence references (optional, one per line)<textarea onChange={(event) => update({ ...draft, evidence: event.target.value })} rows={3} value={draft.evidence} /></label>
      <button className="order-button" disabled={saving || !draft.description.trim()} type="submit">{saving ? "Saving…" : "Record dispute"}</button>
    </form>
  </section>;
}

export function AdminOrderDetailPage() {
  const { orderId = "" } = useParams();
  const navigate = useNavigate();
  const order = useAdminResource((token) => adminOrderService.detail(orderId, token), `order:${orderId}`);
  const history = useAdminResource((token) => adminOrderService.history(orderId, { page: 1, pageSize: 50 }, token), `history:${orderId}`);
  const settlement = useAdminResource((token) => adminCreditService.settlement(orderId, token).catch(noReservation), `settlement:${orderId}`);
  const disputes = useAdminResource((token) => adminService.disputes({ orderId, pageSize: 50 }, token), `disputes:${orderId}`);
  const errand = order.data;

  return <WorkspaceShell adminDescription={DESCRIPTION} className="order-shell admin-shell" userDescription={DESCRIPTION}>
    <Link className="order-back" to="/admin/orders">← Errands</Link>
    <header className="order-heading">
      <div>
        <h1>{errand?.itemDescription ?? "Errand"}</h1>
        <p>Errand #{shortId(orderId)} · read-only administrator view</p>
      </div>
      {errand ? <span className="admin-badges"><OrderBadge state={errand.state} />{errand.overdueAt ? <OverdueFlag /> : null}</span> : null}
    </header>

    <div className="admin-grid">
      <AdminPanel resource={order} title="Errand details">
        {errand ? <>
          <OrderSummary order={errand} />
          <dl className="order-facts">
            <AdminFact label="Errand ID"><span className="order-id">{errand.orderId}</span></AdminFact>
            <AdminFact label="Requester ID"><span className="order-id">{errand.requesterId}</span></AdminFact>
            <AdminFact label="Courier ID"><span className="order-id">{errand.courierId ?? "Not assigned"}</span></AdminFact>
            {TIMESTAMPS.filter(([key]) => errand[key]).map(([key, label]) => <AdminFact key={key} label={label}>{orderTime(String(errand[key]))} SGT</AdminFact>)}
            {errand.failureReason ? <AdminFact label="Failure reason">{failureReasons[errand.failureReason]}{errand.failureDetails ? <small>{errand.failureDetails}</small> : null}</AdminFact> : null}
          </dl>
        </> : null}
      </AdminPanel>

      <AdminPanel resource={history} title="State history">
        {history.data ? <ol className="order-history">
          {history.data.items.map((entry) => <li key={entry.sequence}>
            <strong>{entry.previousState ? `${stateLabel(entry.previousState)} → ` : ""}{stateLabel(entry.newState)}</strong>
            <small>{entry.actorType === "SYSTEM" ? "System" : `User ${shortId(entry.actorId)}`}{entry.failureReason ? ` · ${failureReasons[entry.failureReason]}` : ""}</small>
            <time dateTime={entry.occurredAt}>{orderTime(entry.occurredAt)} SGT</time>
          </li>)}
        </ol> : null}
      </AdminPanel>

      <AdminPanel resource={settlement} title="Credit settlement">
        <SettlementFacts settlement={settlement.data} />
      </AdminPanel>

      <AdminPanel resource={disputes} title="Disputes about this errand">
        {disputes.data ? disputes.data.items.length === 0
          ? <p className="order-muted">No disputes recorded for this errand.</p>
          : <DisputeList items={disputes.data.items} /> : null}
      </AdminPanel>

      {errand ? <DisputeForm onCreated={(dispute) => navigate(`/admin/disputes/${dispute.disputeId}`)} orderId={errand.orderId} /> : null}
    </div>
  </WorkspaceShell>;
}
