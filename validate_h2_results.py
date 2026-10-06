"""Unabhängige Abschlussprüfung gespeicherter H2-Szenarienergebnisse."""

from __future__ import annotations

import argparse
import calendar
import hashlib
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Final, Sequence
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import numpy as np
import pandas as pd


CHECKS_FILENAME: Final[str] = "validation_checks.csv"
SAMPLES_FILENAME: Final[str] = "validation_samples.csv"
REPORT_FILENAME: Final[str] = "validation_report.json"
COMPARISON_FILENAME: Final[str] = "scenario_comparison.csv"
ELECTRICITY_TOLERANCE_MWH: Final[float] = 1e-6
HYDROGEN_TOLERANCE_KG: Final[float] = 1e-4
COST_TOLERANCE_EUR_PER_YEAR: Final[float] = 0.05
RELATIVE_TOLERANCE: Final[float] = 1e-8
COST_COLUMNS: Final[tuple[str, ...]] = (
    "pv_annualized_capex_eur_per_year",
    "pv_fixed_opex_eur_per_year",
    "pv_variable_opex_eur_per_year",
    "wind_annualized_capex_eur_per_year",
    "wind_fixed_opex_eur_per_year",
    "wind_variable_opex_eur_per_year",
    "electrolyzer_annualized_capex_eur_per_year",
    "electrolyzer_fixed_opex_eur_per_year",
    "compressor_annualized_capex_eur_per_year",
    "compressor_fixed_opex_eur_per_year",
    "h2_storage_annualized_capex_eur_per_year",
    "h2_storage_fixed_opex_eur_per_year",
    "grid_electricity_eur_per_year",
    "water_eur_per_year",
)


@dataclass(frozen=True, slots=True)
class ValidationArtifacts:
    output_directory: Path
    checks_path: Path
    samples_path: Path
    report_path: Path
    all_checks_passed: bool


