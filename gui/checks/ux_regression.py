"""Real Streamlit interactions; mock only model/job/result IO boundaries, never solve."""
from pathlib import Path
from types import SimpleNamespace
import io
import json
import os
import re
import sys

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest
import streamlit as st
import matplotlib.pyplot as plt

TEST_PATH = Path(__file__).resolve()
DEFAULT_ROOT = TEST_PATH.parents[2] if TEST_PATH.parent.name == 'checks' and TEST_PATH.parent.parent.name == 'gui' else TEST_PATH.parents[1]
GUI_ROOT = Path(os.environ.get('H2_GUI_SOURCE_ROOT', DEFAULT_ROOT)).resolve()
sys.path.insert(0, str(GUI_ROOT))
MODEL_ROOT = Path(os.environ.get('H2_REPO_ROOT', GUI_ROOT)).resolve()
if str(MODEL_ROOT) not in sys.path:
    sys.path.append(str(MODEL_ROOT))
from gui import case_study_registry, model_adapter, jobs, result_loader, plotting
from gui.analysis_intent import ANALYSES


def widget(at, category, key):
    return next(item for item in getattr(at, category) if item.key == key)


def run(at):
    at.run(timeout=15)
    assert not at.exception, [item.message for item in at.exception]
    return at


def page(at, value):
    widget(at, 'radio', 'navigation').set_value(value)
    return run(at)


def kind(at, value, identity='eu_2024:hamburg_moorburg'):
    if value == 'sensitivity':
        return page(at, 'Sensitivitätsanalyse')
    page(at, 'Analyse')
    widget(at, 'radio', identity+':analysis_source').set_value(
        'Gespeicherte Ergebnisse' if value == 'saved_results' else 'Neue Berechnung')
    return run(at)


def count(at):
    for item in at.caption:
        found = re.search(r'= (\d+) neue Modellläufe', item.value)
        if found:return int(found.group(1))
        found = re.match(r'(\d+) neue Modellläufe:', item.value)
        if found:return int(found.group(1))
    raise AssertionError('No visible native execution count')


