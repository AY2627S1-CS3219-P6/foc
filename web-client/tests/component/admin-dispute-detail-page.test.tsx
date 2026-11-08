// AI Assistance Disclosure:
// Tool: Claude Code (model: Claude Opus 5.5), date: 2026-10-28, 2026-10-29, 2026-11-08
// Scope: Added dispute detail component tests, including errand outcome decisions.
// Author review: I validated correctness and supplied additional boundary checks.

import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AdminDisputeDetailPage } from "../../src/pages/admin-dispute-detail-page";

const auth = vi.hoisted(() => ({
  user: { userId: "admin", username: "ada", email: "ada@u.nus.edu", displayName: "Ada", systemRole: "ADMIN", accountStatus: "ACTIVE" },
  withCurrentAccess: vi.fn(),
}));

vi.mock("../../src/app/use-auth", () => ({ useAuth: () => auth }));

const DISPUTE_ID = "d1d1d1d1-0000-4000-8000-000000000001";
const ORDER_ID = "e2e2e2e2-0000-4000-8000-000000000002";
const dispute = {
  disputeId: DISPUTE_ID, orderId: ORDER_ID, description: "Courier marked it delivered; nothing arrived.",
  status: "UNDER_REVIEW", resolutionReason: null, createdBy: "admin-1", version: 2,
  createdAt: "2026-10-20T04:00:00Z", updatedAt: "2026-10-20T05:00:00Z", evidenceRefs: ["chat:42"],
  history: [
    { sequence: 1, fromStatus: null, toStatus: "OPEN", actorId: "admin-1", reason: null, occurredAt: "2026-10-20T04:00:00Z" },
    { sequence: 2, fromStatus: "OPEN", toStatus: "UNDER_REVIEW", actorId: "admin-1", reason: null, occurredAt: "2026-10-20T05:00:00Z" },
  ],
};
const errand = {
  orderId: ORDER_ID, supplierId: "s1", itemDescription: "Iced latte", deliveryLocation: "COM1", reward: 3,
  acceptanceDeadline: "2026-10-20T05:00:00Z", deliveryDeadline: "2026-10-20T06:00:00Z",
  pickup: { name: "Campus Cafe", buildingArea: "COM1", pickupLocationDescription: "Counter", floor: null, latitude: null, longitude: null, updatedAt: "2026-10-01T00:00:00Z" },
  state: "COMPLETED", createdAt: "2026-10-20T03:00:00Z", updatedAt: "2026-10-20T04:00:00Z", requesterId: "r1", courierId: "c1",
};
const settlement = { orderId: ORDER_ID, state: "TRANSFERRED", amount: 3, updatedAt: "2026-10-20T04:00:00Z" };

const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });

