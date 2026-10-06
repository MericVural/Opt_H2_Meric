"""GUI adapter protection and actual native runner equivalence, no annual solves."""
from pathlib import Path
import sys
import json
import subprocess
import os
import numpy as np
import pandas as pd
import pytest

G=Path(os.environ.get('H2_GUI_SOURCE_ROOT',Path(__file__).resolve().parents[1])).resolve()
sys.path.insert(0,str(G))
from gui import model_adapter as adapter
from gui.gui_utils import parse_wacc_percent, parse_values
from gui.case_study_registry import load_registry

ROOT=Path(os.environ.get('H2_MODEL_REPO',G)).resolve()
PYTHON=Path(os.environ.get('H2_MODEL_PYTHON',sys.executable)).resolve()

def artifact_root(tmp_path):
    """Default to pytest isolation; an explicit short root avoids Windows MAX_PATH."""
    configured=os.environ.get('H2_GUI_TEST_ARTIFACT_ROOT')
    selected=Path(configured).resolve() if configured else tmp_path
    selected.mkdir(parents=True,exist_ok=True)
    return selected

@pytest.fixture
def tiny_input(tmp_path):
    t=np.arange(24)
    data=pd.DataFrame({'timestamp':pd.date_range('2025-01-01',periods=24,freq='h',tz='UTC'),
        'pv_capacity_factor':np.maximum(0,np.sin((t-6)*np.pi/12))*.75,
        'wind_capacity_factor':.25+.1*np.cos(t*np.pi/12),
        'electricity_price':80.+40.*np.cos(t*np.pi/12),
        'grid_emission_factor':220.,'h2_demand':416.6666666666667})
    path=tmp_path/'24h_input.csv'; data.to_csv(path,index=False)
    return path

def tiny_options():
    return dict(study_id='synthetic_regression',site_id='namibia_reference',runner_kind='legacy',
                uniform_wacc_percent='11',uniform_wacc_source='Explicit11percent synthetic regression fixture',
                model_python=PYTHON)

def test_requirement04_and05_solver_and_scenarios_forwarded(tiny_input):
    plan=adapter.build_single_plan(ROOT,tiny_input,('red_monthly','red_hourly'),'scipy-highs',**tiny_options())
    assert plan['solver']=='scipy-highs'
    assert plan['scenarios']==['red_monthly','red_hourly']
    assert plan['native_eu_site'] is None and plan['site_id']=='namibia_reference'
    assert plan['optimization_count']==2

def test_requirement06_demand_profile_selected_from_registry():
    reg=load_registry(ROOT)
    plan=adapter.build_plan(reg,'eu_2024','hamburg_moorburg',['D1','D2'],['reference'],'scipy-highs',model_python=PYTHON)
    assert [p['profile_id'] for p in plan['plans']]==['D1','D2']
    assert all(p['native_eu_site']=='hamburg_moorburg' for p in plan['plans'])
    assert 'D1' in plan['plans'][0]['input']['path'] and 'D2' in plan['plans'][1]['input']['path']
    assert plan['optimization_count']==2
    for item in plan['plans']:
        assert item['expected_hours']==8784
        assert item['input_context']['annual_h2_requested_kg']==pytest.approx(3650000)
    with pytest.raises(ValueError,match='Nachfrageprofil'):
        adapter.build_plan(reg,'namibia','namibia',['D2'],['reference'],'scipy-highs',model_python=PYTHON)

@pytest.mark.parametrize('value', ['3.30','3,30','3,30 %',3.3])
def test_requirement07_wacc_percent_to_fraction(value):
    assert parse_wacc_percent(value)==pytest.approx(.033)

@pytest.mark.parametrize('value', ['330','100','-1','nan','inf',True])
def test_wacc_invalid_percent_not_silently_reinterpreted(value):
    with pytest.raises(ValueError):parse_wacc_percent(value)

