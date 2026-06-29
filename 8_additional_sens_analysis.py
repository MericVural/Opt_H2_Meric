"""
Parallel case-study sensitivity workflow for decentralized electric ammonia systems.

Sensitivity design
------------------
This script runs one-at-a-time sensitivity analyses around a shared baseline.

Baseline:
- hb_pl_min = 0.3
- factor_lower_night = 0.2
- t_day = 20
- scale_exp = 1

Sensitivity families:
1. hb_min_load:
   vary hb_pl_min from 0.0 to 0.5
   keep factor_lower_night = 0.2, t_day = 20, scale_exp = 1

2. tariff:
   vary factor_lower_night from 0.0 to 0.5
   keep hb_pl_min = 0.3, t_day = 20, scale_exp = 1

3. scale:
   vary t_day from 0 to 100
   keep hb_pl_min = 0.3, factor_lower_night = 0.2
   and apply CAPEX scaling with scale_exp = 1

4. scale_exp:
   vary scale_exp from 0.6 to 1
   keep hb_pl_min = 0.3, factor_lower_night = 0.2
   and evaluate at t_day = 100

No Brightway foreground database writing is performed in this script.
Only optimization outputs are collected and saved.

Important behavior
------------------
Hourly operation outputs are saved ONLY for the BASELINE cases.
Sensitivity cases do not save hourly operation outputs.
"""

import json
import time
import pickle
import concurrent.futures

import pandas as pd

# import own Python files, vars, mappings, and functions
from config import (
    NAME_REF_DB,
    COST_DATA,
    NAME_FUTURE_DB,
    FUTURE_POWER_PRICES,
    LOCATIONS_SENS_PLUS,
    FILE_PATH_CASE_STUDIES,
)
import calculate_renewable_yield as cry
import opt_ammonia_functions as opt
import energy_data_processor as ep

# -----------------------------
# Global settings
# -----------------------------
GEN_RESULTS = True

COST_DICT = COST_DATA[NAME_REF_DB].to_dict()
COST_DICT_FUTURE = COST_DATA[NAME_FUTURE_DB].to_dict()

ALL_DBS = [NAME_REF_DB]  # or [NAME_REF_DB, NAME_FUTURE_DB]

SCENARIOS = {
    "grid_connected": {"autonomous_elect": False, "no_renewables": True},
    "hybrid": {"autonomous_elect": False, "no_renewables": False},
    "off_grid": {"autonomous_elect": True, "no_renewables": False},
}

# -----------------------------
# Sensitivity settings
# -----------------------------
BASELINE_HB_PL_MIN = 0.3
BASELINE_FACTOR_LOWER_NIGHT = 0.2
BASELINE_T_DAY = 20
BASELINE_SCALE_EXP = 1

HB_MIN_LOAD_VALUES = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5]
LOWER_NIGHT_VALUES = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5]
T_DAY_VALUES = [20, 40, 60, 80, 100]

# Economies-of-scale CAPEX exponent sensitivity
SCALE_EXP_VALUES = [0.6, 0.7, 0.8, 0.9, 1]
SCALE_EXP_TEST_T_DAY = 100  # representative larger plant size

# Save hourly operation output only for baseline cases
SAVE_OPERATION_OUTPUT = True
SAVE_OPERATION_FOR_LOCATIONS = None
# Example:
# SAVE_OPERATION_FOR_LOCATIONS = {
#     "Netherlands (Schagen)",
#     "Spain (J. de la Frontera)",
#     "Australia (Victoria)",
# }

# -----------------------------
# Load input data
# -----------------------------
with open("input_data/dict_ghg_impacts.txt", "r") as file:
    DICT_GHG_IMPACTS = json.load(file)

with open("input_data/dict_ghg_impacts_future.txt", "r") as file:
    DICT_GHG_IMPACTS_FUTURE = json.load(file)


# -----------------------------
# Helper functions
# -----------------------------
def get_capex_scale_factor(
    t_day,
    baseline_t_day=BASELINE_T_DAY,
    scale_exp=BASELINE_SCALE_EXP,
):
    """
    Compute scaling factor for specific HB CAPEX terms.

    Applied as:
        hb_capex_scaled = hb_capex_base * (t_day / baseline_t_day) ** (scale_exp - 1)

    This is equivalent to standard total-CAPEX power-law scaling,
    but written here for specific CAPEX inputs.
    """
    return (t_day / baseline_t_day) ** (scale_exp - 1.0)


