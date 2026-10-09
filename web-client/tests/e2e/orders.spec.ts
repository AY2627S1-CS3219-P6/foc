import { expect, test, type Page } from "@playwright/test";

const supplierId = "550e8400-e29b-41d4-a716-446655440000";
const orderId = "550e8400-e29b-41d4-a716-446655440001";
const operationId = "550e8400-e29b-41d4-a716-446655440002";
const order = {
  orderId, supplierId, itemDescription: "One vegetarian sandwich", deliveryLocation: "COM3 level 1 collection point", reward: 10,
  acceptanceDeadline: "2035-01-01T04:00:00Z", deliveryDeadline: "2035-01-01T05:00:00Z", state: "OPEN", createdAt: "2026-10-09T12:00:00Z",
  pickup: { name: "Cool Spot", buildingArea: "COM2", pickupLocationDescription: "Collect at the counter", floor: "1", latitude: null, longitude: null, updatedAt: "2026-10-09T12:00:00Z" },
};
const participant = { ...order, requesterId: "user-id", courierId: null, updatedAt: order.createdAt };
const list = (items: unknown[], page = 1, pageSize = 12, total = items.length) => ({ items, page, pageSize, total });
const pending = { operationId, stage: "RESERVATION_UNKNOWN", orderId: null, statusUrl: `/v1/order-creations/${operationId}`, retryCreation: false, errorCode: "CREDIT_UNAVAILABLE" };

async function mockSession(page: Page) {
  await page.route("**/v1/auth/sessions/refresh", (route) => route.fulfill({ json: { accessToken: "test-token", tokenType: "Bearer", expiresAt: "2035-01-01T00:00:00Z" } }));
  await page.route("**/v1/users/me", (route) => route.fulfill({ json: { userId: "user-id", username: "student", email: "student@u.nus.edu", displayName: "Jihun Hwang", systemRole: "USER", accountStatus: "ACTIVE" } }));
  await page.route(`**/api/v1/suppliers/${supplierId}`, (route) => route.fulfill({ json: { id: supplierId, name: "Cool Spot", building_area: "COM2", status: "ACTIVE" } }));
  await page.route((url) => url.pathname === "/api/v1/suppliers", (route) => route.fulfill({ json: { items: [{ id: supplierId, name: "Cool Spot", building_area: "COM2", floor: "1", categories: ["FOOD"], status: "ACTIVE", opening_time: null, closing_time: null }], page: 1, page_size: 20, total: 1 } }));
  await page.route((url) => url.pathname === "/v1/orders", (route) => route.fulfill({ json: list([order]) }));
  await page.route((url) => url.pathname === "/v1/orders/mine", (route) => route.fulfill({ json: list([participant]) }));
  await page.route((url) => url.pathname === `/v1/orders/${orderId}`, (route) => route.fulfill({ json: participant }));
  await page.route((url) => url.pathname === `/v1/orders/${orderId}/history`, (route) => route.fulfill({ json: list([{ sequence: 1, previousState: null, newState: "OPEN", actorId: "user-id", actorType: "USER", occurredAt: order.createdAt }], 1, 20) }));
}

async function fillForm(page: Page) {
  await page.getByRole("combobox", { name: "Pickup supplier", exact: true }).click();
  await page.getByRole("option", { name: "Cool Spot COM2", exact: true }).click();
  await page.getByLabel("Delivery location", { exact: true }).fill(order.deliveryLocation);
  await page.getByLabel("Latest acceptance time (SGT)").fill("2035-01-01T12:00");
  await page.getByLabel("Latest delivery time (SGT)").fill("2035-01-01T13:00");
  await page.getByLabel("Instructions", { exact: true }).fill(order.itemDescription);
  await page.getByLabel("Credit reward", { exact: true }).fill("10");
}

