"""Scientific GUI figures: explicit cases, readable labels and unchanged values."""
import io

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from gui import plotting
from plot_h2_results import COST_COMPONENTS, SCENARIO_COLORS


def result_frame():
    rows = []
    for profile in ("D0", "D1", "D2"):
        for index, scenario in enumerate(("S0", "S1", "S2")):
            row = {"site_id": "hamburg_moorburg", "site_label": "Hamburg-Moorburg · eine sehr lange Quellen- und Laufbeschreibung",
                   "scenario_id": scenario, "demand_profile": profile, "profile": profile,
                   "solver_name": "scipy-highs", "case_id": "baseline", "case_label": "Unveränderter wissenschaftlicher Basisfall",
                   "__result_directory": "C:/native/"+profile+"/"+scenario,
                   "lcoh_eur_per_kg_h2": 4.+index+int(profile[1])*.1,
                   "annual_h2_delivered_kg": 3_650_000., "objective_eur_per_year": (4.+index)*3_650_000,
                   "pv_capacity_mw": 10.+index, "wind_capacity_mw": 20.+index,
                   "electrolyzer_capacity_mw": 30.+index, "compressor_capacity_mw": .5+index*.1,
                   "h2_storage_capacity_kg": 1000.+index*100,
                   "operational_emission_intensity_kg_co2e_per_kg_h2": 6.-index,
                   "regulatory_emission_intensity_kg_co2e_per_kg_h2": 7. if index==0 else 0.}
            for _, _, columns, _ in COST_COMPONENTS:
                for column in columns:
                    row[column] = 1_000_000. if column!="grid_electricity_eur_per_year" else -250_000.
            rows.append(row)
    return pd.DataFrame(rows)


def demand_frame():
    rows = []
    for scenario in ("S0", "S1", "S2"):
        for factor in (.5, .75, 1., 1.25, 1.5):
            rows.append({"site_label": "Hamburg", "scenario_id": scenario, "demand_profile": "D1",
                         "solver_name": "scipy-highs", "sensitivity_parameter": "h2_demand_multiplier",
                         "sensitivity_value": factor, "lcoh_eur_per_kg_h2": 4.+int(scenario[1]),
                         "annual_h2_delivered_kg": factor*3_650_000.,
                         "objective_eur_per_year": factor*3_650_000.*(4.+int(scenario[1])),
                         "__collection": "Gebundene Versuchsreihe"})
    return pd.DataFrame(rows)


@pytest.fixture(autouse=True)
def close_figures():
    yield
    plt.close("all")


@pytest.mark.parametrize("chart_type", ["Balkendiagramm", "Liniendiagramm", "Gruppierte Balken"])
def test_explicit_comparison_has_one_selected_metric_and_preserves_exports(chart_type):
    frame=result_frame(); before=frame.copy(deep=True)
    figure=plotting.comparison_figure(frame, metric="pv_capacity_mw", chart_type=chart_type, group_by="scenario_id")
    assert len(figure.axes)==1
    assert figure.axes[0].get_ylabel()=="PV-Leistung [MW]"
    assert_frame_equal(frame,before)
    buffer=io.BytesIO();figure.savefig(buffer, format="png", dpi=100)
    assert buffer.getvalue().startswith(b"\x89PNG")
    svg=io.BytesIO();figure.savefig(svg,format="svg")
    assert b"<svg" in svg.getvalue()


def test_case_mapping_retains_unabbreviated_context_for_every_short_label():
    frame=result_frame(); mapping=plotting.case_label_table(frame)
    assert mapping.Diagrammfall.tolist()==[f"F{i:02d}" for i in range(1,10)]
    assert mapping.Standort.tolist()==frame.site_label.tolist()
    assert mapping.Ergebnisordner.tolist()==frame["__result_directory"].tolist()
    figure=plotting.comparison_figure(frame)
    labels=figure.axes[0].get_xticklabels()
    assert all(label.get_text().startswith("F") and len(label.get_text())<=5 for label in labels)
    assert all(label.get_rotation()==28 for label in labels)
    figure.canvas.draw();renderer=figure.canvas.get_renderer()
    rectangles=[label.get_window_extent(renderer) for label in labels]
    assert all(not left.overlaps(right) for left,right in zip(rectangles,rectangles[1:]))


def test_every_requested_case_is_shown_without_averaging_or_truncation():
    frame=result_frame(); figure=plotting.comparison_figure(frame)
    assert [bar.get_height() for bar in figure.axes[0].patches]==frame.lcoh_eur_per_kg_h2.tolist()
    oversized=pd.concat([frame,frame.iloc[:4]],ignore_index=True)
    with pytest.raises(ValueError,match="höchstens 12 Fälle"):
        plotting.comparison_figure(oversized)


