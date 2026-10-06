"""Fail-closed reader for REE's historical peninsular DEMANDAAU snapshots.

This module preserves the published fields and decodes REE's local civil times.
It does not construct an approved emissions factor. The portal describes
instantaneous/telemeasured power, rather than settled five-minute mean energy.
Any MW * 5/60 conversion exposed here is an explicitly diagnostic rectangle
approximation and is subject to technology, net/gross and coverage reconciliation.

Primary sources (snapshots and SHA256s are in ../sources/spain_checks):
* https://demanda.ree.es/visiona/build/curvas_demanda.min.js?v=4.1.1.2
  The generation table excludes raw ``hid``; ``turb``, ``conb``, ``bat`` and
  ``consBat`` populate the separate storage table. ``sol`` and ``aut`` are
  older aggregate fields, not additional generation technologies.
* https://demanda.ree.es/visiona/l10n/es_ES.js?v=4.1.1.2
  ``gnhd`` is Hidráulica, ``bio`` is Biocombustible, ``cogenResto`` is
  Cogeneración y residuos and ``vap`` is Turbina de vapor. The help describes
  instantaneous power and an explicit self-consumption coverage change from
  2025-12-11; earlier coverage includes only mandatory telemetry.
* https://demanda.ree.es/WSvisionaMovilesPeninsulaRest/resources/
  demandaGeneracionPeninsula?callback=sample&curva=DEMANDAAU&fecha=2025-10-26
  The raw ordered timestamps distinguish ``2A:mm`` and ``2B:mm``. A is the
  first 02:xx hour (+02:00) and B the second (+01:00), as independently checked
  against Europe/Madrid civil-time rules. This inference is explicit: the
  frontend source does not itself document the UTC meaning of the suffixes.
* https://www.ree.es/es/datos/generacion
  Defines instantaneous/telemeasured power, production boundaries and storage.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime, timedelta, timezone
import json
import math
import re
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

TIMEZONE = "Europe/Madrid"
SOURCE_URL = (
    "https://demanda.ree.es/WSvisionaMovilesPeninsulaRest/resources/"
    "demandaGeneracionPeninsula?callback=sample&curva=DEMANDAAU&fecha={day}"
)
FIELD_LABELS = {
    "eol": "Eólica",
    "nuc": "Nuclear",
    "gf": "Fuel/gas",
    "car": "Carbón",
    "cc": "Ciclo combinado",
    "gnhd": "Hidráulica",
    "solFot": "Solar fotovoltaica",
    "solTer": "Solar térmica",
    "bio": "Biocombustible",
    "cogenResto": "Cogeneración y residuos",
    "vap": "Turbina de vapor",
}
PRIMARY_GENERATION_FIELDS = tuple(FIELD_LABELS)
STORAGE_FIELDS = ("turb", "conb", "bat", "consBat")
AGGREGATE_FIELDS = ("hid", "sol", "aut")
EXCHANGE_FIELDS = (
    "inter", "icb", "expAnd", "expMar", "expPor", "expFra", "expTot",
    "impFra", "impPor", "impMar", "impAnd", "impTot",
)
KNOWN_NUMERIC_FIELDS = frozenset(
    PRIMARY_GENERATION_FIELDS + STORAGE_FIELDS + AGGREGATE_FIELDS
    + EXCHANGE_FIELDS + ("dem", "dif")
)
_TS = re.compile(r"^(\d{4}-\d{2}-\d{2}) (\d{2}|2[AB]):(\d{2})$")
_JSONP = re.compile(
    r"^[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*\s*\((.*)\)\s*;?\s*$",
    re.DOTALL,
)


class REEDataError(ValueError):
    """A snapshot violates the source/time/field contract."""


def _load_payload(payload: str | bytes | Mapping[str, Any]) -> Mapping[str, Any]:
    if isinstance(payload, Mapping):
        return payload
    if isinstance(payload, bytes):
        payload = payload.decode("utf-8-sig")
    if not isinstance(payload, str):
        raise REEDataError("Payload must be JSON, JSONP or a mapping")
    source = payload.lstrip("\ufeff").strip()
    if not source.startswith("{"):
        wrapper = _JSONP.fullmatch(source)
        if not wrapper:
            raise REEDataError("Unsupported JSONP wrapper; JavaScript is never evaluated")
        source = wrapper.group(1)
    try:
        result = json.loads(source)
    except json.JSONDecodeError as exc:
        raise REEDataError("Invalid JSON payload") from exc
    if not isinstance(result, Mapping):
        raise REEDataError("Expected a JSON object")
    return result


def _timestamp_utc(raw: str) -> datetime:
    match = _TS.fullmatch(raw)
    if not match:
        raise REEDataError(f"Unsupported REE timestamp: {raw!r}")
    day_text, hour_token, minute_text = match.groups()
    special = hour_token in ("2A", "2B")
    hour = 2 if special else int(hour_token)
    try:
        wall = datetime.combine(date.fromisoformat(day_text), datetime.min.time())
        wall = wall.replace(hour=hour, minute=int(minute_text))
    except ValueError as exc:
        raise REEDataError(f"Invalid civil timestamp: {raw!r}") from exc
    madrid = ZoneInfo(TIMEZONE)
    first = wall.replace(tzinfo=madrid, fold=0)
    second = wall.replace(tzinfo=madrid, fold=1)
    ambiguous = first.utcoffset() != second.utcoffset()
    if special:
        if not ambiguous or first.utcoffset() != timedelta(hours=2) or second.utcoffset() != timedelta(hours=1):
            raise REEDataError(f"2A/2B suffix outside the Madrid autumn transition: {raw!r}")
        local = first if hour_token == "2A" else second
    else:
        if ambiguous:
            raise REEDataError(f"Ambiguous/nonexistent local hour requires a valid 2A/2B suffix: {raw!r}")
        local = first
    utc = local.astimezone(timezone.utc)
    if utc.astimezone(madrid).replace(tzinfo=None) != wall:
        raise REEDataError(f"Nonexistent Madrid local time: {raw!r}")
    if int(minute_text) % 5:
        raise REEDataError(f"Timestamp is outside the five-minute grid: {raw!r}")
    return utc


def expected_day_index(day: str | date) -> pd.DatetimeIndex:
    """Real five-minute intervals for one local date, including DST changes."""
    day_value = date.fromisoformat(day) if isinstance(day, str) else day
    madrid = ZoneInfo(TIMEZONE)
    start = datetime.combine(day_value, datetime.min.time(), tzinfo=madrid)
    end = datetime.combine(day_value + timedelta(days=1), datetime.min.time(), tzinfo=madrid)
    return pd.date_range(
        start.astimezone(timezone.utc), end.astimezone(timezone.utc),
        freq="5min", inclusive="left", name="time_utc",
    )


def parse_day(payload: str | bytes | Mapping[str, Any], day: str | date) -> pd.DataFrame:
    """Return every source field on an exact aware UTC five-minute index.

    Padding outside the target local date is trimmed explicitly. Gaps,
    duplicates, reordered rows and invalid timestamps raise; values are never
    filled. JSON nulls become NaNs and actual zeros are retained.
    """
    day_value = date.fromisoformat(day) if isinstance(day, str) else day
    target = day_value.isoformat()
    obj = _load_payload(payload)
    rows = obj.get("valoresHorariosGeneracion")
    if not isinstance(rows, list):
        raise REEDataError("Missing valoresHorariosGeneracion list")
    selected = []
    for row in rows:
        if not isinstance(row, Mapping) or not isinstance(row.get("ts"), str):
            raise REEDataError("Each raw row must have a string ts")
        if row["ts"].split(" ", 1)[0] == target:
            selected.append(dict(row))
    if not selected:
        raise REEDataError(f"No rows for {target}")
    index = pd.DatetimeIndex([_timestamp_utc(row["ts"]) for row in selected], name="time_utc")
    expected = expected_day_index(day_value)
    if not index.equals(expected):
        missing = expected.difference(index)
        extra = index.difference(expected)
        raise REEDataError(
            f"Incomplete or unordered local day {target}: rows={len(index)}, expected={len(expected)}, "
            f"duplicates={int(index.duplicated().sum())}, missing={len(missing)}, extra={len(extra)}"
        )
    columns = tuple(selected[0])
    if any(set(row) != set(columns) for row in selected):
        raise REEDataError("Field schema changes within the day; no silent missing-column fill")
    for row in selected:
        for column, value in row.items():
            if column == "ts" or value is None:
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise REEDataError(f"Invalid numeric source value in {column!r}; only explicit null may denote missing data")
    frame = pd.DataFrame(selected, index=index)
    for column in frame.columns:
        if column == "ts":
            continue
        values = frame[column]
        if any(value is not None and not isinstance(value, (int, float)) for value in values):
            raise REEDataError(f"Non-numeric value in source field {column!r}")
        frame[column] = pd.to_numeric(values, errors="raise")
    frame.attrs.update({
        "source_url": SOURCE_URL.format(day=target), "local_day": target,
        "local_timezone": TIMEZONE, "raw_row_count": len(rows),
        "trimmed_padding_rows": len(rows) - len(selected),
        "resolution_minutes": 5, "power_unit": "MW",
        "power_semantics": "instantaneous/telemeasured or estimated; not verified interval mean",
        "energy_release_status": "DIAGNOSTIC_ONLY_NOT_APPROVED_ENERGY",
        "self_consumption_coverage_change": "2025-12-11",
        "dst_suffix_rule": "2A first02h(+02);2B second02h(+01); explicit civil-time inference",
    })
    return frame


def primary_generation_fields(frame: pd.DataFrame) -> tuple[str, ...]:
    """Return documented primary fields, refusing unknown or missing categories."""
    unknown = set(frame.columns) - KNOWN_NUMERIC_FIELDS - {"ts"}
    missing = set(PRIMARY_GENERATION_FIELDS) - set(frame.columns)
    if unknown or missing:
        raise REEDataError(f"Unreconciled generation schema: unknown={sorted(unknown)}, missing={sorted(missing)}")
    return PRIMARY_GENERATION_FIELDS


def report_quality(frame: pd.DataFrame) -> dict[str, Any]:
    numeric = frame.select_dtypes(include="number")
    fields = primary_generation_fields(frame)
    primary_sum = frame.loc[:, list(fields)].sum(axis=1, min_count=len(fields))
    return {
        "rows": len(frame), "utc_first": frame.index[0].isoformat(),
        "utc_last": frame.index[-1].isoformat(),
        "nulls_by_field": {key: int(value) for key, value in numeric.isna().sum().items()},
        "zeros_by_field": {key: int(value) for key, value in numeric.eq(0).sum().items()},
        "negative_counts_by_field": {key: int(value) for key, value in numeric.lt(0).sum().items()},
        "zero_primary_sum_count": int(primary_sum.eq(0).sum()),
        "zero_primary_sum_times_utc": [stamp.isoformat() for stamp in frame.index[primary_sum.eq(0)]],
        "null_primary_sum_count": int(primary_sum.isna().sum()),
        "excluded_storage_fields": list(STORAGE_FIELDS),
        "excluded_aggregate_fields": list(AGGREGATE_FIELDS),
        "factor_zero_is_not_inferred_from_zero_denominator": True,
        "metadata": dict(frame.attrs),
    }


def hourly_rectangle_approximation(frame: pd.DataFrame) -> pd.DataFrame:
    """Diagnostic hour-energy approximation, with no automatic NaN replacement.

    Each valid hour has 12 measured/estimated power points. The left rectangle
    approximation sums these points * 5/60. Storage and raw parent aggregates
    are excluded. An hour with any missing value retains NaN for that category.
    """
    fields = primary_generation_fields(frame)
    for column in fields:
        if frame[column].map(lambda value: isinstance(value, bool) or (pd.notna(value) and not math.isfinite(value))).any():
            raise REEDataError(f"Invalid finite numeric power in {column!r}")
    if not isinstance(frame.index, pd.DatetimeIndex) or frame.index.tz is None:
        raise REEDataError("An aware UTC index is required")
    if not frame.index.is_monotonic_increasing or frame.index.has_duplicates:
        raise REEDataError("Unique chronological five-minute values are required")
    if str(frame.index.tz) != "UTC":
        raise REEDataError("Convert to the canonical UTC index before hourly aggregation")
    if len(frame.index) > 1 and not (frame.index[1:] - frame.index[:-1] == pd.Timedelta(minutes=5)).all():
        raise REEDataError("No five-minute gaps may be filled in hourly aggregation")
    counts = frame.groupby(frame.index.floor("h")).size()
    if not counts.eq(12).all():
        raise REEDataError("Each diagnostic hour needs all 12 five-minute source points")
    hourly = frame.loc[:, list(fields)].resample("h").sum(min_count=12) * (5 / 60)
    hourly.attrs.update(frame.attrs)
    hourly.attrs.update({
        "unit": "MWh_rectangle_approximation", "aggregation": "sum of twelve MW samples * 5/60 h",
        "interval_interpretation": "explicit left rectangle approximation for [t,t+1h)",
        "energy_release_status": "DIAGNOSTIC_ONLY_NOT_APPROVED_ENERGY",
        "approved_emissions_factor": False,
    })
    return hourly
