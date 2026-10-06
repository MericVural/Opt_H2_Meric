"""Synthetic 24-hour EU integration; no empirical annual-result claims.

The existing independent export validator checks each three-scenario group.
Corruption cases prohibit solver calls so provenance failures cannot be hidden
by a successful optimization.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil

import numpy as np
import pandas as pd
import pytest

from config_h2 import Scenario, iter_scalar_parameters
from eu_site_configuration import DEFAULT_EU_DESIGN_PATH, EU_SITE_IDS, load_eu_site_configuration
from h2_sensitivity_overrides import WACC_COMPONENTS
import run_h2_sensitivity as sensitivity
from run_h2_scenarios import run_h2_scenarios
import run_single_site_h2 as single
from validate_h2_results import validate_h2_results

SCENARIOS = (Scenario.REFERENCE, Scenario.RED_MONTHLY, Scenario.RED_HOURLY)
VARIANTS = (
    ("price_low", "electricity_price_offset_eur_per_mwh", -20., "EUR_2023/MWh"),
    ("price_high", "electricity_price_offset_eur_per_mwh", 20., "EUR_2023/MWh"),
    ("wacc_low", "real_wacc_shift_fraction", -.01, "fraction"),
    ("wacc_high", "real_wacc_shift_fraction", .01, "fraction"),
    ("capex_low", "electrolyzer_capex_factor", .75, "factor"),
    ("capex_high", "electrolyzer_capex_factor", 1.25, "factor"),
    ("energy_low", "electrolyzer_specific_electricity_factor", .9, "factor"),
    ("energy_high", "electrolyzer_specific_electricity_factor", 1.1, "factor"),
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, contents: dict) -> None:
    path.write_text(json.dumps(contents, allow_nan=False), encoding="utf-8")


def write_cases(path: Path, variants=VARIANTS) -> None:
    rows = [{"case_id": "baseline", "parameter": "baseline", "level": "base",
             "label": "Synthetic baseline", "value": "", "unit": "-",
             "source": "Synthetic software test", "note": "Not empirical evidence"}]
    rows.extend({"case_id": case_id, "parameter": parameter, "level": "test", "label": case_id,
                 "value": value, "unit": unit, "source": "Synthetic software test", "note": "Not a forecast"}
                for case_id, parameter, value, unit in variants)
    pd.DataFrame(rows).to_csv(path, index=False)


def write_source(root: Path, site_id: str) -> dict:
    root.mkdir(parents=True)
    design = root / "immutable_design.json"
    design.write_bytes(DEFAULT_EU_DESIGN_PATH.read_bytes())
    selected = load_eu_site_configuration(site_id, design_path=design)
    year = selected.metadata["historical_year"]
    source, contract, cases = root / "input.csv", root / "input.metadata.json", root / "cases.csv"
    frame = pd.DataFrame({
        "timestamp": pd.date_range(f"{year}-01-01", periods=24, freq="h", tz="UTC"),
        "pv_capacity_factor": np.ones(24), "wind_capacity_factor": np.full(24, .3),
        "electricity_price": np.r_[-5., np.linspace(20., 120., 23)],
        "grid_emission_factor": np.linspace(250., 480., 24),
        "regulatory_grid_emission_factor": np.linspace(50., 96., 24),
        "h2_demand": np.full(24, 100.),
        "arbitrary_text": ["NA", "001", "", "a,b", "ümlaut", "2e3"] * 4,
    })
    frame.to_csv(source, index=False)
    context = {"site_id": site_id, "country_code": selected.site.country_code,
               "calendar_timezone": selected.calendar_timezone, "historical_year": year, "price_year": 2023}
    write_json(contract, {"schema_version": "1.0", "input_sha256": digest(source),
        "emission_factor_mode": "explicit_separate_factors", **context,
        "emission_factor_sources": {role: {
            "source_description": "Synthetic separate factor for software integration",
            "reference_year": year, "spatial_scope": "synthetic_test_system", "unit": "kg_CO2e/MWh",
            "emissions_basis": "synthetic_operational_CO2e" if role == "operational" else "synthetic_regulatory_CO2e",
        } for role in ("operational", "regulatory")}})
    write_cases(cases)
    return {"source": source, "contract": contract, "cases": cases, "design": design,
            "site_id": site_id, "selected": selected}


def kwargs(fixture: dict) -> dict:
    return {"solver_backend": "scipy-highs", "emission_factor_metadata_path": fixture["contract"],
            "require_separate_emission_factors": True, "eu_site": fixture["site_id"],
            "eu_design_path": fixture["design"]}


@pytest.fixture(scope="module", params=EU_SITE_IDS)
def economic_results(tmp_path_factory, request):
    root = tmp_path_factory.mktemp(request.param)
    fixture = write_source(root / "source", request.param)
    baseline = run_h2_scenarios(fixture["source"], root / "accepted_baseline", **kwargs(fixture))
    validation = validate_h2_results(baseline.output_directory, expected_hours=24)
    assert validation.all_checks_passed
    original_files = {path: digest(path) for path in baseline.output_directory.rglob("*") if path.is_file()}
    calls = []
    original_run = sensitivity.run_single_site_h2
    def count_new_solves(*args, **call_kwargs):
        assert call_kwargs["sensitivity_override"] is not None, "Accepted baseline may never be resolved"
        calls.append(call_kwargs["sensitivity_override"])
        return original_run(*args, **call_kwargs)
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(sensitivity, "run_single_site_h2", count_new_solves)
        artifacts = sensitivity.run_h2_sensitivity(
            fixture["source"], fixture["cases"], root / "economic", scenarios=SCENARIOS,
            reuse_baseline_directory=baseline.output_directory, **kwargs(fixture))
    assert len(calls) == 24
    assert all(digest(path) == sha for path, sha in original_files.items())
    fixture.update(root=root, baseline=baseline, artifacts=artifacts)
    return fixture


def validate_case_group(artifacts, case_id: str, directory: Path):
    comparison = pd.read_csv(artifacts.comparison_path)
    group = comparison.loc[comparison.case_id == case_id].copy()
    group["scenario_id"] = group.scenario.map({"reference": "S0", "red_monthly": "S1", "red_hourly": "S2"})
    group["result_directory"] = group.scenario
    group.to_csv(directory / "scenario_comparison.csv", index=False)
    return validate_h2_results(directory, expected_hours=24)


def test_complete_eu_oat_preserves_sources_calendar_and_exact_text(economic_results):
    fixture = economic_results
    artifacts = fixture["artifacts"]
    comparison = pd.read_csv(artifacts.comparison_path)
    metadata = json.loads(artifacts.metadata_path.read_text(encoding="utf-8"))
    assert len(comparison) == 27
    assert set(comparison.scenario) == {scenario.value for scenario in SCENARIOS}
    assert (comparison.solver_status == "optimal").all()
    assert metadata["number_of_optimization_runs"] == 24
    assert metadata["number_of_reused_baseline_runs"] == 3
    assert metadata["eu_site_configuration"]["design_sha256"] == digest(fixture["design"])
    base = pd.read_csv(fixture["source"], dtype=str, keep_default_na=False)
    source_metadata = json.loads(fixture["contract"].read_text())
    base_parameters = {name: parameter.value for name, parameter in iter_scalar_parameters(fixture["selected"].config)}
    for case_id, parameter, value, _ in VARIANTS:
        case_input = artifacts.output_directory / "case_inputs" / f"{case_id}.csv"
        sidecar = case_input.with_suffix(".metadata.json")
        contract = json.loads(sidecar.read_text())
        child = pd.read_csv(case_input, dtype=str, keep_default_na=False)
        assert contract["schema_version"] == "1.0"
        assert contract["input_sha256"] == digest(case_input)
        assert contract["parent_input"] == {"path": str(fixture["source"].resolve()), "sha256": digest(fixture["source"]),
            "metadata_path": str(fixture["contract"].resolve()), "metadata_sha256": digest(fixture["contract"])}
        assert contract["emission_factor_sources"] == source_metadata["emission_factor_sources"]
        assert child.arbitrary_text.equals(base.arbitrary_text)
        for column in base.columns:
            if column == "electricity_price" and parameter == "electricity_price_offset_eur_per_mwh":
                np.testing.assert_allclose(pd.to_numeric(child[column]), pd.to_numeric(base[column]) + value, rtol=1e-12)
                assert np.diff(pd.to_numeric(child[column])).tolist() == pytest.approx(np.diff(pd.to_numeric(base[column])))
                assert float(child[column].iloc[0]) == -5 + value
            elif column == "timestamp":
                assert pd.to_datetime(child[column], utc=True).equals(pd.to_datetime(base[column], utc=True))
            elif column != "arbitrary_text":
                np.testing.assert_allclose(pd.to_numeric(child[column]), pd.to_numeric(base[column]), rtol=1e-12)
        for scenario in SCENARIOS:
            run = artifacts.runs[(case_id, scenario.value)]
            info = json.loads(run.metadata_path.read_text())
            actual = {name: item["value"] for name, item in info["model_parameters"].items()}
            expected = base_parameters.copy()
            if parameter == "real_wacc_shift_fraction":
                for name in WACC_COMPONENTS:
                    expected[f"technologies.{name}.real_wacc_fraction"] += value
            elif parameter in ("electrolyzer_capex_factor", "electrolyzer_specific_electricity_factor"):
                target = "capex_eur_per_kw" if parameter == "electrolyzer_capex_factor" else "specific_electricity_kwh_per_kg_h2"
                expected[f"technologies.electrolyzer.{target}"] *= value
            assert actual == pytest.approx(expected)
            assert info["schema_version"] == "1.7"
            assert info["calendar_scope"]["annualization"]["annual_hours"] == 8784
            assert info["calendar_scope"]["annualization"]["factor"] == 366
            assert info["model_calendar"]["temporal_correlation_timezone"] == fixture["selected"].calendar_timezone
            assert info["input"]["emission_factor_metadata"]["sha256"] == digest(sidecar)
            wacc = info["input"]["eu_site_configuration"]["wacc"]
            assert wacc["reference_year"] == 2021
            assert wacc["baseline_real_wacc_fraction_per_year"] == fixture["selected"].metadata["wacc"]["real_wacc_fraction_per_year"]
            assert wacc["effective_rates_are_sensitivity_assumptions"] is (parameter == "real_wacc_shift_fraction")
            for name in WACC_COMPONENTS:
                assert wacc["real_wacc_fraction_per_year"][name] == expected[f"technologies.{name}.real_wacc_fraction"]
                assert info["model_parameters"][f"technologies.{name}.real_wacc_fraction"]["reference_year"] == 2021
            exported = pd.read_csv(run.validated_input_path, dtype=str, keep_default_na=False)
            assert exported.arbitrary_text.equals(base.arbitrary_text)
        validation = validate_case_group(artifacts, case_id, artifacts.output_directory / "runs" / case_id)
        assert validation.all_checks_passed


def test_baseline_only_reuse_prohibits_every_solver_call(economic_results, tmp_path, monkeypatch):
    fixture = economic_results
    cases = tmp_path / "baseline.csv"
    write_cases(cases, ())
    def forbidden(*args, **kwargs):
        pytest.fail("Baseline reuse is read-only and must not invoke a solver or single runner")
    monkeypatch.setattr(single, "optimize_hydrogen_system", forbidden)
    monkeypatch.setattr(sensitivity, "run_single_site_h2", forbidden)
    artifacts = sensitivity.run_h2_sensitivity(fixture["source"], cases, tmp_path / "reuse", scenarios=SCENARIOS,
        reuse_baseline_directory=fixture["baseline"].output_directory, **kwargs(fixture))
    metadata = json.loads(artifacts.metadata_path.read_text())
    assert metadata["number_of_optimization_runs"] == 0
    assert metadata["number_of_reused_baseline_runs"] == 3
    comparison = pd.read_csv(artifacts.comparison_path)
    assert set(comparison.run_origin) == {"reused_validated_baseline"}
    assert comparison.lcoh_change_percent_vs_baseline.eq(0).all()
    assert not (artifacts.output_directory / "runs").exists()


@pytest.mark.parametrize("tampering", ["configuration", "sources", "validation", "missing_scenario", "hourly_balance"])
def test_invalid_baseline_archive_cannot_trigger_a_solve(economic_results, tmp_path, monkeypatch, tampering):
    fixture = economic_results
    archive = tmp_path / "copied_baseline"
    shutil.copytree(fixture["baseline"].output_directory, archive)
    if tampering == "validation":
        receipt_path = archive / "validation" / "validation_report.json"
        receipt = json.loads(receipt_path.read_text())
        receipt["all_checks_passed"] = False
        write_json(receipt_path, receipt)
    elif tampering == "missing_scenario":
        comparison_path = archive / "scenario_comparison.csv"
        comparison = pd.read_csv(comparison_path)
        comparison.loc[comparison.scenario != "red_hourly"].to_csv(comparison_path, index=False)
        receipt_path = archive / "validation" / "validation_report.json"
        receipt = json.loads(receipt_path.read_text())
        receipt["source_comparison"]["sha256"] = digest(comparison_path)
        write_json(receipt_path, receipt)
    elif tampering == "hourly_balance":
        hourly_path = archive / "S0_reference" / "hourly_operation.csv"
        hourly = pd.read_csv(hourly_path)
        hourly.loc[0, "grid_import_mwh"] += 1
        hourly.to_csv(hourly_path, index=False)
    else:
        metadata_path = archive / "S0_reference" / "run_metadata.json"
        metadata = json.loads(metadata_path.read_text())
        if tampering == "configuration":
            metadata["model_parameters"]["technologies.pv.capex_eur_per_kw"]["value"] *= 2
        else:
            metadata["input"]["emission_factor_metadata"]["sha256"] = "0" * 64
        write_json(metadata_path, metadata)
    def forbidden(*args, **kwargs):
        pytest.fail("An invalid reused archive must be rejected before any new solve")
    monkeypatch.setattr(single, "optimize_hydrogen_system", forbidden)
    monkeypatch.setattr(sensitivity, "run_single_site_h2", forbidden)
    with pytest.raises(single.H2RunError):
        sensitivity.run_h2_sensitivity(fixture["source"], fixture["cases"], tmp_path / "invalid", scenarios=SCENARIOS,
            reuse_baseline_directory=archive, **kwargs(fixture))


@pytest.mark.parametrize("tampering", ["configuration", "text_metadata", "operation", "record_fields_removed"])
def test_independent_validator_rejects_unreported_sensitivity_changes(economic_results, tmp_path, tampering):
    fixture = economic_results
    original = fixture["artifacts"].output_directory / "runs" / "price_low"
    copied = tmp_path / "group"
    shutil.copytree(original, copied)
    if tampering == "text_metadata":
        path = copied / "reference" / "validated_input.csv"
        data = pd.read_csv(path, dtype=str, keep_default_na=False)
        data.loc[0, "arbitrary_text"] = "changed"
        data.to_csv(path, index=False)
        expected_check = "sensitivity_parent_input_contract"
    else:
        path = copied / "reference" / "run_metadata.json"
        metadata = json.loads(path.read_text())
        if tampering == "configuration":
            metadata["model_parameters"]["technologies.electrolyzer.fixed_opex_eur_per_kw_year"]["value"] *= 2
        elif tampering == "record_fields_removed":
            del metadata["sensitivity_override"]
            del metadata["input"]["sensitivity_provenance"]
        else:
            metadata["sensitivity_override"]["operation"] = "replace_hourly_prices_with_constant"
        write_json(path, metadata)
        expected_check = "sensitivity_one_factor_configuration"
    checked = validate_h2_results(copied, expected_hours=24, output_directory=tmp_path / "tampered_validation")
    assert not checked.all_checks_passed
    checks = pd.read_csv(checked.checks_path)
    assert expected_check in set(checks.loc[~checks.passed, "check_id"])


@pytest.mark.parametrize("tampering", ["parent_csv", "parent_metadata", "undeclared_csv", "record",
                                      "baseline_hash", "baseline_values", "design_hash", "context_removed"])
def test_provenance_tampering_is_rejected_before_solver(tmp_path, monkeypatch, tampering):
    fixture = write_source(tmp_path / "source", EU_SITE_IDS[0])
    write_cases(fixture["cases"], (VARIANTS[0],))
    result = sensitivity.run_h2_sensitivity(fixture["source"], fixture["cases"], tmp_path / "initial",
                                          scenarios=(Scenario.REFERENCE,), **kwargs(fixture))
    child = result.output_directory / "case_inputs" / "price_low.csv"
    sidecar = child.with_suffix(".metadata.json")
    contract = json.loads(sidecar.read_text())
    snapshot = Path(contract["baseline_configuration"]["path"])
    if tampering in ("parent_csv", "parent_metadata"):
        target = fixture["source"] if tampering == "parent_csv" else fixture["contract"]
        target.write_bytes(target.read_bytes() + b"\n")
    elif tampering == "undeclared_csv":
        data = pd.read_csv(child, dtype=str, keep_default_na=False)
        data.loc[0, "arbitrary_text"] = "tampered"
        data.to_csv(child, index=False)
        contract["input_sha256"] = digest(child)
    elif tampering == "record":
        contract["case_transformation"]["value"] = -19
    elif tampering == "context_removed":
        del contract["country_code"]
    else:
        baseline = json.loads(snapshot.read_text())
        if tampering == "baseline_values":
            baseline["model_parameters"]["technologies.pv.capex_eur_per_kw"]["value"] *= 2
        elif tampering == "design_hash":
            baseline["eu_design_sha256"] = "0" * 64
        else:
            baseline["model_calendar"]["temporal_correlation_timezone"] = "UTC"
        write_json(snapshot, baseline)
        if tampering != "baseline_hash":
            contract["baseline_configuration"]["sha256"] = digest(snapshot)
    write_json(sidecar, contract)
    def forbidden(*args, **kwargs):
        pytest.fail("Provenance must be rejected before invoking the solver")
    monkeypatch.setattr(single, "optimize_hydrogen_system", forbidden)
    with pytest.raises((ValueError, single.H2RunError)):
        single.run_single_site_h2(child, tmp_path / "forbidden", **{**kwargs(fixture),
            "emission_factor_metadata_path": sidecar}, sensitivity_override={
                "parameter": VARIANTS[0][1], "value": VARIANTS[0][2],
                "source": "Synthetic software test", "note": "Not a forecast"})
    assert not (tmp_path / "forbidden").exists()


@pytest.mark.parametrize("parameter,value,unit", [
    ("real_wacc_shift_fraction", -.02, "fraction"), ("real_wacc_shift_fraction", 1., "fraction"),
    ("electrolyzer_capex_factor", 0., "factor"), ("electrolyzer_specific_electricity_factor", -1., "factor"),
])
def test_all_interventions_are_bounded_before_first_solve(tmp_path, monkeypatch, parameter, value, unit):
    fixture = write_source(tmp_path / "source", EU_SITE_IDS[0])
    write_cases(fixture["cases"], (*VARIANTS[:1], ("invalid_late_case", parameter, value, unit)))
    def forbidden(*args, **kwargs):
        pytest.fail("The entire intervention table must be validated before the first solve")
    monkeypatch.setattr(single, "optimize_hydrogen_system", forbidden)
    with pytest.raises(ValueError):
        sensitivity.run_h2_sensitivity(fixture["source"], fixture["cases"], tmp_path / "invalid", **kwargs(fixture))


def test_legacy_constant_price_and_uniform_wacc_with_derived_contract(tmp_path):
    fixture = write_source(tmp_path / "source", EU_SITE_IDS[0])
    write_cases(fixture["cases"], (("constant", "electricity_price_eur_per_mwh", 50., "EUR_2023/MWh"),
                                 ("uniform", "uniform_real_wacc_fraction", .11, "fraction")))
    artifacts = sensitivity.run_h2_sensitivity(fixture["source"], fixture["cases"], tmp_path / "legacy",
                                             scenarios=SCENARIOS, **kwargs(fixture))
    assert pd.read_csv(artifacts.output_directory / "case_inputs" / "constant.csv").electricity_price.eq(50).all()
    for scenario in SCENARIOS:
        info = json.loads(artifacts.runs[("uniform", scenario.value)].metadata_path.read_text())
        for name in WACC_COMPONENTS:
            parameter = info["model_parameters"][f"technologies.{name}.real_wacc_fraction"]
            assert parameter["value"] == .11
            assert parameter["reference_year"] is None
    for case_id in ("constant", "uniform"):
        assert validate_case_group(artifacts, case_id, artifacts.output_directory / "runs" / case_id).all_checks_passed
