import { type FormEvent, useEffect, useState } from "react";
import { disputeReports, type DisputeReport } from "../api/admin-service";
import { isApiRequestError } from "../api/client";
import type { OrderState } from "../api/order-service";
import { clearDraft, readDraft, writeDraft } from "../app/admin-presentation";
import { orderError, orderTime } from "../app/order-presentation";
import { useAuth } from "../app/use-auth";
import { DisputeBadge } from "./admin-ui";

// Admin Service accepts reports once a courier has accepted the errand.
const REPORTABLE_STATES: OrderState[] = ["ACCEPTED", "PICKED_UP", "DELIVERED", "COMPLETED", "FAILED"];

const messages: Record<string, string> = {
  REPORT_ALREADY_OPEN: "You already have an open report about this errand.",
  REPORT_NOT_ALLOWED: "Problems can be reported once a courier accepts the errand.",
  ORDER_NOT_FOUND: "Only the requester or courier can report a problem with this errand.",
  ORDER_UNAVAILABLE: "Errand records are unavailable, so nothing was sent. Try again.",
  IDEMPOTENCY_KEY_REUSED: "This form was already used for a different report. Reload the page and try again.",
};

function reportError(failure: unknown): string {
  return isApiRequestError(failure) && messages[failure.code] ? messages[failure.code] : orderError(failure);
}

const awaitingDecision = (report: DisputeReport) => report.status === "OPEN" || report.status === "UNDER_REVIEW";

/** N2F3.2: the requester or courier reports a problem; an administrator reviews it and decides. */
export function ErrandReportPanel({ orderId, state }: { orderId: string; state: OrderState }) {
  const { withCurrentAccess } = useAuth();
  const draftKey = `errand-report-draft:${orderId}`;
  const [reports, setReports] = useState<DisputeReport[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [reload, setReload] = useState(0);
  const [description, setDescription] = useState(() => readDraft(draftKey, ""));
  // One key per report: retrying after an ambiguous failure returns the original (N2NFR3.3).
  const [idempotencyKey, setIdempotencyKey] = useState(() => crypto.randomUUID());
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let active = true;
    setLoadError(null);
    withCurrentAccess((token) => disputeReports.mine({ orderId, pageSize: 50 }, token))
      .then((page) => { if (active) setReports(page.items); })
      .catch((failure) => { if (active) setLoadError(reportError(failure)); });
    return () => { active = false; };
  }, [orderId, reload, withCurrentAccess]);

  function update(value: string) {
    setDescription(value);
    writeDraft(draftKey, value);
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const report = await withCurrentAccess((token) => disputeReports.report(
        { orderId, description: description.trim() }, idempotencyKey, token,
      ));
      clearDraft(draftKey);
      setDescription("");
      setIdempotencyKey(crypto.randomUUID());
      setReports((current) => [report, ...(current ?? []).filter((item) => item.disputeId !== report.disputeId)]);
    } catch (failure) {
      setError(reportError(failure));
      if (isApiRequestError(failure) && failure.code === "REPORT_ALREADY_OPEN") setReload((n) => n + 1);
    } finally {
      setSaving(false);
    }
  }

  return <section aria-labelledby="errand-report-heading" className="order-panel">
    <h2 id="errand-report-heading">Report a problem</h2>
    {loadError ? <p role="alert">{loadError} <button className="order-text-button" onClick={() => setReload((n) => n + 1)} type="button">Retry reports</button></p>
      : reports === null ? <p role="status">Loading reports…</p> : <>
        {reports.length ? <ol className="order-history">{reports.map((report) => <li key={report.disputeId}>
          <DisputeBadge status={report.status} />
          <time dateTime={report.createdAt}>Reported {orderTime(report.createdAt)} SGT</time>
          <p>{report.description}</p>
          {report.resolutionReason ? <p><strong>Decision:</strong> {report.resolutionReason}</p> : null}
        </li>)}</ol> : null}
        {reports.some(awaitingDecision)
          ? <p className="order-muted">An administrator is reviewing your report. You can report again after a decision.</p>
          : REPORTABLE_STATES.includes(state) ? <>
            <p className="order-muted">Describe what went wrong. An administrator reviews it and records a decision; reporting does not change the errand or move credits.</p>
            {error ? <p className="admin-form-error" role="alert">{error}</p> : null}
            <form onSubmit={submit}>
              <label className="order-label">What went wrong<textarea maxLength={2000} onChange={(event) => update(event.target.value)} required rows={4} value={description} /></label>
              <button className="order-button" disabled={saving || !description.trim()} type="submit">{saving ? "Sending…" : "Report problem"}</button>
            </form>
          </> : !reports.length ? <p className="order-muted">No problems reported.</p> : null}
      </>}
  </section>;
}
