"""Strict, offline adapters for the historical EU Step 19 data contract.

Final model rows represent UTC interval starts, [t, t+1h). Weather profiles
are evaluated at t+30min: Open-Meteo radiation at t+1h belongs to that hour;
instantaneous boundary observations at t and t+1h are averaged. No source
timestamps are remapped by position and no missing values are filled.

This module fetches no data and supplies no emission-factor assumptions.
Callers must explicitly remove storage and hierarchy aggregates before
constructing the domestic primary-production emissions mix.
"""

from __future__ import annotations

import calendar
from collections.abc import Mapping
from numbers import Integral, Real
from urllib.parse import urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import numpy as np
import pandas as pd


class HistoricalDataError(ValueError):
    """A source or design violates the historical interval contract."""


_WEATHER_FIELDS = {
    "temperature_2m": ("temp_air", "°C"),
    "surface_pressure": ("pressure", "hPa"),
    "wind_speed_10m": ("wind_speed", "m/s"),
    "shortwave_radiation": ("ghi", "W/m²"),
    "direct_normal_irradiance": ("dni", "W/m²"),
    "diffuse_radiation": ("dhi", "W/m²"),
}
WEATHER_COLUMNS = ("temp_air", "ghi", "dni", "dhi", "wind_speed", "pressure")


def local_year_index(year: int, timezone_name: str) -> pd.DatetimeIndex:
    """Return every real UTC hour in a local calendar year, including leap day.

    Local DST hours remain distinct in UTC. Annual model scaling is configured
    separately; this adapter never drops or relabels source observations.
    """
    if isinstance(year, bool) or not isinstance(year, Integral) or not 1900 <= year <= 2199:
        raise HistoricalDataError("year must be an integer between 1900 and 2199.")
    if not isinstance(timezone_name, str) or not timezone_name:
        raise HistoricalDataError("timezone_name must be an explicit IANA timezone.")
    try:
        zone = ZoneInfo(timezone_name)
        start = pd.Timestamp(year=int(year), month=1, day=1, tz=zone)
        end = pd.Timestamp(year=int(year) + 1, month=1, day=1, tz=zone)
    except (ZoneInfoNotFoundError, ValueError, TypeError) as exc:
        raise HistoricalDataError(f"Invalid local-year timezone: {timezone_name!r}.") from exc
    index = pd.date_range(start.tz_convert("UTC"), end.tz_convert("UTC"), freq="h", inclusive="left")
    expected_hours = 8784 if calendar.isleap(int(year)) else 8760
    if len(index) != expected_hours:
        raise HistoricalDataError(f"Local year has {len(index)} hours instead of {expected_hours}.")
    return index


