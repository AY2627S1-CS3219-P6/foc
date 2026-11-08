// AI Assistance Disclosure:
// Tool: Claude Code (model: Claude Opus 5.5), date: 2026-10-28, 2026-10-29, 2026-11-08
// Scope: Implemented the dispute detail page and status form; added reporter origin and errand
// outcome decisions with a credit preview.
// Author review: I validated correctness and supplied additional boundary checks.

import { type FormEvent, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { adminService, NEXT_STATUSES, type Dispute, type DisputeTarget, type ErrandOutcome } from "../api/admin-service";
import { adminCreditService, type Settlement } from "../api/credit-service";
import { adminOrderService, recordedFailureReasons, type OrderParticipant } from "../api/order-service";
import {
  adminError, allowedOutcomes, clearDraft, creditEffect, disputeOrigin, disputeStatusLabels, errandOutcomeLabels,
  needsRefresh, noReservation, readDraft, shortId, stateLabel, writeDraft,
} from "../app/admin-presentation";
import { orderTime } from "../app/order-presentation";
import { useAdminResource } from "../app/use-admin-resource";
import { useAuth } from "../app/use-auth";
import { AdminFact, AdminPanel, DisputeBadge, OverdueFlag, SettlementFacts } from "../components/admin-ui";
import { OrderBadge } from "../components/order-ui";
import { WorkspaceShell } from "../components/workspace-shell";

const DESCRIPTION = "Oversee errands, disputes and platform analytics.";
// Order keeps at most 500 characters of an administrator's failure reason.
const OUTCOME_REASON_LIMIT = 500;

type StatusFormProps = {
  dispute: Dispute;
  errand: OrderParticipant | null;
  settlement: Settlement | null;
  onChanged: () => void;
};

/**
 * N2F3.3 and N2F3.7: move the dispute through its workflow and, when closing it, optionally
 * decide the errand's outcome. Credits then follow the errand through Order and Credit.
 */
function StatusForm({ dispute, errand, settlement, onChanged }: StatusFormProps) {
  const { withCurrentAccess } = useAuth();
  const options = NEXT_STATUSES[dispute.status];
  const draftKey = `admin-dispute-reason:${dispute.disputeId}`;
  const [target, setTarget] = useState<DisputeTarget | undefined>(options[0]);
  const [outcome, setOutcome] = useState<ErrandOutcome | null>(null);
  const [reason, setReason] = useState(() => readDraft(draftKey, ""));
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState<{ message: string; refresh: boolean } | null>(null);
  const [saving, setSaving] = useState(false);

  if (!target) {
    return <section aria-labelledby="admin-update-status" className="order-panel admin-wide">
      <h2 id="admin-update-status">Update status</h2>
      <p>This dispute is {disputeStatusLabels[dispute.status].toLowerCase()} and cannot change further.</p>
      {dispute.errandOutcome ? <p>{errandOutcomeLabels[dispute.errandOutcome]} with this decision.</p> : null}
    </section>;
  }
  const chosen = target;
  const closing = chosen === "RESOLVED" || chosen === "REJECTED";
  const outcomes = closing && errand ? allowedOutcomes(errand.state) : [];
  const applied = outcome && outcomes.includes(outcome) ? outcome : null;
  // The reserved amount is what moves; fall back to the reward if Credit has not answered.
  const amount = settlement?.state === "RESERVED" ? settlement.amount : errand?.reward ?? 0;

  function invalid(): string | null {
    if (closing && !reason.trim()) return "Give a reason to resolve or reject this dispute.";
    if (applied && reason.trim().length > OUTCOME_REASON_LIMIT) {
      return `Keep the reason within ${OUTCOME_REASON_LIMIT} characters when deciding the errand outcome.`;
    }
    return null;
  }

  function review(event: FormEvent) {
    event.preventDefault();
    const problem = invalid();
    if (problem) {
      setError({ message: problem, refresh: false });
      return;
    }
    setError(null);
    if (applied) setConfirming(true);
    else void save();
  }

  async function save() {
    setSaving(true);
    setError(null);
    try {
      await withCurrentAccess((token) => adminService.transition(dispute.disputeId, {
        toStatus: chosen, reason: reason.trim() || null, expectedVersion: dispute.version,
        ...(applied ? { errandOutcome: applied } : {}),
      }, token));
      clearDraft(draftKey);
      onChanged();
    } catch (failure) {
      setConfirming(false);
      setError({ message: adminError(failure), refresh: needsRefresh(failure) });
    } finally {
      setSaving(false);
    }
  }

  return <section aria-labelledby="admin-update-status" className="order-panel admin-wide">
    <h2 id="admin-update-status">Update status</h2>
    <p className="order-muted">{closing
      ? "Close the case with a reason. You can also decide the errand's outcome; credits then follow the errand."
      : "Review the case before deciding it. The errand outcome can be decided when you resolve or reject."}</p>
    {dispute.reporterRole ? <p className="order-muted">The requester and courier will both see the reason you give when you resolve or reject this report.</p> : null}
    {error ? <div className="admin-panel-error" role="alert">
      <p>{error.message}</p>
      {error.refresh ? <button className="order-button order-secondary" onClick={onChanged} type="button">Refresh dispute</button> : null}
    </div> : null}
    {confirming && applied && errand ? <div aria-labelledby="admin-confirm-decision" className="admin-confirm" role="group">
      <p id="admin-confirm-decision"><strong>Confirm your decision</strong></p>
      <p>Mark this dispute as {disputeStatusLabels[chosen].toLowerCase()} and mark errand #{shortId(errand.orderId)} as {applied === "FAILED" ? "failed" : "completed"}.</p>
      <p>{creditEffect(applied, amount)} This cannot be undone.</p>
      <div className="order-actions">
        <button className="order-button" disabled={saving} onClick={() => void save()} type="button">{saving ? "Applying…" : "Confirm and apply"}</button>
        <button className="order-button order-secondary" disabled={saving} onClick={() => setConfirming(false)} type="button">Back</button>
      </div>
    </div> : <form onSubmit={review}>
      <fieldset className="admin-choices">
        <legend>New status</legend>
        {options.map((option) => <label key={option}>
          <input checked={chosen === option} name="status" onChange={() => setTarget(option)} type="radio" value={option} />
          {disputeStatusLabels[option]}
        </label>)}
      </fieldset>
      {closing ? <fieldset className="admin-choices admin-choices-stacked">
        <legend>Errand outcome</legend>
        <label>
          <input checked={!applied} name="outcome" onChange={() => setOutcome(null)} type="radio" value="NONE" />
          <span>Leave the errand as it is<small>Records your decision only. The errand and its credits stay as they are.</small></span>
        </label>
        {outcomes.map((option) => <label key={option}>
          <input checked={applied === option} name="outcome" onChange={() => setOutcome(option)} type="radio" value={option} />
          <span>{option === "FAILED" ? "Mark the errand as failed" : "Mark the errand as completed"}<small>{creditEffect(option, amount)}</small></span>
        </label>)}
        {!errand ? <p className="order-muted">Errand details are not loaded, so its outcome cannot be changed right now.</p>
          : !outcomes.length ? <p className="order-muted">This errand is {stateLabel(errand.state).toLowerCase()}, so its outcome can no longer be changed here.</p> : null}
      </fieldset> : null}
      <label className="order-label">{closing ? `Reason (required${applied ? `, up to ${OUTCOME_REASON_LIMIT} characters` : ""})` : "Note (optional)"}
        <textarea maxLength={applied ? OUTCOME_REASON_LIMIT : 1000} onChange={(event) => { setReason(event.target.value); writeDraft(draftKey, event.target.value); }} rows={3} value={reason} />
      </label>
      <button className="order-button" disabled={saving} type="submit">{saving ? "Saving…" : applied ? "Review decision" : `Mark as ${disputeStatusLabels[chosen].toLowerCase()}`}</button>
    </form>}
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
  // A decision can change the errand and its credits, so refresh every panel together.
  const reloadAll = () => {
    dispute.reload();
    order.reload();
    settlement.reload();
  };

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
            {data.errandOutcome ? <AdminFact label="Errand outcome">{errandOutcomeLabels[data.errandOutcome]}</AdminFact> : null}
          </dl>
        </> : null}
      </AdminPanel>

      <AdminPanel resource={dispute} title="Case history">
        {data ? <ol className="order-history">
          {data.history.map((entry) => <li key={entry.sequence}>
            <strong>{entry.fromStatus ? `${disputeStatusLabels[entry.fromStatus]} → ` : ""}{disputeStatusLabels[entry.toStatus]}</strong>
            {entry.reason ? <small>{entry.reason}</small> : null}
            {entry.errandOutcome ? <small>{errandOutcomeLabels[entry.errandOutcome]}</small> : null}
            <small>Admin {shortId(entry.actorId)}</small>
            <time dateTime={entry.occurredAt}>{orderTime(entry.occurredAt)} SGT</time>
          </li>)}
        </ol> : null}
      </AdminPanel>

      <AdminPanel resource={order} title="Errand state">
        {errand ? <>
          <p className="admin-badges"><OrderBadge state={errand.state} />{errand.overdueAt ? <OverdueFlag /> : null}</p>
          <p>{errand.itemDescription}</p>
          {errand.failureReason ? <p className="order-muted">Failure reason: {recordedFailureReasons[errand.failureReason]}</p> : null}
          {errand.decidedByAdministrator ? <p className="order-muted">Decided by an administrator{errand.decisionDisputeId ? ` for dispute #${shortId(errand.decisionDisputeId)}` : ""}.</p> : null}
          <Link to={`/admin/orders/${errand.orderId}`}>View errand and its history</Link>
        </> : null}
      </AdminPanel>

      <AdminPanel resource={settlement} title="Credit settlement">
        <SettlementFacts errandState={errand?.state} settlement={settlement.data} />
      </AdminPanel>

      {data ? <StatusForm
        dispute={data}
        errand={errand}
        key={`${data.disputeId}:${data.version}`}
        onChanged={reloadAll}
        settlement={settlement.data}
      /> : null}
    </div>
  </WorkspaceShell>;
}