@pytest.fixture
def harness(tmp_path, monkeypatch):
    """Small source/summary fixtures isolate GUI intent from native numerical tests."""
    params = {
        'technologies.pv.capex_eur_per_kw': 1000.,
        'technologies.wind_onshore.capex_eur_per_kw': 2000.,
        'technologies.h2_storage.capex_eur_per_kg_h2': 800.,
        'technologies.electrolyzer.capex_eur_per_kw': 1500.,
        'technologies.electrolyzer.specific_electricity_kwh_per_kg_h2': 50.,
        'technologies.pv.real_wacc_fraction': .11,
    }
    records = {name: {'value': value, 'source': 'Explicit test source', 'note': 'GUI fixture'}
               for name, value in params.items()}
    def make_site(study_id, site_id, profiles, mean, historical=False):
        folder=tmp_path/site_id; folder.mkdir()
        refs={}
        for profile in profiles:
            path=folder/(profile+'.csv')
            pd.DataFrame({'electricity_price':[mean-10,mean+10], 'h2_demand':{'D0':[5,5],'D1':[0,10],'D2':[10,0]}[profile]}).to_csv(path,index=False)
            sidecar=folder/(profile+'.json'); sidecar.write_text('{}',encoding='utf-8')
            refs[profile]=SimpleNamespace(path=path,metadata_path=sidecar,description=profile+' delivery',
                metadata={'demand_profile':{'annual_h2_requested_kg':3650000}},exists=True)
        design=folder/'design.json';design.write_text('{}',encoding='utf-8')
        doc=folder/'study.md';doc.write_text('Documented fixture',encoding='utf-8')
        return SimpleNamespace(study_id=study_id,site_id=site_id,label=site_id,profiles=refs,
            runner_kind='legacy' if historical else 'eu',can_run=True,historical=historical,
            metadata={'baseline_metadata':{'model_parameters':records}},
            year_roles={'study_operation_year':2025 if historical else 2024,'cost_price_year':2023},
            design_path=design,documentation_path=doc,run_limitation='')
    eu=make_site('eu_2024','hamburg_moorburg',['D0','D1','D2'],100.)
    huelva=make_site('eu_2024','andalusia_huelva',['D0','D1','D2'],200.)
    nam=make_site('namibia','namibia',['D0'],128.,True)
    studies={'eu_2024':SimpleNamespace(label='EU',role='2024 fixture',sites={eu.site_id:eu,huelva.site_id:huelva}),
             'namibia':SimpleNamespace(label='Namibia',role='Historical fixture',sites={nam.site_id:nam})}
    registry=SimpleNamespace(studies=studies,warnings=[],get_site=lambda s,t:studies[s].sites[t])
    monkeypatch.setattr(case_study_registry,'load_registry',lambda *a,**k:registry)
    monkeypatch.setattr(case_study_registry,'contained_path',lambda root,path,**k:Path(path))
    monkeypatch.setattr(model_adapter,'supported_parameters',lambda *a,**k:{p:'native unit' for p in (
        'electricity_price_offset_eur_per_mwh','real_wacc_multiplier','real_wacc_shift_fraction',
        'pv_capex_eur_per_kw','wind_capex_eur_per_kw','h2_storage_capex_eur_per_kg_h2',
        'electrolyzer_capex_eur_per_kw','electrolyzer_specific_electricity_kwh_per_kg_h2',
        'electricity_price_eur_per_mwh','electrolyzer_capex_factor','electrolyzer_specific_electricity_factor',
        'h2_demand_multiplier')})
    calls=[];submitted=[];plots=[];downloads=[]
    def make_plan(variants=None,**kwargs):
        variants=list(variants or [])
        plan={'kind':'sensitivity' if variants else 'single', 'variants':variants,
            'study_id':kwargs['study_id'],'site_id':kwargs['site_id'],'profile_id':kwargs['profile_id'],
            'scenarios':list(kwargs['scenarios']),'solver':kwargs['solver'],
            'input':{'path':str(kwargs['input_csv'])},'source_metadata':str(kwargs['source_metadata']),
            'optimization_count':len(kwargs['scenarios'])*(1+len(variants))}
        calls.append(plan)
        return plan
    monkeypatch.setattr(model_adapter,'build_single_plan',make_plan)
    monkeypatch.setattr(model_adapter,'build_sensitivity_plan',make_plan)
    monkeypatch.setattr(model_adapter,'combine_plans',lambda plans:{'plans':plans,'kind':'combined',
        'optimization_count':sum(p['optimization_count'] for p in plans)})
    job=tmp_path/'job';job.mkdir();job_state={'status':'queued','total_runs':1,'completed_runs':0}
    def submit(plan,*args,**kwargs):submitted.append(plan);return job
    monkeypatch.setattr(jobs,'submit_job',submit)
    monkeypatch.setattr(jobs,'list_jobs',lambda *a,**k:[])
    monkeypatch.setattr(jobs,'read_status',lambda *a,**k:job_state.copy())
    monkeypatch.setattr(model_adapter,'probe_solvers',lambda *a,**k:pytest.fail('Unrequested solver probe'))
    rows=[]
    for i,(profile,scenario) in enumerate([('D0','reference'),('D0','red_hourly'),('D1','reference'),('D1','red_hourly')]):
        directory=tmp_path/('result_'+str(i));directory.mkdir()
        (directory/'run_metadata.json').write_text('{"fixture_case":'+str(i)+'}',encoding='utf-8')
        row={'__result_directory':str(directory),'site_id':eu.site_id,'scenario_id':scenario,
             'profile':profile,'solver_name':'gurobi' if i==3 else 'scipy-highs','case_id':'baseline','source_label':'UI fixture',
             'lcoh_eur_per_kg_h2':float(i+1),'objective_eur_per_year':1000000.,
             'annual_h2_delivered_kg':3650000.,'solver_status':'optimal','number_of_hours':8784}
        pd.DataFrame([row]).to_csv(directory/'summary.csv',index=False)
        rows.append(row)
    state={'frame':pd.DataFrame(rows)}
    monkeypatch.setattr(result_loader,'load_registered_results',lambda registry, study_id, site_id, **k:state['frame'][state['frame'].site_id==site_id].copy())
    monkeypatch.setattr(result_loader,'load_job_results',lambda *a,**k:state['frame'].copy())
    monkeypatch.setattr(result_loader,'validation_for_result',lambda *a,**k:{'status':'not_found','covers_selected_result':False})
    monkeypatch.setattr(result_loader,'describe_case_sources',lambda *a,**k:{'weather':{'source':'Weather fixture'},'electricity_price':{'source':'Price fixture'},'emission_factors':{'source':'Emission fixture'},'technical_costs':{'source':'Cost fixture'},'wacc':{'source':'Finance fixture'},'demand':{'annual_h2_requested_kg':3650000},'dataflow':{}})
    monkeypatch.setattr(result_loader,'comparison_context',lambda registry, frame:(pd.DataFrame({'year':[2024]}),['Different study assumptions'] if frame.study_id.nunique()>1 else []))
    monkeypatch.setattr(result_loader,'load_sensitivity_comparisons',lambda *a,**k:pd.DataFrame())
    def load_bundle(path,*args,**kwargs):
        summary=pd.read_csv(Path(path)/'summary.csv')
        return SimpleNamespace(summary=summary,validation={},provenance={},hourly=pd.DataFrame())
    monkeypatch.setattr(result_loader,'load_result_directory',load_bundle)
    monkeypatch.setattr(result_loader,'derived_operational_metrics',lambda *a,**k:pd.DataFrame())
    def figure(frame,**kwargs):plots.append(frame.copy());return plt.figure(figsize=(1,1))
    for function in ('lcoh_figure','capacity_figure','cost_components_figure','emissions_figure','comparison_figure','profile_comparison_figure'):
        monkeypatch.setattr(plotting,function,figure)
    original_download=st.download_button
    def download(label,data,*args,**kwargs):
        downloads.append((label,data,kwargs.get('key')))
        return original_download(label,data,*args,**kwargs)
    monkeypatch.setattr(st,'download_button',download)
    at=run(AppTest.from_file(GUI_ROOT/'gui/app.py',default_timeout=15))
    return SimpleNamespace(at=at,calls=calls,submitted=submitted,plots=plots,downloads=downloads,
        state=state,rows=rows,registry=registry,job_state=job_state,job=job)



