from dataclasses import asdict,replace
import hashlib
import importlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import eu_site_configuration as eu
from config_h2 import Scenario,default_model_config
from opt_hydrogen_functions import capital_recovery_factor,_calculate_annual_costs_from_values
from eu_test_designs import write_calendar_design

@pytest.fixture(autouse=True)
def explicit_archived_design(tmp_path,monkeypatch):
    path=write_calendar_design(eu.DEFAULT_EU_DESIGN_PATH,tmp_path/'archived_2025_design.json',2025)
    monkeypatch.setattr(eu,'DEFAULT_EU_DESIGN_PATH',path)

@pytest.mark.parametrize("site_id,country,zone,expected",[
    ("hamburg_moorburg","DE","Europe/Berlin",[.013,.013,.033,.033,.033]),
    ("huelva_la_rabida","ES","Europe/Madrid",[.036,.031,.0535,.0535,.0535]),
])
def test_country_and_component_real_benchmarks(site_id,country,zone,expected):
    selected=eu.load_eu_site_configuration(site_id)
    assert selected.site.country_code==country
    assert selected.calendar_timezone==zone
    components=[selected.config.technologies.pv,selected.config.technologies.wind_onshore,
                selected.config.technologies.electrolyzer,selected.config.technologies.compressor,
                selected.config.technologies.h2_storage]
    assert [c.real_wacc_fraction.value for c in components]==expected
    assert all(c.real_wacc_fraction.reference_year==2021 for c in components)
    assert all(c.real_wacc_fraction.unit=='fraction' for c in components)
    assert all('real after-tax' in c.real_wacc_fraction.note for c in components)
    assert 'IRENA' in components[0].real_wacc_fraction.source
    assert 'Brandt' in components[2].real_wacc_fraction.source

@pytest.mark.parametrize("site_id",eu.EU_SITE_IDS)
def test_all_scenarios_use_same_financing(site_id):
    selected=[eu.load_eu_site_configuration(site_id,base_config=replace(default_model_config(),scenario=s)) for s in Scenario]
    assert [x.config.scenario for x in selected]==list(Scenario)
    rates=[x.metadata['wacc']['real_wacc_fraction_per_year'] for x in selected]
    assert all(x==rates[0] for x in rates)
    assert all(x.metadata['wacc']['rates_invariant_across_scenarios'] is True for x in selected)

@pytest.mark.parametrize("site_id",eu.EU_SITE_IDS)
def test_selected_historical_year_replaces_TMY_metadata(site_id):
    c=eu.load_eu_site_configuration(site_id).config
    assert c.study.weather_start_year.value==2025
    assert c.study.weather_end_year.value==2025
    assert c.study.profile_calendar_year.value==2025
    assert c.study.number_of_time_steps.value==8760
    assert 'TMY' in c.study.profile_calendar_year.note
    assert 'ERA5' in c.study.weather_start_year.source
    assert '2007-2016' not in c.study.weather_start_year.source

def test_defaults_and_technical_overrides_preserved():
    baseline=default_model_config()
    old=asdict(baseline)
    technologies=replace(baseline.technologies,
                         electrolyzer=replace(baseline.technologies.electrolyzer,
                             capex_eur_per_kw=replace(baseline.technologies.electrolyzer.capex_eur_per_kw,value=975.)))
    base=replace(baseline,scenario=Scenario.RED_HOURLY,technologies=technologies)
    selected=eu.load_eu_site_configuration('hamburg_moorburg',base_config=base).config
    assert asdict(baseline)==old
    assert default_model_config()==baseline
    assert selected.scenario==base.scenario
    assert selected.study.h2_demand_kg_per_day==base.study.h2_demand_kg_per_day
    for name in ['pv','wind_onshore','electrolyzer','compressor','h2_storage']:
        a=asdict(getattr(selected.technologies,name));b=asdict(getattr(base.technologies,name))
        a.pop('real_wacc_fraction');b.pop('real_wacc_fraction')
        assert a==b
    assert selected.technologies.water==base.technologies.water
    assert selected.paths==base.paths

