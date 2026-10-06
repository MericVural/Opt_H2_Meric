"""Daily result analysis view: real saved EU results, no native execution boundary."""
from datetime import date
import hashlib
import io
import os
from pathlib import Path
import subprocess
import sys

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

GUI_ROOT = Path(os.environ.get('H2_GUI_SOURCE_ROOT', Path(__file__).resolve().parents[2])).resolve()
MODEL_ROOT = Path(os.environ.get('H2_REPO_ROOT', r'C:\Forschungsarbeit\Opt_H2_Meric-h2')).resolve()
sys.path.insert(0, str(GUI_ROOT))
if str(MODEL_ROOT) not in sys.path:
    sys.path.append(str(MODEL_ROOT))
os.environ['H2_REPO_ROOT'] = str(MODEL_ROOT)

from gui import case_study_registry, jobs, model_adapter, result_loader

COLLECTION = 'H₂-Jahresnachfrage: 50–150 % (2024)'
DAILY_VIEW = 'Tagesstrom: Solar, Wind und Netz'
MODES = ['Stündlicher Tagesverlauf', 'Kumulative Tagesenergie']
BASES = ['Direktversorgung', 'Erzeugung und Netzbezug']


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def widget(at, category, key):
    return next(item for item in getattr(at, category) if item.key == key)


def run(at):
    at.run(timeout=180)
    assert not at.exception, [item.message for item in at.exception]
    return at


@pytest.fixture
def real_data(monkeypatch):
    """Only launch boundaries are forbidden; files, native values and plots are real."""
    def forbidden(*args, **kwargs):
        pytest.fail('Selecting a saved daily view must not start a model, worker or solver probe.')
    monkeypatch.setattr(subprocess, 'run', forbidden)
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    for name in ('build_single_plan', 'build_sensitivity_plan', 'preflight_plan', 'probe_solvers', '_core_request'):
        monkeypatch.setattr(model_adapter, name, forbidden)
    for name in ('submit_job', 'prepare_job', 'start_job', 'run_job'):
        monkeypatch.setattr(jobs, name, forbidden)
    registry = case_study_registry.load_registry(MODEL_ROOT)
    return registry