# -----------------------------
# Worker
# -----------------------------
def run_single_case_ammonia(job):
    """
    Run one optimization case in a worker process.
    Returns techno-economic results only, plus optionally hourly operation output.
    """
    try:
        country = job["country"]
        iso2 = job["iso2"]
        lat = job["lat"]
        lon = job["lon"]
        scenario_name = job["scenario_name"]
        scenario_kwargs = job["scenario_kwargs"]
        db = job["db"]
        cost_dict_in = job["cost_dict"]
        dict_ghg_impacts_in = job["dict_ghg_impacts"]
        future_power_prices_dict = job["future_power_prices_dict"]
        hb_pl_min = job["hb_pl_min"]
        factor_lower_night = job["factor_lower_night"]
        t_day = job["t_day"]
        scale_exp = job["scale_exp"]
        sensitivity_family = job["sensitivity_family"]
        sensitivity_value = job["sensitivity_value"]
        save_operation_output = job["save_operation_output"]

        cost_dict = cost_dict_in.copy()
        dict_ghg_impacts = dict_ghg_impacts_in.copy()

        # Set sensitivity parameters
        cost_dict["hb_pl_min"] = hb_pl_min
        cost_dict["dr"] = ep.get_latest_avg_wacc(iso2)

        # Apply economies-of-scale CAPEX factor
        capex_scale_factor = get_capex_scale_factor(
            t_day=t_day,
            baseline_t_day=BASELINE_T_DAY,
            scale_exp=scale_exp,
        )

        if "hb_capex" not in cost_dict:
            raise KeyError("hb_capex not found in cost_dict")

        cost_dict["hb_capex"] *= capex_scale_factor

        # Optimization limits (scaled with plant size)
        base_limits = ep.get_max_caps_regions()
        scale_factor = t_day / BASELINE_T_DAY

        # Scale all numeric limits with plant size
        dict_limits = {
            k: (v * scale_factor if isinstance(v, (int, float)) else v)
            for k, v in base_limits.items()
        }

        # Power prices
        if db == NAME_REF_DB:
            power_prices = ep.get_elect_prices(
                iso2,
                factor_lower_night=factor_lower_night,
            )
        else:
            power_prices = ep.get_elect_prices(
                iso2,
                factor_lower_night=factor_lower_night,
                price_file=future_power_prices_dict,
            )

        # Renewable CFs
        data_processor = cry.RenewableEnergyProcessor(lat, lon)
        cf_pv, cf_wind = data_processor.process_data()

        # Hourly input dataframe
        df_data = pd.DataFrame(
            data={
                "pv_MW_array": cf_pv,
                "wind_MW_array_on": cf_wind,
                "grid_abs_price": power_prices,
                "rev_inj": 0,
            },
            index=pd.date_range("2023-01-01 00:00", periods=8760, freq="h"),
        )

        # Grid GHG intensities
        df_data["ghg_impact"] = ep.get_activity_env_elect_from_dict(iso2, db=db)
        df_data["ghg_impact_cons"] = 0

        # Run optimization
        # overview_totals, lca_results, input_vars, df_out
        totals_cost_min, __, opt_vars, df_out = opt.opt_amm_electric_hb(
            df_data,
            1,
            0,
            cost_dict,
            dict_ghg_impacts,
            dict_limits,
            sec_db=db,
            export_alias=scenario_name,
            LOC_ELECT=iso2,
            consider_down_times=False,
            size_nh3_system=t_day * 365,
            save_operation_output=SAVE_OPERATION_OUTPUT,
            **scenario_kwargs,
        )

        # Infeasible
        if len(totals_cost_min) == 0 and (opt_vars is None or len(opt_vars) == 0):
            return {
                "status": "infeasible",
                "country": country,
                "iso2": iso2,
                "scenario": scenario_name,
                "db_name": db,
                "hb_pl_min": hb_pl_min,
                "factor_lower_night": factor_lower_night,
                "t_day": t_day,
                "scale_exp": scale_exp,
                "capex_scale_factor": capex_scale_factor,
                "sensitivity_family": sensitivity_family,
                "sensitivity_value": sensitivity_value,
            }

        totals_cost_min = totals_cost_min.copy()
        totals_cost_min["country"] = country
        totals_cost_min["iso2"] = iso2
        totals_cost_min["scenario"] = scenario_name
        totals_cost_min["db_name"] = db
        totals_cost_min["hb_pl_min"] = hb_pl_min
        totals_cost_min["factor_lower_night"] = factor_lower_night
        totals_cost_min["t_day"] = t_day
        totals_cost_min["scale_exp"] = scale_exp
        totals_cost_min["capex_scale_factor"] = capex_scale_factor
        totals_cost_min["sensitivity_family"] = sensitivity_family
        totals_cost_min["sensitivity_value"] = sensitivity_value

        if isinstance(opt_vars, dict):
            opt_vars = opt_vars.copy()
            opt_vars["country"] = country
            opt_vars["iso2"] = iso2
            opt_vars["scenario"] = scenario_name
            opt_vars["db_name"] = db
            opt_vars["hb_pl_min"] = hb_pl_min
            opt_vars["factor_lower_night"] = factor_lower_night
            opt_vars["t_day"] = t_day
            opt_vars["scale_exp"] = scale_exp
            opt_vars["capex_scale_factor"] = capex_scale_factor
            opt_vars["sensitivity_family"] = sensitivity_family
            opt_vars["sensitivity_value"] = sensitivity_value

        operation_payload = None
        if save_operation_output:
            try:
                operation_payload = df_out.copy()
                if isinstance(operation_payload, pd.DataFrame):
                    operation_payload["country"] = country
                    operation_payload["iso2"] = iso2
                    operation_payload["scenario"] = scenario_name
                    operation_payload["db_name"] = db
                    operation_payload["hb_pl_min"] = hb_pl_min
                    operation_payload["factor_lower_night"] = factor_lower_night
                    operation_payload["t_day"] = t_day
                    operation_payload["scale_exp"] = scale_exp
                    operation_payload["capex_scale_factor"] = capex_scale_factor
                    operation_payload["sensitivity_family"] = sensitivity_family
                    operation_payload["sensitivity_value"] = sensitivity_value
            except Exception:
                operation_payload = df_out

        return {
            "status": "ok",
            "country": country,
            "iso2": iso2,
            "scenario": scenario_name,
            "db_name": db,
            "hb_pl_min": hb_pl_min,
            "factor_lower_night": factor_lower_night,
            "t_day": t_day,
            "scale_exp": scale_exp,
            "capex_scale_factor": capex_scale_factor,
            "sensitivity_family": sensitivity_family,
            "sensitivity_value": sensitivity_value,
            "totals_cost_min": totals_cost_min,
            "opt_vars": opt_vars,
            "operation_output": operation_payload,
        }

    except Exception as e:
        return {
            "status": "error",
            "error": repr(e),
            "country": job["country"],
            "iso2": job["iso2"],
            "scenario": job["scenario_name"],
            "db_name": job["db"],
            "hb_pl_min": job["hb_pl_min"],
            "factor_lower_night": job["factor_lower_night"],
            "t_day": job["t_day"],
            "scale_exp": job["scale_exp"],
            "sensitivity_family": job["sensitivity_family"],
            "sensitivity_value": job["sensitivity_value"],
        }


