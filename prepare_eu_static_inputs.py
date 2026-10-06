"""Release EU historical inputs with sourced static annual operational references.

EEA's published 2024 gross-generation CO2e intensity is converted with the
archived Eurostat 2024 gross/net generation ratio. This is our own approximate
national net-generation reference, not an EEA net/consumption/hourly factor.
All source bytes and source cells are checked before either site is written.
Reference and application year are explicit; actual source-year weather/prices
and all leap-day hours are retained. Optional prescribed D1/D2 demand uses
the site local calendar with the same fixed annual H2 volume.
"""
from __future__ import annotations

import argparse
import csv
from copy import deepcopy
import hashlib
from io import StringIO
import json
import math
from pathlib import Path, PurePosixPath

import pandas as pd

from eu_emission_factor_audit import JsonStat
from eu_demand_profiles import PROFILES, demand_profile
from h2_input_data import validate_hourly_input
from prepare_eu_regulatory_inputs import (
    ANNUAL_H2_KG, SITE_SETTINGS, prepare_site_input, sha256,
)

METHOD = "static_annual_national_net_generation_proxy"
PRODUCERS = (("PRR_MAIN", "ELC"), ("PRR_MAIN", "CHP"), ("PRR_AUTO", "ELC"), ("PRR_AUTO", "CHP"))
COUNTRY_LABELS = {"DE": "Germany", "ES": "Spain"}