IDENTITY='eu_2024:hamburg_moorburg'


def saved(at, identity=IDENTITY):
    return kind(at, 'saved_results', identity)


def set_multi(at, key, values):
    widget(at,'multiselect',key).set_value(values)
    return run(at)


def can_start(at,key):
    buttons=[b for b in at.button if b.key==key]
    return bool(buttons and not buttons[0].disabled)


def test_exact_five_main_sections_and_no_intermediate_start_buttons(harness):
    at=harness.at
    assert widget(at,'radio','navigation').options==[
        'Analyse','Sensitivitätsanalyse','Vergleich','Quellen','Export']
    assert widget(at,'button',IDENTITY+':analysis_start').label=='Berechnen'
    assert not [b for b in at.button if b.key and any(
        suffix in b.key for suffix in (':preview_run',':back_to_plan',':open_results',':view_existing'))]
    for value in widget(at,'radio','navigation').options:
        page(at,value)
        assert widget(at,'radio','navigation').value==value
    assert not harness.calls and not harness.submitted


@pytest.mark.parametrize('profiles,scenarios,both,expected',[
    (['D0'],['reference'],False,1),
    (['D0'],['reference','red_monthly','red_hourly'],False,3),
    (['D0','D1','D2'],['reference'],False,3),
    (['D0'],['reference'],True,2),
])
def test_direct_analysis_scope_equals_actual_submitted_job(harness,profiles,scenarios,both,expected):
    h=harness;at=h.at
    set_multi(at,IDENTITY+':profiles',profiles)
    set_multi(at,IDENTITY+':scenarios',scenarios)
    widget(at,'checkbox',IDENTITY+':compare_solvers').set_value(both);run(at)
    assert count(at)==expected and not h.calls
    widget(at,'button',IDENTITY+':analysis_start').click();run(at)
    assert widget(at,'radio','navigation').value=='Analyse'
    plan=h.submitted[-1]
    assert plan['analysis_intent']['type']=='analysis'
    assert plan['optimization_count']==expected
    assert {p['profile_id'] for p in plan['plans']}==set(profiles)
    assert all(p['scenarios']==scenarios and p['variants']==[] for p in plan['plans'])
    assert {p['solver'] for p in plan['plans']}==({'scipy-highs','gurobi'} if both else {'scipy-highs'})
    assert at.session_state[IDENTITY+':analysis_job_dir']==str(h.job)
    assert any('aktualisiert sich automatisch' in item.value for item in at.caption)


