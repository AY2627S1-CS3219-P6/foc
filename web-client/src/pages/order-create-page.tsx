import { type FormEvent, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { isApiRequestError } from "../api/client";
import { emptyOrderForm, formFromInput, readAttempt, saveAttempt, validateOrderForm, type CreationAttempt, type OrderForm } from "../api/order-draft";
import { orderService, type OrderCreation, type OrderParticipant } from "../api/order-service";
import { useAuth } from "../app/use-auth";
import { FormField } from "../components/form-field";
import { OrderSupplierPicker } from "../components/order-supplier-picker";
import { OrderBadge, OrderShell, OrderSummary } from "../components/order-ui";
import { orderError } from "../app/order-presentation";

export function OrderCreatePage() {
  const { user } = useAuth();
  return user ? <OrderCreateForm key={user.userId} userId={user.userId} /> : null;
}

function OrderCreateForm({ userId }: { userId: string }) {
  const { withCurrentAccess } = useAuth();
  const [initial] = useState(() => {
    try { return { attempt: readAttempt(userId), error: null }; }
    catch { return { attempt: null, error: "We could not restore your saved request. Check My errands and reload this page before posting again." }; }
  });
  const [attempt, setAttempt] = useState<CreationAttempt | null>(initial.attempt);
  const [storageError, setStorageError] = useState<string | null>(initial.error);
  const [form, setForm] = useState<OrderForm>(() => initial.attempt ? formFromInput(initial.attempt.input) : { ...emptyOrderForm });
  const [fields, setFields] = useState<Partial<Record<keyof OrderForm, string>>>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const inFlight = useRef(false);
  const [success, setSuccess] = useState<OrderParticipant | null>(null);
  const errorRef = useRef<HTMLDivElement>(null);
  const locked = Boolean(attempt) || busy || Boolean(storageError);

  function persist(next: CreationAttempt | null) {
    try { saveAttempt(userId, next); setAttempt(next); return true; }
    catch { setStorageError("Your browser could not save the request details. Check My errands and reload this page before posting again."); return false; }
  }

  function acceptProgress(next: OrderCreation) {
    setAttempt((current) => current ? { ...current, operation: next, closed: next.stage === "ABORTED" } : current);
    if (next.stage === "ABORTED" && attempt) {
      try { saveAttempt(userId, { ...attempt, closed: true }); }
      catch { setStorageError("We could not save the latest update. Reload before creating another errand."); }
    }
  }

  const operationId = attempt?.operation?.operationId;
  const stage = attempt?.operation?.stage;
  useEffect(() => {
    if (!operationId || stage === "ABORTED" || stage === "SUCCEEDED" || stage === "READY_TO_FINALIZE") return;
    let active = true;
    let timer: number;
    async function poll() {
      if (!inFlight.current) {
        try {
          const next = await withCurrentAccess((token) => orderService.creation(operationId!, token));
          if (active) { setAttempt((current) => current ? { ...current, operation: next, closed: next.stage === "ABORTED" } : current); setError(null); }
        } catch (failure) { if (active) setError(orderError(failure)); }
      }
      if (active) timer = window.setTimeout(poll, 5000);
    }
    timer = window.setTimeout(poll, 5000);
    return () => { active = false; window.clearTimeout(timer); };
  }, [operationId, stage, withCurrentAccess]);

  async function submit(event?: FormEvent) {
    event?.preventDefault();
    if (inFlight.current || storageError || attempt?.closed) return;
    let current = attempt;
    if (!current) {
      const validated = validateOrderForm(form);
      setFields(validated.errors);
      if (!validated.input) { setError("Check the highlighted fields before posting."); window.setTimeout(() => errorRef.current?.focus(), 0); return; }
      current = { key: crypto.randomUUID(), input: validated.input };
      if (!persist(current)) return;
    }
    inFlight.current = true; setBusy(true); setError(null);
    try {
      const response = await withCurrentAccess((token) => orderService.create(current.input, current.key, token));
      if ("operationId" in response) {
        const next = { ...current, operation: response, closed: response.stage === "ABORTED" };
        persist(next);
      } else {
        setSuccess(response);
        persist(null);
      }
    } catch (failure) {
      setError(orderError(failure));
      if (isApiRequestError(failure)) {
        const mapped: Partial<Record<keyof OrderForm, string>> = {};
        for (const field of failure.fieldErrors) if (field.field in emptyOrderForm) mapped[field.field as keyof OrderForm] = field.message;
        setFields(mapped);
        // Validation occurs before any creation side effect. Other failures can
        // be ambiguous: retain the key/body instead of permitting a duplicate.
        if (failure.status === 422) persist(null);
        // These 409 codes mean a closed operation (or a pre-creation Supplier
        // rejection with no reservation). Never discard unknown conflicts.
        if (failure.status === 409 && ["CREATION_ABORTED", "INSUFFICIENT_CREDIT", "WALLET_NOT_READY", "DEADLINE_PASSED", "SUPPLIER_UNAVAILABLE"].includes(failure.code)) persist({ ...current, closed: true });
      }
    } finally { inFlight.current = false; setBusy(false); }
  }

  async function checkProgress() {
    if (!operationId || inFlight.current) return;
    inFlight.current = true; setBusy(true); setError(null);
    try { acceptProgress(await withCurrentAccess((token) => orderService.creation(operationId, token))); }
    catch (failure) { setError(orderError(failure)); }
    finally { inFlight.current = false; setBusy(false); }
  }

  function update(field: keyof OrderForm, value: string) { setForm((current) => ({ ...current, [field]: value })); }
  function reset() { if (persist(null)) { setForm({ ...emptyOrderForm }); setSuccess(null); setError(null); setFields({}); } }
  return <OrderShell>
    <Link className="order-back" to="/orders">← Open errands</Link>
    {success ? <>
      <div className="order-heading"><div><h1>{success.state === "OPEN" ? "Your errand is open" : "Your errand is confirmed"}</h1><p>{success.state === "OPEN" ? "Your errand is ready for someone to accept." : "Your errand was already posted. Here is its latest update."}</p></div></div>
      <section className="order-panel order-confirmation"><OrderBadge state={success.state} /><h2>{success.itemDescription}</h2><OrderSummary order={success} /><Link to={`/orders/${success.orderId}`}>View errand details</Link></section>
      <div className="order-actions"><Link className="order-button" to="/orders/mine">View my errands</Link><button className="order-button order-secondary" disabled={Boolean(storageError)} type="button" onClick={reset}>Create another</button></div>
    </> : <>
      <div className="order-heading"><div><h1>Create an errand</h1><p>Choose a pickup supplier, set the deadlines and offer a credit reward.</p></div></div>
      {attempt ? <section className="order-panel order-pending" aria-label="Creation progress"><h2>{attempt.closed ? "Your errand was not posted" : attempt.operation?.stage === "SUCCEEDED" ? "Your errand is posted" : "Checking your errand"}</h2>
        <p>{attempt.closed ? "You can create a new errand now." : attempt.operation?.stage === "SUCCEEDED" ? "View your errand below." : "We are checking whether your errand was posted. Keep this page open and do not post it again."}</p>
        <div className="order-actions">
          {attempt.closed ? <button className="order-button" type="button" disabled={busy || Boolean(storageError)} onClick={reset}>Start a new request</button> : attempt.operation?.stage === "SUCCEEDED" && attempt.operation.orderId ? <><Link className="order-button" to={`/orders/${attempt.operation.orderId}`}>View confirmed errand</Link><button className="order-button order-secondary" type="button" disabled={busy || Boolean(storageError)} onClick={reset}>Create another</button></> : <button className="order-button" disabled={busy || Boolean(storageError) || Boolean(attempt.operation && !attempt.operation.retryCreation)} type="button" onClick={() => void submit()}>{busy ? "Checking…" : attempt.operation?.retryCreation ? "Finish posting errand" : "Try again"}</button>}
          {operationId && !attempt.closed ? <button className="order-button order-secondary" disabled={busy} type="button" onClick={() => void checkProgress()}>Check status</button> : null}
        </div>
      </section> : null}
      {error ? <div className="order-error order-panel" role="alert" tabIndex={-1} ref={errorRef}>{error}</div> : null}
      <form className="order-create-grid" noValidate onSubmit={(event) => void submit(event)}>
        <fieldset disabled={locked} className="order-form-fields"><legend className="sr-only">Errand details</legend>
          <OrderSupplierPicker required value={form.supplierId} onChange={(value) => update("supplierId", value)} disabled={locked} />
          {fields.supplierId ? <p className="field-error" role="alert">{fields.supplierId}</p> : null}
          <FormField label="Delivery location" value={form.deliveryLocation} onChange={(event) => update("deliveryLocation", event.target.value)} maxLength={300} required error={fields.deliveryLocation} placeholder="e.g. COM3 level 1 collection point" />
          <FormField label="Latest acceptance time (SGT)" type="datetime-local" value={form.acceptanceDeadline} onChange={(event) => update("acceptanceDeadline", event.target.value)} required error={fields.acceptanceDeadline} />
          <FormField label="Latest delivery time (SGT)" type="datetime-local" value={form.deliveryDeadline} onChange={(event) => update("deliveryDeadline", event.target.value)} required error={fields.deliveryDeadline} hint="Dates and times are shown in Singapore time." />
        </fieldset>
        <div><fieldset disabled={locked} className="order-form-fields"><legend className="sr-only">Instructions and reward</legend>
          <label className="order-label">Instructions<textarea aria-label="Instructions" required maxLength={1000} rows={4} value={form.itemDescription} onChange={(event) => update("itemDescription", event.target.value)} aria-invalid={Boolean(fields.itemDescription)} aria-describedby={fields.itemDescription ? "order-description-error" : "order-description-hint"} placeholder="e.g. One vegetarian sandwich, no chilli" /></label>
          {fields.itemDescription ? <p className="field-error" role="alert" id="order-description-error">{fields.itemDescription}</p> : <p className="field-hint" id="order-description-hint">Visible to people browsing this errand. Do not include private contact details.</p>}
          <FormField label="Credit reward" type="number" min={1} max={2147483647} step={1} value={form.reward} onChange={(event) => update("reward", event.target.value)} error={fields.reward} required hint="Whole-number credits only." />
        </fieldset>
          <section className="order-panel order-reservation"><h2>Your reward</h2><p>The reward is set aside when your errand is posted.</p><p>Your courier can receive it after you confirm receipt of the item.</p></section>
          {!attempt ? <button className="order-button order-submit" disabled={locked} type="submit">{busy ? "Posting…" : "Post errand"}</button> : null}
        </div>
      </form>
    </>}
    {storageError ? <p className="order-panel order-error" role="alert">{storageError}</p> : null}
  </OrderShell>;
}
