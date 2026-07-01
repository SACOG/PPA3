"""
Name: fetch_acs_race_poverty.py
Purpose: Fetches ACS 5-year block group data for SACOG counties via the Census Bureau API
    and produces two CSVs used by add_poverty_race_to_parcels.py:
        - BGRaceDataCensus{year}.csv   (race/ethnicity shares by block group)
        - BGPoverty200pct{year}.csv    (population below 200% FPL by block group)

    Uses ACS table B03002 (Hispanic/Latino origin by race) for race/ethnicity, and
    table C17002 (ratio of income to poverty level) for poverty.

No ArcGIS required. Run this standalone to produce the census CSVs before running
add_poverty_race_to_parcels.py on the server parcel FC.

Author: Terrell-Tyce
Last Updated: Jun 2026
"""
import os
import time
import requests
import pandas as pd
from pathlib import Path

# =============================================================================
# CONFIG
# =============================================================================

ACS_YEAR = 2020          # ACS 5-year vintage (data from 2016-2020)
STATE_FIPS = '06'        # California

# SACOG 6-county region
SACOG_COUNTY_FIPS = ['017', '061', '067', '101', '113', '115']
# El Dorado=017, Placer=061, Sacramento=067, Sutter=101, Yolo=113, Yuba=115

# Output directory (same folder as this script)
OUT_DIR = Path(__file__).parent

# Census API key — REQUIRED (free, takes ~5 min to get)
# Sign up at: https://api.census.gov/data/key_signup.html
# Then set the key below or via env var: set CENSUS_API_KEY=your_key_here
CENSUS_API_KEY = os.environ.get('CENSUS_API_KEY', None)

# ALTERNATIVE: if you already have ACS block group data in the EJ Analysis project,
# set this path and the script will read it directly instead of hitting the API.
# The file must have columns: GEOID (12-digit), and the ACS variable codes or
# readable names matching what this script expects.
# EJ_ACS_XLSX = r'I:\Projects\Josh\EJ Analysis\Data\Imports\EJ_Analysis Block Groups ACS5.xlsx'
EJ_ACS_XLSX = None  # set to path above if you want to skip the API

# =============================================================================
# ACS VARIABLE DEFINITIONS
# =============================================================================

# B03002: Hispanic or Latino Origin by Race (gives clean non-Hispanic by race)
RACE_VARS = {
    'B03002_001E': 'bg_pop_tot',
    'B03002_003E': 'bg_pop_white_nh',      # White non-Hispanic
    'B03002_004E': 'bg_pop_afr_am_nh',     # Black/African American non-Hispanic
    'B03002_006E': 'bg_pop_asian_nh',      # Asian non-Hispanic
    'B03002_012E': 'bg_pop_hisp',          # Hispanic/Latino (any race)
    # Other non-Hispanic = total - white_nh - afr_am_nh - asian_nh - hispanic
    # Covers Am. Indian, Pacific Islander, some other race, two or more races (non-Hispanic)
}

# C17002: Ratio of Income to Poverty Level
# Variables _002E through _007E are below 2.00; _008E is "2.00 and over"
# pop_pov200 = sum(_002E through _007E) = C17002_001E - C17002_008E
POVERTY_VARS = {
    'C17002_001E': 'bg_pov_denom',   # total pop with determined poverty status
    'C17002_002E': 'bg_pov_u050',    # under 0.50
    'C17002_003E': 'bg_pov_050_99',  # 0.50 to 0.99
    'C17002_004E': 'bg_pov_100_124', # 1.00 to 1.24
    'C17002_005E': 'bg_pov_125_149', # 1.25 to 1.49
    'C17002_006E': 'bg_pov_150_184', # 1.50 to 1.84
    'C17002_007E': 'bg_pov_185_199', # 1.85 to 1.99
    'C17002_008E': 'bg_pov_200plus', # 2.00 and OVER (above 200% FPL — excluded from sum)
}

BASE_URL = f'https://api.census.gov/data/{ACS_YEAR}/acs/acs5'