def test_invalid_empty_analysis_selection_cannot_start(harness):
    at=harness.at
    set_multi(at,IDENTITY+':profiles',[])
    assert count(at)==0 and not can_start(at,IDENTITY+':analysis_start')
    set_multi(at,IDENTITY+':profiles',['D0'])
    set_multi(at,IDENTITY+':scenarios',[])
    assert count(at)==0 and not can_start(at,IDENTITY+':analysis_start')
    assert not harness.calls and not harness.submitted


def test_direct_analysis_completion_displays_native_metrics_on_same_page(harness):
    h=harness;at=h.at
    widget(at,'button',IDENTITY+':analysis_start').click();run(at)
    h.job_state.update(status='completed',total_runs=3,completed_runs=3,validation_status='passed')
    run(at)
    assert widget(at,'radio','navigation').value=='Analyse'
    assert widget(at,'selectbox',IDENTITY+':analysis_live:result_v2')
    assert next(m.value for m in at.metric if m.label=='LCOH')=='1.0000 EUR/kg H₂'
    assert any('Berechnung abgeschlossen' in item.value for item in at.success)
    assert len(h.submitted)==1


def test_invalid_oat_draft_survives_navigation_and_cannot_use_old_variants(harness):
    h=harness;at=h.at;parameter='pv_capex_eur_per_kw'
    page(at,'Sensitivitätsanalyse')
    set_multi(at,IDENTITY+':oat_parameters',[parameter])
    assert len(at.session_state[IDENTITY+':variants'])==2
    widget(at,'text_input',IDENTITY+parameter+':values').set_value('invalid draft');run(at)
    assert at.session_state[IDENTITY+':variants'] is None
    assert not can_start(at,IDENTITY+':sensitivity_start')
    page(at,'Export');page(at,'Sensitivitätsanalyse')
    assert widget(at,'text_input',IDENTITY+parameter+':values').value=='invalid draft'
    assert not can_start(at,IDENTITY+':sensitivity_start')
    page(at,'Analyse')
    assert can_start(at,IDENTITY+':analysis_start')
    assert not h.calls and not h.submitted


def test_preset_resets_relative_interpretation_and_exact_fifteen_points(harness):
    h=harness;at=h.at;parameter='pv_capex_eur_per_kw'
    page(at,'Sensitivitätsanalyse')
    set_multi(at,IDENTITY+':oat_parameters',[parameter])
    widget(at,'radio',IDENTITY+parameter+':meaning').set_value('Änderung zur Basis [%]');run(at)
    widget(at,'text_input',IDENTITY+parameter+':relative_values').set_value('-90; 90');run(at)
    widget(at,'button',IDENTITY+':common_preset').click();run(at)
    variants=at.session_state[IDENTITY+':variants']
    assert len(variants)==15
    points={p:[r['value'] for r in variants if r['parameter']==p] for p in {r['parameter'] for r in variants}}
    assert points['pv_capex_eur_per_kw']==pytest.approx([750,1250])
    assert points['wind_capex_eur_per_kw']==pytest.approx([500,1000,3000])
    assert points['electricity_price_offset_eur_per_mwh']==pytest.approx([-50,50])
    assert points['real_wacc_multiplier']==pytest.approx([7/11,15/11])
    assert widget(at,'radio',IDENTITY+parameter+':meaning').value=='Direkte Parameterwerte'
    assert count(at)==48
    assert not [b for b in at.button if b.key==IDENTITY+':use_sensitivity']
    assert can_start(at,IDENTITY+':sensitivity_start')
    page(at,'Analyse');set_multi(at,IDENTITY+':scenarios',['reference'])
    assert count(at)==1