def validate_design(design: Mapping[str, object]) -> None:
    """Validate an explicit 2024 or 2025 EU historical source-year contract.

    Required sites are Hamburg/Moorburg and Huelva/La Rabida. Calendar counts
    follow the declared year; historical source years must agree with it.
    """
    if not isinstance(design, Mapping):
        raise HistoricalDataError("Design must be a mapping.")
    if "consumed_by_current_model" in design and type(design["consumed_by_current_model"]) is not bool:
        raise HistoricalDataError("consumed_by_current_model must be an explicit boolean.")
    contract = design.get("time")
    if not isinstance(contract, Mapping):
        raise HistoricalDataError("Design requires a time mapping.")
    year = contract.get("historical_year")
    if isinstance(year, bool) or not isinstance(year, Integral) or year not in (2024, 2025):
        raise HistoricalDataError("time.historical_year must explicitly be 2024 or 2025.")
    expected_hours = 8784 if calendar.isleap(int(year)) else 8760
    required = {
        "historical_year": year,
        "resolution_hours": 1,
        "storage_timezone": "UTC",
        "interval_semantics": "start, [t,t+1h)",
        "expected_hours": expected_hours,
        "reject_positional_year_remapping": True,
    }
    for key, expected in required.items():
        actual = contract.get(key)
        if actual != expected or (isinstance(expected, int) and not isinstance(expected, bool) and isinstance(actual, bool)):
            raise HistoricalDataError(f"time.{key} must be {expected!r}; got {actual!r}.")
    for key in ("source_weather_year", "source_market_year"):
        if key in contract and (contract[key] != year or isinstance(contract[key], bool)):
            raise HistoricalDataError(f"time.{key} must equal the declared historical year {year}.")
    if contract.get("year_basis") != "local calendar year at each site":
        raise HistoricalDataError("time.year_basis must declare the local calendar year at each site.")
    for key in ("monthly_grouping", "demand_profile_grouping"):
        if contract.get(key) != "site local timezone":
            raise HistoricalDataError(f"time.{key} must use site local timezone.")

    sites = design.get("sites")
    if not isinstance(sites, list) or len(sites) != 2:
        raise HistoricalDataError("Design requires exactly the two EU sites in a sites list.")
    expected_sites = {"hamburg_moorburg": "Europe/Berlin", "huelva_la_rabida": "Europe/Madrid"}
    seen: set[str] = set()
    start = _aware_timestamp(contract.get("start_utc_inclusive"), "time.start_utc_inclusive")
    end = _aware_timestamp(contract.get("end_utc_exclusive"), "time.end_utc_exclusive")
    for site in sites:
        if not isinstance(site, Mapping):
            raise HistoricalDataError("Every site must be a mapping.")
        site_id = site.get("site_id")
        if not isinstance(site_id, str) or site_id not in expected_sites or site_id in seen:
            raise HistoricalDataError(f"Unknown or duplicate site_id: {site_id!r}.")
        seen.add(site_id)
        zone_name = site.get("calendar_timezone")
        if zone_name != expected_sites[site_id]:
            raise HistoricalDataError(f"{site_id}.calendar_timezone must be {expected_sites[site_id]}.")
        index = local_year_index(year, zone_name)
        if start != index[0] or end != index[-1] + pd.Timedelta(hours=1):
            raise HistoricalDataError(f"UTC boundaries do not equal the full local year for {site_id}.")
        local_index = index.tz_convert(zone_name)
        d2_hours = int(((local_index.dayofweek < 5) & (local_index.hour >= 8) & (local_index.hour < 20)).sum())
        expected_d2_hours = d2_hours

    demand = design.get("hydrogen_demand")
    if not isinstance(demand, Mapping) or not isinstance(demand.get("profiles"), Mapping):
        raise HistoricalDataError("Design requires hydrogen_demand.profiles.D2.")
    d2 = demand["profiles"].get("D2")
    if not isinstance(d2, Mapping):
        raise HistoricalDataError("Design requires hydrogen_demand.profiles.D2.")
    expected_d2 = "1 ifMonday-Friday and08<=local_hour<20 else0"
    if d2.get("weight") != expected_d2:
        raise HistoricalDataError("D2.weight must preserve the prescribed Monday-Friday 08:00–20:00 local profile.")
    if "active_hours" in d2 and (d2["active_hours"] != expected_d2_hours or isinstance(d2["active_hours"], bool)):
        raise HistoricalDataError(f"D2.active_hours must be {expected_d2_hours} for {year}.")


