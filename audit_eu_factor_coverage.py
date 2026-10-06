"""Quantify Step 19 factor coverage without inventing residual fuel weights.

This classifies actual positive hourly categories and reports annual exposure.
Country-year factor averages are labelled candidates; this is not an input
release. In particular, non-overlapping generation categories do not imply
that their annual statistical fuel weights have an exact matching partition.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd


class FactorCoverageError(ValueError):
    pass


DIRECT = {'DE': {'hydro': 'RA100', 'wind_offshore': 'RA300',
                 'wind_onshore': 'RA300', 'solar': 'RA420'},
          'ES': {'eol': 'RA300', 'nuc': 'N900H', 'gnhd': 'RA100',
                 'solFot': 'RA420', 'solTer': 'RA410'}}
FUELS = {'DE': {'gas': ('G3000',), 'lignite': ('C0220', 'C0330'),
                'hard_coal': ('C0110', 'C0121', 'C0129', 'C0311')},
         'ES': {'cc': ('G3000',), 'car': ('C0110', 'C0121', 'C0129', 'C0311'),
                'gf': ('O4671XR5220B', 'O4680', 'O4699')}}
UNRESOLVED = {
    'DE': {
        'biomass': 'Biogas R5300 overlaps landfill/sewage subgroups classified in other_renewable; solid-biomass CHP has no composition point.',
        'other_renewable': 'SMARD includes geothermal, landfill gas, sewage gas and colliery methane. Their separate electricity weights are not resolved; colliery gas is not emission-free.',
        'other_conventional': 'Waste, oil, recovered gases, hydrogen-rich fuels and mixed-fuel production require a sourced compatible partition.',
    },
    'ES': {
        'bio': 'Biocombustible is not identical to the REData Otras renovables aggregate; fuel/operator/CHP shares are not a measured hourly partition.',
        'cogenResto': 'CHP plus waste needs renewable/nonrenewable waste and fuel shares; secondary-heat intensity/scope is unresolved.',
        'vap': 'Aboño II conversion documents natural gas and blast-furnace gas, but not actual 2025 fuel-energy shares or converted-unit net efficiency.',
    },
}
KNOWN = {geo: set(DIRECT[geo]) | set(FUELS[geo]) | set(UNRESOLVED[geo]) for geo in ('DE', 'ES')}
STORAGE = {'DE': {'pumped_storage_output'}, 'ES': set()}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_verified_prepared(folder):
    folder = Path(folder)
    report_path = folder / 'preparation_report.json'
    report = json.loads(report_path.read_text(encoding='utf-8'))
    hashes = report.get('output_hashes', {})
    names = {'DE': 'de_generation_hourly_mwh_unreleased.csv',
             'ES': 'es_generation_hourly_rectangle_mwh_unreleased.csv'}
    frames, evidence = {}, []
    for geo, name in names.items():
        path = folder / name
        actual_hash = sha256(path)
        if hashes.get(name) != actual_hash:
            raise FactorCoverageError('Prepared generation hash differs: ' + name)
        frames[geo] = pd.read_csv(path)
        evidence.append({'country': geo, 'file': name, 'sha256': actual_hash})
    return frames, {'preparation_report_sha256': sha256(report_path), 'generation_sources': evidence}


def validate_generation(frame, geo):
    if geo not in KNOWN or not isinstance(frame, pd.DataFrame) or frame.empty:
        raise FactorCoverageError('Expected a nonempty known-country generation frame.')
    if frame.columns.duplicated().any() or 'timestamp' not in frame:
        raise FactorCoverageError('Unique category columns and timestamp required.')
    index = pd.to_datetime(frame['timestamp'], utc=True, errors='raise')
    if index.isna().any() or index.duplicated().any() or not index.is_monotonic_increasing:
        raise FactorCoverageError('Unique increasing real UTC intervals required.')
    if len(index) > 1 and not index.diff().iloc[1:].eq(pd.Timedelta(hours=1)).all():
        raise FactorCoverageError('Consecutive hourly UTC intervals required.')
    categories = set(frame.columns) - {'timestamp'}
    unknown = categories - KNOWN[geo] - STORAGE[geo]
    if unknown:
        raise FactorCoverageError('Unknown generation categories: ' + ', '.join(sorted(unknown)))
    primary = frame.drop(columns=['timestamp', *sorted(categories & STORAGE[geo])]).copy()
    if primary.empty:
        raise FactorCoverageError('No primary generation categories.')
    for category in primary:
        primary[category] = pd.to_numeric(primary[category], errors='raise')
    array = primary.to_numpy(dtype=float)
    if not np.isfinite(array).all() or (array < 0).any():
        raise FactorCoverageError('Generation must be finite and nonnegative.')
    if (primary.sum(axis=1) <= 0).any():
        raise FactorCoverageError('A full hour has no positive primary generation denominator.')
    return primary


def candidate_factor(records, geo, codes, *, non_chp_only=False):
    selected = [r for r in records if r['geo'] == geo and r['siec'] in codes
                and (not non_chp_only or 'CHP' not in r['plant'])
                and r['gross_power']['value'] is not None and r['gross_power']['value'] > 0]
    if not selected:
        return {'point_kgCO2e_per_MWh': None, 'status': 'no_compatible_positive_annual_candidate'}
    numerator = denominator = 0.0
    selected_ids = []
    for record in selected:
        if record.get('method_status') == 'blocked':
            return {'point_kgCO2e_per_MWh': None, 'status': 'positive_annual_candidate_blocked'}
        point = record.get('calculation', {}).get('point_kgCO2e_per_MWh')
        net = record.get('net_correction', {}).get('gross_to_net_factor')
        if point is None or net is None or not math.isfinite(point) or not math.isfinite(net) or net < 1:
            return {'point_kgCO2e_per_MWh': None, 'status': 'annual_candidate_has_no_composition_point'}
        key = (record['geo'], record['plant'], record['siec'])
        if key in selected_ids:
            raise FactorCoverageError('Duplicate annual record would double weight a factor.')
        selected_ids.append(key)
        # Weight electricity-specific intensities by compatible net electricity.
        weight = record['gross_power']['value'] / net
        numerator += weight * point
        denominator += weight
    return {'point_kgCO2e_per_MWh': numerator / denominator,
            'net_power_weight_TJ': denominator, 'annual_record_ids': selected_ids,
            'status': 'conditional_2024_country_net_electricity_weighted_candidate',
            'not_an_observed_2025_technology_factor': True,
            'spatial_and_plant_type_transfer_unverified': True}


def audit_country(frame, geo, annual, boundary):
    primary = validate_generation(frame, geo)
    total = float(primary.to_numpy().sum())
    records = annual['category_records']
    zeros = {(r['geo'], r['siec']): r for r in boundary['direct_zero_resolutions']}
    rows = []
    for category in primary:
        energy = float(primary[category].sum())
        row = {'category': category, 'annual_generation_MWh_or_rectangle_proxy': energy,
               'share_percent': 100 * energy / total, 'positive_hours': int((primary[category] > 0).sum()),
               'released_for_model': False, 'candidate': None}
        if energy == 0:
            row.update(status='no_positive_generation_observed', reason='No factor invented; this category has zero observed energy.')
        elif category in DIRECT[geo]:
            code = DIRECT[geo][category]
            if (geo, code) in zeros:
                resolution = zeros[(geo, code)]
                row['candidate'] = {'point_kgCO2e_per_MWh': resolution['factor_kgCO2e_per_MWh_electricity_net'],
                                    'siec': code, 'source_sha256': resolution['source_sha256']}
            else:
                source_rows = [r for r in records if r['geo'] == geo and r['siec'] == code
                               and r.get('method_status') == 'sourced_direct_noncombustible_factor']
                values = {r['calculation']['point_kgCO2e_per_MWh'] for r in source_rows}
                if len(values) != 1:
                    raise FactorCoverageError('Direct noncombustible mapping not uniquely sourced: ' + category)
                row['candidate'] = {'point_kgCO2e_per_MWh': values.pop(), 'siec': code}
            row.update(status='sourced_direct_noncombustible_mapping', reason='Direct operational boundary only; lifecycle excluded.')
        elif category in FUELS[geo]:
            row['candidate'] = candidate_factor(records, geo, FUELS[geo][category], non_chp_only=geo == 'ES')
            row.update(status='conditional_annual_fuel_group_candidate',
                       reason='2024 country/fuel/plant proxy; matching public-grid/mainland and technology scope still requires assessment.')
        else:
            row.update(status='positive_category_unresolved', reason=UNRESOLVED[geo][category])
        rows.append(row)
    unresolved = [row for row in rows if row['status'] == 'positive_category_unresolved']
    return {'country': geo, 'hours': len(primary), 'total_primary_generation_MWh_or_rectangle_proxy': total,
            'categories': rows, 'unresolved_generation_MWh_or_rectangle_proxy': sum(r['annual_generation_MWh_or_rectangle_proxy'] for r in unresolved),
            'unresolved_share_percent': sum(r['share_percent'] for r in unresolved),
            'point_hourly_factor_released': False,
            'energy_semantics': 'SMARD net public-grid energy' if geo == 'DE' else 'REE instantaneous-power hourly rectangle proxy; not measured interval energy'}


def build_report(prepared, annual_path, boundary_path, output):
    frames, sources = load_verified_prepared(prepared)
    annual = json.loads(Path(annual_path).read_text(encoding='utf-8'))
    boundary = json.loads(Path(boundary_path).read_text(encoding='utf-8'))
    if annual.get('historical_year') != 2025 or annual.get('annual_proxy_year') != 2024:
        raise FactorCoverageError('Expected explicitly declared 2025/2024 proxy contract.')
    if boundary.get('annual_audit_sha256') != sha256(annual_path):
        raise FactorCoverageError('Boundary resolutions belong to another annual audit.')
    reports = [audit_country(frames[geo], geo, annual, boundary) for geo in ('DE', 'ES')]
    for frame in frames.values():
        expected = pd.date_range('2024-12-31T23:00:00Z', periods=8760, freq='h')
        if not pd.DatetimeIndex(pd.to_datetime(frame['timestamp'], utc=True)).equals(expected):
            raise FactorCoverageError('Expected full local 2025 calendar UTC hours.')
    report = {'schema_version': 1, 'created_utc': datetime.now(timezone.utc).isoformat(),
              'historical_year': 2025, 'annual_proxy_year': 2024,
              'source_evidence': sources, 'annual_audit_sha256': sha256(annual_path),
              'boundary_resolution_sha256': sha256(boundary_path), 'software_sha256': sha256(__file__),
              'countries': reports, 'ready_for_model': False, 'step19_complete': False,
              'candidate_status': 'Category candidates and unresolved annual exposure only; not a released point or bounded hourly factor series',
              'no_unresolved_category_zero_fill': True}
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepared', required=True, type=Path)
    parser.add_argument('--annual-audit', required=True, type=Path)
    parser.add_argument('--boundary-resolution', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    result = build_report(args.prepared, args.annual_audit, args.boundary_resolution, args.output)
    print(json.dumps([{'country': c['country'], 'unresolved_share_percent': c['unresolved_share_percent']} for c in result['countries']], indent=2))
