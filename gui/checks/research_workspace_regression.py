"""U2: actual goal-led UI with real archived results; solver submission forbidden."""
import io
import json
import os
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

ROOT=Path(__file__).resolve().parents[2]
MODEL=Path(os.environ.get('H2_REPO_ROOT',ROOT))
sys.path.insert(0,str(ROOT));sys.path.append(str(MODEL))
from gui import jobs, model_adapter, sensitivity_design, analysis_contracts, result_loader
from gui.case_study_registry import load_registry
from gui.research_logic import percent_variants, flatten_plans, demand_observation, observed_delta

A='research:eu_2024:hamburg_moorburg:Analyse'
S='research:eu_2024:hamburg_moorburg:Sensitivitätsanalyse'


@pytest.fixture(scope='module')
def app():
    original=jobs.submit_job
    jobs.submit_job=lambda *a,**k: (_ for _ in ()).throw(AssertionError('A read-only UI action must never start optimization'))
    os.environ['H2_REPO_ROOT']=str(MODEL)
    at=AppTest.from_file(str(ROOT/'gui/app.py'),default_timeout=90)
    at.run(timeout=90)
    assert not at.exception
    yield at
    jobs.submit_job=original


def run(at):
    at.run(timeout=90)
    assert not at.exception, [x.message for x in at.exception]
    return at


def page(at,name):
    at.radio(key='navigation').set_value(name);return run(at)


def data(at):
    return pd.read_csv(io.BytesIO(at.session_state['last_chart_data']))


def test_default_starts_with_research_question_and_consistent_scenarios(app):
    assert app.radio(key=A+':goal').value=='rules'
    frame=data(app)
    assert set(frame.scenario_id)=={'S0','S1','S2'}
    assert set(frame.profile)=={'D0'}
    assert frame['__native_input_sha256'].nunique()==1
    assert frame['__native_configuration_sha256'].nunique()==1
    assert any('S2 liegt gegenüber S1' in x.value for x in app.markdown)
    assert not any(x.label=='Diagrammtyp' for x in app.selectbox)


def test_cost_components_have_no_arbitrary_metric_selector(app):
    app.radio(key=A+':result:cost').set_value('Kostenbestandteile');run(app)
    assert not app.warning
    assert set(data(app).scenario_id)=={'S0','S1','S2'}
    assert not any(x.label=='Kennzahl' for x in app.selectbox)


def test_emissions_keep_native_reference_and_exact_context(app):
    app.radio(key=A+':result:view').set_value('Netz & Emissionen');run(app)
    frame=data(app)
    assert frame['red_iii_maximum_product_intensity_kg_co2e_per_kg_h2'].nunique()==1
    assert len(frame)==3
    assert any('statischer Länderfaktor' in x.value for x in app.caption)
    app.multiselect(key=A+':rules').set_value([]);run(app)
    assert 'last_chart_data' not in app.session_state
    app.multiselect(key=A+':rules').set_value(['S0','S1','S2']);run(app)


def test_quantity_is_15_native_points_with_own_bases_and_real_observation(app):
    page(app,'Sensitivitätsanalyse')
    frame=data(app)
    assert len(frame)==15
    assert set(frame.__plot_x)=={50,75,100,125,150}
    assert frame.__oat_is_baseline.sum()==3
    assert app.selectbox(key=S+':influence:metric:Kosten').value=='objective_eur_per_year'
    assert any('proportional' in x.value for x in app.markdown)
    assert not any('Grenze' in label for item in app.selectbox for label in item.options)


def test_delivery_profile_is_categorical_equal_quantity(app):
    app.radio(key=S+':goal').set_value('profile');run(app)
    frame=data(app)
    assert set(frame.profile)=={'D0','D1','D2'}
    assert np.allclose(frame.annual_h2_delivered_kg,frame.annual_h2_delivered_kg.iloc[0],rtol=1e-9,atol=1e-3)
    assert set(frame.case_id)=={'baseline'}
    assert [m.label for m in app.metric]==['D0 · LCOH','D1 · LCOH','D2 · LCOH']


def test_driver_labels_actual_price_operation(app):
    app.radio(key=S+':goal').set_value('drivers');run(app)
    assert not app.warning, [w.value for w in app.warning]
    frame=data(app)
    assert len(frame)>0
    assert frame.__oat_is_baseline.sum()==3
    assert frame.__plot_operation.eq('add_to_hourly_price_profile').all()


