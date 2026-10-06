"""Normal quantity-sensitivity selection; real widgets and native-file IO contracts.

Optimization/job boundaries are replaced by the shared GUI harness. Reading
native exports and drawing the actual five demand levels remain independent.
"""
import io
import hashlib
import json
import subprocess
from types import SimpleNamespace

import matplotlib.pyplot as plt
import pandas as pd
import pytest

from gui import model_adapter, plotting, result_loader
from gui.result_loader import load_sensitivity_comparisons as read_saved_sensitivities
from gui.checks.ux_regression import harness, widget, run, page, kind, count


PARAMETER='h2_demand_multiplier'
FACTORS=[.5,.75,1.25,1.5]


@pytest.fixture
def quantity_gui(harness,monkeypatch):
    supported=model_adapter.supported_parameters()
    monkeypatch.setattr(model_adapter,'supported_parameters',lambda *args,**kwargs:{**supported,PARAMETER:'factor'})
    run(harness.at)
    return harness


def select_quantity(at,identity='eu_2024:hamburg_moorburg'):
    kind(at,'sensitivity',identity)
    widget(at,'multiselect',identity+':oat_parameters').set_value([PARAMETER]);run(at)


def open_saved_sensitivity(at,identity='eu_2024:hamburg_moorburg'):
    page(at,'Sensitivitätsanalyse')
    widget(at,'radio',identity+':sensitivity_source').set_value('Gespeicherte Versuchsreihe');run(at)


@pytest.mark.parametrize('site_id',['hamburg_moorburg','andalusia_huelva'])
def test_normal_demand_selection_counts_45_years_per_site_and_displays_annual_amounts(quantity_gui,site_id):
    h=quantity_gui;at=h.at;identity='eu_2024:'+site_id
    widget(at,'selectbox','site:eu_2024').set_value(site_id);run(at)
    kind(at,'sensitivity',identity)
    widget(at,'multiselect',identity+':sens_profiles').set_value(['D0','D1','D2']);run(at)
    assert widget(at,'multiselect',identity+':oat_parameters').value==[]
    widget(at,'multiselect',identity+':oat_parameters').set_value([PARAMETER]);run(at)
    variants=at.session_state[identity+':variants']
    assert [v['parameter'] for v in variants]==[PARAMETER]*4
    assert [v['value'] for v in variants]==FACTORS
    assert all('der Basis' in v['label'] for v in variants)
    assert count(at)==45
    start=widget(at,'button',identity+':sensitivity_start')
    assert start.label=='Sensitivität berechnen' and not start.disabled
    assert not [button for button in at.button if button.key in (identity+':demand_quantity_preset',identity+':use_sensitivity')]
    annual=next(df.value for df in at.dataframe if 'Jährliche Pflichtlieferung [kg/a]' in df.value)
    assert len(annual)==15
    for profile in ['D0','D1','D2']:
        selected=annual[annual.Lieferprofil==profile]
        assert selected['Jahresnachfrage [% der Basis]'].tolist()==[50,75,100,125,150]
        assert selected['Jährliche Pflichtlieferung [kg/a]'].tolist()==[1825000,2737500,3650000,4562500,5475000]
        assert selected.Fall.tolist().count('Unveränderter Basisfall')==1
    assert any('keine Größendegression' in note.value for note in at.info)
    assert any('jede Stunde desselben Profils proportional' in note.value for note in at.caption)
    assert not h.calls and not h.submitted
    start.click();run(at)
    assert widget(at,'radio','navigation').value=='Sensitivitätsanalyse'
    submitted=h.submitted[-1]
    assert submitted['optimization_count']==45
    assert submitted['analysis_intent']['type']=='sensitivity'
    assert len(submitted['plans'])==3
    assert {plan['profile_id'] for plan in submitted['plans']}=={'D0','D1','D2'}
    assert all(plan['site_id']==site_id and plan['study_id']=='eu_2024' for plan in submitted['plans'])
    assert all([variant['value'] for variant in plan['variants']]==FACTORS for plan in submitted['plans'])
    assert all(len(plan['scenarios'])==3 for plan in submitted['plans'])
    assert submitted['gui_oat_design']['numeric_variants_crossed_with_profile_levels'] is False


