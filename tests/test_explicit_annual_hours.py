"""Calendar accounting tests: no historical EU full-year solve is performed."""
from dataclasses import replace
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from config_h2 import DEFAULT_CONFIG, iter_scalar_parameters
import eu_site_configuration as eu
from eu_test_designs import write_calendar_design
from h2_input_data import HourlyInputError, validate_hourly_input
from opt_hydrogen_functions import optimize_hydrogen_system
from run_h2_scenarios import run_h2_scenarios
from run_single_site_h2 import H2RunError, _load_emission_factor_metadata, _require_eu_input_context_matches
from validate_h2_results import _check_annualization_contract, _independent_source_contract_matches, validate_h2_results

def selected(tmp_path,year=2024):
    path=write_calendar_design(eu.DEFAULT_EU_DESIGN_PATH,tmp_path/f'design_{year}.json',year)
    return eu.load_eu_site_configuration('hamburg_moorburg',design_path=path)

def frame(year,hours,period=24):
    return pd.DataFrame({
        'timestamp':pd.date_range(f'{year}-01-01',periods=period,freq='h',tz='UTC'),
        'pv_capacity_factor':np.ones(period),'wind_capacity_factor':np.zeros(period),
        'electricity_price':np.zeros(period),'grid_emission_factor':np.full(period,300.),
        'h2_demand':np.full(period,3650000/hours),
    })

def test_legacy_defaults_remain_365_days():
    assert DEFAULT_CONFIG.study.annual_hours.value==8760
    assert DEFAULT_CONFIG.study.annualization_basis=='legacy_365_day_reference'
    assert DEFAULT_CONFIG.study.h2_demand_kg_per_year==3650000

@pytest.mark.parametrize('year,hours',[(2024,8784),(2025,8760)])
def test_both_historical_calendars_keep_fixed_annual_volume(tmp_path,year,hours):
    configuration=selected(tmp_path,year)
    study=configuration.config.study
    assert study.annual_hours.value==hours
    assert study.number_of_time_steps.value==hours
    assert study.annualization_basis=='historical_calendar_year'
    assert study.h2_demand_kg_per_year==pytest.approx(3650000)
    assert study.h2_demand_kg_per_hour==pytest.approx(3650000/hours)
    study.validate()

@pytest.mark.parametrize('basis,hours', [('historical_calendar_year',8760),('legacy_365_day_reference',8784),('invented',8784)])
def test_configuration_rejects_contradictory_reference_basis(tmp_path,basis,hours):
    config=selected(tmp_path).config
    invalid=replace(config,study=replace(config.study,annualization_basis=basis,
        annual_hours=replace(config.study.annual_hours,value=hours)))
    with pytest.raises(ValueError):invalid.validate()

@pytest.mark.parametrize('backend',['gurobi','scipy_highs'])
@pytest.mark.parametrize('year,hours',[(2024,8784),(2025,8760)])
def test_small_actual_solves_preserve_annual_target_for_each_basis(tmp_path,backend,year,hours):
    config=selected(tmp_path,year).config
    result=optimize_hydrogen_system(frame(year,hours),config=config,solver_backend=backend)
    assert result.annual_hours==hours
    assert result.modeled_hours==24
    assert result.annualization_factor==hours/24
    assert result.annual_h2_delivered_kg==pytest.approx(3650000)
    assert result.annualization_basis=='historical_calendar_year'
    assert result.objective_eur_per_year>0
    assert result.lcoh_eur_per_kg_h2==pytest.approx(result.objective_eur_per_year/3650000)

def test_eu_calendar_rejects_source_from_another_year(tmp_path):
    source=frame(2025,8784)
    source.attrs['eu_site_configuration']=selected(tmp_path).metadata
    with pytest.raises(HourlyInputError,match='Kalenderjahr'):
        validate_hourly_input(source)

def test_full_leap_year_cannot_silently_use_legacy_365_day_reference():
    with pytest.raises(ValueError,match='Jahresstundenbasis'):
        optimize_hydrogen_system(frame(2024,8784,8784),solver_backend='scipy_highs')

