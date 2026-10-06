r"""Kontrollierter Einstiegspunkt für einen einzelnen H2-Modelllauf.

Beispiel im Windows-Terminal::

    python run_single_site_h2.py --input input.csv --scenario reference --output-dir results\testlauf

Der Runner liest ausschließlich die ausdrücklich angegebene CSV-Datei. Er
erzeugt eine validierte Eingabekopie, eine einzeilige Zusammenfassung, den
stündlichen Betrieb und JSON-Metadaten für die Nachvollziehbarkeit.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Final, Sequence

import gurobipy as gp
import pandas as pd
import scipy

from config_h2 import DEFAULT_CONFIG, ModelConfig, Scenario, iter_scalar_parameters
from eu_site_configuration import EU_SITE_IDS, load_eu_site_configuration
from h2_input_data import (
    LEGACY_EMISSION_MODE,
    COMPLETE_EMISSIONS_REPORTING,
    REGULATORY_ONLY_EMISSION_MODE,
    SEPARATE_EMISSION_MODE,
    HourlyInputError,
    validate_hourly_input,
)
from opt_hydrogen_functions import (
    HydrogenOptimizationError,
    HydrogenOptimizationResult,
    optimize_hydrogen_system,
)


SUMMARY_FILENAME: Final[str] = "summary.csv"
HOURLY_OPERATION_FILENAME: Final[str] = "hourly_operation.csv"
VALIDATED_INPUT_FILENAME: Final[str] = "validated_input.csv"
RUN_METADATA_FILENAME: Final[str] = "run_metadata.json"
OUTPUT_FILENAMES: Final[tuple[str, ...]] = (
    SUMMARY_FILENAME,
    HOURLY_OPERATION_FILENAME,
    VALIDATED_INPUT_FILENAME,
    RUN_METADATA_FILENAME,
)
SUPPORTED_CLI_SCENARIOS: Final[tuple[str, ...]] = (
    Scenario.REFERENCE.value,
    Scenario.RED_MONTHLY.value,
    Scenario.RED_HOURLY.value,
    Scenario.OFF_GRID.value,
)


class H2RunError(RuntimeError):
    """Fehler beim Laden oder Schreiben eines vollständigen Modelllaufs."""


@dataclass(frozen=True, slots=True)
class RunArtifacts:
    """Pfade und Ergebnis des erfolgreich abgeschlossenen Modelllaufs."""

    output_directory: Path
    summary_path: Path
    hourly_operation_path: Path
    validated_input_path: Path
    metadata_path: Path
    result: HydrogenOptimizationResult


def run_single_site_h2(
    input_path: str | Path,
    output_directory: str | Path,
    *,
    scenario: Scenario | str = Scenario.REFERENCE,
    config: ModelConfig = DEFAULT_CONFIG,
    overwrite: bool = False,
    solver_output: bool = False,
    solver_backend: str = "auto",
    emission_factor_metadata_path: str | Path | None = None,
    require_separate_emission_factors: bool = False,
    emissions_reporting: str = COMPLETE_EMISSIONS_REPORTING,
    eu_site: str | None = None,
    eu_design_path: str | Path | None = None,
    sensitivity_override: dict | None = None,
) -> RunArtifacts:
    """Führe einen Modelllauf aus und schreibe seine vier Ergebnisdateien."""

    if not isinstance(overwrite, bool):
        raise TypeError("overwrite muss ein boolescher Wert sein.")
    selected_scenario = _coerce_scenario(scenario)
    selected_eu_site = None
    if eu_site is not None:
        selected_eu_site = load_eu_site_configuration(eu_site, base_config=config, design_path=eu_design_path)
        config = selected_eu_site.config
    elif eu_design_path is not None:
        raise H2RunError("eu_design_path benötigt eine explizite eu_site-Auswahl.")
    baseline_config = config
    override_record = None
    if sensitivity_override is not None:
        from h2_sensitivity_overrides import apply_sensitivity_override
        config, override_record = apply_sensitivity_override(config, sensitivity_override)
        if selected_eu_site is not None:
            from copy import deepcopy
            site_metadata = deepcopy(selected_eu_site.metadata)
            wacc = site_metadata["wacc"]
            wacc["baseline_real_wacc_fraction_per_year"] = dict(wacc["real_wacc_fraction_per_year"])
            wacc["real_wacc_fraction_per_year"] = {name: getattr(config.technologies, name).real_wacc_fraction.value
                for name in ("pv", "wind_onshore", "electrolyzer", "compressor", "h2_storage")}
            wacc["effective_rates_are_sensitivity_assumptions"] = override_record["parameter"] in ("real_wacc_shift_fraction", "real_wacc_multiplier", "uniform_real_wacc_fraction")
            site_metadata["sensitivity_override"] = override_record
            if override_record["parameter"] == "h2_demand_multiplier":
                annualization = site_metadata["annualization"]
                original_target = annualization["annual_h2_delivery_kg"]
                annualization.update(baseline_annual_h2_delivery_kg=original_target,
                    annual_h2_delivery_kg=original_target * override_record["value"],
                    demand_multiplier=override_record["value"],
                    effective_delivery_is_sensitivity_assumption=True)
            selected_eu_site = replace(selected_eu_site, config=config, metadata=site_metadata)

    source_path = Path(input_path).expanduser().resolve()
    if not source_path.exists():
        raise FileNotFoundError(
            f"Die Eingabedatei wurde nicht gefunden: {source_path}"
        )
    if not source_path.is_file():
        raise H2RunError(f"Der Eingabepfad ist keine Datei: {source_path}")

    try:
        raw_input = pd.read_csv(source_path, dtype=str, keep_default_na=False)
    except (pd.errors.ParserError, UnicodeDecodeError) as exc:
        raise H2RunError(
            f"Die CSV-Eingabedatei konnte nicht gelesen werden: {source_path}"
        ) from exc
    input_sha256 = _sha256(source_path)
    if emission_factor_metadata_path is not None:
        _load_emission_factor_metadata(
            raw_input, Path(emission_factor_metadata_path), input_sha256
        )
    if selected_eu_site is not None:
        _require_eu_input_context_matches(raw_input, selected_eu_site.metadata)
        raw_input.attrs["eu_site_configuration"] = selected_eu_site.metadata
    if raw_input.attrs.get("sensitivity_provenance") is not None:
        from h2_sensitivity_overrides import verify_case_provenance
        verify_case_provenance(raw_input, override_record, baseline_config=baseline_config)
    elif override_record is not None and (selected_eu_site is not None or override_record["parameter"] == "h2_demand_multiplier"):
        raise H2RunError("EU sensitivity_override benötigt einen abgeleiteten SHA-gebundenen Quellenvertrag.")
    if override_record is not None:
        raw_input.attrs["sensitivity_override"] = override_record
    raw_input.attrs["temporal_correlation_timezone"] = config.study.temporal_correlation_timezone
    validated_input = validate_hourly_input(
        raw_input,
        require_separate_emission_factors=require_separate_emission_factors,
        emissions_reporting=emissions_reporting,
    )

    run_config = replace(config, scenario=selected_scenario)
    run_config.validate()
    result = optimize_hydrogen_system(
        validated_input,
        config=run_config,
        solver_output=solver_output,
        solver_backend=solver_backend,
        require_separate_emission_factors=require_separate_emission_factors,
        emissions_reporting=emissions_reporting,
    )

    output_paths = _prepare_output_paths(
        Path(output_directory).expanduser(),
        source_path=source_path,
        overwrite=overwrite,
    )
    summary = _build_summary(
        result=result,
        config=run_config,
        validated_input=validated_input,
        source_path=source_path,
        input_sha256=input_sha256,
    )
    metadata = _build_metadata(
        result=result,
        config=run_config,
        validated_input=validated_input,
        source_path=source_path,
        input_sha256=input_sha256,
    )

    _write_csv_atomic(validated_input, output_paths[VALIDATED_INPUT_FILENAME])
    _write_csv_atomic(summary, output_paths[SUMMARY_FILENAME])
    _write_csv_atomic(
        result.hourly_operation,
        output_paths[HOURLY_OPERATION_FILENAME],
    )
    _write_json_atomic(metadata, output_paths[RUN_METADATA_FILENAME])

    return RunArtifacts(
        output_directory=output_paths[SUMMARY_FILENAME].parent,
        summary_path=output_paths[SUMMARY_FILENAME],
        hourly_operation_path=output_paths[HOURLY_OPERATION_FILENAME],
        validated_input_path=output_paths[VALIDATED_INPUT_FILENAME],
        metadata_path=output_paths[RUN_METADATA_FILENAME],
        result=result,
    )


def _load_emission_factor_metadata(
    data: pd.DataFrame, path: Path, input_sha256: str
) -> None:
    """Load a factor contract bound to the exact CSV bytes, before optimization.

    The JSON requires ``schema_version='1.0'``, ``input_sha256``,
    ``emission_factor_mode='explicit_separate_factors'`` or
    ``emission_factor_mode='regulatory_only'`` and
    ``emission_factor_sources`` as documented in ``validate_hourly_input``.
    It does not select or invent regulatory factors from a country name.
    """
    source = path.expanduser().resolve()
    try:
        metadata = json.loads(source.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise H2RunError("Emissionsfaktor-Metadaten sind keine gültige JSON-Datei.") from exc
    if not isinstance(metadata, dict) or metadata.get("schema_version") != "1.0":
        raise H2RunError("Emissionsfaktor-Metadaten benötigen schema_version 1.0.")
    if metadata.get("input_sha256") != input_sha256:
        raise H2RunError("Der Hash der Emissionsfaktor-Metadaten passt nicht zur Eingabe.")
    if metadata.get("emission_factor_mode") not in (SEPARATE_EMISSION_MODE, REGULATORY_ONLY_EMISSION_MODE):
        raise H2RunError("Emissionsfaktor-Metadaten müssen getrennte Faktoren oder regulatory_only deklarieren.")
    data.attrs["emission_factor_mode"] = metadata["emission_factor_mode"]
    data.attrs["emission_factor_sources"] = metadata.get("emission_factor_sources")
    data.attrs["emission_factor_metadata"] = {
        "source_path": str(source), "sha256": _sha256(source)
    }
    if "parent_input" in metadata or "case_transformation" in metadata:
        if not isinstance(metadata.get("parent_input"), dict) or not isinstance(metadata.get("case_transformation"), dict):
            raise H2RunError("Abgeleiteter Quellenvertrag benötigt parent_input und case_transformation.")
        data.attrs["sensitivity_provenance"] = {
            "parent_input": metadata["parent_input"], "case_transformation": metadata["case_transformation"],
            "baseline_configuration": metadata.get("baseline_configuration")}
    context = {key: metadata[key] for key in (
        "site_id", "country_code", "calendar_timezone", "historical_year", "price_year",
        "annualization_basis", "annual_hours", "expected_hours", "demand_profile",
    ) if key in metadata}
    for key in ("site_id", "country_code", "calendar_timezone"):
        if key in context and (not isinstance(context[key], str) or not context[key].strip()):
            raise H2RunError(f"Der Quellenvertrag benötigt einen gültigen {key}.")
    for key in ("historical_year", "price_year"):
        if key in context and (isinstance(context[key], bool) or not isinstance(context[key], int) or not 1900 <= context[key] <= 2100):
            raise H2RunError(f"Der Quellenvertrag benötigt ein gültiges ganzzahliges {key}.")
    for key in ("annual_hours", "expected_hours"):
        if key in context and (type(context[key]) is not int or context[key] not in (8760,8784)):
            raise H2RunError(f"Der Quellenvertrag benötigt gültige {key}.")
    if "expected_hours" in context and len(data) != context["expected_hours"]:
        raise H2RunError("CSV-Stundenanzahl widerspricht expected_hours des Quellenvertrags.")
    if "annualization_basis" in context and context["annualization_basis"] not in ("historical_calendar_year","legacy_365_day_reference"):
        raise H2RunError("Unbekannte Quellenvertrag-Annualisierungsbasis.")
    if "demand_profile" in context and not isinstance(context["demand_profile"],dict):
        raise H2RunError("demand_profile muss ein dokumentiertes Profilobjekt sein.")
    data.attrs["declared_input_context"] = context


def _require_eu_input_context_matches(data: pd.DataFrame, site_metadata: dict) -> None:
    """Reject declared source/site contradictions without inferring a CSV year."""
    expected = {
        "site_id": site_metadata["site_id"],
        "country_code": site_metadata["country_code"],
        "calendar_timezone": site_metadata["calendar_timezone"],
        "historical_year": site_metadata["historical_year"],
        "price_year": site_metadata["wacc"]["cost_price_year"],
        "annualization_basis": site_metadata["annualization"]["basis"],
        "annual_hours": site_metadata["annualization"]["annual_hours"],
        "expected_hours": site_metadata["time_contract"]["expected_hours"],
    }
    for key, value in data.attrs.get("declared_input_context", {}).items():
        if key == "demand_profile":
            if value.get("annual_kg") != site_metadata["annualization"]["annual_h2_delivery_kg"]:
                raise H2RunError("Quellenvertrag demand_profile.annual_kg widerspricht der festen EU-Jahreslieferung.")
            continue
        if value != expected[key]:
            raise H2RunError(f"Quellenvertrag {key}={value!r} widerspricht --eu-site: erwartet {expected[key]!r}.")


def _coerce_scenario(scenario: Scenario | str) -> Scenario:
    if isinstance(scenario, Scenario):
        return scenario
    if not isinstance(scenario, str):
        raise TypeError("scenario muss ein String oder ein Scenario-Wert sein.")
    try:
        return Scenario(scenario)
    except ValueError as exc:
        allowed = ", ".join(item.value for item in Scenario)
        raise ValueError(
            f"Unbekanntes Szenario '{scenario}'. Erlaubte Werte: {allowed}."
        ) from exc


def _prepare_output_paths(
    output_directory: Path,
    *,
    source_path: Path,
    overwrite: bool,
) -> dict[str, Path]:
    resolved_output_directory = output_directory.resolve()
    if resolved_output_directory.exists() and not resolved_output_directory.is_dir():
        raise H2RunError(
            f"Der Ausgabepfad ist kein Verzeichnis: {resolved_output_directory}"
        )

    output_paths = {
        filename: resolved_output_directory / filename
        for filename in OUTPUT_FILENAMES
    }
    colliding_outputs = [
        path.name for path in output_paths.values() if path.resolve() == source_path
    ]
    if colliding_outputs:
        raise H2RunError(
            "Die Eingabedatei darf nicht denselben Pfad wie eine Ergebnisdatei haben: "
            + ", ".join(colliding_outputs)
            + "."
        )
    existing_outputs = [path for path in output_paths.values() if path.exists()]
    if existing_outputs and not overwrite:
        names = ", ".join(path.name for path in existing_outputs)
        raise FileExistsError(
            f"Ergebnisdateien existieren bereits ({names}). Nutze --overwrite zum Ersetzen."
        )

    resolved_output_directory.mkdir(parents=True, exist_ok=True)
    return output_paths


def _build_summary(
    *,
    result: HydrogenOptimizationResult,
    config: ModelConfig,
    validated_input: pd.DataFrame,
    source_path: Path,
    input_sha256: str,
) -> pd.DataFrame:
    summary: dict[str, object] = {
        "solver_status": result.solver_status,
        "solver_name": result.solver_name,
        "scenario": config.scenario.value,
        "input_file": str(source_path),
        "input_sha256": input_sha256,
        "number_of_hours": len(validated_input),
        "emission_factor_mode": validated_input.attrs["emission_factor_mode"],
        "emissions_reporting": result.emissions_reporting,
        "operational_emissions_status": result.operational_emissions_status,
        "start_timestamp_utc": validated_input["timestamp"].iloc[0].isoformat(),
        "end_timestamp_utc": validated_input["timestamp"].iloc[-1].isoformat(),
        "annualization_factor": result.annualization_factor,
        "annual_hours": result.annual_hours,
        "modeled_hours": result.modeled_hours,
        "annualization_basis": result.annualization_basis,
        "objective_eur_per_year": result.objective_eur_per_year,
        "lcoh_eur_per_kg_h2": result.lcoh_eur_per_kg_h2,
        "annual_h2_delivered_kg": result.annual_h2_delivered_kg,
        "annual_h2_produced_kg": result.annual_h2_produced_kg,
        "annual_grid_emissions_kg_co2e": result.annual_grid_emissions_kg_co2e,
        "operational_emission_intensity_kg_co2e_per_kg_h2": (
            result.operational_emission_intensity_kg_co2e_per_kg_h2
        ),
        "annual_regulatory_non_renewable_electricity_mwh": (
            result.annual_regulatory_non_renewable_electricity_mwh
        ),
        "annual_regulatory_emissions_kg_co2e": (
            result.annual_regulatory_emissions_kg_co2e
        ),
        "regulatory_emission_intensity_kg_co2e_per_kg_h2": (
            result.regulatory_emission_intensity_kg_co2e_per_kg_h2
        ),
        "regulatory_emission_intensity_g_co2e_per_mj_h2": (
            result.regulatory_emission_intensity_g_co2e_per_mj_h2
        ),
        "red_iii_ghg_savings_fraction": result.red_iii_ghg_savings_fraction,
        "red_iii_ghg_compliant": result.red_iii_ghg_compliant,
        "red_iii_maximum_product_intensity_kg_co2e_per_kg_h2": (
            result.red_iii_maximum_product_intensity_kg_co2e_per_kg_h2
        ),
        "red_iii_maximum_product_intensity_g_co2e_per_mj": (
            result.red_iii_maximum_product_intensity_g_co2e_per_mj
        ),
        "solver_runtime_seconds": result.runtime_seconds,
        "optimality_gap_fraction": result.optimality_gap_fraction,
        "max_electricity_balance_residual_mwh": (
            result.max_electricity_balance_residual_mwh
        ),
        "max_hydrogen_balance_residual_kg": (
            result.max_hydrogen_balance_residual_kg
        ),
        "annual_cost_balance_residual_eur_per_year": (
            result.annual_cost_balance_residual_eur_per_year
        ),
        "red_iii_temporal_mode": result.red_iii_temporal_mode,
        "red_iii_temporal_compliant": result.red_iii_temporal_compliant,
        "red_iii_correlation_periods": result.red_iii_correlation_periods,
        "max_red_iii_temporal_deficit_mwh": (
            result.max_red_iii_temporal_deficit_mwh
        ),
    }
    summary.update(result.capacities)
    summary.update(result.annual_costs)
    return pd.DataFrame([summary])


def _build_metadata(
    *,
    result: HydrogenOptimizationResult,
    config: ModelConfig,
    validated_input: pd.DataFrame,
    source_path: Path,
    input_sha256: str,
) -> dict[str, object]:
    parameters = {
        name: {
            "value": float(parameter.value),
            "unit": parameter.unit,
            "source": parameter.source,
            "reference_year": parameter.reference_year,
            "note": parameter.note,
        }
        for name, parameter in iter_scalar_parameters(config)
    }
    gurobi_version = ".".join(str(part) for part in gp.gurobi.version())
    return {
        "schema_version": "1.7",
        **({"sensitivity_override": validated_input.attrs["sensitivity_override"]}
           if "sensitivity_override" in validated_input.attrs else {}),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "scenario": config.scenario.value,
        "input": {
            "source_path": str(source_path),
            "sha256": input_sha256,
            "number_of_hours": len(validated_input),
            "start_timestamp_utc": validated_input["timestamp"].iloc[0].isoformat(),
            "end_timestamp_utc": validated_input["timestamp"].iloc[-1].isoformat(),
            "time_zone": "UTC",
            "frequency": "1h",
            "emission_factor_mode": validated_input.attrs["emission_factor_mode"],
            "emissions_reporting": result.emissions_reporting,
            "emission_factor_sources": validated_input.attrs.get("emission_factor_sources", {}),
            "emission_factor_metadata": validated_input.attrs.get("emission_factor_metadata"),
            "legacy_shared_factor": (
                validated_input.attrs["emission_factor_mode"] == LEGACY_EMISSION_MODE
            ),
            "eu_site_configuration": validated_input.attrs.get("eu_site_configuration"),
            "declared_input_context": validated_input.attrs.get("declared_input_context", {}),
            **({"sensitivity_provenance": validated_input.attrs["sensitivity_provenance"]}
               if "sensitivity_provenance" in validated_input.attrs else {}),
            **validated_input.attrs.get("declared_input_context", {}),
        },
        "calendar_scope": {
            "annualization": {
                "basis": result.annualization_basis,
                "reference_year": (int(config.study.profile_calendar_year.value)
                                   if result.annualization_basis == "historical_calendar_year" else None),
                "annual_hours": result.annual_hours,
                "modeled_hours": result.modeled_hours,
                "time_step_hours": config.study.time_step_hours.value,
                "factor": result.annualization_factor,
                "period_interpretation": ("complete_historical_calendar_year"
                    if result.annualization_basis == "historical_calendar_year" and result.modeled_hours == result.annual_hours
                    else "cyclic_period_reference_annualization"),
            },
            "requested_site_timezone": (validated_input.attrs.get("eu_site_configuration") or {}).get("calendar_timezone"),
            "monthly_correlation_calendar": config.study.temporal_correlation_timezone,
            "monthly_grouping_basis": ("utc_calendar_month" if config.study.temporal_correlation_timezone == "UTC"
                                       else "site_local_calendar_month"),
            "hourly_grouping_basis": "physical_utc_hour",
            "site_timezone_applied_to_monthly_correlation": (
                validated_input.attrs.get("eu_site_configuration") is not None
                and config.study.temporal_correlation_timezone != "UTC"),
            "note": "S1 korreliert die gesamte Elektrolyse- und Kompressorstrommenge je konfiguriertem Kalender-Monat; S2 prüft jede physische UTC-Stunde separat.",
        },
        "software": {
            "python": sys.version.split()[0],
            "pandas": pd.__version__,
            "scipy": scipy.__version__,
            "gurobi": gurobi_version,
        },
        "result": {
            "emissions_reporting": result.emissions_reporting,
            "operational_emissions_status": result.operational_emissions_status,
            "solver_status": result.solver_status,
            "solver_name": result.solver_name,
            "solver_runtime_seconds": result.runtime_seconds,
            "optimality_gap_fraction": result.optimality_gap_fraction,
            "objective_eur_per_year": result.objective_eur_per_year,
            "lcoh_eur_per_kg_h2": result.lcoh_eur_per_kg_h2,
            "emissions": {
                "factor_mode": validated_input.attrs["emission_factor_mode"],
                "operational_grid_emissions_kg_co2e_per_year": (
                    result.annual_grid_emissions_kg_co2e
                ),
                "operational_intensity_kg_co2e_per_kg_h2": (
                    result.operational_emission_intensity_kg_co2e_per_kg_h2
                ),
                "regulatory_non_renewable_electricity_mwh_per_year": (
                    result.annual_regulatory_non_renewable_electricity_mwh
                ),
                "regulatory_emissions_kg_co2e_per_year": (
                    result.annual_regulatory_emissions_kg_co2e
                ),
                "regulatory_intensity_kg_co2e_per_kg_h2": (
                    result.regulatory_emission_intensity_kg_co2e_per_kg_h2
                ),
                "regulatory_intensity_g_co2e_per_mj_h2_lhv": (
                    result.regulatory_emission_intensity_g_co2e_per_mj_h2
                ),
                "red_iii_ghg_savings_fraction": (
                    result.red_iii_ghg_savings_fraction
                ),
                "red_iii_ghg_compliant": result.red_iii_ghg_compliant,
                "maximum_intensity_kg_co2e_per_kg_h2": (
                    result.red_iii_maximum_product_intensity_kg_co2e_per_kg_h2
                ),
                "maximum_intensity_g_co2e_per_mj_h2_lhv": (
                    result.red_iii_maximum_product_intensity_g_co2e_per_mj
                ),
                "scope_note": (
                    ("Betriebliche Stromemissionen werden im expliziten regulatory_only-Modus nicht bewertet; "
                     "fehlende Faktoren und Kennzahlen werden nicht durch null ersetzt. "
                     if result.emissions_reporting == REGULATORY_ONLY_EMISSION_MODE else
                     "Die operative Bilanz bewertet jeden physischen Netzbezug "
                     "mit grid_emission_factor. ")
                    + "Die regulatorische Bilanz nutzt "
                    "regulatory_grid_emission_factor; Legacy-Eingaben verwenden "
                    "ausdrücklich denselben Faktor für beide Bilanzen. Sie "
                    "bewertet zeitlich zugeordneten erneuerbaren Strom im "
                    "allgemeinen Art.-4(4)-Pfad mit null. Berücksichtigt werden "
                    "nur Stromemissionen bis zur H2-Bereitstellung; Herstellung "
                    "der Anlagen und weitere Vorketten liegen außerhalb der "
                    "gewählten Systemgrenze. Bezugsbasis ist der H2-Heizwert "
                    "von 120 MJ/kg."
                ),
            },
            "balance_diagnostics": {
                "max_electricity_balance_residual_mwh": (
                    result.max_electricity_balance_residual_mwh
                ),
                "max_hydrogen_balance_residual_kg": (
                    result.max_hydrogen_balance_residual_kg
                ),
                "annual_cost_balance_residual_eur_per_year": (
                    result.annual_cost_balance_residual_eur_per_year
                ),
            },
            "red_iii_temporal_check": {
                "mode": result.red_iii_temporal_mode,
                "calendar_timezone": config.study.temporal_correlation_timezone,
                "grouping_basis": ("physical_utc_hour" if result.red_iii_temporal_mode == "hourly"
                                   else "calendar_month" if result.red_iii_temporal_mode == "monthly" else None),
                "compliant": result.red_iii_temporal_compliant,
                "number_of_correlation_periods": (
                    result.red_iii_correlation_periods
                ),
                "max_deficit_mwh": result.max_red_iii_temporal_deficit_mwh,
                "scope_note": (
                    "Die zeitliche Strommengen-Korrelation ist in den Szenarien "
                    "red_monthly und red_hourly optimiert und ex post geprüft. "
                    "Die Niedrigpreis-Ausnahme ist mangels Day-Ahead- und ETS-Daten "
                    "nicht aktiviert. Die regulatorische THG-Intensität wird "
                    "berechnet und für RED-Szenarien gegen den Grenzwert geprüft. "
                    "Zusätzlichkeit, geografische Korrelation und eindeutige "
                    "Allokation bleiben extern zu belegende Eingangsnachweise."
                ),
            },
        },
        "model_parameters": parameters,
        "model_calendar": {"temporal_correlation_timezone": config.study.temporal_correlation_timezone},
        "output_files": {
            "validated_input": VALIDATED_INPUT_FILENAME,
            "summary": SUMMARY_FILENAME,
            "hourly_operation": HOURLY_OPERATION_FILENAME,
            "metadata": RUN_METADATA_FILENAME,
        },
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for block in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_csv_atomic(data: pd.DataFrame, destination: Path) -> None:
    temporary = destination.with_name(destination.name + ".tmp")
    try:
        data.to_csv(temporary, index=False, encoding="utf-8")
        os.replace(temporary, destination)
    finally:
        if temporary.exists():
            temporary.unlink()


def _write_json_atomic(data: dict[str, object], destination: Path) -> None:
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
        description=(
            "Führt den geprüften H2-Basiskern für eine stündliche CSV-Datei aus."
        ),
        epilog=(
            "Beispiel: python run_single_site_h2.py --input test_input.csv "
            "--scenario reference --output-dir results\\testlauf"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="CSV-Datei mit den sechs Pflichtspalten aus h2_input_data.py.",
    )
    parser.add_argument(
        "--scenario",
        choices=SUPPORTED_CLI_SCENARIOS,
        default=Scenario.REFERENCE.value,
        help="Stromversorgungsszenario; Standard: reference.",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="Zielordner für Eingabekopie, Zusammenfassung, Stundenwerte und Metadaten.",
    )
    parser.add_argument(
        "--solver",
        choices=("auto", "gurobi", "scipy-highs"),
        default="auto",
        help=(
            "LP-Löser; auto nutzt Gurobi und wechselt bei einer größenbeschränkten "
            "Lizenz für große Modelle zu SciPy/HiGHS."
        ),
    )
    parser.add_argument(
        "--emission-factor-metadata",
        type=Path,
        help="JSON-Quellenvertrag für separate/regulatory-only Faktoren, gebunden an den CSV-SHA256.",
    )
    parser.add_argument(
        "--emissions-reporting",
        choices=("complete", "regulatory-only"),
        default="complete",
        help="complete benötigt den betrieblichen Faktor; regulatory-only berechnet ausschließlich die regulatorische THG-Bilanz ohne operative Ersatzwerte.",
    )
    parser.add_argument("--eu-site", choices=EU_SITE_IDS, help="Aktiviert die dokumentierten historischen EU-Standort- und Technologie-WACC-Werte.")
    parser.add_argument("--eu-design", type=Path, help="Optionaler expliziter EU-Entwurfs-JSON-Pfad für --eu-site.")
    parser.add_argument(
        "--require-separate-emission-factors",
        action="store_true",
        help="Verlangt vor dem Solve unabhängig dokumentierte operative/regulatorische Faktoren.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Ersetzt vorhandene Ergebnisdateien mit denselben vier Namen.",
    )
    parser.add_argument(
        "--solver-output",
        action="store_true",
        help="Zeigt das vollständige Gurobi-Protokoll.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_argument_parser()
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not arguments:
        parser.print_help()
        print(
            "\nEs wurde noch kein Modelllauf gestartet. Gib --input und --output-dir an."
        )
        return 0

    args = parser.parse_args(arguments)
    try:
        artifacts = run_single_site_h2(
            args.input,
            args.output_dir,
            scenario=args.scenario,
            overwrite=args.overwrite,
            solver_output=args.solver_output,
            solver_backend=args.solver,
            emission_factor_metadata_path=args.emission_factor_metadata,
            require_separate_emission_factors=args.require_separate_emission_factors,
            emissions_reporting=args.emissions_reporting.replace("-", "_"),
            eu_site=args.eu_site,
            eu_design_path=args.eu_design,
        )
    except (
        FileNotFoundError,
        FileExistsError,
        H2RunError,
        HourlyInputError,
        HydrogenOptimizationError,
        NotImplementedError,
        OSError,
        TypeError,
        ValueError,
    ) as exc:
        print(f"Fehler: {exc}", file=sys.stderr)
        return 1

    print("Modelllauf erfolgreich abgeschlossen.")
    print(f"Szenario: {args.scenario}")
    print(f"Solver: {artifacts.result.solver_name}")
    print(f"LCOH: {artifacts.result.lcoh_eur_per_kg_h2:.4f} EUR/kg H2")
    print(
        "Regulatorische THG-Intensität: "
        f"{artifacts.result.regulatory_emission_intensity_kg_co2e_per_kg_h2:.4f} "
        "kg CO2e/kg H2, "
        f"RED-III-Grenzwert eingehalten={artifacts.result.red_iii_ghg_compliant}"
    )
    print(
        "Maximale Bilanzfehler: "
        f"Strom {artifacts.result.max_electricity_balance_residual_mwh:.3e} MWh, "
        f"H2 {artifacts.result.max_hydrogen_balance_residual_kg:.3e} kg"
    )
    if artifacts.result.red_iii_temporal_compliant is not None:
        print(
            "RED-III-Zeitkorrelation: "
            f"{artifacts.result.red_iii_temporal_mode}, "
            f"konform={artifacts.result.red_iii_temporal_compliant}"
        )
    print(f"Zusammenfassung: {artifacts.summary_path}")
    print(f"Stundenwerte: {artifacts.hourly_operation_path}")
    print(f"Validierte Eingabe: {artifacts.validated_input_path}")
    print(f"Metadaten: {artifacts.metadata_path}")
    return 0


if __name__ == "__main__":
    return_code = main()
    if return_code:
        raise SystemExit(return_code)


__all__ = [
    "H2RunError",
    "RunArtifacts",
    "build_argument_parser",
    "main",
    "run_single_site_h2",
]