def _positive(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a finite positive number")
    return float(value)


def _source_bytes(root: Path, item: dict) -> bytes:
    relative = PurePosixPath(item["file"])
    if relative.is_absolute() or ".." in relative.parts or ":" in item["file"] or "\\" in item["file"]:
        raise ValueError("Source path must be relative to the source root")
    path = (root / Path(*relative.parts)).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Source path leaves source root")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != item["sha256"]:
        raise ValueError(f"Source SHA256 mismatch: {relative}")
    return raw


def load_factor_catalog(catalog_path: Path, *, source_root: Path) -> dict:
    """Recalculate both factors from original hashed CSV/JSON-stat observations."""
    raw_catalog = catalog_path.read_bytes()
    catalog = json.loads(raw_catalog)
    if catalog.get("schema_version") != "1.0" or catalog.get("method") != METHOD:
        raise ValueError("Unsupported static factor catalog contract")
    year = catalog.get("application_year")
    if catalog.get("reference_year") != 2024 or isinstance(year, bool) or year not in (2024, 2025):
        raise ValueError("Catalog must declare source2024 and explicit application2024 or2025")
    transfer = catalog.get("temporal_year_transfer_proxy", year != 2024)
    if not isinstance(transfer, bool) or transfer != (year != 2024):
        raise ValueError("Temporal transfer status disagrees with reference/application year")
    if catalog.get("unit") != "kg_CO2e/MWh" or catalog.get("denominator_basis") != "net_electricity_generation":
        raise ValueError("Static catalog needs CO2e per net electricity generation")
    if catalog.get("data_vintage_alignment") != "not_verified":
        raise ValueError("EEA/Eurostat vintage alignment must remain explicitly unverified")
    if set(catalog.get("records", {})) != set(COUNTRY_LABELS):
        raise ValueError("Catalog must contain exactly DE and ES")
    source_data = {key: _source_bytes(source_root, item) for key, item in catalog["sources"].items()}
    decoded_csv = source_data["eea_csv"].decode("utf-8-sig")
    header = next(csv.reader(StringIO(decoded_csv)))
    if len(header) != len(set(header)):
        raise ValueError("Duplicate EEA CSV headers")
    rows = list(csv.DictReader(StringIO(decoded_csv)))
    peh = JsonStat(json.loads(source_data["eurostat_peh"]))
    if set(peh.ids) != {"freq", "plants", "operator", "nrg_bal", "siec", "unit", "geo", "time"}:
        raise ValueError("Unexpected Eurostat electricity dataset dimensions")
    for country, label in COUNTRY_LABELS.items():
        record = catalog["records"][country]
        if record.get("country_label") != label:
            raise ValueError("Catalog country mapping disagrees with original EEA label")
        matches = [row for row in rows if row.get("Countries") == label]
        if len(matches) != 1 or "2024" not in matches[0]:
            raise ValueError("Missing or duplicate EEA country/year cell")
        gross = _positive(float(matches[0]["2024"]), "EEA gross intensity")
        if gross != _positive(record["eea_gross_factor_kg_co2e_per_mwh"], "Catalog gross factor"):
            raise ValueError("EEA gross factor disagrees with original source cell")
        generation = {}
        producer_values = {}
        for kind in ("GEP", "NEP"):
            values = []
            for operator, plants in PRODUCERS:
                observation = peh.get(freq="A", plants=plants, operator=operator, nrg_bal=kind, siec="TOTAL", unit="GWH", geo=country, time="2024")
                if not observation.usable():
                    raise ValueError("Missing/flagged/negative generation source cell")
                values.append(observation.value)
                producer_values[(kind, operator, plants)] = observation.value
            generation[kind] = sum(values)
            total = peh.get(freq="A", plants="TOTAL", operator="TOTAL", nrg_bal=kind, siec="TOTAL", unit="GWH", geo=country, time="2024")
            if not total.usable(positive=True) or not math.isclose(generation[kind], total.value, rel_tol=1e-12):
                raise ValueError("Four producer groups disagree with published TOTAL")
            if not math.isclose(generation[kind], _positive(record[f"{kind.lower()}_gwh"], kind), rel_tol=1e-12):
                raise ValueError("Generation sum disagrees with original Eurostat cells")
        if any(producer_values[("NEP", operator, plants)] > producer_values[("GEP", operator, plants)] for operator, plants in PRODUCERS):
            raise ValueError("Producer net generation exceeds gross generation")
        ratio = generation["GEP"] / generation["NEP"]
        calculated = gross * ratio
        if ratio < 1 or not math.isclose(calculated, _positive(record["factor_kg_co2e_per_mwh"], "Net reference"), rel_tol=1e-12):
            raise ValueError("Catalog factor disagrees with gross/net calculation")
        if record.get("spatial_scope") != country or not record.get("application_spatial_scope"):
            raise ValueError("Country/reference/application spatial scope is missing")
    catalog["catalog_sha256"] = hashlib.sha256(raw_catalog).hexdigest()
    return catalog


def operational_source(catalog: dict, country: str) -> dict:
    record = catalog["records"][country]
    return {
        "source_description": "EEA 2024 early-estimate national CO2e/gross-generation intensity; own Eurostat 2024 gross/net denominator conversion",
        "source_url": catalog["sources"]["eea_methodology"]["url"],
        "reference_year": 2024, "application_year": catalog["application_year"],
        "temporal_year_transfer_proxy": catalog["application_year"] != 2024,
        "spatial_scope": country, "application_spatial_scope": record["application_spatial_scope"],
        "unit": "kg_CO2e/MWh",
        "emissions_basis": "Annual national net-generation reference proxy, EEA inventory convention; excludes imports, grid losses, fuel upstream and plant construction; EEA assigns nuclear/renewables zero, including biomass. Not a measured consumption, marginal or hourly factor.",
        "temporal_resolution": "annual_constant", "method": METHOD,
        "factor_kg_co2e_per_mwh": record["factor_kg_co2e_per_mwh"],
        "eea_gross_factor_kg_co2e_per_mwh": record["eea_gross_factor_kg_co2e_per_mwh"],
        "gross_generation_gwh": record["gep_gwh"], "net_generation_gwh": record["nep_gwh"],
        "data_vintage_alignment": "not_verified",
        "provisional_status": "EEA early estimate for 2024",
        "source_catalog_sha256": catalog["catalog_sha256"],
        "source_files": deepcopy(catalog["sources"]),
        "uncertainties": deepcopy(catalog["uncertainties"]),
        "uncertainty_quantified": False,
    }


def prepare_static_site_input(source: Path, *, site_id: str, expected_sha256: str, catalog: dict, profile: str = "D0") -> pd.DataFrame:
    year = catalog["application_year"]
    data = prepare_site_input(source, site_id=site_id, expected_sha256=expected_sha256, historical_year=year)
    country = SITE_SETTINGS[site_id][0]
    demand, demand_metadata = demand_profile(pd.DatetimeIndex(data["timestamp"]), profile=profile,
        timezone=SITE_SETTINGS[site_id][1], historical_year=year, annual_kg=ANNUAL_H2_KG)
    data["h2_demand"] = demand.to_numpy()
    data.attrs["demand_profile"] = demand_metadata
    data["grid_emission_factor"] = catalog["records"][country]["factor_kg_co2e_per_mwh"]
    data.attrs["emission_factor_mode"] = "explicit_separate_factors"
    data.attrs["emission_factor_sources"]["operational"] = operational_source(catalog, country)
    return validate_hourly_input(data, expected_hours=len(data), require_separate_emission_factors=True)


def release_inputs(prepared: Path, output: Path, *, catalog_path: Path, source_root: Path, profiles: tuple[str, ...] = ("D0",)) -> dict:
    catalog = load_factor_catalog(catalog_path, source_root=source_root)
    preparation_path = prepared / "preparation_report.json"
    preparation = json.loads(preparation_path.read_bytes())
    year = catalog["application_year"]
    if preparation.get("historical_year") != year:
        raise ValueError("Preparation report historical year disagrees with factor application year")
    if not profiles or len(set(profiles)) != len(profiles) or any(profile not in PROFILES for profile in profiles):
        raise ValueError("Release profiles must be unique D0,D1,D2 selections")
    validated = {}
    for site in SITE_SETTINGS:
        name = f"{site}_profiles_prices_unreleased.csv"
        expected = preparation.get("output_hashes", {}).get(name)
        if not isinstance(expected, str) or len(expected) != 64:
            raise ValueError("Missing prepared source hash")
        for profile in profiles:
            validated[(site, profile)] = prepare_static_site_input(prepared / name, site_id=site, expected_sha256=expected, catalog=catalog, profile=profile)
    if output.exists():
        raise FileExistsError("Use a new release directory; existing scientific artifacts are not overwritten")
    if output.resolve() == prepared.resolve() or output.resolve() in prepared.resolve().parents:
        raise ValueError("Release directory must not replace the prepared sources")
    output.mkdir(parents=True)
    result = {
        "schema_version": "1.0", "decision_date": "2026-10-03",
        "decision": "Researcher chose static country operational factors and authorized actual2024 historical calendar; prior2025 release remains reproducible",
        "method": METHOD, "historical_year": year, "price_year": 2023,
        "temporal_year_transfer_proxy": year != 2024,
        "annualization_basis": "historical_calendar_year", "annual_hours": len(next(iter(validated.values()))),
        "operational_reference_year": 2024, "regulatory_reference_year": 2020,
        "cost_inputs_released": True, "regulatory_inputs_released": True,
        "operational_static_reference_factors_released": True,
        "hourly_dynamic_operational_factors_released": False,
        "annual_solver_runs_performed": False,
        "catalog_sha256": catalog["catalog_sha256"],
        "preparation_report_sha256": sha256(preparation_path),
        "demand": {"profiles": list(profiles), "annual_kg": ANNUAL_H2_KG},
        "uncertainties": catalog["uncertainties"], "sites": {},
    }
    for (site, profile), data in validated.items():
        country, timezone, regulatory = SITE_SETTINGS[site]
        csv_path = output / f"{site}_{profile}_static_factors.csv"
        data.to_csv(csv_path, index=False, float_format="%.17g")
        metadata = {
            "schema_version": "1.0", "input_sha256": sha256(csv_path),
            "emission_factor_mode": "explicit_separate_factors",
            "emission_factor_sources": data.attrs["emission_factor_sources"],
            "historical_year": year, "price_year": 2023,
            "annualization_basis": "historical_calendar_year", "annual_hours": len(data),
            "expected_hours": len(data), "demand_profile": data.attrs["demand_profile"],
            "site_id": site, "country_code": country, "calendar_timezone": timezone,
            "operational_emissions_status": "evaluated",
            "operational_factor_interpretation": "static_annual_generation_reference",
        }
        meta_path = csv_path.with_suffix(".metadata.json")
        meta_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        key = site if profiles == ("D0",) else f"{site}_{profile}"
        result["sites"][key] = {
            "site_id": site, "demand_profile": data.attrs["demand_profile"],
            "input_file": csv_path.name, "input_sha256": sha256(csv_path),
            "metadata_file": meta_path.name, "metadata_sha256": sha256(meta_path),
            "source_sha256": preparation["output_hashes"][f"{site}_profiles_prices_unreleased.csv"],
            "hours": len(data), "negative_price_hours": int((data["electricity_price"] < 0).sum()),
            "annual_h2_demand_kg": float(data["h2_demand"].sum()),
            "operational_factor_kg_co2e_per_mwh": catalog["records"][country]["factor_kg_co2e_per_mwh"],
            "regulatory_factor_kg_co2e_per_mwh": regulatory,
        }
    (output / "static_factor_release_report.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--catalog", type=Path, default=Path("input_data/h2_eu_static_factors.json"))
    parser.add_argument("--source-root", type=Path, default=Path("."))
    parser.add_argument("--profiles", default="D0", help="Comma-separated D0,D1,D2; equal fixed annual volume")
    args = parser.parse_args()
    result = release_inputs(args.prepared, args.output, catalog_path=args.catalog, source_root=args.source_root, profiles=tuple(args.profiles.split(",")))
    print(json.dumps({"method": result["method"], "sites": result["sites"]}))


if __name__ == "__main__":
    main()