def test_complete_leap_year_is_validated_and_independently_annualized_without_solving(tmp_path):
    selection=selected(tmp_path)
    raw=frame(2024,8784,8784)
    raw['timestamp']=pd.date_range('2023-12-31T23:00:00Z',periods=8784,freq='h')
    raw.attrs['eu_site_configuration']=selection.metadata
    validated=validate_hourly_input(raw,expected_hours=8784)
    parameters={key:{'value':value.value} for key,value in iter_scalar_parameters(selection.config)}
    annualization={'basis':'historical_calendar_year','reference_year':2024,
        'annual_hours':8784,'modeled_hours':8784,'time_step_hours':1,'factor':1.0,
        'period_interpretation':'complete_historical_calendar_year'}
    summary=pd.Series({'annualization_factor':1.0,'annual_hours':8784,'modeled_hours':8784,
        'annualization_basis':'historical_calendar_year'})
    metadata={'schema_version':'1.6','calendar_scope':{'annualization':annualization},
        'input':{'eu_site_configuration':selection.metadata}}
    checks=[]
    factor=_check_annualization_contract(checks,'reference',validated,validated,metadata,summary,parameters)
    assert factor==1.0
    assert all(check['passed'] for check in checks)
    assert validated.h2_demand.sum()==pytest.approx(3650000)

def export(tmp_path):
    selection=selected(tmp_path)
    path=tmp_path/'input.csv';frame(2024,8784).to_csv(path,index=False)
    artifacts=run_h2_scenarios(path,tmp_path/'results',solver_backend='scipy-highs',
        eu_site='hamburg_moorburg',eu_design_path=selection.metadata['design_path'])
    return artifacts

def test_runner_exports_explicit_basis_and_independent_validator_passes(tmp_path):
    artifacts=export(tmp_path)
    metadata=json.loads(artifacts.scenario_runs['S0'].metadata_path.read_text(encoding='utf-8'))
    assert metadata['calendar_scope']['annualization']['factor']==366
    assert metadata['calendar_scope']['annualization']['annual_hours']==8784
    assert metadata['calendar_scope']['annualization']['period_interpretation']=='cyclic_period_reference_annualization'
    assert validate_h2_results(artifacts.output_directory,expected_hours=24).all_checks_passed

@pytest.mark.parametrize('mutation',['factor','reference_year','annual_hours','parameter_hours','missing_contract','source_design'])
def test_validator_rejects_manipulated_annualization(tmp_path,mutation):
    artifacts=export(tmp_path)
    run=artifacts.scenario_runs['S0']
    metadata=json.loads(run.metadata_path.read_text(encoding='utf-8'))
    if mutation=='factor':
        summary=pd.read_csv(run.summary_path)
        summary.loc[0,'annualization_factor']=365
        summary.to_csv(run.summary_path,index=False)
        metadata['calendar_scope']['annualization']['factor']=365
    elif mutation=='reference_year': metadata['calendar_scope']['annualization']['reference_year']=2025
    elif mutation=='annual_hours': metadata['calendar_scope']['annualization']['annual_hours']=8760
    elif mutation=='parameter_hours': metadata['model_parameters']['study.annual_hours']['value']=8760
    elif mutation=='missing_contract': del metadata['calendar_scope']['annualization']
    else:
        design_path=Path(metadata['input']['eu_site_configuration']['design_path'])
        design=json.loads(design_path.read_text(encoding='utf-8'))
        design['time']['historical_year']=2025
        design_path.write_text(json.dumps(design),encoding='utf-8')
    run.metadata_path.write_text(json.dumps(metadata),encoding='utf-8')
    validation=validate_h2_results(artifacts.output_directory,expected_hours=24)
    assert not validation.all_checks_passed
    checks=pd.read_csv(validation.checks_path)
    failed=checks.loc[(checks.scenario=='reference')&(~checks.passed),'check_id']
    assert any(name.startswith('annualization_') for name in failed)

@pytest.mark.parametrize('target',['comparison','batch_metadata'])
def test_validator_rejects_manipulation_of_comparison_annualization(tmp_path,target):
    artifacts=export(tmp_path)
    if target=='comparison':
        comparison=pd.read_csv(artifacts.comparison_path)
        comparison.loc[0,'annualization_factor']=365
        comparison.to_csv(artifacts.comparison_path,index=False)
    else:
        metadata=json.loads(artifacts.metadata_path.read_text(encoding='utf-8'))
        metadata['annualization']['annual_hours']=8760
        artifacts.metadata_path.write_text(json.dumps(metadata),encoding='utf-8')
    result=validate_h2_results(artifacts.output_directory,expected_hours=24)
    assert not result.all_checks_passed

