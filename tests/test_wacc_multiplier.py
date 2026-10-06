"""Relative financing intervention: synthetic software tests, not annual evidence."""
from __future__ import annotations

import json
from pathlib import Path
import shutil

import numpy as np
import pandas as pd
import pytest

from config_h2 import Scenario, iter_scalar_parameters
from eu_site_configuration import EU_SITE_IDS, load_eu_site_configuration
from h2_sensitivity_overrides import WACC_COMPONENTS, apply_sensitivity_override
import run_h2_sensitivity as sensitivity
from run_h2_scenarios import run_h2_scenarios
import run_single_site_h2 as single
from validate_h2_results import validate_h2_results
from test_eu_h2_sensitivity import digest, kwargs, validate_case_group, write_cases, write_json, write_source

FACTORS = (7 / 11, 15 / 11, 1.0)
VARIANTS = tuple((case_id, "real_wacc_multiplier", factor, "factor") for case_id, factor in
                 zip(("wacc_relative_low", "wacc_relative_high", "wacc_identity"), FACTORS, strict=True))
SCENARIOS = (Scenario.REFERENCE, Scenario.RED_MONTHLY, Scenario.RED_HOURLY)


def override(factor):
    return {"parameter": "real_wacc_multiplier", "value": factor,
            "source": "Synthetic relative financing scenario", "note": "Not a financing observation"}


@pytest.mark.parametrize("site_id", EU_SITE_IDS)
@pytest.mark.parametrize("factor", FACTORS)
def test_multiplier_changes_only_five_rates_and_preserves_country_ratios(site_id, factor):
    base = load_eu_site_configuration(site_id).config
    before = dict(iter_scalar_parameters(base))
    changed_config, record = apply_sensitivity_override(base, override(factor))
    after = dict(iter_scalar_parameters(changed_config))
    keys = {f"technologies.{name}.real_wacc_fraction" for name in WACC_COMPONENTS}
    assert dict(iter_scalar_parameters(base)) == before
    assert record["operation"] == "multiply_all_five_real_wacc_rates"
    assert set(record["changed_scalar_parameters"]) == (keys if factor != 1 else set())
    for key, original in before.items():
        if key in keys:
            assert after[key].value == pytest.approx(original.value * factor)
            assert after[key].unit == original.unit
            assert after[key].reference_year == original.reference_year == 2021
            assert after[key].source == override(factor)["source"]
        else:
            assert after[key] == original
    for left in WACC_COMPONENTS:
        for right in WACC_COMPONENTS:
            a, b = f"technologies.{left}.real_wacc_fraction", f"technologies.{right}.real_wacc_fraction"
            assert after[a].value / after[b].value == pytest.approx(before[a].value / before[b].value)


@pytest.mark.parametrize("factor", [0., -1., float("nan"), float("inf"), True, None, 100.])
def test_invalid_multiplier_or_resulting_rate_is_rejected(factor):
    with pytest.raises(ValueError):
        apply_sensitivity_override(load_eu_site_configuration(EU_SITE_IDS[0]).config, override(factor))


def test_rate_equal_to_one_is_rejected():
    base = load_eu_site_configuration(EU_SITE_IDS[0]).config
    factor = 1 / base.technologies.electrolyzer.real_wacc_fraction.value
    with pytest.raises(ValueError):
        apply_sensitivity_override(base, override(factor))


@pytest.fixture(scope="module", params=EU_SITE_IDS)
def multiplier_results(tmp_path_factory, request):
    root = tmp_path_factory.mktemp("relative_financing_" + request.param)
    fixture = write_source(root / "source", request.param)
    write_cases(fixture["cases"], VARIANTS)
    baseline = run_h2_scenarios(fixture["source"], root / "accepted_baseline", **kwargs(fixture))
    assert validate_h2_results(baseline.output_directory, expected_hours=24).all_checks_passed
    base_hashes = {path: digest(path) for path in baseline.output_directory.rglob("*") if path.is_file()}
    results = sensitivity.run_h2_sensitivity(fixture["source"], fixture["cases"], root / "relative_financing",
        scenarios=SCENARIOS, reuse_baseline_directory=baseline.output_directory, **kwargs(fixture))
    assert all(digest(path) == value for path, value in base_hashes.items())
    fixture.update(root=root, artifacts=results)
    return fixture