def validate_h2_results(
    results_directory: str | Path,
    *,
    output_directory: str | Path | None = None,
    expected_hours: int = 8_760,
    overwrite: bool = False,
) -> ValidationArtifacts:
    """Rechne zentrale Bilanzen unabhängig aus den Exportdateien nach."""

    if isinstance(expected_hours, bool) or not isinstance(expected_hours, int):
        raise TypeError("expected_hours muss eine ganze Zahl sein.")
    if expected_hours <= 0:
        raise ValueError("expected_hours muss positiv sein.")
    if not isinstance(overwrite, bool):
        raise TypeError("overwrite muss ein boolescher Wert sein.")

    results_root = Path(results_directory).expanduser().resolve()
    comparison_path = results_root / COMPARISON_FILENAME
    if not comparison_path.is_file():
        raise FileNotFoundError(f"Szenarienvergleich nicht gefunden: {comparison_path}")
    output_root = (
        Path(output_directory).expanduser().resolve()
        if output_directory is not None
        else results_root / "validation"
    )
    paths = {
        "checks": output_root / CHECKS_FILENAME,
        "samples": output_root / SAMPLES_FILENAME,
        "report": output_root / REPORT_FILENAME,
    }
    existing = [path for path in paths.values() if path.exists()]
    if existing and not overwrite:
        raise FileExistsError(
            "Validierungsergebnisse existieren bereits: "
            + ", ".join(path.name for path in existing)
            + ". Nutze --overwrite zum Ersetzen."
        )

    comparison = pd.read_csv(comparison_path)
    batch_metadata_path = results_root / "scenario_comparison_metadata.json"
    batch_metadata = json.loads(batch_metadata_path.read_text(encoding="utf-8")) if batch_metadata_path.is_file() else None
    required_comparison = {
        "scenario_id",
        "scenario",
        "result_directory",
        "input_sha256",
        "annual_h2_delivered_kg",
    }
    missing = sorted(required_comparison.difference(comparison.columns))
    if missing:
        raise ValueError(
            "Szenarienvergleich enthält nicht alle Pflichtspalten: " + ", ".join(missing)
        )
    if comparison.empty:
        raise ValueError("Szenarienvergleich darf nicht leer sein.")

    checks: list[dict[str, object]] = []
    samples: list[dict[str, object]] = []
    input_hashes = comparison["input_sha256"].astype(str)
    _add_check(
        checks,
        scenario="all",
        check_id="same_source_input_hash",
        value=float(input_hashes.nunique()),
        limit="= 1",
        passed=input_hashes.nunique() == 1,
        detail="Alle Szenarien müssen auf derselben Standort-Eingabedatei beruhen.",
    )
    expected_core = {"reference", "red_monthly", "red_hourly"}
    actual_scenarios = set(comparison["scenario"].astype(str))
    _add_check(
        checks,
        scenario="all",
        check_id="core_scenarios_present",
        value=float(len(actual_scenarios.intersection(expected_core))),
        limit="= 3",
        passed=expected_core.issubset(actual_scenarios),
        detail="S0, S1 und S2 müssen im Vergleich enthalten sein.",
    )

    for comparison_row in comparison.itertuples(index=False):
        scenario = str(comparison_row.scenario)
        scenario_directory = results_root / str(comparison_row.result_directory)
        summary_path = scenario_directory / "summary.csv"
        hourly_path = scenario_directory / "hourly_operation.csv"
        metadata_path = scenario_directory / "run_metadata.json"
        validated_input_path = scenario_directory / "validated_input.csv"
        for path in (summary_path, hourly_path, metadata_path, validated_input_path):
            if not path.is_file():
                raise FileNotFoundError(f"Ergebnisdatei fehlt: {path}")

        summary = pd.read_csv(summary_path)
        hourly = pd.read_csv(hourly_path)
        validated_input = pd.read_csv(validated_input_path)
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if len(summary) != 1:
            raise ValueError(f"{summary_path} muss genau eine Zeile enthalten.")
        summary_row = summary.iloc[0]
        parameters = metadata.get("model_parameters", {})
        _check_sensitivity_contract(checks, scenario, validated_input, metadata, parameters, validated_input_path)
        correlation_timezone = _check_temporal_calendar_contract(checks, scenario, metadata, batch_metadata)
        annualization_factor = _check_annualization_contract(
            checks, scenario, hourly, validated_input, metadata, summary_row, parameters
        )
        comparison_factor = getattr(comparison_row, "annualization_factor", float("nan"))
        comparison_ok = np.isfinite(float(comparison_factor)) and abs(float(comparison_factor)-annualization_factor) <= 1e-9
        for name in ("annual_hours", "modeled_hours", "annualization_basis"):
            if name in summary_row.index:
                comparison_ok = comparison_ok and getattr(comparison_row, name, None) == summary_row[name]
        _add_check(checks, scenario=scenario, check_id="annualization_comparison_matches_run",
                   value=float(bool(comparison_ok)), limit="= 1", passed=bool(comparison_ok),
                   detail="Szenarienvergleich übernimmt dieselbe unabhängig geprüfte Annualisierung wie der Einzellauf.")
        if isinstance(batch_metadata, dict) and ("annualization" in batch_metadata
                or str(batch_metadata.get("schema_version")) not in {"1.0","1.1","1.2"}):
            batch_contract = batch_metadata.get("annualization")
            modeled = len(hourly) * _parameter_value(parameters,"study.time_step_hours")
            batch_ok = (isinstance(batch_contract,dict)
                        and batch_contract.get("annual_hours") == round(annualization_factor*modeled,9)
                        and batch_contract.get("modeled_hours") == modeled
                        and batch_contract.get("basis") == summary_row.get("annualization_basis"))
            _add_check(checks,scenario=scenario,check_id="annualization_batch_metadata",value=float(bool(batch_ok)),
                       limit="= 1",passed=bool(batch_ok),detail="Auch die Stapel-Metadaten stimmen mit der unabhängig ermittelten Jahresbasis überein.")

        _check_time_axis(
            checks,
            scenario=scenario,
            hourly=hourly,
            validated_input=validated_input,
            expected_hours=expected_hours,
        )
        _add_check(
            checks,
            scenario=scenario,
            check_id="summary_input_hash_matches_comparison",
            value=float(
                str(summary_row["input_sha256"]) == str(comparison_row.input_sha256)
            ),
            limit="= 1",
            passed=str(summary_row["input_sha256"]) == str(comparison_row.input_sha256),
            detail="Hash aus Einzellauf und Szenarienvergleich.",
        )

        electric_residual = (
            hourly["pv_self_consumption_mwh"]
            + hourly["wind_self_consumption_mwh"]
            + hourly["grid_import_mwh"]
            - hourly["electrolyzer_electricity_mwh"]
            - hourly["compressor_electricity_mwh"]
        )
        storage_previous = hourly["h2_storage_level_kg"].shift(1)
        storage_previous.iloc[0] = hourly["h2_storage_level_kg"].iloc[-1]
        hydrogen_residual = (
            hourly["h2_storage_level_kg"]
            - storage_previous
            - hourly["h2_after_compression_kg"]
            + hourly["h2_demand_kg"]
        )
        _max_abs_check(
            checks,
            scenario,
            "hourly_electricity_balance",
            electric_residual,
            ELECTRICITY_TOLERANCE_MWH,
            "PV-Eigenverbrauch + Wind-Eigenverbrauch + Netz = Elektrolyseur + Kompressor.",
        )
        _max_abs_check(
            checks,
            scenario,
            "cyclic_hydrogen_storage_balance",
            hydrogen_residual,
            HYDROGEN_TOLERANCE_KG,
            "Speicherstand einschließlich zyklischem Übergang von Stunde 8760 zu Stunde 1.",
        )

        specific_electricity = _parameter_value(
            parameters,
            "technologies.electrolyzer.specific_electricity_kwh_per_kg_h2",
        ) / 1_000.0
        compressor_specific = (
            _parameter_value(
                parameters,
                "technologies.compressor.isentropic_energy_kwh_per_kg_h2",
            )
            / _parameter_value(
                parameters,
                "technologies.compressor.isentropic_efficiency_fraction",
            )
            / _parameter_value(
                parameters,
                "technologies.compressor.mechanical_efficiency_fraction",
            )
            / 1_000.0
        )
        h2_loss_fraction = _parameter_value(
            parameters, "technologies.compressor.h2_loss_fraction"
        )
        _max_abs_check(
            checks,
            scenario,
            "electrolyzer_conversion",
            hourly["h2_production_kg"]
            - hourly["electrolyzer_electricity_mwh"] / specific_electricity,
            HYDROGEN_TOLERANCE_KG,
            "H2-Produktion aus Elektrolyseur-Strom und spezifischem Strombedarf.",
        )
        _max_abs_check(
            checks,
            scenario,
            "compressor_electricity",
            hourly["compressor_electricity_mwh"]
            - hourly["h2_production_kg"] * compressor_specific,
            ELECTRICITY_TOLERANCE_MWH,
            "Verdichtungsstrom aus H2-Produktion und Wirkungsgraden.",
        )
        _max_abs_check(
            checks,
            scenario,
            "compressor_hydrogen_loss",
            hourly["h2_after_compression_kg"]
            - hourly["h2_production_kg"] * (1.0 - h2_loss_fraction),
            HYDROGEN_TOLERANCE_KG,
            "H2-Menge nach dem modellierten Verdichtungsverlust.",
        )
        _max_upper_check(
            checks,
            scenario,
            "pv_availability",
            hourly["pv_generation_mwh"] - hourly["pv_available_mwh"],
            ELECTRICITY_TOLERANCE_MWH,
            "PV-Erzeugung darf die verfügbare Energiemenge nicht überschreiten.",
        )
        _max_upper_check(
            checks,
            scenario,
            "wind_availability",
            hourly["wind_generation_mwh"] - hourly["wind_available_mwh"],
            ELECTRICITY_TOLERANCE_MWH,
            "Winderzeugung darf die verfügbare Energiemenge nicht überschreiten.",
        )
        _max_upper_check(
            checks,
            scenario,
            "storage_capacity",
            hourly["h2_storage_level_kg"] - float(summary_row["h2_storage_capacity_kg"]),
            HYDROGEN_TOLERANCE_KG,
            "Speicherstand darf die optimierte Kapazität nicht überschreiten.",
        )

        cost_sum = float(summary_row[list(COST_COLUMNS)].sum())
        objective = float(summary_row["objective_eur_per_year"])
        cost_residual = cost_sum - objective
        _add_check(
            checks,
            scenario=scenario,
            check_id="annual_cost_sum",
            value=abs(cost_residual),
            limit=f"<= {COST_TOLERANCE_EUR_PER_YEAR} EUR/a",
            passed=abs(cost_residual) <= COST_TOLERANCE_EUR_PER_YEAR,
            detail=f"Kostenkomponenten minus Zielfunktion: {cost_residual:.9g} EUR/a.",
        )
        delivered = float(summary_row["annual_h2_delivered_kg"])
        lcoh_residual = float(summary_row["lcoh_eur_per_kg_h2"]) - objective / delivered
        _add_check(
            checks,
            scenario=scenario,
            check_id="lcoh_definition",
            value=abs(lcoh_residual),
            limit=f"<= {RELATIVE_TOLERANCE} EUR/kg",
            passed=abs(lcoh_residual) <= RELATIVE_TOLERANCE,
            detail="LCOH = Jahreskosten / jährlich ausgelieferte H2-Menge.",
        )
        delivered_from_hours = float(hourly["h2_demand_kg"].sum()) * annualization_factor
        delivery_residual = delivered_from_hours - delivered
        _add_check(
            checks,
            scenario=scenario,
            check_id="annual_hydrogen_delivery",
            value=abs(delivery_residual),
            limit=f"<= {HYDROGEN_TOLERANCE_KG} kg/a",
            passed=abs(delivery_residual) <= HYDROGEN_TOLERANCE_KG,
            detail="Jahresnachfrage aus Stundenwerten und Annualisierungsfaktor.",
        )

        regulatory_factor = _check_emission_factor_contract(
            checks, scenario, validated_input, hourly, metadata, summary_row
        )
        has_operational_factor = "grid_emission_factor" in validated_input.columns
        if has_operational_factor:
            operational_emission_residual = (
                hourly["operational_grid_emissions_kg_co2e"]
                - hourly["grid_import_mwh"] * validated_input["grid_emission_factor"]
            )
        regulatory_emission_residual = (
            hourly["regulatory_emissions_kg_co2e"]
            - hourly["regulatory_non_renewable_electricity_mwh"]
            * regulatory_factor
        )
        if has_operational_factor:
            _max_abs_check(
                checks,
                scenario,
                "hourly_operational_emissions",
                operational_emission_residual,
                1e-5,
                "Physischer Netzbezug multipliziert mit dem stündlichen Netzfaktor.",
            )
        else:
            comparison_ok = all(
                column in comparison.columns and pd.isna(getattr(comparison_row, column))
                for column in ("annual_grid_emissions_kg_co2e", "operational_emission_intensity_kg_co2e_per_kg_h2")
            ) and getattr(comparison_row, "emissions_reporting", None) == "regulatory_only" and getattr(comparison_row, "operational_emissions_status", None) == "not_evaluated"
            _add_check(
                checks, scenario=scenario, check_id="comparison_operational_emissions_not_evaluated",
                value=float(comparison_ok), limit="= 1", passed=bool(comparison_ok),
                detail="Der Szenarienvergleich darf fehlende operative Emissionsresultate nicht durch null ersetzen.",
            )
        _max_abs_check(
            checks,
            scenario,
            "hourly_regulatory_emissions",
            regulatory_emission_residual,
            1e-5,
            "Regulatorisch nicht erneuerbare Strommenge multipliziert mit dem regulatorischen Eingabefaktor.",
        )
        annual_regulatory = (
            float(hourly["regulatory_emissions_kg_co2e"].sum())
            * annualization_factor
        )
        annual_emission_checks = [
            (
                "annual_regulatory_emissions",
                annual_regulatory,
                float(summary_row["annual_regulatory_emissions_kg_co2e"]),
            ),
        ]
        if has_operational_factor:
            annual_emission_checks.append((
                "annual_operational_emissions",
                float(hourly["operational_grid_emissions_kg_co2e"].sum()) * annualization_factor,
                float(summary_row["annual_grid_emissions_kg_co2e"]),
            ))
        for check_id, calculated, exported in annual_emission_checks:
            residual = calculated - exported
            tolerance = max(1e-4, RELATIVE_TOLERANCE * max(abs(exported), 1.0))
            _add_check(
                checks,
                scenario=scenario,
                check_id=check_id,
                value=abs(residual),
                limit=f"<= {tolerance:.6g} kg CO2e/a",
                passed=abs(residual) <= tolerance,
                detail="Unabhängige Summe der stündlichen Emissionsspalte.",
            )

        renewable = hourly["pv_generation_mwh"] + hourly["wind_generation_mwh"]
        rfnbo_use = hourly["rf_nbo_electricity_mwh"]
        correlation_period_count = 0
        if scenario == "red_monthly":
            timestamps = pd.to_datetime(hourly["timestamp"], utc=True)
            monthly_margin = (renewable - rfnbo_use).groupby(
                timestamps.dt.tz_convert(correlation_timezone).dt.strftime("%Y-%m")
            ).sum()
            correlation_period_count = len(monthly_margin)
            minimum_margin = float(monthly_margin.min())
            _add_check(
                checks,
                scenario=scenario,
                check_id="red_monthly_energy_correlation",
                value=minimum_margin,
                limit=f">= {-ELECTRICITY_TOLERANCE_MWH} MWh",
                passed=minimum_margin >= -ELECTRICITY_TOLERANCE_MWH,
                detail=f"Kleinste Differenz Erzeugung minus Elektrolyse- und Kompressorstrombedarf im Kalender-Monat ({correlation_timezone}).",
            )
        elif scenario == "red_hourly":
            correlation_period_count = len(hourly)
            minimum_margin = float((renewable - rfnbo_use).min())
            _add_check(
                checks,
                scenario=scenario,
                check_id="red_hourly_energy_correlation",
                value=minimum_margin,
                limit=f">= {-ELECTRICITY_TOLERANCE_MWH} MWh",
                passed=minimum_margin >= -ELECTRICITY_TOLERANCE_MWH,
                detail="Kleinste stündliche Differenz Erzeugung minus RFNBO-Strombedarf.",
            )

        temporal = metadata.get("result", {}).get("red_iii_temporal_check", {})
        count_ok = (summary_row.get("red_iii_correlation_periods") == correlation_period_count
                    and type(temporal.get("number_of_correlation_periods")) is int
                    and temporal["number_of_correlation_periods"] == correlation_period_count)
        _add_check(checks, scenario=scenario, check_id="red_temporal_period_count",
                   value=float(correlation_period_count), limit="= Summary- und Metadaten-Zähler", passed=bool(count_ok),
                   detail="S1 zählt unabhängige Ortsmonate einschließlich Jahr, S2 physische Stunden; S0/S3 haben keine Zeitkorrelation.")

        _check_parameter_documentation(checks, scenario, parameters)
        samples.extend(
            _sample_hourly_balances(
                scenario,
                hourly,
                electric_residual,
                hydrogen_residual,
                storage_previous,
            )
        )

    checks_frame = pd.DataFrame(checks)
    samples_frame = pd.DataFrame(samples)
    all_passed = bool(checks_frame["passed"].all())
    output_root.mkdir(parents=True, exist_ok=True)
    _write_csv_atomic(checks_frame, paths["checks"])
    _write_csv_atomic(samples_frame, paths["samples"])
    _write_json_atomic(
        {
            "schema_version": "1.1",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "method": "Unabhängige Ex-post-Nachrechnung aus exportierten CSV- und JSON-Dateien",
            "source_comparison": {
                "path": str(comparison_path),
                "sha256": _sha256(comparison_path),
            },
            "expected_hours_per_scenario": expected_hours,
            "number_of_scenarios": int(len(comparison)),
            "number_of_checks": int(len(checks_frame)),
            "passed_checks": int(checks_frame["passed"].sum()),
            "failed_checks": int((~checks_frame["passed"]).sum()),
            "all_checks_passed": all_passed,
            "tolerances": {
                "electricity_mwh": ELECTRICITY_TOLERANCE_MWH,
                "hydrogen_kg": HYDROGEN_TOLERANCE_KG,
                "annual_cost_eur": COST_TOLERANCE_EUR_PER_YEAR,
                "relative": RELATIVE_TOLERANCE,
            },
            "scope_note": (
                "Die Prüfung validiert numerische Modellbilanzen, Ergebnisexport, "
                "monatliche beziehungsweise stündliche Strommengen-Korrelation und "
                "den implementierten THG-Teil. "
                "Im regulatory_only-Modus bestätigt sie außerdem das explizite "
                "Nichtbewerten betrieblicher Emissionen; fehlende Werte sind kein Nullergebnis. "
                "Externe Nachweise zu Zusätzlichkeit, geografischer Korrelation, "
                "Gebotszone, Vertrag und Allokation bleiben "
                "außerhalb dieser technischen Validierung."
            ),
            "output_files": {
                "checks": CHECKS_FILENAME,
                "samples": SAMPLES_FILENAME,
                "report": REPORT_FILENAME,
            },
        },
        paths["report"],
    )
    return ValidationArtifacts(
        output_root,
        paths["checks"],
        paths["samples"],
        paths["report"],
        all_passed,
    )