def test_explicit_and_range_include_native_baseline_once_and_reject_zero(quantity_gui):
    h=quantity_gui;at=h.at;identity='eu_2024:hamburg_moorburg';prefix=identity+PARAMETER
    select_quantity(at)
    widget(at,'text_input',prefix+':values').set_value('0,5; 0,75; 1; 1,25; 1,5');run(at)
    assert [v['value'] for v in at.session_state[identity+':variants']]==FACTORS
    assert any('nicht erneut' in note.value for note in at.caption)
    widget(at,'radio',prefix+':mode').set_value('Bereich');run(at)
    widget(at,'number_input',prefix+':absolute:step').set_value(.25);run(at)
    assert [v['value'] for v in at.session_state[identity+':variants']]==FACTORS
    widget(at,'number_input',prefix+':absolute:min').set_value(0.);run(at)
    assert at.session_state[identity+':variants'] is None
    assert any('größer als null' in error.value for error in at.error)
    assert widget(at,'button',identity+':sensitivity_start').disabled
    page(at,'Analyse');page(at,'Sensitivitätsanalyse')
    assert widget(at,'number_input',prefix+':absolute:min').value==0.
    assert at.session_state[identity+':variants'] is None
    assert widget(at,'button',identity+':sensitivity_start').disabled
    assert not h.calls and not h.submitted


def test_common_preset_after_demand_retains_exact_15_variants_and_48_count(quantity_gui):
    h=quantity_gui;at=h.at;identity='eu_2024:hamburg_moorburg'
    select_quantity(at)
    widget(at,'button',identity+':common_preset').click();run(at)
    variants=at.session_state[identity+':variants']
    assert len(variants)==15 and PARAMETER not in {v['parameter'] for v in variants}
    points={parameter:[v['value'] for v in variants if v['parameter']==parameter] for parameter in {v['parameter'] for v in variants}}
    assert points['wind_capex_eur_per_kw']==[500,1000,3000]
    assert points['electricity_price_offset_eur_per_mwh']==[-50,50]
    assert points['real_wacc_multiplier']==pytest.approx([7/11,15/11])
    assert count(at)==48
    assert not widget(at,'button',identity+':sensitivity_start').disabled
    assert not h.calls and not h.submitted


def test_historical_namibia_hides_unproven_quantity_override_and_keeps_common_preset(quantity_gui):
    h=quantity_gui;at=h.at
    widget(at,'selectbox','study_selection').set_value('namibia');run(at)
    page(at,'Sensitivitätsanalyse')
    identity='namibia:namibia'
    assert not [button for button in at.button if button.key==identity+':demand_quantity_preset']
    assert 'H₂-Jahresnachfrage: Faktor zur Basis' not in widget(at,'multiselect',identity+':oat_parameters').options
    widget(at,'button',identity+':common_preset').click();run(at)
    assert len(at.session_state[identity+':variants'])==15
    assert count(at)==48
    assert not h.calls and not h.submitted


def test_quantity_and_categorical_profile_are_normal_parameters_without_factorial_expansion(quantity_gui):
    h=quantity_gui;at=h.at;identity='eu_2024:hamburg_moorburg'
    kind(at,'sensitivity')
    widget(at,'multiselect',identity+':oat_parameters').set_value([PARAMETER,'h2_delivery_profile']);run(at)
    assert widget(at,'multiselect',identity+':sens_profiles').value==['D0']
    assert widget(at,'multiselect',identity+'h2_delivery_profile:levels').value==['D0','D1','D2']
    assert count(at)==21  # (D0 * [one basis + four quantity changes] + D1 + D2) * three scenarios
    assert not h.calls and not h.submitted
    widget(at,'button',identity+':sensitivity_start').click();run(at)
    assert widget(at,'radio','navigation').value=='Sensitivitätsanalyse'
    plan=h.submitted[-1]
    assert plan['optimization_count']==21
    assert plan['gui_oat_design']['profile_only_levels']==['D1','D2']
    assert plan['gui_oat_design']['numeric_variants_crossed_with_profile_levels'] is False
    contexts={child['profile_id']:child for child in plan['plans']}
    assert [v['value'] for v in contexts['D0']['variants']]==FACTORS
    assert contexts['D1']['variants']==contexts['D2']['variants']==[]
    assert all(len(child['scenarios'])==3 for child in contexts.values())
    assert plan['gui_oat_design']['profile_input_receipt']['annual_h2_requested_kg']==10.


