"""Read-only contracts shared by scientific views and their exact CSV exports.

This module never runs a solver or changes an archived result. Native receipts
are reduced to display evidence; a missing or ambiguous reference is an error.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd


SCALAR_PATHS = {
    "pv_capex_eur_per_kw": "technologies.pv.capex_eur_per_kw",
    "wind_capex_eur_per_kw": "technologies.wind_onshore.capex_eur_per_kw",
    "h2_storage_capex_eur_per_kg_h2": "technologies.h2_storage.capex_eur_per_kg_h2",
    "electrolyzer_capex_eur_per_kw": "technologies.electrolyzer.capex_eur_per_kw",
    "electrolyzer_specific_electricity_kwh_per_kg_h2": "technologies.electrolyzer.specific_electricity_kwh_per_kg_h2",
}
LABELS = {
    "h2_demand_multiplier": "H₂-Jahresnachfrage",
    "h2_delivery_profile": "H₂-Lieferprofil",
    "electricity_price_offset_eur_per_mwh": "Verschiebung der Preisreihe",
    "electricity_price_eur_per_mwh": "Konstanter Strompreis",
    "real_wacc_multiplier": "Faktor aller Komponenten-WACC",
    "real_wacc_shift_fraction": "Verschiebung aller Komponenten-WACC",
    "uniform_real_wacc_fraction": "Einheitlicher realer WACC",
    "electrolyzer_capex_factor": "Faktor des PEM-CAPEX",
    "electrolyzer_specific_electricity_factor": "Faktor des PEM-Strombedarfs",
    "pv_capex_eur_per_kw": "PV-CAPEX",
    "wind_capex_eur_per_kw": "Wind-CAPEX",
    "h2_storage_capex_eur_per_kg_h2": "H₂-Speicher-CAPEX",
    "electrolyzer_capex_eur_per_kw": "PEM-CAPEX",
    "electrolyzer_specific_electricity_kwh_per_kg_h2": "PEM-Strombedarf",
}
UNITS = {"pv_capex_eur_per_kw": "EUR 2023/kW", "wind_capex_eur_per_kw": "EUR 2023/kW",
    "h2_storage_capex_eur_per_kg_h2": "EUR 2023/kg H₂", "electrolyzer_capex_eur_per_kw": "EUR 2023/kW",
    "electrolyzer_specific_electricity_kwh_per_kg_h2": "kWh/kg H₂"}
FACTORS = {"h2_demand_multiplier", "real_wacc_multiplier", "electrolyzer_capex_factor", "electrolyzer_specific_electricity_factor"}
OPERATIONS = {"electricity_price_offset_eur_per_mwh": "add_to_hourly_price_profile",
    "electricity_price_eur_per_mwh": "replace_hourly_prices_with_constant",
    "h2_demand_multiplier": "multiply_hourly_h2_demand_preserve_profile",
    "real_wacc_multiplier": "multiply_all_five_real_wacc_rates",
    "real_wacc_shift_fraction": "add_to_all_five_real_wacc_rates",
    "uniform_real_wacc_fraction": "replace_all_five_real_wacc_rates"}


def _present(value):
    return value is not None and value is not pd.NA and value is not pd.NaT and not (isinstance(value, float) and math.isnan(value)) and str(value) != ""


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str).encode()).hexdigest()


def _number(value, label):
    try:
        result = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{label} ist nicht numerisch belegt.") from None
    if not math.isfinite(result):
        raise ValueError(f"{label} ist nicht endlich belegt.")
    return result


def _parameter_column(frame):
    field = next((name for name in ("sensitivity_parameter", "parameter") if name in frame), None)
    if field is None:
        raise ValueError("Der Sensitivitätsparameter fehlt im gespeicherten Vertrag.")
    return field


def _parameters(metadata):
    return {key: {name: entry.get(name) for name in ("value", "unit", "reference_year")}
        for key, entry in metadata.get("model_parameters", {}).items() if isinstance(entry, dict)}


def _contained(root, raw):
    from .case_study_registry import contained_path
    return contained_path(root, raw)


def native_contract_fields(metadata, row, directory, root, *, input_cache=None):
    """Compact, independently useful fields from this row's native metadata.

    Reconstruction uses native scalar changes, never similarity of costs.
    Legacy direct scalar interventions use the saved comparison's explicit
    native base value. Input comparisons hash actual unmodified input columns.
    """
    params = _parameters(metadata)
    if not params:
        return {}
    raw_input = metadata.get("input", {})
    provenance = raw_input.get("sensitivity_provenance", {})
    transformation = provenance.get("case_transformation") or metadata.get("sensitivity_override") or {}
    family_parameter = row.get("sensitivity_parameter", row.get("parameter", "baseline"))
    parameter = transformation.get("parameter") or row.get("applied_parameter") or family_parameter
    operation = transformation.get("operation") or row.get("parameter_operation")
    if not _present(operation):
        operation = "unchanged" if family_parameter == "baseline" else OPERATIONS.get(parameter, "replace_baseline_scalar")
    fields = {"__native_configuration_sha256": _digest(params),
        "__native_calendar_sha256": _digest(metadata.get("model_calendar", {})),
        "__native_software_sha256": _digest(metadata.get("software", {})),
        "__native_input_sha256": raw_input.get("sha256"),
        "__baseline_input_sha256": provenance.get("parent_input", {}).get("sha256"),
        "__native_operation": operation, "__native_applied_parameter": parameter}
    if _present(row.get("parameter_operation")) and row["parameter_operation"] != operation:
        fields["__oat_contract_error"] = "Gespeicherte Operation widerspricht der nativen Provenienz."
    value = next((candidate for candidate in (transformation.get("value"), row.get("applied_value"), row.get("sensitivity_value"), row.get("value")) if _present(candidate)), None)
    if _present(value):
        fields["__native_applied_value"] = value
    baseline_params = json.loads(json.dumps(params))
    changed = transformation.get("changed_scalar_parameters", {})
    if changed:
        for key, change in changed.items():
            if key not in baseline_params or not _present(change.get("base_value")):
                fields["__oat_contract_error"] = "Native skalare Basisänderung ist unvollständig."
                continue
            baseline_params[key]["value"] = change["base_value"]
    elif family_parameter != "baseline":
        base = row.get("source_baseline_parameter_value")
        if not _present(base):
            base = row.get("baseline_parameter_value")
        if parameter in SCALAR_PATHS and _present(base):
            baseline_params[SCALAR_PATHS[parameter]]["value"] = _number(base, "Nativer Basiswert")
        elif parameter == "uniform_real_wacc_fraction" and _present(base):
            for key in baseline_params:
                if key.endswith(".real_wacc_fraction"):
                    baseline_params[key]["value"] = _number(base, "Nativer WACC-Basiswert")
        elif parameter in SCALAR_PATHS or parameter in {"uniform_real_wacc_fraction", "real_wacc_multiplier", "real_wacc_shift_fraction", "electrolyzer_capex_factor", "electrolyzer_specific_electricity_factor"}:
            fields["__oat_contract_error"] = "Rekonstruktion der eigenen nativen Basiskonfiguration fehlt."
    fields["__baseline_configuration_sha256"] = _digest(baseline_params)
    if parameter in SCALAR_PATHS:
        fields["__native_base_value"] = baseline_params.get(SCALAR_PATHS[parameter], {}).get("value")
    receipt = provenance.get("baseline_configuration", {})
    if receipt.get("path") and receipt.get("sha256"):
        try:
            snapshot_path = _contained(root, receipt["path"])
            if hashlib.sha256(snapshot_path.read_bytes()).hexdigest() != receipt["sha256"]:
                raise ValueError("Die gesicherte Basiskonfiguration wurde geändert.")
            snapshot = json.loads(snapshot_path.read_text(encoding="utf-8-sig"))
            # Validate the reconstructed values against the original snapshot.
            expected = _parameters(snapshot)
            if _digest(expected) != fields["__baseline_configuration_sha256"]:
                raise ValueError("Native Variante passt nicht zur gesicherten Basiskonfiguration.")
            fields["__baseline_receipt_sha256"] = receipt["sha256"]
        except (OSError, ValueError, KeyError) as exc:
            fields["__oat_contract_error"] = str(exc)
    data_path = Path(directory) / "validated_input.csv"
    fields["__native_validated_input_path"] = str(data_path)
    fields["__contract_repo_root"] = str(Path(root).resolve())
    # Keep discovery inexpensive: full input values are read lazily, only for
    # the selected family when an exact native parent receipt is insufficient.
    if input_cache is None:
        return fields
    if data_path.is_file():
        cache = input_cache if input_cache is not None else {}
        if data_path not in cache:
            data = pd.read_csv(data_path)
            if "timestamp" in data:
                data["timestamp"] = pd.to_datetime(data.timestamp, utc=True).astype(str)
            signatures = {}
            for label, excluded in (("full", ()), ("price", ("electricity_price",)), ("demand", ("h2_demand",))):
                columns = sorted(c for c in data if c not in excluded)
                table = data[columns]
                signatures[label] = hashlib.sha256(("|".join(columns)).encode() + pd.util.hash_pandas_object(table, index=False).values.tobytes()).hexdigest()
            cache[data_path] = signatures
        signatures = cache[data_path]
        fields.update(__native_input_values_sha256=signatures["full"],
            __input_without_price_sha256=signatures["price"], __input_without_demand_sha256=signatures["demand"])
    return fields


def parameter_presentation(frame, parameter):
    """Name the actual operation, including historical harmonized aliases."""
    column = _parameter_column(frame)
    selected = frame.loc[frame[column].eq(parameter)]
    operations = set()
    for _, row in selected.iterrows():
        operation = row.get("__native_operation", row.get("parameter_operation"))
        if not _present(operation):
            applied = row.get("applied_parameter")
            operation = OPERATIONS.get(applied if _present(applied) else parameter, "replace_baseline_scalar")
        # Some accepted tables map their native unchanged baseline to the
        # displayed parameter family (notably demand=1). It supplies the own
        # reference, not a second kind of intervention. Its full native
        # configuration/input is still checked by prepare_oat_frame below.
        if operation == "unchanged" and (row.get("__native_applied_parameter") == "baseline" or row.get("case_id") == "baseline"):
            continue
        operations.add(str(operation))
    if len(operations) > 1:
        raise ValueError("Verschiedene Preis-/Parameteroperationen dürfen keine gemeinsame Sensitivitätsachse teilen.")
    operation = next(iter(operations), OPERATIONS.get(parameter, "replace_baseline_scalar"))
    label = LABELS.get(parameter, parameter)
    relative = "relative_level" in selected and not selected.empty and selected.relative_level.notna().all()
    note = "Eigene unveränderte Basis; nur tatsächlich berechnete Varianten."
    if operation == "add_to_hourly_price_profile":
        label = "Verschiebung der Preisreihe"
        xlabel = "Jahresmittel der verschobenen Preisreihe [Faktor der Basis]" if relative else "Verschiebung der Preisreihe [EUR/MWh]"
        note += " Ein Offset wird zu jeder Stunde addiert; einzelne Stundenpreise werden nicht mit dem Achsenfaktor multipliziert. Geldbasis gemäß ausgewähltem Fall."
    elif operation == "replace_hourly_prices_with_constant":
        label = "Konstanter Strompreis"
        xlabel = "Konstanter Strompreis [Faktor des Basispreises]" if relative else "Konstanter Strompreis [EUR/MWh]"
        note += " Jede Stunde erhält denselben Tarif. Geldbasis gemäß ausgewähltem Fall."
    elif parameter == "h2_demand_multiplier":
        xlabel = "H₂-Jahresnachfrage [% der Basis]"
    elif operation == "multiply_all_five_real_wacc_rates":
        label = "Faktor aller Komponenten-WACC"
        xlabel = label + " [–]"
    elif relative:
        xlabel = label + " [Faktor des Basiswerts]"
    elif parameter == "real_wacc_shift_fraction":
        xlabel = label + " [Prozentpunkte]"
    elif parameter == "uniform_real_wacc_fraction":
        xlabel = label + " [%]"
    elif parameter in FACTORS:
        xlabel = label + " [–]"
    else:
        xlabel = label + (" [" + UNITS[parameter] + "]" if parameter in UNITS else "")
    return {"label": label, "xlabel": xlabel, "note": note, "operation": operation, "relative": relative}


def _groups(frame):
    columns = [c for c in ("study_id", "site_id", "scenario_id") if c in frame]
    for alternatives in (("demand_profile", "profile"), ("solver_name",)):
        column = next((c for c in alternatives if c in frame), None)
        if column:
            columns.append(column)
    if not columns:
        raise ValueError("Standort-/Profil-/Szenario-/Solverkontext fehlt für die Sensitivität.")
    return columns


def _same(left, right, fields):
    return all(_present(left.get(field)) and _present(right.get(field)) and str(left[field]) == str(right[field]) for field in fields)


def _input_signature(row, label, cache):
    field = {"full": "__native_input_values_sha256", "price": "__input_without_price_sha256", "demand": "__input_without_demand_sha256"}[label]
    if _present(row.get(field)):
        return row[field]
    root = row.get("__contract_repo_root")
    raw = row.get("__native_validated_input_path")
    if not _present(root) or not _present(raw):
        return None
    path = _contained(root, raw)
    _load_input(path, cache)
    return cache[path].get(label)


def _load_input(path, cache):
    if path not in cache:
        if not path.is_file():
            cache[path] = {}
        else:
            data = pd.read_csv(path)
            if "timestamp" in data:
                data["timestamp"] = pd.to_datetime(data.timestamp, utc=True).astype(str)
            signatures = {}
            for name, excluded in (("full", ()), ("price", ("electricity_price",)), ("demand", ("h2_demand",))):
                columns = sorted(c for c in data if c not in excluded)
                signatures[name] = hashlib.sha256(("|".join(columns)).encode() + pd.util.hash_pandas_object(data[columns], index=False).values.tobytes()).hexdigest()
            cache[path] = {**signatures, "data": data}
    return cache[path].get("data")


def _actual_intervention_matches(variant, baseline, parameter, cache):
    roots = [row.get("__contract_repo_root") for row in (variant, baseline)]
    paths = [row.get("__native_validated_input_path") for row in (variant, baseline)]
    if not all(_present(value) for value in [*roots, *paths]):
        return False
    data, base = [_load_input(_contained(root, path), cache) for root, path in zip(roots, paths)]
    if data is None or base is None or len(data) != len(base):
        return False
    operation = variant.get("__native_operation", variant.get("parameter_operation"))
    changed_column = "electricity_price" if operation in {"add_to_hourly_price_profile", "replace_hourly_prices_with_constant"} else "h2_demand" if parameter == "h2_demand_multiplier" else None
    if changed_column is None:
        return _input_signature(variant, "full", cache) == _input_signature(baseline, "full", cache)
    if changed_column not in data or changed_column not in base:
        return False
    label = "price" if changed_column == "electricity_price" else "demand"
    if _input_signature(variant, label, cache) != _input_signature(baseline, label, cache):
        return False
    value = next((variant.get(name) for name in ("__native_applied_value", "applied_value", "sensitivity_value", "value") if _present(variant.get(name))), None)
    if not _present(value):
        return False
    value = _number(value, "Nativer Eingriffswert")
    original = pd.to_numeric(base[changed_column], errors="raise").to_numpy()
    actual = pd.to_numeric(data[changed_column], errors="raise").to_numpy()
    expected = original + value if operation == "add_to_hourly_price_profile" else np.full(len(original), value) if operation == "replace_hourly_prices_with_constant" else original * value
    if not np.allclose(actual, expected, rtol=1e-11, atol=1e-9):
        return False
    # An actual input intervention must agree with the displayed level too.
    # Historical harmonized price factors describe the arithmetic mean,
    # whereas native offsets and demand factors are direct intervention values.
    if _present(variant.get("__plot_x")):
        plotted = _number(variant["__plot_x"], "Dargestellte Parameterstufe")
        if changed_column == "electricity_price" and _present(variant.get("relative_level")):
            mean = float(np.mean(original))
            if abs(mean) < 1e-12:
                return False
            expected_level = float(np.mean(actual)) / mean
        else:
            expected_level = value
        if not math.isclose(plotted, expected_level, rel_tol=1e-11, abs_tol=1e-9):
            return False
    return True


def _reference_matches(variant, baseline, parameter, cache):
    if _present(variant.get("__oat_contract_error")) or _present(baseline.get("__oat_contract_error")):
        return False
    config = variant.get("__baseline_configuration_sha256")
    native = baseline.get("__native_configuration_sha256")
    if _present(config) or _present(native):
        if not _present(config) or not _present(native) or config != native:
            return False
        if not _same(variant, baseline, ["__native_calendar_sha256", "__native_software_sha256"]):
            return False
        # Check only this chosen family, with one read per native input. This
        # also confirms the actual hourly delta and profile preservation.
        if _present(variant.get("__native_validated_input_path")) and _present(baseline.get("__native_validated_input_path")):
            return _actual_intervention_matches(variant, baseline, parameter, cache)
        operation = variant.get("__native_operation", variant.get("parameter_operation"))
        label = "price" if operation in {"add_to_hourly_price_profile", "replace_hourly_prices_with_constant"} else "demand" if parameter == "h2_demand_multiplier" else "full"
        left, right = _input_signature(variant, label, cache), _input_signature(baseline, label, cache)
        return _present(left) and _present(right) and left == right
    # A complete explicit synthetic/display contract can be used by callers
    # that already verified the native sources. A plain cost/input row cannot.
    return _same(variant, baseline, ["baseline_context_sha256"])


def _case_id(row):
    for field in ("__analysis_id", "__result_directory", "result_directory", "case_id"):
        if _present(row.get(field)):
            return str(row[field])
    raise ValueError("Der native Referenzfall besitzt keine eindeutige Fall-ID.")


def _base_x(variants, parameter, presentation):
    if presentation["relative"] or parameter in FACTORS:
        return 1.0
    if parameter in {"electricity_price_offset_eur_per_mwh", "real_wacc_shift_fraction"} or presentation["operation"] == "add_to_hourly_price_profile":
        return 0.0
    values = []
    for _, row in variants.iterrows():
        value = row.get("__native_base_value")
        if not _present(value):
            value = row.get("source_baseline_parameter_value")
        if not _present(value):
            value = row.get("baseline_parameter_value")
        values.append(_number(value, "Eigener nativer Basiswert"))
    if not values or any(value != values[0] for value in values):
        raise ValueError("Die numerische Reihe besitzt keine eindeutige eigene Basisstufe.")
    return values[0]


def prepare_oat_frame(frame, *, parameter, metric=None):
    """Exact native variant rows plus their one proven own reference per curve."""
    data = frame.copy(deep=True)
    if "__plot_x" in data and "group_columns" in frame.attrs and "xlabel" in frame.attrs:
        if frame.attrs.get("oat_parameter") != parameter:
            raise ValueError("Vorbereitete Grafikdaten gehören zu einer anderen Parameterfamilie.")
        if metric is not None and (metric not in data or not pd.to_numeric(data[metric], errors="raise").map(math.isfinite).all()):
            raise ValueError("Die gewählte Ergebnisgröße ist nicht für alle dargestellten Fälle bewertet.")
        return data
    column = _parameter_column(data)
    selected = data.loc[data[column].eq(parameter)].copy()
    if selected.empty:
        raise ValueError("Für diesen Parameter liegen keine berechneten Varianten vor.")
    if "__oat_contract_error" in selected and selected.__oat_contract_error.notna().any():
        raise ValueError("Der native Sensitivitätsvertrag ist widersprüchlich: " + str(selected.__oat_contract_error.dropna().iloc[0]))
    family = next((c for c in ("__collection_id", "__gui_oat_family_id", "__collection", "__source_csv") if c in data), None)
    if family is None or selected[family].isna().any() or selected[family].nunique() != 1:
        raise ValueError("Eine Versuchsreihe eindeutig auswählen; verschiedene Familien werden nicht verbunden.")
    presentation = parameter_presentation(selected, parameter)
    group_columns = _groups(selected)
    x_column = "relative_level" if presentation["relative"] else next((c for c in ("sensitivity_value", "value") if c in selected and selected[c].notna().all()), None)
    if x_column is None:
        raise ValueError("Die tatsächlich angewandten Parameterstufen fehlen.")
    selected["__plot_x"] = pd.to_numeric(selected[x_column], errors="raise")
    if not presentation["relative"] and presentation["operation"] == "add_to_hourly_price_profile" and parameter != "electricity_price_offset_eur_per_mwh" and "applied_value" in selected:
        selected["__plot_x"] = pd.to_numeric(selected.applied_value, errors="raise")
    selected["__oat_is_baseline"] = False
    baselines = data.loc[data[column].eq("baseline") & data[family].eq(selected[family].iloc[0])].copy()
    outputs = []
    input_cache = {}
    for _, variants in selected.groupby(group_columns, dropna=False, sort=False):
        first = variants.iloc[0]
        if any(not _present(first.get(c)) for c in group_columns):
            raise ValueError("Ein Vergleichskontext enthält unbenannte Standort-/Profil-/Solverwerte.")
        base_x = _base_x(variants, parameter, presentation)
        embedded = variants.loc[variants.__plot_x.eq(base_x)]
        candidates = baselines.copy()
        for field in group_columns:
            candidates = candidates.loc[candidates[field].astype(str).eq(str(first[field]))]
        if embedded.empty:
            matches = [row for _, row in candidates.iterrows() if all(_reference_matches(variant, row, parameter, input_cache) for _, variant in variants.iterrows())]
            if len(matches) != 1:
                raise ValueError("Eigene Basis fehlt oder ist mehrdeutig; keine fremde Referenz wird eingesetzt.")
            baseline = matches[0].copy()
            reference_id = _case_id(baseline)
            baseline["__plot_x"] = base_x
            baseline["__oat_is_baseline"] = True
            baseline["__oat_reference_id"] = reference_id
            variants = variants.copy()
            variants["__oat_reference_id"] = reference_id
            outputs.extend([variants, pd.DataFrame([baseline])])
        else:
            if len(embedded) != 1:
                raise ValueError("Die Basisstufe ist mehrfach gespeichert; genau eine Referenz auswählen.")
            baseline = embedded.iloc[0]
            # A quantity table explicitly labels the unchanged factor 1 as a
            # quantity row. Its source identity is retained, never duplicated.
            if not all(_reference_matches(variant, baseline, parameter, input_cache) for _, variant in variants.iterrows()):
                raise ValueError("Eine vorhandene Basisstufe ist nicht an den eigenen Basisvertrag gebunden.")
            variants = variants.copy()
            variants["__oat_reference_id"] = _case_id(baseline)
            variants.loc[variants.__plot_x.eq(base_x), "__oat_is_baseline"] = True
            outputs.append(variants)
    prepared = pd.concat(outputs, ignore_index=True)
    if parameter == "h2_demand_multiplier" or (not presentation["relative"] and parameter in {"real_wacc_shift_fraction", "uniform_real_wacc_fraction"}):
        prepared["__plot_x"] *= 100
    for _, group in prepared.groupby(group_columns, dropna=False):
        if group.__plot_x.duplicated().any():
            raise ValueError("Mehrere Versuchspunkte besitzen dieselbe Parameterstufe.")
    if not prepared.__plot_x.map(math.isfinite).all():
        raise ValueError("Die Sensitivitätsachse enthält nicht endliche Werte.")
    if metric is not None:
        if metric not in prepared or not pd.to_numeric(prepared[metric], errors="raise").map(math.isfinite).all():
            raise ValueError("Die gewählte Ergebnisgröße ist nicht für alle dargestellten Fälle bewertet.")
    prepared = prepared.sort_values([*group_columns, "__plot_x"], kind="stable").reset_index(drop=True)
    prepared.attrs.update(xlabel=presentation["xlabel"], note=presentation["note"], group_columns=group_columns,
        parameter_label=presentation["label"], operation=presentation["operation"], oat_parameter=parameter)
    return prepared


def _comparison_key(row):
    fields = ("study_id", "site_id", "demand_profile", "solver_name", "__native_input_sha256",
        "__native_configuration_sha256", "__native_calendar_sha256", "__native_software_sha256")
    if not all(_present(row.get(c)) for c in fields):
        return None
    return tuple(str(row[c]) for c in fields)


def controlled_scenario_defaults(frame):
    """Prefer one proven complete S0/S1/S2 group, otherwise one concrete case."""
    groups = {}
    for _, row in frame.iterrows():
        key = _comparison_key(row)
        if key is not None and _bound_validated(row):
            groups.setdefault(key, {}).setdefault(str(row.get("scenario_id")), []).append(row)
    for key in sorted(groups):
        group = groups[key]
        if all(s in group and len(group[s]) == 1 for s in ("S0", "S1", "S2")):
            return [_case_id(group[s][0]) for s in ("S0", "S1", "S2")]
    return [_case_id(frame.iloc[0])] if not frame.empty else []


def _bound_validated(row):
    if row.get("__bound_validation_passed") is True:
        return True
    try:
        copies = json.loads(row.get("__result_copies", "[]"))
    except (TypeError, ValueError):
        return False
    selected = row.get("__result_directory")
    return any(copy.get("__result_directory") == selected and copy.get("validation_evidence", {}).get("status") == "passed"
        and copy.get("validation_evidence", {}).get("covers_selected_result") is True
        and copy.get("validation_evidence", {}).get("source_comparison_hash_matches") is True for copy in copies)


def comparison_design(frame):
    keys = [_comparison_key(row) for _, row in frame.iterrows()]
    if len(frame) > 1 and None not in keys and len(set(keys)) == 1 and frame.scenario_id.nunique() == len(frame):
        row = frame.iloc[0]
        return f"Kontrollierter Szenarienvergleich: {', '.join(frame.scenario_id.astype(str))}; Standort {row.site_id}, Profil {row.demand_profile}, Nachfrage, Daten, Basisparameter und Solver {row.solver_name} bleiben gleich."
    differences = [label for field, label in (("site_id", "Standort"), ("demand_profile", "Lieferprofil"),
        ("scenario_id", "Szenario"), ("solver_name", "Solver"), ("annual_h2_delivered_kg", "Jahresmenge"),
        ("sensitivity_parameter", "Parameterfamilie")) if field in frame and frame[field].astype(str).nunique() > 1]
    suffix = " Unterschiede: " + ", ".join(differences) + "." if differences else ""
    return "Deskriptive Fallgegenüberstellung; ein kontrollierter Vergleich ist nicht durch vollständige gemeinsame Verträge belegt." + suffix


__all__ = ["prepare_oat_frame", "parameter_presentation", "native_contract_fields", "controlled_scenario_defaults", "comparison_design"]