@pytest.mark.parametrize('site_id', ['hamburg_moorburg', 'huelva_la_rabida'])
@pytest.mark.parametrize('profile', ['D0', 'D2'])
def test_daily_electricity_is_directly_available_in_real_saved_analysis(real_data, site_id, profile):
    registry = real_data
    identity = 'eu_2024:' + site_id
    saved = result_loader.load_sensitivity_comparisons(registry, 'eu_2024', site_id)
    quantity = saved[saved['__collection'].eq(COLLECTION)].copy()
    assert len(quantity) == 45 and set(quantity.demand_profile) == {'D0','D1','D2'}
    assert quantity['__collection_id'].nunique() == 1
    assert quantity.number_of_hours.eq(8784).all()
    assert quantity.solver_status.eq('optimal').all()
    family_id = str(quantity['__collection_id'].iloc[0])
    source_csvs = {Path(path) for path in quantity['__source_csv']}
    before = {str(path):digest(path) for path in source_csvs}

    at = AppTest.from_file(str(GUI_ROOT/'gui/app.py'), default_timeout=180)
    # Open the actual saved workflow directly; its data/catalog is not mocked.
    at.session_state['navigation'] = 'Analyse'
    at.session_state['study_selection'] = 'eu_2024'
    at.session_state['site:eu_2024'] = site_id
    at.session_state[identity+':analysis_source'] = 'Gespeicherte Ergebnisse'
    at.session_state[identity+':analysis_collection'] = family_id
    at.session_state[identity+':results:saved_profiles'] = [profile]
    run(at)
    assert widget(at, 'radio', 'navigation').value == 'Analyse'
    assert widget(at,'selectbox',identity+':analysis_collection').value == family_id
    assert widget(at,'multiselect',identity+':results:saved_profiles').value == [profile]
    selector = widget(at, 'selectbox', identity+':graph')
    assert selector.label == 'Darstellung' and DAILY_VIEW in selector.options
    selector.set_value(DAILY_VIEW)
    run(at)
    assert widget(at, 'radio', 'navigation').value == 'Analyse'
    day = widget(at, 'date_input', identity+':daily_day')
    assert day.label == 'Tag auswählen'
    assert day.value == date(2024, 1, 2), 'Default is a complete local day, not the UTC/year boundary.'
    mode = widget(at, 'radio', identity+':daily_mode')
    assert mode.label == 'Tagesdarstellung' and mode.options == MODES
    assert mode.value == MODES[0]
    basis = widget(at, 'radio', identity+':daily_basis')
    assert basis.label == 'Stromgrößen' and basis.options == BASES
    picker = widget(at, 'selectbox', identity+':result_v2')
    assert picker.label == 'Gespeicherten Ergebnisfall wählen'
    chosen = quantity[(quantity.demand_profile == profile) &
                      (quantity['__analysis_id'] == picker.value)]
    assert len(chosen) == 1, 'Daily case must come from the explicitly selected family/profile.'
    directory = Path(chosen.iloc[0]['__result_directory'])
    native = {directory/name:digest(directory/name)
              for name in ('summary.csv','hourly_operation.csv','validated_input.csv','run_metadata.json')}
    assert not at.error, [item.value for item in at.error]
    figure = at.session_state['last_figure_export']
    assert figure['label'] == DAILY_VIEW
    assert figure['png'].startswith(b'\x89PNG') and b'<svg' in figure['svg']
    daily = pd.read_csv(io.BytesIO(at.session_state['last_chart_data']))
    assert len(daily) == 24
    assert set(daily.source_result_directory) == {str(directory)}
    timezone = registry.get_site('eu_2024',site_id).metadata['input_metadata']['calendar_timezone']
    assert set(pd.to_datetime(daily.timestamp,utc=True).dt.tz_convert(timezone).dt.date) == {date(2024,1,2)}

    # Both visible controls actually render in the single-case analysis.
    mode.set_value(MODES[1])
    widget(at, 'radio', identity+':daily_basis').set_value(BASES[1])
    widget(at, 'date_input', identity+':daily_day').set_value(date(2024, 2, 10))
    run(at)
    assert widget(at, 'radio', identity+':daily_mode').value == MODES[1]
    assert widget(at, 'radio', identity+':daily_basis').value == BASES[1]
    assert widget(at, 'date_input', identity+':daily_day').value == date(2024, 2, 10)
    assert widget(at, 'radio', 'navigation').value == 'Analyse'
    assert not at.error, [item.value for item in at.error]
    assert at.session_state['last_figure_export']['label'] == DAILY_VIEW
    assert at.session_state['last_figure_export']['png'].startswith(b'\x89PNG')
    assert b'<svg' in at.session_state['last_figure_export']['svg']
    daily = pd.read_csv(io.BytesIO(at.session_state['last_chart_data']))
    assert len(daily) == 24
    assert set(daily.source_result_directory) == {str(directory)}
    assert set(pd.to_datetime(daily.timestamp,utc=True).dt.tz_convert(timezone).dt.date) == {date(2024,2,10)}
    assert before == {str(path):digest(path) for path in source_csvs}
    assert native == {path:digest(path) for path in native}

    # Returning to the existing quantity curve retains the chosen profile and
    # exactly the original 5 levels × 3 scenarios in its existing CSV export.
    at.session_state[identity+':sensitivity_source']='Gespeicherte Versuchsreihe'
    at.session_state[identity+':oat_collection']=family_id
    at.session_state[identity+':oat_view_profile']=profile
    at.session_state[identity+':oat_chart']=DAILY_VIEW  # migrate the former menu value
    widget(at,'radio','navigation').set_value('Sensitivitätsanalyse')
    run(at)
    assert DAILY_VIEW not in widget(at,'selectbox',identity+':oat_chart').options
    assert widget(at, 'selectbox', identity+':oat_view_profile').value == profile
    assert widget(at, 'selectbox', identity+':oat_view_parameter').value == 'h2_demand_multiplier'
    assert widget(at, 'selectbox', identity+':oat_chart').value == 'Sensitivitätskurve'
    tables = [element.value for element in at.dataframe
              if {'__collection','sensitivity_parameter','demand_profile'}.issubset(element.value.columns)]
    assert any(len(frame) == 15 and set(frame.demand_profile) == {profile} for frame in tables)
    assert before == {str(path):digest(path) for path in source_csvs}
    assert native == {path:digest(path) for path in native}


