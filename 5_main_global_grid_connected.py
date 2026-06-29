"""
This script runs parallel ammonia-system optimizations for all countries
with relevant nitrogen demand.

It first scans the global xarray dataset and selects one representative
grid cell per unique ISO2 code, provided the cell has non-zero nitrogen
demand and valid solar and wind capacity factors. For each country-scenario
combination, it then prepares country-specific techno-economic inputs,
electricity prices, and grid GHG intensities, and runs the optimization in
parallel.

The resulting techno-economic outputs are collected into a single dataframe
and saved for further analysis.
"""

import pandas as pd 
import json
import concurrent.futures
import pickle
import bw2data
import sys
import time
import numpy as np

# import own Python files, vars, mappings, and functions
from config import (NAME_REF_DB, COST_DATA, OUTPUT_FILE_XARRAY, 
                    PROJECT_NAME, FILE_PATH_GLOBAL_RESULTS_GRID)

import energy_data_processor as ep
import opt_ammonia_functions as opt

# Set BW project
bw2data.projects.set_current(PROJECT_NAME)

COST_DICT = COST_DATA[NAME_REF_DB].to_dict() # techno-economic data

# Load the pickle with pandas
with open(OUTPUT_FILE_XARRAY, "rb") as f:
    DS = pickle.load(f)

# Read GHG info for system components
with open("input_data/dict_ghg_impacts.txt", 'r') as file:
    DICT_GHG_IMPACTS = json.load(file)

# ---- user-defined parameters ----
scenarios = {
    "grid_connected": {"autonomous_elect": False, "no_renewables": True}}

def run_single_case(args, cost_dict=COST_DICT, dict_ghg_impacts=DICT_GHG_IMPACTS):
    """Run optimization cases in parallel."""
    # Unpack args (safer for ProcessPoolExecutor)
    country, iso2, __, __, scenario_name, kwargs = args

    cost_dict = cost_dict.copy()
    dict_ghg_impacts = dict_ghg_impacts.copy()

    # get optimzation limits, with proper bounds
    dict_limits = ep.get_max_caps_regions()

    # get country-specific WACC/dr
    cost_dict['dr'] = ep.get_latest_avg_wacc(iso2)

    # get country-specific retail prices
    power_prices = ep.get_elect_prices(iso2)

    # And fill:
    df_data = pd.DataFrame(data={'pv_MW_array': 0, 
                                        'wind_MW_array_on': 0,
                                         "grid_abs_price": power_prices,
                                        "rev_inj": 0, 
                                        }, index=pd.date_range('1/1/{} 00:00'.format(2023), 
                                                               periods=8760, freq='h'))

    # Fill also the data on the GHG impacts factors.
    df_data['ghg_impact'] = ep.get_activity_env_elect_from_dict(iso2,db=NAME_REF_DB)
    df_data['ghg_impact_cons'] = 0 # no credit for inserted GHGs considered

    # Run optimization
    totals_cost_min, __, __ = opt.opt_amm_electric_hb(
        df_data, 1, 0, cost_dict, dict_ghg_impacts, dict_limits,
        export_alias=scenario_name,
        LOC_ELECT=iso2, consider_down_times=False, **kwargs
    )

    # Add identifiers
    totals_cost_min['country'] = country
    totals_cost_min['iso2'] = iso2
    totals_cost_min['scenario'] = scenario_name

    return totals_cost_min

# --- replace the job-building loop in main() with this unique-iso2 logic ---
def main():
    start_time = time.time()  # record the start time

    # collect a single representative cell per unique iso2
    iso2_representative = {}  # iso2 -> dict(name, lat, lon, demand_tonnes)
    for i_lat in range(len(DS.lat)):
        for i_lon in range(len(DS.lon)):
            cell = DS.isel(lat=i_lat, lon=i_lon)

            # same filtering as before
            if ( (cell.synthetic_nitrogen_tonnes.item()>0) and
                (not np.any(np.isnan(cell.cf_solar))) and
                (not np.any(np.isnan(cell.cf_wind)))):
                
                iso2 = cell.ISO_A2.item()

                # --- skip invalid ISO codes ---
                # skip real NaN
                if iso2 is None or (isinstance(iso2, float) and np.isnan(iso2)):
                    continue
                # skip 'nan' strings or placeholder codes
                if str(iso2).strip().upper() in ["NAN", "-99", ""]:
                    continue
                # --------------------------------
                
                # if we haven't seen this iso2 yet, store this cell as representative
                if iso2 not in iso2_representative:
                    iso2_representative[iso2] = {
                        "name": cell.NAME_EN.item(),
                        "lat": cell.lat.item(),
                        "lon": cell.lon.item(),
                        "demand_tonnes": cell.synthetic_nitrogen_tonnes.item(),
                    }

    # Build jobs only from unique iso2 representatives
    jobs = []
    for iso2, info in iso2_representative.items():
        for scenario_name, kwargs in scenarios.items():
            # Append the demand_tonnes so we can store it reliably later
            jobs.append((info["name"], iso2, info["lat"], info["lon"], scenario_name, kwargs))

    print(f"Prepared {len(jobs)} jobs (one representative per unique ISO2; unique ISO2 count: {len(iso2_representative)}).")
    total_jobs = len(jobs)

    # --- the rest of your parallel execution can remain the same ---
    results = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=9) as executor:
        for i, res in enumerate(executor.map(run_single_case, jobs), 1):
            elapsed_time = time.time() - start_time  # seconds
            elapsed_minutes = elapsed_time / 60
            avg_time_per_job = elapsed_time / i
            remaining_minutes = avg_time_per_job * (total_jobs - i) / 60

            sys.stdout.write(
                f"\rFinished {i}/{total_jobs} | Elapsed: {elapsed_minutes:.0f} min | "
                f"Remaining: {remaining_minutes:.0f} min, {remaining_minutes/60:.1f} hours"
            )
            sys.stdout.flush()

            # res already contains synthetic_nitrogen_tonnes (set inside run_single_case)
            results.append(res)

    totals_cost_all = pd.concat(results, ignore_index=True).set_index(['country', 'iso2', 'scenario'])
    totals_cost_all.to_pickle(FILE_PATH_GLOBAL_RESULTS_GRID)

    return totals_cost_all

if __name__ == "__main__":
    totals_cost_all = main()
    print("Job done, results shape:", totals_cost_all.shape)