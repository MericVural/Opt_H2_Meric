"""Small synthetic solves verify EU finance selection at both runner ports.

These 24-hour fixtures establish software integration only. They are neither
historical site input nor empirical operational emissions evidence.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from config_h2 import default_model_config
from eu_site_configuration import DEFAULT_EU_DESIGN_PATH, EU_SITE_IDS, load_eu_site_configuration
import run_h2_scenarios as batch
import run_single_site_h2 as single
import eu_site_configuration as eu
from eu_test_designs import write_calendar_design

@pytest.fixture(autouse=True)
def explicit_archived_design(tmp_path,monkeypatch):
    path=write_calendar_design(eu.DEFAULT_EU_DESIGN_PATH,tmp_path/'archived_2025_design.json',2025)
    monkeypatch.setattr(eu,'DEFAULT_EU_DESIGN_PATH',path)
    monkeypatch.setitem(globals(),'DEFAULT_EU_DESIGN_PATH',path)


COMPONENTS = (
    ("pv", "pv", "pv_capacity_mw"),
    ("wind_onshore", "wind", "wind_capacity_mw"),
    ("electrolyzer", "electrolyzer", "electrolyzer_capacity_mw"),
    ("compressor", "compressor", "compressor_capacity_mw"),
    ("h2_storage", "h2_storage", "h2_storage_capacity_kg"),
)


def _declared_context(site_id: str) -> dict:
    selected = load_eu_site_configuration(site_id)
    return {"site_id": site_id, "country_code": selected.site.country_code,
            "calendar_timezone": selected.calendar_timezone,
            "historical_year": 2025, "price_year": 2023}


def _write_fixture(directory: Path, *, context: dict | None = None) -> tuple[Path, Path]:
    directory.mkdir()
    frame = pd.DataFrame({
        "timestamp": pd.date_range("2025-01-01", periods=24, freq="h", tz="UTC"),
        "pv_capacity_factor": np.ones(24),
        "wind_capacity_factor": np.full(24, .3),
        "electricity_price": np.full(24, 70.),
        "h2_demand": np.full(24, 100.),
        "regulatory_grid_emission_factor": np.full(24, 60.),
    })
    source = directory / "synthetic_input.csv"
    frame.to_csv(source, index=False)
    contract = directory / "synthetic_contract.json"
    contents = {
        "schema_version": "1.0",
        "input_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "emission_factor_mode": "regulatory_only",
        "emission_factor_sources": {"regulatory": {
            "source_description": "Synthetic software fixture, no empirical factor",
            "reference_year": 2025,
            "spatial_scope": "synthetic_test_system",
            "unit": "kg_CO2e/MWh",
            "emissions_basis": "synthetic_regulatory_CO2e",
        }},
    }
    if context is not None:
        contents.update(context)
    contract.write_text(json.dumps(contents), encoding="utf-8")
    return source, contract


def _assert_finance(artifacts, site_id: str | None) -> dict:
    metadata = json.loads(artifacts.metadata_path.read_text(encoding="utf-8"))
    expected = default_model_config() if site_id is None else load_eu_site_configuration(site_id).config
    assert metadata["input"]["number_of_hours"] == 24
    assert metadata["result"]["operational_emissions_status"] == "not_evaluated"
    assert artifacts.result.capacities["electrolyzer_capacity_mw"] > 0
    assert artifacts.result.capacities["compressor_capacity_mw"] > 0
    for name, cost_prefix, capacity_key in COMPONENTS:
        technology = getattr(expected.technologies, name)
        rate = technology.real_wacc_fraction.value
        parameter = metadata["model_parameters"][f"technologies.{name}.real_wacc_fraction"]
        assert parameter["value"] == rate
        assert parameter["reference_year"] == technology.real_wacc_fraction.reference_year
        life = int(technology.lifetime_years.value)
        # Independent present-value identity, applied to actual solved capacities.
        annuity = 1 / sum((1 + rate) ** -year for year in range(1, life + 1))
        capex = (technology.capex_eur_per_kg_h2.value if name == "h2_storage"
                 else technology.capex_eur_per_mw)
        cost = artifacts.result.annual_costs[f"{cost_prefix}_annualized_capex_eur_per_year"]
        assert cost == pytest.approx(capex * artifacts.result.capacities[capacity_key] * annuity, rel=1e-11, abs=1e-8)
    selection = metadata["input"]["eu_site_configuration"]
    if site_id is None:
        assert selection is None
        assert metadata["model_parameters"]["study.weather_start_year"]["value"] == 2007
        assert metadata["model_parameters"]["study.weather_end_year"]["value"] == 2016
    else:
        context = _declared_context(site_id)
        assert metadata["input"]["declared_input_context"] == context
        assert all(metadata["input"][key] == value for key, value in context.items())
        assert selection["site_id"] == site_id
        assert selection["design_sha256"] == hashlib.sha256(DEFAULT_EU_DESIGN_PATH.read_bytes()).hexdigest()
        assert selection["wacc"]["reference_year"] == 2021
        assert selection["wacc"]["no_additional_inflation_conversion"] is True
        assert selection["wacc"]["no_second_tax_shield"] is True
        assert selection["hourly_input_verified_by_this_function"] is False
        assert metadata["model_parameters"]["study.weather_start_year"]["value"] == 2025
        assert metadata["model_parameters"]["study.weather_end_year"]["value"] == 2025
        assert metadata["calendar_scope"]["monthly_correlation_calendar"] == selection["calendar_timezone"]
        assert metadata["calendar_scope"]["monthly_grouping_basis"] == "site_local_calendar_month"
        assert metadata["calendar_scope"]["site_timezone_applied_to_monthly_correlation"] is True
        assert metadata["calendar_scope"]["requested_site_timezone"] == selection["calendar_timezone"]
    return metadata


@pytest.mark.parametrize("runner_name", ["single", "batch"])
@pytest.mark.parametrize("site_id", [None, *EU_SITE_IDS])
def test_24_hour_runner_costs_and_archive_use_selected_finance(tmp_path, runner_name, site_id):
    context = None if site_id is None else _declared_context(site_id)
    source, contract = _write_fixture(tmp_path / "source", context=context)
    kwargs = dict(solver_backend="scipy-highs", emission_factor_metadata_path=contract,
                  emissions_reporting="regulatory_only", eu_site=site_id)
    if runner_name == "single":
        _assert_finance(single.run_single_site_h2(source, tmp_path / "results", **kwargs), site_id)
        return
    artifacts = batch.run_h2_scenarios(source, tmp_path / "results", include_off_grid=True, **kwargs)
    assert set(artifacts.scenario_runs) == {"S0", "S1", "S2", "S3"}
    metadata = [_assert_finance(result, site_id) for result in artifacts.scenario_runs.values()]
    recorded_rates = [{name: row["model_parameters"][f"technologies.{name}.real_wacc_fraction"]["value"]
                       for name, _, _ in COMPONENTS} for row in metadata]
    assert all(rates == recorded_rates[0] for rates in recorded_rates)
    batch_metadata = json.loads(artifacts.metadata_path.read_text(encoding="utf-8"))
    assert batch_metadata["input"]["eu_site_configuration"] == metadata[0]["input"]["eu_site_configuration"]
    if context is not None:
        assert batch_metadata["input"]["declared_input_context"] == context
        assert all(batch_metadata["input"][key] == value for key, value in context.items())


@pytest.mark.parametrize("runner_name", ["single", "batch"])
@pytest.mark.parametrize("field,wrong", [
    ("site_id", "huelva_la_rabida"), ("country_code", "ES"),
    ("calendar_timezone", "Europe/Madrid"), ("historical_year", 2024), ("price_year", 2025),
])
def test_selected_site_rejects_contradictory_source_context_before_solving(tmp_path, monkeypatch, runner_name, field, wrong):
    context = _declared_context("hamburg_moorburg")
    context[field] = wrong
    source, contract = _write_fixture(tmp_path / "source", context=context)
    module, target, runner = ((single, "optimize_hydrogen_system", single.run_single_site_h2)
                              if runner_name == "single"
                              else (batch, "run_single_site_h2", batch.run_h2_scenarios))
    def forbidden(*args, **kwargs):
        pytest.fail("Conflicting site/source context must be rejected before solving")
    monkeypatch.setattr(module, target, forbidden)
    with pytest.raises(single.H2RunError):
        runner(source, tmp_path / "unused_output", emission_factor_metadata_path=contract,
               emissions_reporting="regulatory_only", eu_site="hamburg_moorburg")
    assert not (tmp_path / "unused_output").exists()


@pytest.mark.parametrize("runner_name", ["single", "batch"])
def test_declared_source_site_alone_preserves_context_and_legacy_finance(tmp_path, runner_name):
    context = _declared_context("hamburg_moorburg")
    source, contract = _write_fixture(tmp_path / "source", context=context)
    kwargs = dict(solver_backend="scipy-highs", emission_factor_metadata_path=contract,
                  emissions_reporting="regulatory_only")
    if runner_name == "single":
        artifacts = single.run_single_site_h2(source, tmp_path / "results", **kwargs)
        metadata = _assert_finance(artifacts, None)
    else:
        artifacts = batch.run_h2_scenarios(source, tmp_path / "results", **kwargs)
        for result in artifacts.scenario_runs.values():
            metadata = _assert_finance(result, None)
            assert metadata["input"]["declared_input_context"] == context
        metadata = json.loads(artifacts.metadata_path.read_text(encoding="utf-8"))
    assert metadata["input"]["eu_site_configuration"] is None
    assert metadata["input"]["declared_input_context"] == context
    assert all(metadata["input"][key] == value for key, value in context.items())


@pytest.mark.parametrize("runner_name", ["single", "batch"])
@pytest.mark.parametrize("site_id", EU_SITE_IDS)
def test_cli_forwards_site_and_design_arguments(monkeypatch, tmp_path, runner_name, site_id):
    module, target = (single, "run_single_site_h2") if runner_name == "single" else (batch, "run_h2_scenarios")
    captured = {}
    def capture(*args, **kwargs):
        captured.update(kwargs)
        raise single.H2RunError("Stop after proving CLI forwarding; no solve required")
    monkeypatch.setattr(module, target, capture)
    design = tmp_path / "explicit_design.json"
    assert module.main(["--input", str(tmp_path / "unused.csv"), "--output-dir", str(tmp_path / "unused_output"),
                        "--eu-site", site_id, "--eu-design", str(design),
                        "--emissions-reporting", "regulatory-only"]) == 1
    assert captured["eu_site"] == site_id
    assert captured["eu_design_path"] == design
    assert captured["emissions_reporting"] == "regulatory_only"
    assert not (tmp_path / "unused_output").exists()


@pytest.mark.parametrize("runner", [single.run_single_site_h2, batch.run_h2_scenarios])
def test_design_override_requires_explicit_site_before_any_IO(tmp_path, runner):
    with pytest.raises(single.H2RunError, match="eu_site"):
        runner(tmp_path / "nonexistent.csv", tmp_path / "unused_output", eu_design_path=DEFAULT_EU_DESIGN_PATH)
    assert not (tmp_path / "unused_output").exists()


def test_batch_cli_rejects_ambiguous_finance_selection(tmp_path):
    with pytest.raises(SystemExit) as error:
        batch.main(["--input", str(tmp_path / "nonexistent.csv"), "--output-dir", str(tmp_path / "unused_output"),
                    "--eu-site", EU_SITE_IDS[0], "--uniform-real-wacc", "0.04", "--wacc-source", "synthetic"])
    assert error.value.code == 2
    assert not (tmp_path / "unused_output").exists()