def _check_emission_factor_contract(
    checks: list[dict[str, object]],
    scenario: str,
    validated_input: pd.DataFrame,
    hourly: pd.DataFrame,
    metadata: dict[str, object],
    summary_row: pd.Series,
) -> pd.Series:
    """Verify both exported factors against input, without optimizer helpers.

    Historical exports without the optional input column keep their explicit
    legacy interpretation. A new separate pair requires its own sources.
    """
    input_metadata = metadata.get("input", {})
    if not isinstance(input_metadata, dict):
        input_metadata = {}
    mode = input_metadata.get("emission_factor_mode", "legacy_shared_factor")
    separate = "regulatory_grid_emission_factor" in validated_input.columns
    operational_present = "grid_emission_factor" in validated_input.columns
    regulatory_only = not operational_present
    expected_mode = "regulatory_only" if regulatory_only else "explicit_separate_factors" if separate else "legacy_shared_factor"
    expected_reporting = "regulatory_only" if regulatory_only else "complete"
    reporting = input_metadata.get("emissions_reporting", "complete")
    mode_ok = mode == expected_mode and reporting == expected_reporting
    if "emission_factor_mode" in summary_row.index:
        mode_ok = mode_ok and summary_row["emission_factor_mode"] == mode
    result_metadata = metadata.get("result", {})
    result_emissions = result_metadata.get("emissions", {})
    if "emissions_reporting" in summary_row.index:
        mode_ok = mode_ok and summary_row["emissions_reporting"] == expected_reporting
    if "emissions_reporting" in result_metadata:
        mode_ok = mode_ok and result_metadata["emissions_reporting"] == expected_reporting
    if "factor_mode" in result_emissions:
        mode_ok = mode_ok and result_emissions["factor_mode"] == expected_mode
    _add_check(
        checks, scenario=scenario, check_id="emission_factor_mode_consistency",
        value=float(mode_ok), limit="= 1", passed=bool(mode_ok),
        detail=f"Eingabespalten und Metadaten müssen {expected_mode} ausweisen.",
    )
    sources = input_metadata.get("emission_factor_sources")
    sources_ok = True
    if separate:
        sources_ok = isinstance(sources, dict)
        if regulatory_only:
            sources_ok = sources_ok and set(sources or {}) == {"regulatory"}
        for role in (("regulatory",) if regulatory_only else ("operational", "regulatory")):
            source = sources.get(role) if isinstance(sources, dict) else None
            if not isinstance(source, dict):
                sources_ok = False
                continue
            year = source.get("reference_year")
            sources_ok = sources_ok and (
                all(isinstance(source.get(key), str) and bool(source[key].strip())
                    for key in ("source_description", "spatial_scope", "emissions_basis"))
                and isinstance(year, int) and not isinstance(year, bool)
                and 1900 <= year <= 2100 and source.get("unit") == "kg_CO2e/MWh"
            )
        try:
            json.dumps(sources, allow_nan=False)
        except (TypeError, ValueError):
            sources_ok = False
    _add_check(
        checks, scenario=scenario, check_id="emission_factor_sources_documented",
        value=float(sources_ok), limit="= 1", passed=bool(sources_ok),
        detail=("Nur die eigenständige regulatorische Quelle mit Basis, Jahr, Raum und Einheit; keine vorgetäuschte operative Quelle."
                if regulatory_only else "Eigenständige operative und regulatorische Quellen mit Basis, Jahr, Raum und Einheit."
                if separate else "Legacy-Eingabe: gemeinsam verwendeter Faktor, kein separater Quellenbeleg."),
    )
    if regulatory_only:
        absent_ok = (
            "grid_emission_factor_kg_co2e_per_mwh" not in hourly.columns
            and "operational_grid_emissions_kg_co2e" not in hourly.columns
            and all(column in summary_row.index and pd.isna(summary_row[column])
                    for column in ("annual_grid_emissions_kg_co2e", "operational_emission_intensity_kg_co2e_per_kg_h2"))
            and result_emissions.get("operational_grid_emissions_kg_co2e_per_year", "missing") is None
            and result_emissions.get("operational_intensity_kg_co2e_per_kg_h2", "missing") is None
            and summary_row.get("operational_emissions_status") == "not_evaluated"
            and result_metadata.get("operational_emissions_status") == "not_evaluated"
            and result_metadata.get("emissions_reporting") == "regulatory_only"
        )
        _add_check(
            checks, scenario=scenario, check_id="operational_emissions_not_evaluated",
            value=float(absent_ok), limit="= 1", passed=bool(absent_ok),
            detail="Operative Faktoren fehlen ausdrücklich; CSV-Kennzahlen sind leer und JSON-Kennzahlen null, niemals ein Nullfaktor/-ergebnis.",
        )
    else:
        operational = validated_input["grid_emission_factor"]
        _max_abs_check(
            checks, scenario, "operational_factor_matches_input",
            hourly["grid_emission_factor_kg_co2e_per_mwh"] - operational,
            1e-8, "Operativer Exportfaktor stimmt mit der validierten Eingabe überein.",
        )
        status_ok = (summary_row.get("operational_emissions_status", "evaluated") == "evaluated"
                     and result_metadata.get("operational_emissions_status", "evaluated") == "evaluated")
        _add_check(checks, scenario=scenario, check_id="operational_emissions_evaluated_status",
                   value=float(status_ok), limit="= 1", passed=bool(status_ok),
                   detail="Vollständige Emissionseingaben werden als ausgewertet gekennzeichnet.")
    regulatory = (validated_input["regulatory_grid_emission_factor"] if separate
                  else validated_input.get("grid_emission_factor", pd.Series(np.nan, index=validated_input.index)))
    output_regulatory = hourly.get("regulatory_grid_emission_factor_kg_co2e_per_mwh")
    regulatory_present_ok = output_regulatory is not None or not separate
    _add_check(
        checks, scenario=scenario, check_id="regulatory_factor_export_present",
        value=float(regulatory_present_ok), limit="= 1", passed=regulatory_present_ok,
        detail="Getrennte Eingaben benötigen eine getrennte regulatorische Exportspalte.",
    )
    if output_regulatory is None:
        output_regulatory = hourly.get("grid_emission_factor_kg_co2e_per_mwh", pd.Series(np.nan, index=hourly.index))
    _max_abs_check(
        checks, scenario, "regulatory_factor_matches_input",
        output_regulatory - regulatory, 1e-8,
        "Regulatorischer Exportfaktor stimmt mit der eigenen Eingabespalte bzw. dokumentiertem Legacy-Modus überein.",
    )
    factor_series = [regulatory, output_regulatory]
    if operational_present:
        factor_series.extend([validated_input["grid_emission_factor"], hourly["grid_emission_factor_kg_co2e_per_mwh"]])
    factors_finite = all(
        np.isfinite(values.to_numpy(dtype=float)).all() and (values >= 0.0).all()
        for values in factor_series
    )
    _add_check(
        checks, scenario=scenario, check_id="emission_factors_finite_nonnegative",
        value=float(factors_finite), limit="= 1", passed=bool(factors_finite),
        detail="Fehlende oder ungültige Faktoren dürfen nicht als null behandelt werden.",
    )
    if separate:
        receipt_ok = _independent_source_contract_matches(input_metadata, summary_row, validated_input)
        _add_check(
            checks, scenario=scenario, check_id="emission_factor_source_contract_hash",
            value=float(receipt_ok), limit="= 1", passed=bool(receipt_ok),
            detail="Der unveränderte Quellenvertrag ist an die ursprünglichen CSV-Bytes gebunden und stimmt mit den Exportmetadaten überein.",
        )
    return regulatory


