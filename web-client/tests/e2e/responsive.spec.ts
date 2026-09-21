import { expect, test } from "@playwright/test";

const viewports = [
  { name: "mobile", width: 375, height: 812 },
  { name: "tablet portrait", width: 768, height: 1024 },
  { name: "tablet landscape", width: 1024, height: 768 },
  { name: "desktop", width: 1440, height: 1024 },
];

for (const viewport of viewports) {
  test(`sign-in is usable at ${viewport.name} (${viewport.width}x${viewport.height})`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await page.goto("/sign-in");

    await expect(page.getByRole("heading", { name: "Welcome back" })).toBeVisible();
    await expect(page.getByLabel("NUS email")).toBeVisible();
    await expect(page.getByLabel("Password")).toBeVisible();
    await expect(page.getByRole("button", { name: "Sign in" })).toBeVisible();
  });
}

test("registration fields are stacked in the requested order and align on desktop", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1024 });
  await page.goto("/register");
  await expect(page.getByLabel("Display name (Optional)")).toBeVisible();

  const geometry = await page.locator("form input").evaluateAll((inputs) =>
    inputs.map((input) => {
      const box = input.getBoundingClientRect();
      return { label: input.labels?.[0]?.textContent?.trim(), x: box.x, width: box.width, y: box.y };
    }),
  );
  expect(geometry.map((input) => input.label)).toEqual([
    "Display name (Optional)",
    "Username",
    "NUS email",
    "Password",
    "Confirm password",
  ]);
  expect(new Set(geometry.map((input) => input.x)).size).toBe(1);
  expect(new Set(geometry.map((input) => input.width)).size).toBe(1);
  expect(geometry.map((input) => input.y)).toEqual([...geometry.map((input) => input.y)].sort((a, b) => a - b));
});