for (const width of [375, 768, 1024, 1440]) {
  test(`Order create/browse/detail match shared responsive shell at ${width}px`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width, height: 900 });
    await mockSession(page);
    await page.goto("/orders");
    await expect(page.getByRole("heading", { name: "Open errands" })).toBeVisible();
    await expect(page.locator(".workspace-topbar")).toBeVisible();
    await expect(page.getByRole("button", { name: "Accept", exact: true })).toHaveCount(0);
    await page.screenshot({ path: testInfo.outputPath(`order-browse-${width}.png`), fullPage: true });
    await page.getByRole("link", { name: /View errand/ }).click();
    await expect(page.getByRole("heading", { name: "Lifecycle history" })).toBeVisible();
    await expect(page.getByText("Participant action")).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await page.screenshot({ path: testInfo.outputPath(`order-detail-${width}.png`), fullPage: true });
    await page.goto("/orders/new");
    await fillForm(page);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await page.screenshot({ path: testInfo.outputPath(`order-create-${width}.png`), fullPage: true });
    await page.getByRole("combobox", { name: "Pickup supplier" }).click();
    await expect(page.getByRole("option", { name: "Cool Spot COM2" })).toBeVisible();
    await page.screenshot({ path: testInfo.outputPath(`order-picker-${width}.png`), fullPage: true });
  });
}

