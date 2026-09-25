# Repair delivery — 24 September 2026

## Implemented

1. Corrected measurement units, full observed epoch history, search verdict consistency and benchmark metric scope.
2. Added transactional CSV validation/import with exact schemas, lot declarations, completeness checks and immutable measurements.
3. Connected full-lot Module A and reconstructed rehearsal Module B inference. Verified bundled artifact hashes. Stored immutable forecasts, run hashes, policy versions and provenance.
4. Added observed REJECT / predicted-risk HOLD separation and historical observed-failure retention.
5. Added operator-protected operational reads/writes, read-only default, request-size bounds, finite-number validation, literal search and bounded pagination.
6. Added a workspace for imports, analysis, evidence review, append-only review notes and CSV/JSON exports.
7. Fixed stale request races, API error messages, missing-page handling, fake online indicator and operating-cutoff label. Split frontend pages into separately loaded bundles.
8. Added configurable database storage, real readiness, pinned runtime dependencies, Docker build, Render demo config and GitHub Actions checks.
9. Added 78-part synthetic training fixtures and rewritten setup/deployment instructions.

## Evidence

- 19 backend integration/workflow tests passed locally.
- Production frontend build passed.
- Source lint exits successfully; four React effect-state advisory warnings remain. These effects initialize asynchronous requests. No lint errors.
- Explicit undefined-name check uses browser globals.
- Checked patch whitespace and application import/runtime artifact loading.
- Local browser navigation was blocked by the browser environment; visual/mobile acceptance is not claimed.
- Docker deployment, Render persistence/backup restoration and production load were not tested in this environment.

## Remaining gates

The original Module B fitted artifact is absent from the supplied repository. The rebuilt artifact is REHEARSAL and has no independent operational validation yet. Historical prediction metrics must not be reused as its accuracy claim. Real-device evaluation, false-positive/false-negative analysis, interval calibration, variant/lot slices and engineering release approval remain necessary.

Infrastructure still needs an operator key and durable storage configured by the deployment owner. For production add individual user accounts/roles, audited measurement revisions, monitoring, backup restoration testing, multi-instance database support and instrument ingestion. This delivery does not claim every possible bug is fixed or a production-ready “10/10”.

## Apply safely

Use a new branch and inspect the included combined patch before merging. The patch targets upstream commit aea60f9b81c214d910a24fe4495921af26e85954. If upstream has changed, resolve conflicts instead of replacing newer work blindly. No remote push or deployment was performed.
