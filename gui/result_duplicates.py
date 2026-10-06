"""Conservative display grouping of saved native exports; never runs a model.

Every output row keeps a representative's original fields and a JSON list of
all source rows. Files, job states and validation reports are never modified.
Missing evidence permits only grouping references to the same physical export.
The optional validation_lookup callback accepts one absolute result path and
returns that path's bound validation evidence dictionary.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable
import csv
import hashlib
import json
import math
import re

import pandas as pd


_SHA256 = re.compile(r"[0-9a-f]{64}\Z", re.IGNORECASE)
_SCENARIOS = {"reference": "S0", "red_monthly": "S1", "red_hourly": "S2", "off_grid": "S3"}
_SUMMARY_REQUIRED = {
    "scenario", "input_sha256", "solver_name", "solver_status",
    "objective_eur_per_year", "lcoh_eur_per_kg_h2", "annual_h2_delivered_kg",
    "pv_capacity_mw", "wind_capacity_mw", "electrolyzer_capacity_mw",
    "compressor_capacity_mw", "h2_storage_capacity_kg",
}
_ADDED_FIELDS = {
    "__analysis_id", "__execution_count", "__source_count", "__result_copies",
    "__collection_id", "__collection_execution_count", "validation_evidence", "native_metadata",
}
_DATA_ERRORS = (OSError, UnicodeError, json.JSONDecodeError, csv.Error, ValueError, KeyError)


def _json_value(value: Any) -> Any:
    """Serialize row scalars without NaN or pandas/numpy scalar objects."""
    if value is None or value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "item"):
        return _json_value(value.item())
    return str(value)


def _canonical(value: Any) -> str:
    return json.dumps(_json_value(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _reject_json_constant(value: str):
    raise ValueError("Non-finite values cannot establish scientific equivalence: " + value)


def _present(value: Any) -> bool:
    return value is not None and value != ""


def _original_rows(frame: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for source in frame.to_dict(orient="records"):
        source = _json_value(source)
        copies = source.get("__result_copies")
        if isinstance(copies, str):
            try:
                decoded = json.loads(copies)
            except json.JSONDecodeError:
                decoded = None
            if isinstance(decoded, list) and decoded and all(isinstance(item, dict) for item in decoded):
                rows.extend({key: value for key, value in item.items() if key not in _ADDED_FIELDS} for item in decoded)
                continue
        rows.append({key: value for key, value in source.items() if key not in _ADDED_FIELDS})
    return rows


def _scientific_input(original: dict[str, Any]) -> dict[str, Any]:
    """Remove only receipts that vary when the same input is copied for a job."""
    value = json.loads(_canonical(original))
    value.pop("source_path", None)
    receipt = value.get("emission_factor_metadata")
    if isinstance(receipt, dict):
        # Generated sidecars embed execution paths. Their scientific content is
        # recorded by emission_factor_sources and the native input/context.
        receipt.pop("source_path", None)
        receipt.pop("sha256", None)
        if not receipt:
            value.pop("emission_factor_metadata", None)
    site = value.get("eu_site_configuration")
    if isinstance(site, dict):
        site.pop("design_path", None)
    provenance = value.get("sensitivity_provenance")
    if isinstance(provenance, dict):
        for name in ("parent_input", "baseline_configuration"):
            receipt = provenance.get(name)
            if isinstance(receipt, dict):
                receipt.pop("path", None)
                receipt.pop("metadata_path", None)
        transformation = provenance.get("case_transformation")
        if isinstance(transformation, dict):
            transformation.pop("case_id", None)
    return value


def _bound_validation(evidence: dict[str, Any]) -> bool:
    return (
        evidence.get("status") == "passed"
        and evidence.get("covers_selected_result") is True
        and evidence.get("source_comparison_hash_matches") is True
    )


class _Evidence:
    """All read/hash/report caches are scoped to one public API invocation."""

    def __init__(self, repo_root: str | Path, validation_lookup: Callable | None):
        self.root = Path(repo_root).resolve()
        self.outputs = (self.root / "outputs_h2").resolve()
        self.validation_lookup = validation_lookup
        self.hashes: dict[Path, str] = {}
        self.jsons: dict[Path, dict[str, Any]] = {}
        self.native: dict[Path, dict[str, Any] | None] = {}
        self.reports: dict[Path, dict[str, Any]] = {}

    def result_path(self, row: dict[str, Any]) -> Path | None:
        for field in ("__result_directory", "result_directory", "resolved_result_directory"):
            raw = row.get(field)
            if not isinstance(raw, str) or not raw:
                continue
            try:
                path = Path(raw)
                path = (path if path.is_absolute() else self.root / path).resolve()
            except (OSError, ValueError):
                return None
            if not path.is_relative_to(self.outputs):
                return None
            return path
        return None

    def file_hash(self, path: Path) -> str:
        if path not in self.hashes:
            with path.open("rb") as handle:
                self.hashes[path] = hashlib.file_digest(handle, "sha256").hexdigest()
        return self.hashes[path]

    def read_json(self, path: Path) -> dict[str, Any]:
        if path not in self.jsons:
            value = json.loads(path.read_text(encoding="utf-8-sig"), parse_constant=_reject_json_constant)
            if not isinstance(value, dict):
                raise ValueError("Native JSON evidence must be an object.")
            self.jsons[path] = value
        return self.jsons[path]

    def validation(self, path: Path | None) -> dict[str, Any]:
        if path is None or self.validation_lookup is None:
            return {}
        if path not in self.reports:
            try:
                value = self.validation_lookup(str(path))
                self.reports[path] = _json_value(value) if isinstance(value, dict) else {}
            except _DATA_ERRORS:
                self.reports[path] = {}
        return self.reports[path]

    def _gui_code(self, directory: Path) -> dict[str, str] | None:
        jobs_root = self.outputs / "gui_runs"
        if not directory.is_relative_to(jobs_root):
            return None
        relative = directory.relative_to(jobs_root)
        if len(relative.parts) < 2:
            raise ValueError("Native result is not within a GUI job.")
        job = jobs_root / relative.parts[0]
        plan_path = job / "plan.json"
        expected = (job / "plan.sha256").read_text(encoding="ascii").strip()
        if not _SHA256.fullmatch(expected) or self.file_hash(plan_path) != expected:
            raise ValueError("GUI plan receipt no longer matches its file.")
        plan = self.read_json(plan_path)
        matches = []
        for execution in plan.get("execution_plans", []):
            if not isinstance(execution, dict) or not isinstance(execution.get("output_directory"), str):
                continue
            output = Path(execution["output_directory"]).resolve()
            if output.is_relative_to(job) and directory.is_relative_to(output):
                matches.append(execution)
        if len(matches) != 1:
            raise ValueError("No unique frozen execution plan covers this result.")
        codes = matches[0].get("code_sha256")
        if not isinstance(codes, dict) or not codes or any(
            not isinstance(name, str) or not isinstance(digest, str) or not _SHA256.fullmatch(digest)
            for name, digest in codes.items()
        ):
            raise ValueError("Frozen model code evidence is incomplete.")
        return codes

    def native_evidence(self, directory: Path) -> dict[str, Any] | None:
        if directory in self.native:
            return self.native[directory]
        try:
            required = [directory / name for name in ("summary.csv", "run_metadata.json", "hourly_operation.csv", "validated_input.csv")]
            if not all(path.is_file() and path.resolve().is_relative_to(self.outputs) for path in required):
                raise ValueError("Native four-file evidence is incomplete.")
            with required[0].open(encoding="utf-8-sig", newline="") as handle:
                summaries = list(csv.DictReader(handle))
            if len(summaries) != 1:
                raise ValueError("Grouping requires one exact native scenario result.")
            summary = summaries[0]
            if not _SUMMARY_REQUIRED.issubset(summary) or any(not _present(summary[key]) for key in _SUMMARY_REQUIRED):
                raise ValueError("Native scientific summary is incomplete.")
            if None in summary or any(
                not math.isfinite(float(summary[key]))
                for key in _SUMMARY_REQUIRED - {"scenario", "input_sha256", "solver_name", "solver_status"}
            ):
                raise ValueError("Native scientific summary contains missing or non-finite results.")
            metadata = self.read_json(required[1])
            for key in ("input", "model_parameters", "calendar_scope", "model_calendar", "software", "result"):
                if not isinstance(metadata.get(key), dict) or not metadata[key]:
                    raise ValueError("Native scientific metadata is incomplete.")
            raw_input = metadata["input"]
            result = metadata["result"]
            input_hash = raw_input.get("sha256")
            if not isinstance(input_hash, str) or not _SHA256.fullmatch(input_hash):
                raise ValueError("Native input hash is absent.")
            if summary["input_sha256"] != input_hash or summary["scenario"] != metadata.get("scenario"):
                raise ValueError("Native summary and metadata disagree.")
            if summary["solver_status"] != "optimal" or result.get("solver_status") != "optimal":
                raise ValueError("Only saved optimal native results can be grouped across directories.")
            if summary["solver_name"] != result.get("solver_name"):
                raise ValueError("Native solver evidence disagrees.")
            for name in ("objective_eur_per_year", "lcoh_eur_per_kg_h2"):
                left, right = float(summary[name]), float(result[name])
                if not math.isfinite(left) or not math.isfinite(right) or left != right:
                    raise ValueError("Native scientific result evidence disagrees.")
            scientific_summary = {key: value for key, value in summary.items() if key not in ("input_file", "solver_runtime_seconds")}
            scientific_result = {key: value for key, value in result.items() if key != "solver_runtime_seconds"}
            science = {
                "schema_version": metadata.get("schema_version"),
                "scenario": metadata["scenario"], "input": _scientific_input(raw_input),
                "model_parameters": metadata["model_parameters"],
                "calendar_scope": metadata["calendar_scope"], "model_calendar": metadata["model_calendar"],
                "software": metadata["software"], "result": scientific_result, "summary": scientific_summary,
                "hourly_operation_sha256": self.file_hash(required[2]),
                "validated_input_sha256": self.file_hash(required[3]),
            }
            code = self._gui_code(directory)
            if code is not None:
                science["gui_model_code_sha256"] = code
            value = {"science": science, "metadata": metadata,
                     "metadata_receipt": {"path": str(required[1]), "sha256": self.file_hash(required[1])}}
        except _DATA_ERRORS + (TypeError,):
            value = None
        self.native[directory] = value
        return value

    def fingerprint(self, row: dict[str, Any], path: Path | None) -> str | None:
        if path is None:
            return None
        native = self.native_evidence(path)
        if native is None:
            return None
        profile = row.get("profile") or row.get("demand_profile")
        identity = {"study_id": row.get("study_id"), "site_id": row.get("site_id"),
                    "profile": profile, "scenario_id": row.get("scenario_id")}
        if not all(_present(value) for value in identity.values()):
            return None
        scenario = native["metadata"]["scenario"]
        if identity["scenario_id"] != _SCENARIOS.get(scenario, scenario):
            return None
        declared_solver = row.get("solver_name")
        if _present(declared_solver) and declared_solver != native["science"]["summary"]["solver_name"]:
            return None
        identity["variant"] = _variant_identity(row)
        identity["years"] = _physical_identity(row)["years"]
        return _digest({"identity": identity, "native": native["science"]})

    def rank(self, row: dict[str, Any]) -> tuple:
        path = self.result_path(row)
        evidence = self.validation(path)
        native = self.native_evidence(path) if path is not None else None
        timestamp = str(native["metadata"].get("created_at_utc", "")) if native else ""
        complete_gui = row.get("gui_job_state") == "completed" and row.get("gui_validation_status") == "passed"
        return (_bound_validation(evidence), complete_gui, timestamp, _canonical(row))

    def provenance(self, row: dict[str, Any]) -> dict[str, Any]:
        copy = dict(row)
        path = self.result_path(row)
        if path is not None:
            copy["__result_directory"] = str(path)
        copy["validation_evidence"] = self.validation(path)
        native = self.native_evidence(path) if path is not None else None
        if native is not None:
            copy["native_metadata"] = native["metadata_receipt"]
        elif path is not None:
            metadata_path = path / "run_metadata.json"
            try:
                if metadata_path.is_file() and metadata_path.resolve().is_relative_to(self.outputs):
                    copy["native_metadata"] = {"path": str(metadata_path), "sha256": self.file_hash(metadata_path)}
            except (OSError, ValueError):
                pass
        return copy


def _physical_identity(row: dict[str, Any]) -> dict[str, Any]:
    """A shared comparison folder can contain several distinct saved cases."""
    identity = {
        "study_id": row.get("study_id"), "site_id": row.get("site_id"),
        "profile": row.get("profile") or row.get("demand_profile"),
        "scenario": row.get("scenario_id") or row.get("scenario"),
        "solver": row.get("solver_name"), "variant": _variant_identity(row),
    }
    identity["years"] = {
        key: value for key, value in row.items()
        if (key.endswith("_year") or key.endswith("_reference_year")) and _present(value)
    }
    return identity


def _physical_groups(rows: list[dict[str, Any]], evidence: _Evidence, *, variants: bool = False) -> list[list[dict[str, Any]]]:
    grouped = defaultdict(list)
    for index, row in enumerate(rows):
        path = evidence.result_path(row)
        key = ("path", str(path), _canonical(_physical_identity(row))) if path is not None else ("missing", _digest(row), index)
        if variants:
            key += (_canonical(_variant_identity(row)),)
        grouped[key].append(row)
    return list(grouped.values())


def _group_key(rows: list[dict[str, Any]], evidence: _Evidence) -> tuple[str, str]:
    signatures = {evidence.fingerprint(row, evidence.result_path(row)) for row in rows}
    if len(signatures) == 1 and None not in signatures:
        return "semantic", next(iter(signatures))
    path = evidence.result_path(rows[0])
    return ("physical", _digest((str(path), _physical_identity(rows[0])))) if path is not None else ("missing", _digest(rows[0]))


def _source_identity(row: dict[str, Any], evidence: _Evidence) -> tuple:
    source = row.get("__source_csv")
    if isinstance(source, str) and source:
        path = Path(source)
        source = str((path if path.is_absolute() else evidence.root / path).resolve())
        return ("csv", source, row.get("__source_csv_sha256"))
    return ("unrecorded", row.get("__collection"), row.get("gui_job_id"), str(evidence.result_path(row)))


def _make_row(rows: list[dict[str, Any]], analysis_id: str, evidence: _Evidence) -> dict[str, Any]:
    representative = max(rows, key=evidence.rank)
    output = dict(representative)
    copies = sorted((evidence.provenance(row) for row in rows), key=_canonical)
    output.update(
        __analysis_id=analysis_id,
        __execution_count=len({str(path) for row in rows if (path := evidence.result_path(row)) is not None}),
        __source_count=len({_source_identity(row, evidence) for row in rows}),
        __result_copies=_canonical(copies),
    )
    return output


def collapse_duplicate_results(frame: pd.DataFrame, repo_root: str | Path, validation_lookup=None) -> pd.DataFrame:
    """Return unique saved basis cases, retaining every source row as JSON.

    Semantic IDs omit representative paths and discovery order. Where evidence
    is incomplete, an ID describes the one physical export directory instead.
    No different directories are combined without complete matching evidence.
    """
    if frame.empty:
        return frame.copy()
    evidence = _Evidence(repo_root, validation_lookup)
    groups = defaultdict(list)
    missing_counts = defaultdict(int)
    for physical in _physical_groups(_original_rows(frame), evidence):
        key = _group_key(physical, evidence)
        if key[0] == "missing":
            missing_counts[key] += 1
            key = key + (missing_counts[key],)
        groups[key].extend(physical)
    outputs = [_make_row(rows, "result:" + _digest(key), evidence) for key, rows in groups.items()]
    return pd.DataFrame(sorted(outputs, key=lambda row: row["__analysis_id"])).reset_index(drop=True)


def _variant_identity(row: dict[str, Any]) -> dict[str, Any]:
    parameter = row.get("sensitivity_parameter") or row.get("parameter")
    value = row.get("value")
    if isinstance(value, str) and value:
        try:
            numeric = float(value)
            if math.isfinite(numeric):
                value = numeric
        except ValueError:
            pass
    return {"parameter": parameter, "value": value, "unit": row.get("unit"), "level": row.get("level")}


def _collection_key(row: dict[str, Any], evidence: _Evidence) -> tuple:
    family = row.get("__gui_oat_family_id")
    if isinstance(family, str) and family:
        # New GUI OAT jobs explicitly define a family across several native
        # profile CSVs. Their complete multiset, not each child separately,
        # is the unit of equivalence. Every row retains its own source receipt.
        return (row.get("__collection") or row.get("source_label"),
                ("gui_oat_family", family), row.get("gui_job_id"))
    return (row.get("__collection") or row.get("source_label"), _source_identity(row, evidence), row.get("gui_job_id"))


def collapse_duplicate_sensitivity_collections(frame: pd.DataFrame, repo_root: str | Path, validation_lookup=None) -> pd.DataFrame:
    """Fold only complete equal variant multisets, preserving curve families.

    A partially overlapping collection remains a separate complete collection.
    __collection is the deterministic representative label; __collection_id is
    independent of that label and original rows retain every collection alias.
    __collection_execution_count counts distinct physical variant-set exports.
    """
    if frame.empty:
        return frame.copy()
    evidence = _Evidence(repo_root, validation_lookup)
    collections = defaultdict(list)
    for row in _original_rows(frame):
        collections[_collection_key(row, evidence)].append(row)
    families = defaultdict(list)
    for original_key, rows in collections.items():
        entries = []
        for physical in _physical_groups(rows, evidence, variants=True):
            representative = max(physical, key=evidence.rank)
            signature = _group_key(physical, evidence)
            entry = (_canonical((signature, _variant_identity(representative))), physical)
            entries.append(entry)
        entries.sort(key=lambda item: (item[0], str(evidence.result_path(item[1][0])), _canonical(item[1])))
        semantic = all(_group_key(physical, evidence)[0] == "semantic" for _, physical in entries)
        multiset = sorted(label for label, _ in entries)
        # Complete shared physical sets also establish collection equivalence;
        # mixed/incomplete different directories cannot match this fingerprint.
        family_key = ("semantic" if semantic else "physical", _digest(multiset))
        families[family_key].append((original_key, entries))
    outputs = []
    for family_key, members in families.items():
        collection_id = "collection:" + _digest(family_key)
        def collection_rank(member):
            rows = [row for _, physical in member[1] for row in physical]
            ranks = [evidence.rank(row) for row in rows]
            return (all(rank[0] for rank in ranks), sum(rank[0] for rank in ranks), max(ranks), _canonical(member[0]))
        representative_collection = max(members, key=collection_rank)
        label = representative_collection[0][0]
        export_sets = {
            tuple(sorted(str(evidence.result_path(physical[0])) for _, physical in entries))
            for _, entries in members
        }
        for index in range(len(representative_collection[1])):
            copies = [row for _, entries in members for row in entries[index][1]]
            entry_label = representative_collection[1][index][0]
            output = _make_row(copies, "result:" + _digest((collection_id, entry_label, index)), evidence)
            output["__collection"] = label
            output["__collection_id"] = collection_id
            output["__collection_execution_count"] = len(export_sets)
            outputs.append(output)
    return pd.DataFrame(sorted(outputs, key=lambda row: (row["__collection_id"], row["__analysis_id"]))).reset_index(drop=True)
