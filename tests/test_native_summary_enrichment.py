"""Condensed tables receive missing native fields without altering their values."""
from pathlib import Path
import json
import os
import sys

import pandas as pd
import pytest

GUI_ROOT = Path(os.environ.get("H2_GUI_SOURCE_ROOT", Path(__file__).resolve().parents[1])).resolve()
ROOT = Path(os.environ.get("H2_MODEL_REPO", Path(__file__).resolve().parents[1])).resolve()
sys.path.insert(0, str(GUI_ROOT))
from gui.case_study_registry import load_registry
from gui.result_loader import _fill_missing_native_summaries, load_registered_results, load_sensitivity_comparisons


@pytest.fixture
def registry():
    return load_registry(ROOT)


def test_condensed_actual_case_receives_solver_fields_preserving_values(registry):
    original = load_registered_results(registry, "eu_2024", "hamburg_moorburg", "D0").iloc[[0]].copy()
    condensed = original.drop(columns=["solver_name", "solver_runtime_seconds", "optimality_gap_fraction"])
    # A pre-existing value (including zero) must not be replaced by native CSV.
    condensed["lcoh_eur_per_kg_h2"] = 0.0
    enriched = _fill_missing_native_summaries(condensed, ROOT)
    assert enriched.solver_name.iloc[0] == "scipy_highs"
    assert enriched.solver_runtime_seconds.iloc[0] == original.solver_runtime_seconds.iloc[0]
    assert enriched.optimality_gap_fraction.iloc[0] == original.optimality_gap_fraction.iloc[0]
    assert enriched.lcoh_eur_per_kg_h2.iloc[0] == 0.0
    for column in condensed:
        if column.startswith("__native_"):
            continue
        present = condensed[column].notna()
        pd.testing.assert_series_equal(enriched.loc[present, column], condensed.loc[present, column], check_dtype=False)
    assert Path(enriched.__native_summary_path.iloc[0]).name == "summary.csv"
    assert len(enriched.__native_summary_sha256.iloc[0]) == 64


def test_all_registered_tables_receive_exact_native_solver_identity(registry):
    for study, site in [("eu_2024", "hamburg_moorburg"), ("eu_2024", "huelva_la_rabida"), ("namibia", "namibia")]:
        for table in [load_registered_results(registry, study, site), load_sensitivity_comparisons(registry, study, site)]:
            assert table.solver_name.notna().all()
            for _, row in table.iterrows():
                source = pd.read_csv(Path(row["__result_directory"]) / "summary.csv").iloc[0]
                assert row.solver_name == source.solver_name
                assert row.lcoh_eur_per_kg_h2 == source.lcoh_eur_per_kg_h2


def test_missing_json_solver_fallback_and_no_invented_temporal_flag(tmp_path):
    case = tmp_path / "outputs_h2" / "case"
    case.mkdir(parents=True)
    pd.DataFrame([{"scenario": "reference", "lcoh_eur_per_kg_h2": 5.0, "red_iii_temporal_compliant": None}]).to_csv(case / "summary.csv", index=False)
    (case / "run_metadata.json").write_text(json.dumps({"result": {"solver_name": "fixture_solver", "solver_runtime_seconds": 2.0}}), encoding="utf-8")
    table = pd.DataFrame([{"scenario_id": "S0", "__result_directory": str(case), "lcoh_eur_per_kg_h2": 6.0, "solver_name": float("nan")}])
    result = _fill_missing_native_summaries(table, tmp_path)
    assert result.solver_name.iloc[0] == "fixture_solver"
    assert result.lcoh_eur_per_kg_h2.iloc[0] == 6.0
    assert pd.isna(result.get("red_iii_temporal_compliant", pd.Series([None])).iloc[0])


def test_mismatched_case_cannot_fill_other_scenario_fields(tmp_path):
    case = tmp_path / "outputs_h2" / "case"
    case.mkdir(parents=True)
    pd.DataFrame([{"scenario": "reference", "solver_name": "wrong_case_solver"}]).to_csv(case / "summary.csv", index=False)
    result = _fill_missing_native_summaries(pd.DataFrame([{"scenario_id": "S2", "__result_directory": str(case)}]), tmp_path)
    assert "solver_name" not in result


def test_enrichment_rejects_output_path_escape(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    pd.DataFrame([{"scenario": "reference", "solver_name": "outside_solver"}]).to_csv(outside / "summary.csv", index=False)
    result = _fill_missing_native_summaries(pd.DataFrame([{"scenario_id": "S0", "__result_directory": str(outside)}]), tmp_path)
    assert "solver_name" not in result