function routeFetch(transition: () => Response, current: object = dispute, related: { errand?: object; settlement?: object } = {}) {
  const fetchMock = vi.fn<(input: RequestInfo | URL, init?: RequestInit) => Promise<Response>>(async (input) => {
    const url = String(input);
    if (url.endsWith("/transitions")) return transition();
    if (url.includes("/admin/disputes/")) return json(current);
    if (url.includes("/admin/orders/")) return json(related.errand ?? errand);
    if (url.includes("/admin/credit/reservations/")) return json(related.settlement ?? settlement);
    return json({ error: { code: "NOT_FOUND", message: "Not found", correlationId: "c", fieldErrors: [] } }, 404);
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

async function renderDispute() {
  await act(async () => {
    render(<MemoryRouter initialEntries={[`/admin/disputes/${DISPUTE_ID}`]}><Routes>
      <Route element={<AdminDisputeDetailPage />} path="/admin/disputes/:disputeId" />
    </Routes></MemoryRouter>);
  });
  await screen.findByRole("heading", { name: "Update status" });
}

const posts = (fetchMock: ReturnType<typeof routeFetch>) =>
  fetchMock.mock.calls.filter(([, init]) => init?.method === "POST");

describe("Admin dispute detail", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    sessionStorage.clear();
    vi.stubGlobal("matchMedia", vi.fn(() => ({ matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn() })));
    auth.withCurrentAccess.mockImplementation((operation: (token: string) => Promise<unknown>) => operation("current-token"));
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("shows the errand state and credit settlement as separate panels", async () => {
    routeFetch(() => json(dispute));
    await renderDispute();
    const errandPanel = await screen.findByRole("region", { name: "Errand state" });
    expect(await within(errandPanel).findByText("COMPLETED")).toBeVisible();
    const creditPanel = screen.getByRole("region", { name: "Credit settlement" });
    expect(await within(creditPanel).findByText("Transferred to the courier")).toBeVisible();
    expect(screen.getByText("chat:42")).toBeVisible();
  });

  it("shows who raised the dispute", async () => {
    routeFetch(() => json(dispute));
    await renderDispute();
    expect(screen.getByText("Recorded by")).toBeVisible();
    cleanup();
    routeFetch(() => json(dispute), { ...dispute, reporterRole: "COURIER", createdBy: "c1c1c1c1-0000", evidenceRefs: [] });
    await renderDispute();
    expect(screen.getByText("Reported by")).toBeVisible();
    expect(screen.getByText("Courier C1C1C1C1")).toBeVisible();
    expect(screen.queryByText("Evidence")).toBeNull();
    expect(screen.getByText(/requester and courier will both see the reason/)).toBeVisible();
  });

    it("requires a reason before resolving and sends nothing without one", async () => {
    const fetchMock = routeFetch(() => json(dispute));
    await renderDispute();
    fireEvent.click(screen.getByRole("radio", { name: "Resolved" }));
    await act(async () => { fireEvent.click(screen.getByRole("button", { name: "Mark as resolved" })); });
    expect(screen.getByRole("alert")).toHaveTextContent("Give a reason to resolve or reject this dispute.");
    expect(posts(fetchMock)).toHaveLength(0);
  });

  it("asks the administrator to refresh after a concurrent change and keeps the reason", async () => {
    const fetchMock = routeFetch(() => json({ error: { code: "VERSION_CONFLICT", message: "conflict", correlationId: "c", fieldErrors: [] } }, 409));
    await renderDispute();
    fireEvent.click(screen.getByRole("radio", { name: "Rejected" }));
    fireEvent.change(screen.getByLabelText("Reason (required)"), { target: { value: "Duplicate report." } });
    await act(async () => { fireEvent.click(screen.getByRole("button", { name: "Mark as rejected" })); });
    expect(await screen.findByRole("button", { name: "Refresh dispute" })).toBeVisible();
    expect(screen.getByRole("alert")).toHaveTextContent("changed by someone else");
    const [, init] = posts(fetchMock)[0];
    expect(JSON.parse(String(init?.body))).toEqual({ toStatus: "REJECTED", reason: "Duplicate report.", expectedVersion: 2 });
    expect(sessionStorage.getItem(`admin-dispute-reason:${DISPUTE_ID}`)).toBe(JSON.stringify("Duplicate report."));
  });

  describe("deciding the errand outcome", () => {
    const delivered = { ...errand, state: "DELIVERED" };
    const reserved = { ...settlement, state: "RESERVED" };

    async function chooseFailure() {
      fireEvent.click(screen.getByRole("radio", { name: /Mark the errand as failed/ }));
      fireEvent.change(screen.getByLabelText(/Reason \(required/), { target: { value: "Nothing arrived." } });
      await act(async () => { fireEvent.click(screen.getByRole("button", { name: "Review decision" })); });
    }

    it("offers only the outcomes the errand allows, with their credit effect", async () => {
      routeFetch(() => json(dispute), dispute, { errand: delivered, settlement: reserved });
      await renderDispute();
      expect(await screen.findByRole("radio", { name: /Mark the errand as failed\s*3 credits return to the requester/ })).toBeVisible();
      expect(screen.getByRole("radio", { name: /Mark the errand as completed\s*3 credits are paid to the courier/ })).toBeVisible();
      expect(screen.getByRole("radio", { name: /Leave the errand as it is/ })).toBeChecked();
    });

    it("hides outcomes for an errand that can no longer change", async () => {
      routeFetch(() => json(dispute));
      await renderDispute();
      expect(await screen.findByText(/This errand is completed, so its outcome can no longer be changed here/)).toBeVisible();
      expect(screen.queryByRole("radio", { name: /Mark the errand as failed/ })).toBeNull();
    });

    it("confirms before applying and sends the outcome with the decision", async () => {
      const fetchMock = routeFetch(() => json({ ...dispute, status: "RESOLVED", version: 3, errandOutcome: "FAILED" }), dispute, { errand: delivered, settlement: reserved });
      await renderDispute();
      await screen.findByRole("radio", { name: /Mark the errand as failed/ });
      await chooseFailure();
      const confirm = screen.getByRole("group", { name: "Confirm your decision" });
      expect(within(confirm).getByText(/3 credits return to the requester\. This cannot be undone\./)).toBeVisible();
      expect(posts(fetchMock)).toHaveLength(0);
      await act(async () => { fireEvent.click(within(confirm).getByRole("button", { name: "Confirm and apply" })); });
      const [, init] = posts(fetchMock)[0];
      expect(JSON.parse(String(init?.body))).toEqual({ toStatus: "RESOLVED", reason: "Nothing arrived.", expectedVersion: 2, errandOutcome: "FAILED" });
    });

    it("goes back without sending anything", async () => {
      const fetchMock = routeFetch(() => json(dispute), dispute, { errand: delivered, settlement: reserved });
      await renderDispute();
      await screen.findByRole("radio", { name: /Mark the errand as failed/ });
      await chooseFailure();
      fireEvent.click(screen.getByRole("button", { name: "Back" }));
      expect(screen.getByRole("radio", { name: /Mark the errand as failed/ })).toBeChecked();
      expect(posts(fetchMock)).toHaveLength(0);
    });

    it("asks for a refresh when the errand changed first", async () => {
      routeFetch(
        () => json({ error: { code: "ERRAND_CHANGED", message: "changed", correlationId: "c", fieldErrors: [] } }, 409),
        dispute,
        { errand: delivered, settlement: reserved },
      );
      await renderDispute();
      await screen.findByRole("radio", { name: /Mark the errand as failed/ });
      await chooseFailure();
      await act(async () => { fireEvent.click(screen.getByRole("button", { name: "Confirm and apply" })); });
      expect(screen.getByRole("alert")).toHaveTextContent("The errand changed, so this outcome is no longer possible.");
      expect(screen.getByRole("button", { name: "Refresh dispute" })).toBeVisible();
    });
  });
});
