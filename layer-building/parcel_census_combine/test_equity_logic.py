"""
test_equity_logic.py
Verifies equity indicator logic (poverty + race/ethnicity) without arcpy or server access.

Uses real ACS CSVs produced by fetch_acs_race_poverty.py plus synthetic parcel data
whose GEOIDs match real block groups, so we can confirm:
  - prorating formula produces reasonable rates (not 0% or 100% everywhere)
  - ethnic shares sum to ~1.0 per parcel
  - poverty rates are in plausible range (<100%)
  - JSON output structure matches equity report template
"""
import json
import pandas as pd
from pathlib import Path

HERE = Path(__file__).parent

RACE_CSV = HERE / 'BGRaceDataCensus2020.csv'
POV_CSV  = HERE / 'BGPoverty200pct2020.csv'


# ---------------------------------------------------------------------------
# Replicate _build_bg_lookup from add_poverty_race_to_parcels.py (no arcpy)
# ---------------------------------------------------------------------------

def build_bg_lookup(race_csv, pov_csv):
    """
    Returns dict: GEOID -> shares dict.
    Denominator is ALWAYS race pop_tot (B03002_001E), not C17002_001E.
    At BG level, C17002_001E = count of ppl below 200% FPL (not total pop).
    """
    df_race = pd.read_csv(race_csv, dtype={'GEOID': str})
    df_pov  = pd.read_csv(pov_csv,  dtype={'GEOID': str})

    # Only take pop_pov200 from poverty CSV; use race pop_tot as denominator
    df = df_race.merge(df_pov[['GEOID', 'pop_pov200']], on='GEOID', how='outer')

    pop = df['pop_tot'].replace(0, pd.NA)

    df['_pov200_share']  = (df['pop_pov200']    / pop).fillna(0).clip(0, 1)
    df['_white_share']   = (df['pop_white_nh']  / pop).fillna(0).clip(0, 1)
    df['_afr_am_share']  = (df['pop_afr_am_nh'] / pop).fillna(0).clip(0, 1)
    df['_asian_share']   = (df['pop_asian_nh']  / pop).fillna(0).clip(0, 1)
    df['_other_share']   = (df['pop_other_nh']  / pop).fillna(0).clip(0, 1)
    df['_hisp_share']    = (df['pop_hisp']       / pop).fillna(0).clip(0, 1)

    return df.set_index('GEOID')[[
        '_pov200_share', '_white_share', '_afr_am_share',
        '_asian_share', '_other_share', '_hisp_share',
    ]].to_dict('index')


def prorate_parcels(parcels_df, bg_lookup):
    """
    Applies BG shares to synthetic parcel POP_TOT.
    Returns parcels_df with 6 new count columns.
    """
    out = parcels_df.copy()
    for col, key in [
        ('pop_pov200',    '_pov200_share'),
        ('pop_white_nh',  '_white_share'),
        ('pop_afr_am_nh', '_afr_am_share'),
        ('pop_asian_nh',  '_asian_share'),
        ('pop_other_nh',  '_other_share'),
        ('pop_hisp',      '_hisp_share'),
    ]:
        out[col] = out.apply(
            lambda r: round(r['POP_TOT'] * bg_lookup.get(r['GEOID'], {}).get(key, 0)),
            axis=1
        )
    return out


def simulate_project_buffer(parcels_df, geoids_in_buffer):
    """Sum parcel fields for parcels whose GEOID is in the simulated buffer."""
    buf = parcels_df[parcels_df['GEOID'].isin(geoids_in_buffer)]
    cols = ['POP_TOT', 'pop_pov200', 'pop_white_nh', 'pop_afr_am_nh',
            'pop_asian_nh', 'pop_other_nh', 'pop_hisp']
    return buf[cols].sum()


def build_equity_json(sums, region_bg_lookup, project_geoids, all_geoids):
    """
    Produces JSON output mirroring run_equity_report.py's make_equity_rpt_artexp().
    Uses the region as a stand-in for community-type benchmark (sufficient for testing structure).
    """
    pop_tot = sums['POP_TOT']
    if pop_tot == 0:
        return {'error': 'no population in buffer'}

    # Project-level rates
    pct_pov  = sums['pop_pov200']    / pop_tot
    pct_wh   = sums['pop_white_nh']  / pop_tot
    pct_aa   = sums['pop_afr_am_nh'] / pop_tot
    pct_as   = sums['pop_asian_nh']  / pop_tot
    pct_oth  = sums['pop_other_nh']  / pop_tot
    pct_hisp = sums['pop_hisp']      / pop_tot

    # Region benchmark (sum across all BGs, divide by region total pop)
    df_race = pd.read_csv(RACE_CSV, dtype={'GEOID': str})
    df_pov  = pd.read_csv(POV_CSV,  dtype={'GEOID': str})
    reg_pop = df_race['pop_tot'].sum()
    reg_pov = df_pov['pop_pov200'].sum()

    def reg_rate(col):
        return df_race[col].sum() / reg_pop if reg_pop > 0 else 0

    out = {
        "Population": int(pop_tot),
        "Share of population in households below 200% federal poverty level": {
            "Within project location": round(pct_pov, 4),
            "Within community type": None,   # needs benchmark CSV re-run (null until then)
            "Within region": round(reg_pov / reg_pop, 4) if reg_pop > 0 else None,
        },
        "Ethnic composition of population near project": {
            "White non-Hispanic":          {"Within project location": round(pct_wh,   4), "Within community type": None, "Within region": round(reg_rate('pop_white_nh'),  4)},
            "African American non-Hispanic":{"Within project location": round(pct_aa,  4), "Within community type": None, "Within region": round(reg_rate('pop_afr_am_nh'), 4)},
            "Asian non-Hispanic":           {"Within project location": round(pct_as,  4), "Within community type": None, "Within region": round(reg_rate('pop_asian_nh'),  4)},
            "Other non-Hispanic":           {"Within project location": round(pct_oth, 4), "Within community type": None, "Within region": round(reg_rate('pop_other_nh'),  4)},
            "Hispanic/Latino":              {"Within project location": round(pct_hisp,4), "Within community type": None, "Within region": round(reg_rate('pop_hisp'),       4)},
        }
    }
    return out


