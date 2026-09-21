# FoC Web Client

The Sprint 1 web client is a React, Vite, and TypeScript single-page application. It communicates only with User Service through same-origin `/v1/` requests.

## Local development

Use Node.js 22 or newer.

```sh
npm ci
npm run dev
```

Vite listens on port 5173 and proxies `/v1/` unchanged to `http://localhost:8000`. Start User Service separately from `foc/user-service/` when exercising authentication and profile flows.

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
