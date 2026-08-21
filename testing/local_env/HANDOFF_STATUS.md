# PPA3 Local Test Environment — Work Ledger

This file is the persistent session handoff. Update it after every milestone or material blocker.

## Current state

- Working branch: `local-test-env` (branched from `main`)
- Base clone: `SACOG/PPA3` branch `main`
- Final harness suite: 42 passing tests under ArcGIS Pro 3.7 base Python.
- Report runtime transplanted; report route smoke-tested successfully
- Committed to `local-test-env`; the suite runs green against stock `main` plus the gp-services hooks
- The committed changes are the curated local-environment transplant: `testing/local_env/` plus 30 backward-compatible gp-services files
- The current public workflow contract is stored in `live_contract.json`; its read-only audit
  matches all five reachable live workflow variants as of 2026-08-12.

## Confirmed production contract

- STIP: selectable project type and outcomes; six freeway/eight non-freeway outcomes.
- CMCP US50: selectable project type and outcomes; six freeway/eight non-freeway outcomes.
- ATP: fixed non-freeway type; current live workflow lists six outcomes, including Equity.
- Federal: separate freeway/non-freeway entry choices; fixed outcomes; both use report name
  `Regional Federal Funding Program`; each requires one of three funding subprograms.
- Outcome-to-service mapping is project-type driven. Program controls the allowed outcome set and
  whether it is selectable.

## Completed implementation

- Portable config, ArcGIS Python discovery, configurable sandbox root, and setup/doctor/start
  entry points.
- Current live contract, exact dispatch preview, separate report/funding programs, ATP Equity,
  Federal funding choices, validation, and explicit recorded developer override.
- Background process orchestration with atomic manifests, collision-safe IDs, timings, timeouts,
  logs, and continuation after individual failures.
- Functional browser input/status/history/report flow grounded in the live tool.
- Specialized Equity reporting plus a lossless generic renderer for every other successful service;
  failed services show their recorded error.
- Candidate line is staged into the local GDB during setup, removing the mapped-drive runtime
  dependency.
- Maintainer architecture and five-minute team demo handoff documents.
- Private per-service scratch and private per-run archive/config prevent collisions with ArcGIS Pro
  and other harness sessions.
- Real validation completed for ATP, every non-freeway service, every freeway service, and Federal
  funding input propagation. See `VALIDATION.md` for run IDs and evidence.

## Access checkpoint

`I:` was not mounted in the Codex process; `setup.ps1 -CandidateSource <path>` handles this portably,
and the staged local `TestTruxelBridge` was verified with ArcPy. The apparent licensing problem was
execution-context isolation: ArcPy reports ArcInfo/3.7 in the normal Windows user context. ArcGIS
Pro remained open successfully during the complete run matrix.

## Next action

Independent of `data_layer_update`: this branch deliberately does not carry the data-layer work, so the
test environment can be created from `main` alone.
