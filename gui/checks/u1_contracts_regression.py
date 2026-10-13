"""U1 reference and operation contracts; tiny native exports, no solver calls."""
import json
from pathlib import Path

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from gui.analysis_contracts import (prepare_oat_frame, parameter_presentation,
    native_contract_fields, controlled_scenario_defaults, comparison_design)


def synthetic(parameter, levels, *, base=None, relative=False):
    rows = []
    for scenario in ("S0", "S1", "S2"):
        common = dict(study_id="eu_2024", site_id="hamburg", scenario_id=scenario,
            demand_profile="D0", solver_name="scipy-highs", __collection_id="family-a",
            baseline_context_sha256="explicit-fixture-baseline", lcoh_eur_per_kg_h2=4.)
        rows.append({**common, "case_id": "baseline-" + scenario, "sensitivity_parameter": "baseline", "sensitivity_value": None})
        for index, level in enumerate(levels):
            row = {**common, "case_id": str(index) + "-" + scenario, "sensitivity_parameter": parameter,
                "sensitivity_value": level, "baseline_parameter_value": base}
            if relative:
                row["relative_level"] = level
            rows.append(row)
    return pd.DataFrame(rows)


@pytest.mark.parametrize("parameter,levels,base,expected", [
    ("real_wacc_multiplier", [.7, 1.4], None, [.7, 1., 1.4]),
    ("electrolyzer_capex_factor", [.75, 1.25], None, [.75, 1., 1.25]),
    ("electricity_price_offset_eur_per_mwh", [-38., 38.], 0, [-38., 0., 38.]),
    ("pv_capex_eur_per_kw", [690.75, 1151.25], 921., [690.75, 921., 1151.25]),
    ("uniform_real_wacc_fraction", [.07, .15], .11, [7., 11., 15.]),
    ("real_wacc_shift_fraction", [-.01, .01], 0., [-1., 0., 1.]),
])
def test_every_numeric_oat_uses_own_existing_native_basis(parameter, levels, base, expected):
    frame = synthetic(parameter, levels, base=base)
    before = frame.copy(deep=True)
    prepared = prepare_oat_frame(frame, parameter=parameter, metric="lcoh_eur_per_kg_h2")
    for _, curve in prepared.groupby("scenario_id"):
        assert list(curve.__plot_x) == pytest.approx(expected)
        assert curve.__oat_is_baseline.sum() == 1
        assert curve.__oat_reference_id.nunique() == 1
    assert set(prepared.case_id) == set(frame.case_id)
    assert_frame_equal(frame, before)
    assert_frame_equal(prepare_oat_frame(prepared, parameter=parameter), prepared)


def test_historical_price_family_name_cannot_mislabel_native_offset():
    frame = synthetic("electricity_price_eur_per_mwh", [.5, 1.5], base=1., relative=True)
    variants = frame.sensitivity_parameter.ne("baseline")
    frame.loc[variants, "parameter_operation"] = "add_to_hourly_price_profile"
    frame.loc[variants, "applied_parameter"] = "electricity_price_offset_eur_per_mwh"
    frame.loc[variants, "applied_value"] = [-38., 38.] * 3
    prepared = prepare_oat_frame(frame, parameter="electricity_price_eur_per_mwh")
    assert parameter_presentation(frame, "electricity_price_eur_per_mwh")["label"] == "Verschiebung der Preisreihe"
    assert "Jahresmittel" in prepared.attrs["xlabel"]
    assert "nicht" in prepared.attrs["note"]
    assert set(prepared.__plot_x) == {.5, 1., 1.5}
    assert set(prepared.sensitivity_parameter) == {"baseline", "electricity_price_eur_per_mwh"}