def _independent_source_contract_matches(input_metadata: dict, summary_row: pd.Series, validated_input: pd.DataFrame) -> bool:
    """Re-read the source receipt independently, without importing runner code."""
    receipt = input_metadata.get("emission_factor_metadata")
    if not isinstance(receipt, dict):
        return False
    try:
        receipt_path = Path(receipt["source_path"])
        source_csv = Path(input_metadata["source_path"])
        contract = json.loads(receipt_path.read_text(encoding="utf-8"))
        if not isinstance(contract, dict):
            return False
        declared = {key: contract[key] for key in (
            "site_id", "country_code", "calendar_timezone", "historical_year", "price_year",
            "annualization_basis", "annual_hours", "expected_hours", "demand_profile",
        ) if key in contract}
        if declared != input_metadata.get("declared_input_context", {}):
            return False
        if any(input_metadata.get(key) != value for key, value in declared.items()):
            return False
        site = input_metadata.get("eu_site_configuration")
        if isinstance(site, dict):
            expected = {"site_id": site.get("site_id"), "country_code": site.get("country_code"),
                        "calendar_timezone": site.get("calendar_timezone"), "historical_year": site.get("historical_year"),
                        "price_year": site.get("wacc", {}).get("cost_price_year"),
                        "annualization_basis":site.get("annualization",{}).get("basis"),
                        "annual_hours":site.get("annualization",{}).get("annual_hours"),
                        "expected_hours":site.get("time_contract",{}).get("expected_hours")}
            if any(value != expected.get(key) for key, value in declared.items() if key != "demand_profile"):
                return False
            if "demand_profile" in declared and (not isinstance(declared["demand_profile"],dict)
                    or declared["demand_profile"].get("annual_kg") != site.get("annualization",{}).get("annual_h2_delivery_kg")):
                return False
        raw_input = pd.read_csv(source_csv)
        if len(raw_input) != len(validated_input):
            return False
        if contract.get("emission_factor_mode") == "regulatory_only" and "grid_emission_factor" in raw_input.columns:
            return False
        required_numeric = ["pv_capacity_factor", "wind_capacity_factor", "electricity_price", "h2_demand", "regulatory_grid_emission_factor"]
        if "grid_emission_factor" in validated_input.columns:
            required_numeric.append("grid_emission_factor")
        for column in required_numeric:
            if column not in raw_input.columns or column not in validated_input.columns:
                return False
            left = pd.to_numeric(raw_input[column], errors="raise").to_numpy(dtype=float)
            right = pd.to_numeric(validated_input[column], errors="raise").to_numpy(dtype=float)
            if not np.isfinite(left).all() or not np.isfinite(right).all() or not np.allclose(left, right, rtol=1e-12, atol=1e-12):
                return False
        raw_time = pd.to_datetime(raw_input["timestamp"], errors="raise", utc=True)
        exported_time = pd.to_datetime(validated_input["timestamp"], errors="raise", utc=True)
        if not raw_time.equals(exported_time):
            return False
        return (
            _sha256(receipt_path) == receipt.get("sha256")
            and _sha256(source_csv) == input_metadata.get("sha256") == summary_row["input_sha256"]
            and contract.get("schema_version") == "1.0"
            and contract.get("input_sha256") == input_metadata.get("sha256")
            and contract.get("emission_factor_mode") == input_metadata.get("emission_factor_mode")
            and contract.get("emission_factor_sources") == input_metadata.get("emission_factor_sources")
        )
    except (OSError, KeyError, TypeError, ValueError):
        return False


