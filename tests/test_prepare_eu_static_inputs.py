"""Source-cell, release-contract and solver checks for annual EU references."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil

import numpy as np
import pandas as pd
import pytest

from h2_input_data import validate_hourly_input
from opt_hydrogen_functions import optimize_hydrogen_system
from prepare_eu_static_inputs import load_factor_catalog, operational_source, release_inputs
from prepare_eu_regulatory_inputs import regulatory_source
from run_h2_scenarios import run_h2_scenarios
from validate_h2_results import validate_h2_results


ROOT = Path(__file__).resolve().parents[1]
if os.name == "nt":
    ROOT = Path("\\\\?\\" + str(ROOT))
CATALOG = ROOT / "input_data/h2_eu_static_factors.json"


@pytest.fixture
def evidence(tmp_path):
    catalog = json.loads(CATALOG.read_bytes())
    for item in catalog["sources"].values():
        destination = tmp_path / item["file"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / item["file"], destination)
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(catalog), encoding="utf-8")
    return tmp_path, path, catalog


def save_catalog(evidence):
    root, path, catalog = evidence
    path.write_text(json.dumps(catalog), encoding="utf-8")
    return load_factor_catalog(path, source_root=root)


def mutate_peh(evidence, change):
    root, _, catalog = evidence
    item = catalog["sources"]["eurostat_peh"]
    path = root / item["file"]
    document = json.loads(path.read_bytes())
    change(document)
    path.write_text(json.dumps(document), encoding="utf-8")
    item["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()


def prepared_profiles(root):
    prepared = root / "prepared"
    prepared.mkdir()
    frame = pd.DataFrame({
        "timestamp": pd.date_range("2023-12-31T23:00:00Z", periods=8784, freq="h"),
        "pv_capacity_factor": .25, "wind_capacity_factor": .3,
        "electricity_price_real_eur2023_per_mwh": -10.25,
    })
    hashes = {}
    for site in ("hamburg_moorburg", "huelva_la_rabida"):
        path = prepared / f"{site}_profiles_prices_unreleased.csv"
        frame.to_csv(path, index=False)
        hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    (prepared / "preparation_report.json").write_text(json.dumps({"historical_year": 2024, "output_hashes": hashes}), encoding="utf-8")
    return prepared


def test_actual_published_cells_and_own_net_conversion():
    catalog = load_factor_catalog(CATALOG, source_root=ROOT)
    de, es = catalog["records"]["DE"], catalog["records"]["ES"]
    assert de["eea_gross_factor_kg_co2e_per_mwh"] == 291
    assert es["eea_gross_factor_kg_co2e_per_mwh"] == 125
    assert de["factor_kg_co2e_per_mwh"] == pytest.approx(304.65034889546985)
    assert es["factor_kg_co2e_per_mwh"] == pytest.approx(128.81023975654873)
    assert catalog["data_vintage_alignment"] == "not_verified"
    assert catalog["uncertainty_quantified"] is False
    assert catalog["application_year"] == 2024
    assert catalog["temporal_year_transfer_proxy"] is False
    assert "including islands" in es["application_spatial_scope"]


@pytest.mark.parametrize("key,value", [("reference_year", 2025), ("application_year", 2023), ("unit", "kg_CO2/MWh"), ("denominator_basis", "gross"), ("data_vintage_alignment", "verified")])
def test_wrong_method_boundary_or_year_rejected(evidence, key, value):
    evidence[2][key] = value
    with pytest.raises(ValueError):
        save_catalog(evidence)


def test_catalog_factor_change_cannot_replace_original_cell(evidence):
    evidence[2]["records"]["DE"]["eea_gross_factor_kg_co2e_per_mwh"] = 310
    with pytest.raises(ValueError, match="source cell"):
        save_catalog(evidence)


def test_net_conversion_cannot_be_changed_independently(evidence):
    evidence[2]["records"]["ES"]["factor_kg_co2e_per_mwh"] = 125
    with pytest.raises(ValueError, match="gross/net"):
        save_catalog(evidence)


def test_swapped_country_label_rejected(evidence):
    evidence[2]["records"]["ES"]["country_label"] = "Germany"
    with pytest.raises(ValueError, match="country mapping"):
        save_catalog(evidence)


def test_changed_primary_source_hash_rejected(evidence):
    root, path, catalog = evidence
    source = root / catalog["sources"]["eea_csv"]["file"]
    source.write_bytes(source.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="SHA256"):
        load_factor_catalog(path, source_root=root)


def test_duplicate_csv_headers_are_rejected(evidence):
    root, _, catalog = evidence
    item = catalog["sources"]["eea_csv"]
    path = root / item["file"]
    text = path.read_text("utf-8-sig").replace("2023,2024", "2024,2024", 1)
    path.write_text(text, encoding="utf-8")
    item["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="Duplicate"):
        save_catalog(evidence)


def test_flagged_generation_cell_rejected(evidence):
    cell = evidence[2]["records"]["DE"]["producer_plant_groups"][0]["peh_gross"]["flat_index"]
    mutate_peh(evidence, lambda document: document.setdefault("status", {}).__setitem__(str(cell), "e"))
    with pytest.raises(ValueError, match="flagged"):
        save_catalog(evidence)


def test_source_path_cannot_leave_archive(evidence):
    evidence[2]["sources"]["eea_csv"]["file"] = "../outside.csv"
    with pytest.raises(ValueError, match="relative"):
        save_catalog(evidence)


def test_both_full_year_releases_preserve_inputs_and_sources(evidence):
    root, path, catalog = evidence
    prepared = prepared_profiles(root)
    output = root / "released"
    report = release_inputs(prepared, output, catalog_path=path, source_root=root)
    assert report["hourly_dynamic_operational_factors_released"] is False
    for site, country, regulatory in (("hamburg_moorburg", "DE", 357.48), ("huelva_la_rabida", "ES", 194.76)):
        record = report["sites"][site]
        csv_path = output / record["input_file"]
        data = pd.read_csv(csv_path)
        metadata = json.loads((output / record["metadata_file"]).read_bytes())
        data.attrs.update({key: metadata[key] for key in ("emission_factor_mode", "emission_factor_sources")})
        checked = validate_hourly_input(data, expected_hours=8784, require_separate_emission_factors=True)
        np.testing.assert_allclose(checked["grid_emission_factor"], catalog["records"][country]["factor_kg_co2e_per_mwh"], rtol=1e-14)
        assert checked["regulatory_grid_emission_factor"].eq(regulatory).all()
        assert checked["electricity_price"].eq(-10.25).all()
        assert checked["pv_capacity_factor"].eq(.25).all()
        np.testing.assert_allclose(checked["wind_capacity_factor"], .3, rtol=1e-14)
        assert checked["h2_demand"].sum() == pytest.approx(3650000)
        assert metadata["input_sha256"] == hashlib.sha256(csv_path.read_bytes()).hexdigest()
        assert metadata["emission_factor_sources"]["operational"]["reference_year"] == 2024
        assert metadata["emission_factor_sources"]["operational"]["application_year"] == 2024
        assert metadata["emission_factor_sources"]["operational"]["temporal_year_transfer_proxy"] is False
        assert metadata["emission_factor_sources"]["regulatory"]["reference_year"] == 2020


def test_no_output_before_both_sites_validate(evidence):
    root, path, _ = evidence
    prepared = prepared_profiles(root)
    (prepared / "huelva_la_rabida_profiles_prices_unreleased.csv").write_bytes(b"bad")
    output = root / "released"
    with pytest.raises(ValueError, match="SHA256"):
        release_inputs(prepared, output, catalog_path=path, source_root=root)
    assert not output.exists()


def test_factor_application_and_profile_source_year_must_agree(evidence):
    root, path, catalog = evidence
    prepared = prepared_profiles(root)
    report_path = prepared / "preparation_report.json"
    report = json.loads(report_path.read_bytes())
    report["historical_year"] = 2025
    report_path.write_text(json.dumps(report), encoding="utf-8")
    with pytest.raises(ValueError, match="application year"):
        release_inputs(prepared, root / "wrong_year", catalog_path=path, source_root=root)
    assert not (root / "wrong_year").exists()


def test_all_profiles_have_separate_csv_binding_and_identical_exogenous_inputs(evidence):
    root, path, _ = evidence
    prepared = prepared_profiles(root)
    output = root / "profiles"
    report = release_inputs(prepared, output, catalog_path=path, source_root=root, profiles=("D0","D1","D2"))
    assert len(report["sites"]) == 6
    frames = {}
    for key, record in report["sites"].items():
        data = pd.read_csv(output / record["input_file"])
        frames[key] = data
        assert data["h2_demand"].sum() == pytest.approx(3650000)
        assert len(data) == 8784
        meta = json.loads((output / record["metadata_file"]).read_bytes())
        assert meta["annual_hours"] == 8784
        assert meta["historical_year"] == 2024
        assert meta["input_sha256"] == hashlib.sha256((output / record["input_file"]).read_bytes()).hexdigest()
        assert (data["h2_demand"] > 0).sum() == {"D0":8784,"D1":4392,"D2":3144}[record["demand_profile"]["profile"]]
    for site in ("hamburg_moorburg", "huelva_la_rabida"):
        for profile in ("D1", "D2"):
            pd.testing.assert_frame_equal(frames[f"{site}_D0"].drop(columns="h2_demand"), frames[f"{site}_{profile}"].drop(columns="h2_demand"))


def test_existing_output_is_preserved(evidence):
    root, path, _ = evidence
    prepared = prepared_profiles(root)
    output = root / "released"
    output.mkdir()
    sentinel = output / "old.txt"
    sentinel.write_text("existing research", encoding="utf-8")
    with pytest.raises(FileExistsError):
        release_inputs(prepared, output, catalog_path=path, source_root=root)
    assert sentinel.read_text("utf-8") == "existing research"


def short_case(catalog, country):
    frame = pd.DataFrame({
        "timestamp": pd.date_range("2025-01-01", periods=24, freq="h", tz="UTC"),
        "pv_capacity_factor": 0., "wind_capacity_factor": 0., "electricity_price": 50.,
        "h2_demand": 100., "grid_emission_factor": catalog["records"][country]["factor_kg_co2e_per_mwh"],
        "regulatory_grid_emission_factor": 357.48 if country == "DE" else 194.76,
    })
    frame.attrs.update({"emission_factor_mode": "explicit_separate_factors", "emission_factor_sources": {"operational": operational_source(catalog, country), "regulatory": regulatory_source(country)}})
    return frame


@pytest.mark.parametrize("backend", ["gurobi", "scipy_highs"])
@pytest.mark.parametrize("country", ["DE", "ES"])
def test_static_emissions_equal_energy_times_factor_without_cost_change(backend, country):
    catalog = load_factor_catalog(CATALOG, source_root=ROOT)
    complete = short_case(catalog, country)
    reg_only = complete.drop(columns="grid_emission_factor")
    reg_only.attrs = {"emission_factor_mode": "regulatory_only", "emission_factor_sources": {"regulatory": regulatory_source(country)}}
    result = optimize_hydrogen_system(complete, solver_backend=backend, require_separate_emission_factors=True)
    other = optimize_hydrogen_system(reg_only, solver_backend=backend, emissions_reporting="regulatory_only")
    assert result.objective_eur_per_year == pytest.approx(other.objective_eur_per_year)
    assert result.capacities == pytest.approx(other.capacities)
    pd.testing.assert_series_equal(result.hourly_operation["grid_import_mwh"], other.hourly_operation["grid_import_mwh"])
    grid = result.hourly_operation["grid_import_mwh"].sum() * result.annualization_factor
    assert grid > 0
    assert result.annual_grid_emissions_kg_co2e == pytest.approx(grid * catalog["records"][country]["factor_kg_co2e_per_mwh"])
    assert result.annual_regulatory_emissions_kg_co2e == pytest.approx(other.annual_regulatory_emissions_kg_co2e)


def test_scenario_exports_and_independent_validator_keep_proxy_sources(tmp_path):
    catalog = load_factor_catalog(CATALOG, source_root=ROOT)
    data = short_case(catalog, "ES")
    data["pv_capacity_factor"] = 1.
    source = tmp_path / "input.csv"
    data.to_csv(source, index=False)
    metadata = tmp_path / "input.metadata.json"
    metadata.write_text(json.dumps({"schema_version": "1.0", "input_sha256": hashlib.sha256(source.read_bytes()).hexdigest(), "emission_factor_mode": "explicit_separate_factors", "emission_factor_sources": data.attrs["emission_factor_sources"]}), encoding="utf-8")
    output = tmp_path / "scenarios"
    run_h2_scenarios(source, output, solver_backend="scipy-highs", emission_factor_metadata_path=metadata, require_separate_emission_factors=True)
    validation = validate_h2_results(output, expected_hours=24)
    assert validation.all_checks_passed
    for name in ("S0_reference", "S1_red_monthly", "S2_red_hourly"):
        exported = json.loads((output / name / "run_metadata.json").read_bytes())
        assert exported["input"]["emission_factor_sources"] == data.attrs["emission_factor_sources"]
