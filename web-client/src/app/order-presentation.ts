import { isApiRequestError } from "../api/client";

export function orderError(failure: unknown): string {
  return isApiRequestError(failure) ? `${failure.message}${failure.correlationId ? ` Reference: ${failure.correlationId}` : ""}` : "We could not complete this request. Try again.";
}

export function orderTime(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Time unavailable" : new Intl.DateTimeFormat("en-SG", {
    timeZone: "Asia/Singapore", day: "numeric", month: "short", year: "numeric", hour: "numeric", minute: "2-digit",
  }).format(date);
}
