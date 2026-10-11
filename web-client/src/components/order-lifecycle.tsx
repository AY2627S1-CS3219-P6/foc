import { useEffect, useRef, useState } from "react";
import { isApiRequestError } from "../api/client";
import { orderService, type OrderDetail, type OrderParticipant } from "../api/order-service";
import { orderError } from "../app/order-presentation";
import { useAuth } from "../app/use-auth";

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
  const inFlight = useRef(false);
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => { mounted.current = false; window.clearInterval(timer); };
  }, []);
  const requester = "requesterId" in order && order.requesterId === user?.userId;
  // Assessment responses omit requester IDs; the server still enforces self-acceptance.
  const action = requester ? "cancel" : "accept";
  const closed = order.state !== "OPEN";
  const deadlinePassed = now >= Date.parse(order.acceptanceDeadline);
  async function submit() {
    if (inFlight.current || closed || (deadlinePassed && !uncertain)) return;
    inFlight.current = true; setBusy(true); setError(null); setNotice(null);
    try {
      const updated = await withCurrentAccess((token) => orderService[action](order.orderId, token));
      if (!mounted.current) return;
      setUncertain(false); setConfirming(false);
      setNotice(action === "accept" ? "You accepted this errand." : "Errand cancelled. Credit release is processed separately.");
      onChanged(updated);
    } catch (failure) {
      if (!mounted.current) return;
      const unknown = !isApiRequestError(failure) || failure.status === 0 || failure.status >= 500;
      setUncertain(unknown);
      setError(unknown ? "We could not confirm the result. Retry the same action safely, or refresh the errand to check its status." : orderError(failure));
    } finally {
      inFlight.current = false;
      if (mounted.current) setBusy(false);
    }
  }
  return <section className="order-panel" aria-label="Errand actions" aria-busy={busy}>
    <h2>Errand actions</h2>
    {notice ? <p role="status">{notice}</p> : null}
    {error ? <p role="alert">{error}</p> : null}
    {closed ? <p>No accept or cancel action is available for a {order.state.toLowerCase().replaceAll("_", " ")} errand.</p>
      : deadlinePassed && !uncertain ? <p>The acceptance deadline has passed. Expiry is processed automatically; refresh to see the latest status.</p>
      : <>
        <p>{requester ? "You can cancel until someone accepts or the acceptance deadline passes." : "Accept this errand to become its courier. You cannot cancel it after accepting."}</p>
        {confirming && !uncertain ? <p>Cancel this errand? This cannot be undone.</p> : null}
        <div className="order-actions">
          <button className="order-button" disabled={busy} type="button" onClick={() => requester && !confirming && !uncertain ? setConfirming(true) : void submit()}>
            {busy ? "Confirming…" : uncertain ? `Retry ${action}` : requester ? confirming ? "Confirm cancellation" : "Cancel errand" : "Accept errand"}
          </button>
          {confirming && !uncertain ? <button className="order-button order-secondary" disabled={busy} type="button" onClick={() => setConfirming(false)}>Keep errand</button> : null}
        </div>
      </>}
    <button className="order-text-button" disabled={busy} type="button" onClick={onRefresh}>Refresh errand</button>
    <p className="order-muted">Availability and deadlines are checked by the server. Pickup, delivery and completion controls will follow.</p>
  </section>;
}
