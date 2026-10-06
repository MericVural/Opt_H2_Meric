"""Group saved analyses conservatively without running or modifying the model."""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pandas as pd
import pytest


GUI_ROOT = Path(os.environ.get("H2_GUI_SOURCE_ROOT", Path(__file__).resolve().parents[2])).resolve()
MODEL_ROOT = Path(os.environ.get("H2_MODEL_REPO", os.environ.get("H2_REPO_ROOT", "C:/Forschungsarbeit/Opt_H2_Meric-h2"))).resolve()
sys.path.insert(0, str(GUI_ROOT))
if str(MODEL_ROOT) not in sys.path:
    sys.path.append(str(MODEL_ROOT))

from gui.result_duplicates import collapse_duplicate_results, collapse_duplicate_sensitivity_collections


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, sort_keys=True, allow_nan=False), encoding="utf-8")


@pytest.fixture(autouse=True)
def prohibit_processes(monkeypatch):
    def prohibited(*args, **kwargs):
        pytest.fail("Reading and grouping saved exports must not launch a process")

    monkeypatch.setattr(subprocess, "run", prohibited)
    monkeypatch.setattr(subprocess, "Popen", prohibited)


@pytest.fixture
def saved_case(tmp_path):
    """Two-hour native exports: explicit scientific contracts, no optimization."""
    code = tmp_path / "opt_hydrogen_functions.py"
    code.write_text("# Static synthetic model implementation receipt.\n", encoding="utf-8")

    def make(name, *, parameter=1000.0, scenario="reference", solver="scipy_highs", year=2024,
             input_value=10.0, hourly_value=1.0, software="1.17.1", runtime=1.0):
        directory = tmp_path / "outputs_h2" / name
        directory.mkdir(parents=True)
        inputs = pd.DataFrame({
            "timestamp": ["2024-01-01T00:00:00Z", "2024-01-01T01:00:00Z"],
            "electricity_price": [input_value, 20.0], "h2_demand": [100.0, 100.0],
        })
        inputs.to_csv(directory / "validated_input.csv", index=False)
        input_hash = digest(directory / "validated_input.csv")
        pd.DataFrame({
            "timestamp": inputs.timestamp, "grid_import_mwh": [hourly_value, 2.0],
            "h2_delivered_kg": [100.0, 100.0],
        }).to_csv(directory / "hourly_operation.csv", index=False)
        native = {
            "scenario": scenario, "input_sha256": input_hash, "input_file": str(directory / "validated_input.csv"),
            "solver_status": "optimal", "solver_name": solver, "solver_runtime_seconds": runtime,
            "optimality_gap_fraction": 0.0, "objective_eur_per_year": 1000.0,
            "lcoh_eur_per_kg_h2": 5.0, "annual_h2_delivered_kg": 200.0,
            "pv_capacity_mw": 1.0, "wind_capacity_mw": 2.0, "electrolyzer_capacity_mw": 3.0,
            "compressor_capacity_mw": 0.2, "h2_storage_capacity_kg": 100.0,
            "number_of_hours": 2, "annualization_factor": 1.0,
        }
        pd.DataFrame([native]).to_csv(directory / "summary.csv", index=False)
        metadata = {
            "schema_version": "1.2", "created_at_utc": f"2026-10-05T00:00:{int(runtime):02d}Z",
            "scenario": scenario,
            "input": {"source_path": str(directory / "validated_input.csv"), "sha256": input_hash,
                      "number_of_hours": 2, "time_zone": "UTC", "frequency": "1h"},
            "model_parameters": {"technologies.pv.capex_eur_per_kw": {
                "value": parameter, "unit": "EUR_2023/kW", "reference_year": 2023,
                "source": "Explicit synthetic scientific test contract",
            }},
            "calendar_scope": {"historical_year": year, "calendar_timezone": "Europe/Berlin", "price_year": 2023},
            "model_calendar": {"operation_year": year, "number_of_hours": 2, "time_step_hours": 1.0},
            "software": {"python": "3.11.15", "pandas": "3.0.5", "scipy": software},
            "result": {key: value for key, value in native.items() if key not in ("input_file", "input_sha256", "scenario")},
        }
        write_json(directory / "run_metadata.json", metadata)
        source_csv = directory.parent / (directory.name + "_comparison.csv")
        pd.DataFrame([native]).to_csv(source_csv, index=False)
        row = {
            **native, "scenario_id": {"reference": "S0", "red_monthly": "S1", "red_hourly": "S2"}[scenario],
            "study_id": "eu_2024", "site_id": "hamburg_moorburg", "profile": "D0", "demand_profile": "D0",
            "case_id": "baseline", "__result_directory": str(directory), "__collection": name,
            "__source_csv": str(source_csv), "__source_csv_sha256": digest(source_csv), "source_label": name,
        }
        return row

    return make


def copies(row) -> list[dict]:
    records = json.loads(row["__result_copies"])
    assert isinstance(records, list)
    return records