def test_absolute_and_percent_range_have_separate_persistent_widgets(harness):
    at=harness.at;parameter='pv_capex_eur_per_kw';prefix=IDENTITY+parameter
    page(at,'Sensitivitätsanalyse');set_multi(at,IDENTITY+':oat_parameters',[parameter])
    widget(at,'radio',prefix+':mode').set_value('Bereich');run(at)
    widget(at,'number_input',prefix+':absolute:min').set_value(600.)
    widget(at,'number_input',prefix+':absolute:max').set_value(1400.)
    widget(at,'number_input',prefix+':absolute:step').set_value(400.);run(at)
    assert [v['value'] for v in at.session_state[IDENTITY+':variants']]==[600,1000,1400]
    widget(at,'radio',prefix+':meaning').set_value('Änderung zur Basis [%]');run(at)
    assert widget(at,'number_input',prefix+':relative:min').value==-25
    assert [v['value'] for v in at.session_state[IDENTITY+':variants']]==[750,1250]
    page(at,'Analyse');page(at,'Sensitivitätsanalyse')
    widget(at,'radio',prefix+':meaning').set_value('Direkte Parameterwerte');run(at)
    assert [v['value'] for v in at.session_state[IDENTITY+':variants']]==[600,1000,1400]


def test_direct_multi_scope_oat_is_sum_of_points_and_native_forwarding(harness):
    h=harness;at=h.at
    page(at,'Sensitivitätsanalyse')
    set_multi(at,IDENTITY+':sens_profiles',['D0','D2'])
    set_multi(at,IDENTITY+':sens_scenarios',['reference','red_hourly'])
    set_multi(at,IDENTITY+':oat_parameters',['real_wacc_multiplier'])
    assert count(at)==12
    widget(at,'button',IDENTITY+':sensitivity_start').click();run(at)
    assert widget(at,'radio','navigation').value=='Sensitivitätsanalyse'
    plan=h.submitted[-1]
    assert plan['optimization_count']==12
    assert {p['profile_id'] for p in plan['plans']}=={'D0','D2'}
    assert all(p['scenarios']==['reference','red_hourly'] and len(p['variants'])==2 for p in plan['plans'])
    assert plan['gui_oat_design']['numeric_variants_crossed_with_profile_levels'] is False
    assert plan['analysis_intent']['type']=='sensitivity'


def test_profile_dimension_is_normal_selection_and_not_factorial(harness):
    h=harness;at=h.at
    page(at,'Sensitivitätsanalyse')
    set_multi(at,IDENTITY+':sens_scenarios',['reference'])
    set_multi(at,IDENTITY+':oat_parameters',['pv_capex_eur_per_kw','h2_delivery_profile'])
    assert count(at)==5
    widget(at,'button',IDENTITY+':sensitivity_start').click();run(at)
    plan=h.submitted[-1]
    assert plan['optimization_count']==5
    children={p['profile_id']:p for p in plan['plans']}
    assert len(children['D0']['variants'])==2
    assert children['D1']['variants']==children['D2']['variants']==[]
    assert all(v['parameter']!='h2_delivery_profile' for p in children.values() for v in p['variants'])
    assert plan['gui_oat_design']['profile_input_receipt']['annual_h2_requested_kg']==10


def test_direct_sensitivity_completion_displays_own_table_curve_and_metrics_on_same_page(harness,monkeypatch):
    h=harness;at=h.at
    page(at,'Sensitivitätsanalyse')
    set_multi(at,IDENTITY+':oat_parameters',['real_wacc_multiplier'])
    widget(at,'button',IDENTITY+':sensitivity_start').click();run(at)
    frame=h.state['frame'].iloc[:2].copy()
    frame['sensitivity_parameter']=['baseline','real_wacc_multiplier']
    frame['sensitivity_value']=[1.,15/11]
    frame['value']=[1.,15/11]
    h.state['frame']=frame
    monkeypatch.setattr(plotting,'oat_curve_figure',lambda frame,**kwargs:plt.figure(figsize=(1,1)))
    h.job_state.update(status='completed',total_runs=9,completed_runs=9,validation_status='passed')
    run(at)
    assert widget(at,'radio','navigation').value=='Sensitivitätsanalyse'
    assert widget(at,'selectbox',IDENTITY+':sensitivity_live:oat_view_parameter').value=='real_wacc_multiplier'
    assert widget(at,'selectbox',IDENTITY+':sensitivity_live:sens_details:result_v2')
    assert any('Berechnung abgeschlossen' in item.value for item in at.success)
    csv=next(data for _,data,key in reversed(h.downloads) if key==IDENTITY+':sensitivity_live:sens_download')
    assert pd.read_csv(io.BytesIO(csv))['__result_directory'].tolist()==frame['__result_directory'].tolist()
    assert len(h.submitted)==1


