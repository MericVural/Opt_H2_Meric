"""Meaningful registry/source separation tests against documented local cases."""
from pathlib import Path
import os
import sys
from copy import deepcopy
import pytest

G=Path(os.environ.get('H2_GUI_SOURCE_ROOT',Path(__file__).resolve().parents[1])).resolve()
sys.path.insert(0,str(G))
from gui.case_study_registry import load_registry, RegistryError, contained_path, archived_config_compatibility

ROOT=Path(os.environ.get('H2_MODEL_REPO',G)).resolve()

@pytest.fixture(scope='module')
def registry():
    return load_registry(ROOT)

def test_requirement01_documented_studies_recognized(registry):
    assert {'eu_2024','namibia'} <= set(registry.studies)
    assert registry.studies['eu_2024'].documentation_path.name=='FALLSTUDIE_HAMBURG_ANDALUSIEN.md'
    assert registry.studies['namibia'].documentation_path.name=='FALLSTUDIE_NAMIBIA.md'

def test_requirement02_site_belongs_to_study(registry):
    assert set(registry.studies['eu_2024'].sites)=={'hamburg_moorburg','huelva_la_rabida'}
    assert set(registry.studies['namibia'].sites)=={'namibia'}
    with pytest.raises(RegistryError,match='gehört nicht'):
        registry.get_site('namibia','hamburg_moorburg')
    with pytest.raises(RegistryError,match='gehört nicht'):
        registry.get_site('eu_2024','namibia')

def test_requirement03_country_case_sources_are_not_mixed(registry):
    de=registry.get_site('eu_2024','hamburg_moorburg')
    es=registry.get_site('eu_2024','huelva_la_rabida')
    na=registry.get_site('namibia','namibia')
    assert de.profiles['D0'].path!=es.profiles['D0'].path!=na.profiles['D0'].path
    assert de.metadata['baseline_metadata']['input']['eu_site_configuration']['country_code']=='DE'
    assert es.metadata['baseline_metadata']['input']['eu_site_configuration']['country_code']=='ES'
    assert 'eu_site_configuration' not in na.metadata['baseline_metadata']['input']
    assert na.uniform_wacc['value']==.11
    assert de.year_roles['wacc_source_year']==2021
    assert de.metadata['baseline_metadata']['model_parameters']['technologies.pv.real_wacc_fraction']['value']==.013
    assert es.metadata['baseline_metadata']['model_parameters']['technologies.pv.real_wacc_fraction']['value']==.036

def test_year_roles_do_not_call_TMY_index_year_weather_year(registry):
    de=registry.get_site('eu_2024','hamburg_moorburg').year_roles
    assert (de['study_operation_year'],de['weather_year'],de['market_price_year'],de['operational_emission_reference_year'])==(2024,2024,2024,2024)
    assert (de['cost_price_year'],de['wacc_source_year'],de['regulatory_factor_reference_year'])==(2023,2021,2020)
    na=registry.get_site('namibia','namibia').year_roles
    assert na['profile_index_year']==2025
    assert na['weather_year']=='TMY 2007–2016'
    assert na['market_price_year'] is None

def test_requirement12_historical_status_retained_despite_checked_native_compatibility(registry):
    na=registry.get_site('namibia','namibia')
    assert na.historical is True
    assert registry.studies['namibia'].role=='historical'
    assert na.metadata['compatibility']['compatible'] is True
    assert na.metadata['compatibility']['annual_solver_calls']==0
    assert na.can_run is True
    assert registry.get_site('eu_2024','hamburg_moorburg').historical is False

@pytest.mark.parametrize('tamper', ['parameter','input_hash','missing_parameters'])
def test_historical_compatibility_rejects_changed_assumptions(registry,tamper):
    site=registry.get_site('namibia','namibia')
    metadata=deepcopy(site.metadata['baseline_metadata'])
    if tamper=='parameter': metadata['model_parameters']['technologies.pv.capex_eur_per_kw']['value']*=1.1
    elif tamper=='input_hash': metadata['input']['sha256']='0'*64
    else: metadata.pop('model_parameters')
    result=archived_config_compatibility(ROOT,metadata,site.profiles['D0'].path)
    assert result['compatible'] is False
    assert result['annual_solver_calls']==0

def test_registry_path_confinement():
    with pytest.raises(RegistryError,match='außerhalb'):
        contained_path(ROOT,ROOT.parent/'unrelated.csv')
