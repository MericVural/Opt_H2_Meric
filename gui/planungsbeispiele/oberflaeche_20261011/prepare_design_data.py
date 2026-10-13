from pathlib import Path
import csv,json,hashlib
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT=Path(r'C:\Forschungsarbeit\Opt_H2_Meric-h2')
OUT=Path(__file__).parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
inputs=[]
def read(relative):
    p=ROOT/relative
    inputs.append({'path':relative,'sha256':sha(p)})
    return list(csv.DictReader(p.open(encoding='utf-8-sig')))
fields={'percent':'demand_percent_of_baseline','amount':'annual_h2_delivered_kg','cost':'objective_eur_per_year',
        'lcoh':'lcoh_eur_per_kg_h2','pv':'pv_capacity_mw','wind':'wind_capacity_mw','pem':'electrolyzer_capacity_mw',
        'storage':'h2_storage_capacity_kg','grid':'annual_grid_import_mwh',
        'operational':'operational_emission_intensity_kg_co2e_per_kg_h2',
        'regulatory':'regulatory_emission_intensity_kg_co2e_per_kg_h2','limit':'red_iii_maximum_product_intensity_kg_co2e_per_kg_h2'}
demand=read('outputs_h2/eu_case_studies/historical_2024/demand_quantity_20261005/results/demand_quantity_comparison.csv')
data={'demand':[],'scenarios':[],'daily':{}}
for r in demand:
    data['demand'].append({'site':r['site_id'],'profile':r['demand_profile'],'scenario':r['scenario_id'],**{k:float(r[v]) for k,v in fields.items()}})
assert len(data['demand'])==90
scenario_ids={'reference':'S0','red_monthly':'S1','red_hourly':'S2'}
for site in ('hamburg_moorburg','huelva_la_rabida'):
    rows=read(f'outputs_h2/eu_case_studies/historical_2024/verification_runs/basis_20261004_121938UTC/runs/{site}/D0/scenario_comparison.csv')
    for r in rows:
        data['scenarios'].append({'site':site,'profile':'D0','scenario':scenario_ids[r['scenario']],**{k:float(r[v]) if v in r and r[v] else None for k,v in fields.items() if k!='percent'},'percent':100})
hourly=read('outputs_h2/eu_case_studies/historical_2024/verification_runs/basis_20261004_121938UTC/runs/hamburg_moorburg/D0/S2_red_hourly/hourly_operation.csv')
for day in ('2024-01-02','2024-01-03','2024-01-04'):
    selected=[]
    for r in hourly:
        local=datetime.fromisoformat(r['timestamp']).astimezone(ZoneInfo('Europe/Berlin'))
        if str(local.date())==day:
            selected.append({'hour':local.hour,'pv':float(r['pv_self_consumption_mwh']),
                'wind':float(r['wind_self_consumption_mwh']),'grid':float(r['grid_import_mwh']),
                'total':float(r['electrolyzer_electricity_mwh'])+float(r['compressor_electricity_mwh'])})
    assert len(selected)==24
    assert max(abs(r['pv']+r['wind']+r['grid']-r['total']) for r in selected)<1e-6
    data['daily'][day]=selected
(OUT/'preview_data.json').write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
(OUT/'entwurfsnachweis.json').write_text(json.dumps({'version':'D1','date':'2026-10-10','purpose':'Frozen read-only excerpt for interface preview; no optimizer, no new validation claim','inputs':inputs,'counts':{'demand':90,'scenarios':6,'daily_hours':72},'daily_scope':'Hamburg D0 S2, fresh D0 basis, 2024-01-02 through 2024-01-04, Europe/Berlin'},ensure_ascii=False,indent=2),encoding='utf-8')
print('Prepared existing data: 90 demand cases, 6 scenario cases, 72 hourly rows.')
