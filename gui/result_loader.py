"""Read native H2 exports, provenance and validator reports without any solver import."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd

from .case_study_registry import Registry, SiteConfiguration, ResultReference, contained_path, file_sha256, read_json, extract_year_roles
from .result_duplicates import collapse_duplicate_results, collapse_duplicate_sensitivity_collections

NATIVE_TO_ID = {"reference": "S0", "red_monthly": "S1", "red_hourly": "S2", "off_grid": "S3"}


@dataclass
class ResultBundle:
    summary: pd.DataFrame
    metadata: dict[str, Any]
    hourly: dict[str, pd.DataFrame] = field(default_factory=dict)
    validation: dict[str, Any] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)

    def derived_operational_metrics(self) -> pd.DataFrame:
        return derived_operational_metrics(self)


def _output_path(root, path, *, must_exist=False):
    p = contained_path(root, path, must_exist=must_exist)
    output_root = contained_path(root, "outputs_h2")
    if not p.is_relative_to(output_root):
        raise ValueError("Ergebnisse dürfen nur aus outputs_h2 geladen werden.")
    return p


def _scenario_ids(frame):
    frame = frame.copy()
    if "scenario_id" not in frame:
        if "scenario" in frame:
            frame["scenario_id"] = frame["scenario"].map(NATIVE_TO_ID).fillna(frame["scenario"])
        else:
            frame["scenario_id"] = [f"Fall {i+1}" for i in range(len(frame))]
    return frame


def _result_paths(frame, csv_path, root):
    paths = []
    for _, row in frame.iterrows():
        if pd.notna(row.get("source_result_directory")):
            path = contained_path(root, str(row["source_result_directory"]))
        elif pd.notna(row.get("result_directory")):
            supplied = Path(str(row["result_directory"]))
            path = contained_path(root, supplied if supplied.is_absolute() else csv_path.parent / supplied)
        else:
            path = csv_path.parent
        paths.append(str(_output_path(root, path)))
    frame = frame.copy()
    frame["__result_directory"] = paths
    return frame


def _fill_missing_native_summaries(frame: pd.DataFrame, root: Path) -> pd.DataFrame:
    """Fill absent cells from the exact saved case; preserve existing values.

    Condensed analysis tables can omit solver diagnostics and temporal flags.
    Only a unique scenario/input-matched native summary and its scalar result
    metadata are used. Empty native values remain empty; no values are derived.
    """
    frame = frame.reset_index(drop=True).copy()
    if frame.empty or "__result_directory" not in frame:
        return frame
    cached = {}
    for index, row in frame.iterrows():
        try:
            directory = _output_path(root, str(row["__result_directory"]), must_exist=True)
            if directory not in cached:
                summary_path = directory / "summary.csv"
                summary = _scenario_ids(pd.read_csv(summary_path)) if summary_path.is_file() else pd.DataFrame()
                metadata_path = directory / "run_metadata.json"
                metadata = read_json(metadata_path) if metadata_path.is_file() else {}
                cached[directory] = (summary_path, summary, metadata_path, metadata)
            summary_path, native, metadata_path, metadata = cached[directory]
            if len(native) != 1:
                continue
            native_row = native.iloc[0]
            if pd.notna(row.get("scenario_id")) and str(row.scenario_id) != str(native_row.scenario_id):
                continue
            if pd.notna(row.get("input_sha256")) and pd.notna(native_row.get("input_sha256")) and row.input_sha256 != native_row.input_sha256:
                continue
            candidates = dict(native_row)
            # JSON result fields are a fallback for old condensed CSV exports.
            # Nested structures/model parameters are deliberately not flattened.
            for field_name, value in metadata.get("result", {}).items():
                if isinstance(value, (str, int, float, bool)) and (field_name not in candidates or pd.isna(candidates[field_name])):
                    candidates[field_name] = value
            filled = []
            for field_name, value in candidates.items():
                if field_name.startswith("__") or pd.isna(value):
                    continue
                if field_name in frame and pd.notna(frame.at[index, field_name]):
                    continue
                if field_name not in frame:
                    frame[field_name] = np.nan if isinstance(value, (int, float, np.number)) and not isinstance(value, (bool, np.bool_)) else None
                elif isinstance(value, (str, bool)) and frame[field_name].dtype.kind not in "OUSb":
                    frame[field_name] = frame[field_name].astype(object)
                frame.at[index, field_name] = value
                filled.append(field_name)
            frame.at[index, "__native_summary_path"] = str(summary_path)
            frame.at[index, "__native_summary_sha256"] = file_sha256(summary_path)
            if metadata_path.is_file():
                frame.at[index, "__native_metadata_path"] = str(metadata_path)
                frame.at[index, "__native_metadata_sha256"] = file_sha256(metadata_path)
            frame.at[index, "__native_filled_fields"] = ", ".join(filled)
        except (ValueError, KeyError, FileNotFoundError):
            # Missing/in-progress/unsafe or mismatched sources remain unavailable.
            continue
    return frame.infer_objects()


def _read_registered_reference(registry, ref: ResultReference, site: SiteConfiguration):
    if not ref.path.is_file():
        if ref.optional:
            return pd.DataFrame()
        raise FileNotFoundError(f"Registrierte Ergebnisdatei fehlt: {ref.path}")
    csv = _output_path(registry.repo_root, ref.path, must_exist=True)
    frame = _scenario_ids(pd.read_csv(csv))
    if "site_id" in frame:
        frame = frame.loc[frame.site_id == site.site_id].copy()
    else:
        frame["site_id"] = site.site_id
    if "demand_profile" not in frame:
        frame["demand_profile"] = ref.profile or next(iter(site.profiles), None)
    if ref.exclude_profiles:
        frame = frame.loc[~frame.demand_profile.isin(ref.exclude_profiles)].copy()
    frame["study_id"] = site.study_id
    frame["site_label"] = site.label
    frame["historical_case_study"] = site.historical
    frame["__collection"] = ref.label
    frame["__source_csv"] = str(csv)
    frame["__source_csv_sha256"] = file_sha256(csv)
    frame["source_label"] = ref.label
    frame["profile"] = frame["demand_profile"]
    if "sensitivity_parameter" not in frame and "parameter" in frame:
        frame["sensitivity_parameter"] = frame["parameter"]
    if "parameter" not in frame and "sensitivity_parameter" in frame:
        frame["parameter"] = frame["sensitivity_parameter"]
    frame = _result_paths(frame, csv, registry.repo_root)
    return _fill_missing_native_summaries(frame, registry.repo_root)


def _gui_job_tables(registry: Registry, site: SiteConfiguration, *, sensitivity: bool) -> list[pd.DataFrame]:
    """Discover only persisted GUI jobs for this exact study/site selection."""
    root = registry.repo_root
    jobs_root = _output_path(root, "outputs_h2/gui_runs")
    if not jobs_root.is_dir():
        return []
    frames = []
    for job in sorted(jobs_root.iterdir(), reverse=True):
        if not job.is_dir() or not (job / "plan.json").is_file():
            continue
        try:
            plan_path = _output_path(root, job / "plan.json", must_exist=True)
            expected_path = job / "plan.sha256"
            if not expected_path.is_file() or file_sha256(plan_path) != expected_path.read_text(encoding="ascii").strip():
                continue
            record = read_json(plan_path)
            status = read_json(job / "status.json") if (job / "status.json").is_file() else {}
            state = status.get("state", "unknown")
            for execution in record.get("execution_plans", []):
                if execution.get("study_id") != site.study_id or execution.get("site_id") != site.site_id:
                    continue
                profile = execution.get("profile_id")
                if profile not in site.profiles:
                    continue
                requested_design = record.get("requested_plan", {}).get("gui_oat_design")
                execution_design = execution.get("gui_oat_design")
                # Explicit new OAT experiments retain their own baselines for
                # both numeric curves and categorical profile comparisons.
                # Older cost-only discovery semantics remain unchanged.
                new_oat = isinstance(requested_design, dict) or isinstance(execution_design, dict)
                out = _output_path(root, execution["output_directory"])
                csv = out / "sensitivity_comparison.csv"
                tables = []
                if csv.is_file():
                    table = _result_paths(_scenario_ids(pd.read_csv(csv)), csv, root)
                    if "case_id" in table:
                        if sensitivity:
                            parameter_field="sensitivity_parameter" if "sensitivity_parameter" in table else "parameter" if "parameter" in table else None
                            # Demand curves include the native 100 % case. It
                            # must come from this same GUI execution/profile,
                            # rather than a separately registered baseline.
                            has_quantity=parameter_field is not None and table[parameter_field].eq("h2_demand_multiplier").any()
                            if not has_quantity and not new_oat:table=table.loc[table.case_id != "baseline"].copy()
                        else:
                            table=table.loc[table.case_id == "baseline"].copy()
                    elif sensitivity:
                        continue
                    tables.append((table,csv))
                elif (not sensitivity or new_oat) and out.is_dir():
                    # Failed/in-progress jobs can still have saved optimal
                    # native cases. These remain visibly partial/unaccepted.
                    for summary in (out / "runs/baseline").glob("*/summary.csv"):
                        table = _result_paths(_scenario_ids(pd.read_csv(summary)),summary,root)
                        table["case_id"] = "baseline"
                        tables.append((table,summary))
                for table, source_csv in tables:
                    if table.empty:
                        continue
                    table = _fill_missing_native_summaries(table, root)
                    if "solver_status" in table:
                        table = table.loc[table.solver_status == "optimal"].copy()
                    if table.empty:
                        continue
                    label = f"GUI {job.name} · {state}"
                    if state != "completed" or status.get("validation_status") != "passed":
                        label += " · teilweise / nicht vollständig validiert"
                    table["study_id"], table["site_id"], table["site_label"] = site.study_id,site.site_id,site.label
                    table["demand_profile"], table["profile"] = profile,profile
                    table["historical_case_study"] = site.historical
                    table["__collection"], table["source_label"] = label,label
                    table["__source_csv"], table["__source_csv_sha256"] = str(source_csv),file_sha256(source_csv)
                    table["gui_job_state"], table["gui_validation_status"] = state,status.get("validation_status","not_run")
                    table["gui_job_id"] = job.name
                    table["gui_job_plan_sha256"] = file_sha256(plan_path)
                    if sensitivity and new_oat:
                        # One explicitly composed GUI experiment is one saved
                        # family across its child profile CSVs. Native source
                        # bindings remain separate on every original row.
                        table["__gui_oat_family_id"] = job.name + ":" + file_sha256(plan_path)
                    if "sensitivity_parameter" not in table and "parameter" in table:
                        table["sensitivity_parameter"] = table["parameter"]
                    if sensitivity and new_oat and "sensitivity_parameter" not in table:
                        table["sensitivity_parameter"] = "baseline"
                        table["parameter"] = "baseline"
                    frames.append(table.reset_index(drop=True))
        except (ValueError,KeyError,FileNotFoundError,pd.errors.EmptyDataError,pd.errors.ParserError):
            # In-progress partial writes, missing files or an unsafe registry
            # reference cannot be represented as a successful result.
            continue
    return frames


def load_registered_results(registry: Registry, study_id: str, site_id: str, profile: str | None = None) -> pd.DataFrame:
    site = registry.get_site(study_id, site_id)
    frames = [_read_registered_reference(registry, ref, site) for ref in site.result_sources]
    frames.extend(_gui_job_tables(registry,site,sensitivity=False))
    frames = [f for f in frames if not f.empty]
    if not frames:
        return pd.DataFrame()
    results = pd.concat(frames, ignore_index=True)
    if profile is not None:
        if profile not in site.profiles:
            raise ValueError(f"Unbekanntes Nachfrageprofil: {profile}")
        results = results.loc[results.demand_profile == profile].copy()
    return collapse_duplicate_results(results, registry.repo_root,
        validation_lookup=lambda path: validation_for_result(path, registry.repo_root))


def load_sensitivity_comparisons(registry: Registry, study_id: str, site_id: str) -> pd.DataFrame:
    site = registry.get_site(study_id, site_id)
    frames = [_read_registered_reference(registry, ref, site) for ref in site.sensitivity_sources]
    frames.extend(_gui_job_tables(registry,site,sensitivity=True))
    frames = [f for f in frames if not f.empty]
    if not frames:
        return pd.DataFrame()
    return collapse_duplicate_sensitivity_collections(pd.concat(frames, ignore_index=True), registry.repo_root,
        validation_lookup=lambda path: validation_for_result(path, registry.repo_root))


def load_job_results(job_dir: str | Path, repo_root: str | Path) -> pd.DataFrame:
    """Read only the selected persisted job, including its numeric OAT variants.

    The plan hash and each native comparison source are bound to the returned
    rows. Partial jobs remain partial; their global status never replaces the
    independent report for a particular native result. Reading starts no process.
    """
    root = Path(repo_root).resolve()
    job = _output_path(root, job_dir, must_exist=True)
    jobs_root = _output_path(root, "outputs_h2/gui_runs")
    if not job.is_relative_to(jobs_root) or job == jobs_root:
        raise ValueError("Der gewählte Auftrag muss unter outputs_h2/gui_runs liegen.")
    plan_path = _output_path(root, job / "plan.json", must_exist=True)
    expected_path = job / "plan.sha256"
    if not expected_path.is_file() or file_sha256(plan_path) != expected_path.read_text(encoding="ascii").strip():
        raise ValueError("Der gespeicherte GUI-Auftrag ist nicht an seinen Plan-Hash gebunden.")
    record = read_json(plan_path)
    status = read_json(job / "status.json") if (job / "status.json").is_file() else {}
    state = status.get("state", "unknown")
    label = f"GUI {job.name} · {state}"
    if state != "completed" or status.get("validation_status") != "passed":
        label += " · teilweise / nicht vollständig validiert"
    frames = []
    for execution in record.get("execution_plans", []):
        out = _output_path(root, execution["output_directory"])
        if not out.is_relative_to(job):
            raise ValueError("Die Ergebnisablage gehört nicht zum ausgewählten GUI-Auftrag.")
        tables = []
        for filename in ("sensitivity_comparison.csv", "scenario_comparison.csv"):
            csv = out / filename
            if csv.is_file():
                tables = [(_result_paths(_scenario_ids(pd.read_csv(csv)), csv, root), csv)]
                break
        if not tables and out.is_dir():
            # A failed worker can already have native optimal exports without
            # its aggregate comparison. Expose those exact files honestly.
            for summary_path in sorted((out / "runs").rglob("summary.csv")):
                table = _result_paths(_scenario_ids(pd.read_csv(summary_path)), summary_path, root)
                table["case_id"] = summary_path.parent.parent.name
                tables.append((table, summary_path))
        for table, source_csv in tables:
            if any(not Path(str(path)).is_relative_to(out) for path in table["__result_directory"]):
                raise ValueError("Ein nativer Ergebnisverweis gehört nicht zur gewählten Auftragsausführung.")
            table = _fill_missing_native_summaries(table, root)
            if "solver_status" in table:
                table = table.loc[table.solver_status == "optimal"].copy()
            if table.empty:
                continue
            context = execution.get("gui_context", {})
            profile = execution.get("profile_id")
            table["study_id"] = execution.get("study_id")
            table["site_id"] = execution.get("site_id")
            table["site_label"] = context.get("site_label", execution.get("site_id"))
            table["profile"], table["demand_profile"] = profile, profile
            table["historical_case_study"] = context.get("historical", execution.get("runner_kind") == "legacy")
            table["__collection"], table["source_label"] = label, label
            table["__source_csv"], table["__source_csv_sha256"] = str(source_csv), file_sha256(source_csv)
            table["gui_job_id"], table["gui_job_state"] = job.name, state
            table["gui_validation_status"] = status.get("validation_status", "not_run")
            table["gui_job_plan_sha256"] = file_sha256(plan_path)
            if "sensitivity_parameter" not in table and "parameter" in table:
                table["sensitivity_parameter"] = table["parameter"]
            if "sensitivity_value" not in table and "value" in table:
                table["sensitivity_value"] = table["value"]
            frames.append(table.reset_index(drop=True))
    if not frames:
        return pd.DataFrame()
    return collapse_duplicate_results(pd.concat(frames, ignore_index=True), root,
        validation_lookup=lambda path: validation_for_result(path, root))


def validation_for_result(path: str | Path, repo_root: str | Path) -> dict[str, Any]:
    selected = _output_path(repo_root, path, must_exist=True)
    if selected.is_file():
        selected = selected.parent
    output_root = contained_path(repo_root, "outputs_h2")
    candidates = []
    for parent in (selected, *selected.parents):
        if not parent.is_relative_to(output_root):
            break
        candidates.extend([parent / "validation/validation_report.json", parent / "validation_report.json"])
    for report_path in candidates:
        if not report_path.is_file():
            continue
        report = read_json(report_path)
        binding = report.get("source_comparison", {})
        try:
            csv_path = _output_path(repo_root, binding["path"], must_exist=True)
            hash_matches = file_sha256(csv_path) == binding.get("sha256")
            comp = _scenario_ids(pd.read_csv(csv_path))
            comp = _result_paths(comp, csv_path, repo_root)
            covered = selected == csv_path.parent or str(selected) in set(comp["__result_directory"])
        except (KeyError, ValueError, FileNotFoundError):
            covered, hash_matches = False, False
        if not covered:
            continue
        return {"status": "passed" if report.get("all_checks_passed") is True and hash_matches else "failed_or_changed",
            "report_path": str(report_path), "report_sha256": file_sha256(report_path),
            "source_comparison_hash_matches": hash_matches, "covers_selected_result": True,
            "report": report,
            "interpretation": "Gespeicherter unabhängiger Prüferbericht mit Vergleichstabellen-Hash; keine neue Prüfung der Stundenexports beim Anzeigen."}
    return {"status": "not_found", "covers_selected_result": False,
        "interpretation": "Kein eindeutig an diesen Ergebnisfall gebundener Prüferbericht gefunden; optimaler Solverstatus ersetzt keinen Validierungsnachweis."}


def _input_hash_check(root, metadata):
    raw = metadata.get("input", {})
    expected = raw.get("sha256")
    declared_path = raw.get("source_path")
    if not declared_path:
        return {"status": "not_recorded", "expected_sha256": expected}
    try:
        path = contained_path(root, declared_path, must_exist=True)
        actual = file_sha256(path)
        return {"path": str(path), "expected_sha256": expected, "actual_sha256": actual,
            "status": "matches" if actual == expected else "mismatch"}
    except (ValueError, FileNotFoundError) as exc:
        return {"path": declared_path, "expected_sha256": expected, "status": "unavailable", "reason": str(exc)}


def load_result_directory(path: str | Path, repo_root: str | Path, include_hourly: bool = False) -> ResultBundle:
    directory = _output_path(repo_root, path, must_exist=True)
    if directory.is_file():
        directory = directory.parent
    comparison = directory / "scenario_comparison.csv"
    single = directory / "summary.csv"
    if comparison.is_file():
        csv_path = comparison
        metadata_path = directory / "scenario_comparison_metadata.json"
    elif single.is_file():
        csv_path = single
        metadata_path = directory / "run_metadata.json"
    else:
        raise FileNotFoundError(f"Keine native Vergleichs-/Ergebnisdatei in {directory}")
    summary = _result_paths(_scenario_ids(pd.read_csv(csv_path)), csv_path, repo_root).reset_index(drop=True)
    metadata = read_json(metadata_path) if metadata_path.is_file() else {}
    hourly, run_metadata, hashes = {}, {}, []
    files = {str(csv_path): file_sha256(csv_path)}
    if metadata_path.is_file():
        files[str(metadata_path)] = file_sha256(metadata_path)
    for _, row in summary.iterrows():
        scenario = str(row["scenario_id"])
        result_dir = _output_path(repo_root, row["__result_directory"], must_exist=True)
        run_path = result_dir / "run_metadata.json"
        run = read_json(run_path) if run_path.is_file() else {}
        run_metadata[scenario] = run
        hashes.append({"scenario_id": scenario, **_input_hash_check(repo_root, run)})
        if run_path.is_file():
            files[str(run_path)] = file_sha256(run_path)
        if include_hourly:
            hourly_path = result_dir / "hourly_operation.csv"
            if not hourly_path.is_file():
                raise FileNotFoundError(f"Stundenexport fehlt: {hourly_path}")
            h = pd.read_csv(hourly_path)
            if "timestamp" not in h:
                raise ValueError(f"Stundenexport enthält keine timestamp-Spalte: {hourly_path}")
            h["timestamp"] = pd.to_datetime(h.timestamp, utc=True, errors="raise")
            if h.timestamp.duplicated().any() or not h.timestamp.is_monotonic_increasing:
                raise ValueError(f"Stundenexport hat keine eindeutige aufsteigende Zeitachse: {hourly_path}")
            hourly[scenario] = h
            files[str(hourly_path)] = file_sha256(hourly_path)
    if comparison.is_file():
        metadata = {"scenario_comparison": metadata, "runs": run_metadata}
    validation = validation_for_result(directory, repo_root)
    provenance = {"source_directory": str(directory), "files_sha256": files,
        "input_hash_checks": hashes, "hashes_checked_without_solver": True}
    return ResultBundle(summary, metadata, hourly, validation, provenance)


def derived_operational_metrics(bundle: ResultBundle) -> pd.DataFrame:
    """Display sums/ratios from saved exports; not a second model calculation."""
    records = []
    for _, row in bundle.summary.iterrows():
        scenario = str(row["scenario_id"])
        h = bundle.hourly.get(scenario)
        values = {"scenario_id": scenario}
        if h is None:
            records.append(values)
            continue
        factor = float(row.get("annualization_factor", 1))
        annual_sums = {
            "annual_grid_import_mwh": ("grid_import_mwh",),
            "annual_direct_renewable_use_mwh": ("pv_self_consumption_mwh", "wind_self_consumption_mwh"),
            "annual_curtailment_mwh": ("pv_curtailment_mwh", "wind_curtailment_mwh"),
            "annual_renewable_surplus_mwh": ("renewable_surplus_mwh",),
            "annual_electrolyzer_electricity_mwh": ("electrolyzer_electricity_mwh",),
            "annual_total_process_electricity_mwh": ("rf_nbo_electricity_mwh",),
        }
        for field, columns in annual_sums.items():
            if all(col in h for col in columns):
                values[field] = float(h[list(columns)].sum().sum())*factor
        capacity = row.get("electrolyzer_capacity_mw")
        if pd.notna(capacity) and float(capacity) > 0 and "annual_electrolyzer_electricity_mwh" in values:
            values["electrolyzer_full_load_hours"] = values["annual_electrolyzer_electricity_mwh"] / float(capacity)
        total = values.get("annual_total_process_electricity_mwh", 0)
        if total > 0 and "annual_direct_renewable_use_mwh" in values:
            values["physical_direct_renewable_share"] = values["annual_direct_renewable_use_mwh"]/total
        if "h2_storage_level_kg" in h:
            values["maximum_storage_inventory_kg"] = float(h.h2_storage_level_kg.max())
        if {"h2_after_compression_kg", "h2_demand_kg"}.issubset(h):
            net_flow = h.h2_after_compression_kg-h.h2_demand_kg
            values["storage_net_inflow_positive_kg_per_year"] = float(net_flow.clip(lower=0).sum())*factor
            values["storage_net_outflow_kg_per_year"] = float((-net_flow.clip(upper=0)).sum())*factor
            values["storage_absolute_net_flow_kg_per_year"] = float(net_flow.abs().sum())*factor
        records.append(values)
    return pd.DataFrame(records)


def describe_case_sources(registry: Registry, study_id: str, site_id: str, profile: str = "D0") -> dict[str, Any]:
    site = registry.get_site(study_id, site_id)
    if profile not in site.profiles:
        raise ValueError(f"Unbekanntes Nachfrageprofil {profile}")
    ref = site.profiles[profile]
    design = site.metadata.get("design", {})
    meta = ref.metadata
    sources = meta.get("sources", {})
    factors = meta.get("emission_factor_sources", {})
    baseline = site.metadata.get("baseline_metadata", {})
    params = baseline.get("model_parameters", {})
    technical = {key: value for key, value in params.items() if "capex" in key or "opex" in key}
    wacc = {key: value for key, value in params.items() if "wacc" in key}
    country = site.metadata.get("site_record", {}).get("country_code", meta.get("site", {}).get("country_code"))
    weather = sources.get("weather") or {**design.get("weather", {}), "sources": {k:v for k,v in design.get("sources", {}).items() if k.startswith("weather_")}}
    price = sources.get("electricity_price") or {**design.get("electricity_cost", {}), "source_url": design.get("sources", {}).get(f"{country}_price"), "market_year": site.year_roles["market_price_year"]}
    return {"study_id": study_id, "site_id": site_id, "label": site.label,
        "year_roles": extract_year_roles({**site.metadata, "input_metadata": meta}),
        "weather": weather, "site_record": site.metadata.get("site_record", {}),
        "electricity_price": price,
        "emission_factors": factors or {"legacy_shared_factor": sources.get("grid_emission_factor", {})},
        "technical_costs": technical, "wacc": wacc or design.get("financing", {}),
        "demand": meta.get("demand_profile") or sources.get("h2_demand") or design.get("hydrogen_demand", {}),
        "input": {"path": str(ref.path), "sha256": file_sha256(ref.path) if ref.path.is_file() else None,
            "metadata_path": str(ref.metadata_path), "metadata_sha256": file_sha256(ref.metadata_path) if ref.metadata_path.is_file() else None},
        "compatibility": site.metadata.get("compatibility", {}),
        "dataflow": {"weather_preparation": "acquire_eu_historical_sources.py → prepare_eu_historical_data.py → prepare_eu_static_inputs.py" if site.runner_kind == "eu" else "prepare_single_site_h2_input.py → calculate_renewable_yield.py",
            "native_runner": "run_single_site_h2.py / run_h2_scenarios.py / run_h2_sensitivity.py",
            "independent_validator": "validate_h2_results.py", "plotters": "plot_h2_results.py / plot_h2_sensitivity.py"}}


def comparison_context(registry: Registry, cases: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    records = []
    for _, row in cases.iterrows():
        site = registry.get_site(str(row.study_id), str(row.site_id))
        case_metadata = site.metadata.get("baseline_metadata", {})
        metadata_path = None
        result_directory = row.get("__result_directory", row.get("result_directory"))
        if pd.notna(result_directory):
            try:
                metadata_path = _output_path(registry.repo_root, Path(str(result_directory)) / "run_metadata.json", must_exist=True)
                case_metadata = read_json(metadata_path)
            except (ValueError, FileNotFoundError):
                metadata_path = None
        params = case_metadata.get("model_parameters", {})
        unit = params.get("study.functional_unit_kg_h2", {}).get("value")
        pressure = params.get("study.delivery_pressure_bar", {}).get("value")
        records.append({"study_id": row.study_id, "site_id": row.site_id, "scenario_id": row.get("scenario_id"),
            "demand_profile": row.get("demand_profile"), "annual_h2_delivered_kg": row.get("annual_h2_delivered_kg"),
            "functional_unit_kg_h2": unit, "delivery_pressure_bar": pressure,
            "solver_name": row.get("solver_name", case_metadata.get("result", {}).get("solver_name")),
            "source_collection": row.get("source_label", row.get("__collection")),
            "result_directory": result_directory,
            "case_metadata_path": str(metadata_path) if metadata_path else None,
            "historical_case": site.historical,
            "model_status": "historical_archived" if site.historical else "current_case_study",
            "metadata_schema_version": case_metadata.get("schema_version"),
            "software_versions": case_metadata.get("software", {}),
            **extract_year_roles({**site.metadata, "baseline_metadata": case_metadata})})
    context = pd.DataFrame(records)
    warnings = []
    if len(context) > 1:
        if context.solver_name.dropna().nunique() > 1:
            warnings.append("Verschiedene Solver sind getrennte Ergebnisfälle. Gleiche Zielfunktionswerte können bei mehreren Optima unterschiedliche Kapazitäten und Stundenlösungen besitzen.")
        keys = ("study_operation_year", "weather_year", "market_price_year", "cost_price_year", "wacc_source_year", "annual_h2_delivered_kg", "delivery_pressure_bar")
        if any(context[key].astype(str).nunique(dropna=False) > 1 for key in keys):
            warnings.append("Diese Fälle besitzen unterschiedliche Untersuchungsjahre oder wirtschaftliche Bezugsbasen. Der Vergleich ist daher nur eingeschränkt interpretierbar.")
        if context.historical_case.any():
            warnings.append("Namibia ist ein historischer TMY-/Preisproxyfall; kein methodisch identischer EU-2024-Fall und kein isolierter kausaler Ländereffekt. Das Preisjahr des 128-EUR/MWh-Proxys ist ungeklärt.")
    return context, warnings


__all__ = ["ResultBundle", "load_result_directory", "load_registered_results", "load_sensitivity_comparisons", "derived_operational_metrics", "describe_case_sources", "validation_for_result", "comparison_context"]