def test_sensitivity_scope_settings_persist_across_navigation(harness):
    at=harness.at
    page(at,'Sensitivitätsanalyse')
    set_multi(at,IDENTITY+':sens_profiles',['D2'])
    set_multi(at,IDENTITY+':sens_scenarios',['off_grid'])
    widget(at,'selectbox',IDENTITY+':sens_solver').set_value('auto')
    widget(at,'checkbox',IDENTITY+':sens_compare_solvers').set_value(True);run(at)
    page(at,'Quellen');page(at,'Sensitivitätsanalyse')
    assert widget(at,'multiselect',IDENTITY+':sens_profiles').value==['D2']
    assert widget(at,'multiselect',IDENTITY+':sens_scenarios').value==['off_grid']
    assert widget(at,'selectbox',IDENTITY+':sens_solver').value=='auto'
    assert widget(at,'checkbox',IDENTITY+':sens_compare_solvers').value is True


def test_sources_retain_configuration_years_validation_and_explicit_solver_probe(harness,monkeypatch):
    h=harness;at=h.at
    calls=[]
    monkeypatch.setattr(model_adapter,'probe_solvers',lambda *a,**k:calls.append('probe') or {'scipy-highs':{'available':True}})
    page(at,'Quellen')
    assert not calls
    labels=[item.label for item in at.expander]
    assert 'Basiskonfiguration und Solver-Verfügbarkeit' in labels
    assert 'Vollständige Quellenverträge, Datenfluss und Hashnachweise' in labels
    assert 'Validierungsnachweis eines gespeicherten Falls' in labels
    assert any('Betriebsjahr' in str(item.value) for item in at.dataframe)
    widget(at,'button',IDENTITY+':probe').click();run(at)
    assert calls==['probe'] and not h.submitted


def test_saved_filters_stable_picker_graph_scope_and_export_contents(harness):
    h=harness;at=h.at;saved(at)
    chosen=h.rows[3]['__result_directory']
    widget(at,'selectbox',IDENTITY+':result_v2').set_value(chosen);run(at)
    set_multi(at,IDENTITY+':result:cases',[chosen])
    assert h.plots[-1]['__result_directory'].tolist()==[chosen]
    h.state['frame']=h.state['frame'].iloc[::-1].reset_index(drop=True);run(at)
    assert widget(at,'selectbox',IDENTITY+':result_v2').value==chosen
    set_multi(at,IDENTITY+':result:cases',[r['__result_directory'] for r in h.rows])
    assert len(h.plots[-1])==4
    widget(at,'multiselect',IDENTITY+':results:saved_profiles').set_value(['D1'])
    widget(at,'multiselect',IDENTITY+':results:saved_scenarios').set_value(['red_hourly']);run(at)
    assert h.plots[-1]['__result_directory'].tolist()==[chosen]
    assert next(m.value for m in at.metric if m.label=='LCOH')=='4.0000 EUR/kg H₂'
    widget(at,'multiselect',IDENTITY+':results:saved_profiles').set_value([]);run(at)
    assert not [s for s in at.selectbox if s.key==IDENTITY+':result_v2']
    page(at,'Export')
    widget(at,'multiselect',IDENTITY+':export:saved_profiles').set_value(['D1'])
    widget(at,'multiselect',IDENTITY+':export:saved_scenarios').set_value(['red_hourly']);run(at)
    csv=next(data for label,data,key in reversed(h.downloads) if key==IDENTITY+':export_results')
    assert pd.read_csv(io.BytesIO(csv))['__result_directory'].tolist()==[chosen]
    assert widget(at,'selectbox',IDENTITY+':export:result_v2').value==chosen
    metadata=next(data for label,data,key in reversed(h.downloads) if key==IDENTITY+':native_json')
    assert metadata==b'{"fixture_case":3}'
    assert next(data for _,data,key in reversed(h.downloads) if key=='export_figure_png').startswith(b'\x89PNG')
    assert b'<svg' in next(data for _,data,key in reversed(h.downloads) if key=='export_figure_svg')


