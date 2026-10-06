"""Release hashed historical cost/regulatory inputs without inventing operational EF.

The scope decision was made by the researcher on 2026-10-03. Operational
factors and historical generation quality remain separate research artifacts.
No solver is called here. D0 is the already selected constant annual demand.
"""
from __future__ import annotations

import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path

import numpy as np
import pandas as pd

from h2_input_data import validate_hourly_input


SITE_SETTINGS = {
    "hamburg_moorburg": ("DE", "Europe/Berlin", 357.48),
    "huelva_la_rabida": ("ES", "Europe/Madrid", 194.76),
}
ANNEX_SOURCE = "https://eur-lex.europa.eu/eli/reg_del/2023/1185/oj"
ANNUAL_H2_KG = 3_650_000.0
HOURS = 8760


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def regulatory_source(country: str) -> dict:
    return {
        "source_description": "Delegated Regulation (EU) 2023/1185, Annex C Table A, electricity values for 2020; gCO2e/MJ multiplied by 3.6",
        "source_url": ANNEX_SOURCE,
        "reference_year": 2020,
        "spatial_scope": country,
        "unit": "kg_CO2e/MWh",
        "emissions_basis": "Regulatory electricity partial diagnostic; not historical operational emissions or complete RFNBO certification",
    }


def prepare_site_input(source: Path, *, site_id: str, expected_sha256: str, historical_year: int = 2025) -> pd.DataFrame:
    if site_id not in SITE_SETTINGS:
        raise ValueError("Unknown EU site")
    source_bytes = source.read_bytes()
    if hashlib.sha256(source_bytes).hexdigest() != expected_sha256:
        raise ValueError("Prepared profile/price source SHA256 mismatch")
    country, timezone, factor = SITE_SETTINGS[site_id]
    if isinstance(historical_year, bool) or historical_year not in (2024, 2025):
        raise ValueError("EU prepared release supports explicitly declared historical2024 or2025")
    local_start = pd.Timestamp(year=historical_year, month=1, day=1, tz=timezone)
    local_end = pd.Timestamp(year=historical_year + 1, month=1, day=1, tz=timezone)
    expected_axis = pd.date_range(local_start.tz_convert("UTC"), local_end.tz_convert("UTC"), freq="h", inclusive="left")
    hours = len(expected_axis)
    raw = pd.read_csv(BytesIO(source_bytes))
    required = ["timestamp", "pv_capacity_factor", "wind_capacity_factor", "electricity_price_real_eur2023_per_mwh"]
    if raw.columns.duplicated().any() or not set(required).issubset(raw.columns):
        raise ValueError("Prepared profile/price columns are incomplete")
    data = raw[required].rename(columns={"electricity_price_real_eur2023_per_mwh": "electricity_price"}).copy()
    data["h2_demand"] = ANNUAL_H2_KG / hours
    data["regulatory_grid_emission_factor"] = factor
    data.attrs.update({"emission_factor_mode": "regulatory_only", "emission_factor_sources": {"regulatory": regulatory_source(country)}})
    data = validate_hourly_input(data, expected_hours=hours, emissions_reporting="regulatory_only")
    if not np.array_equal(data["timestamp"].to_numpy(), expected_axis.to_numpy()):
        raise ValueError("Input must contain exact UTC intervals of the declared local historical year")
    if set(data["timestamp"].dt.tz_convert(timezone).dt.year) != {historical_year}:
        raise ValueError("Input is outside the local historical year")
    return data


def release_inputs(prepared: Path, output: Path) -> dict:
    report_path = prepared / "preparation_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    year = report.get("historical_year")
    if isinstance(year, bool) or year not in (2024, 2025):
        raise ValueError("Preparation report needs explicit historical2024 or2025")
    validated = {}
    for site_id in SITE_SETTINGS:
        name = f"{site_id}_profiles_prices_unreleased.csv"
        expected = report.get("output_hashes", {}).get(name)
        if not isinstance(expected, str) or len(expected) != 64:
            raise ValueError("Missing prepared source hash")
        validated[site_id] = prepare_site_input(prepared / name, site_id=site_id, expected_sha256=expected, historical_year=year)
    output.mkdir(parents=True, exist_ok=True)
    result = {
        "schema_version": "1.0", "decision_date": "2026-10-03",
        "decision": "Researcher authorized cost and regulatory continuation; operational emissions remain conditional and unresolved",
        "historical_year": year, "price_year": 2023,
        "step19_scope": "costs_and_regulatory_inputs",
        "cost_inputs_released": True, "regulatory_inputs_released": True,
        "operational_point_factors_released": False,
        "annual_solver_runs_performed": False,
        "preparation_report_sha256": sha256(report_path),
        "demand": {"profile": "D0", "annual_kg": ANNUAL_H2_KG, "hourly_kg": ANNUAL_H2_KG / len(next(iter(validated.values()))), "source": "Fixed prescribed annual3650000kg; hours follow declared calendar"},
        "model_limits": [
            "Regulatory electrical partial diagnostic; no complete certification claim",
            "Continuous idealized grid availability; no reconstruction of actual Huelva blackout operation",
            "Wholesale energy prices in real EUR2023; excluded grid fees, levies and procurement margins",
            "Step20 site WACC and Step21/22 demand/calendar implementation required before annual comparison",
        ], "sites": {},
    }
    for site_id, data in validated.items():
        csv_path = output / f"{site_id}_D0_regulatory_only.csv"
        data.to_csv(csv_path, index=False, float_format="%.17g")
        sidecar = {
            "schema_version": "1.0", "input_sha256": sha256(csv_path),
            "emission_factor_mode": "regulatory_only",
            "emission_factor_sources": data.attrs["emission_factor_sources"],
            "historical_year": year, "price_year": 2023,
            "site_id": site_id, "country_code": SITE_SETTINGS[site_id][0],
            "calendar_timezone": SITE_SETTINGS[site_id][1],
            "operational_emissions_status": "not_evaluated",
        }
        meta_path = csv_path.with_suffix(".metadata.json")
        meta_path.write_text(json.dumps(sidecar, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        result["sites"][site_id] = {
            "input_file": csv_path.name, "input_sha256": sha256(csv_path),
            "metadata_file": meta_path.name, "metadata_sha256": sha256(meta_path),
            "source_sha256": report["output_hashes"][f"{site_id}_profiles_prices_unreleased.csv"],
            "hours": len(data), "negative_price_hours": int((data["electricity_price"] < 0).sum()),
            "annual_h2_demand_kg": float(data["h2_demand"].sum()),
            "regulatory_factor_kg_co2e_per_mwh": SITE_SETTINGS[site_id][2],
            "operational_factor_column_present": False,
        }
    (output / "cost_regulatory_release_report.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = release_inputs(args.prepared, args.output)
    print(json.dumps({"released_scope": result["step19_scope"], "sites": list(result["sites"]), "operational_point_factors_released": False}))


if __name__ == "__main__":
    main()
