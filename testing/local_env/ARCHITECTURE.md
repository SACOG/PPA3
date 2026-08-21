# Maintainer Architecture

## Runtime flow

1. `webapp/app.py` validates form fields against `live_contract.json` and resolves a registered
   local candidate line.
2. `dispatch.py` converts program, project type, and selected outcomes into the ordered production
   service list.
3. `orchestrator.py` creates an atomic manifest and starts a background controller thread.
4. For isolation, the controller launches `run_local.py` in a new ArcGIS Pro Python process for
   each service.
5. `run_local.py` sets `PPA3_LOCAL_CONFIG`, applies the safety gate, maps web fields to the report
   service input schema, and calls the existing GP entry function.
6. The controller preserves logs/results, updates status after every transition, and writes the
   merged output.
7. `reporting/render.py` creates a standalone report using specialized YAML layouts or its generic
   lossless fallback.

## Deliberate boundaries

The harness owns contract modeling, local path redirection, process orchestration, observability,
and report presentation. The GP calculations remain in their existing service folders. Changes to
those folders should be limited to the local-config switch or a narrowly proven invocation fix.

`build_test_gdb.py` is the only data-refresh entry point. It reads approved production sources and
writes to the configured local root. Candidate source geometry is copied during this same step so
runtime is independent of mapped drives.

Each invocation creates a unique scratch workspace beside its run manifest. Never restore the old
behavior that deleted ArcPy's account-wide default `scratch.gdb`; that can interfere with ArcGIS Pro
and other standalone Python sessions.

The controller also copies `PPA3Testing_run.gdb` into each run directory and writes a run-specific
`globalconfig/data_paths.yaml` that points logging to that copy. Treat the sandbox run GDB as an
empty schema template, not a shared runtime database.

## Extension points

- Add/change public inputs in `live_contract.json`, then update dispatch and web tests.
- Register project lines in `samples/lines.json`, then rerun setup.
- Add a specialized outcome layout at `reporting/layout/<service>.yaml`; otherwise the generic
  renderer remains complete and useful.
- Add a service only after registering its folder/module/function in the contract and ensuring its
  `config_links.py` honors `PPA3_LOCAL_CONFIG`.

## Verification layers

- Pure tests: contract, dispatch, configuration containment, orchestration failure behavior, and
  report fallback behavior.
- Flask tests: form states, validation, preview, dashboard, and route containment.
- Doctor: license, packages, sandbox assets, all service safety gates, candidate geometry, and port.
- Real matrix: ATP non-freeway, full non-freeway, freeway, and Federal-input runs.

Raw run evidence is intentionally ignored by Git. Commit code/config/docs, never generated run
folders, service logs, merged project results, or copied sandbox data.