def adapt_open_meteo_weather(payload: Mapping[str, object], target_index: pd.DatetimeIndex) -> pd.DataFrame:
    """Adapt a complete UTC Open-Meteo hourly payload to midpoint weather.

    Required source fields: temperature_2m (°C), surface_pressure (hPa),
    wind_speed_10m (m/s), shortwave_radiation, direct_normal_irradiance and
    diffuse_radiation (W/m²), with hourly.time (iso8601). Payload timezone
    must explicitly be GMT/UTC and utc_offset_seconds must be zero.

    Returned index is target_index+30min, in UTC. Pressure becomes Pa;
    temperature/wind/pressure average the two interval boundaries; radiation
    takes source(t+1h). All requested boundaries must exist without filling.
    """
    target = _utc_hourly_index(target_index, "target_index")
    if not isinstance(payload, Mapping):
        raise HistoricalDataError("Open-Meteo payload must be a mapping.")
    if payload.get("timezone") not in ("GMT", "UTC"):
        raise HistoricalDataError("Open-Meteo timezone must explicitly be GMT or UTC.")
    if payload.get("utc_offset_seconds") != 0 or isinstance(payload.get("utc_offset_seconds"), bool):
        raise HistoricalDataError("Open-Meteo utc_offset_seconds must be zero.")
    hourly = payload.get("hourly")
    units = payload.get("hourly_units")
    if not isinstance(hourly, Mapping) or not isinstance(units, Mapping):
        raise HistoricalDataError("Open-Meteo payload requires hourly and hourly_units mappings.")
    if units.get("time") != "iso8601":
        raise HistoricalDataError("Open-Meteo hourly_units.time must be iso8601.")
    times = hourly.get("time")
    if not isinstance(times, (list, tuple)) or not times or not all(isinstance(item, str) and item for item in times):
        raise HistoricalDataError("Open-Meteo hourly.time must be a nonempty array of ISO timestamps.")
    try:
        source_index = pd.DatetimeIndex(pd.to_datetime(times, utc=True, errors="raise"))
    except (TypeError, ValueError) as exc:
        raise HistoricalDataError("Open-Meteo source timestamps are invalid.") from exc
    source_index = _utc_hourly_index(source_index, "Open-Meteo hourly.time")
    weather = pd.DataFrame(index=source_index)
    for source_name, (target_name, expected_unit) in _WEATHER_FIELDS.items():
        if units.get(source_name) != expected_unit:
            raise HistoricalDataError(f"Open-Meteo {source_name} requires unit {expected_unit!r}; got {units.get(source_name)!r}.")
        values = hourly.get(source_name)
        if not isinstance(values, (list, tuple)) or len(values) != len(source_index):
            raise HistoricalDataError(f"Open-Meteo {source_name} must have exactly {len(source_index)} values.")
        weather[target_name] = _finite_array(values, source_name)
    for name in ("ghi", "dni", "dhi", "wind_speed"):
        if (weather[name] < 0).any():
            raise HistoricalDataError(f"Open-Meteo {name} contains negative values.")
    if (weather["pressure"] <= 0).any():
        raise HistoricalDataError("Open-Meteo surface pressure must be positive.")
    weather["pressure"] *= 100.0
    endpoints = target + pd.Timedelta(hours=1)
    required = target.union(endpoints)
    missing = required.difference(source_index)
    if len(missing):
        raise HistoricalDataError(f"Open-Meteo misses {len(missing)} required interval boundaries; first: {missing[0].isoformat()}.")
    midpoint = target + pd.Timedelta(minutes=30)
    result = pd.DataFrame(index=midpoint)
    for name in ("temp_air", "wind_speed", "pressure"):
        result[name] = (weather.loc[target, name].to_numpy() + weather.loc[endpoints, name].to_numpy()) / 2.0
    for name in ("ghi", "dni", "dhi"):
        result[name] = weather.loc[endpoints, name].to_numpy()
    return result.loc[:, WEATHER_COLUMNS]


