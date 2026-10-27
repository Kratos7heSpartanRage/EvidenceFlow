# Frontend Guide
- All server calls go through src/lib/api.ts using types in src/types/api.ts (generated from
  OpenAPI once available; hand-written mirror before that). No fetch() in components.
- Server state via TanStack Query; poll /api/runs/{id} every 1.5s while status=running.
- Structure: src/features/<area>/{components,hooks,pages}; shared UI in src/components/ui.
- Every data view handles loading, empty (with a next-step hint), error (with retry) and success.
- Forms: client validation mirrors backend (exclude requires reason; date_from ≤ date_to;
  non-empty expression). Still display backend 422 messages.
- Machine vs human: machine suggestions use an outlined "Suggested" badge with evidence tooltip;
  human decisions use a solid badge with reviewer + time; inherited/conflict_resolution origins
  are labelled. Never render a suggestion as if it were a decision.
- Counts on the dashboard come from API responses only. No literals.
- Accessibility: keyboard I/E/M/N(ext) on screening; focus management in modals; aria-labels on
  icon buttons; colour is never the only signal.
- Show the NCBI disclaimer wherever PubMed results appear.
- Tests: Vitest + Testing Library for the reason-required modal, badge rendering, diff rendering
  from fixture JSON.
- Develop against src/mocks/*.json until the endpoint exists; delete a mock when its endpoint ships.
