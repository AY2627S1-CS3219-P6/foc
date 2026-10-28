import { requestJson } from "./client";

export type DisputeStatus = "OPEN" | "UNDER_REVIEW" | "RESOLVED" | "REJECTED";
export type DisputeTarget = Exclude<DisputeStatus, "OPEN">;

export type DisputeHistoryEntry = {
  sequence: number;
  fromStatus: DisputeStatus | null;
  toStatus: DisputeStatus;
  actorId: string;
  reason: string | null;
  occurredAt: string;
};

export type DisputeSummary = {
  disputeId: string;
  orderId: string;
  description: string;
  status: DisputeStatus;
  resolutionReason: string | null;
  createdBy: string;
  createdAt: string;
  updatedAt: string;
  version: number;
};

export type Dispute = DisputeSummary & { evidenceRefs: string[]; history: DisputeHistoryEntry[] };

export type AuditEntry = {
  auditId: string;
  actorId: string;
  action: "DISPUTE_CREATE" | "DISPUTE_TRANSITION";
  targetType: "DISPUTE" | "ORDER";
  targetId: string;
  outcome: "SUCCESS" | "REJECTED";
  errorCode: string | null;
  correlationId: string;
  occurredAt: string;
};

export type AdminPage<T> = { items: T[]; page: number; pageSize: number; total: number };
export type NewDispute = { orderId: string; description: string; evidenceRefs: string[] };
export type DisputeTransition = { toStatus: DisputeTarget; reason: string | null; expectedVersion: number };

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
