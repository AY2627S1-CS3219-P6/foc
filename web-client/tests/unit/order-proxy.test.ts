// @vitest-environment node
import { afterAll, beforeAll, expect, it } from "vitest";
import { createServer, type ViteDevServer } from "vite";
import viteConfig from "../../vite.config";

const backends: ViteDevServer[] = [];
let vite: ViteDevServer | undefined;
let baseUrl: string;

beforeAll(async () => {
  const targets = new Map<string, string>();
  for (const [port, name] of [[8000, "user"], [8001, "supplier"], [8002, "order"]] as const) {
    const backend = await createServer({
      configFile: false, logLevel: "silent",
      server: { host: "127.0.0.1", port: 0, hmr: false },
      plugins: [{
        name: `mock-${name}-api`,
        configureServer(server) {
          server.middlewares.use((_request, response) => {
            response.setHeader("Content-Type", "application/json");
            response.end(JSON.stringify({ service: name }));
          });
        },
      }],
    });
    backends.push(backend);
    await backend.listen();
    targets.set(`http://localhost:${port}`, backend.resolvedUrls!.local[0]);
  }
  const proxy = Object.fromEntries(Object.entries(viteConfig.server!.proxy!).map(([prefix, options]) => {
    const target = typeof options === "string" ? options : String(options.target);
    expect(targets.has(target)).toBe(true);
    return [prefix, { ...(typeof options === "string" ? {} : options), target: targets.get(target) }];
  }));
  vite = await createServer({
    ...viteConfig, configFile: false, logLevel: "silent",
    server: { host: "127.0.0.1", port: 0, hmr: false, proxy },
  });
  await vite.listen();
  baseUrl = vite.resolvedUrls!.local[0];
});

afterAll(async () => {
  await vite?.close();
  await Promise.all(backends.map((backend) => backend.close()));
});

it.each([
  ["/v1/orders", "order"],
  ["/v1/orders?supplierId=id&pageSize=20", "order"],
  ["/v1/orders/mine?relationship=requester", "order"],
  ["/v1/orders/id/history", "order"],
  ["/v1/order-creations/id", "order"],
  ["/v1/admin/orders?requesterId=id", "order"],
  ["/v1/users/me", "user"],
  ["/v1/admin/users?email=test", "user"],
  ["/v1/orders-other", "user"],
  ["/api/v1/suppliers?page_size=6", "supplier"],
  ["/api/v1/admin/suppliers", "supplier"],
])("routes %s only to %s", async (path, service) => {
  const response = await fetch(new URL(path, baseUrl));
  expect(response.status).toBe(200);
  expect(await response.json()).toEqual({ service });
});