# -----------------------------
# Job builder
# -----------------------------
def build_all_jobs(locations, scenarios, all_dbs):
    """
    Build jobs for:
    - one baseline case
    - hb minimum-load sensitivity
    - tariff sensitivity
    - scale sensitivity (with baseline scale exponent)
    - scale exponent sensitivity at larger representative size

    Only baseline jobs save hourly operation outputs.
    """
    jobs = []

    for db in all_dbs:
        for country, iso2, lat, lon in locations:
            cost_dict = COST_DICT.copy() if db == NAME_REF_DB else COST_DICT_FUTURE.copy()
            dict_ghg_impacts = (
                DICT_GHG_IMPACTS.copy()
                if db == NAME_REF_DB
                else DICT_GHG_IMPACTS_FUTURE.copy()
            )

            for scenario_name, scenario_kwargs in scenarios.items():

                baseline_save_operation_output = SAVE_OPERATION_OUTPUT
                if SAVE_OPERATION_FOR_LOCATIONS is not None:
                    baseline_save_operation_output = country in SAVE_OPERATION_FOR_LOCATIONS

                # -------------------------
                # 1. Baseline
                # -------------------------
                jobs.append(
                    {
                        "country": country,
                        "iso2": iso2,
                        "lat": lat,
                        "lon": lon,
                        "scenario_name": scenario_name,
                        "scenario_kwargs": scenario_kwargs,
                        "db": db,
                        "cost_dict": cost_dict,
                        "dict_ghg_impacts": dict_ghg_impacts,
                        "future_power_prices_dict": FUTURE_POWER_PRICES,
                        "hb_pl_min": BASELINE_HB_PL_MIN,
                        "factor_lower_night": BASELINE_FACTOR_LOWER_NIGHT,
                        "t_day": BASELINE_T_DAY,
                        "scale_exp": BASELINE_SCALE_EXP,
                        "sensitivity_family": "baseline",
                        "sensitivity_value": "baseline",
                        "save_operation_output": baseline_save_operation_output,
                    }
                )

                # -------------------------
                # 2. HB minimum-load sensitivity
                # -------------------------
                for hb_pl_min in HB_MIN_LOAD_VALUES:
                    if hb_pl_min == BASELINE_HB_PL_MIN:
                        continue
                    jobs.append(
                        {
                            "country": country,
                            "iso2": iso2,
                            "lat": lat,
                            "lon": lon,
                            "scenario_name": scenario_name,
                            "scenario_kwargs": scenario_kwargs,
                            "db": db,
                            "cost_dict": cost_dict,
                            "dict_ghg_impacts": dict_ghg_impacts,
                            "future_power_prices_dict": FUTURE_POWER_PRICES,
                            "hb_pl_min": hb_pl_min,
                            "factor_lower_night": BASELINE_FACTOR_LOWER_NIGHT,
                            "t_day": BASELINE_T_DAY,
                            "scale_exp": BASELINE_SCALE_EXP,
                            "sensitivity_family": "hb_min_load",
                            "sensitivity_value": hb_pl_min,
                            "save_operation_output": False,
                        }
                    )

                # -------------------------
                # 3. Tariff sensitivity
                # -------------------------
                for factor_lower_night in LOWER_NIGHT_VALUES:
                    if factor_lower_night == BASELINE_FACTOR_LOWER_NIGHT:
                        continue
                    jobs.append(
                        {
                            "country": country,
                            "iso2": iso2,
                            "lat": lat,
                            "lon": lon,
                            "scenario_name": scenario_name,
                            "scenario_kwargs": scenario_kwargs,
                            "db": db,
                            "cost_dict": cost_dict,
                            "dict_ghg_impacts": dict_ghg_impacts,
                            "future_power_prices_dict": FUTURE_POWER_PRICES,
                            "hb_pl_min": BASELINE_HB_PL_MIN,
                            "factor_lower_night": factor_lower_night,
                            "t_day": BASELINE_T_DAY,
                            "scale_exp": BASELINE_SCALE_EXP,
                            "sensitivity_family": "tariff",
                            "sensitivity_value": factor_lower_night,
                            "save_operation_output": False,
                        }
                    )

                # -------------------------
                # 4. Scale sensitivity
                # -------------------------
                for t_day in T_DAY_VALUES:
                    if t_day == BASELINE_T_DAY:
                        continue
                    jobs.append(
                        {
                            "country": country,
                            "iso2": iso2,
                            "lat": lat,
                            "lon": lon,
                            "scenario_name": scenario_name,
                            "scenario_kwargs": scenario_kwargs,
                            "db": db,
                            "cost_dict": cost_dict,
                            "dict_ghg_impacts": dict_ghg_impacts,
                            "future_power_prices_dict": FUTURE_POWER_PRICES,
                            "hb_pl_min": BASELINE_HB_PL_MIN,
                            "factor_lower_night": BASELINE_FACTOR_LOWER_NIGHT,
                            "t_day": t_day,
                            "scale_exp": BASELINE_SCALE_EXP,
                            "sensitivity_family": "scale",
                            "sensitivity_value": t_day,
                            "save_operation_output": False,
                        }
                    )

                # -------------------------
                # 5. CAPEX economies-of-scale exponent sensitivity
                # -------------------------
                for scale_exp in SCALE_EXP_VALUES:
                    if scale_exp == BASELINE_SCALE_EXP:
                        continue
                    jobs.append(
                        {
                            "country": country,
                            "iso2": iso2,
                            "lat": lat,
                            "lon": lon,
                            "scenario_name": scenario_name,
                            "scenario_kwargs": scenario_kwargs,
                            "db": db,
                            "cost_dict": cost_dict,
                            "dict_ghg_impacts": dict_ghg_impacts,
                            "future_power_prices_dict": FUTURE_POWER_PRICES,
                            "hb_pl_min": BASELINE_HB_PL_MIN,
                            "factor_lower_night": BASELINE_FACTOR_LOWER_NIGHT,
                            "t_day": SCALE_EXP_TEST_T_DAY,
                            "scale_exp": scale_exp,
                            "sensitivity_family": "scale_exp",
                            "sensitivity_value": scale_exp,
                            "save_operation_output": False,
                        }
                    )

    return jobs


