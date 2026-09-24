import { afterEach, describe, expect, it, vi } from "vitest";
import { supplierService } from "../../src/api/supplier-service";

describe("Supplier Service client", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("sends bearer auth and repeated category filters to the same-origin API", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ items: [], page: 2, page_size: 6, total: 0 }), {
      headers: { "content-type": "application/json" },
    }));
    vi.stubGlobal("fetch", fetchMock);

    await supplierService.list({ q: " cafe ", categories: ["FOOD", "COFFEE"], page: 2, pageSize: 6 }, "test-token");

    const [url, options] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/api/v1/suppliers?");
    expect(new URL(url, "http://localhost").searchParams.getAll("category")).toEqual(["FOOD", "COFFEE"]);
    expect(new URL(url, "http://localhost").searchParams.get("q")).toBe("cafe");
    expect((options.headers as Headers).get("Authorization")).toBe("Bearer test-token");
  });

  it("maps Supplier validation fields into the shared API error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({
      error: { code: "VALIDATION_ERROR", message: "Supplier data is invalid", fields: [{ field: "name", message: "Must not be blank" }] },
    }), { status: 422, headers: { "content-type": "application/json" } })));

    await expect(supplierService.create({ name: "", categories: [], building_area: "", pickup_location_description: "" }, "test-token"))
      .rejects.toMatchObject({ status: 422, fieldErrors: [{ field: "name", message: "Must not be blank" }] });
  });
});
