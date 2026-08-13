# GP-service Python requirements

`requirements.txt` lists the direct third-party Python dependencies imported by
the PPA geoprocessing report services. ArcPy is intentionally excluded because
it is supplied and licensed by the matching ArcGIS Pro or ArcGIS Server Python
runtime.

## Installing

Create a clone of the ArcGIS Python environment rather than modifying the
default environment. From the activated clone, run:

```powershell
python -m pip install -r requirements.txt
```

The pinned versions were tested with ArcGIS Pro 3.7. Revalidate them when
upgrading ArcGIS Pro because compiled geospatial packages must remain compatible
with Esri's Python runtime.

## Validation performed

Testing was performed on August 13, 2026 in a clean clone of the ArcGIS Pro 3.7
default Python environment:

- The requirements installed successfully and all six packages imported.
- ArcPy initialized with an ArcGIS Advanced (`ArcInfo`) license.
- All 25 GP-service entrypoints and their transitive Python dependencies
  imported successfully.
- Each entrypoint was executed separately against synthetic local feature
  classes, rasters, CSV files, and JSON templates in a disposable sandbox.
- Production hostnames, URLs, UNC paths, `.sde` connections, ArcGIS Server
  directories, and output paths outside the sandbox were rejected before
  execution. Server logging and public map delivery were redirected locally.
- 22 of 25 entrypoints completed their calculations and produced local report
  output. The three remaining failures were existing service/configuration
  issues, not missing Python packages: Housing Choice references an undefined
  `col_housing_type`; Existing Assets and Mixed Use use a legacy community-type
  classifier that did not classify the synthetic test geometry.

`pip check` also reports conflicts already present in Esri's base environment,
including packages not imported by these GP report services. Those conflicts did
not prevent dependency imports or the verified functional runs.
