"""Two solver fixtures remain distinct saved cases; no solver is executed."""
from pathlib import Path
import os
import sys
import subprocess

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

GUI_ROOT = Path(os.environ.get("H2_GUI_SOURCE_ROOT", Path(__file__).resolve().parents[1])).resolve()
ROOT = Path(os.environ.get("H2_MODEL_REPO", Path(__file__).resolve().parents[1])).resolve()
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(GUI_ROOT))
from gui.case_study_registry import load_registry
from gui.result_loader import comparison_context, load_registered_results
from gui import plotting


@pytest.fixture
def registry(monkeypatch):
    def no_solver(*args, **kwargs):
        raise AssertionError("Saved-result views must not start a solver process")
    monkeypatch.setattr(subprocess, "run", no_solver)
    monkeypatch.setattr(subprocess, "Popen", no_solver)
    return load_registry(ROOT)


@pytest.fixture
def two_solver_fixture(registry):
    native = load_registered_results(registry, "eu_2024", "hamburg_moorburg", "D0").iloc[[0]].copy()
    frame = pd.concat([native, native], ignore_index=True)
    # Deliberate label fixture, not a claim that the second solver was run.
    frame["solver_name"] = ["scipy_highs", "gurobi"]
    frame.loc[1, "lcoh_eur_per_kg_h2"] += .01
    return frame


@pytest.mark.parametrize("factory", [plotting.lcoh_figure, plotting.capacity_figure, plotting.cost_components_figure])
def test_same_case_solver_labels_and_separate_bars(two_solver_fixture, factory):
    figure = factory(two_solver_fixture)
    try:
        for axis in figure.axes:
            labels = [tick.get_text() for tick in axis.get_xticklabels()]
            assert len(labels) == 2
            assert "scipy_highs" in labels[0]
            assert "gurobi" in labels[1]
            assert all(len(container.patches) == 2 for container in axis.containers)
        if factory is plotting.lcoh_figure:
            heights = [patch.get_height() for patch in figure.axes[0].patches]
            np.testing.assert_allclose(heights, two_solver_fixture.lcoh_eur_per_kg_h2)
        if factory is plotting.capacity_figure:
            np.testing.assert_allclose([patch.get_height() for patch in figure.axes[1].patches], two_solver_fixture.h2_storage_capacity_kg / 1000)
    finally:
        plt.close(figure)


def test_comparison_context_keeps_solver_cases_separate(registry, two_solver_fixture):
    context, warnings = comparison_context(registry, two_solver_fixture)
    assert len(context) == 2
    assert context.solver_name.tolist() == ["scipy_highs", "gurobi"]
    assert context.case_metadata_path.notna().all()
    assert any("Verschiedene Solver" in warning for warning in warnings)


def test_namibia_context_does_not_invent_market_or_operating_year(registry):
    native = load_registered_results(registry, "namibia", "namibia", "D0").iloc[[0]]
    context, _ = comparison_context(registry, native)
    row = context.iloc[0]
    assert row.market_price_year is None
    assert row.study_operation_year is None
    assert row.profile_index_year == 2025
    assert row.weather_year == "TMY 2007–2016"
    assert row.cost_price_year == 2023  # Explicit native technology CAPEX reference.


def test_oat_curves_do_not_join_two_solver_results(two_solver_fixture):
    frame = pd.concat([two_solver_fixture, two_solver_fixture], ignore_index=True)
    frame["sensitivity_parameter"] = "electrolyzer_capex_factor"
    frame["sensitivity_value"] = [.75, .75, 1.25, 1.25]
    frame["__collection"] = "Single deliberate two-solver label fixture"
    figure = plotting.oat_curve_figure(frame, parameter="electrolyzer_capex_factor")
    try:
        lines = figure.axes[0].lines
        assert len(lines) == 2
        assert {line.get_label().split(" · ")[-1] for line in lines} == {"scipy_highs", "gurobi"}
        assert all(len(line.get_xdata()) == 2 for line in lines)
    finally:
        plt.close(figure)