def test_identical_analyses_keep_every_source_and_original_export(saved_case, tmp_path):
    first = saved_case("registered", runtime=1)
    second = saved_case("copied", runtime=9)
    alias_source = tmp_path / "outputs_h2" / "demand_comparison.csv"
    alias_source.write_bytes(Path(first["__source_csv"]).read_bytes())
    alias = {**first, "__collection": "Demand comparison", "source_label": "Another registered source",
             "__source_csv": str(alias_source), "__source_csv_sha256": digest(alias_source)}
    frame = pd.DataFrame([first, second, alias])
    original = frame.copy(deep=True)
    paths = sorted((tmp_path / "outputs_h2").rglob("*"))
    before = {str(path): digest(path) for path in paths if path.is_file()}

    collapsed = collapse_duplicate_results(frame, tmp_path)

    assert len(collapsed) == 1
    selected = collapsed.iloc[0]
    assert selected["__execution_count"] == 2
    assert selected["__source_count"] == 3
    assert selected["__analysis_id"]
    records = copies(selected)
    assert len(records) == 3
    assert {record["__result_directory"] for record in records} == {first["__result_directory"], second["__result_directory"]}
    assert {record["source_label"] for record in records} == {"registered", "copied", "Another registered source"}
    for record in records:
        assert record["__source_csv_sha256"] == digest(Path(record["__source_csv"]))
        receipt = record["native_metadata"]
        assert receipt["sha256"] == digest(Path(receipt["path"]))
    pd.testing.assert_frame_equal(frame, original)
    assert before == {str(path): digest(path) for path in paths if path.is_file()}


def test_semantic_group_and_representative_are_stable_under_discovery_order(saved_case, tmp_path):
    frame = pd.DataFrame([saved_case("z_copy", runtime=8), saved_case("a_original", runtime=1)])
    forward = collapse_duplicate_results(frame, tmp_path)
    reverse = collapse_duplicate_results(frame.iloc[::-1].reset_index(drop=True), tmp_path)
    assert len(forward) == len(reverse) == 1
    for column in ("__analysis_id", "__result_directory", "__execution_count", "__source_count", "__result_copies"):
        assert forward.iloc[0][column] == reverse.iloc[0][column]


def test_bound_validation_selects_representative_without_erasing_failed_evidence(saved_case, tmp_path):
    stale = saved_case("a_stale_job_status", runtime=1)
    valid = saved_case("z_validated_export", runtime=2)
    # A saved job's optimistic status does not supersede the bound report.
    stale.update(gui_job_state="completed", gui_validation_status="passed")
    receipts = {
        stale["__result_directory"]: {"status": "failed_or_changed", "covers_selected_result": True,
                                     "source_comparison_hash_matches": False},
        valid["__result_directory"]: {"status": "passed", "covers_selected_result": True,
                                     "source_comparison_hash_matches": True},
    }

    collapsed = collapse_duplicate_results(pd.DataFrame([stale, valid]), tmp_path,
                                           validation_lookup=lambda path: copy.deepcopy(receipts[str(path)]))

    assert len(collapsed) == 1
    selected = collapsed.iloc[0]
    assert selected["__result_directory"] == valid["__result_directory"]
    evidence = {record["__result_directory"]: record for record in copies(selected)}
    assert evidence[stale["__result_directory"]]["gui_validation_status"] == "passed"
    assert evidence[stale["__result_directory"]]["validation_evidence"]["status"] == "failed_or_changed"
    assert evidence[valid["__result_directory"]]["validation_evidence"]["status"] == "passed"


@pytest.mark.parametrize("difference", [
    {"input_value": 99.0}, {"solver": "gurobi"}, {"year": 2025}, {"parameter": 1250.0},
    {"hourly_value": 7.0}, {"software": "1.18.0"}, {"scenario": "red_hourly"},
])
def test_scientific_differences_stay_distinct_even_with_identical_lcoh(saved_case, tmp_path, difference):
    frame = pd.DataFrame([saved_case("first"), saved_case("different", **difference)])
    assert frame.lcoh_eur_per_kg_h2.nunique() == 1
    collapsed = collapse_duplicate_results(frame, tmp_path)
    assert len(collapsed) == 2
    assert collapsed["__analysis_id"].nunique() == 2
    assert collapsed["__execution_count"].tolist() == [1, 1]


@pytest.mark.parametrize("missing", ["summary.csv", "run_metadata.json", "validated_input.csv", "hourly_operation.csv"])
def test_incomplete_export_cannot_prove_equivalence_at_another_path(saved_case, tmp_path, missing):
    complete = saved_case("complete")
    partial = saved_case("partial")
    (Path(partial["__result_directory"]) / missing).unlink()
    collapsed = collapse_duplicate_results(pd.DataFrame([complete, partial]), tmp_path)
    assert len(collapsed) == 2
    assert set(collapsed["__result_directory"]) == {complete["__result_directory"], partial["__result_directory"]}


