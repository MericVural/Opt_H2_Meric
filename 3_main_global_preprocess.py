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

import concurrent.futures
import sys
import time
import pickle

# import own Python files, vars, mappings, and functions
from config import (OUTPUT_FILE_XARRAY, OUTPUT_FILE_XARRAY_INIT,N_DEMAND_THRESHOLD)
import calculate_renewable_yield as crp

# Load the pickle with pandas
with open(OUTPUT_FILE_XARRAY_INIT, "rb") as f:
    ds = pickle.load(f)

def process_cell(lat_val, lon_val):
    """Process one lat/lon cell."""
    cell = ds.sel(lat=lat_val, lon=lon_val, method="nearest")
    if (cell.synthetic_nitrogen_tonnes > N_DEMAND_THRESHOLD):
        data_processor = crp.RenewableEnergyProcessor(lat_val, lon_val)
        cf_pv, cf_wind = data_processor.process_data()
        return lat_val, lon_val, cf_pv, cf_wind
    return None

def process_cell_wrapper(args):
    lat_val, lon_val = args
    try:
        return process_cell(lat_val, lon_val)
    except Exception as e:
        print(f"Skipping cell {lat_val, lon_val} due to error: {e}")
        return None

def main():
    start_time = time.time()
    
    # Prepare jobs
    jobs = [(lat, lon) for lat in ds.lat.values for lon in ds.lon.values ]
    results = []

    # Parallel processing
    with concurrent.futures.ProcessPoolExecutor(max_workers=9) as executor:
        for i, res in enumerate(executor.map(process_cell_wrapper, jobs), 1):
            elapsed_time = time.time() - start_time
            elapsed_minutes = elapsed_time / 60
            avg_time_per_job = elapsed_time / i
            remaining_minutes = avg_time_per_job * (len(jobs) - i) / 60

            sys.stdout.write(
                f"\rProcessed {i}/{len(jobs)} | Elapsed: {elapsed_minutes:.0f} min | "
                f"Remaining: {remaining_minutes:.0f} min, {remaining_minutes/60:.1f} hours"
            )
            sys.stdout.flush()

            if res is not None:
                results.append(res)

    print("\nAll cells processed, updating dataset...")

    # Update the dataset once
    for lat_val, lon_val, cf_pv, cf_wind in results:
        ds.cf_solar.loc[dict(lat=lat_val, lon=lon_val)] = cf_pv
        ds.cf_wind.loc[dict(lat=lat_val, lon=lon_val)] = cf_wind

    # Save (serialize) the xarray dataset
    with open(OUTPUT_FILE_XARRAY, "wb") as f:
        pickle.dump(ds, f)

    print(f"Dataset saved to {OUTPUT_FILE_XARRAY}")

if __name__ == "__main__":
    main()