@pytest.mark.parametrize("chart_type", ["Gruppierte Balken", "Liniendiagramm"])
def test_categorical_profile_sensitivity_keeps_d0_d1_d2_and_native_scenario_colors(chart_type):
    frame=result_frame();figure=plotting.profile_comparison_figure(frame,chart_type=chart_type)
    ax=figure.axes[0]
    assert [tick.get_text() for tick in ax.get_xticklabels()]==["D0","D1","D2"]
    assert [text.get_text() for text in ax.get_legend().get_texts()]==["S0","S1","S2"]
    if chart_type=="Liniendiagramm":
        assert [line.get_color() for line in ax.lines]==[SCENARIO_COLORS[s] for s in ("S0","S1","S2")]
        for line,scenario in zip(ax.lines,("S0","S1","S2")):
            assert list(line.get_ydata())==frame[frame.scenario_id==scenario].lcoh_eur_per_kg_h2.tolist()


def test_ambiguous_categorical_cells_are_rejected_instead_of_aggregated():
    frame=result_frame();duplicate=pd.concat([frame,frame.iloc[[0]]],ignore_index=True)
    with pytest.raises(ValueError,match="Mehrere Fälle"):
        plotting.profile_comparison_figure(duplicate)
    with pytest.raises(ValueError,match="bereits auf der x-Achse"):
        plotting.profile_comparison_figure(frame,group_by="demand_profile")


@pytest.mark.parametrize("metric", ["lcoh_eur_per_kg_h2", "objective_eur_per_year", "annual_h2_delivered_kg"])
def test_oat_still_uses_all_five_actual_demand_levels_and_unit(metric):
    frame=demand_frame();before=frame.copy(deep=True)
    figure=plotting.oat_curve_figure(frame,parameter="h2_demand_multiplier",metric=metric)
    assert len(figure.axes)==1
    assert all(list(line.get_xdata())==[50.,75.,100.,125.,150.] for line in figure.axes[0].lines)
    assert list(figure.axes[0].get_xticks())==[50.,75.,100.,125.,150.]
    assert figure.axes[0].get_ylabel()==plotting.METRICS[metric]
    assert_frame_equal(frame,before)


def test_oat_cannot_silently_combine_families_or_duplicate_parameter_points():
    frame=demand_frame();mixed=frame.copy();mixed.loc[0,"__collection"]="Anderes Design"
    with pytest.raises(ValueError,match="Eine Versuchsreihe"):
        plotting.oat_curve_figure(mixed,parameter="h2_demand_multiplier")
    duplicated=pd.concat([frame,frame.iloc[[0]]],ignore_index=True)
    with pytest.raises(ValueError,match="dieselbe Parameterstufe"):
        plotting.oat_curve_figure(duplicated,parameter="h2_demand_multiplier")


@pytest.mark.parametrize("figure_name", ["lcoh_figure","capacity_figure","cost_components_figure","emissions_figure"])
def test_existing_scientific_figure_api_is_preserved_with_readable_names(figure_name):
    frame=result_frame();before=frame.copy(deep=True)
    figure=getattr(plotting,figure_name)(frame)
    figure.canvas.draw();assert_frame_equal(frame,before)
    for ax in figure.axes:
        assert all(len(label.get_text().splitlines()[0])<=30 for label in ax.get_xticklabels())
    if figure_name=="cost_components_figure":
        assert any(bar.get_height()<0 for bar in figure.axes[0].patches)
        assert "negative Importkosten" in figure.texts[-1].get_text()


@pytest.mark.parametrize("bad_value", [float("nan"),float("inf"),"nicht bewertet"])
def test_unavailable_metric_is_explicit_instead_of_a_zero_bar(bad_value):
    frame=result_frame();frame["pv_capacity_mw"]=frame["pv_capacity_mw"].astype(object)
    frame.loc[0,"pv_capacity_mw"]=bad_value
    with pytest.raises(ValueError):
        plotting.comparison_figure(frame,metric="pv_capacity_mw")


def test_grouping_by_site_id_uses_same_axis_for_corresponding_site_labels():
    hamburg=result_frame().iloc[:3].copy();huelva=hamburg.copy()
    huelva["site_id"]="andalusia_huelva";huelva["site_label"]="Huelva-La Rábida"
    frame=pd.concat([hamburg,huelva],ignore_index=True)
    figure=plotting.comparison_figure(frame,chart_type="Gruppierte Balken",group_by="site_id")
    assert [tick.get_text() for tick in figure.axes[0].get_xticklabels()]==["S0","S1","S2"]
    assert len(figure.axes[0].patches)==6


def test_all_previous_metrics_remain_available_alongside_emissions_and_solver_metrics():
    prior={"lcoh_eur_per_kg_h2","objective_eur_per_year","pv_capacity_mw","wind_capacity_mw",
           "electrolyzer_capacity_mw","compressor_capacity_mw","h2_storage_capacity_kg",
           "annual_grid_import_mwh","annual_h2_delivered_kg"}
    assert prior<=set(plotting.METRICS)
    frame=result_frame();available=plotting.available_metrics(frame)
    assert "operational_emission_intensity_kg_co2e_per_kg_h2" in available
    assert "regulatory_emission_intensity_kg_co2e_per_kg_h2" in available
    assert "solver_runtime_seconds" not in available