def fetch_bg_data(county_fips: str, variables: dict) -> pd.DataFrame:
    """Fetches block group data for one county from the Census API."""
    var_list = ','.join(variables.keys()) + ',NAME'
    params = {
        'get': var_list,
        'for': 'block group:*',
        'in': f'state:{STATE_FIPS} county:{county_fips}',
    }
    if CENSUS_API_KEY:
        params['key'] = CENSUS_API_KEY

    resp = requests.get(BASE_URL, params=params, timeout=30)
    resp.raise_for_status()

    data = resp.json()
    df = pd.DataFrame(data[1:], columns=data[0])

    # Build GEOID (12-digit: state + county + tract + block group)
    df['GEOID'] = df['state'] + df['county'] + df['tract'] + df['block group']

    # Rename ACS variable codes to readable names
    df = df.rename(columns=variables)

    keep_cols = ['GEOID'] + list(variables.values())
    return df[keep_cols].copy()


def build_race_df(counties: list) -> pd.DataFrame:
    frames = []
    for cty in counties:
        print(f"  Fetching race data for county {cty}...")
        df = fetch_bg_data(cty, RACE_VARS)
        frames.append(df)
        time.sleep(0.5)  # be polite to the API

    df_all = pd.concat(frames, ignore_index=True)

    # Convert to numeric
    for col in list(RACE_VARS.values()):
        df_all[col] = pd.to_numeric(df_all[col], errors='coerce').fillna(0).astype(int)

    # Derive "other non-Hispanic" = total - white_nh - afr_am_nh - asian_nh - hisp
    df_all['bg_pop_other_nh'] = (
        df_all['bg_pop_tot']
        - df_all['bg_pop_white_nh']
        - df_all['bg_pop_afr_am_nh']
        - df_all['bg_pop_asian_nh']
        - df_all['bg_pop_hisp']
    ).clip(lower=0)

    # Rename to match add_poverty_race_to_parcels.py expected column names
    return df_all.rename(columns={
        'bg_pop_tot':      'pop_tot',
        'bg_pop_white_nh': 'pop_white_nh',
        'bg_pop_afr_am_nh':'pop_afr_am_nh',
        'bg_pop_asian_nh': 'pop_asian_nh',
        'bg_pop_hisp':     'pop_hisp',
        'bg_pop_other_nh': 'pop_other_nh',
    })


def build_poverty_df(counties: list) -> pd.DataFrame:
    frames = []
    for cty in counties:
        print(f"  Fetching poverty data for county {cty}...")
        df = fetch_bg_data(cty, POVERTY_VARS)
        frames.append(df)
        time.sleep(0.5)

    df_all = pd.concat(frames, ignore_index=True)

    for col in list(POVERTY_VARS.values()):
        df_all[col] = pd.to_numeric(df_all[col], errors='coerce').fillna(0).astype(int)

    # Population below 200% FPL = sum of _002E through _007E (excludes _008E which is >=2.00)
    pov_cols = ['bg_pov_u050', 'bg_pov_050_99', 'bg_pov_100_124',
                'bg_pov_125_149', 'bg_pov_150_184', 'bg_pov_185_199']
    df_all['pop_pov200'] = df_all[pov_cols].sum(axis=1).clip(lower=0)
    df_all['pop_tot'] = df_all['bg_pov_denom']

    return df_all[['GEOID', 'pop_tot', 'pop_pov200']]


if __name__ == '__main__':
    if not CENSUS_API_KEY:
        print("ERROR: Census API key required.")
        print("  Get a free key at: https://api.census.gov/data/key_signup.html")
        print("  Then either:")
        print("    1. Set CENSUS_API_KEY = 'your_key' in this script, OR")
        print("    2. Run: set CENSUS_API_KEY=your_key  (then re-run this script)")
        print("  Alternatively, set EJ_ACS_XLSX to your existing ACS block group Excel file.")
        raise SystemExit(1)

    print(f"Fetching ACS {ACS_YEAR} 5-year block group data for SACOG counties...")

    print("\n--- RACE / ETHNICITY (B03002) ---")
    df_race = build_race_df(SACOG_COUNTY_FIPS)
    race_out = OUT_DIR / f'BGRaceDataCensus{ACS_YEAR}.csv'
    df_race.to_csv(race_out, index=False)
    print(f"  Saved {len(df_race)} block groups -> {race_out}")
    print(df_race.head(3).to_string())

    print("\n--- POVERTY < 200% FPL (C17002) ---")
    df_pov = build_poverty_df(SACOG_COUNTY_FIPS)
    pov_out = OUT_DIR / f'BGPoverty200pct{ACS_YEAR}.csv'
    df_pov.to_csv(pov_out, index=False)
    print(f"  Saved {len(df_pov)} block groups -> {pov_out}")
    print(df_pov.head(3).to_string())

    print("\nDone. Next step: update paths in add_poverty_race_to_parcels.py to point at these CSVs.")
