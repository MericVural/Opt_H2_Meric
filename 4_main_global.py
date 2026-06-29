# In this Python script, we optimize all energy system lay-outs over the
# world where there is nitrogen demand (N_DEMAND_THRESHOLD >= x)
# considering various configurations.
# NOTE: we can run on our laptop/desktop but this would take multiple days - week.
# We make use of HPC from ETH instead (Euler)

import pandas as pd 
import json, traceback
import concurrent.futures
import pickle
import sys
import time
import numpy as np

# import own Python files, vars, mappings, and functions
from config import (NAME_REF_DB, COST_DATA, OUTPUT_FILE_XARRAY, TEMP_FILE,
                    N_DEMAND_THRESHOLD, FILE_PATH_GLOBAL_RESULTS)

import energy_data_processor as ep
import opt_ammonia_functions as opt

COST_DICT = COST_DATA[NAME_REF_DB].to_dict() # techno-economic data

# Load the pickle with pandas
with open(OUTPUT_FILE_XARRAY, "rb") as f:
    DS = pickle.load(f)

# Read GHG info for system components
with open("input_data/dict_ghg_impacts.txt", 'r') as file:
    DICT_GHG_IMPACTS = json.load(file)

SAVE_INTERVAL = 500

# ---- user-defined parameters ----
scenarios = {
    "hybrid": {"autonomous_elect": False, "no_renewables": False},
    "off_grid": {"autonomous_elect": True, "no_renewables": False},
}

def run_single_case(args, cost_dict=COST_DICT, dict_ghg_impacts=DICT_GHG_IMPACTS):
    """Run optimization cases in parallel."""
    # Unpack args (safer for ProcessPoolExecutor)
    country, iso2, lat, lon, scenario_name, nitrogen_demand, kwargs = args

    cost_dict = cost_dict.copy()
    dict_ghg_impacts = dict_ghg_impacts.copy()

    # get optimzation limits, with proper bounds
    dict_limits = ep.get_max_caps_regions()

    # get country-specific WACC/dr
    cost_dict['dr'] = ep.get_latest_avg_wacc(iso2)

    # get country-specific retail prices
    power_prices = ep.get_elect_prices(iso2)

    # Get hourly cfs for solar and wind:
    cell = DS.sel(lat=lat, lon=lon, method="nearest")

    # And fill:
    df_data = pd.DataFrame(data={'pv_MW_array': cell.cf_solar, 
                                        'wind_MW_array_on': cell.cf_wind,
                                         "grid_abs_price": power_prices,
                                        "rev_inj": 0, 
                                        }, index=pd.date_range('1/1/{} 00:00'.format(2023), 
                                                               periods=8760, freq='h'))

    # Fill also the data on the GHG impacts factors.
    df_data['ghg_impact'] = ep.get_activity_env_elect_from_dict(iso2,db=NAME_REF_DB)
    df_data['ghg_impact_cons'] = 0 # no credit for inserted GHGs considered

    # Run optimization
    try:
        totals_cost_min, __, __ = opt.opt_amm_electric_hb(
            df_data, 1, 0, cost_dict, dict_ghg_impacts, dict_limits,
            export_alias=scenario_name,
            LOC_ELECT=iso2, consider_down_times=False, **kwargs
        )

        # Add identifiers
        totals_cost_min['country'] = country
        totals_cost_min['iso2'] = iso2
        totals_cost_min['scenario'] = scenario_name
        totals_cost_min['lat'] = lat
        totals_cost_min['lon'] = lon
        totals_cost_min['synthetic_nitrogen_tonnes'] = nitrogen_demand

    # in case of an error, save the error and log
    except Exception as e:
        error_info = {
            "case": [iso2, lat, lon, scenario_name],
            "error": str(e),
            "traceback": traceback.format_exc()
        }
        with open("failed_cases.log", "a") as f:
            f.write(json.dumps(error_info) + "\n")

        return ([iso2, lat, lon, scenario_name], None)

    return ([iso2, lat, lon, scenario_name], totals_cost_min)

def main():
    start_time = time.time()  # record the start time
    jobs = []

    for i_lat in range(len(DS.lat)):
        for i_lon in range(len(DS.lon)):
            # read static attributes for this cell
            cell = DS.isel(lat=i_lat, lon=i_lon)
            
            # check both conditions
            if ((cell.synthetic_nitrogen_tonnes.item() > N_DEMAND_THRESHOLD) and 
                (not np.any(np.isnan(cell.cf_solar))) and (not np.any(np.isnan(cell.cf_wind))) ):
                name = cell.NAME_EN.item()
                iso2 = cell.ISO_A2.item()
                lat_val = cell.lat.item()
                lon_val = cell.lon.item()
                nitrogen_demand = cell.synthetic_nitrogen_tonnes.item()
                
                for scenario_name, kwargs in scenarios.items():
                    jobs.append((name, iso2, lat_val, lon_val, scenario_name, nitrogen_demand, kwargs))

    print(f"Running {len(jobs)} optimizations...")
    total_jobs = len(jobs)

    # --- parallel execution ---
    with concurrent.futures.ProcessPoolExecutor(max_workers=10) as executor:
        results = []
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

            # check if succesfull and otherwise log
            case_data, df = res
            if df is None:
                sys.stdout.write(f"Case failed: {case_data}")
                sys.stdout.flush()
            else:
                results.append(df)

            # --- periodic save ---
            if i % SAVE_INTERVAL == 0 or i == len(jobs):
                try:
                    temp_df = pd.concat(results, ignore_index=True).set_index(
                        ['country', 'iso2', 'scenario', 'lat', 'lon']
                    )
                    temp_df.to_pickle(TEMP_FILE)
                    print(f"\n Saved intermediate results at iteration {i}")
                except Exception as e:
                    print(f"\n Warning: could not save at iteration {i}: {e}")

    totals_cost_all = pd.concat(results, ignore_index=True).set_index(['country', 'iso2', 'scenario', 'lat', 'lon'])
    totals_cost_all.to_pickle(FILE_PATH_GLOBAL_RESULTS)

    return totals_cost_all

if __name__ == "__main__":
    totals_cost_all = main()
    print("Job done, results shape:", totals_cost_all.shape)