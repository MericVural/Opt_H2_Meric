"""Explicit one-factor configuration changes, applied after site selection.

This module changes configuration copies only; the mathematical LP is unchanged.
Legacy absolute parameters retain their original meaning.
"""
from dataclasses import replace
from math import isfinite
from collections.abc import Mapping
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from copy import deepcopy

from config_h2 import CONFIG_SENSITIVITY_PARAMETERS, ModelConfig, iter_scalar_parameters, with_sensitivity_parameter
from h2_input_data import NUMERIC_HOURLY_COLUMNS, REGULATORY_EMISSION_COLUMN

WACC_COMPONENTS = ("pv", "wind_onshore", "electrolyzer", "compressor", "h2_storage")
NEW_SENSITIVITY_PARAMETERS = (
    "electricity_price_offset_eur_per_mwh", "real_wacc_shift_fraction", "real_wacc_multiplier",
    "electrolyzer_capex_factor", "electrolyzer_specific_electricity_factor", "h2_demand_multiplier",
)
INPUT_OVERRIDE_PARAMETERS = ("electricity_price_eur_per_mwh", "electricity_price_offset_eur_per_mwh", "h2_demand_multiplier")


def scaled_demand_profile(profile: dict, multiplier: float) -> dict:
    """Copy the declared delivery shape, scaling only its two quantity fields."""
    if not isinstance(profile, dict):
        raise ValueError("Demand sensitivity requires a documented demand_profile object.")
    updated = deepcopy(profile)
    for name in ("annual_kg", "kg_per_active_hour"):
        if name not in profile:
            if name == "annual_kg":
                raise ValueError("Demand profile requires an annual_kg target.")
            continue
        value = profile[name]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) or value <= 0:
            raise ValueError("Demand profile quantity fields must be finite and positive.")
        updated[name] = value * multiplier
        if not isfinite(updated[name]):
            raise ValueError("Scaled demand profile quantities must remain finite.")
    return updated


def apply_sensitivity_override(config: ModelConfig, override: Mapping) -> tuple[ModelConfig, dict]:
    """Validate one explicit intervention and record exact scalar before/after values."""
    if not isinstance(override, Mapping) or set(override) - {"parameter", "value", "source", "note"}:
        raise ValueError("sensitivity_override requires parameter, value, source and optional note only.")
    parameter, value, source = (override.get(key) for key in ("parameter", "value", "source"))
    note = override.get("note", "")
    if parameter not in (*NEW_SENSITIVITY_PARAMETERS, *CONFIG_SENSITIVITY_PARAMETERS, *INPUT_OVERRIDE_PARAMETERS):
        raise ValueError("Unknown sensitivity_override parameter.")
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise ValueError("Sensitivity override value must be finite and numeric.")
    if not isinstance(source, str) or not source.strip() or not isinstance(note, str):
        raise ValueError("Sensitivity override requires source and textual note.")
    numeric = float(value)
    before = dict(iter_scalar_parameters(config))
    if parameter in ("real_wacc_shift_fraction", "real_wacc_multiplier"):
        if parameter == "real_wacc_multiplier" and numeric <= 0:
            raise ValueError("WACC multipliers must be positive.")
        technologies = config.technologies
        updates = {}
        for name in WACC_COMPONENTS:
            technology = getattr(technologies, name)
            original = technology.real_wacc_fraction
            applied = (original.value * numeric if parameter == "real_wacc_multiplier"
                       else original.value + numeric)
            explanation = (" Multiply every component's real baseline rate; relative rate ratios retained."
                           if parameter == "real_wacc_multiplier"
                           else " Additive shift of every component's real rate; baseline differences retained.")
            updates[name] = replace(technology, real_wacc_fraction=replace(original,
                value=applied, source=source, note=note + explanation))
        updated = replace(config, technologies=replace(technologies, **updates))
        operation = ("multiply_all_five_real_wacc_rates" if parameter == "real_wacc_multiplier"
                     else "add_to_all_five_real_wacc_rates")
    elif parameter in ("electrolyzer_capex_factor", "electrolyzer_specific_electricity_factor"):
        if numeric <= 0:
            raise ValueError("Sensitivity multipliers must be positive.")
        attribute = ("capex_eur_per_kw" if parameter == "electrolyzer_capex_factor"
                     else "specific_electricity_kwh_per_kg_h2")
        absolute_parameter = ("electrolyzer_capex_eur_per_kw" if parameter == "electrolyzer_capex_factor"
                              else "electrolyzer_specific_electricity_kwh_per_kg_h2")
        updated = with_sensitivity_parameter(config, absolute_parameter,
            getattr(config.technologies.electrolyzer, attribute).value * numeric, source=source, note=note)
        operation = "multiply_baseline_scalar"
    elif parameter == "h2_demand_multiplier":
        if numeric <= 0:
            raise ValueError("H2 demand multipliers must be positive.")
        original = config.study.h2_demand_kg_per_day
        updated = replace(config, study=replace(config.study,
            h2_demand_kg_per_day=replace(original, value=original.value * numeric,
                source=source, note=note + " Multiply the prescribed hourly delivery profile; active hours and shape retained.")))
        operation = "multiply_hourly_h2_demand_preserve_profile"
    elif parameter in INPUT_OVERRIDE_PARAMETERS:
        if parameter == "electricity_price_eur_per_mwh" and numeric <= 0:
            raise ValueError("Legacy constant prices must be positive.")
        updated = config
        operation = "add_to_hourly_price_profile" if parameter.endswith("offset_eur_per_mwh") else "replace_hourly_prices_with_constant"
    else:
        updated = with_sensitivity_parameter(config, parameter, numeric, source=source, note=note)
        operation = "replace_baseline_scalar"
    updated.validate()
    after = dict(iter_scalar_parameters(updated))
    changed = {name: {"base_value": original.value, "applied_value": after[name].value, "unit": original.unit}
               for name, original in before.items() if original.value != after[name].value}
    return updated, {"parameter": parameter, "value": numeric, "source": source, "note": note,
                     "operation": operation, "changed_scalar_parameters": changed}


