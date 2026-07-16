"""
tcac_score.py — TCAC opportunity score indicator for Community Design.

Reports the maximum TCAC composite opportunity index (`index_`) among the TCAC
opportunity areas a project directly intersects, plus that polygon's opportunity
category (`oppcat`).

IMPORTANT: no module-level `arcpy` or `parameters` import — arcpy is imported
inside get_max_tcac so the pure logic stays testable without arcpy.
"""


def _select_max_tcac(rows):
    """Pick the (index, category) with the greatest index.

    rows: iterable of (index, category) tuples; index is float|None, category str|None.
    Returns (max_index, category) or (None, None) if no row has a non-None index.
    A blank/None category on the chosen row is reported as "Not Categorized".
    On an index tie, the first-encountered row wins.
    """
    best_index = None
    best_category = None
    for index, category in rows:
        if index is None:
            continue
        if best_index is None or index > best_index:
            best_index = index
            best_category = category
    if best_index is None:
        return (None, None)
    if best_category is None or str(best_category).strip() == "":
        best_category = "Not Categorized"
    return (best_index, best_category)


def get_max_tcac(fc_project, fc_tcac, col_index="index_", col_category="oppcat"):
    """Return the max TCAC index (and its category) among polygons fc_project intersects.

    fc_tcac resolves against arcpy.env.workspace (the fgdb). Read-only.
    Returns {"tcac_index": float|None, "tcac_category": str|None}.
    """
    import arcpy

    lyr = "tcac_sel_lyr"
    if arcpy.Exists(lyr):
        arcpy.management.Delete(lyr)
    arcpy.management.MakeFeatureLayer(fc_tcac, lyr)
    arcpy.management.SelectLayerByLocation(lyr, "INTERSECT", fc_project)
    rows = [(r[0], r[1]) for r in arcpy.da.SearchCursor(lyr, [col_index, col_category])]
    arcpy.management.Delete(lyr)

    max_index, category = _select_max_tcac(rows)
    return {"tcac_index": max_index, "tcac_category": category}
