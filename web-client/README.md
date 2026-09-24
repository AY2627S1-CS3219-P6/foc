# FoC Web Client

The React, Vite, and TypeScript client uses same-origin `/v1/` requests for
User Service and `/api/v1/` for Supplier Service. Both APIs own authentication
and authorization decisions. The client does not connect to either database.

## Local development

Use Node.js 22 or newer.

```sh
npm ci
npm run dev
```

Vite listens on port 5173. It proxies `/v1/` to User Service on port 8000 and
Supplier API requests to Supplier Service on port 8001. Start both services
and their local databases using the [root setup guide](../README.md) for the
complete UI. Sign in before opening Supplier pages.

| Route | Audience | Purpose |
| --- | --- | --- |
| `/suppliers` and `/suppliers/:id` | Any signed-in user | Browse active suppliers, search, filter, sort, paginate, and view details. |
| `/admin/suppliers` and `/admin/suppliers/:id` | Admin or Super Admin | Browse active and inactive suppliers and view full details. |
| `/admin/suppliers/new` and `/admin/suppliers/:id/edit` | Admin or Super Admin | Create and edit supplier records. |

Management pages include activation, deactivation, and Remove. The current
Supplier Service `DELETE` returns `DEACTIVATED` and retains the row, so the UI
explains this in its confirmation dialog. The API checks current permissions
again for every management request.

See [Supplier UI traceability](SUPPLIER_UI.md) for backlog and Milestone D2
coverage and remaining service-level requirements.

## Checks

```sh
npm run build
npm test
npm run test:e2e
```

The browser suite covers the supported 375×812, 768×1024, 1024×768, and 1440×1024 layouts.

## Container

From `foc/user-service/`, start the integrated stack with:

```sh
docker compose up --build
```

The web client is served at `http://localhost:3000`. Nginx preserves both API
path prefixes and falls back to the SPA for client routes. For the integrated
User and Supplier stack, use the root [`compose.yaml`](../compose.yaml) as
described in the repository README.