def test_new_quantity_design_counts_both_sites_all_profiles_without_solving(app):
    app.radio(key=S+':goal').set_value('quantity')
    app.radio(key=S+':mode').set_value('Neu berechnen');run(app)
    app.multiselect(key=S+':sites').set_value(['hamburg_moorburg','huelva_la_rabida'])
    app.multiselect(key=S+':profiles:quantity').set_value(['D0','D1','D2']);run(app)
    assert any('**90 Modellfälle**' in x.value for x in app.markdown)
    assert not app.button(key=S+':new:quantity:submit').disabled
    app.multiselect(key=S+':new:quantity:levels').set_value([100]);run(app)
    assert app.button(key=S+':new:quantity:submit').disabled
    app.multiselect(key=S+':new:quantity:levels').set_value([50,75,100,125,150]);run(app)
    app.radio(key=S+':mode').set_value('Ergebnisse auswerten');run(app)


def test_exact_sensitivity_point_opens_daily_not_baseline(app):
    point=app.selectbox(key=S+':point:result_v2')
    options=point.options
    # Initial selected point is a native variant; record the exact path first.
    frame=data(app)
    app.button(key=S+':open_point').click();run(app)
    assert app.radio(key='navigation').value=='Analyse'
    daily=data(app)
    requested=app.session_state['research_daily_case']['row']['__result_directory']
    assert daily.source_result_directory.eq(requested).all()
    assert len(daily) in (23,24,25)
    modes=[x for x in app.radio if x.label=='Tagesdarstellung']
    modes[0].set_value('Kumulative Tagesenergie');run(app)
    assert data(app).source_result_directory.eq(requested).all()
    assert np.isclose(data(app).cumulative_grid_mwh.iloc[-1],data(app).selected_grid_mwh.sum())
    app.button(key='research_close_daily').click();run(app)


def test_site_comparison_has_no_misleading_global_site_filter(app):
    page(app,'Vergleich')
    assert not any(x.key=='site:eu_2024' for x in app.selectbox)
    frame=data(app)
    assert set(frame.site_id)=={'hamburg_moorburg','huelva_la_rabida'}
    assert set(frame.scenario_id)=={'S0'}
    assert np.allclose(frame.annual_h2_delivered_kg,frame.annual_h2_delivered_kg.iloc[0],rtol=1e-9,atol=1e-3)


def test_sources_and_export_remain_reachable(app):
    page(app,'Quellen')
    assert any(x.label=='Basiskonfiguration und Solver-Verfügbarkeit' for x in app.expander)
    page(app,'Export')
    assert any(x.label=='Exakte Daten dieser Grafik (CSV)' for x in app.get('download_button'))


@pytest.mark.parametrize('levels',[[0],[-5],[float('nan')],[float('inf')],[]])
def test_invalid_demand_levels_rejected(levels):
    with pytest.raises(ValueError):percent_variants(levels)


def test_quantity_reference_and_flat_multisite_composition():
    variants=percent_variants([50,75,100,125,150,100])
    assert [v['value'] for v in variants]==[.5,.75,1.25,1.5]
    scope=sensitivity_design.oat_profile_scope(['D0','D1','D2'],['reference','red_monthly','red_hourly'],variants)
    assert 2*scope['optimization_count']==90
    leaves=[{'kind':'single','site_id':str(i)} for i in range(4)]
    result=flatten_plans([{'kind':'combined','plans':[leaves[0],{'kind':'combined','plans':leaves[1:]}]}])
    assert result==leaves


def test_delta_does_not_pair_ambiguous_scenarios():
    frame=pd.DataFrame({'scenario_id':['S1','S2','S2'],'lcoh_eur_per_kg_h2':[5,6,7]})
    assert observed_delta(frame) is None


def test_no_proportionality_claim_without_reference_contract():
    frame=pd.DataFrame({'annual_h2_delivered_kg':[1,2],'objective_eur_per_year':[10,20]})
    assert demand_observation(frame) is None


