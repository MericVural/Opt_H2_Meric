"""Persisted inline results are selected-job native exports with bound evidence."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys

import pandas as pd
import pytest

GUI_ROOT = Path(os.environ.get('H2_GUI_SOURCE_ROOT', Path(__file__).resolve().parents[2])).resolve()
sys.path.insert(0, str(GUI_ROOT))
MODEL_ROOT = Path(os.environ.get('H2_REPO_ROOT', GUI_ROOT)).resolve()
if str(MODEL_ROOT) not in sys.path:
    sys.path.append(str(MODEL_ROOT))
from gui.result_loader import load_job_results
from gui.result_loader import load_sensitivity_comparisons
from gui.checks.demand_quantity_regression import write_saved_gui_job
from types import SimpleNamespace


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rewrite_plan(job, update):
    path = job/'plan.json'
    data = json.loads(path.read_text(encoding='utf-8'))
    update(data)
    path.write_text(json.dumps(data), encoding='utf-8')
    (job/'plan.sha256').write_text(digest(path), encoding='ascii')


@pytest.fixture(autouse=True)
def prohibit_processes(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('Reading inline results must not start a solver or worker')
    monkeypatch.setattr(subprocess, 'run', forbidden)
    monkeypatch.setattr(subprocess, 'Popen', forbidden)


def test_inline_exact_job_keeps_all_profiles_baselines_and_variants_and_sources(tmp_path):
    original = write_saved_gui_job(tmp_path, 'chosen', ['D0','D1','D2'])
    other = write_saved_gui_job(tmp_path, 'other', ['D0'], lcoh=9.)
    job = tmp_path/'outputs_h2/gui_runs/chosen'
    before = {str(p):digest(p) for p in tmp_path.rglob('*') if p.is_file()}
    table = load_job_results(job, tmp_path)
    assert len(table) == 45
    assert set(table.demand_profile) == {'D0','D1','D2'}
    assert set(table.gui_job_id) == {'chosen'}
    assert table.lcoh_eur_per_kg_h2.eq(4.).all()
    assert set(table[table.case_id == 'baseline']['__result_directory']) == set(original.values())
    assert not set(other.values()) & set(table['__result_directory'])
    assert set(table.sensitivity_parameter) == {'baseline','h2_demand_multiplier'}
    for _, row in table.iterrows():
        assert row['__source_csv_sha256'] == digest(row['__source_csv'])
        assert row.gui_job_plan_sha256 == digest(job/'plan.json')
        copies = json.loads(row['__result_copies'])
        assert len(copies) == 1
        assert copies[0]['validation_evidence']['status'] == 'not_found'
    assert before == {str(p):digest(p) for p in tmp_path.rglob('*') if p.is_file()}


@pytest.mark.parametrize('state',['running','failed','completed'])
def test_inline_job_status_cannot_replace_bound_native_validation(tmp_path, state):
    write_saved_gui_job(tmp_path, 'chosen', ['D0'])
    job = tmp_path/'outputs_h2/gui_runs/chosen'
    (job/'status.json').write_text(json.dumps({'state':state,'validation_status':'passed'}), encoding='utf-8')
    table = load_job_results(job, tmp_path)
    assert len(table) == 15
    assert table.gui_job_state.eq(state).all()
    for _, row in table.iterrows():
        assert json.loads(row['__result_copies'])[0]['validation_evidence']['status'] == 'not_found'
    if state != 'completed':
        assert table.source_label.str.contains('teilweise / nicht vollständig validiert', regex=False).all()


def test_inline_own_validation_receipt_is_bound_and_changed_source_stays_failed(tmp_path):
    write_saved_gui_job(tmp_path, 'chosen', ['D0'])
    job = tmp_path/'outputs_h2/gui_runs/chosen'
    csv = job/'D0/sensitivity_comparison.csv'
    report = job/'D0/validation/validation_report.json'
    report.parent.mkdir()
    report.write_text(json.dumps({'all_checks_passed':True,
        'source_comparison':{'path':str(csv),'sha256':digest(csv)}}), encoding='utf-8')
    table = load_job_results(job, tmp_path)
    for _, row in table.iterrows():
        evidence = json.loads(row['__result_copies'])[0]['validation_evidence']
        assert evidence['status'] == 'passed'
        assert evidence['report_sha256'] == digest(report)
        assert evidence['source_comparison_hash_matches'] is True
    csv.write_bytes(csv.read_bytes()+b'\n')
    changed = load_job_results(job, tmp_path)
    assert len(changed) == 15
    assert {json.loads(row['__result_copies'])[0]['validation_evidence']['status']
            for _, row in changed.iterrows()} == {'failed_or_changed'}


@pytest.mark.parametrize('tamper',['plan_hash','missing_hash','outside_job','outside_outputs'])
def test_inline_rejects_unbound_or_foreign_job_paths(tmp_path, tamper):
    write_saved_gui_job(tmp_path, 'chosen', ['D0'])
    job = tmp_path/'outputs_h2/gui_runs/chosen'
    if tamper == 'plan_hash':
        (job/'plan.json').write_bytes((job/'plan.json').read_bytes()+b' ')
    elif tamper == 'missing_hash':
        (job/'plan.sha256').unlink()
    elif tamper == 'outside_job':
        write_saved_gui_job(tmp_path, 'other', ['D0'])
        rewrite_plan(job, lambda record:record['execution_plans'][0].update(
            output_directory=str(tmp_path/'outputs_h2/gui_runs/other/D0')))
    else:
        rewrite_plan(job, lambda record:record['execution_plans'][0].update(output_directory=str(tmp_path)))
    with pytest.raises(ValueError):
        load_job_results(job, tmp_path)


def test_inline_fallback_for_failed_partial_worker_keeps_saved_native_cases(tmp_path):
    write_saved_gui_job(tmp_path, 'chosen', ['D0'])
    job = tmp_path/'outputs_h2/gui_runs/chosen'
    (job/'D0/sensitivity_comparison.csv').unlink()
    (job/'status.json').write_text(json.dumps({'state':'failed','validation_status':'not_run'}), encoding='utf-8')
    table = load_job_results(job, tmp_path)
    assert len(table) == 15
    assert table.gui_job_state.eq('failed').all()
    assert table.source_label.str.contains('teilweise', regex=False).all()
    assert all(Path(p).name == 'summary.csv' for p in table['__source_csv'])
    assert len(table[table.case_id == 'baseline']) == 3


def test_inline_rejects_comparison_rows_referencing_another_job(tmp_path):
    write_saved_gui_job(tmp_path, 'chosen', ['D0'])
    foreign = write_saved_gui_job(tmp_path, 'foreign', ['D0'])
    job = tmp_path/'outputs_h2/gui_runs/chosen'
    csv = job/'D0/sensitivity_comparison.csv'
    table = pd.read_csv(csv)
    table.loc[0,'source_result_directory'] = foreign[('D0','S0')]
    table.to_csv(csv,index=False)
    with pytest.raises(ValueError, match='Auftragsausführung'):
        load_job_results(job, tmp_path)


def test_inline_returns_empty_when_selected_job_has_no_exports(tmp_path):
    write_saved_gui_job(tmp_path, 'chosen', ['D0'])
    job = tmp_path/'outputs_h2/gui_runs/chosen'
    rewrite_plan(job, lambda record:record['execution_plans'][0].update(output_directory=str(job/'empty')))
    assert load_job_results(job, tmp_path).empty


def profile_oat_job(root, name, profiles=('D0','D1','D2')):
    write_saved_gui_job(root, name, list(profiles), parameter='pv_capex_eur_per_kw')
    job = root/'outputs_h2/gui_runs'/name
    for profile in profiles:
        if profile != 'D0':
            csv = job/profile/'sensitivity_comparison.csv'
            table = pd.read_csv(csv)
            table[table.case_id == 'baseline'].to_csv(csv, index=False)
    def metadata(record):
        record['requested_plan'] = {'gui_oat_design':{
            'base_profiles':['D0'], 'profile_parameter':'h2_delivery_profile',
            'profile_levels':list(profiles),
            'numeric_variants_crossed_with_profile_levels':False}}
        for child in record['execution_plans']:
            child['gui_oat_design'] = {
                'profile_parameter':'h2_delivery_profile',
                'role':'numeric_base_context' if child['profile_id'] == 'D0' else 'profile_only_level'}
    rewrite_plan(job, metadata)
    return job


def fixture_registry(root):
    site = SimpleNamespace(study_id='eu_2024',site_id='hamburg_moorburg',label='Hamburg',
        profiles=dict.fromkeys(['D0','D1','D2']), historical=False, sensitivity_sources=[])
    return SimpleNamespace(repo_root=root,get_site=lambda study, site_id:site)


def test_saved_profile_oat_is_one_family_with_baselines_and_no_factorial_variants(tmp_path):
    job = profile_oat_job(tmp_path, 'profile_oat')
    table = load_sensitivity_comparisons(fixture_registry(tmp_path),'eu_2024','hamburg_moorburg')
    assert len(table) == 15
    assert table['__collection_id'].nunique() == 1
    assert table['__gui_oat_family_id'].nunique() == 1
    assert set(table[table.case_id == 'baseline'].demand_profile) == {'D0','D1','D2'}
    assert set(table[table.case_id != 'baseline'].demand_profile) == {'D0'}
    assert len(table[table.case_id == 'baseline']) == 9
    assert set(table.sensitivity_parameter) == {'baseline','pv_capex_eur_per_kw'}
    for _, row in table.iterrows():
        original = json.loads(row['__result_copies'])[0]
        assert original['__source_csv_sha256'] == digest(original['__source_csv'])
        assert original['gui_job_plan_sha256'] == digest(job/'plan.json')
        assert original['validation_evidence']['status'] == 'not_found'


def test_saved_new_numeric_only_oat_preserves_own_baseline_old_family_contract_unchanged(tmp_path):
    write_saved_gui_job(tmp_path, 'new_numeric', ['D0'], parameter='pv_capex_eur_per_kw')
    job = tmp_path/'outputs_h2/gui_runs/new_numeric'
    rewrite_plan(job, lambda record:record.update(requested_plan={'gui_oat_design':{
        'base_profiles':['D0'], 'profile_parameter':None,'profile_levels':[],
        'numeric_variants_crossed_with_profile_levels':False}}))
    write_saved_gui_job(tmp_path, 'old_numeric', ['D1'], parameter='pv_capex_eur_per_kw')
    table = load_sensitivity_comparisons(fixture_registry(tmp_path),'eu_2024','hamburg_moorburg')
    new = table[table.gui_job_id == 'new_numeric']
    old = table[table.gui_job_id == 'old_numeric']
    assert len(new) == 9 and len(new[new.case_id == 'baseline']) == 3
    assert len(old) == 6 and not old.case_id.eq('baseline').any()
    assert json.loads(old.iloc[0]['__result_copies'])[0].get('__gui_oat_family_id') is None


def test_complete_equal_new_profile_jobs_group_as_whole_with_all_child_sources(tmp_path):
    profile_oat_job(tmp_path,'original')
    profile_oat_job(tmp_path,'repeat')
    table = load_sensitivity_comparisons(fixture_registry(tmp_path),'eu_2024','hamburg_moorburg')
    assert len(table) == 15 and table['__collection_id'].nunique() == 1
    assert table['__collection_execution_count'].eq(2).all()
    assert table['__execution_count'].eq(2).all()
    originals = [original for _, row in table.iterrows() for original in json.loads(row['__result_copies'])]
    assert {original['gui_job_id'] for original in originals} == {'original','repeat'}
    assert len({original['__source_csv'] for original in originals}) == 6
    assert {original['demand_profile'] for original in originals} == {'D0','D1','D2'}


def test_partially_overlapping_new_profile_jobs_remain_complete_separate_families(tmp_path):
    profile_oat_job(tmp_path,'full')
    profile_oat_job(tmp_path,'partial',profiles=('D0','D1'))
    table = load_sensitivity_comparisons(fixture_registry(tmp_path),'eu_2024','hamburg_moorburg')
    assert len(table) == 27 and table['__collection_id'].nunique() == 2
    assert len(table[table.gui_job_id == 'full']) == 15
    assert len(table[table.gui_job_id == 'partial']) == 12
    assert table['__collection_execution_count'].eq(1).all()
