"""Reference-only registry, separate study/site identities and metadata-derived years."""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from functools import lru_cache
from pathlib import PureWindowsPath
from typing import Any


class RegistryError(ValueError):
    """A registry entry is malformed or points outside the repository."""


@lru_cache(maxsize=4)
def _snapshot_paths(root):
    """Explicit archived path aliases; original scientific files stay byte-identical."""
    manifest=Path(root)/'gui/data_snapshot/manifest.json'
    if not manifest.is_file():return '',set()
    data=read_json(manifest)
    original=str(data.get('source_repository_root','')).replace('\\','/').rstrip('/')
    declared=set()
    for name in data.get('files',{}):
        p=Path(name)
        if p.is_absolute() or '..' in p.parts or PureWindowsPath(name).is_absolute():
            raise RegistryError('Ungültiger Dateipfad im Übergabemanifest.')
        declared.add(name)
        declared.update(str(parent).replace('\\','/') for parent in p.parents if str(parent)!='.')
    return original,declared


def contained_path(repo_root: str | Path, path: str | Path, *, must_exist: bool = False) -> Path:
    root = Path(repo_root).resolve()
    text=str(path).replace('\\','/')
    if text.startswith('//?/'):text=text[4:]
    supplied = Path(text)
    foreign_absolute=PureWindowsPath(text).is_absolute() or supplied.is_absolute()
    direct=(supplied if supplied.is_absolute() else root/supplied).resolve()
    if foreign_absolute and (not direct.is_relative_to(root) or not supplied.is_absolute()):
        original,declared=_snapshot_paths(str(root))
        if original and text.casefold().startswith(original.casefold()+'/'):
            relative=text[len(original)+1:]
            if '..' in Path(relative).parts or relative not in declared:
                raise RegistryError(f'Archivpfad ist nicht im Übergabemanifest freigegeben: {path}')
            supplied=root/relative
        else:
            raise RegistryError(f'Pfad liegt außerhalb des Repositorys: {path}')
    resolved = (supplied if supplied.is_absolute() else root / supplied).resolve()
    if not resolved.is_relative_to(root):
        raise RegistryError(f"Pfad liegt außerhalb des Repositorys: {path}")
    if must_exist and not resolved.exists():
        raise FileNotFoundError(f"Registrierte Datei fehlt: {resolved}")
    return resolved


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024*1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: str | Path) -> dict[str, Any]:
    content = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(content, dict):
        raise RegistryError(f"JSON-Objekt erwartet: {path}")
    return content


@dataclass(frozen=True)
class InputReference:
    profile_id: str
    path: Path
    metadata_path: Path
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def exists(self) -> bool:
        return self.path.is_file() and self.metadata_path.is_file()

    @property
    def description(self) -> str:
        demand = self.metadata.get("demand_profile", {})
        return str(demand.get("description") or demand.get("profile_description") or self.metadata.get("gui_profile_description") or self.profile_id)


@dataclass(frozen=True)
class ResultReference:
    label: str
    path: Path
    kind: str
    profile: str | None = None
    exclude_profiles: tuple[str, ...] = ()
    optional: bool = False


@dataclass(frozen=True)
class SiteConfiguration:
    study_id: str
    site_id: str
    label: str
    runner_kind: str
    can_run: bool
    historical: bool
    profiles: dict[str, InputReference]
    design_path: Path | None
    documentation_path: Path
    result_sources: tuple[ResultReference, ...]
    sensitivity_sources: tuple[ResultReference, ...]
    metadata: dict[str, Any]
    run_limitation: str = ""

    @property
    def inputs(self) -> dict[str, InputReference]:
        return self.profiles

    @property
    def input_paths(self) -> dict[str, Path]:
        return {key: value.path for key, value in self.profiles.items()}

    @property
    def metadata_paths(self) -> dict[str, Path]:
        return {key: value.metadata_path for key, value in self.profiles.items()}

    @property
    def uniform_wacc(self) -> dict[str, Any] | None:
        return self.metadata.get("compatibility", {}).get("uniform_wacc")

    @property
    def year_roles(self) -> dict[str, Any]:
        return extract_year_roles(self.metadata)