test("creation distinguishes Credit unavailable from success and replays the saved request", async ({ page }) => {
  await mockSession(page);
  const calls: { body: string | null; key: string | undefined }[] = [];
  await page.route((url) => url.pathname === "/v1/orders", (route) => {
    calls.push({ body: route.request().postData(), key: route.request().headers()["idempotency-key"] });
    return calls.length === 1 ? route.fulfill({ status: 503, json: { error: { code: "CREDIT_UNAVAILABLE", message: "Credit is not configured.", fieldErrors: [] } } }) : route.fulfill({ status: 201, json: participant });
  });
  await page.goto("/orders/new"); await fillForm(page);
  await page.getByRole("button", { name: "Post errand", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("Credit is not configured.");
  await expect(page.getByRole("heading", { name: "Your errand is open" })).toHaveCount(0);
  await expect(page.getByLabel("Instructions", { exact: true })).toBeDisabled();
  await page.reload();
  await page.getByRole("button", { name: "Retry same request" }).click();
  await expect(page.getByRole("heading", { name: "Your errand is open" })).toBeVisible();
  expect(calls).toHaveLength(2);
  expect(calls[0]).toEqual(calls[1]);
  expect(calls[0].key).toBeTruthy();
  expect(JSON.parse(calls[0].body!).acceptanceDeadline).toBe("2035-01-01T04:00:00.000Z");
});

test("202 is pending, requires fresh authenticated retry, and closed attempts allow a new request", async ({ page }) => {
  await mockSession(page);
  let count = 0;
  await page.route((url) => url.pathname === "/v1/orders", (route) => route.fulfill({ status: 202, json: ++count === 1 ? pending : { ...pending, stage: "ABORTED", retryCreation: false } }));
  await page.route(`**/v1/order-creations/${operationId}`, (route) => route.fulfill({ json: { ...pending, stage: "READY_TO_FINALIZE", retryCreation: true } }));
  await page.goto("/orders/new"); await fillForm(page);
  await page.getByRole("button", { name: "Post errand", exact: true }).click();
  await expect(page.getByRole("region", { name: "Creation progress" })).toContainText("confirmation pending");
  await expect(page.getByRole("button", { name: "Retry same request" })).toBeDisabled();
  await page.getByRole("button", { name: "Check status" }).click();
  await page.getByRole("button", { name: "Finish creating errand" }).click();
  await expect(page.getByRole("heading", { name: "This attempt is closed" })).toBeVisible();
  await page.getByRole("button", { name: "Start a new request" }).click();
  await expect(page.getByLabel("Instructions", { exact: true })).toBeEnabled();
});

test("assessment detail does not request private history", async ({ page }) => {
  await mockSession(page);
  let historyCalls = 0;
  await page.route(`**/v1/orders/${orderId}`, (route) => route.fulfill({ json: order }));
  await page.route(`**/v1/orders/${orderId}/history*`, (route) => { historyCalls++; return route.fulfill({ status: 404, json: {} }); });
  await page.goto(`/orders/${orderId}`);
  await expect(page.getByText("Participant information and lifecycle history are private.", { exact: false })).toBeVisible();
  expect(historyCalls).toBe(0);
  await expect(page.getByRole("heading", { name: "Lifecycle history" })).toHaveCount(0);
});

test("own-order relationship and pagination are sent to the service", async ({ page }) => {
  await mockSession(page);
  const queries: string[] = [];
  await page.route((url) => url.pathname === "/v1/orders/mine", (route) => {
    const params = new URL(route.request().url()).searchParams;
    queries.push(params.toString());
    return route.fulfill({ json: list([participant], Number(params.get("page")), 12, 13) });
  });
  await page.goto("/orders/mine");
  await page.getByRole("button", { name: "As courier" }).click();
  await expect(page.getByRole("button", { name: "As courier" })).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByRole("heading", { name: order.itemDescription })).toBeVisible();
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await expect(page.getByText("Page 2 of 2")).toBeVisible();
  expect(queries.at(-1)).toContain("relationship=courier");
  expect(queries.at(-1)).toContain("page=2");
});

test("input errors are announced and never send a creation", async ({ page }) => {
  await mockSession(page);
  let posted = false;
  await page.route((url) => url.pathname === "/v1/orders", (route) => { posted = true; return route.fulfill({ json: participant }); });
  await page.goto("/orders/new");
  await page.getByRole("button", { name: "Post errand", exact: true }).click();
  await expect(page.getByText("Check the highlighted fields before posting.")).toBeVisible();
  await expect(page.getByLabel("Credit reward", { exact: true })).toHaveAttribute("aria-invalid", "true");
  expect(posted).toBe(false);
});

test("empty lists and dependency failures offer honest recovery", async ({ page }) => {
  await mockSession(page);
  let unavailable = true;
  await page.route((url) => url.pathname === "/v1/orders", (route) => unavailable
    ? route.fulfill({ status: 503, json: { error: { code: "AUTH_UNAVAILABLE", message: "Identity validation is unavailable." } } })
    : route.fulfill({ json: list([]) }));
  await page.goto("/orders");
  await expect(page.getByRole("alert")).toContainText("Identity validation is unavailable.");
  unavailable = false;
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(page.getByRole("heading", { name: "No open errands found" })).toBeVisible();
});

test("anonymous visitors cannot access Order pages", async ({ page }) => {
  await page.route("**/v1/auth/sessions/refresh", (route) => route.fulfill({ status: 401, json: {} }));
  for (const path of ["/orders", "/orders/new", "/orders/mine", `/orders/${orderId}`]) {
    await page.goto(path);
    await expect(page).toHaveURL(/\/sign-in$/);
  }
});

test("supplier filter and stale pagination use the supported Order contract", async ({ page }) => {
  await mockSession(page);
  const queries: string[] = [];
  await page.route((url) => url.pathname === "/v1/orders", (route) => {
    const params = new URL(route.request().url()).searchParams;
    queries.push(params.toString());
    return route.fulfill({ json: list(Number(params.get("page")) === 1 ? [order] : [], Number(params.get("page")), 12, 1) });
  });
  await page.goto("/orders?page=9");
  await expect(page.getByRole("heading", { name: order.itemDescription })).toBeVisible();
  await expect(page.getByText("Page 1 of 1")).toBeVisible();
  await page.locator(".order-filter summary").click();
  await page.getByRole("combobox", { name: "Filter by supplier", exact: true }).click();
  await page.getByRole("option", { name: "Cool Spot COM2", exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`supplierId=${supplierId}`));
  await expect(page.getByRole("heading", { name: order.itemDescription })).toBeVisible();
  await expect.poll(() => queries.at(-1)).toContain(`supplierId=${supplierId}`);
  await page.getByRole("combobox", { name: "Filter by supplier" }).click();
  await page.getByRole("option", { name: "All suppliers", exact: true }).click();
  await expect(page).not.toHaveURL(/supplierId=/);
});

test("supplier dropdown searches in one field and supports keyboard selection", async ({ page }) => {
  await mockSession(page);
  const queries: string[] = [];
  await page.route((url) => url.pathname === "/api/v1/suppliers", (route) => {
    const query = new URL(route.request().url()).searchParams.get("q") ?? "";
    queries.push(query);
    const items = query === "missing" ? [] : [{ id: supplierId, name: "Cool Spot", building_area: "COM2" }];
    return route.fulfill({ json: { items, total: items.length, page: 1, page_size: 20 } });
  });
  await page.goto("/orders/new");
  const input = page.getByRole("combobox", { name: "Pickup supplier" });
  await input.fill("missing");
  await expect(page.getByText("No active suppliers match this search.")).toBeVisible();
  await input.fill("Cool");
  await expect(page.getByRole("option", { name: "Cool Spot COM2" })).toBeVisible();
  await input.press("ArrowDown");
  await input.press("Enter");
  await expect(input).toHaveValue("Cool Spot · COM2");
  await expect(input).toHaveAttribute("aria-expanded", "false");
  await input.press("ArrowDown");
  await input.press("Escape");
  await expect(input).toHaveValue("Cool Spot · COM2");
  await input.fill("missing");
  await page.getByLabel("Delivery location", { exact: true }).click();
  await expect(input).toHaveValue("");
  await page.getByRole("button", { name: "Post errand", exact: true }).click();
  await expect(page.getByText("Select an active supplier.", { exact: true })).toBeVisible();
  expect(queries).toContain("Cool");
  await expect(page.getByText("Find a supplier", { exact: true })).toHaveCount(0);
  await expect(page.getByRole("button", { name: /Previous suppliers|Next suppliers/ })).toHaveCount(0);
});

test("supplier dropdown loads later pages on scroll without replacing earlier choices", async ({ page }) => {
  await mockSession(page);
  const suppliers = Array.from({ length: 21 }, (_, index) => ({ id: `supplier-${index}`, name: `Supplier ${index + 1}`, building_area: "COM2" }));
  await page.route((url) => url.pathname === "/api/v1/suppliers", (route) => {
    const current = Number(new URL(route.request().url()).searchParams.get("page"));
    return route.fulfill({ json: { items: suppliers.slice((current - 1) * 20, current * 20), total: 21, page: current, page_size: 20 } });
  });
  await page.goto("/orders/new");
  const input = page.getByRole("combobox", { name: "Pickup supplier" });
  await input.click();
  await expect(page.getByRole("option")).toHaveCount(20);
  await page.getByRole("listbox").evaluate((list) => { list.scrollTop = list.scrollHeight; });
  await expect(page.getByRole("option")).toHaveCount(21);
  await page.getByRole("option", { name: "Supplier 21 COM2", exact: true }).click();
  await expect(input).toHaveValue("Supplier 21 · COM2");
});

test("supplier search ignores stale responses and offers retry after an outage", async ({ page }) => {
  await mockSession(page);
  let unavailable = true;
  await page.route((url) => url.pathname === "/api/v1/suppliers", async (route) => {
    if (unavailable) return route.fulfill({ status: 503, json: { error: { message: "Supplier temporarily unavailable." } } });
    const query = new URL(route.request().url()).searchParams.get("q");
    if (query === "slow") await new Promise((resolve) => setTimeout(resolve, 800));
    return route.fulfill({ json: { items: query === "missing" ? [] : [{ id: supplierId, name: "Cool Spot", building_area: "COM2" }], total: query === "missing" ? 0 : 1, page: 1, page_size: 20 } });
  });
  await page.goto("/orders/new");
  const input = page.getByRole("combobox", { name: "Pickup supplier" });
  await input.click();
  await expect(page.getByRole("alert")).toContainText("Supplier temporarily unavailable.");
  unavailable = false;
  await page.getByRole("button", { name: "Retry suppliers" }).click();
  await expect(page.getByRole("option", { name: "Cool Spot COM2" })).toBeVisible();
  const slowRequest = page.waitForRequest((request) => new URL(request.url()).searchParams.get("q") === "slow");
  await input.fill("slow");
  await slowRequest;
  const slowResponse = page.waitForResponse((response) => new URL(response.url()).searchParams.get("q") === "slow");
  await input.fill("missing");
  await expect(page.getByText("No active suppliers match this search.")).toBeVisible();
  await slowResponse;
  await expect(page.getByRole("option")).toHaveCount(0);
});

test("concurrent clicks send one creation and a lost response retains the same retry key", async ({ page }) => {
  await mockSession(page);
  const keys: string[] = [];
  await page.route((url) => url.pathname === "/v1/orders", async (route) => {
    keys.push(route.request().headers()["idempotency-key"]);
    if (keys.length === 1) { await new Promise((resolve) => setTimeout(resolve, 150)); await route.abort("failed"); }
    else await route.fulfill({ status: 200, json: participant });
  });
  await page.goto("/orders/new"); await fillForm(page);
  await page.getByRole("button", { name: "Post errand", exact: true }).evaluate((button: HTMLButtonElement) => { button.click(); button.click(); });
  await expect(page.getByRole("alert")).toContainText("Check your connection");
  expect(keys).toHaveLength(1);
  await page.getByRole("button", { name: "Retry same request" }).click();
  await expect(page.getByRole("heading", { name: "Your errand is open" })).toBeVisible();
  expect(keys[0]).toBe(keys[1]);
});