# -----------------------------
# Main
# -----------------------------
def main_parallel_ammonia_sensitivity(max_workers=4, locations_subset=None):
    start_time = time.time()

    all_totals = []
    all_opt_vars = []
    all_operation_outputs = []

    if locations_subset is None:
        locations_subset = LOCATIONS_SENS_PLUS

    if GEN_RESULTS:
        print("Building all one-at-a-time sensitivity jobs...")
        jobs = build_all_jobs(
            locations=locations_subset,
            scenarios=SCENARIOS,
            all_dbs=ALL_DBS,
        )
        total_jobs = len(jobs)
        print(f"Prepared {total_jobs} jobs.")

        finished = 0
        infeasible_count = 0
        error_count = 0

        with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(run_single_case_ammonia, job) for job in jobs]

            for future in concurrent.futures.as_completed(futures):
                res = future.result()
                finished += 1

                elapsed_time = time.time() - start_time
                elapsed_minutes = elapsed_time / 60
                avg_time_per_job = elapsed_time / finished
                remaining_minutes = avg_time_per_job * (total_jobs - finished) / 60

                print(
                    f"\rFinished {finished}/{total_jobs} | "
                    f"Elapsed: {elapsed_minutes:.1f} min | "
                    f"Remaining: {remaining_minutes:.1f} min | "
                    f"Infeasible: {infeasible_count} | Errors: {error_count}",
                    end="",
                )

                if res["status"] == "infeasible":
                    infeasible_count += 1
                    print(
                        f"\nWarning: infeasible case for "
                        f'{res["country"]} | {res["scenario"]} | {res["db_name"]} | '
                        f'{res["sensitivity_family"]}={res["sensitivity_value"]}'
                    )
                    continue

                if res["status"] == "error":
                    error_count += 1
                    print(
                        f"\nError for {res['country']} | {res['scenario']} | {res['db_name']} | "
                        f"{res['sensitivity_family']}={res['sensitivity_value']}: {res['error']}"
                    )
                    continue

                all_totals.append(res["totals_cost_min"])

                if isinstance(res["opt_vars"], dict):
                    all_opt_vars.append(pd.DataFrame([res["opt_vars"]]))

                if (
                    res["sensitivity_family"] == "baseline"
                    and res["operation_output"] is not None
                    and isinstance(res["operation_output"], pd.DataFrame)
                ):
                    all_operation_outputs.append(res["operation_output"])

        print()

        if not all_totals:
            raise ValueError("No optimization results collected.")

        totals_cost_all = pd.concat(all_totals, ignore_index=True)

        index_cols = [
            col
            for col in [
                "country",
                "iso2",
                "scenario",
                "db_name",
                "sensitivity_family",
                "sensitivity_value",
            ]
            if col in totals_cost_all.columns
        ]
        if index_cols:
            totals_cost_all = totals_cost_all.set_index(index_cols)

        cases_path = str(FILE_PATH_CASE_STUDIES).replace(".pkl", "_sens_extra.pkl")
        totals_cost_all.to_pickle(cases_path)
        print(f"Saved techno-economic sensitivity results to: {cases_path}")

        if all_opt_vars:
            opt_vars_all = pd.concat(all_opt_vars, ignore_index=True)
            opt_vars_path = str(FILE_PATH_CASE_STUDIES).replace(".pkl", "_opt_vars.pkl")
            opt_vars_all.to_pickle(opt_vars_path)
            print(f"Saved optimization variables to: {opt_vars_path}")
        else:
            opt_vars_all = pd.DataFrame()

        if all_operation_outputs:
            operation_all = pd.concat(all_operation_outputs, axis=0)
            operation_path = str(FILE_PATH_CASE_STUDIES).replace(".pkl", "_operation.pkl")
            operation_all.to_pickle(operation_path)
            print(f"Saved hourly BASELINE operation outputs to: {operation_path}")
        else:
            operation_all = pd.DataFrame()

    else:
        with open(FILE_PATH_CASE_STUDIES, "rb") as file:
            totals_cost_all = pickle.load(file)

        opt_vars_path = str(FILE_PATH_CASE_STUDIES).replace(".pkl", "_opt_vars.pkl")
        operation_path = str(FILE_PATH_CASE_STUDIES).replace(".pkl", "_operation.pkl")

        with open(opt_vars_path, "rb") as file:
            opt_vars_all = pickle.load(file)

        with open(operation_path, "rb") as file:
            operation_all = pickle.load(file)

    return totals_cost_all, opt_vars_all, operation_all


if __name__ == "__main__":
    totals_cost_all, opt_vars_all, operation_all = main_parallel_ammonia_sensitivity(
        max_workers=8,
        locations_subset=LOCATIONS_SENS_PLUS,
    )