def _check_time_axis(
    checks: list[dict[str, object]],
    *,
    scenario: str,
    hourly: pd.DataFrame,
    validated_input: pd.DataFrame,
    expected_hours: int,
) -> None:
    row_count_ok = len(hourly) == expected_hours == len(validated_input)
    _add_check(
        checks,
        scenario=scenario,
        check_id="hour_count",
        value=float(len(hourly)),
        limit=f"= {expected_hours}",
        passed=row_count_ok,
        detail="Stundenbetrieb und validierte Eingabe müssen gleich lang sein.",
    )
    timestamps = pd.to_datetime(hourly["timestamp"], utc=True, errors="coerce")
    valid_timestamps = not timestamps.isna().any()
    hourly_steps = (
        valid_timestamps
        and timestamps.is_monotonic_increasing
        and not timestamps.duplicated().any()
        and (timestamps.diff().dropna() == pd.Timedelta(hours=1)).all()
    )
    _add_check(
        checks,
        scenario=scenario,
        check_id="continuous_utc_hourly_axis",
        value=float(bool(hourly_steps)),
        limit="= 1",
        passed=bool(hourly_steps),
        detail="Eindeutige, sortierte und lückenlos stündliche UTC-Zeitachse.",
    )


def _check_sensitivity_contract(
    checks: list[dict[str, object]], scenario: str, data: pd.DataFrame,
    metadata: dict, parameters: dict, validated_input_path: Path,
) -> None:
    """Independently reconstruct OAT changes and parent data; no optimizer helper is reused."""
    provenance = metadata.get("input", {}).get("sensitivity_provenance")
    override = metadata.get("sensitivity_override")
    if provenance is None and override is None:
        # A derived source contract still requires the exported sensitivity
        # fields; deleting both fields must not disable this independent audit.
        try:
            receipt = metadata["input"]["emission_factor_metadata"]
            contract = json.loads(Path(receipt["source_path"]).read_text(encoding="utf-8"))
            if not any(key in contract for key in ("parent_input", "case_transformation", "baseline_configuration")):
                return
        except (KeyError, TypeError, ValueError, OSError):
            return  # The existing source-contract checks handle missing sources.
    input_ok, config_ok = True, True
    try:
        parent = provenance["parent_input"]
        record = provenance["case_transformation"]
        snapshot_receipt = provenance["baseline_configuration"]
        source_receipt = metadata["input"]["emission_factor_metadata"]
        child_contract = json.loads(Path(source_receipt["source_path"]).read_text(encoding="utf-8"))
        input_ok = all(child_contract.get(key) == provenance[key]
                       for key in ("parent_input", "case_transformation", "baseline_configuration"))
        input_ok = input_ok and _sha256(Path(parent["path"])) == parent["sha256"] and _sha256(Path(parent["metadata_path"])) == parent["metadata_sha256"]
        source = json.loads(Path(parent["metadata_path"]).read_text(encoding="utf-8"))
        input_ok = input_ok and source.get("input_sha256") == parent["sha256"] and source.get("emission_factor_sources") == metadata["input"].get("emission_factor_sources")
        input_ok = input_ok and source.get("emission_factor_mode") == metadata["input"].get("emission_factor_mode")
        parent_context = {key: source[key] for key in (
            "site_id", "country_code", "calendar_timezone", "historical_year", "price_year",
            "annualization_basis", "annual_hours", "expected_hours", "demand_profile",
        ) if key in source}
        if record.get("parameter") == "h2_demand_multiplier" and "demand_profile" in parent_context:
            profile = dict(parent_context["demand_profile"])
            for quantity in ("annual_kg", "kg_per_active_hour"):
                if quantity in profile:
                    original_quantity = profile[quantity]
                    input_ok = input_ok and not isinstance(original_quantity, bool) and np.isfinite(float(original_quantity)) and original_quantity > 0
                    profile[quantity] = original_quantity * record["value"]
            input_ok = input_ok and "annual_kg" in profile
            parent_context["demand_profile"] = profile
        input_ok = input_ok and parent_context == metadata["input"].get("declared_input_context", {})
        original = pd.read_csv(parent["path"], dtype=str, keep_default_na=False)
        data = pd.read_csv(validated_input_path, dtype=str, keep_default_na=False)
        input_ok = input_ok and original.columns.tolist() == data.columns.tolist() and len(original) == len(data)
        intervention = record["parameter"]
        for column in original.columns:
            if column == "timestamp":
                input_ok = input_ok and pd.to_datetime(original[column], utc=True).equals(pd.to_datetime(data[column], utc=True))
            elif column in ("pv_capacity_factor", "wind_capacity_factor", "electricity_price",
                            "grid_emission_factor", "regulatory_grid_emission_factor", "h2_demand"):
                expected = pd.to_numeric(original[column])
                if column == "electricity_price" and intervention == "electricity_price_offset_eur_per_mwh": expected = expected + record["value"]
                elif column == "electricity_price" and intervention == "electricity_price_eur_per_mwh": expected = pd.Series(record["value"], index=expected.index)
                elif column == "h2_demand" and intervention == "h2_demand_multiplier": expected = expected * record["value"]
                same = np.allclose(pd.to_numeric(data[column]), expected, rtol=1e-12, atol=1e-12, equal_nan=True)
                input_ok = input_ok and same
            else:
                input_ok = input_ok and data[column].equals(original[column])
        config_ok = _sha256(Path(snapshot_receipt["path"])) == snapshot_receipt["sha256"]
        baseline = json.loads(Path(snapshot_receipt["path"]).read_text(encoding="utf-8"))
        base_parameters = baseline["model_parameters"]
        if "accepted_baseline_metadata" in baseline:
            receipt = baseline["accepted_baseline_metadata"]
            config_ok = config_ok and _sha256(Path(receipt["path"])) == receipt["sha256"]
            accepted = json.loads(Path(receipt["path"]).read_text(encoding="utf-8"))
            actual = {key: {name: item.get(name) for name in ("value", "unit", "reference_year")}
                      for key, item in accepted["model_parameters"].items()}
            config_ok = config_ok and actual == base_parameters and accepted["input"]["sha256"] == parent["sha256"]
        expected_values = {key: item["value"] for key, item in base_parameters.items()}
        value = record.get("value")
        targets = {
            "electrolyzer_capex_eur_per_kw": "technologies.electrolyzer.capex_eur_per_kw",
            "electrolyzer_specific_electricity_kwh_per_kg_h2": "technologies.electrolyzer.specific_electricity_kwh_per_kg_h2",
            "pv_capex_eur_per_kw": "technologies.pv.capex_eur_per_kw", "wind_capex_eur_per_kw": "technologies.wind_onshore.capex_eur_per_kw",
            "h2_storage_capex_eur_per_kg_h2": "technologies.h2_storage.capex_eur_per_kg_h2",
        }
        wacc_keys = [f"technologies.{name}.real_wacc_fraction" for name in ("pv", "wind_onshore", "electrolyzer", "compressor", "h2_storage")]
        operations = {
            "baseline": "unchanged", "real_wacc_shift_fraction": "add_to_all_five_real_wacc_rates",
            "real_wacc_multiplier": "multiply_all_five_real_wacc_rates",
            "uniform_real_wacc_fraction": "replace_baseline_scalar",
            "electricity_price_offset_eur_per_mwh": "add_to_hourly_price_profile",
            "electricity_price_eur_per_mwh": "replace_hourly_prices_with_constant",
            "electrolyzer_capex_factor": "multiply_baseline_scalar",
            "electrolyzer_specific_electricity_factor": "multiply_baseline_scalar",
            "h2_demand_multiplier": "multiply_hourly_h2_demand_preserve_profile",
            **{key: "replace_baseline_scalar" for key in targets},
        }
        config_ok = config_ok and record.get("operation") == operations.get(intervention)
        if intervention != "baseline":
            config_ok = config_ok and not isinstance(value, bool) and np.isfinite(float(value))
            config_ok = config_ok and isinstance(record.get("source"), str) and bool(record["source"].strip())
            config_ok = config_ok and isinstance(record.get("note"), str)
            if intervention not in ("real_wacc_shift_fraction", "electricity_price_offset_eur_per_mwh"):
                config_ok = config_ok and value > 0
        if intervention == "real_wacc_shift_fraction":
            for key in wacc_keys: expected_values[key] += value
        elif intervention == "real_wacc_multiplier":
            for key in wacc_keys: expected_values[key] *= value
        elif intervention == "uniform_real_wacc_fraction":
            for key in wacc_keys: expected_values[key] = value
        elif intervention in ("electrolyzer_capex_factor", "electrolyzer_specific_electricity_factor"):
            key = targets["electrolyzer_capex_eur_per_kw" if intervention == "electrolyzer_capex_factor" else "electrolyzer_specific_electricity_kwh_per_kg_h2"]
            expected_values[key] *= value
        elif intervention in targets:
            expected_values[targets[intervention]] = value
        elif intervention == "h2_demand_multiplier":
            expected_values["study.h2_demand_kg_per_day"] *= value
        elif intervention not in ("baseline", "electricity_price_offset_eur_per_mwh", "electricity_price_eur_per_mwh"):
            config_ok = False
        config_ok = config_ok and all(0 <= expected_values[key] < 1 for key in wacc_keys)
        changed = {key: {"base_value": base_parameters[key]["value"], "applied_value": expected_values[key], "unit": base_parameters[key]["unit"]}
                   for key in expected_values if base_parameters[key]["value"] != expected_values[key]}
        config_ok = config_ok and changed == record.get("changed_scalar_parameters") and set(parameters) == set(base_parameters)
        for key, expected in expected_values.items():
            actual = parameters.get(key, {})
            config_ok = config_ok and np.isfinite(float(actual.get("value", float("nan")))) and abs(float(actual["value"])-expected) <= 1e-10
            config_ok = config_ok and actual.get("unit") == base_parameters[key]["unit"]
            expected_year = None if intervention == "uniform_real_wacc_fraction" and key in wacc_keys else base_parameters[key]["reference_year"]
            config_ok = config_ok and actual.get("reference_year") == expected_year
        expected_override = {key: value for key, value in record.items() if key != "case_id"}
        config_ok = config_ok and (override is None if intervention == "baseline" else override == expected_override)
        config_ok = config_ok and baseline["model_calendar"] == metadata.get("model_calendar")
        site = metadata["input"].get("eu_site_configuration")
        if isinstance(site, dict):
            config_ok = config_ok and baseline.get("eu_design_sha256") == site.get("design_sha256")
            if override is not None:
                config_ok = config_ok and site.get("sensitivity_override") == override
                if intervention == "h2_demand_multiplier":
                    annualization = site.get("annualization", {})
                    baseline_target = base_parameters["study.h2_demand_kg_per_day"]["value"] * base_parameters["study.annual_hours"]["value"] / 24
                    config_ok = config_ok and np.isclose(float(annualization.get("baseline_annual_h2_delivery_kg", float("nan"))), baseline_target, rtol=1e-12, atol=1e-9)
                    config_ok = config_ok and np.isclose(float(annualization.get("annual_h2_delivery_kg", float("nan"))), baseline_target * value, rtol=1e-12, atol=1e-9)
                    config_ok = config_ok and annualization.get("demand_multiplier") == value
                    config_ok = config_ok and annualization.get("effective_delivery_is_sensitivity_assumption") is True
                expected_sensitivity_rates = intervention in ("real_wacc_shift_fraction", "real_wacc_multiplier", "uniform_real_wacc_fraction")
                config_ok = config_ok and site["wacc"].get("effective_rates_are_sensitivity_assumptions") is expected_sensitivity_rates
                for name in ("pv", "wind_onshore", "electrolyzer", "compressor", "h2_storage"):
                    key = f"technologies.{name}.real_wacc_fraction"
                    config_ok = config_ok and site["wacc"]["baseline_real_wacc_fraction_per_year"].get(name) == base_parameters[key]["value"]
                    config_ok = config_ok and site["wacc"]["real_wacc_fraction_per_year"].get(name) == expected_values[key]
    except (KeyError, TypeError, ValueError, OSError, AttributeError):
        input_ok, config_ok = False, False
    _add_check(checks, scenario=scenario, check_id="sensitivity_parent_input_contract", value=float(bool(input_ok)),
               limit="= 1", passed=bool(input_ok), detail="Originale CSV/Sidecar-Hashes und unveränderte Stundenwerte sind unabhängig geprüft; Preisoffset erhält Preisverlauf, Nachfragemultiplikator erhält Profilform und Kalender.")
    _add_check(checks, scenario=scenario, check_id="sensitivity_one_factor_configuration", value=float(bool(config_ok)),
               limit="= 1", passed=bool(config_ok), detail="Genau die deklarierte Intervention folgt der SHA-gebundenen Basiskonfiguration; übrige Werte, Kalender, Einheiten und Bezugsjahre bleiben erhalten.")


