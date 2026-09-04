# Stories — Parking Lot

Parked / deferred work (revisit when the need arises). Full parked story files (where they exist)
live in `product/stories/parking-lot/`.

| # | Title | Reason |
|----|----|----|
| — | Docker deployment profile | Owner: skip Docker; native/systemd only. Revisit if reproducible-topology need arises |
| 42 | Schemathesis API gate | Parked 2026-09-02 by owner → `product/stories/parking-lot/story-42-schemathesis-api-gate.md`. Needs infra (running app + disposable DB); admin API still small/stable — lower ROI than config/Settings/soul. Resume anytime. |
| 43 | Provider-neutral contracts package | Parked 2026-09-04 → `parking-lot/story-43-contracts-package.md`. Premature — one control plane + gateway, boundaries already clean seams. Revisit with the P2 runtime-plane split. |
| 46 | Soul/skills/knowledge + self-knowledge | Parked 2026-09-04 → `parking-lot/story-46-soul-skills-knowledge.md`. Ahead of consumption — nothing loads knowledge/self-knowledge yet; soul done ([[story-60]]). Resume when the runtime loads knowledge (P2 [[story-51]]). |
| 48 | Companies + company-access + identity_claims | Parked 2026-08-27 by owner — do the rest of P1 first, come back to companies later. Full subsystem (tables `companies`/`person_company_access`/`identity_claims`, a company service, Companies admin page, and company-access wiring into the People create/edit/view flow). Completes the deferred story-31 follow-up. |