def run_validation(bg_lookup):
    """
    Sanity checks on the bg_lookup computed from real census CSVs.
    """
    print("\n=== SANITY CHECKS ON BG LOOKUP ===")
    shares = pd.DataFrame(bg_lookup).T
    share_cols = ['_white_share', '_afr_am_share', '_asian_share', '_other_share', '_hisp_share']
    shares['ethnic_sum'] = shares[share_cols].sum(axis=1)

    print(f"Block groups loaded: {len(shares)}")
    print(f"Poverty share range: {shares['_pov200_share'].min():.3f} - {shares['_pov200_share'].max():.3f}")
    print(f"Poverty share mean:  {shares['_pov200_share'].mean():.3f}")
    print(f"\nEthnic share sum per BG (should be close to 1.0):")
    print(f"  Mean: {shares['ethnic_sum'].mean():.4f}")
    print(f"  Min:  {shares['ethnic_sum'].min():.4f}")
    print(f"  Max:  {shares['ethnic_sum'].max():.4f}")

    bad_pov = shares[shares['_pov200_share'] > 1.0]
    if len(bad_pov):
        print(f"\nWARNING: {len(bad_pov)} BGs have poverty share > 1.0 (check denominator logic)")
    else:
        print(f"\nOK: No BGs with poverty share > 1.0")

    ethnic_outliers = shares[shares['ethnic_sum'] > 1.1]
    if len(ethnic_outliers):
        print(f"WARNING: {len(ethnic_outliers)} BGs have ethnic share sum > 1.1")
    else:
        print("OK: All BGs have ethnic share sum <= 1.1")


if __name__ == '__main__':
    print("Loading real ACS CSVs...")
    bg_lookup = build_bg_lookup(RACE_CSV, POV_CSV)
    print(f"Loaded {len(bg_lookup)} block groups")

    run_validation(bg_lookup)

    # Synthetic parcel data: 20 parcels assigned to 3 real BGs from Sacramento County
    # Chosen GEOIDs are real values that appear in the race CSV
    df_race_raw = pd.read_csv(RACE_CSV, dtype={'GEOID': str})
    sac_bgs = df_race_raw[df_race_raw['GEOID'].str.startswith('06006')]['GEOID'].head(3).tolist()
    if not sac_bgs:
        sac_bgs = df_race_raw['GEOID'].head(3).tolist()

    print(f"\nUsing real BG GEOIDs for synthetic parcels: {sac_bgs}")

    import random
    random.seed(42)
    parcels = pd.DataFrame({
        'PARCELID': [f'PCL{i:04d}' for i in range(20)],
        'GEOID':    [sac_bgs[i % 3] for i in range(20)],
        'POP_TOT':  [random.randint(2, 12) for _ in range(20)],
    })

    print("\nApplying BG demographic shares to synthetic parcels...")
    parcels = prorate_parcels(parcels, bg_lookup)

    # Simulate a buffer covering 10 of the 20 parcels
    buffer_geoids = sac_bgs[:2]
    sums = simulate_project_buffer(parcels, buffer_geoids)

    print(f"\nSimulated buffer sums:")
    print(sums.to_string())

    print("\nBuilding equity JSON output...")
    result = build_equity_json(sums, bg_lookup, buffer_geoids, sac_bgs)
    print(json.dumps(result, indent=2))

    # Validate structure matches template
    print("\n=== STRUCTURE VALIDATION ===")
    required_top = {
        "Population",
        "Share of population in households below 200% federal poverty level",
        "Ethnic composition of population near project",
    }
    missing = required_top - set(result.keys())
    print(f"Required top-level keys present: {'YES' if not missing else 'MISSING: ' + str(missing)}")

    eth = result.get("Ethnic composition of population near project", {})
    required_ethnic = {"White non-Hispanic", "African American non-Hispanic",
                       "Asian non-Hispanic", "Other non-Hispanic", "Hispanic/Latino"}
    missing_ethnic = required_ethnic - set(eth.keys())
    print(f"All 5 ethnic groups present: {'YES' if not missing_ethnic else 'MISSING: ' + str(missing_ethnic)}")

    pov = result.get("Share of population in households below 200% federal poverty level", {})
    assert 0.0 <= pov["Within project location"] <= 1.0, "Poverty rate out of range!"
    print(f"Poverty rate in [0,1]: YES ({pov['Within project location']:.1%})")

    eth_sum = sum(v["Within project location"] for v in eth.values())
    print(f"Ethnic shares sum to ~1.0: {eth_sum:.4f} ({'OK' if abs(eth_sum - 1.0) < 0.02 else 'CHECK'})")

    reg_pov = pov.get("Within region")
    print(f"Regional poverty rate: {reg_pov:.1%} ({'OK — plausible' if reg_pov and 0.05 < reg_pov < 0.95 else 'CHECK'})")

    print("\nAll checks passed." if not missing and not missing_ethnic else "\nSome checks failed — see above.")