def _check_temporal_calendar_contract(
    checks: list[dict[str, object]], scenario: str,
    metadata: dict[str, object], batch_metadata: object,
) -> str:
    """Check the exported calendar independently, retaining recorded UTC archives.

    For EU runs the original SHA-bound design supplies the timezone. Neither
    the optimizer's grouping helper nor a mutable output label is used to
    construct the validator's monthly groups.
    """
    schema = str(metadata.get("schema_version", "1.0"))
    legacy = schema in {"1.0", "1.1", "1.2", "1.3", "1.4", "1.5", "1.6"}
    scope = metadata.get("calendar_scope", {})
    model_calendar = metadata.get("model_calendar")
    explicit = isinstance(model_calendar, dict)
    configured = model_calendar.get("temporal_correlation_timezone") if explicit else "UTC"
    expected_timezone = configured
    source_ok = True
    site = metadata.get("input", {}).get("eu_site_configuration")
    if isinstance(site, dict) and (explicit or not legacy):
        try:
            raw = Path(site["design_path"]).read_bytes()
            design = json.loads(raw.decode("utf-8-sig"))
            rows = [row for row in design["sites"] if row.get("site_id") == site.get("site_id")]
            source_ok = len(rows) == 1
            if source_ok:
                expected_timezone = rows[0]["calendar_timezone"]
                source_ok = (hashlib.sha256(raw).hexdigest() == site.get("design_sha256")
                    and design["time"].get("monthly_grouping") == "site local timezone"
                    and site.get("calendar_timezone") == expected_timezone
                    and site.get("time_contract", {}).get("monthly_grouping") == "site local timezone"
                    and site.get("temporal_correlation") == {
                        "monthly_basis": "site_local_timezone", "timezone": expected_timezone,
                        "hourly_basis": "physical_utc_hour"})
                declared = metadata.get("input", {}).get("declared_input_context", {})
                if "calendar_timezone" in declared:
                    source_ok = source_ok and declared["calendar_timezone"] == expected_timezone
        except (KeyError, TypeError, ValueError, OSError):
            source_ok = False
    valid_timezone = True
    try:
        if not isinstance(expected_timezone, str):
            raise ValueError("Missing calendar timezone")
        ZoneInfo(expected_timezone)
    except (ZoneInfoNotFoundError, TypeError, ValueError):
        valid_timezone = False
        expected_timezone = "UTC"  # Failed check remains explicit; finish other independent checks.
    monthly_basis = "utc_calendar_month" if expected_timezone == "UTC" else "site_local_calendar_month"
    expected_applied = isinstance(site, dict) and expected_timezone != "UTC"
    temporal = metadata.get("result", {}).get("red_iii_temporal_check", {})
    mode = {"red_monthly": "monthly", "red_hourly": "hourly"}.get(scenario)
    ok = valid_timezone and (explicit or legacy) and configured == expected_timezone
    if explicit or not legacy:
        ok = ok and isinstance(scope, dict) and all((
            scope.get("monthly_correlation_calendar") == expected_timezone,
            scope.get("monthly_grouping_basis") == monthly_basis,
            scope.get("hourly_grouping_basis") == "physical_utc_hour",
            scope.get("site_timezone_applied_to_monthly_correlation") is expected_applied,
            scope.get("requested_site_timezone") == (site.get("calendar_timezone") if isinstance(site, dict) else None),
            temporal.get("calendar_timezone") == expected_timezone,
            temporal.get("mode") == mode,
            temporal.get("grouping_basis") == ("physical_utc_hour" if mode == "hourly" else "calendar_month" if mode == "monthly" else None),
        ))
    elif isinstance(scope, dict) and "monthly_correlation_calendar" in scope:
        ok = ok and scope["monthly_correlation_calendar"] == "UTC" and scope.get("site_timezone_applied_to_monthly_correlation") is False
    _add_check(checks, scenario=scenario, check_id="temporal_calendar_configuration",
               value=float(bool(ok)), limit="= 1", passed=bool(ok),
               detail="Explizite Monatszeitzone, Ortsmonatsbasis und physische UTC-Stundenbasis stimmen mit der Modellkonfiguration überein; ältere Archive behalten UTC.")
    _add_check(checks, scenario=scenario, check_id="temporal_calendar_source_contract",
               value=float(bool(source_ok)), limit="= 1", passed=bool(source_ok),
               detail="EU-Monatskalender folgt der unveränderten SHA-gebundenen Design-Datei und dem Eingabequellenvertrag.")
    if isinstance(batch_metadata, dict) and ("temporal_calendar" in batch_metadata
            or str(batch_metadata.get("schema_version")) not in {"1.0", "1.1", "1.2", "1.3"}):
        batch_ok = batch_metadata.get("temporal_calendar") == {
            "timezone": expected_timezone, "monthly_grouping_basis": monthly_basis,
            "hourly_grouping_basis": "physical_utc_hour"}
        _add_check(checks, scenario=scenario, check_id="temporal_calendar_batch_metadata",
                   value=float(bool(batch_ok)), limit="= 1", passed=bool(batch_ok),
                   detail="Der Stapellauf dokumentiert denselben unabhängig geprüften Monatskalender.")
    return expected_timezone


