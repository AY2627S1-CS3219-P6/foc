import { expect, test, type Page } from "@playwright/test";

const supplierId = "550e8400-e29b-41d4-a716-446655440000";

async function mockSupplierSession(page: Page, role: "USER" | "ADMIN" = "USER") {
  await page.route("**/v1/auth/sessions/refresh", (route) => route.fulfill({ json: {
    accessToken: "valid-test-token", tokenType: "Bearer", expiresAt: "2030-01-01T00:00:00Z",
  } }));
  await page.route("**/v1/users/me", (route) => route.fulfill({ json: {
    userId: "user-id", username: "testuser", email: "testuser@u.nus.edu", displayName: "Jihun Hwang", systemRole: role, accountStatus: "ACTIVE",
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

for (const viewport of [{ width: 375, height: 812 }, { width: 768, height: 1024 }, { width: 1024, height: 768 }, { width: 1440, height: 1024 }]) {
  test(`supplier browsing and detail remain usable at ${viewport.width}px`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await mockSupplierSession(page);
    await page.goto("/suppliers");
    await expect(page.getByRole("heading", { name: "Campus suppliers" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Cool Spot" })).toBeVisible();
    await page.getByRole("link", { name: "View Cool Spot" }).click();
    await expect(page.getByText("Opp Lift").first()).toBeVisible();
    await expect(page.getByText("09:00–21:30")).toBeVisible();
    await expect(page.getByText("Food / Coffee").first()).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    if (viewport.width === 375) await expect(page.getByRole("navigation", { name: "Mobile navigation" })).toBeVisible();
  });
}

test("search and filters apply automatically without losing one another", async ({ page }) => {
  await mockSupplierSession(page);
  await page.goto("/suppliers");
  await expect(page.getByRole("heading", { name: "Cool Spot" })).toBeVisible();
  await page.getByRole("searchbox", { name: "Search suppliers" }).fill("cool");
  await page.locator(".supplier-category-picker summary").click();
  await page.getByRole("checkbox", { name: "Food" }).click();
  await expect(page).toHaveURL(/category=FOOD/);
  await page.getByRole("combobox", { name: "Sort suppliers" }).selectOption("desc");
  await expect(page).toHaveURL(/q=cool/);
  const query = new URL(page.url()).searchParams;
  expect(query.get("q")).toBe("cool");
  expect(query.has("building_area")).toBe(false);
  expect(query.getAll("category")).toEqual(["FOOD"]);
  expect(query.get("sort")).toBe("desc");
  await page.getByRole("button", { name: "Clear filters" }).click();
  await expect(page.getByRole("searchbox", { name: "Search suppliers" })).toHaveValue("");
  expect(new URL(page.url()).search).toBe("");
});

test("pagination appears only when results span more than one page", async ({ page }) => {
  await mockSupplierSession(page);
  await page.goto("/suppliers");
  await expect(page.getByRole("heading", { name: "Cool Spot" })).toBeVisible();
  await expect(page.getByRole("combobox", { name: "Suppliers per page" })).toHaveCount(0);
  await page.route((url) => url.pathname === "/api/v1/suppliers", (route) => route.fulfill({ json: {
    items: [{ id: supplierId, name: "Cool Spot", categories: ["FOOD"], building_area: "Com2", floor: null, status: "ACTIVE", opening_time: null, closing_time: null }],
    page: Number(new URL(route.request().url()).searchParams.get("page") ?? 1), page_size: 6, total: 7,
  } }));
  await page.reload();
  await expect(page.getByRole("combobox", { name: "Suppliers per page" })).toBeVisible();
  await page.getByRole("button", { name: "Next" }).click();
  await expect(page).toHaveURL(/page=2/);
});

test("normal users cannot open Supplier management pages", async ({ page }) => {
  await mockSupplierSession(page);
  await page.goto("/admin/suppliers");
  await expect(page.getByRole("heading", { name: "Supplier management requires an administrator" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Manage suppliers" })).toHaveCount(0);
});

test("admin listing includes inactive suppliers and applies the status filter", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1024 });
  await mockSupplierSession(page, "ADMIN");
  await page.route((url) => url.pathname === "/api/v1/admin/suppliers", (route) => {
    const status = new URL(route.request().url()).searchParams.get("status");
    const items = [
      { id: supplierId, name: "Cool Spot", categories: ["FOOD"], building_area: "Com2", floor: null, status: "ACTIVE", opening_time: "09:00", closing_time: "21:30" },
      { id: "550e8400-e29b-41d4-a716-446655440001", name: "Former Cafe", categories: ["COFFEE"], building_area: "Central Library", floor: null, status: "INACTIVE", opening_time: null, closing_time: null },
    ].filter((item) => !status || item.status === status);
    return route.fulfill({ json: { items, page: 1, page_size: 6, total: items.length } });
  });
  await page.goto("/admin/suppliers");
  await expect(page.getByRole("heading", { name: "Former Cafe" })).toBeVisible();
  await page.getByRole("combobox", { name: "Supplier status" }).selectOption("INACTIVE");
  await expect(page.getByRole("heading", { name: "Cool Spot" })).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "Former Cafe" })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});

test("supplier form validates required fields and 24-hour times before posting", async ({ page }) => {
  await mockSupplierSession(page, "ADMIN");
  let postCount = 0;
  await page.route((url) => url.pathname === "/api/v1/admin/suppliers", (route) => {
    if (route.request().method() === "POST") postCount += 1;
    return route.fulfill({ json: { items: [], page: 1, page_size: 6, total: 0 } });
  });
  await page.goto("/admin/suppliers/new");
  await page.getByRole("button", { name: "Create supplier" }).click();
  await expect(page.getByText("Enter a supplier name.")).toBeVisible();
  await expect(page.getByText("Select at least one category.")).toBeVisible();
  await page.getByRole("textbox", { name: "Opening time (optional)" }).fill("9:00");
  await page.getByRole("textbox", { name: "Closing time (optional)" }).fill("18:00");
  await page.getByRole("button", { name: "Create supplier" }).click();
  await expect(page.getByText("Use 24-hour HH:mm, such as 09:00.")).toBeVisible();
  expect(postCount).toBe(0);
});

test("edit form waits for supplier data and offers retry after a load failure", async ({ page }) => {
  await mockSupplierSession(page, "ADMIN");
  let unavailable = true;
  await page.route((url) => url.pathname === `/api/v1/admin/suppliers/${supplierId}`, (route) => {
    return unavailable
      ? route.fulfill({ status: 503, json: { error: { code: "SERVICE_UNAVAILABLE", message: "Supplier Service is temporarily unavailable." } } })
      : route.fulfill({ json: {
          id: supplierId, name: "Cool Spot", categories: ["FOOD"], building_area: "Com2", floor: null,
          pickup_location_description: "Opp Lift", latitude: null, longitude: null, image_url: null,
          status: "ACTIVE", opening_time: "09:00", closing_time: "21:30",
          created_at: "2026-09-23T02:00:00Z", updated_at: "2026-09-23T03:00:00Z",
        } });
  });
  await page.goto(`/admin/suppliers/${supplierId}/edit`);
  await expect(page.getByRole("heading", { name: "Supplier form could not load" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Save changes" })).toHaveCount(0);
  unavailable = false;
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(page.getByRole("textbox", { name: "Supplier name *" })).toHaveValue("Cool Spot");
});

test("admin creates, edits, and deactivates a supplier through live API contracts", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await mockSupplierSession(page, "ADMIN");
  let saved = {
    id: supplierId, name: "Cool Spot", categories: ["FOOD"], building_area: "Com2", floor: null,
    pickup_location_description: "Opp Lift", latitude: null, longitude: null, image_url: null,
    status: "ACTIVE", opening_time: "09:00", closing_time: "21:30",
    created_at: "2026-09-23T02:00:00Z", updated_at: "2026-09-23T03:00:00Z",
  };
  const writes: Array<{ method: string; body?: Record<string, unknown> }> = [];
  await page.route((url) => url.pathname === "/api/v1/admin/suppliers", (route) => {
    if (route.request().method() === "POST") {
      const body = route.request().postDataJSON() as Record<string, unknown>;
      writes.push({ method: "POST", body });
      saved = { ...saved, ...body } as typeof saved;
      return route.fulfill({ status: 201, json: saved });
    }
    return route.fulfill({ json: { items: [], page: 1, page_size: 6, total: 0 } });
  });
  await page.route((url) => url.pathname === `/api/v1/admin/suppliers/${supplierId}`, (route) => {
    const method = route.request().method();
    if (method === "PATCH") {
      const body = route.request().postDataJSON() as Record<string, unknown>;
      writes.push({ method, body });
      saved = { ...saved, ...body } as typeof saved;
      return route.fulfill({ json: saved });
    }
    if (method === "DELETE") {
      writes.push({ method });
      saved.status = "INACTIVE";
      return route.fulfill({ json: { id: supplierId, outcome: "DEACTIVATED" } });
    }
    return route.fulfill({ json: saved });
  });

  await page.goto("/admin/suppliers");
  await page.getByRole("link", { name: "+ Add supplier", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Add supplier" })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.getByRole("textbox", { name: "Supplier name *" }).fill("Cool Spot");
  await page.getByRole("textbox", { name: "Building / campus area *" }).fill("Com2");
  await page.getByRole("textbox", { name: "Pickup location description *" }).fill("Opp Lift");
  await page.getByRole("checkbox", { name: "Food" }).click();
  await page.getByRole("textbox", { name: "Opening time (optional)" }).fill("09:00");
  await page.getByRole("textbox", { name: "Closing time (optional)" }).fill("21:30");
  await page.getByRole("button", { name: "Create supplier" }).click();
  await expect(page.getByRole("heading", { name: "Cool Spot" })).toBeVisible();
  expect(writes[0]).toMatchObject({ method: "POST", body: { categories: ["FOOD"], opening_time: "09:00", closing_time: "21:30" } });

  await page.getByRole("link", { name: "Edit supplier" }).click();
  await page.getByRole("textbox", { name: "Supplier name *" }).fill("Cool Spot Updated");
  await page.getByRole("button", { name: "Save changes" }).click();
  await expect(page.getByRole("heading", { name: "Cool Spot Updated" })).toBeVisible();
  expect(writes[1]).toMatchObject({ method: "PATCH", body: { name: "Cool Spot Updated" } });

  await page.getByRole("button", { name: "Deactivate", exact: true }).click();
  await expect(page.getByRole("dialog", { name: "Deactivate supplier?" })).toContainText("record will be retained");
  await page.getByRole("button", { name: "Deactivate supplier" }).click();
  await expect(page.getByRole("status").filter({ hasText: "was deactivated" })).toContainText("was deactivated");
  await expect(page.getByText("Inactive", { exact: true })).toBeVisible();
  expect(writes[2]).toMatchObject({ method: "DELETE" });
});