def test_repeated_reference_to_same_incomplete_export_is_one_execution(saved_case, tmp_path):
    first = saved_case("partial")
    (Path(first["__result_directory"]) / "hourly_operation.csv").unlink()
    alias_source = tmp_path / "outputs_h2" / "second_comparison.csv"
    alias_source.write_bytes(Path(first["__source_csv"]).read_bytes())
    second = {**first, "__collection": "Second source", "source_label": "Second source",
              "__source_csv": str(alias_source), "__source_csv_sha256": digest(alias_source)}
    collapsed = collapse_duplicate_results(pd.DataFrame([first, second]), tmp_path)
    assert len(collapsed) == 1
    assert collapsed.iloc[0]["__execution_count"] == 1
    assert collapsed.iloc[0]["__source_count"] == 2


@pytest.mark.parametrize("context", [
    {"scenario_id": "S2", "scenario": "red_hourly"},
    {"profile": "D1", "demand_profile": "D1"},
    {"site_id": "another_site"},
    {"solver_name": "gurobi"},
    {"parameter": "pv_capex_eur_per_kw", "sensitivity_parameter": "pv_capex_eur_per_kw", "value": 1250.0},
])
def test_shared_export_directory_does_not_merge_different_scientific_contexts(saved_case, tmp_path, context):
    first = saved_case("shared_comparison_directory")
    second = {**first, **context}
    # Older comparison tables may reference their common parent export folder.
    # Sharing that location cannot establish that the table rows are one case.
    collapsed = collapse_duplicate_results(pd.DataFrame([first, second]), tmp_path)
    assert len(collapsed) == 2
    assert collapsed["__analysis_id"].nunique() == 2
    assert collapsed["__result_directory"].nunique() == 1


def collection(saved_case, tmp_path, name, variants):
    rows = []
    source = tmp_path / "outputs_h2" / name / "sensitivity_comparison.csv"
    for case_id, parameter in variants:
        row = saved_case(name + "/" + case_id, parameter=parameter)
        row.update(case_id=case_id, parameter="pv_capex_eur_per_kw", sensitivity_parameter="pv_capex_eur_per_kw",
                   value=parameter, __collection=name, __source_csv=str(source), source_label=name)
        rows.append(row)
    pd.DataFrame(rows).to_csv(source, index=False)
    for row in rows:
        row["__source_csv_sha256"] = digest(source)
    return rows


def test_identical_complete_sensitivity_collections_collapse_as_a_whole(saved_case, tmp_path):
    variants = [("low", 750.0), ("high", 1250.0)]
    original = collection(saved_case, tmp_path, "original_curve", variants)
    repeated = collection(saved_case, tmp_path, "repeated_curve", [("low_copy", 750.0), ("high_copy", 1250.0)])
    frame = pd.DataFrame(original + repeated)
    collapsed = collapse_duplicate_sensitivity_collections(frame, tmp_path)
    reverse = collapse_duplicate_sensitivity_collections(frame.iloc[::-1].reset_index(drop=True), tmp_path)
    assert len(collapsed) == 2
    assert collapsed["__collection"].nunique() == 1
    assert set(collapsed.value) == {750.0, 1250.0}
    assert set(collapsed["__execution_count"]) == {2}
    assert set(collapsed["__source_count"]) == {2}
    assert set(collapsed["__analysis_id"]) == set(reverse["__analysis_id"])
    assert set(collapsed["__result_directory"]) == set(reverse["__result_directory"])
    retained = [record for _, row in collapsed.iterrows() for record in copies(row)]
    assert {record["__result_directory"] for record in retained} == {row["__result_directory"] for row in original + repeated}
    assert {record["__collection"] for record in retained} == {"original_curve", "repeated_curve"}
    assert {record["case_id"] for record in retained} == {"low", "high", "low_copy", "high_copy"}


def test_partial_sensitivity_overlap_preserves_both_complete_curves(saved_case, tmp_path):
    original = collection(saved_case, tmp_path, "first_curve", [("low", 750.0), ("high", 1250.0)])
    overlapping = collection(saved_case, tmp_path, "other_curve", [("low", 750.0), ("extra", 1500.0)])
    collapsed = collapse_duplicate_sensitivity_collections(pd.DataFrame(original + overlapping), tmp_path)
    assert len(collapsed) == 4
    assert set(collapsed.loc[collapsed["__collection"] == "first_curve", "case_id"]) == {"low", "high"}
    assert set(collapsed.loc[collapsed["__collection"] == "other_curve", "case_id"]) == {"low", "extra"}
    assert set(collapsed["__result_directory"]) == {row["__result_directory"] for row in original + overlapping}


def test_empty_results_are_safe_without_native_exports(tmp_path):
    frame = pd.DataFrame(columns=["__result_directory", "scenario_id", "profile"])
    assert collapse_duplicate_results(frame, tmp_path).empty
    assert collapse_duplicate_sensitivity_collections(frame, tmp_path).empty