def _check_annualization_contract(
    checks: list[dict[str, object]], scenario: str,
    hourly: pd.DataFrame, validated_input: pd.DataFrame,
    metadata: dict[str, object], summary: pd.Series, parameters: object,
) -> float:
    """Derive the factor independently; never trust the exported factor alone."""
    scope = metadata.get("calendar_scope", {})
    contract = scope.get("annualization") if isinstance(scope, dict) else None
    explicit = isinstance(contract, dict)
    schema = str(metadata.get("schema_version", "1.0"))
    requires_contract = schema not in {"1.0", "1.1", "1.2", "1.3", "1.4", "1.5"}
    basis = contract.get("basis") if explicit else "legacy_365_day_reference"
    canonical_hours = 8760.0
    ok = explicit or not requires_contract
    def same_number(value: object, expected: float) -> bool:
        try:
            return not isinstance(value, bool) and np.isfinite(float(value)) and abs(float(value)-expected) <= 1e-9
        except (TypeError, ValueError):
            return False
    if basis == "historical_calendar_year":
        year = contract.get("reference_year")
        if type(year) is int and 1900 <= year <= 2199:
            canonical_hours = float(24*(366 if calendar.isleap(year) else 365))
            ok = ok and same_number(_parameter_value(parameters, "study.profile_calendar_year"), year)
        else:
            ok = False
    elif basis == "legacy_365_day_reference":
        if explicit:
            ok = ok and contract.get("reference_year") is None
    else:
        ok = False
    step = _parameter_value(parameters, "study.time_step_hours")
    modeled_hours = float(len(hourly)) * step
    ok = ok and step == 1.0 and 0 < modeled_hours <= canonical_hours and len(hourly) == len(validated_input)
    expected_factor = canonical_hours / modeled_hours if modeled_hours > 0 else float("nan")
    if explicit:
        ok = ok and all((
            same_number(contract.get("annual_hours"), canonical_hours),
            same_number(contract.get("modeled_hours"), modeled_hours),
            same_number(contract.get("time_step_hours"), step),
            same_number(_parameter_value(parameters, "study.annual_hours"), canonical_hours),
            same_number(summary.get("annual_hours"), canonical_hours),
            same_number(summary.get("modeled_hours"), modeled_hours),
            summary.get("annualization_basis") == basis,
            contract.get("period_interpretation") == (
                "complete_historical_calendar_year" if basis == "historical_calendar_year" and modeled_hours == canonical_hours
                else "cyclic_period_reference_annualization"),
        ))
    ok = ok and same_number(_parameter_value(parameters, "study.number_of_time_steps")*step, canonical_hours)
    site = metadata.get("input", {}).get("eu_site_configuration")
    source_ok = True
    if isinstance(site, dict) and not explicit and not requires_contract:
        # Old archives never exported the new annualization source contract.
        # Retain their explicit 365-day convention without demanding that the
        # formerly active design path still points to the archived file today.
        source_ok = (site.get("historical_year") == 2025
                     and site.get("time_contract",{}).get("expected_hours") == 8760)
    elif isinstance(site, dict):
        try:
            source = Path(site["design_path"])
            raw = source.read_bytes()
            design = json.loads(raw.decode("utf-8-sig"))
            time = design["time"]
            year = time["historical_year"]
            hours = 24*(366 if calendar.isleap(year) else 365)
            local = pd.to_datetime(validated_input["timestamp"], utc=True).dt.tz_convert(site["calendar_timezone"])
            source_ok = (type(year) is int and hashlib.sha256(raw).hexdigest() == site["design_sha256"]
                         and site.get("historical_year") == year and time.get("expected_hours") == hours
                         and canonical_hours == hours and set(local.dt.year) == {year})
            original_target = float(design["hydrogen_demand"]["annual_kg"])
            target = original_target
            override = metadata.get("sensitivity_override")
            if isinstance(override, dict) and override.get("parameter") == "h2_demand_multiplier":
                multiplier = override.get("value")
                demand_ok = (not isinstance(multiplier, bool) and isinstance(multiplier, (int, float))
                             and np.isfinite(multiplier) and multiplier > 0
                             and override.get("operation") == "multiply_hourly_h2_demand_preserve_profile"
                             and site.get("sensitivity_override") == override)
                target = original_target * multiplier if demand_ok else float("nan")
                annualization = site.get("annualization", {})
                demand_ok = demand_ok and all((
                    same_number(annualization.get("baseline_annual_h2_delivery_kg"), original_target),
                    same_number(annualization.get("annual_h2_delivery_kg"), target),
                    same_number(annualization.get("demand_multiplier"), multiplier),
                    annualization.get("effective_delivery_is_sensitivity_assumption") is True,
                    same_number(_parameter_value(parameters, "study.h2_demand_kg_per_day"), target / (hours / 24)),
                ))
                source_ok = source_ok and demand_ok
            if modeled_hours == hours:
                source_ok = source_ok and abs(float(validated_input["h2_demand"].sum())-target) <= HYDROGEN_TOLERANCE_KG
                source_ok = source_ok and (pd.to_datetime(validated_input["timestamp"], utc=True).iloc[0] == pd.Timestamp(time["start_utc_inclusive"]))
        except (KeyError, TypeError, ValueError, OSError):
            source_ok = False
    _add_check(checks, scenario=scenario, check_id="annualization_basis_consistency",
               value=float(bool(ok)), limit="= 1", passed=bool(ok),
               detail="Jahresstundenbasis folgt unabhängig aus Legacy-Konvention oder Gregorianischem Kalender und Modellparametern.")
    _add_check(checks, scenario=scenario, check_id="annualization_source_contract",
               value=float(bool(source_ok)), limit="= 1", passed=bool(source_ok),
               detail="EU-Kalender und Volljahreslieferung folgen der SHA-gebundenen ursprünglichen Design-Datei; eine dokumentierte Nachfragesensitivität skaliert ausschließlich deren Jahresziel.")
    factor_ok = same_number(summary.get("annualization_factor"), expected_factor)
    if explicit:
        factor_ok = factor_ok and same_number(contract.get("factor"), expected_factor)
    _add_check(checks, scenario=scenario, check_id="annualization_factor_independent",
               value=abs(float(summary["annualization_factor"])-expected_factor), limit="<= 1e-9", passed=bool(factor_ok),
               detail="Annualisierung = unabhängig ermittelte Jahresstunden / tatsächliche modellierte Stunden.")
    return expected_factor