def test_settings_persist_across_pages_and_sites_without_proxy_carryover(harness):
    h=harness;at=h.at
    set_multi(at,IDENTITY+':profiles',['D1'])
    set_multi(at,IDENTITY+':scenarios',['red_hourly'])
    widget(at,'selectbox',IDENTITY+':solver').set_value('gurobi');run(at)
    page(at,'Quellen');page(at,'Analyse')
    assert widget(at,'multiselect',IDENTITY+':profiles').value==['D1']
    assert widget(at,'multiselect',IDENTITY+':scenarios').value==['red_hourly']
    assert widget(at,'selectbox',IDENTITY+':solver').value=='gurobi'
    widget(at,'selectbox','study_selection').set_value('namibia');run(at)
    page(at,'Sensitivitätsanalyse')
    widget(at,'button','namibia:namibia:common_preset').click();run(at)
    assert [r['value'] for r in at.session_state['namibia:namibia:variants']
        if r['parameter']=='electricity_price_offset_eur_per_mwh']==[-64,64]
    widget(at,'selectbox','study_selection').set_value('eu_2024');run(at)
    widget(at,'selectbox','site:eu_2024').set_value('andalusia_huelva');run(at)
    widget(at,'button','eu_2024:andalusia_huelva:common_preset').click();run(at)
    assert [r['value'] for r in at.session_state['eu_2024:andalusia_huelva:variants']
        if r['parameter']=='electricity_price_offset_eur_per_mwh']==[-100,100]
    widget(at,'selectbox','site:eu_2024').set_value('hamburg_moorburg');run(at)
    page(at,'Analyse')
    assert widget(at,'multiselect',IDENTITY+':profiles').value==['D1']
    assert widget(at,'multiselect',IDENTITY+':scenarios').value==['red_hourly']
    assert widget(at,'selectbox',IDENTITY+':solver').value=='gurobi'
    assert count(at)==1 and not h.calls and not h.submitted


def test_saved_solver_filters_transfer_to_export_and_keep_explicit_empty_selection(harness):
    h=harness;at=h.at;saved(at)
    widget(at,'multiselect',IDENTITY+':results:saved_profiles').set_value(['D1'])
    widget(at,'multiselect',IDENTITY+':results:saved_scenarios').set_value(['red_hourly'])
    widget(at,'multiselect',IDENTITY+':results:saved_solvers').set_value(['gurobi']);run(at)
    chosen=h.rows[3]['__result_directory']
    page(at,'Export')
    assert widget(at,'multiselect',IDENTITY+':export:saved_profiles').value==['D1']
    assert widget(at,'multiselect',IDENTITY+':export:saved_scenarios').value==['red_hourly']
    assert widget(at,'multiselect',IDENTITY+':export:saved_solvers').value==['gurobi']
    csv=next(data for label,data,key in reversed(h.downloads) if key==IDENTITY+':export_results')
    assert pd.read_csv(io.BytesIO(csv))['__result_directory'].tolist()==[chosen]
    widget(at,'multiselect',IDENTITY+':export:saved_solvers').set_value([]);run(at)
    csv=next(data for label,data,key in reversed(h.downloads) if key==IDENTITY+':export_results')
    assert pd.read_csv(io.BytesIO(csv)).empty
    assert not [s for s in at.selectbox if s.key==IDENTITY+':export:result_v2']
    page(at,'Analyse')
    widget(at,'radio',IDENTITY+':analysis_source').set_value('Gespeicherte Ergebnisse');run(at)
    assert widget(at,'multiselect',IDENTITY+':results:saved_solvers').value==[]
    assert not [s for s in at.selectbox if s.key==IDENTITY+':result_v2']
    assert not h.submitted