@pytest.mark.parametrize("site_id",eu.EU_SITE_IDS)
def test_selected_rates_reach_actual_model_annualized_costs(site_id):
    selected=eu.load_eu_site_configuration(site_id)
    c=selected.config
    zeros=np.array([0.])
    capacities={'pv_capacity_mw':1.,'wind_capacity_mw':1.,'electrolyzer_capacity_mw':1.,
                'compressor_capacity_mw':1.,'h2_storage_capacity_kg':1.}
    actual=_calculate_annual_costs_from_values(config=c,data=pd.DataFrame({'electricity_price':[0.]}),
                annualization_factor=1.,capacities=capacities,pv_generation_mwh=zeros,
                wind_generation_mwh=zeros,grid_import_mwh=zeros,h2_production_kg=zeros)
    for name,key in [('pv','pv'),('wind_onshore','wind'),('electrolyzer','electrolyzer'),('compressor','compressor'),('h2_storage','h2_storage')]:
        component=getattr(c.technologies,name)
        rate=component.real_wacc_fraction.value
        life=component.lifetime_years.value
        # Present-value identity independently checks the implemented capital recovery.
        expected_factor=1/sum((1+rate)**(-i) for i in range(1,int(life)+1))
        assert capital_recovery_factor(rate,life)==pytest.approx(expected_factor,rel=1e-12)
        capex=component.capex_eur_per_kg_h2.value if name=='h2_storage' else component.capex_eur_per_mw
        assert actual[key+'_annualized_capex_eur_per_year']==pytest.approx(capex*expected_factor,rel=1e-12)

def test_source_metadata_exact_design_hash_and_no_tax_deflation():
    selected=eu.load_eu_site_configuration('huelva_la_rabida')
    m=selected.metadata
    assert m['design_sha256']==hashlib.sha256(eu.DEFAULT_EU_DESIGN_PATH.read_bytes()).hexdigest()
    assert m['wacc']['reference_year']==2021
    assert m['wacc']['cost_price_year']==2023
    assert m['wacc']['no_additional_inflation_conversion'] is True
    assert m['wacc']['no_second_tax_shield'] is True
    assert m['wacc']['real_wacc_fraction_per_year']['electrolyzer']==.0535
    assert m['hourly_input_verified_by_this_function'] is False
    json.dumps(m,allow_nan=False)

@pytest.mark.parametrize("site_id",['DE','ES','namibia','Hamburg','',None,True])
def test_unknown_site_rejected(site_id):
    with pytest.raises(ValueError,match='Unknown EU site'):
        eu.load_eu_site_configuration(site_id)

def write_design(tmp_path,change):
    x=json.loads(eu.DEFAULT_EU_DESIGN_PATH.read_text(encoding='utf-8-sig'))
    change(x)
    p=tmp_path/'design.json';p.write_text(json.dumps(x),encoding='utf-8')
    return p

@pytest.mark.parametrize("change,match",[
    (lambda x:x['sites'][0]['real_wacc_fraction_per_year'].update(electrolyzer=.07),'WACC.electrolyzer'),
    (lambda x:x['sites'][0]['real_wacc_fraction_per_year'].update(pv=True),'finite numeric'),
    (lambda x:x['financing'].update(reference_year=2025),'reference_year'),
    (lambda x:x['financing'].update(no_inflation_conversion=1),'no_inflation_conversion'),
    (lambda x:x['time'].update(source_weather_year=2024),'source_weather_year'),
    (lambda x:x['time'].update(historical_year=True),'historical_year'),
    (lambda x:x['sites'][0].update(country_code='ES'),'country_code'),
    (lambda x:x['sites'][0].update(calendar_timezone='UTC'),'calendar_timezone'),
    (lambda x:x['sources'].update(WACC=''),'sources.WACC'),
    (lambda x:x['sites'].append(x['sites'][0]),'exactly one'),
])
def test_conflicting_scientific_design_rejected(tmp_path,change,match):
    p=write_design(tmp_path,change)
    with pytest.raises(ValueError,match=match):
        eu.load_eu_site_configuration('hamburg_moorburg',design_path=p)

def test_import_has_no_design_file_IO(monkeypatch):
    def fail(*a,**k):
        raise AssertionError('Module import must not read a design file')
    monkeypatch.setattr(Path,'read_bytes',fail)
    importlib.reload(eu)