def test_requirement08_sensitivity_values_generated_without_grid_drift():
    assert parse_values(min_value='-30',max_value='30',step='10',percent=True)==[-.3,-.2,-.1,0,.1,.2,.3]
    assert parse_values('0,9;1;1,1')==[.9,1.,1.1]
    assert parse_values(min_value='.1',max_value='.35',step='.1')==[.1,.2,.3]
    for kwargs in ({'explicit_text':'1;1'},{'min_value':0,'max_value':1,'step':0},
                   {'explicit_text':'1','min_value':0,'max_value':1,'step':1}):
        with pytest.raises(ValueError):parse_values(**kwargs)

def test_requirement09_OAT_is_sum_of_cases_not_cartesian_product(tiny_input):
    specs=[{'parameter':'pv_capex_eur_per_kw','values':[690.75,1151.25]},
           {'parameter':'wind_capex_eur_per_kw','values':[889.75,2669.25]},
           {'parameter':'electrolyzer_capex_eur_per_kw','values':[972.75],'active':False}]
    plan=adapter.build_sensitivity_plan(ROOT,tiny_input,('reference','red_monthly','red_hourly'),
        'scipy-highs',variants=specs,**tiny_options())
    assert len(plan['variants'])==4
    assert plan['optimization_count']==15
    rows=adapter.case_table_rows(plan)
    assert len(rows)==5 and rows[0]['parameter']=='baseline'
    assert [r['parameter'] for r in rows[1:]]==['pv_capex_eur_per_kw']*2+['wind_capex_eur_per_kw']*2
    assert all(r['unit']=='EUR_2023/kW' for r in rows[1:])

def test_requirement11_missing_Gurobi_has_message_and_no_silent_fallback(tiny_input,monkeypatch):
    monkeypatch.setattr(adapter,'probe_solvers',lambda *args,**kwargs:{'solvers':{'gurobi':{'available':False,'reason':'gurobipy fehlt'}}})
    with pytest.raises(ValueError,match='gurobipy fehlt.*SciPy/HiGHS'):
        adapter.build_single_plan(ROOT,tiny_input,('reference',),'gurobi',**tiny_options())

def test_invalid_request_rejected_before_solver(tiny_input):
    with pytest.raises(ValueError,match='historische'):
        adapter.build_single_plan(ROOT,tiny_input,can_run=False,**tiny_options())
    with pytest.raises(ValueError,match='Unbekannter Solver'):
        adapter.build_single_plan(ROOT,tiny_input,solver='invented',**tiny_options())
    with pytest.raises(ValueError):
        adapter.build_single_plan(ROOT,tiny_input,scenarios=('invented',),**tiny_options())
    with pytest.raises(ValueError,match='gemischt'):
        adapter.build_single_plan(ROOT,tiny_input,site_id='hamburg_moorburg',uniform_wacc_percent='11',
                                  uniform_wacc_source='fixture',runner_kind='eu')
    with pytest.raises(ValueError):
        adapter.build_sensitivity_plan(ROOT,tiny_input,variants=[{'parameter':'pv_capex_eur_per_kw','value':-1}],**tiny_options())

def test_selected_source_change_invalidates_plan(tiny_input):
    plan=adapter.build_single_plan(ROOT,tiny_input,('reference',),'scipy-highs',**tiny_options())
    tiny_input.write_text(tiny_input.read_text(encoding='utf-8')+'\n',encoding='utf-8')
    with pytest.raises(ValueError,match='Quelle wurde'):
        adapter.preflight_plan(plan)