def test_saved_profile_comparison_uses_only_actual_100_percent_baselines(quantity_gui,monkeypatch):
    h=quantity_gui;at=h.at;identity='eu_2024:hamburg_moorburg'
    monkeypatch.setattr(result_loader,'load_sensitivity_comparisons',lambda *args,**kwargs:sensitivity_fixture(result_directory=h.rows[0]['__result_directory']))
    captured=[]
    def profile_figure(frame,**kwargs):captured.append(frame.copy());return plt.figure(figsize=(1,1))
    monkeypatch.setattr(plotting,'profile_comparison_figure',profile_figure)
    open_saved_sensitivity(at)
    widget(at,'selectbox',identity+':oat_view_parameter').set_value('h2_delivery_profile');run(at)
    assert len(captured[-1])==9
    assert set(captured[-1].demand_profile)=={'D0','D1','D2'}
    assert captured[-1].sensitivity_value.eq(1.).all()
    assert captured[-1].annual_h2_delivered_kg.eq(3650000).all()
    assert not [selector for selector in at.selectbox if selector.key==identity+':oat_view_profile']
    data=next(data for _,data,key in reversed(h.downloads) if key==identity+':sens_download')
    saved=pd.read_csv(io.BytesIO(data))
    assert len(saved)==9 and saved.sensitivity_value.eq(1.).all()
    assert not h.calls and not h.submitted


def sensitivity_fixture(*,label_baseline_as_demand=True,result_directory=None):
    rows=[]
    for profile in ['D0','D1','D2']:
        for scenario in ['S0','S1','S2']:
            for factor in [.5,.75,1,1.25,1.5]:
                rows.append({'sensitivity_parameter':PARAMETER if factor!=1 or label_baseline_as_demand else 'baseline',
                    'sensitivity_value':factor if factor!=1 or label_baseline_as_demand else float('nan'),
                    'scenario_id':scenario,'site_label':'Hamburg','demand_profile':profile,'profile':profile,
                    'solver_name':'scipy-highs','lcoh_eur_per_kg_h2':4+int(profile[1]),
                    'objective_eur_per_year':3650000*(4+int(profile[1]))*factor,
                    'annual_h2_delivered_kg':3650000*factor,
                    '__collection':'H₂-Nachfragemenge','case_id':'baseline' if factor==1 else str(factor),
                    **({'__result_directory':result_directory} if result_directory else {})})
    return pd.DataFrame(rows)


def test_saved_curve_profile_filter_matches_download_scope(quantity_gui,monkeypatch):
    h=quantity_gui;at=h.at;identity='eu_2024:hamburg_moorburg'
    monkeypatch.setattr(result_loader,'load_sensitivity_comparisons',lambda *args,**kwargs:sensitivity_fixture(result_directory=h.rows[0]['__result_directory']))
    captured=[]
    def curve(frame,**kwargs):captured.append(frame.copy());return plt.figure(figsize=(1,1))
    monkeypatch.setattr(plotting,'oat_curve_figure',curve)
    open_saved_sensitivity(at)
    assert widget(at,'selectbox',identity+':oat_collection').options==[
        'H₂-Nachfragemenge · Lieferprofile D0, D1, D2 · Solver scipy-highs']
    assert widget(at,'selectbox',identity+':oat_view_profile').value=='D0'
    assert set(captured[-1].demand_profile)=={'D0'}
    widget(at,'selectbox',identity+':oat_view_profile').set_value('D2');run(at)
    assert set(captured[-1].demand_profile)=={'D2'} and len(captured[-1])==15
    data=next(data for _,data,key in reversed(h.downloads) if key==identity+':sens_download')
    saved=pd.read_csv(io.BytesIO(data))
    assert len(saved)==15 and set(saved.demand_profile)=={'D2'}
    assert any('zeigen dieses Lieferprofil' in note.value for note in at.caption)
    assert not h.calls and not h.submitted