def verify_case_provenance(data: pd.DataFrame, override_record: dict | None, *, baseline_config: ModelConfig) -> None:
    """Reject changed parent bytes or changes outside the declared OAT intervention."""
    provenance = data.attrs["sensitivity_provenance"]
    parent, transformation = provenance["parent_input"], provenance["case_transformation"]
    digest = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
    baseline_receipt = provenance.get("baseline_configuration")
    if not isinstance(baseline_receipt, dict) or digest(baseline_receipt["path"]) != baseline_receipt.get("sha256"):
        raise ValueError("Sensitivity baseline configuration hash mismatch.")
    baseline = json.loads(Path(baseline_receipt["path"]).read_text(encoding="utf-8"))
    expected = {name: {"value": parameter.value, "unit": parameter.unit, "reference_year": parameter.reference_year}
                for name, parameter in iter_scalar_parameters(baseline_config)}
    if baseline.get("model_parameters") != expected or baseline.get("model_calendar") != {
            "temporal_correlation_timezone": baseline_config.study.temporal_correlation_timezone}:
        raise ValueError("Sensitivity baseline configuration differs from the selected base model.")
    if baseline.get("eu_design_sha256") != (data.attrs.get("eu_site_configuration") or {}).get("design_sha256"):
        raise ValueError("Sensitivity baseline EU design hash differs from the selected site.")
    accepted_baseline = baseline.get("accepted_baseline_metadata")
    if accepted_baseline is not None and (not isinstance(accepted_baseline, dict)
            or digest(accepted_baseline["path"]) != accepted_baseline.get("sha256")):
        raise ValueError("Sensitivity accepted baseline metadata hash mismatch.")
    if (digest(parent["path"]) != parent.get("sha256")
            or digest(parent["metadata_path"]) != parent.get("metadata_sha256")):
        raise ValueError("Sensitivity parent input or metadata hash mismatch.")
    source = json.loads(Path(parent["metadata_path"]).read_text(encoding="utf-8"))
    if (source.get("input_sha256") != parent["sha256"]
            or source.get("emission_factor_mode") != data.attrs.get("emission_factor_mode")
            or source.get("emission_factor_sources") != data.attrs.get("emission_factor_sources")):
        raise ValueError("Sensitivity factors must retain the original validated source contract.")
    original = pd.read_csv(parent["path"], dtype=str, keep_default_na=False)
    if original.columns.tolist() != data.columns.tolist() or len(original) != len(data):
        raise ValueError("Sensitivity CSV structure differs from its parent.")
    record = {key: value for key, value in transformation.items() if key != "case_id"}
    if override_record is None:
        if record != {"parameter": "baseline", "operation": "unchanged", "changed_scalar_parameters": {}}:
            raise ValueError("Derived sensitivity metadata and explicit override disagree.")
    elif record != override_record:
        raise ValueError("Derived sensitivity metadata and explicit override disagree.")
    for column in original.columns:
        expected = original[column]
        actual = data[column]
        if column == "timestamp":
            identical = pd.to_datetime(expected, utc=True).equals(pd.to_datetime(actual, utc=True))
        elif column in (*NUMERIC_HOURLY_COLUMNS, REGULATORY_EMISSION_COLUMN):
            expected = pd.to_numeric(expected)
            if column == "electricity_price" and record["parameter"] in ("electricity_price_eur_per_mwh", "electricity_price_offset_eur_per_mwh"):
                expected = (expected + record["value"] if record["parameter"] == "electricity_price_offset_eur_per_mwh"
                            else pd.Series(record["value"], index=expected.index))
            elif column == "h2_demand" and record["parameter"] == "h2_demand_multiplier":
                expected = expected * record["value"]
            identical = np.allclose(pd.to_numeric(actual), expected, rtol=1e-12, atol=1e-12, equal_nan=True)
        else:
            identical = actual.astype(str).equals(expected.astype(str))
        if not identical:
            raise ValueError("Sensitivity CSV changed a column outside its single declared intervention: " + column)
    parent_context = {key: source[key] for key in (
        "site_id", "country_code", "calendar_timezone", "historical_year", "price_year",
        "annualization_basis", "annual_hours", "expected_hours", "demand_profile",
    ) if key in source}
    if record["parameter"] == "h2_demand_multiplier" and "demand_profile" in parent_context:
        parent_context["demand_profile"] = scaled_demand_profile(parent_context["demand_profile"], record["value"])
    if parent_context != data.attrs.get("declared_input_context", {}):
        raise ValueError("Sensitivity calendar/demand context differs from its parent source contract.")