def _check_parameter_documentation(
    checks: list[dict[str, object]],
    scenario: str,
    parameters: object,
) -> None:
    if not isinstance(parameters, dict) or not parameters:
        _add_check(
            checks,
            scenario=scenario,
            check_id="parameter_documentation",
            value=0.0,
            limit="= 1",
            passed=False,
            detail="model_parameters fehlt oder ist leer.",
        )
        return
    complete = all(
        isinstance(entry, dict)
        and str(entry.get("unit", "")).strip()
        and str(entry.get("source", "")).strip()
        for entry in parameters.values()
    )
    _add_check(
        checks,
        scenario=scenario,
        check_id="parameter_documentation",
        value=float(bool(complete)),
        limit="= 1",
        passed=bool(complete),
        detail=f"Einheit und Quelle für {len(parameters)} exportierte Modellparameter.",
    )


def _parameter_value(parameters: object, name: str) -> float:
    if not isinstance(parameters, dict) or name not in parameters:
        raise ValueError(f"Modellparameter fehlt in run_metadata.json: {name}")
    entry = parameters[name]
    if not isinstance(entry, dict) or "value" not in entry:
        raise ValueError(f"Modellparameter ist unvollständig: {name}")
    return float(entry["value"])


def _max_abs_check(
    checks: list[dict[str, object]],
    scenario: str,
    check_id: str,
    residual: pd.Series,
    tolerance: float,
    detail: str,
) -> None:
    value = float(np.max(np.abs(pd.to_numeric(residual).to_numpy(dtype=float))))
    _add_check(
        checks,
        scenario=scenario,
        check_id=check_id,
        value=value,
        limit=f"<= {tolerance}",
        passed=value <= tolerance,
        detail=detail,
    )


def _max_upper_check(
    checks: list[dict[str, object]],
    scenario: str,
    check_id: str,
    excess: pd.Series,
    tolerance: float,
    detail: str,
) -> None:
    value = float(pd.to_numeric(excess).max())
    _add_check(
        checks,
        scenario=scenario,
        check_id=check_id,
        value=value,
        limit=f"<= {tolerance}",
        passed=value <= tolerance,
        detail=detail,
    )


def _sample_hourly_balances(
    scenario: str,
    hourly: pd.DataFrame,
    electric_residual: pd.Series,
    hydrogen_residual: pd.Series,
    storage_previous: pd.Series,
) -> list[dict[str, object]]:
    renewable_self = hourly["pv_self_consumption_mwh"] + hourly["wind_self_consumption_mwh"]
    candidate_indices = [
        0,
        int(hourly["grid_import_mwh"].astype(float).idxmax()),
        int(renewable_self.astype(float).idxmax()),
        int(hourly["h2_storage_level_kg"].astype(float).idxmax()),
    ]
    selected_indices: list[int] = []
    for index in candidate_indices:
        if index not in selected_indices:
            selected_indices.append(index)
        if len(selected_indices) == 3:
            break
    for index in np.linspace(0, len(hourly) - 1, 3, dtype=int):
        if len(selected_indices) == 3:
            break
        if int(index) not in selected_indices:
            selected_indices.append(int(index))

    rows: list[dict[str, object]] = []
    for index in selected_indices:
        row = hourly.iloc[index]
        rows.append(
            {
                "scenario": scenario,
                "timestamp": row["timestamp"],
                "pv_self_consumption_mwh": float(row["pv_self_consumption_mwh"]),
                "wind_self_consumption_mwh": float(row["wind_self_consumption_mwh"]),
                "grid_import_mwh": float(row["grid_import_mwh"]),
                "electrolyzer_electricity_mwh": float(row["electrolyzer_electricity_mwh"]),
                "compressor_electricity_mwh": float(row["compressor_electricity_mwh"]),
                "electricity_balance_residual_mwh": float(electric_residual.iloc[index]),
                "previous_storage_kg": float(storage_previous.iloc[index]),
                "h2_after_compression_kg": float(row["h2_after_compression_kg"]),
                "h2_demand_kg": float(row["h2_demand_kg"]),
                "storage_level_kg": float(row["h2_storage_level_kg"]),
                "hydrogen_balance_residual_kg": float(hydrogen_residual.iloc[index]),
            }
        )
    return rows


def _add_check(
    checks: list[dict[str, object]],
    *,
    scenario: str,
    check_id: str,
    value: float,
    limit: str,
    passed: bool,
    detail: str,
) -> None:
    checks.append(
        {
            "scenario": scenario,
            "check_id": check_id,
            "value": value,
            "limit": limit,
            "passed": bool(passed),
            "detail": detail,
        }
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for block in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_csv_atomic(data: pd.DataFrame, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".tmp")
    try:
        data.to_csv(temporary, index=False, encoding="utf-8")
        os.replace(temporary, destination)
    finally:
        if temporary.exists():
            temporary.unlink()


def _write_json_atomic(data: dict[str, object], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".tmp")
    try:
        temporary.write_text(
            json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, destination)
    finally:
        if temporary.exists():
            temporary.unlink()


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prüft gespeicherte S0-, S1- und S2-Ergebnisse unabhängig nach."
    )
    parser.add_argument("--results-dir", required=True, type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--expected-hours", type=int, default=8_760)
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_argument_parser()
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not arguments:
        parser.print_help()
        print("\nEs wurde noch keine Ergebnisvalidierung gestartet.")
        return 0
    args = parser.parse_args(arguments)
    try:
        artifacts = validate_h2_results(
            args.results_dir,
            output_directory=args.output_dir,
            expected_hours=args.expected_hours,
            overwrite=args.overwrite,
        )
    except (FileNotFoundError, FileExistsError, OSError, TypeError, ValueError) as exc:
        print(f"Fehler: {exc}", file=sys.stderr)
        return 1
    checks = pd.read_csv(artifacts.checks_path)
    print(
        f"Validierung: {int(checks['passed'].sum())} von {len(checks)} Prüfungen bestanden."
    )
    print(f"Prüftabelle: {artifacts.checks_path}")
    print(f"Stichproben: {artifacts.samples_path}")
    print(f"Bericht: {artifacts.report_path}")
    return 0 if artifacts.all_checks_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "ValidationArtifacts",
    "build_argument_parser",
    "main",
    "validate_h2_results",
]
