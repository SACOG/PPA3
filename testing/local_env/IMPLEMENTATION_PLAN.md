# PPA3 Local Test Environment — Delivery Plan

## Objective

Deliver a production-safe, portable SACOG developer environment that reproduces the current PPA
input contract, dispatches the same ordered GP services against sandbox data, preserves every raw
result, and produces a useful browser report. Wishlist features and their validation suite remain
outside this effort.

## Definition of done

- A supported SACOG Windows PC with ArcGIS Pro can prepare the environment through one setup entry
  point, diagnose it through one health-check entry point, and launch it through one start command.
- No username-specific executable paths or mandatory `C:\PPA3Testing` assumptions remain.
- The local form represents every meaningful current PPA input. Candidate feature classes replace
  interactive map drawing.
- STIP, CMCP, ATP, and both Federal project types resolve to the current live service order.
- Fixed production choices are clear and protected by default; any developer-only override is
  conspicuous and recorded in the run manifest.
- Each service runs in isolation, failures do not erase earlier results, and manifests/logs are
  written safely and incrementally.
- Every dispatched service appears in the HTML report. Hand-authored layouts are used where they
  exist and a structured raw-data fallback is used everywhere else.
- The environment passes unit/integration tests and a representative real ArcGIS run matrix.
- A fresh-checkout rehearsal succeeds using only the checked-in documentation.

## Milestone 1 — production contract

1. Store a reviewed, normalized snapshot of the public VertiGIS workflow definitions.
2. Model report program separately from funding program.
3. Update ATP to the current six fixed outcomes, including Equity.
4. Confirm STIP/CMCP selectable catalogs and Federal fixed catalogs.
5. Add drift auditing without making normal local use depend on the internet.

Exit check: pure-Python tests prove every program/type dispatch and field rule.

## Milestone 2 — portability and safety

1. Centralize configuration and discover ArcGIS Pro Python without a username-specific path.
2. Make the sandbox root configurable, retaining `C:\PPA3Testing` as the default.
3. Add `setup.ps1`, `doctor.ps1`, and `start.ps1`.
4. Make builders accept explicit roots and source locations.
5. Keep production sources read-only and validate every resolved write target.

Exit check: doctor reports actionable pass/fail results; unit tests pass from the discovered Pro
Python environment.

## Milestone 3 — input and orchestration parity

1. Replace the bare form with a clear developer form grounded in the live contract.
2. Add Federal funding subprograms, confirm-email validation, current help text, and candidate-line
   compatibility filtering.
3. Add a pre-run dispatch preview and explicit developer override mode.
4. Record effective inputs, override state, service timing, error summaries, and environment
   metadata in the manifest.
5. Use collision-safe run identifiers and atomic manifest writes.

Exit check: Flask tests cover all program states, validation failures, preview output, and report
route containment.

## Milestone 4 — report robustness

1. Preserve the five existing specialized ATP layouts.
2. Add Equity support for the current ATP contract.
3. Add a generic renderer for every service without a specialized layout.
4. Render failed, missing, malformed, and partial services without crashing the whole report.
5. Include dispatch/input metadata and make developer overrides visible.

Exit check: synthetic all-service manifests render every dispatched section into a self-contained
offline HTML file.

## Milestone 5 — real data validation

1. Refresh or verify the sandbox from the approved read-only sources.
2. Register reachable candidate lines and validate their geometry/type compatibility.
3. Run representative ATP non-freeway, full non-freeway, freeway, and Federal-input paths.
4. Compare dispatch/results against the stored contract and reports against the real ATP/CMCP
   references.
5. Record runtime, expected data limitations, and reproducible defects separately from harness
   defects.

Exit check: at least one complete real run produces manifest, logs, merged JSON, and report; the
remaining matrix is either passing or documented with exact evidence and remediation.

## Milestone 6 — handoff

1. Rewrite the README around setup, launch, daily use, refresh, troubleshooting, and safety.
2. Add a five-minute team demo script and a maintainer architecture note.
3. Rehearse from a fresh checkout or isolated temporary working copy.
4. Produce a final scope/diff/test report before requesting commit or push authorization.

## Scope guard

Do not transplant or implement PPA wishlist items, TCAC work, unrelated layer-building changes, or
their validation suites. Fix an underlying GP script only when a current production service cannot
be invoked through the harness and the fix is narrowly necessary for the existing behavior.

