# Delivery Validation — 2026-08-13

## Automated verification

- `42 passed` under ArcGIS Pro 3.7 base Python.
- Doctor: all required checks passed, including ArcInfo licensing, packages, sandbox assets, all 15
  source safety gates, candidate geometry, and port availability.
- Public workflow drift audit: all five reachable live workflow variants matched
  `live_contract.json` on 2026-08-12.
- Documented `setup.ps1` rehearsal passed against the existing sandbox without refreshing data or
  changing packages.
- Documented `start.ps1` rehearsal served the real form on port 5055 with HTTP 200; the temporary
  process tree was then stopped.

## Real ArcGIS run matrix

All successful runs used `C:\PPA3Testing\PPA3Testing.gdb\TestTruxelBridge`, ArcGIS Pro 3.7, a
private scratch workspace per service, and a private archive GDB per run.

| Path | Run ID | Result | Runtime evidence |
|---|---|---|---|
| ATP fixed non-freeway | `20260813_005857_017021` | Title + all 6 ATP outcomes passed; merged JSON and report passed | 157.5 seconds total |
| STIP additional non-freeway outcomes | `20260813_010541_421139` | Title, Congestion, and Freight passed | 132.8 seconds total |
| STIP freeway full catalog | `20260813_011145_722943` | Title + all 6 freeway outcomes passed; merged JSON and report passed | 88.0 seconds total |
| Federal fixed non-freeway | `20260813_011345_056251` | Title + all 8 outcomes passed; merged JSON and report passed | 228.4 seconds total |

The Federal run preserved distinct values throughout the pipeline:

- report program: `Regional Federal Funding Program`;
- funding subprogram / GP `Funding_Program`: `System Preservation Program`.

Together the green runs execute every currently dispatched non-freeway and freeway GP service.
CMCP shares those service mappings; its distinct selectable contract is covered by contract,
dispatch, preview, and form tests rather than duplicating the same GP calculations.

## Defects found and repaired

Real execution exposed callable entry points that relied on variables initialized only in their
`if __name__ == '__main__'` blocks. Narrow bindings were moved into the existing functions for VMT,
Congestion, Multimodal, Economic Prosperity, Freight, Safety, Equity, SGR, and their freeway
counterparts. No calculation formula, dataset, output schema, or wishlist behavior was changed.
`test_entrypoint_bindings.py` prevents these callable-runtime names from regressing.

## Known local-only limitation

The sandbox does not contain `C:\PPA3Testing\PPA3_GIS_SVR.aprx`. Services catch that map export
failure and still produce valid metric JSON. The HTML renderer clearly shows its local “map not
available” placeholder. This does not affect metric calculations, merged JSON, service status, or
the rest of the report.

## Coexistence evidence

ArcGIS Pro remained open and responsive during the real run matrix. The harness no longer deletes
ArcPy's account-wide default scratch GDB and never writes normal run logs to the shared sandbox
archive GDB. Each service has private scratch; each run has private archive/config. Another Codex
session can use a separate Python environment without license or file-GDB interference, though
concurrent GP work still shares ordinary machine CPU, RAM, and read bandwidth.
