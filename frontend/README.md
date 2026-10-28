# EvidenceFlow frontend

The workspace connects to FastAPI. It never substitutes sample records when the backend is unavailable.

## Start locally

Start the migrated backend on port 8000 (see `../docs/LIVE_FRONTEND_INTEGRATION.md`). Then:

```sh
npm ci
npm run dev
```

Open the URL printed by Vite, enter the workspace, and create a review or select an existing one. Define the question/PICO and criteria before creating a query. Preview the query, approve import, and follow progress in the run drawer.

All requests pass through `src/lib/api.ts`. Backend UUIDs remain intact; that client maps wire types from `src/types/backend.ts` into the existing workspace view models in `src/types/api.ts`. TanStack Query caches are scoped by review ID and refreshed after mutations.

Copy `.env.example` to `.env.local` to customize the API prefix or development proxy. A deployed build needs a same-origin `/api` reverse proxy or `VITE_API_BASE_URL` pointing to the backend at build time. The development proxy is not a production server.

```sh
npm run test
npm run lint
npm run build
```

Fixtures under `src/mocks/` are imported by tests only. See the live integration guide for limitations and verified workflows.
