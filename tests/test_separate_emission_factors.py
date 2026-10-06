"""Synthetic short-period cases: factor separation must not change dispatch."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from h2_input_data import HourlyInputError, validate_hourly_input
from opt_hydrogen_functions import optimize_hydrogen_system
from run_h2_scenarios import main as scenarios_main, run_h2_scenarios
from run_h2_sensitivity import run_h2_sensitivity
from run_single_site_h2 import H2RunError, run_single_site_h2
from validate_h2_results import validate_h2_results


def _sources() -> dict:
    """These are explicitly synthetic test sources, not published factors."""
    return {
        role: {
            "source_description": f"Synthetic {role} factor fixture; no empirical data",
            "reference_year": 2025,
            "spatial_scope": "synthetic_test_system",
            "unit": "kg_CO2e/MWh",
            "emissions_basis": "synthetic_direct_CO2e" if role == "operational"
                               else "synthetic_regulatory_CO2e",
        }
        for role in ("operational", "regulatory")
    }


def _case(*, separate: bool = True, pv: float = 0.0) -> pd.DataFrame:
    frame = pd.DataFrame({
        "timestamp": pd.date_range("2025-01-01", periods=24, freq="h", tz="UTC"),
        "pv_capacity_factor": np.full(24, pv),
        "wind_capacity_factor": np.zeros(24),
        "electricity_price": np.zeros(24),
        "grid_emission_factor": np.linspace(250.0, 480.0, 24),
        "h2_demand": np.full(24, 100.0),
    })
    if separate:
        frame["regulatory_grid_emission_factor"] = np.linspace(50.0, 96.0, 24)
        frame.attrs["emission_factor_sources"] = _sources()
    return frame


def _write_contract(directory: Path, frame: pd.DataFrame) -> tuple[Path, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    input_path, metadata_path = directory / "input.csv", directory / "factors.json"
    frame.to_csv(input_path, index=False)
    metadata_path.write_text(json.dumps({
        "schema_version": "1.0",
        "input_sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
        "emission_factor_mode": "explicit_separate_factors",
        "emission_factor_sources": frame.attrs["emission_factor_sources"],
    }), encoding="utf-8")
    return input_path, metadata_path


@pytest.mark.parametrize("backend", ["gurobi", "scipy_highs"])
def test_distinct_factors_keep_identical_dispatch_and_cost(backend: str) -> None:
    legacy = optimize_hydrogen_system(_case(separate=False), solver_backend=backend)
    separate = optimize_hydrogen_system(
        _case(), solver_backend=backend, require_separate_emission_factors=True
    )
    assert separate.objective_eur_per_year == pytest.approx(legacy.objective_eur_per_year)
    assert separate.lcoh_eur_per_kg_h2 == pytest.approx(legacy.lcoh_eur_per_kg_h2)
    assert separate.capacities == pytest.approx(legacy.capacities)
    pd.testing.assert_series_equal(
        separate.hourly_operation["grid_import_mwh"], legacy.hourly_operation["grid_import_mwh"]
    )
    assert separate.annual_grid_emissions_kg_co2e == pytest.approx(legacy.annual_grid_emissions_kg_co2e)
    assert separate.annual_regulatory_emissions_kg_co2e == pytest.approx(
        separate.annual_grid_emissions_kg_co2e / 5.0
    )
    assert legacy.annual_regulatory_emissions_kg_co2e == pytest.approx(legacy.annual_grid_emissions_kg_co2e)
    assert separate.hourly_operation.attrs["emission_factor_mode"] == "explicit_separate_factors"
    assert legacy.hourly_operation.attrs["emission_factor_mode"] == "legacy_shared_factor"


def test_validated_sources_are_preserved_without_aliasing_the_raw_frame() -> None:
    frame = _case()
    result = validate_hourly_input(frame, require_separate_emission_factors=True)
    assert result.attrs["emission_factor_sources"] == frame.attrs["emission_factor_sources"]
    assert result.attrs["column_units"]["regulatory_grid_emission_factor"] == "kg_CO2e/MWh"
    result.attrs["emission_factor_sources"]["operational"]["source_description"] = "Changed"
    assert "Synthetic" in frame.attrs["emission_factor_sources"]["operational"]["source_description"]


def test_explicit_mode_rejects_absent_regulatory_factor() -> None:
    with pytest.raises(HourlyInputError, match="regulatory_grid_emission_factor fehlt"):
        validate_hourly_input(_case(separate=False), require_separate_emission_factors=True)


@pytest.mark.parametrize("bad_value", [np.nan, np.inf, -1.0])
def test_invalid_regulatory_factor_is_rejected(bad_value: float) -> None:
    frame = _case()
    frame.loc[1, "regulatory_grid_emission_factor"] = bad_value
    with pytest.raises(HourlyInputError):
        validate_hourly_input(frame)


@pytest.mark.parametrize("key", ["source_description", "reference_year", "spatial_scope", "unit", "emissions_basis"])
@pytest.mark.parametrize("role", ["operational", "regulatory"])
def test_each_factor_requires_its_own_documented_basis(role: str, key: str) -> None:
    frame = _case()
    del frame.attrs["emission_factor_sources"][role][key]
    with pytest.raises(HourlyInputError, match=f"{role}.{key}"):
        validate_hourly_input(frame)


def test_separate_column_does_not_silently_accept_missing_sources() -> None:
    frame = _case()
    frame.attrs.clear()
    with pytest.raises(HourlyInputError, match="emission_factor_sources"):
        validate_hourly_input(frame)


def test_legacy_mode_cannot_override_a_separate_column() -> None:
    frame = _case()
    frame.attrs["emission_factor_mode"] = "legacy_shared_factor"
    with pytest.raises(HourlyInputError, match="widerspricht"):
        validate_hourly_input(frame)


def test_runner_exports_both_sources_and_bound_metadata_hash(tmp_path: Path) -> None:
    input_path, contract_path = _write_contract(tmp_path, _case())
    result = run_single_site_h2(
        input_path, tmp_path / "results", solver_backend="scipy-highs",
        emission_factor_metadata_path=contract_path, require_separate_emission_factors=True,
    )
    metadata = json.loads(result.metadata_path.read_text(encoding="utf-8"))
    assert metadata["input"]["emission_factor_mode"] == "explicit_separate_factors"
    assert metadata["input"]["legacy_shared_factor"] is False
    assert metadata["input"]["emission_factor_sources"] == _sources()
    assert metadata["input"]["emission_factor_metadata"]["sha256"] == hashlib.sha256(contract_path.read_bytes()).hexdigest()
    operation = pd.read_csv(result.hourly_operation_path)
    np.testing.assert_allclose(operation["regulatory_grid_emission_factor_kg_co2e_per_mwh"], np.linspace(50, 96, 24))


def test_runner_blocks_legacy_eu_mode_before_calling_solver(tmp_path: Path, monkeypatch) -> None:
    import run_single_site_h2 as runner
    input_path = tmp_path / "input.csv"
    _case(separate=False).to_csv(input_path, index=False)

    def forbidden_solve(*args, **kwargs):
        pytest.fail("Solver must not run with an absent required factor")

    monkeypatch.setattr(runner, "optimize_hydrogen_system", forbidden_solve)
    with pytest.raises(HourlyInputError, match="Getrennte Emissionsfaktoren"):
        run_single_site_h2(input_path, tmp_path / "results", require_separate_emission_factors=True)
    assert not (tmp_path / "results").exists()


def test_runner_rejects_a_contract_for_different_csv_bytes(tmp_path: Path) -> None:
    input_path, contract_path = _write_contract(tmp_path, _case())
    input_path.write_bytes(input_path.read_bytes() + b"\n")
    with pytest.raises(H2RunError, match="Hash"):
        run_single_site_h2(input_path, tmp_path / "results", emission_factor_metadata_path=contract_path)


def _export_synthetic_scenarios(directory: Path) -> Path:
    input_path, contract_path = _write_contract(directory / "source", _case(pv=1.0))
    root = directory / "scenarios"
    artifacts = run_h2_scenarios(
        input_path, root, solver_backend="scipy-highs",
        emission_factor_metadata_path=contract_path, require_separate_emission_factors=True,
    )
    metadata = json.loads(artifacts.metadata_path.read_text(encoding="utf-8"))
    assert metadata["input"]["emission_factor_mode"] == "explicit_separate_factors"
    assert metadata["input"]["emission_factor_sources"] == _sources()
    return root


def test_independent_validator_accepts_separation_and_rejects_swapped_exports(tmp_path: Path) -> None:
    root = _export_synthetic_scenarios(tmp_path)
    valid = validate_h2_results(root, expected_hours=24)
    assert valid.all_checks_passed is True
    path = root / "S0_reference" / "hourly_operation.csv"
    frame = pd.read_csv(path)
    operational = frame["grid_emission_factor_kg_co2e_per_mwh"].copy()
    frame["grid_emission_factor_kg_co2e_per_mwh"] = frame["regulatory_grid_emission_factor_kg_co2e_per_mwh"]
    frame["regulatory_grid_emission_factor_kg_co2e_per_mwh"] = operational
    frame.to_csv(path, index=False)
    invalid = validate_h2_results(root, expected_hours=24, output_directory=tmp_path / "tampered_validation")
    assert invalid.all_checks_passed is False
    checks = pd.read_csv(invalid.checks_path)
    failed = set(checks.loc[~checks["passed"], "check_id"])
    assert {"operational_factor_matches_input", "regulatory_factor_matches_input"} <= failed


def test_independent_validator_rejects_missing_separate_source_documentation(tmp_path: Path) -> None:
    root = _export_synthetic_scenarios(tmp_path)
    path = root / "S0_reference" / "run_metadata.json"
    metadata = json.loads(path.read_text(encoding="utf-8"))
    del metadata["input"]["emission_factor_sources"]["regulatory"]
    path.write_text(json.dumps(metadata), encoding="utf-8")
    result = validate_h2_results(root, expected_hours=24)
    assert result.all_checks_passed is False
    checks = pd.read_csv(result.checks_path)
    assert "emission_factor_sources_documented" in set(checks.loc[~checks["passed"], "check_id"])


def test_scenarios_cli_passes_the_same_factor_contract_to_all_runs(tmp_path: Path) -> None:
    input_path, contract_path = _write_contract(tmp_path / "source", _case(pv=1.0))
    output = tmp_path / "results"
    assert scenarios_main([
        "--input", str(input_path), "--output-dir", str(output), "--solver", "scipy-highs",
        "--emission-factor-metadata", str(contract_path), "--require-separate-emission-factors",
    ]) == 0
    contract_hashes = []
    for directory in ("S0_reference", "S1_red_monthly", "S2_red_hourly"):
        metadata = json.loads((output / directory / "run_metadata.json").read_text(encoding="utf-8"))
        assert metadata["input"]["legacy_shared_factor"] is False
        contract_hashes.append(metadata["input"]["emission_factor_metadata"]["sha256"])
    assert len(set(contract_hashes)) == 1


def test_scenarios_reject_missing_required_factor_before_creating_outputs(tmp_path: Path, monkeypatch) -> None:
    import run_h2_scenarios as runner
    input_path = tmp_path / "input.csv"
    _case(separate=False).to_csv(input_path, index=False)

    def forbidden_solve(*args, **kwargs):
        pytest.fail("No scenario may solve with an absent required factor")

    monkeypatch.setattr(runner, "run_single_site_h2", forbidden_solve)
    with pytest.raises(HourlyInputError, match="Getrennte Emissionsfaktoren"):
        run_h2_scenarios(input_path, tmp_path / "results", require_separate_emission_factors=True)
    assert not (tmp_path / "results").exists()


def test_sensitivity_runner_clearly_rejects_unsupported_separate_contracts(tmp_path: Path) -> None:
    input_path, _ = _write_contract(tmp_path / "source", _case())
    cases = tmp_path / "cases.csv"
    pd.DataFrame([{
        "case_id": "baseline", "parameter": "baseline", "level": "base", "label": "Synthetic baseline",
        "value": "", "unit": "-", "source": "Synthetic test fixture", "note": "",
    }]).to_csv(cases, index=False)
    with pytest.raises(H2RunError, match="eigenen SHA256-gebundenen"):
        run_h2_sensitivity(input_path, cases, tmp_path / "results")
    assert not (tmp_path / "results").exists()