@dataclass(frozen=True)
class CaseStudy:
    study_id: str
    label: str
    role: str
    sites: dict[str, SiteConfiguration]
    documentation_path: Path


@dataclass(frozen=True)
class Registry:
    repo_root: Path
    registry_path: Path
    studies: dict[str, CaseStudy]
    warnings: tuple[str, ...] = ()

    def get_site(self, study_id: str, site_id: str) -> SiteConfiguration:
        try:
            return self.studies[study_id].sites[site_id]
        except KeyError as exc:
            raise RegistryError(f"Standort {site_id!r} gehört nicht zu Fallstudie {study_id!r}.") from exc


def _parameter_value(parameters, key, field_name="value"):
    value = parameters.get(key, {})
    return value.get(field_name) if isinstance(value, dict) else None


def extract_year_roles(metadata: dict[str, Any]) -> dict[str, Any]:
    """Unknown years remain unknown; an index year is never called a TMY weather year."""
    design = metadata.get("design", {})
    time = design.get("time", {})
    inputs = metadata.get("input_metadata", {})
    raw_sources = inputs.get("sources", {})
    baseline = metadata.get("baseline_metadata", {})
    parameters = baseline.get("model_parameters", {})
    eu = baseline.get("input", {}).get("eu_site_configuration", {})
    weather = raw_sources.get("weather", {})
    factors = inputs.get("emission_factor_sources", {})
    historical = time.get("historical_year", inputs.get("historical_year", eu.get("historical_year")))
    weather_year = time.get("source_weather_year", eu.get("source_weather_year"))
    if weather.get("weather_selection_years"):
        weather_year = "TMY " + "–".join(str(y) for y in weather["weather_selection_years"])
    source_price = raw_sources.get("electricity_price", {})
    source_factor = raw_sources.get("grid_emission_factor", {})
    financing = design.get("financing", {})
    wacc = eu.get("wacc", {})
    cost_year = inputs.get("price_year", financing.get("cost_price_year", wacc.get("cost_price_year")))
    if cost_year is None:
        cost_year = _parameter_value(parameters, "technologies.pv.capex_eur_per_kw", "reference_year")
    return {
        "study_operation_year": historical,
        "profile_index_year": inputs.get("time_axis", {}).get("profile_calendar_year", _parameter_value(parameters, "study.profile_calendar_year")),
        "weather_year": weather_year,
        "market_price_year": time.get("source_market_year", eu.get("source_market_year", source_price.get("data_year"))),
        "operational_emission_reference_year": factors.get("operational", {}).get("reference_year", source_factor.get("data_year")),
        "regulatory_factor_reference_year": factors.get("regulatory", {}).get("reference_year"),
        "cost_price_year": cost_year,
        "wacc_source_year": financing.get("reference_year", wacc.get("reference_year", _parameter_value(parameters, "technologies.pv.real_wacc_fraction", "reference_year"))),
        "regulatory_scope": "modellierte elektrische Teilprüfung; keine vollständige RFNBO-Zertifizierung",
        "result_timestamp_utc": baseline.get("created_at_utc"),
    }


def _refs(root, entries, site_id):
    refs = []
    for item in entries:
        refs.append(ResultReference(label=item["label"], path=contained_path(root, item["path"].format(site_id=site_id)),
            kind=item["kind"], profile=item.get("profile"), exclude_profiles=tuple(item.get("exclude_profiles", [])), optional=bool(item.get("optional", False))))
    return tuple(refs)