def test_runner_exports_factors_effective_rates_and_independent_validation(multiplier_results):
    fixture = multiplier_results
    artifacts = fixture["artifacts"]
    comparison = pd.read_csv(artifacts.comparison_path)
    metadata = json.loads(artifacts.metadata_path.read_text(encoding="utf-8"))
    assert len(comparison) == 12
    assert metadata["number_of_optimization_runs"] == 9
    assert metadata["number_of_reused_baseline_runs"] == 3
    assert metadata["baseline_parameter_values"]["real_wacc_multiplier"] == 1
    base_frame = pd.read_csv(fixture["source"], dtype=str, keep_default_na=False)
    base_parameters = dict(iter_scalar_parameters(fixture["selected"].config))
    for case_id, _, factor, _ in VARIANTS:
        group = comparison.loc[comparison.case_id == case_id]
        assert group.parameter_operation.eq("multiply_all_five_real_wacc_rates").all()
        assert group.baseline_parameter_value.eq(1).all()
        assert group.parameter_change_percent.tolist() == pytest.approx([100 * (factor - 1)] * 3)
        child = artifacts.output_directory / "case_inputs" / (case_id + ".csv")
        child_frame = pd.read_csv(child, dtype=str, keep_default_na=False)
        assert child_frame.columns.tolist() == base_frame.columns.tolist()
        for column in base_frame.columns:
            if column == "timestamp":
                assert pd.to_datetime(child_frame[column], utc=True).equals(pd.to_datetime(base_frame[column], utc=True))
            elif column == "arbitrary_text":
                assert child_frame[column].equals(base_frame[column])
            else:
                np.testing.assert_allclose(pd.to_numeric(child_frame[column]), pd.to_numeric(base_frame[column]), rtol=1e-12, atol=1e-12)
        for scenario in SCENARIOS:
            info = json.loads(artifacts.runs[(case_id, scenario.value)].metadata_path.read_text(encoding="utf-8"))
            record = info["sensitivity_override"]
            assert record["operation"] == "multiply_all_five_real_wacc_rates"
            assert record["value"] == factor
            wacc = info["input"]["eu_site_configuration"]["wacc"]
            assert wacc["effective_rates_are_sensitivity_assumptions"] is True
            assert wacc["baseline_real_wacc_fraction_per_year"] == fixture["selected"].metadata["wacc"]["real_wacc_fraction_per_year"]
            for key, original in base_parameters.items():
                item = info["model_parameters"][key]
                expected = original.value * factor if key.endswith(".real_wacc_fraction") else original.value
                assert item["value"] == pytest.approx(expected)
                assert item["reference_year"] == original.reference_year
            for name in WACC_COMPONENTS:
                key = f"technologies.{name}.real_wacc_fraction"
                assert wacc["real_wacc_fraction_per_year"][name] == pytest.approx(base_parameters[key].value * factor)
        assert validate_case_group(artifacts, case_id, artifacts.output_directory / "runs" / case_id).all_checks_passed


@pytest.mark.parametrize("factor", [0., -1., 100.])
def test_entire_case_table_is_preflighted_before_first_solve(tmp_path, monkeypatch, factor):
    fixture = write_source(tmp_path / "source", EU_SITE_IDS[0])
    write_cases(fixture["cases"], (VARIANTS[0], ("invalid_late", "real_wacc_multiplier", factor, "factor")))
    def forbidden(*args, **call_kwargs):
        pytest.fail("Invalid later intervention must be rejected before every solve")
    monkeypatch.setattr(single, "optimize_hydrogen_system", forbidden)
    monkeypatch.setattr(sensitivity, "run_single_site_h2", forbidden)
    with pytest.raises(ValueError):
        sensitivity.run_h2_sensitivity(fixture["source"], fixture["cases"], tmp_path / "invalid", **kwargs(fixture))


