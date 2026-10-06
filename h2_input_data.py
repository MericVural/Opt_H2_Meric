"""Standardisierte stündliche Eingabedaten für das H2-Optimierungsmodell.

Dieses Modul trennt die Datenprüfung von den späteren Datenquellen. Es ist
unerheblich, ob ein DataFrame aus einem künstlichen Testfall, einer CSV-Datei,
PVGIS oder dem ursprünglichen Modell stammt. Nach erfolgreicher Validierung
besitzt er dieselben Spalten, Einheiten, eine stündliche UTC-Zeitachse und
eindeutige Wertebereiche.

Beim Import werden keine Dateien geöffnet und keine Verzeichnisse angelegt.
"""

from __future__ import annotations

from copy import deepcopy
import json
from types import MappingProxyType
from typing import Final, Mapping

import numpy as np
import pandas as pd


TIMESTAMP_COLUMN: Final[str] = "timestamp"
NUMERIC_HOURLY_COLUMNS: Final[tuple[str, ...]] = (
    "pv_capacity_factor",
    "wind_capacity_factor",
    "electricity_price",
    "grid_emission_factor",
    "h2_demand",
)
REQUIRED_HOURLY_COLUMNS: Final[tuple[str, ...]] = (
    TIMESTAMP_COLUMN,
    *NUMERIC_HOURLY_COLUMNS,
)
HOURLY_COLUMN_UNITS: Final[Mapping[str, str]] = MappingProxyType(
    {
        "timestamp": "UTC",
        "pv_capacity_factor": "fraction",
        "wind_capacity_factor": "fraction",
        "electricity_price": "EUR/MWh",
        "grid_emission_factor": "kg_CO2e/MWh",
        "h2_demand": "kg_H2/h",
    }
)
EXPECTED_TIME_STEP: Final[pd.Timedelta] = pd.Timedelta(hours=1)
REGULATORY_EMISSION_COLUMN: Final[str] = "regulatory_grid_emission_factor"
LEGACY_EMISSION_MODE: Final[str] = "legacy_shared_factor"
SEPARATE_EMISSION_MODE: Final[str] = "explicit_separate_factors"
REGULATORY_ONLY_EMISSION_MODE: Final[str] = "regulatory_only"
COMPLETE_EMISSIONS_REPORTING: Final[str] = "complete"
EMISSION_FACTOR_UNIT: Final[str] = "kg_CO2e/MWh"


class HourlyInputError(ValueError):
    """Verständlicher Validierungsfehler für stündliche Modelldaten."""