def test_exact_sensitivity_case_opens_analysis_without_recalculation(real_data):
    identity='eu_2024:hamburg_moorburg'
    saved=result_loader.load_sensitivity_comparisons(real_data,'eu_2024','hamburg_moorburg')
    family=saved[saved['__collection'].eq(COLLECTION)]
    row=family[(family.demand_profile=='D0') & (family.scenario_id=='S1') &
               (family.sensitivity_value==.5)].iloc[0]
    at=AppTest.from_file(str(GUI_ROOT/'gui/app.py'),default_timeout=180)
    at.session_state['navigation']='Sensitivitätsanalyse'
    at.session_state['study_selection']='eu_2024'
    at.session_state['site:eu_2024']='hamburg_moorburg'
    at.session_state[identity+':sensitivity_source']='Gespeicherte Versuchsreihe'
    at.session_state[identity+':oat_collection']=str(row['__collection_id'])
    at.session_state[identity+':oat_view_profile']='D0'
    at.session_state[identity+':sens_details:result_v2']=str(row['__analysis_id'])
    run(at)
    assert DAILY_VIEW not in widget(at,'selectbox',identity+':oat_chart').options
    widget(at,'button',identity+':daily_analysis').click()
    run(at)
    assert widget(at,'radio','navigation').value=='Analyse'
    assert widget(at,'radio',identity+':analysis_source').value=='Gespeicherte Ergebnisse'
    assert widget(at,'selectbox',identity+':analysis_collection').value==str(row['__collection_id'])
    assert widget(at,'selectbox',identity+':result_v2').value==str(row['__analysis_id'])
    assert widget(at,'selectbox',identity+':graph').value==DAILY_VIEW
    daily=pd.read_csv(io.BytesIO(at.session_state['last_chart_data']))
    assert set(daily.source_result_directory)=={row['__result_directory']}
    assert widget(at,'multiselect',identity+':results:saved_scenarios').value==['S1']
    widget(at,'radio','navigation').set_value('Export')
    run(at)
    assert widget(at,'selectbox',identity+':analysis_collection').value==str(row['__collection_id'])
    assert widget(at,'multiselect',identity+':export:saved_scenarios').value==['S1']
    assert widget(at,'multiselect',identity+':export:saved_profiles').value==['D0']
    widget(at,'selectbox',identity+':analysis_collection').set_value('base_results')
    run(at)
    assert widget(at,'selectbox',identity+':analysis_collection').value=='base_results'


def test_unvalued_saved_metric_explains_missing_values_and_keeps_later_controls(real_data):
    """An existing partial result must not abort the rest of the GUI."""
    at = AppTest.from_string('''
import os
from pathlib import Path
import pandas as pd
import streamlit as st
from gui.app import selected_chart

frame = pd.DataFrame([{
    "__analysis_id": "partial-metric-fixture",
    "__result_directory": str(Path(os.environ["H2_REPO_ROOT"]) / "outputs_h2"),
    "site_id": "hamburg_moorburg", "scenario_id": "S0", "profile": "D0",
    "solver_name": "scipy_highs", "case_id": "baseline",
    "lcoh_eur_per_kg_h2": float("nan"),
}])
selected_chart(frame, "missing-metric", "Gespeicherter Teilfall")
st.selectbox("Weitere Darstellung bleibt erreichbar", ["Tagesstrom", "Stundenbetrieb"], key="after-missing")
''', default_timeout=30)
    at.run(timeout=30)
    assert not at.exception, [item.message for item in at.exception]
    assert any('Grafik nicht verfügbar' in item.value and 'bewertete Werte' in item.value for item in at.info)
    assert widget(at, 'selectbox', 'after-missing').options == ['Tagesstrom', 'Stundenbetrieb']
    assert not at.error
