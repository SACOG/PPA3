"""
Name: add_poverty_race_to_parcels.py
Purpose: Tags census block group poverty and race/ethnicity data onto parcel points.
    Each parcel receives a prorated count: parcel POP_TOT * block group share.
    This enables the equity report to aggregate poverty and ethnic composition
    within a project buffer using the standard LandUseBuffCalcs workflow.

    Fields added to parcel_data_pts_{year}:
        pop_pov200    -- population in HH earning < 200% federal poverty level
        pop_white_nh  -- white non-Hispanic population
        pop_afr_am_nh -- African American non-Hispanic population
        pop_asian_nh  -- Asian non-Hispanic population
        pop_other_nh  -- other non-Hispanic population (incl. multiracial, Am. Indian)
        pop_hisp      -- Hispanic/Latino population (any race)

Usage:
    1. Run this script once per data vintage to update parcel_data_pts_{year}.
    2. Then re-run reg-ctype-aggregation/PPA3_ctype_region_agg.py to regenerate
       Agg_ppa_vals_latest.csv with regional and community-type benchmark values
       for the new equity metrics.

Census CSV format expected:
    Both CSVs must have a GEOID column (matching the block group spatial layer).
    Race CSV columns: pop_tot, pop_white_nh, pop_afr_am_nh, pop_asian_nh, pop_other_nh, pop_hisp
    Poverty CSV columns: pop_tot, pop_pov200
    Sources: ACS 5-year estimates, tables B02001/B03003 (race) and C17002 (poverty ratio)

Author: Terrell-Tyce
Last Updated: Jun 2026
"""
import os
from pathlib import Path

import arcpy
import pandas as pd

arcpy.env.overwriteOutput = True

# =============================================================================
# PATHS — swap comment blocks for local testing vs. production deployment
# =============================================================================

# --- PRODUCTION server paths (active when deploying) ---
# Swap these in when the server parcel FC and block group layer are ready.
# fgdb_or_sde = r'I:\SDE_Connections\SDE-PPA\owner@PPA.sde'
# parcel_fc_year = 2020
# bg_fc = r'I:\Projects\Darren\PPA3_GIS\PPA3_GIS.gdb\Census_BlockGroups2020_region'
# bg_race_csv = r'I:\Projects\Darren\PPA3_GIS\CSV\Census2020\BGRaceDataCensus2020.csv'
# bg_poverty_csv = r'I:\Projects\Darren\PPA3_GIS\CSV\Census2020\BGPoverty200pct2020.csv'

# --- LOCAL TESTING paths (active) ---
# Update these to point at your local test GDB before running locally.
fgdb_or_sde = r'<your local GDB path here>'   # e.g. r'C:\GIS\PPA3_test.gdb'
parcel_fc_year = 2020
bg_fc = r'<GDB path>\Census_BlockGroups2020_region'
bg_race_csv = r'<path>\BGRaceDataCensus2020.csv'
bg_poverty_csv = r'<path>\BGPoverty200pct2020.csv'

# =============================================================================
# CENSUS CSV COLUMN NAMES — adjust if your census extracts use different names
# =============================================================================

F_GEOID = 'GEOID'

# Race CSV columns (ACS B02001 + B03003)
F_BG_POP_TOT = 'pop_tot'
F_BG_WHITE   = 'pop_white_nh'
F_BG_AFR_AM  = 'pop_afr_am_nh'
F_BG_ASIAN   = 'pop_asian_nh'
F_BG_OTHER   = 'pop_other_nh'   # other non-Hispanic (Am. Indian, multiracial, etc.)
F_BG_HISP    = 'pop_hisp'

# Poverty CSV columns (ACS C17002, <200% FPL)
F_BG_POV200  = 'pop_pov200'

# Output field names written to the parcel FC
OUT_FIELDS = ['pop_pov200', 'pop_white_nh', 'pop_afr_am_nh', 'pop_asian_nh', 'pop_other_nh', 'pop_hisp']


def _ensure_fields(fc, field_names):
    existing = {f.name for f in arcpy.ListFields(fc)}
    for fname in field_names:
        if fname not in existing:
            arcpy.management.AddField(fc, fname, 'DOUBLE')
            arcpy.AddMessage(f"  Added field: {fname}")


def _build_bg_lookup(bg_fc_path, race_csv, poverty_csv):
    """Returns dict: GEOID (str) -> dict of shares (0.0–1.0) per demographic group."""

    df_race = pd.read_csv(race_csv, dtype={F_GEOID: str})
    df_pov  = pd.read_csv(poverty_csv, dtype={F_GEOID: str})

    # Use outer join so a BG only in one file still gets processed
    df = df_race.merge(df_pov[[F_GEOID, F_BG_POV200]], on=F_GEOID, how='outer')

    pop = df[F_BG_POP_TOT].replace(0, pd.NA)  # avoid divide-by-zero

    df['_pov200_share']  = (df[F_BG_POV200] / pop).fillna(0).clip(0, 1)
    df['_white_share']   = (df[F_BG_WHITE]   / pop).fillna(0).clip(0, 1)
    df['_afr_am_share']  = (df[F_BG_AFR_AM]  / pop).fillna(0).clip(0, 1)
    df['_asian_share']   = (df[F_BG_ASIAN]   / pop).fillna(0).clip(0, 1)
    df['_other_share']   = (df[F_BG_OTHER]   / pop).fillna(0).clip(0, 1)
    df['_hisp_share']    = (df[F_BG_HISP]    / pop).fillna(0).clip(0, 1)

    return df.set_index(F_GEOID)[[
        '_pov200_share', '_white_share', '_afr_am_share',
        '_asian_share', '_other_share', '_hisp_share'
    ]].to_dict('index')