def validate_hourly_input(
    data: pd.DataFrame,
    *,
    expected_hours: int | None = None,
    require_separate_emission_factors: bool = False,
    emissions_reporting: str = COMPLETE_EMISSIONS_REPORTING,
) -> pd.DataFrame:
    """Prüfe und vereinheitliche einen stündlichen H2-Eingabedatensatz.

    Parameters
    ----------
    data:
        DataFrame mit mindestens den in ``REQUIRED_HOURLY_COLUMNS`` genannten
        Spalten. Zusätzliche Metadatenspalten bleiben erhalten.
    expected_hours:
        Optionale erwartete Zeilenzahl, beispielsweise 24 für einen Test oder
        8.760 für den vollständigen Basisfall.
    require_separate_emission_factors:
        Verlange zwei unabhängig dokumentierte Faktoren. ``grid_emission_factor``
        bleibt der betriebliche Faktor. Die optionale Spalte
        ``regulatory_grid_emission_factor`` aktiviert den getrennten Modus auch
        ohne dieses Flag. Dann muss ``data.attrs['emission_factor_sources']``
        die Einträge ``operational`` und ``regulatory`` enthalten, jeweils mit
        ``source_description``, ``reference_year``, ``spatial_scope``, ``unit``
        und ``emissions_basis``. Quellenwerte sind Beschreibungen, keine
        automatische Bestätigung ihrer wissenschaftlichen Eignung.
    emissions_reporting:
        Standard ``complete`` benötigt weiterhin den betrieblichen Faktor.
        Die explizite Wahl ``regulatory_only`` verlangt ausschließlich
        ``regulatory_grid_emission_factor`` und dessen eigene Quelle;
        ``grid_emission_factor`` und eine operative Quellenangabe müssen fehlen.
        Betriebliche Emissionen bleiben nicht ausgewertet, ohne Ersatzwert.

    Returns
    -------
    pandas.DataFrame
        Eine Kopie der Eingabe. Zeitstempel sind als UTC normalisiert und die
        fünf Modellgrößen als ``float`` gespeichert. Einheiten und Frequenz
        stehen zusätzlich in ``DataFrame.attrs``.

    Notes
    -----
    Negative Strompreise sind zulässig. Kapazitätsfaktoren müssen zwischen
    null und eins liegen; Emissionsfaktor und H2-Nachfrage dürfen nicht
    negativ sein. Mindestens eine Stunde muss eine positive H2-Nachfrage
    enthalten.
    """

    if not isinstance(data, pd.DataFrame):
        raise TypeError("data muss ein pandas.DataFrame sein.")
    if not isinstance(require_separate_emission_factors, bool):
        raise TypeError("require_separate_emission_factors muss ein boolescher Wert sein.")
    if emissions_reporting not in (COMPLETE_EMISSIONS_REPORTING, REGULATORY_ONLY_EMISSION_MODE):
        raise HourlyInputError("emissions_reporting muss complete oder regulatory_only sein.")
    regulatory_only = emissions_reporting == REGULATORY_ONLY_EMISSION_MODE
    if regulatory_only and require_separate_emission_factors:
        raise HourlyInputError("regulatory_only widerspricht require_separate_emission_factors.")
    if regulatory_only and "grid_emission_factor" in data.columns:
        raise HourlyInputError("regulatory_only benötigt keine operative grid_emission_factor-Spalte; sie muss fehlen.")
    if data.empty:
        raise HourlyInputError("Der stündliche Eingabedatensatz ist leer.")
    if data.columns.duplicated().any():
        duplicate_columns = data.columns[data.columns.duplicated()].tolist()
        raise HourlyInputError(
            f"Spaltennamen dürfen nicht doppelt vorkommen: {duplicate_columns}."
        )

    required_columns = (tuple(column for column in REQUIRED_HOURLY_COLUMNS if column != "grid_emission_factor")
                        + (REGULATORY_EMISSION_COLUMN,)) if regulatory_only else REQUIRED_HOURLY_COLUMNS
    missing_columns = [column for column in required_columns if column not in data.columns]
    if missing_columns:
        raise HourlyInputError(
            "Pflichtspalten fehlen: " + ", ".join(missing_columns) + "."
        )

    _validate_expected_hours(expected_hours)
    if expected_hours is not None and len(data) != expected_hours:
        raise HourlyInputError(
            f"Erwartet wurden {expected_hours} Stunden, vorhanden sind {len(data)}."
        )

    validated = data.copy(deep=True)
    validated[TIMESTAMP_COLUMN] = _parse_utc_timestamps(validated[TIMESTAMP_COLUMN])
    _validate_time_axis(validated[TIMESTAMP_COLUMN])
    site_context = data.attrs.get("eu_site_configuration")
    if site_context is not None:
        if not isinstance(site_context, dict):
            raise HourlyInputError("eu_site_configuration muss ein gültiger Standortvertrag sein.")
        year, zone = site_context.get("historical_year"), site_context.get("calendar_timezone")
        if type(year) is not int or not isinstance(zone, str):
            raise HourlyInputError("EU-Kalender benötigt ein explizites Jahr und eine Ortszeitzone.")
        try:
            local = validated[TIMESTAMP_COLUMN].dt.tz_convert(zone)
        except (ValueError, KeyError) as exc:
            raise HourlyInputError("Ungültige EU-Ortszeitzone.") from exc
        if set(local.dt.year) != {year}:
            raise HourlyInputError("EU-Zeitstempel widersprechen dem gewählten historischen Kalenderjahr.")
        contract = site_context.get("time_contract", {})
        if len(validated) == contract.get("expected_hours"):
            if (validated[TIMESTAMP_COLUMN].iloc[0] != pd.Timestamp(contract.get("start_utc_inclusive"))
                    or validated[TIMESTAMP_COLUMN].iloc[-1] + EXPECTED_TIME_STEP != pd.Timestamp(contract.get("end_utc_exclusive"))):
                raise HourlyInputError("EU-Volljahr benötigt die exakten lokalen Jahresgrenzen in UTC.")

    for column in NUMERIC_HOURLY_COLUMNS:
        if regulatory_only and column == "grid_emission_factor":
            continue
        validated[column] = _parse_finite_numeric_column(validated[column], column)
    if REGULATORY_EMISSION_COLUMN in validated.columns:
        validated[REGULATORY_EMISSION_COLUMN] = _parse_finite_numeric_column(
            validated[REGULATORY_EMISSION_COLUMN], REGULATORY_EMISSION_COLUMN
        )
        _require_nonnegative(validated, REGULATORY_EMISSION_COLUMN)

    for column in ("pv_capacity_factor", "wind_capacity_factor"):
        outside_range = ~validated[column].between(0.0, 1.0, inclusive="both")
        if outside_range.any():
            row = int(np.flatnonzero(outside_range.to_numpy())[0])
            value = validated[column].iloc[row]
            raise HourlyInputError(
                f"{column} muss zwischen 0 und 1 liegen; Zeile {row} enthält {value}."
            )

    if not regulatory_only:
        _require_nonnegative(validated, "grid_emission_factor")
    _require_nonnegative(validated, "h2_demand")
    if validated["h2_demand"].sum() <= 0.0:
        raise HourlyInputError(
            "Die gesamte H2-Nachfrage muss größer als null sein."
        )

    factor_contract = _validate_emission_factor_contract(
        data, require_separate=require_separate_emission_factors,
        emissions_reporting=emissions_reporting,
    )
    validated.attrs = deepcopy(data.attrs)
    validated.attrs.update(factor_contract)
    validated.attrs["column_units"] = dict(HOURLY_COLUMN_UNITS)
    if regulatory_only:
        validated.attrs["column_units"].pop("grid_emission_factor")
    if REGULATORY_EMISSION_COLUMN in validated.columns:
        validated.attrs["column_units"][REGULATORY_EMISSION_COLUMN] = EMISSION_FACTOR_UNIT
    validated.attrs["time_zone"] = "UTC"
    validated.attrs["frequency"] = "1h"
    validated.attrs["emissions_reporting"] = emissions_reporting
    validated.attrs["operational_emissions_status"] = "not_evaluated" if regulatory_only else "evaluated"
    return validated