def test_explicit_start_submits_one_flat_90_case_plan(app,monkeypatch,tmp_path):
    submitted=[]
    def build(repo,site,profiles,scenarios,solver,*,variants,profile_levels,compare_solvers):
        assert not profile_levels and not compare_solvers
        assert len(variants)==4
        return model_adapter.combine_plans([{
            'kind':'sensitivity','repo_root':str(repo),'model_python':'fixture-python',
            'study_id':site.study_id,'site_id':site.site_id,'profile_id':p,'solver':solver,
            'scenarios':scenarios,'variants':variants,'optimization_count':15} for p in profiles])
    def submit(plan,*args):
        submitted.append(plan);return tmp_path/'mock-job'
    monkeypatch.setattr(sensitivity_design,'build_oat_profile_plan',build)
    monkeypatch.setattr(jobs,'submit_job',submit)
    monkeypatch.setattr(jobs,'read_status',lambda p:{'status':'queued','total_runs':90,'completed_runs':0})
    page(app,'Sensitivitätsanalyse')
    app.radio(key=S+':mode').set_value('Neu berechnen');run(app)
    app.multiselect(key=S+':sites').set_value(['hamburg_moorburg','huelva_la_rabida'])
    app.multiselect(key=S+':profiles:quantity').set_value(['D0','D1','D2']);run(app)
    assert not submitted
    app.button(key=S+':new:quantity:submit').click();run(app)
    assert len(submitted)==1
    plan=submitted[0]
    assert plan['optimization_count']==90 and len(plan['plans'])==6
    assert {p['site_id'] for p in plan['plans']}=={'hamburg_moorburg','huelva_la_rabida'}
    assert all(p['kind']!='combined' for p in plan['plans'])
    assert plan['analysis_intent']['type']=='quantity'


@pytest.mark.parametrize('goal,expected_count',[
    ('rules',12),('plant',1),('solver',2),('profile',9),
])
def test_start_without_numeric_variants_uses_native_basis_plans(app,monkeypatch,tmp_path,goal,expected_count):
    """Exercise the real button and native input preflight; never launch a worker."""
    submitted=[]
    def submit(plan,*args):
        submitted.append(plan)
        return tmp_path/('mock-'+goal)
    monkeypatch.setattr(jobs,'submit_job',submit)
    monkeypatch.setattr(jobs,'read_status',lambda p:{
        'status':'queued','total_runs':expected_count,'completed_runs':0})
    # Solver forwarding is tested independently of the machine's Gurobi licence.
    monkeypatch.setattr(model_adapter,'probe_solvers',lambda *a,**k:{
        'solvers':{'gurobi':{'available':True}}})
    key=S if goal=='profile' else A
    page(app,'Sensitivitätsanalyse' if goal=='profile' else 'Analyse')
    app.radio(key=key+':goal').set_value(goal);run(app)
    app.radio(key=key+':mode').set_value('Neu berechnen');run(app)
    if goal=='profile':
        app.multiselect(key=S+':sites').set_value(['hamburg_moorburg'])
        app.multiselect(key=S+':profiles:profile').set_value(['D0','D1','D2'])
        app.multiselect(key=S+':scenarios').set_value(['S0','S1','S2'])
    else:
        app.selectbox(key=A+':profile').set_value('D0')
        if goal=='rules':
            app.multiselect(key=A+':rules').set_value(['S0','S1','S2'])
            app.multiselect(key=A+':new:rules:additional_profiles').set_value(['D1','D2'])
            app.multiselect(key=A+':new:rules:additional_scenarios').set_value(['S3'])
        else:
            app.selectbox(key=A+':rule').set_value('S0')
    run(app)
    assert not submitted
    assert any(f'**{expected_count} Modellfälle**' in x.value for x in app.markdown)
    app.button(key=key+':new:'+goal+':submit').click();run(app)
    assert len(submitted)==1, [x.value for x in app.warning]
    assert not app.warning and not app.error
    plan=submitted[0]
    assert plan['optimization_count']==expected_count
    assert plan['analysis_intent']['type']==goal
    assert all(p['kind']=='single' and not p['variants'] for p in plan['plans'])
    assert all(p['expected_hours']==8784 for p in plan['plans'])
    assert all(p['gui_context']['site_id']=='hamburg_moorburg' for p in plan['plans'])
    expected_profiles={'D0','D1','D2'} if goal in ('rules','profile') else {'D0'}
    assert {p['profile_id'] for p in plan['plans']}==expected_profiles
    expected_solvers={'scipy-highs','gurobi'} if goal=='solver' else {'scipy-highs'}
    assert {p['solver'] for p in plan['plans']}==expected_solvers
    if goal=='rules':
        assert all(p['scenarios']==['reference','red_monthly','red_hourly','off_grid'] for p in plan['plans'])
    if goal=='profile':
        assert all(p['gui_oat_design']['profile_parameter']=='h2_delivery_profile' for p in plan['plans'])