def test_old_metadata_without_explicit_contract_retains_legacy_reference(tmp_path):
    path=tmp_path/'input.csv';frame(2025,8760).to_csv(path,index=False)
    artifacts=run_h2_scenarios(path,tmp_path/'legacy',solver_backend='scipy-highs')
    for run in artifacts.scenario_runs.values():
        metadata=json.loads(run.metadata_path.read_text(encoding='utf-8'))
        metadata['schema_version']='1.5'
        del metadata['calendar_scope']['annualization']
        del metadata['model_parameters']['study.annual_hours']
        run.metadata_path.write_text(json.dumps(metadata),encoding='utf-8')
    assert validate_h2_results(artifacts.output_directory,expected_hours=24).all_checks_passed

def source_with_calendar_contract(tmp_path,change=None):
    selection=selected(tmp_path)
    data=frame(2024,8784,8784).drop(columns='grid_emission_factor')
    data['timestamp']=pd.date_range('2023-12-31T23:00:00Z',periods=8784,freq='h')
    data['regulatory_grid_emission_factor']=60.0
    source=tmp_path/'input.csv';data.to_csv(source,index=False)
    context={'site_id':'hamburg_moorburg','country_code':'DE','calendar_timezone':'Europe/Berlin',
        'historical_year':2024,'price_year':2023,'annual_hours':8784,'expected_hours':8784,
        'annualization_basis':'historical_calendar_year','demand_profile':{'profile':'D0','annual_kg':3650000}}
    if change:context.update(change)
    import hashlib
    contract={'schema_version':'1.0','input_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'emission_factor_mode':'regulatory_only','emission_factor_sources':{'regulatory':{
            'source_description':'Synthetic fixture, no empirical factor','reference_year':2024,
            'spatial_scope':'synthetic','unit':'kg_CO2e/MWh','emissions_basis':'synthetic_regulatory_CO2e'}},**context}
    path=tmp_path/'source_contract.json';path.write_text(json.dumps(contract),encoding='utf-8')
    kwargs={'solver_backend':'scipy-highs','eu_site':'hamburg_moorburg','eu_design_path':selection.metadata['design_path'],
        'emissions_reporting':'regulatory_only','emission_factor_metadata_path':path}
    return source,context,kwargs

def test_sidecar_calendar_and_demand_context_is_preserved_and_independently_checked(tmp_path):
    source,context,kwargs=source_with_calendar_contract(tmp_path)
    import hashlib
    input_sha=hashlib.sha256(source.read_bytes()).hexdigest()
    raw=pd.read_csv(source)
    _load_emission_factor_metadata(raw,kwargs['emission_factor_metadata_path'],input_sha)
    selection=eu.load_eu_site_configuration(kwargs['eu_site'],design_path=kwargs['eu_design_path'])
    _require_eu_input_context_matches(raw,selection.metadata)
    raw.attrs['eu_site_configuration']=selection.metadata
    validated=validate_hourly_input(raw,expected_hours=8784,emissions_reporting='regulatory_only')
    assert validated.attrs['declared_input_context']==context
    input_metadata={'source_path':str(source),'sha256':input_sha,
        'declared_input_context':context,**context,
        'eu_site_configuration':selection.metadata,
        'emission_factor_metadata':raw.attrs['emission_factor_metadata'],
        'emission_factor_sources':raw.attrs['emission_factor_sources'],'emission_factor_mode':'regulatory_only'}
    assert _independent_source_contract_matches(input_metadata,pd.Series({'input_sha256':input_sha}),validated)

def test_declared_full_year_rejects_truncated_csv_before_solver(tmp_path):
    source,context,kwargs=source_with_calendar_contract(tmp_path)
    raw=pd.read_csv(source).iloc[:24];raw.to_csv(source,index=False)
    import hashlib
    path=kwargs['emission_factor_metadata_path']
    contract=json.loads(path.read_text(encoding='utf-8'))
    contract['input_sha256']=hashlib.sha256(source.read_bytes()).hexdigest()
    path.write_text(json.dumps(contract),encoding='utf-8')
    with pytest.raises(H2RunError,match='Stundenanzahl'):
        run_h2_scenarios(source,tmp_path/'unused',**kwargs)
    assert not (tmp_path/'unused').exists()

@pytest.mark.parametrize('change',[{'annual_hours':8760},{'expected_hours':8760},
    {'annualization_basis':'legacy_365_day_reference'},{'demand_profile':{'profile':'D0','annual_kg':3660000}}])
def test_sidecar_cannot_override_year_basis_or_fixed_delivery(tmp_path,change):
    source,context,kwargs=source_with_calendar_contract(tmp_path,change)
    with pytest.raises(H2RunError):run_h2_scenarios(source,tmp_path/'unused',**kwargs)
    assert not (tmp_path/'unused').exists()
