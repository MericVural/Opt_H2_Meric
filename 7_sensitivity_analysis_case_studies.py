"""
This script runs a parallel sensitivity analysis for decentralized ammonia
system layouts across selected locations and configurations.

For each location-scenario combination, it perturbs one input parameter at a
time (e.g. electricity price, discount rate, capex, efficiency, or renewable
capacity factor) by a fixed percentage and reruns the optimization. The script
then collects the resulting techno-economic outputs, labels them by country,
scenario, sensitivity parameter, and perturbation factor, and saves the full
results table for subsequent analysis.
"""

import pandas as pd 
import json
import concurrent.futures
import bw2data
import sys
import time

# import own Python files, vars, mappings, and functions
from config import (NAME_REF_DB, COST_DATA, PROJECT_NAME,
                   LOCATIONS_SENS, FILE_PATH_SENS_ANALYSIS)

import calculate_renewable_yield as cry
import opt_ammonia_functions as opt
import energy_data_processor as ep

# Set BW project
bw2data.projects.set_current(PROJECT_NAME)

COST_DICT = COST_DATA[NAME_REF_DB].to_dict() # techno-economic data

# Read GHG info for system components
with open("input_data/dict_ghg_impacts.txt", 'r') as file:
    DICT_GHG_IMPACTS = json.load(file)

# ---- user-defined parameters ----
scenarios = {
    "grid_connected": {"autonomous_elect": False, "no_renewables": True},
    "hybrid": {"autonomous_elect": False, "no_renewables": False},
    "off_grid": {"autonomous_elect": True, "no_renewables": False},
}

search_mapping_for_sensitivity = {
                'power_prices': "Electricity grid price",
                "dr": "Discount rate",
                "hb_capex": "Capex HB-unit",
                "pv_capex": "Capex solar PV",
                "bat_en_capex": "Capex battery (energy)",
                "wind_on_capex": "Capex onshore wind",
                "electr_eff": "Electrolyzer efficiency",
                "electr_capex": "Electrolyzer capex",
                'cf_wind': "Capacity factor wind",
                'cf_pv': "Capacity factor solar",
                }

factors_run = [0.2, -0.2]

def run_single_case(args, cost_dict=COST_DICT, dict_ghg_impacts=DICT_GHG_IMPACTS):

    """Run one optimization case in parallel."""
    # Unpack args (safer for ProcessPoolExecutor)
    country, iso2, lat, lon, scenario_name, sens_factor, factor_change, kwargs = args

    factor = 1 + factor_change

    cost_dict = cost_dict.copy()
    dict_ghg_impacts = dict_ghg_impacts.copy()

    # get optimzation limits, with proper bounds
    dict_limits = ep.get_max_caps_regions()

    # get country-specific WACC/dr
    cost_dict['dr'] = ep.get_latest_avg_wacc(iso2) * factor if sens_factor=='dr' else ep.get_latest_avg_wacc(iso2)

    # get country-specific retail prices
    power_prices = ep.get_elect_prices(iso2) * factor if sens_factor=='power_prices' else ep.get_elect_prices(iso2)

    data_processor = cry.RenewableEnergyProcessor(lat, lon)
    cf_pv, cf_wind = data_processor.process_data()

    # Modify cost dictionary based on the sensitivity factor dynamically
    if sens_factor in ['cf_pv', 'cf_wind']:
        if sens_factor == 'cf_pv':
            cf_pv *= factor
        elif sens_factor == 'cf_wind':
            cf_wind *= factor
    else:
        for k in cost_dict:
            if sens_factor == 'om':
                if ('_om' in str(k)):
                    cost_dict[k] *= factor
            elif sens_factor == k:
                cost_dict[k] *= factor

    # And fill:
    df_data = pd.DataFrame(data={'pv_MW_array': cf_pv, 
                                        'wind_MW_array_on': cf_wind,
                                         "grid_abs_price": power_prices,
                                        "rev_inj": 0, 
                                        }, index=pd.date_range('1/1/{} 00:00'.format(2023), periods=8760, freq='h'))

    # Get grid GHG intensity
    df_data['ghg_impact'] = ep.get_activity_env_elect_from_dict(iso2,db=NAME_REF_DB)
    df_data['ghg_impact_cons'] = 0

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
    totals_cost_min['sensitivity'] = sens_factor
    totals_cost_min['factor'] = factor

    return totals_cost_min

def main():
    start_time = time.time()  # record the start time
    # ---- build all jobs ----
    jobs = [
        (country, iso2, lat, lon, scenario_name, sens_factor, factor_change, kwargs)
        for country, iso2, lat, lon in LOCATIONS_SENS
        for scenario_name, kwargs in scenarios.items()
        for sens_factor in search_mapping_for_sensitivity.keys()
        for factor_change in factors_run
    ]

    print(f"Running {len(jobs)} total cases...")
    total_jobs = len(jobs)

    with concurrent.futures.ProcessPoolExecutor(max_workers=8) as executor:
        results = []

        for i, res in enumerate(executor.map(run_single_case, jobs), 1):
            elapsed_time = time.time() - start_time  # seconds
            elapsed_minutes = elapsed_time / 60
            avg_time_per_job = elapsed_time / i
            remaining_minutes = avg_time_per_job * (total_jobs - i) / 60

            sys.stdout.write(
                f"\rFinished {i}/{total_jobs} | Elapsed: {elapsed_minutes:.2f} min | "
                f"Remaining: {remaining_minutes:.2f} min"
            )
            sys.stdout.flush()

            # prepare result df, before adding
            results.append(res)

    totals_cost_all = pd.concat(results, ignore_index=True).set_index(
        ['country', 'iso2', 'scenario', 'sensitivity', 'factor'])
    
    totals_cost_all.to_pickle(FILE_PATH_SENS_ANALYSIS)

    return totals_cost_all

if __name__ == "__main__":
    totals_cost_all = main()
    print("Job done, results shape:", totals_cost_all.shape)