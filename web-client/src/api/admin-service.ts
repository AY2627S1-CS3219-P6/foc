// AI Assistance Disclosure:
// Tool: Claude Code (model: Claude Opus 5.5), date: 2026-10-28, 2026-10-29, 2026-11-08
// Scope: Implemented the Admin Service client for disputes, reports, status changes and the
// audit log; added errand outcomes.
// Author review: I validated correctness and supplied additional boundary checks.

import { requestJson } from "./client";

export type DisputeStatus = "OPEN" | "UNDER_REVIEW" | "RESOLVED" | "REJECTED";
export type DisputeTarget = Exclude<DisputeStatus, "OPEN">;
export type ReporterRole = "REQUESTER" | "COURIER";
// N2F3.7: the errand outcome an administrator applied through Order when closing a dispute.
export type ErrandOutcome = "FAILED" | "COMPLETED";

export type DisputeHistoryEntry = {
  sequence: number;
  fromStatus: DisputeStatus | null;
  toStatus: DisputeStatus;
  actorId: string;
  reason: string | null;
  errandOutcome?: ErrandOutcome | null;
  occurredAt: string;
};

export type DisputeSummary = {
  disputeId: string;
  orderId: string;
  description: string;
  status: DisputeStatus;
  resolutionReason: string | null;
  errandOutcome?: ErrandOutcome | null;
  // Null when an administrator recorded the dispute rather than an errand participant.
  reporterRole: ReporterRole | null;
  createdBy: string;
  createdAt: string;
  updatedAt: string;
  version: number;
};

export type Dispute = DisputeSummary & { evidenceRefs: string[]; history: DisputeHistoryEntry[] };

export type AuditEntry = {
  auditId: string;
  actorId: string;
  action: "DISPUTE_CREATE" | "DISPUTE_REPORT" | "DISPUTE_TRANSITION" | "ERRAND_DECISION";
  targetType: "DISPUTE" | "ORDER";
  targetId: string;
  outcome: "SUCCESS" | "REJECTED";
  errorCode: string | null;
  correlationId: string;
  occurredAt: string;
};

// What an errand participant sees: never the administrators or the history, and the
// description only for their own reports.
export type DisputeReport = Pick<
  DisputeSummary, "disputeId" | "orderId" | "status" | "resolutionReason" | "errandOutcome" | "createdAt" | "updatedAt"
> & { reporterRole: ReporterRole; ownReport: boolean; description: string | null };

export type AdminPage<T> = { items: T[]; page: number; pageSize: number; total: number };
export type NewDispute = { orderId: string; description: string; evidenceRefs: string[] };
export type NewReport = { orderId: string; description: string };
export type DisputeTransition = {
  toStatus: DisputeTarget;
  reason: string | null;
  expectedVersion: number;
  errandOutcome?: ErrandOutcome | null;
};

// N2F3.3.1: OPEN -> UNDER_REVIEW -> RESOLVED | REJECTED. Admin Service enforces this too.
export const NEXT_STATUSES: Record<DisputeStatus, DisputeTarget[]> = {
  OPEN: ["UNDER_REVIEW"],
  UNDER_REVIEW: ["RESOLVED", "REJECTED"],
  RESOLVED: [],
  REJECTED: [],
};

function query(values: Record<string, string | number | undefined>): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(values)) {
    if (value !== undefined && value !== "") params.set(key, String(value));
  }
  return params.size ? `?${params}` : "";
}

export const adminService = {
  // Reuse the same key and body after an ambiguous failure so a retry cannot duplicate a dispute.
  createDispute: (input: NewDispute, idempotencyKey: string, token: string) =>
    requestJson<Dispute>("/admin/disputes", {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: JSON.stringify(input),
    }, token),
  disputes: (filters: { page?: number; pageSize?: number; status?: DisputeStatus; orderId?: string }, token: string) =>
    requestJson<AdminPage<DisputeSummary>>(`/admin/disputes${query(filters)}`, { method: "GET" }, token),
  dispute: (disputeId: string, token: string) =>
    requestJson<Dispute>(`/admin/disputes/${encodeURIComponent(disputeId)}`, { method: "GET" }, token),
  transition: (disputeId: string, input: DisputeTransition, token: string) =>
    requestJson<Dispute>(`/admin/disputes/${encodeURIComponent(disputeId)}/transitions`, {
      method: "POST",
      body: JSON.stringify(input),
    }, token),
  auditLog: (filters: { page?: number; pageSize?: number }, token: string) =>
    requestJson<AdminPage<AuditEntry>>(`/admin/audit-log${query(filters)}`, { method: "GET" }, token),
};

// N2F3.2: requesters and couriers report problems with their own errands; administrators decide.
export const disputeReports = {
  report: (input: NewReport, idempotencyKey: string, token: string) =>
    requestJson<DisputeReport>("/disputes", {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: JSON.stringify(input),
    }, token),
  // With orderId: every participant report about that errand, for its requester or courier.
  list: (filters: { orderId?: string; page?: number; pageSize?: number }, token: string) =>
    requestJson<AdminPage<DisputeReport>>(`/disputes${query(filters)}`, { method: "GET" }, token),
};
