import { expect, test, type Page } from "@playwright/test";

const supplierId = "550e8400-e29b-41d4-a716-446655440000";

async function mockSupplierSession(page: Page) {
  await page.route("**/v1/auth/sessions/refresh", (route) => route.fulfill({ json: {
    accessToken: "valid-test-token", tokenType: "Bearer", expiresAt: "2030-01-01T00:00:00Z",
  } }));
  await page.route("**/v1/users/me", (route) => route.fulfill({ json: {
    userId: "user-id", username: "testuser", email: "testuser@u.nus.edu", displayName: "Jihun Hwang", systemRole: "USER", accountStatus: "ACTIVE",
  } }));
  await page.route("**/api/v1/categories", (route) => route.fulfill({ json: [
    { code: "FOOD", display_name: "Food" }, { code: "COFFEE", display_name: "Coffee" },
  ] }));
  await page.route((url) => url.pathname === "/api/v1/suppliers", (route) => route.fulfill({ json: {
    items: [{ id: supplierId, name: "Cool Spot", categories: ["FOOD", "COFFEE"], building_area: "Com2", floor: "1", status: "ACTIVE", opening_time: "09:00", closing_time: "21:30" }],
    page: 1, page_size: 6, total: 1,
  } }));
  await page.route((url) => url.pathname === `/api/v1/suppliers/${supplierId}`, (route) => route.fulfill({ json: {
    id: supplierId, name: "Cool Spot", categories: ["FOOD", "COFFEE"], building_area: "Com2", floor: "1", pickup_location_description: "Opp Lift", latitude: 1.294, longitude: 103.773, image_url: null, status: "ACTIVE", opening_time: "09:00", closing_time: "21:30", created_at: "2026-09-23T02:00:00Z", updated_at: "2026-09-23T03:00:00Z",
  } }));
}

for (const viewport of [{ width: 375, height: 812 }, { width: 1440, height: 1024 }]) {
  test(`supplier browsing and detail remain usable at ${viewport.width}px`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await mockSupplierSession(page);
    await page.goto("/suppliers");
    await expect(page.getByRole("heading", { name: "Campus suppliers" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Cool Spot" })).toBeVisible();
    await page.getByRole("link", { name: "View Cool Spot" }).click();
    await expect(page.getByText("Opp Lift").first()).toBeVisible();
    await expect(page.getByText("09:00–21:30")).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    if (viewport.width === 375) await expect(page.getByRole("navigation", { name: "Mobile navigation" })).toBeVisible();
  });
}

test("supplier filters send the supported query contract", async ({ page }) => {
  await mockSupplierSession(page);
  await page.goto("/suppliers");
  await expect(page.getByRole("heading", { name: "Cool Spot" })).toBeVisible();
  await page.getByRole("searchbox", { name: "Search suppliers" }).fill("cool");
  await page.getByPlaceholder("Campus area: All").fill("Com2");
  await page.getByRole("button", { name: "Search", exact: true }).click();
  await page.locator(".supplier-category-picker summary").click();
  await page.getByRole("checkbox", { name: "Food" }).click();
  await expect(page).toHaveURL(/category=FOOD/);
  await page.getByRole("combobox", { name: "Sort suppliers" }).selectOption("desc");
  await expect(page).toHaveURL(/category=FOOD/);
  const query = new URL(page.url()).searchParams;
  expect(query.get("q")).toBe("cool");
  expect(query.get("building_area")).toBe("Com2");
  expect(query.getAll("category")).toEqual(["FOOD"]);
  expect(query.get("sort")).toBe("desc");
});