def _validate_emission_factor_contract(
    data: pd.DataFrame, *, require_separate: bool,
    emissions_reporting: str = COMPLETE_EMISSIONS_REPORTING,
) -> dict[str, object]:
    """Prevent an explicit factor pair from silently sharing a legacy source."""
    declared_mode = data.attrs.get("emission_factor_mode")
    regulatory_only = emissions_reporting == REGULATORY_ONLY_EMISSION_MODE
    if declared_mode not in (None, LEGACY_EMISSION_MODE, SEPARATE_EMISSION_MODE, REGULATORY_ONLY_EMISSION_MODE):
        raise HourlyInputError("Unbekannter emission_factor_mode in den Eingabemetadaten.")
    if regulatory_only and declared_mode not in (None, REGULATORY_ONLY_EMISSION_MODE):
        raise HourlyInputError("regulatory_only widerspricht dem emission_factor_mode der Quellenmetadaten.")
    if not regulatory_only and declared_mode == REGULATORY_ONLY_EMISSION_MODE:
        raise HourlyInputError("regulatory_only benötigt eine explizite emissions_reporting-Auswahl.")
    has_regulatory = REGULATORY_EMISSION_COLUMN in data.columns
    if require_separate or declared_mode == SEPARATE_EMISSION_MODE:
        if not has_regulatory:
            raise HourlyInputError(
                "Getrennte Emissionsfaktoren sind erforderlich; "
                "regulatory_grid_emission_factor fehlt."
            )
    if not has_regulatory:
        if data.attrs.get("emission_factor_sources"):
            raise HourlyInputError(
                "emission_factor_sources beschreibt getrennte Faktoren, "
                "aber regulatory_grid_emission_factor fehlt."
            )
        return {"emission_factor_mode": LEGACY_EMISSION_MODE}
    if declared_mode == LEGACY_EMISSION_MODE:
        raise HourlyInputError(
            "regulatory_grid_emission_factor widerspricht legacy_shared_factor."
        )
    sources = data.attrs.get("emission_factor_sources")
    if not isinstance(sources, dict):
        raise HourlyInputError("Getrennte Faktoren benötigen emission_factor_sources.")
    if regulatory_only and set(sources) != {"regulatory"}:
        raise HourlyInputError("regulatory_only benötigt nur eine regulatorische Quelle; operational darf nicht vorgetäuscht werden.")
    for role in (("regulatory",) if regulatory_only else ("operational", "regulatory")):
        source = sources.get(role)
        if not isinstance(source, dict):
            raise HourlyInputError(f"emission_factor_sources.{role} fehlt.")
        for key in ("source_description", "spatial_scope", "emissions_basis"):
            if not isinstance(source.get(key), str) or not source[key].strip():
                raise HourlyInputError(f"emission_factor_sources.{role}.{key} fehlt.")
        year = source.get("reference_year")
        if isinstance(year, bool) or not isinstance(year, int) or not 1900 <= year <= 2100:
            raise HourlyInputError(
                f"emission_factor_sources.{role}.reference_year muss ein Bezugsjahr sein."
            )
        if source.get("unit") != EMISSION_FACTOR_UNIT:
            raise HourlyInputError(
                f"emission_factor_sources.{role}.unit muss {EMISSION_FACTOR_UNIT} sein."
            )
    try:
        json.dumps(sources, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise HourlyInputError("emission_factor_sources muss gültige JSON-Metadaten enthalten.") from exc
    return {
        "emission_factor_mode": REGULATORY_ONLY_EMISSION_MODE if regulatory_only else SEPARATE_EMISSION_MODE,
        "emission_factor_sources": deepcopy(sources),
    }


def _validate_expected_hours(expected_hours: int | None) -> None:
    if expected_hours is None:
        return
    if isinstance(expected_hours, bool) or not isinstance(expected_hours, int):
        raise TypeError("expected_hours muss eine ganze Zahl oder None sein.")
    if expected_hours <= 0:
        raise ValueError("expected_hours muss positiv sein.")


def _parse_utc_timestamps(values: pd.Series) -> pd.Series:
    try:
        timestamps = pd.to_datetime(values, errors="raise", utc=True)
    except (TypeError, ValueError) as exc:
        raise HourlyInputError(
            "timestamp enthält mindestens einen ungültigen Datumswert."
        ) from exc
    if timestamps.isna().any():
        raise HourlyInputError("timestamp enthält fehlende Datumswerte.")
    return timestamps


def _validate_time_axis(timestamps: pd.Series) -> None:
    duplicated = timestamps.duplicated(keep=False)
    if duplicated.any():
        first_duplicate = timestamps[duplicated].iloc[0]
        raise HourlyInputError(
            f"timestamp enthält einen doppelten Zeitstempel: {first_duplicate}."
        )
    if not timestamps.is_monotonic_increasing:
        raise HourlyInputError("timestamp muss streng aufsteigend sortiert sein.")

    time_steps = timestamps.diff().iloc[1:]
    wrong_steps = time_steps != EXPECTED_TIME_STEP
    if wrong_steps.any():
        position = int(np.flatnonzero(wrong_steps.to_numpy())[0]) + 1
        previous_timestamp = timestamps.iloc[position - 1]
        current_timestamp = timestamps.iloc[position]
        raise HourlyInputError(
            "Die Zeitreihe muss lückenlos stündlich sein; zwischen "
            f"{previous_timestamp} und {current_timestamp} liegt keine Stunde."
        )


def _parse_finite_numeric_column(values: pd.Series, column: str) -> pd.Series:
    if pd.api.types.is_bool_dtype(values.dtype):
        raise HourlyInputError(f"{column} muss numerisch sein und darf keine Bool-Werte enthalten.")
    try:
        numeric = pd.to_numeric(values, errors="raise").astype(float)
    except (TypeError, ValueError) as exc:
        raise HourlyInputError(f"{column} muss ausschließlich Zahlen enthalten.") from exc

    finite = np.isfinite(numeric.to_numpy())
    if not finite.all():
        row = int(np.flatnonzero(~finite)[0])
        raise HourlyInputError(
            f"{column} enthält in Zeile {row} NaN oder einen unendlichen Wert."
        )
    return numeric


def _require_nonnegative(data: pd.DataFrame, column: str) -> None:
    negative = data[column] < 0.0
    if negative.any():
        row = int(np.flatnonzero(negative.to_numpy())[0])
        value = data[column].iloc[row]
        raise HourlyInputError(
            f"{column} darf nicht negativ sein; Zeile {row} enthält {value}."
        )


__all__ = [
    "EXPECTED_TIME_STEP",
    "EMISSION_FACTOR_UNIT",
    "LEGACY_EMISSION_MODE",
    "REGULATORY_EMISSION_COLUMN",
    "REGULATORY_ONLY_EMISSION_MODE",
    "COMPLETE_EMISSIONS_REPORTING",
    "SEPARATE_EMISSION_MODE",
    "HOURLY_COLUMN_UNITS",
    "HourlyInputError",
    "NUMERIC_HOURLY_COLUMNS",
    "REQUIRED_HOURLY_COLUMNS",
    "TIMESTAMP_COLUMN",
    "validate_hourly_input",
]