def test_requirement13_actual_native_CLI_vs_GUI_adapter_regression(tiny_input,tmp_path):
    from gui.jobs import prepare_job, run_job
    direct=tmp_path/'direct_native_CLI'
    argv=[str(PYTHON),str(ROOT/'run_h2_scenarios.py'),'--input',str(tiny_input),
          '--output-dir',str(direct),'--solver','scipy-highs','--uniform-real-wacc','.11',
          '--wacc-source',tiny_options()['uniform_wacc_source']]
    result=subprocess.run(argv,text=True,capture_output=True,shell=False,timeout=120,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0,
        env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONIOENCODING':'utf-8'})
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    plan=adapter.build_single_plan(ROOT,tiny_input,('reference','red_monthly','red_hourly'),
        'scipy-highs',**tiny_options())
    root=artifact_root(tmp_path)
    job=prepare_job(plan,root/'jobs')
    status=run_job(job)
    assert status['state']=='completed',status
    assert status['completed_cases']==status['total_cases']==3
    assert status['validation_status']=='passed'
    record=json.loads((job/'plan.json').read_text(encoding='utf-8'))
    output=Path(record['execution_plans'][0]['output_directory'])/'runs/baseline'
    observations=[]
    for scenario,folder in zip(('reference','red_monthly','red_hourly'),('S0_reference','S1_red_monthly','S2_red_hourly')):
        cli=pd.read_csv(direct/folder/'summary.csv').iloc[0]
        gui=pd.read_csv(output/scenario/'summary.csv').iloc[0]
        assert gui.solver_status==cli.solver_status=='optimal'
        assert gui.solver_name==cli.solver_name
        assert gui.scenario==cli.scenario==scenario
        assert gui.objective_eur_per_year==pytest.approx(cli.objective_eur_per_year,abs=.05,rel=1e-10)
        assert gui.lcoh_eur_per_kg_h2==pytest.approx(cli.lcoh_eur_per_kg_h2,abs=1e-8,rel=1e-10)
        for capacity in ('pv_capacity_mw','wind_capacity_mw','electrolyzer_capacity_mw','compressor_capacity_mw','h2_storage_capacity_kg'):
            assert gui[capacity]==pytest.approx(cli[capacity],abs=1e-6,rel=1e-9)
        assert gui.max_electricity_balance_residual_mwh<=1e-6
        assert cli.max_electricity_balance_residual_mwh<=1e-6
        assert gui.max_hydrogen_balance_residual_kg<=1e-4
        assert cli.max_hydrogen_balance_residual_kg<=1e-4
        cli_hourly=pd.read_csv(direct/folder/'hourly_operation.csv')
        gui_hourly=pd.read_csv(output/scenario/'hourly_operation.csv')
        assert gui_hourly.grid_import_mwh.sum()*gui.annualization_factor==pytest.approx(
            cli_hourly.grid_import_mwh.sum()*cli.annualization_factor,abs=1e-6,rel=1e-9)
        for field in ('annual_h2_produced_kg','annual_h2_delivered_kg',
                      'annual_grid_emissions_kg_co2e','annual_regulatory_emissions_kg_co2e',
                      'max_red_iii_temporal_deficit_mwh'):
            assert gui[field]==pytest.approx(cli[field],abs=1e-5,rel=1e-9)
        cli_params=json.loads((direct/folder/'run_metadata.json').read_text(encoding='utf-8'))['model_parameters']
        gui_params=json.loads((output/scenario/'run_metadata.json').read_text(encoding='utf-8'))['model_parameters']
        assert {k:(v['value'],v['unit'],v['reference_year']) for k,v in cli_params.items()}=={k:(v['value'],v['unit'],v['reference_year']) for k,v in gui_params.items()}
        observations.append({'scenario':scenario,'CLI_objective':float(cli.objective_eur_per_year),
            'GUI_objective':float(gui.objective_eur_per_year),'objective_difference':float(gui.objective_eur_per_year-cli.objective_eur_per_year),
            'CLI_LCOH':float(cli.lcoh_eur_per_kg_h2),'GUI_LCOH':float(gui.lcoh_eur_per_kg_h2)})
    (root/'GUI_CLI_REGRESSION.json').write_text(json.dumps({'actual_direct_native_CLI':argv,
        'GUI_job_path':str(job),'hours':24,'annual_solver_calls':0,'small_optimizer_calls':6,
        'all_three_scenarios_passed':True,'GUI_native_validation_status':status['validation_status'],
        'comparisons':observations},indent=2)+'\n',encoding='utf-8')

def test_frozen_input_corruption_becomes_failed_job_not_success(tiny_input,tmp_path):
    from gui.jobs import prepare_job,run_job
    plan=adapter.build_single_plan(ROOT,tiny_input,('reference',),'scipy-highs',**tiny_options())
    job=prepare_job(plan,artifact_root(tmp_path)/'jobs')
    record=json.loads((job/'plan.json').read_text(encoding='utf-8'))
    copied=Path(record['execution_plans'][0]['input']['path'])
    copied.write_text(copied.read_text(encoding='utf-8')+'\n',encoding='utf-8')
    status=run_job(job)
    assert status['state']=='failed'
    assert status['completed_cases']==0
    assert 'Gefrorene Eingabe' in status['error']
    assert status['validation_status']=='failed'
    assert not list((job/'runs').glob('**/summary.csv'))

def test_tampered_plan_receipt_persists_failed_status_before_solver(tiny_input,tmp_path,monkeypatch):
    from gui.jobs import prepare_job,run_job
    plan=adapter.build_single_plan(ROOT,tiny_input,('reference',),'scipy-highs',**tiny_options())
    job=prepare_job(plan,artifact_root(tmp_path)/'jobs')
    (job/'plan.json').write_text((job/'plan.json').read_text(encoding='utf-8')+'\n',encoding='utf-8')
    def prohibited(*args,**kwargs):raise AssertionError('Corrupt plan must not start a solver')
    monkeypatch.setattr(subprocess,'Popen',prohibited)
    status=run_job(job)
    assert status['state']=='failed' and status['validation_status']=='failed'
    assert status['completed_cases']==0 and 'GUI-Plan' in status['error']
    persisted=json.loads((job/'status.json').read_text(encoding='utf-8'))
    assert persisted['state']=='failed'

def test_missing_gurobipy_import_is_optional_and_highs_remains_available(monkeypatch):
    import builtins
    original=builtins.__import__
    def without_gurobi(name,*args,**kwargs):
        if name=='gurobipy':raise ModuleNotFoundError("No module named 'gurobipy'")
        return original(name,*args,**kwargs)
    monkeypatch.setattr(builtins,'__import__',without_gurobi)
    receipt=adapter._native_action('solvers',str(ROOT),{'annual_hours':24})
    assert receipt['ok'] is True
    assert receipt['solvers']['scipy-highs']['available'] is True
    assert receipt['solvers']['gurobi']['available'] is False
    assert 'gurobipy' in receipt['solvers']['gurobi']['reason']

def test_S0_only_keeps_native_partial_validation_visible(tiny_input,tmp_path):
    from gui.jobs import prepare_job,run_job
    plan=adapter.build_single_plan(ROOT,tiny_input,('reference',),'scipy-highs',**tiny_options())
    job=prepare_job(plan,artifact_root(tmp_path)/'jobs')
    status=run_job(job)
    assert status['state']=='completed',status
    assert status['completed_cases']==status['total_cases']==1
    assert status['validation_status']=='partial_scenario_selection'
    record=json.loads((job/'plan.json').read_text(encoding='utf-8'))
    directory=Path(record['execution_plans'][0]['output_directory'])/'runs/baseline/validation'
    report=json.loads((directory/'validation_report.json').read_text(encoding='utf-8'))
    assert report['all_checks_passed'] is False
    checks=pd.read_csv(directory/'validation_checks.csv')
    assert set(checks.loc[checks.passed==False,'check_id'])=={'core_scenarios_present'}

def test_frozen_GUI_worker_corruption_rejected_before_solver(tiny_input,tmp_path,monkeypatch):
    from gui.jobs import prepare_job,run_job
    plan=adapter.build_single_plan(ROOT,tiny_input,('reference',),'scipy-highs',**tiny_options())
    job=prepare_job(plan,artifact_root(tmp_path)/'jobs')
    copied=job/'evidence/gui/model_adapter.py'
    copied.write_text(copied.read_text(encoding='utf-8')+'\n',encoding='utf-8')
    def prohibited(*args,**kwargs):raise AssertionError('Corrupt GUI worker must not start a solver')
    monkeypatch.setattr(subprocess,'Popen',prohibited)
    status=run_job(job)
    assert status['state']=='failed' and status['completed_cases']==0
    assert status['validation_status']=='failed'
    assert 'Gefrorene Eingabe' in status['error']