@pytest.mark.parametrize("failure", ["missing", "duplicate", "wrong_context", "mixed_family", "wrong_solver"])
def test_missing_ambiguous_or_foreign_reference_is_rejected(failure):
    frame = synthetic("pv_capex_eur_per_kw", [700., 1100.], base=921.)
    base = frame.sensitivity_parameter.eq("baseline")
    if failure == "missing":
        frame = frame.loc[~base]
    elif failure == "duplicate":
        frame = pd.concat([frame, frame.loc[base].iloc[[0]]], ignore_index=True)
    elif failure == "wrong_context":
        frame.loc[base, "baseline_context_sha256"] = "other-scientific-basis"
    elif failure == "mixed_family":
        frame.loc[frame.sensitivity_parameter.ne("baseline")].index
        frame.loc[1, "__collection_id"] = "foreign-family"
    elif failure == "wrong_solver":
        frame.loc[base, "solver_name"] = "gurobi"
    with pytest.raises(ValueError):
        prepare_oat_frame(frame, parameter="pv_capex_eur_per_kw")


def native_rows(root, parameter, *, actual_factor=1., declared_factor=1., price_offset=0., different_weather=False):
    baseline_input = pd.DataFrame({"timestamp": ["2024-01-01T00:00:00Z", "2024-01-01T01:00:00Z"],
        "electricity_price": [-10., 60.], "h2_demand": [0., 10.], "pv_yield": [.2, .4]})
    metadata = {"model_parameters": {"technologies.pv.capex_eur_per_kw": {"value": 921., "unit": "EUR/kW", "reference_year": 2023}},
        "model_calendar": {"temporal_correlation_timezone": "Europe/Berlin"}, "software": {"python": "fixture"},
        "input": {"sha256": "base-input"}}
    common = dict(study_id="eu", site_id="hamburg", scenario_id="S0", demand_profile="D0", solver_name="highs",
        __collection_id="native-family", lcoh_eur_per_kg_h2=4.)
    records = []
    for kind in ("baseline", "variant"):
        directory = root / "outputs_h2" / kind
        directory.mkdir(parents=True)
        data = baseline_input.copy()
        row = {**common, "case_id": kind, "__result_directory": str(directory),
            "sensitivity_parameter": "baseline" if kind == "baseline" else parameter,
            "sensitivity_value": None if kind == "baseline" else declared_factor if parameter == "h2_demand_multiplier" else price_offset}
        meta = json.loads(json.dumps(metadata))
        if kind == "variant":
            data.h2_demand *= actual_factor
            data.electricity_price += price_offset
            if different_weather:
                data.loc[0, "pv_yield"] = .9
            operation = "multiply_hourly_h2_demand_preserve_profile" if parameter == "h2_demand_multiplier" else "add_to_hourly_price_profile"
            value = declared_factor if parameter == "h2_demand_multiplier" else price_offset
            meta["input"]["sha256"] = "variant-input"
            meta["sensitivity_override"] = {"parameter": parameter, "value": value, "operation": operation, "changed_scalar_parameters": {}}
        data.to_csv(directory / "validated_input.csv", index=False)
        row.update(native_contract_fields(meta, row, directory, root))
        records.append(row)
    return pd.DataFrame(records)


def test_native_price_delta_is_checked_against_exact_own_input(tmp_path):
    frame = native_rows(tmp_path, "electricity_price_offset_eur_per_mwh", price_offset=-38.)
    result = prepare_oat_frame(frame, parameter="electricity_price_offset_eur_per_mwh")
    assert list(result.__plot_x) == [-38., 0.]
    assert result.__oat_is_baseline.sum() == 1


@pytest.mark.parametrize("parameter", ["h2_demand_multiplier", "electricity_price_offset_eur_per_mwh"])
def test_displayed_stage_must_match_actual_native_intervention(tmp_path, parameter):
    frame = native_rows(tmp_path, parameter, actual_factor=.5 if parameter == "h2_demand_multiplier" else 1.,
        declared_factor=.5, price_offset=-38. if parameter != "h2_demand_multiplier" else 0.)
    frame.loc[1, "sensitivity_value"] = .75 if parameter == "h2_demand_multiplier" else 38.
    with pytest.raises(ValueError):
        prepare_oat_frame(frame, parameter=parameter)


