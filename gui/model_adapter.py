"""Thin adapter to existing H2 runners and validation, never a second model."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Iterable

try:
    from .gui_utils import numeric_value, parse_wacc_percent, sha256
except ImportError:
    from gui_utils import numeric_value, parse_wacc_percent, sha256

JSON_MARKER = "H2_GUI_JSON:"
DEFAULT_MODEL_PYTHON = Path(r"C:\Users\meric\anaconda3\envs\h2-model\python.exe")


def _python(executable=None) -> str:
    selected = Path(executable or os.environ.get('H2_MODEL_PYTHON') or (DEFAULT_MODEL_PYTHON if DEFAULT_MODEL_PYTHON.is_file() else sys.executable)).resolve()
    if not selected.is_file():
        raise ValueError("Python-Interpreter für das Modell fehlt.")
    return str(selected)


def _core_request(repo_root, model_python, action: str, payload=None) -> dict:
    command = [_python(model_python), str(Path(__file__).resolve()), "--core-action", action,
               "--repo-root", str(Path(repo_root).resolve())]
    result = subprocess.run(command, input=json.dumps(payload or {}, allow_nan=False), text=True,
        encoding="utf-8", capture_output=True, timeout=120, shell=False,
        env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"},
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    lines = [line[len(JSON_MARKER):] for line in result.stdout.splitlines() if line.startswith(JSON_MARKER)]
    if not lines:
        raise ValueError("Modellprüfung fehlgeschlagen: " + (result.stderr or result.stdout)[-1800:])
    receipt = json.loads(lines[-1])
    if not receipt.get("ok"):
        raise ValueError(receipt.get("error", "Modellprüfung fehlgeschlagen."))
    return receipt


def supported_parameters(repo_root, model_python=None) -> dict[str, str]:
    receipt = _core_request(repo_root, model_python, "inspect")
    # Uniform country-rate replacement is an existing legacy capability but is
    # not silently offered as a generic EU financing input.
    return {key: unit for key, unit in receipt["parameter_units"].items()
            if key not in ("baseline", "uniform_real_wacc_fraction")}


def probe_solvers(repo_root, model_python=None, *, annual_hours: int = 8784) -> dict:
    return _core_request(repo_root, model_python, "solvers", {"annual_hours": annual_hours})


def _source(path, *, required=False):
    if path is None:
        if required:
            raise ValueError("Erforderliche Quelle fehlt.")
        return None
    selected = Path(path).resolve()
    if not selected.is_file():
        raise ValueError("Quelldatei fehlt: " + str(selected))
    return {"path": str(selected), "sha256": sha256(selected)}


def build_single_plan(repo_root, input_csv, scenarios=("reference", "red_monthly", "red_hourly"),
                      solver="scipy-highs", *, site_id=None, design_json=None,
                      source_metadata=None, uniform_wacc_percent=None, uniform_wacc_source=None,
                      profile_id="D0", study_id="", model_python=None, can_run=True, source_note="",
                      runner_kind=None) -> dict:
    if not can_run:
        raise ValueError("Dieser historische Fall ist nicht für neue Modellläufe freigegeben.")
    if solver not in ("scipy-highs", "gurobi", "auto"):
        raise ValueError("Unbekannter Solver.")
    scenario_ids = list(scenarios)
    if not scenario_ids or len(set(scenario_ids)) != len(scenario_ids):
        raise ValueError("Mindestens ein eindeutiges Szenario wählen.")
    native_site = site_id if runner_kind != "legacy" else None
    if native_site and uniform_wacc_percent is not None:
        raise ValueError("EU-Länderraten und einheitlicher WACC dürfen nicht gemischt werden.")
    uniform = parse_wacc_percent(uniform_wacc_percent) if uniform_wacc_percent is not None else None
    if uniform is not None and not (uniform_wacc_source or "").strip():
        raise ValueError("Einheitlicher WACC benötigt die dokumentierte Quellenbeschreibung.")
    repo = Path(repo_root).resolve()
    if not (repo / "run_h2_sensitivity.py").is_file():
        raise ValueError("Bestehender H2-Sensitivitätsrunner fehlt.")
    plan = {"schema_version": "1.0", "kind": "single", "repo_root": str(repo),
        "model_python": _python(model_python), "study_id": str(study_id), "site_id": site_id,
        "native_eu_site": native_site, "runner_kind": runner_kind or ("eu" if native_site else "legacy"),
        "profile_id": str(profile_id), "solver": solver, "scenarios": scenario_ids,
        "input": _source(input_csv, required=True), "source_metadata": _source(source_metadata),
        "design": _source(design_json), "uniform_wacc_fraction": uniform,
        "uniform_wacc_source": uniform_wacc_source, "source_note": str(source_note), "variants": [],
        "optimization_count": len(scenario_ids), "code_sha256": {
            path.name: sha256(path) for path in sorted(repo.glob("*.py"))}}
    metadata = json.loads(Path(source_metadata).read_text(encoding="utf-8-sig")) if source_metadata else {}
    plan["metadata_kind"] = "source_contract" if "emission_factor_mode" in metadata else "descriptive_sidecar"
    descriptive_input_hash = metadata.get("output", {}).get("input_sha256")
    if descriptive_input_hash and descriptive_input_hash != plan["input"]["sha256"]:
        raise ValueError("Deskriptive Input-Metadaten gehören zu einer anderen CSV-Datei.")
    if native_site and (plan["design"] is None or plan["source_metadata"] is None or plan["metadata_kind"] != "source_contract"):
        raise ValueError("EU-Läufe benötigen Standortdesign und SHA-gebundenen Inputquellenvertrag.")
    receipt = preflight_plan(plan)
    plan["input_context"] = receipt["input_context"]
    plan["expected_hours"] = receipt["expected_hours"]
    plan["parameter_units"] = receipt["parameter_units"]
    plan["total_runs"] = plan["optimization_count"]
    return plan


def build_sensitivity_plan(repo_root, input_csv, scenarios=("reference", "red_monthly", "red_hourly"),
                           solver="scipy-highs", *, variants=None, sensitivityspecs=None,
                           sensitivity_specs=None, reuse_baseline_dir=None, **kwargs) -> dict:
    if reuse_baseline_dir is not None:
        raise ValueError("GUI-Aufträge erzeugen eigene Basisläufe; native historische Resultate bleiben lesbar.")
    plan = build_single_plan(repo_root, input_csv, scenarios, solver, **kwargs)
    plan["kind"] = "sensitivity"
    expanded = []
    specs = variants if variants is not None else (sensitivityspecs if sensitivityspecs is not None else sensitivity_specs)
    for spec in specs or []:
        if not spec.get("active", True):
            continue
        values = spec.get("values", [spec.get("value")])
        if not isinstance(values, (list, tuple)):
            raise ValueError("Sensitivitätswerte als Liste übergeben.")
        for value in values:
            expanded.append({"parameter": str(spec.get("parameter", "")), "value": numeric_value(value),
                "source": str(spec.get("source", "Explizite GUI-OAT-Szenariowahl des Nutzers")),
                "note": str(spec.get("note", "Einzelfaktorfall; keine Prognose oder Unsicherheitsverteilung.")),
                "label": str(spec.get("label", spec.get("parameter", "")))})
    if not expanded:
        raise ValueError("Mindestens einen aktiven Sensitivitätswert wählen.")
    if len({(row["parameter"], row["value"]) for row in expanded}) != len(expanded):
        raise ValueError("Doppelte Sensitivitätsfälle sind nicht zulässig.")
    plan["variants"] = expanded
    plan["optimization_count"] = (1 + len(expanded)) * len(plan["scenarios"])
    plan["total_runs"] = plan["optimization_count"]
    preflight_plan(plan)
    return plan


def combine_plans(plans: Iterable[dict]) -> dict:
    children = list(plans)
    if not children:
        raise ValueError("Keine Läufe ausgewählt.")
    identities = {(item["study_id"], item["site_id"], item["profile_id"], item["solver"],
                   item["kind"], tuple(item["scenarios"]),
                   json.dumps(item.get("variants", []), sort_keys=True)) for item in children}
    if len(identities) != len(children):
        raise ValueError("Doppelte Studie-/Standort-/Nachfrageprofil-/Solverkonfigurationen.")
    if len({(item["repo_root"], item["model_python"]) for item in children}) != 1:
        raise ValueError("Ein Auftrag benötigt dieselbe Modellversion und denselben Interpreter.")
    return {"schema_version": "1.0", "kind": "combined", "repo_root": children[0]["repo_root"],
        "model_python": children[0]["model_python"], "plans": children,
        "optimization_count": sum(item["optimization_count"] for item in children),
        "total_runs": sum(item["optimization_count"] for item in children)}


def build_plan(registry, study_id, site_id, profiles, scenarios, solver="scipy-highs",
               sensitivityspecs=None, model_python=None) -> dict:
    site = registry.get_site(study_id, site_id)
    if not site.can_run:
        raise ValueError(site.run_limitation or "Historische Fallstudie nicht erneut ausführbar.")
    children = []
    for profile in profiles:
        if profile not in site.profiles:
            raise ValueError("Nachfrageprofil gehört nicht zum gewählten Standort.")
        reference = site.profiles[profile]
        uniform = site.uniform_wacc or {}
        options = {"site_id": site.site_id, "design_json": site.design_path,
            "source_metadata": reference.metadata_path, "profile_id": profile, "study_id": study_id,
            "model_python": model_python, "can_run": site.can_run, "runner_kind": site.runner_kind,
            "uniform_wacc_percent": uniform.get("value") * 100 if uniform else None,
            "uniform_wacc_source": uniform.get("source")}
        builder = build_sensitivity_plan if sensitivityspecs else build_single_plan
        if sensitivityspecs:
            options["sensitivityspecs"] = sensitivityspecs
        children.append(builder(registry.repo_root, reference.path, scenarios, solver, **options))
    return combine_plans(children)


def case_table_rows(plan: dict) -> list[dict]:
    rows = [{"case_id": "baseline", "parameter": "baseline", "level": "base", "label": "Basisfall",
             "value": "", "unit": "-", "source": "Dokumentierte gewählte Fallstudienkonfiguration", "note": "Keine Änderung."}]
    for index, variant in enumerate(plan.get("variants", []), 1):
        rows.append({"case_id": f"oat_{index:04d}", "parameter": variant["parameter"], "level": "explicit",
            "label": variant["label"], "value": variant["value"], "unit": plan["parameter_units"][variant["parameter"]],
            "source": variant["source"], "note": variant["note"]})
    return rows


def preflight_plan(plan: dict) -> dict:
    if plan.get("kind") == "combined":
        return {"ok": True, "children": [preflight_plan(item) for item in plan["plans"]]}
    for key in ("input", "source_metadata", "design"):
        receipt = plan.get(key)
        if receipt and sha256(receipt["path"]) != receipt["sha256"]:
            raise ValueError("Quelle wurde seit Auswahl verändert: " + key)
    current = {path.name: sha256(path) for path in Path(plan["repo_root"]).glob("*.py")}
    if current != plan["code_sha256"]:
        raise ValueError("Modellcode wurde seit Konfiguration verändert; Plan neu erstellen.")
    receipt = _core_request(plan["repo_root"], plan["model_python"], "preflight", plan)
    if plan["solver"] == "gurobi":
        probe = probe_solvers(plan["repo_root"], plan["model_python"], annual_hours=receipt["expected_hours"])
        if not probe["solvers"]["gurobi"]["available"]:
            raise ValueError(probe["solvers"]["gurobi"]["reason"] + " SciPy/HiGHS ist eine verfügbare Alternative.")
    return receipt


def _native_action(action: str, repo_root: str, payload: dict) -> dict:
    sys.path.insert(0, str(Path(repo_root).resolve()))
    if action == "solvers":
        import scipy
        solvers = {"scipy-highs": {"available": True, "version": scipy.__version__},
                   "auto": {"available": True, "reason": "Expliziter bestehender Auto-Solverpfad."}}
        try:
            import gurobipy as gp
            with gp.Env(empty=True) as environment:
                environment.setParam("OutputFlag", 0)
                environment.start()
                with gp.Model(env=environment) as model:
                    # Only a licence-size probe, not the H2 model.
                    count = max(2101, int(payload.get("annual_hours", 8784)) * 10)
                    model.addVars(count, lb=0, obj=1)
                    model.optimize()
                    solvers["gurobi"] = {"available": True, "version": list(gp.gurobi.version()),
                                          "reason": "Installation und Lizenz-Größenprobe erfolgreich."}
        except Exception as exc:
            solvers["gurobi"] = {"available": False, "reason": str(exc)}
        return {"ok": True, "solvers": solvers}
    import run_h2_sensitivity as sensitivity
    if action == "inspect":
        return {"ok": True, "parameter_units": sensitivity.PARAMETER_UNITS,
                "scenarios": [scenario.value for scenario in sensitivity.Scenario]}
    import pandas as pd
    from config_h2 import DEFAULT_CONFIG, Scenario, with_uniform_real_wacc
    from h2_input_data import validate_hourly_input
    from h2_sensitivity_overrides import apply_sensitivity_override
    from eu_site_configuration import load_eu_site_configuration
    from run_single_site_h2 import _load_emission_factor_metadata, _require_eu_input_context_matches
    for scenario in payload["scenarios"]:
        Scenario(scenario)
    config = DEFAULT_CONFIG
    frame = pd.read_csv(payload["input"]["path"], dtype=str, keep_default_na=False)
    selected = None
    if payload.get("native_eu_site"):
        selected = load_eu_site_configuration(payload["native_eu_site"], design_path=payload["design"]["path"])
        config = selected.config
    if payload.get("uniform_wacc_fraction") is not None:
        config = with_uniform_real_wacc(config, payload["uniform_wacc_fraction"], source=payload["uniform_wacc_source"])
    if payload.get("source_metadata") and payload.get("metadata_kind") == "source_contract":
        _load_emission_factor_metadata(frame, Path(payload["source_metadata"]["path"]), payload["input"]["sha256"])
    if selected:
        _require_eu_input_context_matches(frame, selected.metadata)
        frame.attrs["eu_site_configuration"] = selected.metadata
    validated = validate_hourly_input(frame, require_separate_emission_factors=bool(selected))
    for row in payload.get("variants", []):
        if row["parameter"] not in sensitivity.SUPPORTED_PARAMETERS or row["parameter"] == "baseline":
            raise ValueError("Sensitivitätsparameter ist nicht im vorhandenen Runner implementiert.")
        apply_sensitivity_override(config, {key: row[key] for key in ("parameter", "value", "source", "note")})
    if payload.get("variants"):
        import tempfile
        payload = {**payload, "parameter_units": sensitivity.PARAMETER_UNITS}
        with tempfile.TemporaryDirectory(prefix="h2_gui_preflight_") as temporary:
            table = Path(temporary) / "cases.csv"
            pd.DataFrame(case_table_rows(payload)).to_csv(table, index=False)
            sensitivity.load_sensitivity_cases(table)
    context = dict(validated.attrs.get("declared_input_context", {}))
    context.update(annual_h2_requested_kg=float(pd.to_numeric(validated["h2_demand"]).sum()),
        annual_active_delivery_hours=int((pd.to_numeric(validated["h2_demand"]) > 0).sum()),
        temporal_correlation_timezone=config.study.temporal_correlation_timezone)
    return {"ok": True, "input_context": context, "expected_hours": len(validated),
            "parameter_units": sensitivity.PARAMETER_UNITS}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--core-action", choices=("inspect", "preflight", "solvers"), required=True)
    parser.add_argument("--repo-root", required=True)
    arguments = parser.parse_args()
    try:
        result = _native_action(arguments.core_action, arguments.repo_root, json.loads(sys.stdin.read() or "{}"))
    except Exception as exc:
        result = {"ok": False, "error": str(exc), "error_type": type(exc).__name__}
    print(JSON_MARKER + json.dumps(result, ensure_ascii=False, allow_nan=False))
