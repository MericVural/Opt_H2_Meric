"""Offline acceptance tests for strict Step 19 temporal and factor adapters."""

from __future__ import annotations

import copy
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from eu_historical_data import (
    HistoricalDataError,
    adapt_open_meteo_weather,
    aggregate_interval_series,
    construct_operational_factors,
    local_year_index,
    validate_design,
)


def hourly_index(hours=2):
    return pd.date_range("2024-12-31T23:00Z", periods=hours, freq="h")


def design():
    return {
        "consumed_by_current_model": False,
        "time": {
            "historical_year": 2025, "resolution_hours": 1, "storage_timezone": "UTC",
            "interval_semantics": "start, [t,t+1h)", "expected_hours": 8760,
            "reject_positional_year_remapping": True,
            "start_utc_inclusive": "2024-12-31T23:00:00Z",
            "end_utc_exclusive": "2025-12-31T23:00:00Z",
            "year_basis": "local calendar year at each site",
            "monthly_grouping": "site local timezone", "demand_profile_grouping": "site local timezone",
        },
        "sites": [
            {"site_id": "hamburg_moorburg", "calendar_timezone": "Europe/Berlin"},
            {"site_id": "huelva_la_rabida", "calendar_timezone": "Europe/Madrid"},
        ],
        "hydrogen_demand": {"profiles": {"D2": {"weight": "1 ifMonday-Friday and08<=local_hour<20 else0", "active_hours": 3132}}},
    }


@pytest.mark.parametrize("zone", ["Europe/Berlin", "Europe/Madrid"])
def test_local_year_has_exact_bounds_dst_and_d2(zone):
    index = local_year_index(2025, zone)
    assert len(index) == 8760
    assert index[0] == pd.Timestamp("2024-12-31T23:00Z")
    assert index[-1] == pd.Timestamp("2025-12-31T22:00Z")
    local = index.tz_convert(zone)
    assert len(local[local.strftime("%Y-%m-%d") == "2025-03-30"]) == 23
    assert len(local[local.strftime("%Y-%m-%d") == "2025-10-26"]) == 25
    assert ((local.dayofweek < 5) & (local.hour >= 8) & (local.hour < 20)).sum() == 3132


@pytest.mark.parametrize("year,zone", [(1899, "Europe/Berlin"), (True, "Europe/Berlin"), (2025, "invalid-zone"), (2025, None)])
def test_bad_local_year_is_rejected(year, zone):
    with pytest.raises(HistoricalDataError):
        local_year_index(year, zone)


def test_correct_design_and_optional_source_years():
    data = design()
    data["time"].update(source_weather_year=2025, source_market_year=2025)
    original = copy.deepcopy(data)
    assert validate_design(data) is None
    assert data == original


@pytest.mark.parametrize("key,value", [
    ("historical_year", 2023), ("expected_hours", 8784), ("start_utc_inclusive", "2025-01-01T00:00Z"),
    ("end_utc_exclusive", "2026-01-01T00:00Z"), ("start_utc_inclusive", "2024-12-31T23:00"),
    ("reject_positional_year_remapping", False), ("source_weather_year", 2023),
    ("monthly_grouping", "UTC"), ("resolution_hours", True),
])
def test_inconsistent_design_time_is_rejected(key, value):
    data = design()
    data["time"][key] = value
    with pytest.raises(HistoricalDataError):
        validate_design(data)


def test_design_rejects_wrong_site_timezone_d2_and_nonboolean_consumption_flag():
    for mutate in (
        lambda data: data["sites"][0].update(calendar_timezone="UTC"),
        lambda data: data["hydrogen_demand"]["profiles"]["D2"].update(active_hours=3120),
        lambda data: data.update(consumed_by_current_model=1),
    ):
        data = design()
        mutate(data)
        with pytest.raises(HistoricalDataError):
            validate_design(data)


@pytest.mark.parametrize("zone", ["Europe/Berlin", "Europe/Madrid"])
def test_2024_keeps_all_8784_source_hours_leap_day_dst_and_weekday_profile(zone):
    index = local_year_index(2024, zone)
    assert len(index) == 8784
    assert index[0] == pd.Timestamp("2023-12-31T23:00Z")
    assert index[-1] == pd.Timestamp("2024-12-31T22:00Z")
    local = index.tz_convert(zone)
    assert set(local.year) == {2024}
    assert sum(local.strftime("%Y-%m-%d") == "2024-02-29") == 24
    assert sum(local.strftime("%Y-%m-%d") == "2024-03-31") == 23
    assert sum(local.strftime("%Y-%m-%d") == "2024-10-27") == 25
    assert ((local.dayofweek < 5) & (local.hour >= 8) & (local.hour < 20)).sum() == 3144
    assert index.is_unique


def design_2024():
    data = design()
    data["consumed_by_current_model"] = True
    data["time"].update(historical_year=2024, source_weather_year=2024, source_market_year=2024,
                        expected_hours=8784, start_utc_inclusive="2023-12-31T23:00:00Z",
                        end_utc_exclusive="2024-12-31T23:00:00Z")
    data["hydrogen_demand"]["profiles"]["D2"]["active_hours"] = 3144
    return data