def _sjoin_bg_geoid_to_parcels(parcel_fc, bg_fc_path):
    """Spatial join: tags BG GEOID onto each parcel. Returns path to join result."""
    fl_pcl = 'fl_pcl_pov_race'
    fl_bg  = 'fl_bg_pov_race'
    sjoin_out = r'memory\pcl_bg_sjoin_pov_race'

    for fl in [fl_pcl, fl_bg, sjoin_out]:
        if arcpy.Exists(fl):
            arcpy.management.Delete(fl)

    arcpy.management.MakeFeatureLayer(parcel_fc, fl_pcl)
    arcpy.management.MakeFeatureLayer(bg_fc_path, fl_bg)

    arcpy.analysis.SpatialJoin(
        target_features=fl_pcl,
        join_features=fl_bg,
        out_feature_class=sjoin_out,
        join_operation='JOIN_ONE_TO_ONE',
        join_type='KEEP_ALL',
        match_option='INTERSECT',
        field_mapping=f'{F_GEOID} "{F_GEOID}" true true false 80 Text 0 0,First,#,{fl_bg},{F_GEOID},-1,-1'
    )
    return sjoin_out


def _populate_parcel_fields(parcel_fc, sjoin_fc, bg_lookup):
    """Writes poverty/race count fields into parcel FC using PARCELID as the join key."""

    f_parcelid = 'PARCELID'
    f_pop_tot  = 'POP_TOT'

    # Build parcelid -> geoid map from the spatial join result
    parcel_to_geoid = {}
    with arcpy.da.SearchCursor(sjoin_fc, [f_parcelid, F_GEOID]) as cur:
        for row in cur:
            if row[1] is not None:
                parcel_to_geoid[row[0]] = str(row[1])

    update_fields = [f_parcelid, f_pop_tot] + OUT_FIELDS

    n_updated = n_no_match = 0
    with arcpy.da.UpdateCursor(parcel_fc, update_fields) as cur:
        for row in cur:
            pclid   = row[0]
            pop_tot = row[1] if row[1] else 0
            geoid   = parcel_to_geoid.get(pclid)

            if geoid and geoid in bg_lookup:
                bg = bg_lookup[geoid]
                row[2]  = round(pop_tot * bg['_pov200_share'])
                row[3]  = round(pop_tot * bg['_white_share'])
                row[4]  = round(pop_tot * bg['_afr_am_share'])
                row[5]  = round(pop_tot * bg['_asian_share'])
                row[6]  = round(pop_tot * bg['_other_share'])
                row[7]  = round(pop_tot * bg['_hisp_share'])
                n_updated += 1
            else:
                row[2] = row[3] = row[4] = row[5] = row[6] = row[7] = 0
                n_no_match += 1

            cur.updateRow(row)

    arcpy.AddMessage(f"  Updated {n_updated} parcels with poverty/race data.")
    if n_no_match:
        arcpy.AddMessage(f"  {n_no_match} parcels had no matching block group (set to 0).")


if __name__ == '__main__':
    arcpy.env.workspace = fgdb_or_sde

    parcel_fc = os.path.join(fgdb_or_sde, f'parcel_data_pts_{parcel_fc_year}')
    arcpy.AddMessage(f"Target parcel FC: {parcel_fc}")

    arcpy.AddMessage("Ensuring output fields exist on parcel FC...")
    _ensure_fields(parcel_fc, OUT_FIELDS)

    arcpy.AddMessage("Loading census block group poverty and race data...")
    bg_lookup = _build_bg_lookup(bg_fc, bg_race_csv, bg_poverty_csv)
    arcpy.AddMessage(f"  Loaded {len(bg_lookup)} block groups.")

    arcpy.AddMessage("Spatial joining block groups to parcels...")
    sjoin_result = _sjoin_bg_geoid_to_parcels(parcel_fc, bg_fc)

    arcpy.AddMessage("Populating poverty/race fields on parcel FC...")
    _populate_parcel_fields(parcel_fc, sjoin_result, bg_lookup)

    if arcpy.Exists(r'memory\pcl_bg_sjoin_pov_race'):
        arcpy.management.Delete(r'memory\pcl_bg_sjoin_pov_race')

    arcpy.AddMessage(
        "Done.\n"
        "Next steps:\n"
        "  1. Verify field values look reasonable in the parcel FC.\n"
        "  2. If parcel_data_pts_2035 also needs updating, re-run with parcel_fc_year = 2035.\n"
        "  3. Re-run reg-ctype-aggregation/PPA3_ctype_region_agg.py to regenerate\n"
        "     Agg_ppa_vals_latest.csv with regional/community-type benchmarks for\n"
        "     Pct_Pov200, Pct_White_NH, Pct_AfrAm_NH, Pct_Asian_NH, Pct_Other_NH, Pct_Hisp."
    )