@pytest.mark.parametrize('mapped',[True,False])
def test_demand_curve_has_five_percent_points_including_one_baseline(mapped):
    frame=sensitivity_fixture(label_baseline_as_demand=mapped)
    figure=plotting.oat_curve_figure(frame[frame.demand_profile=='D1'],parameter=PARAMETER)
    try:
        lines=figure.axes[0].lines
        assert len(lines)==3
        assert all(list(line.get_xdata())==[50,75,100,125,150] for line in lines)
        assert all(list(line.get_ydata())==[5]*5 for line in lines)
        assert figure.axes[0].get_xlabel()=='H₂-Jahresnachfrage [% der Basis]'
    finally:plt.close(figure)


def write_saved_gui_job(root,job_id,profiles,*,parameter=PARAMETER,lcoh=4.):
    """Persist minimal native exports and their hash-bound GUI plan receipt."""
    job=root/'outputs_h2/gui_runs'/job_id
    executions=[]
    baseline_paths={}
    scenarios={'reference':'S0','red_monthly':'S1','red_hourly':'S2'}
    for profile in profiles:
        output=job/profile
        output.mkdir(parents=True)
        records=[]
        variant_values=[.5,.75,1.25,1.5] if parameter==PARAMETER else [750.,1250.]
        for value in [None,*variant_values]:
            case_id='baseline' if value is None else 'variant_'+str(value)
            demand_factor=value if parameter==PARAMETER and value is not None else 1.
            for scenario,scenario_id in scenarios.items():
                directory=output/'runs'/case_id/(scenario_id+'_'+scenario)
                directory.mkdir(parents=True)
                data=pd.DataFrame({'timestamp':['2024-01-01T00:00:00Z','2024-01-01T01:00:00Z'],
                    'h2_demand':[5*demand_factor,5*demand_factor]})
                data.to_csv(directory/'validated_input.csv',index=False)
                data.to_csv(directory/'hourly_operation.csv',index=False)
                input_hash=hashlib.sha256((directory/'validated_input.csv').read_bytes()).hexdigest()
                summary={'scenario':scenario,'input_sha256':input_hash,'solver_name':'scipy-highs',
                    'solver_status':'optimal','objective_eur_per_year':10*demand_factor*lcoh,
                    'lcoh_eur_per_kg_h2':lcoh,'annual_h2_delivered_kg':10*demand_factor,
                    'pv_capacity_mw':demand_factor,'wind_capacity_mw':0.,'electrolyzer_capacity_mw':demand_factor,
                    'compressor_capacity_mw':.1*demand_factor,'h2_storage_capacity_kg':demand_factor}
                pd.DataFrame([summary]).to_csv(directory/'summary.csv',index=False)
                metadata={'schema_version':'fixture','scenario':scenario,'input':{'sha256':input_hash},
                    'model_parameters':{'quantity':{'value':demand_factor},'pv_capex':{'value':value if parameter!='h2_demand_multiplier' and value is not None else 1000}},
                    'calendar_scope':{'number_of_hours':2},'model_calendar':{'year':2024},
                    'software':{'fixture':'saved native file contract'},'result':summary}
                (directory/'run_metadata.json').write_text(json.dumps(metadata),encoding='utf-8')
                records.append({**summary,'case_id':case_id,'parameter':'baseline' if value is None else parameter,
                    'value':value,'result_directory':str(directory.relative_to(output))})
                if value is None:baseline_paths[(profile,scenario_id)]=str(directory.resolve())
        pd.DataFrame(records).to_csv(output/'sensitivity_comparison.csv',index=False)
        executions.append({'study_id':'eu_2024','site_id':'hamburg_moorburg','profile_id':profile,
            'output_directory':str(output.resolve()),'code_sha256':{'fixture.py':'1'*64}})
    plan_path=job/'plan.json'
    plan_path.write_text(json.dumps({'execution_plans':executions}),encoding='utf-8')
    (job/'plan.sha256').write_text(hashlib.sha256(plan_path.read_bytes()).hexdigest(),encoding='ascii')
    (job/'status.json').write_text(json.dumps({'state':'completed','validation_status':'not_run'}),encoding='utf-8')
    return baseline_paths