def test_2024_design_can_be_consumed_without_relabelling_2025():
    assert validate_design(design_2024()) is None
    prior = design()
    prior["consumed_by_current_model"] = True
    assert validate_design(prior) is None


@pytest.mark.parametrize("key,value", [("expected_hours", 8760), ("source_weather_year", 2025),
                                      ("source_market_year", 2025), ("start_utc_inclusive", "2024-12-31T23:00Z")])
def test_2024_design_rejects_2025_year_or_clock_substitution(key, value):
    data = design_2024()
    data["time"][key] = value
    with pytest.raises(HistoricalDataError):
        validate_design(data)


def weather_payload():
    return {
        "timezone": "GMT", "utc_offset_seconds": 0,
        "hourly_units": {
            "time": "iso8601", "temperature_2m": "°C", "surface_pressure": "hPa",
            "wind_speed_10m": "m/s", "shortwave_radiation": "W/m²",
            "direct_normal_irradiance": "W/m²", "diffuse_radiation": "W/m²",
        },
        "hourly": {
            "time": ["2024-12-31T23:00", "2025-01-01T00:00", "2025-01-01T01:00"],
            "temperature_2m": [0, 10, 20], "surface_pressure": [1000, 1010, 1020],
            "wind_speed_10m": [2, 4, 8], "shortwave_radiation": [100, 200, 300],
            "direct_normal_irradiance": [50, 150, 250], "diffuse_radiation": [20, 40, 60],
        },
    }


def test_weather_semantics_midpoint_pressure_conversion_and_no_mutation():
    data = weather_payload()
    original = copy.deepcopy(data)
    result = adapt_open_meteo_weather(data, hourly_index())
    assert result.index.equals(hourly_index() + pd.Timedelta(minutes=30))
    assert tuple(result.columns) == ("temp_air", "ghi", "dni", "dhi", "wind_speed", "pressure")
    np.testing.assert_allclose(result.temp_air, [5, 15])
    np.testing.assert_allclose(result.wind_speed, [3, 6])
    np.testing.assert_allclose(result.pressure, [100500, 101500])
    np.testing.assert_allclose(result.ghi, [200, 300])
    np.testing.assert_allclose(result.dni, [150, 250])
    np.testing.assert_allclose(result.dhi, [40, 60])
    assert data == original


@pytest.mark.parametrize("field,bad", [("surface_pressure", "Pa"), ("wind_speed_10m", "km/h"), ("shortwave_radiation", "kWh/m²"), ("time", "unixtime")])
def test_weather_wrong_units_are_rejected(field, bad):
    data = weather_payload()
    data["hourly_units"][field] = bad
    with pytest.raises(HistoricalDataError, match="unit|iso8601"):
        adapt_open_meteo_weather(data, hourly_index())


@pytest.mark.parametrize("bad", [None, np.nan, np.inf, True, "2", -1])
def test_weather_invalid_wind_is_rejected(bad):
    data = weather_payload()
    data["hourly"]["wind_speed_10m"][1] = bad
    with pytest.raises(HistoricalDataError):
        adapt_open_meteo_weather(data, hourly_index())


@pytest.mark.parametrize("times", [
    ["2024-12-31T23:00", "2025-01-01T00:00", "2025-01-01T00:00"],
    ["2024-12-31T23:00", "2025-01-01T00:00", "2025-01-01T02:00"],
    ["2025-01-01T00:00", "2025-01-01T01:00", "2025-01-01T02:00"],
    ["2024-12-31T23:00", "2025-01-01T01:00", "2025-01-01T00:00"],
])
def test_weather_duplicate_gap_shift_or_unsorted_is_rejected(times):
    data = weather_payload()
    data["hourly"]["time"] = times
    with pytest.raises(HistoricalDataError):
        adapt_open_meteo_weather(data, hourly_index())


def test_weather_schema_length_timezone_and_endpoint_padding_are_required():
    for mutate in (
        lambda data: data.pop("hourly_units"),
        lambda data: data.update(timezone="Europe/Berlin"),
        lambda data: data.update(utc_offset_seconds=3600),
        lambda data: data["hourly"].update(temperature_2m=[1, 2]),
        lambda data: data["hourly"].pop("direct_normal_irradiance"),
    ):
        data = weather_payload()
        mutate(data)
        with pytest.raises(HistoricalDataError):
            adapt_open_meteo_weather(data, hourly_index())
    data = weather_payload()
    for key in data["hourly"]:
        data["hourly"][key] = data["hourly"][key][:-1]
    with pytest.raises(HistoricalDataError, match="boundaries"):
        adapt_open_meteo_weather(data, hourly_index())