@pytest.mark.parametrize("failure", ["shape", "second_input_intervention", "config", "calendar", "software"])
def test_native_demand_rejects_wrong_factor_and_unrelated_interventions(tmp_path, failure):
    frame = native_rows(tmp_path, "h2_demand_multiplier", actual_factor=.6 if failure == "shape" else .5,
        declared_factor=.5, different_weather=failure == "second_input_intervention")
    column = {"config": "__baseline_configuration_sha256", "calendar": "__native_calendar_sha256", "software": "__native_software_sha256"}.get(failure)
    if column:
        frame.loc[1, column] = "different"
    with pytest.raises(ValueError):
        prepare_oat_frame(frame, parameter="h2_demand_multiplier")


def test_embedded_100_percent_demand_requires_same_native_configuration(tmp_path):
    frame = native_rows(tmp_path, "h2_demand_multiplier", actual_factor=.5, declared_factor=.5)
    frame.loc[0, "sensitivity_parameter"] = "h2_demand_multiplier"
    frame.loc[0, "sensitivity_value"] = 1.
    frame.loc[0, "__native_applied_value"] = 1.
    frame.loc[0, "__native_operation"] = "multiply_hourly_h2_demand_preserve_profile"
    frame.loc[0, "__native_configuration_sha256"] = "foreign-basis-config"
    with pytest.raises(ValueError, match="Basisstufe"):
        prepare_oat_frame(frame, parameter="h2_demand_multiplier")


def test_native_unchanged_baseline_mapped_to_demand_family_is_not_a_second_operation(tmp_path):
    frame = native_rows(tmp_path, "h2_demand_multiplier", actual_factor=.5, declared_factor=.5)
    frame.loc[0, "sensitivity_parameter"] = "h2_demand_multiplier"
    frame.loc[0, "sensitivity_value"] = 1.
    prepared = prepare_oat_frame(frame, parameter="h2_demand_multiplier")
    assert list(prepared.__plot_x) == [50., 100.]
    assert prepared.__oat_is_baseline.sum() == 1
    assert prepared.attrs["operation"] == "multiply_hourly_h2_demand_preserve_profile"


def test_explicit_embedded_demand_basis_is_kept_once_without_inventing_native_rows():
    frame = synthetic("h2_demand_multiplier", [.5, 1., 1.5])
    frame = frame.loc[frame.sensitivity_parameter.ne("baseline")]
    result = prepare_oat_frame(frame, parameter="h2_demand_multiplier")
    assert len(result) == 9
    assert result.__oat_is_baseline.sum() == 3
    assert set(result.__plot_x) == {50., 100., 150.}


def scenario_group():
    return pd.DataFrame([dict(study_id="eu", site_id="hamburg", demand_profile="D0", scenario_id=scenario,
        solver_name="highs", __analysis_id="saved-" + scenario, __bound_validation_passed=True,
        __native_input_sha256="input", __native_configuration_sha256="config", __native_calendar_sha256="calendar",
        __native_software_sha256="software") for scenario in ("S0", "S1", "S2")])


def test_controlled_defaults_require_input_and_configuration_and_bound_validation():
    frame = scenario_group()
    assert controlled_scenario_defaults(frame) == ["saved-S0", "saved-S1", "saved-S2"]
    assert comparison_design(frame).startswith("Kontrollierter Szenarienvergleich")
    frame.loc[1, "__native_configuration_sha256"] = "other-config"
    assert controlled_scenario_defaults(frame) == ["saved-S0"]
    assert comparison_design(frame).startswith("Deskriptive")
    frame = scenario_group()
    frame.loc[1, "__bound_validation_passed"] = False
    assert controlled_scenario_defaults(frame) == ["saved-S0"]


def test_plain_equal_cost_or_input_hash_cannot_prove_controlled_comparison():
    frame = scenario_group().drop(columns=["__native_configuration_sha256"])
    frame["input_sha256"] = "same"
    frame["lcoh_eur_per_kg_h2"] = 4.
    assert controlled_scenario_defaults(frame) == ["saved-S0"]
    assert comparison_design(frame).startswith("Deskriptive")