def archived_config_compatibility(root: Path, archived: dict, input_path: Path) -> dict[str, Any]:
    """Read-only check against current native config, never optimizes or edits it."""
    parameters = archived.get("model_parameters", {})
    wacc_fields = {k: v for k, v in parameters.items() if k.endswith("real_wacc_fraction")}
    receipt: dict[str, Any] = {"compatible": False, "annual_solver_calls": 0, "differences": []}
    if not parameters or not wacc_fields:
        receipt["reason"] = "Archivierte Konfigurations-/WACC-Metadaten fehlen."
        return receipt
    wacc_records = list(wacc_fields.values())
    if any(record != wacc_records[0] for record in wacc_records[1:]):
        receipt["reason"] = "Kein einheitlicher archivierter WACC; dünner Legacy-Adapter nicht freigegeben."
        return receipt
    selected = wacc_records[0]
    receipt["uniform_wacc"] = dict(selected)
    path = root / "config_h2.py"
    module_name = "_gui_registry_config_" + file_sha256(path)[:12]
    try:
        spec = importlib.util.spec_from_file_location(module_name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        config = module.with_uniform_real_wacc(module.default_model_config(), selected["value"],
            source=selected["source"], reference_year=selected.get("reference_year"), note=selected.get("note", ""))
        current = {name: {"value": p.value, "unit": p.unit, "source": p.source,
            "reference_year": p.reference_year, "note": p.note} for name, p in module.iter_scalar_parameters(config)}
        differences = [name for name, value in parameters.items() if current.get(name) != value]
        additional = sorted(set(current)-set(parameters))
        permitted_extra = {"study.annual_hours"}
        input_matches = file_sha256(input_path) == archived.get("input", {}).get("sha256")
        modes_match = config.study.annualization_basis == "legacy_365_day_reference" and config.study.temporal_correlation_timezone == "UTC"
        receipt.update({"matching_archived_parameters": len(parameters)-len(differences),
            "archived_parameter_count": len(parameters), "differences": differences,
            "additional_parameter_fields": additional, "native_input_hash_matches_archive": input_matches,
            "native_config_sha256": file_sha256(path), "calendar_annualization_mode_matches": modes_match})
        receipt["compatible"] = not differences and set(additional).issubset(permitted_extra) and input_matches and modes_match
        receipt["reason"] = "Aktuelle native Konfiguration stimmt mit archivierten Parametern überein; expliziter archivierter WACC erforderlich." if receipt["compatible"] else "Aktuelle Konfiguration oder Input stimmt nicht vollständig mit archiviertem Fall überein."
    except Exception as exc:
        receipt["reason"] = f"Kompatibilitätsprüfung nicht verfügbar: {type(exc).__name__}: {exc}"
    finally:
        sys.modules.pop(module_name, None)
    return receipt


def load_registry(repo_root: str | Path, registry_path: str | Path | None = None) -> Registry:
    root = Path(repo_root).resolve()
    # The shipped registry may live in a staging directory during tests; every
    # scientific file reference still has to resolve inside the selected repo.
    path = Path(registry_path).resolve() if registry_path else Path(__file__).with_name("case_studies.json")
    raw = read_json(path)
    studies, warnings = {}, []
    entries = raw.get("studies")
    if not isinstance(entries, list):
        raise RegistryError("Registry benötigt eine studies-Liste.")
    for entry in entries:
        study_id = entry["study_id"]
        if study_id in studies:
            raise RegistryError(f"Doppelte Fallstudien-ID: {study_id}")
        doc = contained_path(root, entry["documentation"])
        design_path = contained_path(root, entry["design"], must_exist=True) if entry.get("design") else None
        design = read_json(design_path) if design_path else {}
        site_rows = design.get("sites", []) if entry.get("sites_from_design") else entry.get("sites", [])
        if not isinstance(site_rows, list) or not site_rows:
            raise RegistryError(f"Fallstudie {study_id} benötigt dokumentierte Standorte.")
        sites = {}
        for row in site_rows:
            site_id = row["site_id"]
            if site_id in sites:
                raise RegistryError(f"Doppelte Standort-ID: {study_id}/{site_id}")
            profiles = {}
            for profile in row.get("profiles", entry.get("profiles", [])):
                data_ref = row.get("input") or entry["input_template"].format(site_id=site_id, profile=profile)
                meta_ref = row.get("input_metadata") or entry["input_metadata_template"].format(site_id=site_id, profile=profile)
                data_path, meta_path = contained_path(root, data_ref), contained_path(root, meta_ref)
                meta = read_json(meta_path) if meta_path.is_file() else {}
                meta = dict(meta)
                documented = design.get("hydrogen_demand", {}).get("profiles", {}).get(profile, {})
                if documented.get("weight"):
                    meta["gui_profile_description"] = documented["weight"]
                elif meta.get("sources", {}).get("h2_demand"):
                    meta["gui_profile_description"] = str(meta["sources"]["h2_demand"])
                profiles[profile] = InputReference(profile, data_path, meta_path, meta)
                if not profiles[profile].exists:
                    warnings.append(f"Input/Metadaten fehlen: {study_id}/{site_id}/{profile}")
            basis_meta_path = row.get("baseline_metadata")
            if basis_meta_path:
                basis_path = contained_path(root, basis_meta_path)
                baseline = read_json(basis_path) if basis_path.is_file() else {}
            else:
                # Reference comparison has established scenario result paths;
                # it is a read-only source for version and parameter provenance.
                baseline = {}
                for ref in _refs(root, entry.get("results", []), site_id):
                    if ref.kind == "scenario_comparison" and ref.path.is_file():
                        import pandas as pd
                        comp = pd.read_csv(ref.path)
                        if len(comp) and "result_directory" in comp:
                            p = contained_path(root, ref.path.parent / str(comp.result_directory.iloc[0]) / "run_metadata.json")
                            if p.is_file():
                                baseline = read_json(p)
                            break
            metadata = {"design": design, "site_record": row,
                "input_metadata": next(iter(profiles.values())).metadata if profiles else {}, "baseline_metadata": baseline}
            historical = entry.get("role") == "historical"
            inputs_exist = bool(profiles) and all(p.exists for p in profiles.values())
            compatibility_allowed = not historical
            if entry.get("require_archived_config_compatibility") and profiles:
                metadata["compatibility"] = archived_config_compatibility(root, baseline, next(iter(profiles.values())).path)
                compatibility_allowed = metadata["compatibility"]["compatible"]
                if not compatibility_allowed:
                    warnings.append(f"Keine Neu-Ausführung freigegeben: {study_id}/{site_id}: {metadata['compatibility']['reason']}")
            can_run = bool(entry.get("can_run", False)) and compatibility_allowed and inputs_exist
            sites[site_id] = SiteConfiguration(study_id, site_id, row.get("label", site_id), entry.get("runner_kind", "historical_read_only"),
                can_run, historical, profiles, design_path, doc, _refs(root, entry.get("results", []), site_id),
                _refs(root, entry.get("sensitivities", []), site_id), metadata, entry.get("run_limitation", ""))
        studies[study_id] = CaseStudy(study_id, entry.get("label", study_id), entry.get("role", "documented"), sites, doc)
    known = {s.documentation_path.resolve() for s in studies.values()}
    # Do not silently declare an unconfigured MD-only study runnable.
    for doc in (root / "fallstudien").glob("FALLSTUDIE_*.md"):
        if doc.resolve() not in known:
            study_id = "documented_" + doc.stem.lower()
            studies[study_id] = CaseStudy(study_id, doc.stem.replace("FALLSTUDIE_", "").replace("_", " "), "documented", {}, doc)
            warnings.append(f"Dokumentierte Fallstudie ohne ausführbaren Registry-Eintrag: {doc.name}")
    return Registry(root, path, studies, tuple(warnings))


__all__ = ["Registry", "RegistryError", "CaseStudy", "SiteConfiguration", "InputReference", "ResultReference", "load_registry", "contained_path", "read_json", "file_sha256", "extract_year_roles", "archived_config_compatibility"]