@pytest.mark.parametrize("minutes", [5, 15, 60])
def test_interval_price_average_and_power_energy(minutes):
    index = pd.date_range(hourly_index()[0], periods=120 // minutes, freq=f"{minutes}min")
    values = np.arange(len(index), dtype=float) - 10
    price = pd.Series(values, index=index, name="price")
    result = aggregate_interval_series(price, minutes, hourly_index())
    np.testing.assert_allclose(result, values.reshape(2, 60 // minutes).mean(axis=1))
    assert result.index.equals(hourly_index())
    energy = aggregate_interval_series(pd.Series(np.full(len(index), 120.0), index=index), minutes, hourly_index(), value_kind="power")
    np.testing.assert_allclose(energy, [120, 120])


def test_interval_source_padding_is_allowed_without_changing_results():
    index = pd.date_range(hourly_index()[0] - pd.Timedelta(hours=1), periods=16, freq="15min")
    result = aggregate_interval_series(pd.Series(80.0, index=index), 15, hourly_index(), value_kind="power")
    np.testing.assert_allclose(result, [80, 80])


@pytest.mark.parametrize("defect", ["gap", "duplicate", "shift", "naive", "local", "nan", "negative_power"])
def test_invalid_native_grid_or_power_is_rejected(defect):
    index = pd.date_range(hourly_index()[0], periods=8, freq="15min")
    series = pd.Series(120.0, index=index)
    if defect == "gap":
        series = series.drop(index[2])
    elif defect == "duplicate":
        series.index = index[:3].append(index[2:7])
    elif defect == "shift":
        series.index += pd.Timedelta(minutes=15)
    elif defect == "naive":
        series.index = index.tz_localize(None)
    elif defect == "local":
        series.index = index.tz_convert("Europe/Berlin")
    elif defect == "nan":
        series.iloc[2] = np.nan
    else:
        series.iloc[2] = -1
    with pytest.raises(HistoricalDataError):
        aggregate_interval_series(series, 15, hourly_index(), value_kind="power")


@pytest.mark.parametrize("minutes", [0, 30, True])
def test_unsupported_native_resolution_is_rejected(minutes):
    with pytest.raises(HistoricalDataError):
        aggregate_interval_series(pd.Series([1, 2], index=hourly_index()), minutes, hourly_index())


def factor(point=500):
    return {"point": point, "lower": point * .8, "upper": point * 1.2,
            "source_url": "https://example.org/verified-factor", "reference_year": 2025,
            "emissions_basis": "direct_CO2e", "generation_basis": "net_electricity"}


def test_sourced_operational_weighting_bounds_and_inactive_unknown_category():
    generation = pd.DataFrame({"gas": [2., 3.], "renewable": [2., 1.], "inactive_unknown": [0., 0.]}, index=hourly_index())
    records = {"gas": factor(), "renewable": factor(0)}
    original = generation.copy(deep=True)
    original_records = copy.deepcopy(records)
    result = construct_operational_factors(generation, records)
    np.testing.assert_allclose(result.point, [250, 375])
    np.testing.assert_allclose(result.lower, [200, 300])
    np.testing.assert_allclose(result.upper, [300, 450])
    pd.testing.assert_frame_equal(generation, original)
    assert records == original_records


def test_positive_unknown_category_cannot_silently_get_zero_factor():
    generation = pd.DataFrame({"residual": [1., 0.], "gas": [1., 1.]}, index=hourly_index())
    with pytest.raises(HistoricalDataError, match="residual"):
        construct_operational_factors(generation, {"gas": factor()})


@pytest.mark.parametrize("bad", [-1., np.nan, np.inf])
def test_invalid_generation_is_rejected(bad):
    generation = pd.DataFrame({"gas": [1., bad]}, index=hourly_index())
    with pytest.raises(HistoricalDataError):
        construct_operational_factors(generation, {"gas": factor()})


def test_zero_denominator_is_rejected():
    generation = pd.DataFrame({"gas": [1., 0.]}, index=hourly_index())
    with pytest.raises(HistoricalDataError, match="zero denominator"):
        construct_operational_factors(generation, {"gas": factor()})


@pytest.mark.parametrize("key,bad", [
    ("point", "500"), ("point", np.nan), ("point", True), ("point", -1),
    ("lower", 501), ("upper", 499), ("source_url", ""), ("reference_year", None),
    ("emissions_basis", "CO2_only"), ("generation_basis", "gross_electricity"),
])
def test_unsourced_or_inconsistent_factors_are_rejected(key, bad):
    record = factor()
    record[key] = bad
    generation = pd.DataFrame({"gas": [1., 1.]}, index=hourly_index())
    with pytest.raises(HistoricalDataError):
        construct_operational_factors(generation, {"gas": record})


@pytest.mark.parametrize("defect", ["naive", "midpoint", "gap"])
def test_target_requires_exact_aware_utc_hourly_grid(defect):
    index = hourly_index(3)
    if defect == "naive":
        index = index.tz_localize(None)
    elif defect == "midpoint":
        index += pd.Timedelta(minutes=30)
    else:
        index = index.delete(1)
    with pytest.raises(HistoricalDataError):
        adapt_open_meteo_weather(weather_payload(), index)
