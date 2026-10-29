import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { OrderState } from "../../src/api/order-service";
import { ErrandReportPanel } from "../../src/components/errand-report";

const auth = vi.hoisted(() => ({ withCurrentAccess: vi.fn() }));

vi.mock("../../src/app/use-auth", () => ({ useAuth: () => auth }));

const ORDER_ID = "e2e2e2e2-0000-4000-8000-000000000002";
const report = (status: string, resolutionReason: string | null = null) => ({
  disputeId: `d-${status}`, orderId: ORDER_ID, ownReport: true, description: "Courier marked it delivered; nothing arrived.",
  status, resolutionReason, reporterRole: "REQUESTER", createdAt: "2026-10-20T04:00:00Z", updatedAt: "2026-10-20T05:00:00Z",
});
// The other participant's report arrives without its description.
const counterpart = (status: string, resolutionReason: string | null = null) => ({
  ...report(status, resolutionReason), disputeId: `c-${status}`, ownReport: false, description: null, reporterRole: "COURIER",
});
const page = (items: unknown[]) => ({ items, page: 1, pageSize: 50, total: items.length });
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });
const failure = (code: string, status: number) => json({ error: { code, message: code, correlationId: "c", fieldErrors: [] } }, status);

function routeFetch(existing: unknown[], post: () => Response | Promise<Response> = () => json(report("OPEN"), 201)) {
  const fetchMock = vi.fn<(input: RequestInfo | URL, init?: RequestInit) => Promise<Response>>(async (_input, init) =>
    init?.method === "POST" ? post() : json(page(existing)));
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

const posts = (fetchMock: ReturnType<typeof routeFetch>) =>
  fetchMock.mock.calls.filter(([, init]) => init?.method === "POST");

async function renderPanel(state: OrderState = "DELIVERED") {
  await act(async () => { render(<ErrandReportPanel orderId={ORDER_ID} state={state} />); });
}

async function send(description: string) {
  fireEvent.change(screen.getByLabelText("What went wrong"), { target: { value: description } });
  await act(async () => { fireEvent.click(screen.getByRole("button", { name: "Report problem" })); });
}

describe("Errand problem reports", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    sessionStorage.clear();
    auth.withCurrentAccess.mockImplementation((operation: (token: string) => Promise<unknown>) => operation("current-token"));
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("sends only the errand and a description, then waits for a decision", async () => {
    const fetchMock = routeFetch([]);
    await renderPanel();
    expect(String(fetchMock.mock.calls[0][0])).toBe(`/v1/disputes?orderId=${ORDER_ID}&pageSize=50`);
    await send("  Nothing arrived.  ");
    const [url, init] = posts(fetchMock)[0];
    expect(String(url)).toBe("/v1/disputes");
    expect(JSON.parse(String(init?.body))).toEqual({ orderId: ORDER_ID, description: "Nothing arrived." });
    expect(new Headers(init?.headers).get("Idempotency-Key")).toMatch(/^[0-9a-f-]{36}$/);
    expect(await screen.findByText("Open")).toBeVisible();
    expect(screen.getByText(/An administrator is reviewing your report/)).toBeVisible();
    expect(screen.queryByLabelText("What went wrong")).toBeNull();
    expect(sessionStorage.getItem(`errand-report-draft:${ORDER_ID}`)).toBeNull();
  });

  it("shows the decision reason and allows a new report after a decision", async () => {
    routeFetch([report("REJECTED", "Courier showed a delivery photo.")]);
    await renderPanel("COMPLETED");
    expect(screen.getByText("Rejected")).toBeVisible();
    expect(screen.getByText("Courier showed a delivery photo.")).toBeVisible();
    expect(screen.getByLabelText("What went wrong")).toBeVisible();
  });

  it("shows the other participant's report and outcome without its text, and still lets this user report", async () => {
    routeFetch([counterpart("UNDER_REVIEW"), counterpart("RESOLVED", "Requester confirmed it arrived late.")]);
    await renderPanel();
    expect(screen.getAllByText(/The courier reported a problem/)).toHaveLength(2);
    expect(screen.getByText("Requester confirmed it arrived late.")).toBeVisible();
    expect(screen.getByText(/report it from your side too/)).toBeVisible();
    expect(screen.getByLabelText("What went wrong")).toBeVisible();
  });

  it("retries an ambiguous failure with the same key and keeps the draft", async () => {
    let attempt = 0;
    const fetchMock = routeFetch([], () => (++attempt === 1 ? Promise.reject(new TypeError("network")) : json(report("OPEN"), 201)));
    await renderPanel();
    await send("Nothing arrived.");
    expect(screen.getByRole("alert")).toBeVisible();
    expect(sessionStorage.getItem(`errand-report-draft:${ORDER_ID}`)).toBe(JSON.stringify("Nothing arrived."));
    await act(async () => { fireEvent.click(screen.getByRole("button", { name: "Report problem" })); });
    const keys = posts(fetchMock).map(([, init]) => new Headers(init?.headers).get("Idempotency-Key"));
    expect(keys).toHaveLength(2);
    expect(keys[0]).toBe(keys[1]);
  });

  it("explains an existing open report and reloads the list", async () => {
    const fetchMock = routeFetch([], () => failure("REPORT_ALREADY_OPEN", 409));
    await renderPanel();
    await send("Nothing arrived.");
    expect(screen.getByRole("alert")).toHaveTextContent("You already have an open report about this errand.");
    expect(fetchMock.mock.calls.filter(([, init]) => init?.method === "GET")).toHaveLength(2);
  });

  it("offers no form once an errand can no longer be reported", async () => {
    routeFetch([]);
    await renderPanel("CANCELLED");
    expect(screen.getByText("No problems reported.")).toBeVisible();
    expect(screen.queryByRole("button", { name: "Report problem" })).toBeNull();
  });
});