def test_real_saved_gui_loader_keeps_same_execution_demand_baseline_and_cost_family_contract(tmp_path,monkeypatch):
    def no_process(*args,**kwargs):pytest.fail('Reading saved GUI exports must not start any subprocess')
    monkeypatch.setattr(subprocess,'run',no_process)
    monkeypatch.setattr(subprocess,'Popen',no_process)
    profile_ids=['D0','D1','D2']
    native_baselines=write_saved_gui_job(tmp_path,'quantity_job',profile_ids)
    other_baselines=write_saved_gui_job(tmp_path,'different_quantity_job',['D1'],lcoh=9.)
    cost_baselines=write_saved_gui_job(tmp_path,'cost_only_job',['D0'],parameter='pv_capex_eur_per_kw')
    site=SimpleNamespace(study_id='eu_2024',site_id='hamburg_moorburg',label='Hamburg',
        profiles=dict.fromkeys(profile_ids),historical=False,sensitivity_sources=[])
    registry=SimpleNamespace(repo_root=tmp_path,get_site=lambda study,site_id:site)
    table=read_saved_sensitivities(registry,'eu_2024','hamburg_moorburg')
    assert len(table)==66  # 3 demand profiles * 15 + a distinct 15-point family + 6 cost points.
    cost=table[table.gui_job_id=='cost_only_job']
    assert len(cost)==6 and 'baseline' not in set(cost.case_id)
    assert not set(cost_baselines.values()) & set(cost['__result_directory'])
    for profile in profile_ids:
        family=table[(table.gui_job_id=='quantity_job') & (table.demand_profile==profile)]
        assert len(family)==15 and family['__collection_id'].nunique()==1
        assert family['__collection_execution_count'].eq(1).all()
        base=family[family.case_id=='baseline']
        assert len(base)==3
        for _,row in base.iterrows():
            assert row['__result_directory']==native_baselines[(profile,row.scenario_id)]
            assert row['__result_directory'] not in other_baselines.values()
            copies=json.loads(row['__result_copies'])
            assert len(copies)==1 and copies[0]['gui_job_id']=='quantity_job'
            assert copies[0]['validation_evidence']['status']=='not_found'
        figure=plotting.oat_curve_figure(family,parameter=PARAMETER)
        try:
            lines=figure.axes[0].lines
            assert len(lines)==3
            assert all(list(line.get_xdata())==[50,75,100,125,150] for line in lines)
            assert all(list(line.get_ydata())==[4]*5 for line in lines)
        finally:plt.close(figure)


def test_real_gui_profile_families_have_distinct_dropdown_labels(quantity_gui,tmp_path,monkeypatch):
    h=quantity_gui;at=h.at;identity='eu_2024:hamburg_moorburg'
    write_saved_gui_job(tmp_path,'quantity_job',['D0','D1','D2'])
    site=SimpleNamespace(study_id='eu_2024',site_id='hamburg_moorburg',label='Hamburg',
        profiles=dict.fromkeys(['D0','D1','D2']),historical=False,sensitivity_sources=[])
    registry=SimpleNamespace(repo_root=tmp_path,get_site=lambda study,site_id:site)
    table=read_saved_sensitivities(registry,'eu_2024','hamburg_moorburg')
    assert len(table)==45 and table['__collection_id'].nunique()==3
    monkeypatch.setattr(result_loader,'load_sensitivity_comparisons',lambda *args,**kwargs:table.copy())
    open_saved_sensitivity(at)
    selector=widget(at,'selectbox',identity+':oat_collection')
    assert len(selector.options)==3 and len(set(selector.options))==3
    for profile in ['D0','D1','D2']:
        label=next(label for label in selector.options if 'Lieferprofile '+profile+' ·' in label)
        assert label.startswith('GUI quantity_job · completed') and label.endswith('Solver scipy-highs')
        cid=table.loc[table.demand_profile==profile,'__collection_id'].iloc[0]
        widget(at,'selectbox',identity+':oat_collection').set_value(cid);run(at)
        assert widget(at,'selectbox',identity+':oat_view_profile').options==[
            {'D0':'D0 · Lieferung rund um die Uhr','D1':'D1 · Lieferung täglich 08–20 Uhr','D2':'D2 · Lieferung Mo–Fr 08–20 Uhr'}[profile]]
        data=next(data for _,data,key in reversed(h.downloads) if key==identity+':sens_download')
        saved=pd.read_csv(io.BytesIO(data))
        assert len(saved)==15 and set(saved.demand_profile)=={profile}
    assert not h.calls and not h.submitted