@pytest.mark.parametrize("tampering", ["parent_csv", "parent_metadata", "baseline_hash", "forged_baseline_values", "record"])
def test_multiplier_source_receipt_forgery_fails_before_solver(tmp_path, monkeypatch, tampering):
    fixture = write_source(tmp_path / "source", EU_SITE_IDS[0])
    write_cases(fixture["cases"], (VARIANTS[0],))
    result = sensitivity.run_h2_sensitivity(fixture["source"], fixture["cases"], tmp_path / "initial",
        scenarios=(Scenario.REFERENCE,), **kwargs(fixture))
    child = result.output_directory / "case_inputs" / (VARIANTS[0][0] + ".csv")
    sidecar = child.with_suffix(".metadata.json")
    contract = json.loads(sidecar.read_text(encoding="utf-8"))
    snapshot = Path(contract["baseline_configuration"]["path"])
    if tampering in ("parent_csv", "parent_metadata"):
        target = fixture["source"] if tampering == "parent_csv" else fixture["contract"]
        target.write_bytes(target.read_bytes() + b"\n")
    elif tampering == "baseline_hash":
        contract["baseline_configuration"]["sha256"] = "0" * 64
    elif tampering == "forged_baseline_values":
        contents = json.loads(snapshot.read_text(encoding="utf-8"))
        contents["model_parameters"]["technologies.pv.real_wacc_fraction"]["value"] *= 2
        write_json(snapshot, contents)
        contract["baseline_configuration"]["sha256"] = digest(snapshot)
    else:
        contract["case_transformation"]["value"] = .5
    write_json(sidecar, contract)
    def forbidden(*args, **call_kwargs):
        pytest.fail("Source receipt forgery must be rejected before invoking optimizer")
    monkeypatch.setattr(single, "optimize_hydrogen_system", forbidden)
    with pytest.raises((ValueError, single.H2RunError)):
        single.run_single_site_h2(child, tmp_path / "forbidden", **{**kwargs(fixture),
            "emission_factor_metadata_path": sidecar}, sensitivity_override={
                "parameter": "real_wacc_multiplier", "value": FACTORS[0],
                "source": "Synthetic software test", "note": "Not a forecast"})
    assert not (tmp_path / "forbidden").exists()


@pytest.mark.parametrize("tampering", ["operation", "non_wacc", "effective_flag", "baseline_receipt", "source_receipt"])
def test_independent_export_validator_rejects_multiplier_forgery(multiplier_results, tmp_path, tampering):
    fixture = multiplier_results
    original = fixture["artifacts"].output_directory / "runs" / VARIANTS[0][0]
    copied = tmp_path / "group"
    shutil.copytree(original, copied)
    group = pd.read_csv(fixture["artifacts"].comparison_path)
    group = group.loc[group.case_id == VARIANTS[0][0]].copy()
    group["scenario_id"] = group.scenario.map({"reference": "S0", "red_monthly": "S1", "red_hourly": "S2"})
    group["result_directory"] = group.scenario
    group.to_csv(copied / "scenario_comparison.csv", index=False)
    path = copied / "reference" / "run_metadata.json"
    contents = json.loads(path.read_text(encoding="utf-8"))
    expected_check = "sensitivity_one_factor_configuration"
    if tampering == "operation":
        contents["sensitivity_override"]["operation"] = "add_to_all_five_real_wacc_rates"
    elif tampering == "non_wacc":
        contents["model_parameters"]["technologies.pv.capex_eur_per_kw"]["value"] *= 2
    elif tampering == "effective_flag":
        contents["input"]["eu_site_configuration"]["wacc"]["effective_rates_are_sensitivity_assumptions"] = False
    elif tampering == "baseline_receipt":
        contents["input"]["sensitivity_provenance"]["baseline_configuration"]["sha256"] = "0" * 64
    else:
        contents["input"]["sensitivity_provenance"]["parent_input"]["sha256"] = "0" * 64
        expected_check = "sensitivity_parent_input_contract"
    write_json(path, contents)
    validation = validate_h2_results(copied, expected_hours=24, output_directory=tmp_path / "validation")
    assert not validation.all_checks_passed
    checks = pd.read_csv(validation.checks_path)
    assert expected_check in set(checks.loc[~checks.passed, "check_id"])
