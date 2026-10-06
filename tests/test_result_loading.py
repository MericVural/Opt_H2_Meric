from pathlib import Path
import os
import sys
import subprocess
import json
import pandas as pd
import pytest

G=Path(os.environ.get('H2_GUI_SOURCE_ROOT',Path(__file__).resolve().parents[1])).resolve()
sys.path.insert(0,str(G))
from gui.case_study_registry import load_registry
from gui.result_loader import load_registered_results, load_result_directory, load_sensitivity_comparisons, comparison_context

ROOT=Path(os.environ.get('H2_MODEL_REPO',G)).resolve()

def no_process(*args,**kwargs):
    raise AssertionError('Viewing results must never launch a solver/process')

def registered_rows(table,registry,study,site):
    """Find the original registered scientific references among later GUI runs."""
    sources={str(ref.path) for ref in registry.get_site(study,site).result_sources}
    return table.loc[table['__result_copies'].map(lambda value:any(
        copy.get('__source_csv') in sources for copy in json.loads(value)))].copy()

def test_requirement10_native_results_and_hours_read_without_solver(monkeypatch):
    monkeypatch.setattr(subprocess,'run',no_process)
    monkeypatch.setattr(subprocess,'Popen',no_process)
    registry=load_registry(ROOT)
    for study,site,hours in [('eu_2024','hamburg_moorburg',8784),('eu_2024','huelva_la_rabida',8784),('namibia','namibia',8760)]:
        table=load_registered_results(registry,study,site,'D0')
        assert table['__analysis_id'].is_unique
        registered=registered_rows(table,registry,study,site)
        assert len(registered)==3
        assert set(registered.scenario_id)=={'S0','S1','S2'}
        assert set(table.site_id)=={site}
        bundle=load_result_directory(registered.iloc[0]['__result_directory'],ROOT,include_hourly=True)
        source=pd.read_csv(Path(registered.iloc[0]['__result_directory'])/'summary.csv')
        assert bundle.summary.iloc[0].lcoh_eur_per_kg_h2==source.iloc[0].lcoh_eur_per_kg_h2
        assert len(next(iter(bundle.hourly.values())))==hours
        assert bundle.provenance['input_hash_checks'][0]['status']=='matches'

def test_sensitivity_and_demand_results_remain_site_filtered(monkeypatch):
    monkeypatch.setattr(subprocess,'run',no_process)
    registry=load_registry(ROOT)
    for site in ('hamburg_moorburg','huelva_la_rabida'):
        data=load_registered_results(registry,'eu_2024',site,'D1')
        assert data['__analysis_id'].is_unique
        registered=registered_rows(data,registry,'eu_2024',site)
        assert len(registered)==3 and set(data.site_id)=={site} and set(data.demand_profile)=={'D1'}
        assert set(registered.scenario_id)=={'S0','S1','S2'}
        sensitivity=load_sensitivity_comparisons(registry,'eu_2024',site)
        assert not sensitivity.empty and set(sensitivity.site_id)=={site}

def test_cross_study_comparison_shows_year_limitations_without_solver(monkeypatch):
    monkeypatch.setattr(subprocess,'run',no_process)
    registry=load_registry(ROOT)
    table=pd.concat([load_registered_results(registry,'eu_2024','hamburg_moorburg','D0').head(1),
                     load_registered_results(registry,'namibia','namibia','D0').head(1)],ignore_index=True)
    context,warnings=comparison_context(registry,table)
    assert len(context)==2
    assert warnings
    assert set(table.study_id)=={'eu_2024','namibia'}