def test_grouped_copy_selection_survives_representative_change_and_exports_provenance(harness):
    h=harness;at=h.at;saved(at)
    old=h.rows[2].copy();old_path=old['__result_directory']
    widget(at,'selectbox',IDENTITY+':result_v2').set_value(old_path);run(at)
    copy_path=Path(old_path).parent/'identical_copy';copy_path.mkdir()
    metadata=b'{"fixture_case":"identical copy"}'
    (copy_path/'run_metadata.json').write_bytes(metadata)
    copy={**old,'__result_directory':str(copy_path),'source_label':'Second saved execution'}
    pd.DataFrame([copy]).to_csv(copy_path/'summary.csv',index=False)
    h.rows.append(copy)
    group={**old,'__analysis_id':'analysis:stable-duplicate','__execution_count':2,'__source_count':2,
        '__result_copies':json.dumps([old,copy])}
    frame=h.state['frame'].copy()
    for name in group:
        if name not in frame:frame[name]=None
    for name,value in group.items():frame.at[2,name]=value
    h.state['frame']=frame;run(at)
    assert widget(at,'selectbox',IDENTITY+':result_v2').value=='analysis:stable-duplicate'
    assert len(widget(at,'selectbox',IDENTITY+':result_v2').options)==4
    assert next(m.value for m in at.metric if m.label=='LCOH')=='3.0000 EUR/kg H₂'
    h.state['frame'].at[2,'__result_directory']=str(copy_path)
    h.state['frame']=h.state['frame'].iloc[::-1].reset_index(drop=True);run(at)
    assert widget(at,'selectbox',IDENTITY+':result_v2').value=='analysis:stable-duplicate'
    set_multi(at,IDENTITY+':result:cases',['analysis:stable-duplicate'])
    assert h.plots[-1]['__result_directory'].tolist()==[str(copy_path)]
    page(at,'Export')
    widget(at,'selectbox',IDENTITY+':export:result_v2').set_value('analysis:stable-duplicate');run(at)
    csv=next(data for label,data,key in reversed(h.downloads) if key==IDENTITY+':export_results')
    exported=pd.read_csv(io.BytesIO(csv))
    assert len(exported)==4
    selected=exported.loc[exported['__analysis_id']=='analysis:stable-duplicate'].iloc[0]
    assert {r['__result_directory'] for r in json.loads(selected['__result_copies'])}=={old_path,str(copy_path)}
    assert next(data for _,data,key in reversed(h.downloads) if key==IDENTITY+':native_json')==metadata
    assert not h.submitted


def test_comparison_requires_explicit_cases_and_exports_exact_choice(harness):
    h=harness;at=h.at
    page(at,'Vergleich')
    assert widget(at,'multiselect','comparison_cases_v2').value==[]
    assert not [s for s in at.selectbox if s.key=='comparison_metric']
    choices=widget(at,'multiselect','comparison_cases_v2')
    raw_keys=list(at.session_state['comparison_cases_v2'])
    assert raw_keys==[]
    # Streamlit displays format_func labels; choose by actual option values from
    # the DataFrame contract constructed in comparison_view.
    expected=[f"eu_2024:{r['site_id']}:{r['source_label']}:{r['__result_directory']}" for r in h.rows[:2]]
    widget(at,'multiselect','comparison_cases_v2').set_value(expected);run(at)
    widget(at,'selectbox','comparison_metric').set_value('objective_eur_per_year')
    widget(at,'selectbox','comparison_chart_type').set_value('Gruppierte Balken');run(at)
    assert set(h.plots[-1]['__result_directory'])=={r['__result_directory'] for r in h.rows[:2]}
    exported=pd.read_csv(io.BytesIO(at.session_state['comparison_export']))
    assert len(exported)==2
    page(at,'Export')
    assert next(data for _,data,key in reversed(h.downloads) if key=='export_comparison')==at.session_state['comparison_export']
    assert not h.calls and not h.submitted


def test_chart_explicit_empty_selection_does_not_draw_unselected_cases(harness):
    h=harness;at=h.at;saved(at)
    prior=len(h.plots)
    set_multi(at,IDENTITY+':result:cases',[])
    assert len(h.plots)==prior
    assert any('Mindestens einen Fall' in item.value for item in at.caption)
    assert not h.submitted
