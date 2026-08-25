# Story 30 - Establish local → staging → prod environments (GitHub push = staging)

## Status
**Proposed. Infra decision — needs Anthony.** This changes the deploy model currently described in
AGENTS.md rule 10 ("`main` is production; GitHub Pages auto-deploys; there is no staging").

## Problem
Today there are effectively two deploy realities and **no staging**:
- **Public marketing site** (`index.html`, `blog/`, Jekyll) → GitHub Pages → **`simplifyops.co`**
  (the `CNAME`) on push to `main`. That means every push to `main` is a **production** publish.
- **Admin control plane** (`admin_api` + `gateway` + Jinja UI) → runs on **this pi**
  (local/Tailscale); "deploy" = pull + `systemctl restart`, not GitHub Pages.

The owner wants three explicit environments — **local (this machine) → staging (GitHub) →
prod (GitHub)** — where **pushing to GitHub lands in staging**, and staging→prod is a separate,
deliberate promotion handled later.

## Open decisions for Anthony (architecture — rule 3)
1. **Branch/topology** — staging = a `staging` branch (prod = `main`)? Or staging = `main` with
   prod cut from a `release`/tag? This determines what "push to GitHub = staging" means concretely.
2. **Pages target + domain** — GitHub Pages currently publishes `main` to the prod domain
   `simplifyops.co`. Staging needs its own Pages target / preview URL so a staging push does **not**
   hit the prod domain. (Environments/CI or a second Pages site.)
3. **Scope** — does the staging/prod split cover only the marketing site (GitHub Pages), or also a
   staging instance of the control plane? (The control plane isn't on Pages.)
4. **Promotion mechanism** — how staging → prod happens (manual merge/tag, workflow). Explicitly
   deferred per owner ("we will handle staging → prod another time").

## Proposed approach (pending the decisions above)
- Define the branch topology and add the Pages/deploy config so a GitHub push publishes to a
  **staging** target, leaving the prod domain untouched until an explicit promotion.
- Update AGENTS.md rule 10 + `product/product-dev-guidelines.md` to describe the real pipeline once
  wired. Until then, the docs mark the staging/prod split as **pending this story** and warn that
  pushes to `main` still reach the prod domain.

## Acceptance
- A push to GitHub deploys to **staging** (not the prod domain); prod is reached only by a
  deliberate promotion step.
- AGENTS.md rule 10 and `product-dev-guidelines.md` match the wired reality.
- Gate as applicable (mostly config/docs); coordinate on shared infra per rule 8.

## Review
_(fill before commit/push.)_

## Notes
Until this lands, treat GitHub `main` pushes with production-level care — see the note in
`product/product-dev-guidelines.md`.