def aggregate_interval_series(
    series: pd.Series,
    interval_minutes: int,
    target_index: pd.DatetimeIndex,
    *,
    value_kind: str = "price",
) -> pd.Series:
    """Aggregate regular UTC interval-start observations without filling.

    ``price`` accepts EUR/MWh (including negative values) and returns the
    duration-weighted hourly mean. ``power`` accepts nonnegative MW and
    returns hourly MWh by integration. Native intervals must be 5, 15 or
    60 minutes. Sources can include contiguous boundary padding; every
    requested hour must contain exactly all its native intervals.
    """
    target = _utc_hourly_index(target_index, "target_index")
    if not isinstance(series, pd.Series) or series.empty:
        raise HistoricalDataError("series must be a nonempty pandas Series.")
    if isinstance(interval_minutes, bool) or not isinstance(interval_minutes, Integral) or interval_minutes not in (5, 15, 60):
        raise HistoricalDataError("interval_minutes must explicitly be 5, 15 or 60.")
    if value_kind not in ("price", "power"):
        raise HistoricalDataError("value_kind must be 'price' or 'power'.")
    source = _utc_index(series.index, "series.index")
    interval = pd.Timedelta(minutes=int(interval_minutes))
    if not source.equals(source.floor(f"{int(interval_minutes)}min")):
        raise HistoricalDataError("Source timestamps must be aligned native interval starts.")
    if len(source) > 1 and not ((source[1:] - source[:-1]) == interval).all():
        raise HistoricalDataError("Source native interval grid is incomplete or irregular.")
    values = _finite_array(series.to_numpy(), "series")
    if value_kind == "power" and (values < 0).any():
        raise HistoricalDataError("Generation power must be nonnegative MW.")
    required = pd.date_range(target[0], target[-1] + pd.Timedelta(hours=1), freq=interval, inclusive="left")
    missing = required.difference(source)
    if len(missing):
        raise HistoricalDataError(f"Source misses {len(missing)} required native intervals; first: {missing[0].isoformat()}.")
    selected = pd.Series(values, index=source).loc[required].to_numpy()
    per_hour = selected.reshape(len(target), 60 // int(interval_minutes))
    energy_or_weighted_price = per_hour.sum(axis=1) * (int(interval_minutes) / 60.0)
    return pd.Series(energy_or_weighted_price, index=target, name=series.name, dtype=float)


def construct_operational_factors(
    generation_mwh: pd.DataFrame,
    factor_records: Mapping[str, Mapping[str, object]],
) -> pd.DataFrame:
    """Calculate production-weighted point/lower/upper kg CO2e/MWh_net.

    Every positive-generation column needs a sourced factor record with
    numeric ``point``, ``lower``, ``upper`` (kg CO2e/MWh_net), nonempty HTTP(S)
    ``source_url``, integer ``reference_year``, ``emissions_basis='direct_CO2e'``
    and ``generation_basis='net_electricity'``. Require 0 <= lower <= point
    <= upper. Zero-generation categories may have no record. These bounds
    are input sensitivity bounds, not statistical confidence intervals.

    The caller must exclude pumped-storage charging/discharging and source
    hierarchy aggregates before this call. No category is inferred to be
    emission-free and zero total generation is an error.
    """
    if not isinstance(generation_mwh, pd.DataFrame) or generation_mwh.empty or not len(generation_mwh.columns):
        raise HistoricalDataError("generation_mwh must be a nonempty generation DataFrame.")
    index = _utc_hourly_index(generation_mwh.index, "generation_mwh.index")
    if generation_mwh.columns.has_duplicates:
        raise HistoricalDataError("Generation category names must be unique.")
    if not isinstance(factor_records, Mapping):
        raise HistoricalDataError("factor_records must be a mapping of sourced numeric factors.")
    generation = pd.DataFrame(index=index)
    factors: dict[str, list[float]] = {bound: [] for bound in ("point", "lower", "upper")}
    for category in generation_mwh.columns:
        if not isinstance(category, str) or not category:
            raise HistoricalDataError("Generation categories must have nonempty string names.")
        values = _finite_array(generation_mwh[category].to_numpy(), f"generation[{category}]")
        if (values < 0).any():
            raise HistoricalDataError(f"Generation category {category!r} contains negative MWh.")
        generation[category] = values
        record = factor_records.get(category)
        if record is None and not (values > 0).any():
            for bound in factors:
                factors[bound].append(0.0)  # inactive column; contributes exactly zero energy
            continue
        if not isinstance(record, Mapping):
            raise HistoricalDataError(f"Positive production category {category!r} lacks a sourced factor record.")
        _validate_factor_metadata(category, record)
        bounds = {bound: _finite_scalar(record.get(bound), f"factor[{category}].{bound}") for bound in factors}
        if not 0 <= bounds["lower"] <= bounds["point"] <= bounds["upper"]:
            raise HistoricalDataError(f"Factor bounds for {category!r} must satisfy 0 <= lower <= point <= upper.")
        for bound in factors:
            factors[bound].append(bounds[bound])
    denominator = generation.sum(axis=1).to_numpy()
    if not np.isfinite(denominator).all() or (denominator <= 0).any():
        raise HistoricalDataError("Domestic primary generation must be positive and finite in every hour; zero denominator is forbidden.")
    result = pd.DataFrame(index=index)
    matrix = generation.to_numpy()
    for bound, values in factors.items():
        intensity = matrix @ np.asarray(values) / denominator
        if not np.isfinite(intensity).all():
            raise HistoricalDataError(f"Operational {bound} intensity is not finite.")
        result[bound] = intensity
    return result


def _utc_index(index: object, label: str) -> pd.DatetimeIndex:
    if not isinstance(index, pd.DatetimeIndex) or not len(index):
        raise HistoricalDataError(f"{label} must be a nonempty DatetimeIndex.")
    if index.tz is None or str(index.tz) != "UTC":
        raise HistoricalDataError(f"{label} must explicitly be timezone-aware UTC.")
    if index.hasnans or index.has_duplicates or not index.is_monotonic_increasing:
        raise HistoricalDataError(f"{label} must be finite, unique and strictly increasing.")
    return index


def _utc_hourly_index(index: object, label: str) -> pd.DatetimeIndex:
    result = _utc_index(index, label)
    if not result.equals(result.floor("h")):
        raise HistoricalDataError(f"{label} must contain hourly interval-start timestamps.")
    if len(result) > 1 and not ((result[1:] - result[:-1]) == pd.Timedelta(hours=1)).all():
        raise HistoricalDataError(f"{label} must be a complete hourly grid.")
    return result


def _aware_timestamp(value: object, label: str) -> pd.Timestamp:
    try:
        timestamp = pd.Timestamp(value)
    except (TypeError, ValueError) as exc:
        raise HistoricalDataError(f"{label} is not a valid UTC timestamp.") from exc
    if pd.isna(timestamp) or timestamp.tz is None or timestamp.utcoffset() != pd.Timedelta(0):
        raise HistoricalDataError(f"{label} must explicitly be timezone-aware UTC.")
    return timestamp.tz_convert("UTC")


def _finite_scalar(value: object, label: str) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
        raise HistoricalDataError(f"{label} must be a sourced numeric value, not a string or boolean.")
    result = float(value)
    if not np.isfinite(result):
        raise HistoricalDataError(f"{label} must be finite; missing values are forbidden.")
    return result


def _finite_array(values: object, label: str) -> np.ndarray:
    raw = np.asarray(values, dtype=object)
    if raw.ndim != 1 or any(isinstance(value, (bool, np.bool_)) or not isinstance(value, Real) for value in raw):
        raise HistoricalDataError(f"{label} must contain only numeric values, without missing values or booleans.")
    result = np.asarray(raw, dtype=float)
    if not np.isfinite(result).all():
        raise HistoricalDataError(f"{label} must contain only finite numbers; no NaN or infinity.")
    return result


def _validate_factor_metadata(category: str, record: Mapping[str, object]) -> None:
    url = record.get("source_url")
    if not isinstance(url, str) or urlparse(url).scheme not in ("http", "https") or not urlparse(url).netloc:
        raise HistoricalDataError(f"factor[{category}].source_url requires an explicit HTTP(S) evidence URL.")
    year = record.get("reference_year")
    if isinstance(year, bool) or not isinstance(year, Integral) or not 1900 <= year <= 2199:
        raise HistoricalDataError(f"factor[{category}].reference_year requires an explicit integer year.")
    if record.get("emissions_basis") != "direct_CO2e":
        raise HistoricalDataError(f"factor[{category}].emissions_basis must be direct_CO2e.")
    if record.get("generation_basis") != "net_electricity":
        raise HistoricalDataError(f"factor[{category}].generation_basis must be net_electricity.")


__all__ = [
    "HistoricalDataError", "WEATHER_COLUMNS", "local_year_index", "validate_design",
    "adapt_open_meteo_weather", "aggregate_interval_series", "construct_operational_factors",
]
