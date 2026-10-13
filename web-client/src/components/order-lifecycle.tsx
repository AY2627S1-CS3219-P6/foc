import { useEffect, useRef, useState } from "react";
import { isApiRequestError } from "../api/client";
import { failureReasons, orderService, type FailureReason, type OrderAction, type OrderDetail, type OrderFailureInput, type OrderParticipant } from "../api/order-service";
import { orderError, orderTime } from "../app/order-presentation";
import { useAuth } from "../app/use-auth";

const labels: Record<OrderAction, string> = {
  accept: "Accept errand", cancel: "Cancel errand", pickup: "Mark picked up",
  deliver: "Mark delivered", complete: "Confirm received",
};
const notices: Record<OrderAction, string> = {
  accept: "You accepted this errand.", cancel: "Errand cancelled. Your reserved credits will be returned.",
  pickup: "Pickup recorded.", deliver: "Delivery recorded. Waiting for the requester to confirm receipt.",
  complete: "Errand completed. Reward payment is not confirmed yet.",
};

export function OrderLifecycle({ order, onChanged, onRefresh }: {
  order: OrderDetail; onChanged: (order: OrderParticipant) => void; onRefresh: () => void;
}) {
  const { user, withCurrentAccess } = useAuth();
  const [now, setNow] = useState(Date.now);
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [failing, setFailing] = useState(false);
  const [reason, setReason] = useState<FailureReason | "">("");
  const [details, setDetails] = useState("");
  const [uncertainFailure, setUncertainFailure] = useState(false);
  const failureRequest = useRef<OrderFailureInput | null>(null);
  const inFlight = useRef(false);
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => { mounted.current = false; window.clearInterval(timer); };
  }, []);
  const requester = "requesterId" in order && order.requesterId === user?.userId;
  const courier = "courierId" in order && order.courierId === user?.userId;
  const canFail = (requester || courier) && (order.state === "ACCEPTED" || order.state === "PICKED_UP");
  // Assessment responses omit requester IDs; the server still enforces self-acceptance.
  const action: OrderAction | null = order.state === "OPEN" ? requester ? "cancel" : "accept"
    : order.state === "ACCEPTED" && courier ? "pickup"
      : order.state === "PICKED_UP" && courier ? "deliver"
        : order.state === "DELIVERED" && requester ? "complete" : null;
  const deadlinePassed = order.state === "OPEN" && now >= Date.parse(order.acceptanceDeadline);
  const confirmRequired = action === "cancel" || action === "complete";
  async function submit() {
    if (inFlight.current || failing || !action || (deadlinePassed && !uncertain)) return;
    inFlight.current = true; setBusy(true); setError(null); setNotice(null);
    try {
      const updated = await withCurrentAccess((token) => orderService[action](order.orderId, token));
      if (!mounted.current) return;
      setUncertain(false); setConfirming(false);
      setNotice(notices[action]);
      onChanged(updated);
    } catch (failure) {
      if (!mounted.current) return;
      const unknown = !isApiRequestError(failure) || failure.status === 0 || failure.status >= 500;
      setUncertain(unknown);
      setError(unknown ? "We could not confirm the update. Try again here, or refresh to check the errand." : orderError(failure));
    } finally {
      inFlight.current = false;
      if (mounted.current) setBusy(false);
    }
  }
  async function submitFailure() {
    if (inFlight.current || !canFail || !reason || (reason === "OTHER" && !details.trim())) return;
    const input = failureRequest.current ?? { reason, details: details.trim() || null };
    failureRequest.current = input;
    inFlight.current = true; setBusy(true); setError(null); setNotice(null);
    try {
      const updated = await withCurrentAccess((token) => orderService.fail(order.orderId, input, token));
      if (!mounted.current) return;
      setFailing(false); setUncertainFailure(false); failureRequest.current = null;
      setNotice("Errand marked failed. Reserved credits will be returned to the requester.");
      onChanged(updated);
    } catch (failure) {
      if (!mounted.current) return;
      const unknown = !isApiRequestError(failure) || failure.status === 0 || failure.status >= 500;
      setUncertainFailure(unknown);
      if (!unknown) failureRequest.current = null;
      setError(unknown ? "We could not confirm your report. Try again here, or refresh to check the errand." : orderError(failure));
    } finally {
      inFlight.current = false;
      if (mounted.current) setBusy(false);
    }
  }
  return <section className="order-panel" aria-label="Errand actions" aria-busy={busy}>
    <h2>Errand actions</h2>
    {notice ? <p role="status">{notice}</p> : null}
    {error ? <p role="alert">{error}</p> : null}
    {"overdueAt" in order && order.overdueAt ? <p role="status">{order.state === "FAILED" ? "Was overdue" : order.state === "ACCEPTED" || order.state === "PICKED_UP" ? "Delivery overdue" : "Delivered late"} since {orderTime(order.overdueAt)} SGT.{order.state === "ACCEPTED" || order.state === "PICKED_UP" ? " Late delivery is still allowed." : ""}</p> : null}
    {order.state === "FAILED" && "failureReason" in order && order.failureReason ? <div>
      <p>Failure reason: {failureReasons[order.failureReason]}.</p>
      {order.failureDetails ? <p>{order.failureDetails}</p> : null}
      <p>Recorded by the {order.failedBy === order.requesterId ? "requester" : "courier"}{order.failedAt ? ` on ${orderTime(order.failedAt)} SGT` : ""}.</p>
      {!notice ? <p>Reserved credits will be returned to the requester.</p> : null}
    </div> : null}
    {order.state === "COMPLETED" && !notice ? <p>{notices.complete}</p> : null}
    {!action ? order.state === "ACCEPTED" || order.state === "PICKED_UP" ? <p>Waiting for the assigned courier to update the errand.</p> : order.state === "DELIVERED" ? <p>Waiting for the requester to confirm receipt.</p> : order.state === "EXPIRED" ? <p>No one accepted this errand in time.</p> : null
      : deadlinePassed && !uncertain ? <p>The acceptance deadline has passed. Refresh to check the errand.</p>
      : <>
        <p>{action === "cancel" ? "You can cancel until someone accepts or the acceptance deadline passes." : action === "accept" ? "Accept this errand to become its courier. You cannot cancel it after accepting." : action === "pickup" ? "Mark picked up only after collecting the requested item." : action === "deliver" ? "Mark delivered only after handing over the item. The requester must confirm receipt before you receive the reward." : "Confirm only after receiving the item. Your courier can then receive the reward."}</p>
        {confirming && !uncertain ? <p>{action === "cancel" ? "Cancel this errand? This cannot be undone." : "Have you received the item? Completion cannot be undone."}</p> : null}
        <div className="order-actions">
          <button className="order-button" disabled={busy || failing} type="button" onClick={() => confirmRequired && !confirming && !uncertain ? setConfirming(true) : void submit()}>
            {busy ? "Confirming…" : uncertain ? "Try again" : confirming ? action === "cancel" ? "Confirm cancellation" : "Complete errand" : labels[action]}
          </button>
          {confirming && !uncertain ? <button className="order-button order-secondary" disabled={busy} type="button" onClick={() => setConfirming(false)}>{action === "cancel" ? "Keep errand" : "Not yet"}</button> : null}
        </div>
      </>}
    {canFail ? failing ? <form onSubmit={(event) => { event.preventDefault(); void submitFailure(); }}>
      <p>End this errand as failed? This cannot be undone. Reserved credits will be returned to the requester.</p>
      <label className="order-label">Failure reason
        <select required value={reason} disabled={busy || uncertainFailure} onChange={(event) => setReason(event.target.value as FailureReason | "")}>
          <option value="">Select a reason</option>
          {Object.entries(failureReasons).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
      </label>
      <label className="order-label">Failure details{reason === "OTHER" ? " (required)" : " (optional)"}
        <textarea maxLength={500} required={reason === "OTHER"} value={details} disabled={busy || uncertainFailure} onChange={(event) => setDetails(event.target.value)} />
      </label>
      <p className="order-muted">Share what happened. Both of you can read this; avoid private contact details.</p>
      <div className="order-actions">
        <button className="order-button" type="submit" disabled={busy || !reason || (reason === "OTHER" && !details.trim())}>{busy ? "Confirming…" : uncertainFailure ? "Try again" : "Confirm failure"}</button>
        {!uncertainFailure ? <button className="order-button order-secondary" type="button" disabled={busy} onClick={() => { setFailing(false); setError(null); }}>Keep errand</button> : null}
      </div>
    </form> : <button className="order-button order-secondary" type="button" disabled={busy || uncertain} onClick={() => { setFailing(true); setConfirming(false); setError(null); setNotice(null); }}>Mark failed</button> : null}
    <button className="order-text-button" disabled={busy} type="button" onClick={onRefresh}>Refresh errand</button>
  </section>;
}
