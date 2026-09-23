# FoC Web Client

The Sprint 1 web client is a React, Vite, and TypeScript single-page application. It communicates only with User Service through same-origin `/v1/` requests.
The proxy also routes Supplier API paths under `/api/v1/` to Supplier Service
for the upcoming Supplier UI. No Supplier screen uses those routes yet.

## Local development

Use Node.js 22 or newer.

```sh
npm ci
npm run dev
```

Vite listens on port 5173 and proxies `/v1/` unchanged to `http://localhost:8000`. Start User Service separately from `foc/user-service/` when exercising authentication and profile flows.
Vite also proxies Supplier API paths to `http://localhost:8001` when Supplier
Service is running locally.

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

The web client is served at `http://localhost:3000`. Nginx preserves `/v1/` request paths while proxying them to User Service and uses an SPA history fallback for client routes.
For the integrated User and Supplier stack, use the root
[`compose.yaml`](../compose.yaml) as described in the repository README. Nginx
also preserves Supplier API paths when proxying to Supplier Service.
