"""Research questions and cautious descriptions of saved model results.

No optimization and no replacement of native reference/provenance contracts.
"""
from __future__ import annotations

import math
import numpy as np
import pandas as pd

GOALS = {
    'rules': ('Stromregeln vergleichen', 'Was kosten strengere Stromversorgungsregeln?',
        'Stromversorgungsregel S0 / S1 / S2 (optional S3)',
        'Standort, Lieferprofil, Jahresmenge, Preise, Technik und Finanzierung'),
    'plant': ('Anlage auslegen', 'Welche Anlage deckt die H₂-Nachfrage zu minimalen Kosten?',
        'Kein Parameter: kostenoptimale Neuauslegung eines Falls', 'Dokumentierte Eingaben des gewählten Falls'),
    'dispatch': ('Tagesbetrieb verstehen', 'Wann versorgen Solar, Wind und Netz die Anlage?',
        'Angezeigter Zeitraum eines gespeicherten Falls', 'Anlage und optimierter Jahresbetrieb'),
    'solver': ('Solver vergleichen', 'Wie stabil ist die Lösung gegenüber dem Solver?',
        'HiGHS / Gurobi', 'Dieselben Modelleingaben; keine Parameteränderung'),
    'quantity': ('H₂-Jahresmenge verändern', 'Wie ändern sich Kosten und Auslegung mit der H₂-Menge?',
        'Jahresnachfrage in Prozent der Basis', 'Lieferzeiten, Standort und alle übrigen Modellannahmen'),
    'profile': ('Lieferzeiten verändern', 'Wie wirken Lieferfenster auf Kosten und Speicher?',
        'D0 / D1 / D2: zeitliche Verteilung der Pflichtlieferung', 'Gleiche Jahresmenge, Standort und Basisannahmen'),
    'drivers': ('Preis, Finanzierung & Technik', 'Welche Annahmen treiben die Wasserstoffkosten?',
        'Je Variante ein ausgewählter Parameter (OAT)', 'Eigener Bezugsfall und alle übrigen Eingaben'),
    'sites': ('Standorte vergleichen', 'Wie unterscheiden sich die Standorte bei gleicher Aufgabe?',
        'Standort mit seinen Wetter-, Preis- und Finanzierungsannahmen', 'Technologie, Jahresmenge, Lieferprofil und Stromregel soweit belegt'),
}

SCENARIOS = {'S0': 'S0 · Referenz', 'S1': 'S1 · monatlich', 'S2': 'S2 · stündlich', 'S3': 'S3 · ohne Netz'}
PARAMETER_GROUPS = {
    'Strompreis & Finanzierung': ['electricity_price_offset_eur_per_mwh', 'electricity_price_eur_per_mwh',
        'real_wacc_multiplier', 'real_wacc_shift_fraction', 'uniform_real_wacc_fraction'],
    'Elektrolyse': ['electrolyzer_capex_eur_per_kw', 'electrolyzer_capex_factor',
        'electrolyzer_specific_electricity_kwh_per_kg_h2', 'electrolyzer_specific_electricity_factor'],
    'Erneuerbare & Speicher': ['pv_capex_eur_per_kw', 'wind_capex_eur_per_kw', 'h2_storage_capex_eur_per_kg_h2'],
}


def fmt(value, digits=2):
    try:
        number = float(value)
        if not math.isfinite(number): return 'nicht bewertet'
        return f'{number:,.{digits}f}'.replace(',', '_').replace('.', ',').replace('_', '.')
    except (ValueError, TypeError):
        return 'nicht bewertet'


def baseline_rows(frame):
    """Respect embedded quantity=1 baselines without adopting other variants."""
    if frame.empty: return frame.copy()
    if 'case_id' in frame:
        return frame[frame.case_id.eq('baseline')].copy()
    if 'sensitivity_parameter' in frame:
        return frame[frame.sensitivity_parameter.eq('baseline')].copy()
    return frame.copy()


def percent_variants(levels):
    values = sorted({float(value) for value in levels})
    if not values or any(not math.isfinite(value) or value <= 0 for value in values):
        raise ValueError('Nachfragestufen müssen positive, endliche Prozentwerte sein.')
    return [{'parameter': 'h2_demand_multiplier', 'value': value / 100,
             'label': f'h2_demand_{value:g}pct'} for value in values if value != 100]


def baseline_amount(site, profile):
    metadata = site.profiles[profile].metadata.get('demand_profile', {})
    value = metadata.get('annual_h2_requested_kg', metadata.get('annual_kg'))
    if value is None:
        value = pd.read_csv(site.profiles[profile].path, usecols=['h2_demand']).h2_demand.sum()
    return float(value)


def same_annual_demand(frame):
    if frame.empty or 'annual_h2_delivered_kg' not in frame: return False
    values=pd.to_numeric(frame.annual_h2_delivered_kg,errors='coerce').to_numpy()
    return bool(np.isfinite(values).all() and np.allclose(values,values[0],rtol=1e-9,atol=1e-3))


def observed_delta(frame, from_id='S1', to_id='S2', metric='lcoh_eur_per_kg_h2'):
    if frame.empty or metric not in frame or 'scenario_id' not in frame: return None
    first, second = frame[frame.scenario_id.eq(from_id)], frame[frame.scenario_id.eq(to_id)]
    if len(first) != 1 or len(second) != 1: return None
    a, b = float(first.iloc[0][metric]), float(second.iloc[0][metric])
    if not (math.isfinite(a) and math.isfinite(b)): return None
    return {'from': from_id, 'to': to_id, 'absolute': b-a, 'percent': 100*(b/a-1) if a else None}


def demand_observation(prepared):
    """An empirical statement only about the shown, contract-checked points."""
    groups = prepared.attrs.get('group_columns')
    if not groups or '__oat_is_baseline' not in prepared: return None
    deviations = []
    for _, group in prepared.groupby(groups, dropna=False):
        base = group[group.__oat_is_baseline.eq(True)]
        if len(base) != 1: return None
        base = base.iloc[0]
        required = ['annual_h2_delivered_kg', 'objective_eur_per_year', 'lcoh_eur_per_kg_h2']
        if any(c not in group for c in required): return None
        if any(not np.isfinite(group[c].astype(float)).all() for c in required): return None
        if any(float(base[c]) <= 0 for c in required): return None
        ratio = group.annual_h2_delivered_kg / float(base.annual_h2_delivered_kg)
        deviation = np.max(np.abs(group.objective_eur_per_year / float(base.objective_eur_per_year) - ratio))
        lcoh = np.max(np.abs(group.lcoh_eur_per_kg_h2 / float(base.lcoh_eur_per_kg_h2) - 1))
        deviations.append(max(float(deviation), float(lcoh)))
    if not deviations: return None
    if max(deviations) <= 1e-6:
        return 'In den dargestellten Punkten steigen die Jahreskosten proportional zur Nachfrage; die LCOH bleiben innerhalb der numerischen Toleranz konstant.'
    return 'Die dargestellten Punkte weichen von proportionalen Jahreskosten bzw. konstanten LCOH ab. Vor einer Interpretation sind Randbedingungen und numerische Lösung zu prüfen.'


def flatten_plans(plans):
    children = []
    for plan in plans:
        children.extend(flatten_plans(plan['plans']) if plan.get('kind') == 'combined' else [plan])
    return children
