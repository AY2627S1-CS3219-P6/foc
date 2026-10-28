import { isApiRequestError } from "../api/client";
import type { DisputeStatus } from "../api/admin-service";
import type { OrderState } from "../api/order-service";
import { orderError } from "./order-presentation";

export const LIVE_STATES: OrderState[] = ["OPEN", "ACCEPTED", "PICKED_UP", "DELIVERED"];
export const PAST_STATES: OrderState[] = ["COMPLETED", "CANCELLED", "EXPIRED", "FAILED"];
export const ALL_STATES: OrderState[] = [...LIVE_STATES, ...PAST_STATES];

export const disputeStatusLabels: Record<DisputeStatus, string> = {
  OPEN: "Open",
  UNDER_REVIEW: "Under review",
  RESOLVED: "Resolved",
  REJECTED: "Rejected",
};

export const stateLabel = (state: OrderState) => state.replaceAll("_", " ");

const singaporeDay = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Singapore" });
const singaporeClock = new Intl.DateTimeFormat("en-SG", {
  timeZone: "Asia/Singapore", hour: "2-digit", minute: "2-digit", hour12: false,
});
const calendarDay = new Intl.DateTimeFormat("en-SG", { timeZone: "UTC", day: "numeric", month: "short" });

/** Today's Asia/Singapore calendar date as YYYY-MM-DD, matching the analytics periods. */
export function singaporeToday(now = new Date()): string {
  return singaporeDay.format(now);
}

export function shiftDay(day: string, offset: number): string {
  const [year, month, date] = day.split("-").map(Number);
  return new Date(Date.UTC(year, month - 1, date + offset)).toISOString().slice(0, 10);
}

export function dayLabel(day: string): string {
  const [year, month, date] = day.split("-").map(Number);
  return calendarDay.format(new Date(Date.UTC(year, month - 1, date)));
}

// N2F4.2.2: a rate without errands is N/A, never 0%.
export function percent(rate: number | null): string {
  return rate === null ? "N/A" : `${Math.round(rate * 1000) / 10}%`;
}

export function duration(minutes: number | null): string {
  if (minutes === null) return "N/A";
  const whole = Math.round(minutes);
  return whole < 60 ? `${whole} min` : `${Math.floor(whole / 60)} h ${whole % 60} min`;
}

export function shortId(id: string | null | undefined): string {
  return id ? id.slice(0, 8).toUpperCase() : "—";
}

export function updatedAt(time: Date): string {
  return `Updated ${singaporeClock.format(time)} SGT`;
}

const messages: Record<string, string> = {
  VERSION_CONFLICT: "This dispute was changed by someone else. Refresh and review it before trying again.",
  INVALID_TRANSITION: "This status change is no longer allowed. Refresh to see the current status.",
  REASON_REQUIRED: "Give a reason to resolve or reject this dispute.",
  ORDER_NOT_FOUND: "No errand has this ID.",
  ORDER_UNAVAILABLE: "Errand records are unavailable, so nothing was saved. Try again.",
  IDEMPOTENCY_KEY_REUSED: "This form was already used for a different dispute. Reload the page and try again.",
  DISPUTE_NOT_FOUND: "This dispute does not exist.",
  FORBIDDEN: "Administrator access is required. Your role may have changed.",
  VALIDATION_ERROR: "Check the filters and try again.",
  DATABASE_UNAVAILABLE: "This information is unavailable right now. Try again.",
  SERVICE_NOT_READY: "This information is unavailable right now. Try again.",
};

export function adminError(failure: unknown): string {
  if (isApiRequestError(failure) && messages[failure.code]) return messages[failure.code];
  if (isApiRequestError(failure) && failure.status === 404) return "This record was not found.";
  return orderError(failure);
}

export const isVersionConflict = (failure: unknown) =>
  isApiRequestError(failure) && failure.code === "VERSION_CONFLICT";

// A missing credit reservation is a valid outcome to show, not a failure.
export function noReservation(failure: unknown): null {
  if (isApiRequestError(failure) && failure.code === "RESERVATION_NOT_FOUND") return null;
  throw failure;
}

// N2NFR4.6: unsaved dispute text survives retries and refreshes within this browser session.
export function readDraft<T>(key: string, fallback: T): T {
  try {
    const saved = sessionStorage.getItem(key);
    return saved === null ? fallback : (JSON.parse(saved) as T);
  } catch {
    return fallback;
  }
}

export function writeDraft(key: string, value: unknown) {
  try { sessionStorage.setItem(key, JSON.stringify(value)); } catch { /* storage is optional */ }
}

export function clearDraft(key: string) {
  try { sessionStorage.removeItem(key); } catch { /* storage is optional */ }
}
