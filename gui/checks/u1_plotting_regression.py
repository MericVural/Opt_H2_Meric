"""Scientific U1 contracts: native case/time exports and compatible references."""
import io
import subprocess

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal
import pytest

from gui import plotting
from gui.result_loader import ResultBundle


@pytest.fixture(autouse=True)
def saved_data_only(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Saved-result plotting must not invoke a solver/process")
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    yield
    plt.close("all")


def emission_cases():
    return pd.DataFrame({
        "scenario_id": ["S0", "S1", "S2"],
        "case_id": ["baseline", "baseline", "baseline"],
        "operational_emission_intensity_kg_co2e_per_kg_h2": [5., 3., 2.],
        "regulatory_emission_intensity_kg_co2e_per_kg_h2": [5., 0., 1e-11],
        "red_iii_maximum_product_intensity_kg_co2e_per_kg_h2": [3.384, 3.384, 3.384],
        "red_iii_maximum_product_intensity_g_co2e_per_mj": [28.2, 28.2, 28.2],
        "solver_runtime_seconds": [1., 2., 3.],
        "max_hydrogen_balance_residual_kg": [1e-8, 1e-8, 1e-8],
    })


def hourly_bundle():
    times = pd.date_range("2024-10-26T23:00:00Z", periods=5, freq="h")
    hourly = {}
    for index, sid in enumerate(("reference", "red_monthly"), start=1):
        count = len(times)
        hourly[sid] = pd.DataFrame({
            "timestamp": times, "pv_self_consumption_mwh": np.arange(count) * index,
            "wind_self_consumption_mwh": np.full(count, index * 2.),
            "grid_import_mwh": np.full(count, index * 3.),
            "rf_nbo_electricity_mwh": np.arange(count) * index + index * 5.,
            "h2_production_kg": np.arange(count) * index + 10.,
            "h2_demand_kg": np.full(count, index * 12.),
            "h2_storage_level_kg": np.arange(count) * index + 20.,
            "native_unused_diagnostic": np.arange(count) * index + 900.,
        })
    summary = pd.DataFrame({"scenario_id": ["S0", "S1"], "case_id": ["same_case", "same_case"],
                            "solver_name": ["scipy-highs", "scipy-highs"],
                            "input_sha256": ["input0", "input1"],
                            "__result_directory": ["C:/native/S0", "C:/native/S1"]})
    return ResultBundle(summary=summary, metadata={}, hourly=hourly)


def test_normal_metric_choices_keep_outcomes_and_separate_native_references_and_checks():
    frame = emission_cases()
    available = plotting.available_metrics(frame)
    assert "regulatory_emission_intensity_kg_co2e_per_kg_h2" in available
    assert not set(available).intersection(plotting.REFERENCE_METRICS | plotting.DIAGNOSTIC_METRICS)
    assert set(plotting.available_metrics(frame, roles="reference")) == plotting.REFERENCE_METRICS
    assert "solver_runtime_seconds" in plotting.available_metrics(frame, roles="diagnostic")
    assert set(plotting.METRIC_ROLES) == set(plotting.METRICS)
    with pytest.raises(ValueError, match="passenden Intensitätsachse"):
        plotting.comparison_figure(frame, metric="red_iii_maximum_product_intensity_g_co2e_per_mj")


def test_emission_reference_uses_native_matching_units_and_only_regulatory_axis():
    frame = emission_cases()
    before = frame.copy(deep=True)
    figure = plotting.emissions_figure(frame)
    operational, regulatory = figure.axes
    assert not any(line.get_linestyle() == "--" for line in operational.lines)
    limits = [line for line in regulatory.lines if line.get_linestyle() == "--"]
    assert len(limits) == 1
    assert list(limits[0].get_ydata()) == [3.384, 3.384]
    assert [bar.get_height() for bar in regulatory.patches] == [5., 0., 1e-11]
    assert any(line.get_marker() == "o" and list(line.get_ydata()) == [0.] for line in regulatory.lines)
    note = " ".join(figure.texts[-1].get_text().split())
    assert "gesamte Produktbilanz" in note and "allein belegt keine Einhaltung" in note
    assert_frame_equal(frame, before)


def test_distinct_or_missing_native_limits_are_never_averaged_or_invented():
    frame = emission_cases()
    field = "red_iii_maximum_product_intensity_kg_co2e_per_kg_h2"
    frame[field] = [3., 4., np.nan]
    figure = plotting.emissions_figure(frame)
    limits = [line for line in figure.axes[1].lines if line.get_linestyle() == "--"]
    assert [list(line.get_ydata()) for line in limits] == [[3., 3.], [4., 4.]]
    assert "1 von 3 Fällen fehlt" in figure.texts[-1].get_text()
    only_mj = frame.drop(columns=field)
    second = plotting.emissions_figure(only_mj)
    assert not any(line.get_linestyle() == "--" for line in second.axes[1].lines)
    assert "g CO₂e/MJ" in second.texts[-1].get_text()
    assert "nicht umgerechnet" in second.texts[-1].get_text()


def test_hourly_native_values_case_binding_plot_and_csv_are_identical_at_repeated_dst_hour():
    bundle = hourly_bundle()
    before = {sid: frame.copy(deep=True) for sid, frame in bundle.hourly.items()}
    frame = plotting.hourly_frame(bundle, start="2024-10-27T02:00:00+02:00", hours=3, timezone="Europe/Berlin")
    first = frame[frame.selection_scenario_id == "S0"]
    assert first.display_timestamp.dt.strftime("%H:%M %Z").tolist() == ["02:00 CEST", "02:00 CET", "03:00 CET"]
    assert first.selection_result_directory.eq("C:/native/S0").all()
    assert first.selection_input_sha256.eq("input0").all()
    assert first.selection_native_scenario_key.eq("reference").all()
    assert first.selection_hours.eq(3).all() and not first.selection_truncated.any()
    for sid, source in before.items():
        canonical = {"reference": "S0", "red_monthly": "S1"}[sid]
        selected = frame[frame.selection_scenario_id == canonical].reset_index(drop=True)
        assert_frame_equal(selected[list(source.columns)], source.iloc[1:4].reset_index(drop=True))
        assert_frame_equal(bundle.hourly[sid], source)
    figure = plotting.hourly_figure(frame, timezone="Europe/Berlin")
    # The second panel shows native kg as tonnes, including the final step
    # boundary. CSV stores the same selected native kg without conversions.
    assert list(figure.axes[1].lines[0].get_ydata())[:-1] == (first.h2_production_kg / 1000).tolist()
    assert list(figure.axes[2].lines[0].get_ydata()) == (first.h2_storage_level_kg / 1000).tolist()
    csv = pd.read_csv(io.StringIO(frame.to_csv(index=False)))
    assert csv.h2_production_kg.tolist() == frame.h2_production_kg.tolist()
    assert csv.native_unused_diagnostic.tolist() == frame.native_unused_diagnostic.tolist()
    assert csv.selection_result_directory.tolist() == frame.selection_result_directory.tolist()


def test_hourly_tail_reports_true_selected_period_and_shortened_native_export():
    bundle = hourly_bundle()
    frame = plotting.hourly_frame(bundle, start="2024-10-27T03:00:00+01:00", hours=168, timezone="Europe/Berlin")
    assert frame.selection_hours.eq(2).all() and frame.selection_truncated.all()
    assert frame.selection_requested_hours.eq(168).all()
    assert frame.selection_actual_end_utc.eq("2024-10-27T04:00:00+00:00").all()
    assert "2 von 168" in frame.selection_description.iloc[0]
    figure = plotting.hourly_figure(frame, timezone="Europe/Berlin")
    assert "2 von 168" in figure.texts[-1].get_text()


def test_hourly_ambiguous_summary_or_time_gap_cannot_connect_unrelated_data():
    bundle = hourly_bundle()
    bundle.summary = pd.concat([bundle.summary, bundle.summary.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="genau einen passenden Ergebnisfall"):
        plotting.hourly_frame(bundle, hours=3)
    bundle = hourly_bundle()
    bundle.hourly["reference"] = bundle.hourly["reference"].drop(index=2).reset_index(drop=True)
    with pytest.raises(ValueError, match="Zeitlücken"):
        plotting.hourly_frame(bundle, hours=5)


def test_duplicate_comparison_categories_explain_selection_without_aggregation():
    frame = pd.DataFrame({"scenario_id": ["S0", "S0", "S1"], "demand_profile": ["D0", "D0", "D0"],
                          "lcoh_eur_per_kg_h2": [4., 5., 6.]})
    with pytest.raises(ValueError, match="Fallauswahl eingrenzen"):
        plotting.comparison_figure(frame, chart_type="Gruppierte Balken", group_by="scenario_id")
