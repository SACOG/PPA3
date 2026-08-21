# PPA3 Local Test Environment

This is a production-safe developer harness for the existing PPA3 report services. It mirrors the
public PPA input contract, substitutes registered candidate lines for map drawing, runs the same GP
report code against a local data sandbox, exposes progress and logs in a browser, merges the JSON
outputs, and creates a self-contained HTML report.

It does **not** include PPA wishlist features, TCAC work, data-layer-update work, or the former
wishlist validation suite.

## First-time setup on a SACOG Windows PC

Requirements: ArcGIS Pro, access to the SACOG PPA server paths, and a project-line feature class.
Close ArcGIS Pro environment/package operations before setup so the Pro Python environment is not
locked.

```powershell
git clone --branch test-environment https://github.com/SACOG/PPA3.git
cd PPA3
Set-ExecutionPolicy -Scope Process Bypass
.\testing\local_env\setup.ps1
```

The default candidate source is
`I:\Projects\Darren\PPA_V2_GIS\PPA_V2.gdb\TestTruxelBridge`. If `I:` is not mapped, provide the
same feature class by another reachable path:

```powershell
.\testing\local_env\setup.ps1 -CandidateSource "\\server\share\data.gdb\TestLine"
```

Setup discovers ArcGIS Pro Python, installs the small web dependencies if necessary, copies
read-only production reference data into `C:\PPA3Testing`, stages the candidate line locally,
creates local run tables, runs harness tests, and finishes with the health check. Production data
is never updated by this process.

To use a different sandbox root:

```powershell
.\testing\local_env\setup.ps1 -Root "D:\PPA3Testing"
```

If the team uses a named ArcGIS Pro clone, select it explicitly:

```powershell
.\testing\local_env\setup.ps1 -Python "$env:LOCALAPPDATA\ESRI\conda\envs\ppa3-local\python.exe"
```

Setup remembers the selected interpreter in the local sandbox, so later `start.ps1` and
`doctor.ps1` use the same clone automatically.

## Daily use

```powershell
.\testing\local_env\start.ps1
```

Open `http://127.0.0.1:5000`. Choose the report program, project type, funding program when shown,
candidate line, project facts, and outcomes. Confirm the dispatch preview, then start the run. The
detail page updates while each isolated service runs and links to the final report when merging is
complete.

Run folders live under `testing\local_env\out\runs\<timestamp>` and contain:

- `_sample.json`: exact GP-style inputs;
- `manifest.json`: contract version, environment, override flag, status, timing, and errors;
- `<service>.log` and successful `<service>.json` files;
- `merged.json`: all successful service outputs;
- `report.html`: single-file offline report.

The report uses specialized presentation layouts where available. Every other successful service
still appears as a field summary with expandable complete JSON. A failed service appears with its
actual recorded error and never prevents later services from running.

## Health check and refresh

```powershell
.\testing\local_env\doctor.ps1
.\testing\local_env\setup.ps1 -SkipDependencyInstall
```

The second command refreshes sandbox data and candidate geometry, rebuilds schemas, tests, and
checks the result. Useful targeted variants:

```powershell
.\testing\local_env\setup.ps1 -SkipDataRefresh
.\testing\local_env\setup.ps1 -SkipArchiveSchemas
.\testing\local_env\start.ps1 -Port 5050
```

Environment variables:

- `PPA3_LOCAL_ROOT`: sandbox root; default `C:\PPA3Testing`.
- `PPA3_PRO_PYTHON`: explicit ArcGIS Pro `python.exe` when auto-discovery is insufficient.
- `PPA3_SERVICE_TIMEOUT_SECONDS`: per-service timeout; default 1800 seconds.

## Contract fidelity

`live_contract.json` is the normalized public workflow contract captured on 2026-08-12. It keeps
report program separate from funding program and models:

- STIP and CMCP: selectable freeway/non-freeway types and outcomes;
- ATP: fixed non-freeway type and its current six outcomes, including Equity;
- Federal: freeway/non-freeway entry paths, fixed outcomes, and three required funding programs.

To check for public workflow drift without changing local behavior:

```powershell
python .\testing\local_env\audit_live_contract.py
```

## Candidate lines

Candidate definitions are in `samples\lines.json`. Setup copies each source feature class into the
local `PPA3Testing.gdb`; the form and GP runs use only that local copy. Add another registry entry
with a unique `local_name`, reachable `source_path`, and compatible project types, then rerun setup.
The `-CandidateSource` convenience switch overrides the source for the current single-candidate
registry.

## Safety model

- All production SDE, raster, CSV, and JSON locations are read-only sources.
- All intended writes resolve beneath the configured sandbox or the repository run-output folder.
- `PPA3_LOCAL_CONFIG` redirects the 15 report services to staged local configuration.
- Each service passes a source scan that rejects production database/write references.
- Every service runs in a separate Python process with a private scratch workspace; one crash does
  not corrupt the controller or delete another ArcGIS session's scratch geodatabase.
- Every run receives a private copy of the empty archive schema; services never append to the
  shared sandbox archive GDB during normal harness use.
- Manifest and merged JSON updates are atomic.
- Developer overrides are off by default, visible in the form, and recorded in the manifest.

Do not point `PPA3_LOCAL_ROOT` at a production or shared geodatabase. Do not bypass the safety gate.

## Troubleshooting

**Product License has not been initialized** — close or finish any ArcGIS Pro environment clone,
restart ArcGIS Pro, and rerun `doctor.ps1`. Concurrent package/environment operations can
temporarily prevent `arcpy` from acquiring the license.

**Candidate source not found** — map `I:`, connect VPN if required, or pass `-CandidateSource` with
a reachable feature-class path. Once setup succeeds, normal runs use the local copy.

**Port 5000 unavailable** — launch with `start.ps1 -Port 5050`.

**A service fails** — open its log on the run detail page. Other outcomes and `merged.json` remain
available. The report states the service error rather than dropping the section.

**Public UI changed** — run `audit_live_contract.py`, review the differences, then deliberately
update `live_contract.json` and its dispatch tests; normal startup never scrapes production.

See [ARCHITECTURE.md](ARCHITECTURE.md) for maintainers, [DEMO.md](DEMO.md) for the team handoff, and
[VALIDATION.md](VALIDATION.md) for the final real-run evidence.
