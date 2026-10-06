import pandas as pd
import pytest
from audit_eu_factor_coverage import FactorCoverageError, candidate_factor, validate_generation


def frame(**columns):
    return pd.DataFrame({'timestamp': pd.date_range('2025-01-01', periods=2, freq='h', tz='UTC'), **columns})


def record(plant, power, net, factor, fuel='G3000'):
    return {'geo': 'DE', 'plant': plant, 'siec': fuel, 'gross_power': {'value': power},
            'net_correction': {'gross_to_net_factor': net}, 'method_status': 'conditional',
            'calculation': {'point_kgCO2e_per_MWh': factor}}


def test_net_weighted_factor_is_not_gross_weighted():
    result = candidate_factor([record('MAPE', 20, 2, 100), record('MAPCHP', 30, 1, 400)], 'DE', ('G3000',))
    assert result['point_kgCO2e_per_MWh'] == 325
    assert result['net_power_weight_TJ'] == 40
    assert result['not_an_observed_2025_technology_factor']


def test_duplicate_source_record_blocks_double_weighting():
    r = record('MAPE', 20, 1, 100)
    with pytest.raises(FactorCoverageError, match='Duplicate'):
        candidate_factor([r, r], 'DE', ('G3000',))


def test_missing_biomass_composition_point_is_retained():
    result = candidate_factor([record('MAPCHP', 20, 1, None)], 'DE', ('G3000',))
    assert result['point_kgCO2e_per_MWh'] is None


def test_zero_annual_record_does_not_supply_weight():
    result = candidate_factor([record('MAPE', 0, 1, 100)], 'DE', ('G3000',))
    assert result['point_kgCO2e_per_MWh'] is None


def test_storage_is_not_primary_generation():
    result = validate_generation(frame(hydro=[1, 2], pumped_storage_output=[100, 200]), 'DE')
    assert list(result.columns) == ['hydro']
    assert result.sum().iloc[0] == 3


@pytest.mark.parametrize('bad', [float('nan'), float('inf'), -1])
def test_bad_generation_is_never_filled(bad):
    with pytest.raises(FactorCoverageError, match='finite'):
        validate_generation(frame(hydro=[1, bad]), 'DE')


def test_unknown_generation_category_rejected_even_if_zero():
    with pytest.raises(FactorCoverageError, match='Unknown'):
        validate_generation(frame(hydro=[1, 2], invented=[0, 0]), 'DE')


def test_full_zero_hour_is_rejected():
    with pytest.raises(FactorCoverageError, match='no positive'):
        validate_generation(frame(hydro=[1, 0]), 'DE')


def test_time_gap_is_rejected():
    data = frame(hydro=[1, 2])
    data.loc[1, 'timestamp'] += pd.Timedelta(hours=1)
    with pytest.raises(FactorCoverageError, match='Consecutive'):
        validate_generation(data, 'DE')


def test_partial_zero_categories_are_allowed():
    result = validate_generation(frame(hydro=[1, 0], gas=[0, 2]), 'DE')
    assert result.sum(axis=1).tolist() == [1, 2]
