"""Persisted background jobs invoking the existing native H2 CLI runners."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import uuid

try:
    from .gui_utils import atomic_json, read_json, sha256
    from .model_adapter import case_table_rows, preflight_plan
except ImportError:
    from gui_utils import atomic_json, read_json, sha256
    from model_adapter import case_table_rows, preflight_plan

NATIVE_FILES = ("summary.csv", "hourly_operation.csv", "run_metadata.json", "validated_input.csv")
SCENARIO_IDS = {"reference": "S0", "red_monthly": "S1", "red_hourly": "S2", "off_grid": "S3"}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _children(plan):
    return plan["plans"] if plan.get("kind") == "combined" else [plan]


def _safe_label(text):
    return re.sub(r"[^a-zA-Z0-9_-]", "_", str(text))[:80]


def prepare_job(plan: dict, jobs_root, python_executable=None) -> Path:
    """Freeze a reviewed plan and inputs. This starts no optimizer or worker."""
    preflight_plan(plan)
    children = _children(plan)
    executable = str(Path(python_executable or plan["model_python"]).resolve())
    if not Path(executable).is_file():
        raise ValueError("Python-Interpreter für den GUI-Worker fehlt.")
    root = Path(jobs_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    identifier = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SUTC_") + uuid.uuid4().hex[:12]
    job = root / identifier
    job.mkdir(exist_ok=False)
    evidence = job / "evidence"
    code = evidence / "code"
    code.mkdir(parents=True)
    sources = []
    repo = Path(plan["repo_root"])
    for path in sorted(repo.glob("*.py")):
        target = code / path.name
        shutil.copy2(path, target)
        if sha256(target) != children[0]["code_sha256"][path.name]:
            raise ValueError("Modellcode änderte sich beim Einfrieren.")
        sources.append({"original": str(path), "copy": str(target), "sha256": sha256(target)})
    gui_copy = evidence / "gui"
    gui_copy.mkdir()
    for name in ("jobs.py", "gui_utils.py", "model_adapter.py"):
        original_gui = Path(__file__).resolve().parent / name
        target_gui = gui_copy / name
        shutil.copy2(original_gui, target_gui)
        sources.append({"original": str(original_gui), "copy": str(target_gui), "sha256": sha256(target_gui)})
    frozen = []
    for index, child in enumerate(children):
        current = json.loads(json.dumps(child))
        current["original_repo_root"] = current["repo_root"]
        current["repo_root"] = str(code)
        selected = evidence / f"profile_{index:03d}"
        selected.mkdir()
        for key, name in (("input", "input.csv"), ("source_metadata", "input.metadata.json"), ("design", "design.json")):
            receipt = child.get(key)
            if receipt:
                target = selected / name
                shutil.copy2(receipt["path"], target)
                if sha256(target) != receipt["sha256"]:
                    raise ValueError("Eingabedatei änderte sich beim Einfrieren: " + key)
                current[key] = {"path": str(target), "sha256": receipt["sha256"]}
                sources.append({"original": receipt["path"], "copy": str(target), "sha256": receipt["sha256"]})
        table = selected / "cases.csv"
        rows = case_table_rows(current)
        with table.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        current["cases"] = {"path": str(table), "sha256": sha256(table)}
        current["output_directory"] = str(job / "runs" / f"{index:03d}_{_safe_label(child['profile_id'])}")
        frozen.append(current)
    record = {"schema_version": "1.0", "created_at_utc": _now(), "job_id": identifier,
        "requested_plan": plan, "execution_plans": frozen, "source_receipts": sources,
        "optimization_count": plan["optimization_count"], "model_python": plan["model_python"], "worker_python": executable}
    atomic_json(job / "plan.json", record)
    (job / "plan.sha256").write_text(sha256(job / "plan.json") + "\n", encoding="ascii")
    atomic_json(job / "status.json", {"job_id": identifier, "state": "queued", "created_at_utc": _now(),
        "completed_cases": 0, "total_cases": plan["optimization_count"], "progress": 0,
        "solver": children[0]["solver"], "current_case": None, "validation_status": "not_run"})
    return job


def submit_job(plan: dict, jobs_root, python_executable=None) -> Path:
    job = prepare_job(plan, jobs_root, python_executable)
    worker = job / "evidence/gui/jobs.py"
    log_path = job / "worker.log"
    flags = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS if os.name == "nt" else 0
    try:
        with log_path.open("wb") as log:
            worker_python = read_json(job / "plan.json")["worker_python"]
            process = subprocess.Popen([worker_python, str(worker), "--worker", str(job)],
                cwd=str(worker.parent), stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                shell=False, creationflags=flags,
                env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"},
                start_new_session=os.name != "nt")
    except Exception as exc:
        status = read_json(job / "status.json")
        status.update(state="failed", error=str(exc), error_type=type(exc).__name__, finished_at_utc=_now())
        atomic_json(job / "status.json", status)
        raise
    # The worker alone owns status.json; avoid racing its first progress write.
    atomic_json(job / "worker.json", {"worker_pid": process.pid, "launched_at_utc": _now()})
    return job


def start_job(plan: dict, repo_root) -> Path:
    return submit_job(plan, Path(repo_root) / "outputs_h2/gui_runs")


def read_status(job_dir) -> dict:
    job = Path(job_dir).resolve()
    status = read_json(job / "status.json")
    status["job_path"] = str(job)
    status["status"] = status["state"]
    status["total_runs"] = status["total_cases"]
    status["completed_runs"] = status["completed_cases"]
    if (job / "worker.json").is_file():
        status.setdefault("worker_pid", read_json(job / "worker.json")["worker_pid"])
    for name in ("worker.log", "native.log"):
        path = job / name
        if path.is_file():
            status["log_tail"] = path.read_text(encoding="utf-8", errors="replace")[-8000:]
    return status


job_status = read_status


def list_jobs(jobs_root) -> list[dict]:
    root = Path(jobs_root)
    if not root.is_dir():
        return []
    jobs = []
    for path in sorted(root.iterdir(), reverse=True):
        if path.is_dir() and (path / "status.json").is_file():
            try:
                jobs.append(read_status(path))
            except (OSError, ValueError):
                continue
    return jobs


def _completed(output: Path) -> list[Path]:
    completed = []
    if not output.is_dir():
        return completed
    for path in output.rglob("summary.csv"):
        directory = path.parent
        if all((directory / name).is_file() for name in NATIVE_FILES):
            try:
                with path.open(encoding="utf-8", newline="") as handle:
                    rows = list(csv.DictReader(handle))
                if len(rows) == 1 and rows[0].get("solver_status") == "optimal":
                    completed.append(directory)
            except (OSError, ValueError):
                pass
    return completed


def _command(plan: dict) -> list[str]:
    command = [plan["model_python"], str(Path(plan["repo_root"]) / "run_h2_sensitivity.py"),
        "--input", plan["input"]["path"], "--cases", plan["cases"]["path"],
        "--output-dir", plan["output_directory"], "--solver", plan["solver"],
        "--scenarios", *plan["scenarios"]]
    if plan.get("native_eu_site"):
        command.extend(["--eu-site", plan["native_eu_site"], "--eu-design", plan["design"]["path"],
                        "--require-separate-emission-factors"])
    if plan.get("source_metadata") and plan.get("metadata_kind") == "source_contract":
        command.extend(["--emission-factor-metadata", plan["source_metadata"]["path"]])
    if plan.get("uniform_wacc_fraction") is not None:
        command.extend(["--base-uniform-real-wacc", str(plan["uniform_wacc_fraction"]),
                        "--base-wacc-source", plan["uniform_wacc_source"]])
    return command


def _validate_outputs(plan, log) -> tuple[list[dict], bool]:
    output = Path(plan["output_directory"])
    with (output / "sensitivity_comparison.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    results, partial = [], False
    for case in dict.fromkeys(row["case_id"] for row in rows):
        group = [row.copy() for row in rows if row["case_id"] == case]
        directory = output / "runs" / case
        for row in group:
            row["scenario_id"] = SCENARIO_IDS[row["scenario"]]
            row["result_directory"] = row["scenario"]
        with (directory / "scenario_comparison.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(group[0]))
            writer.writeheader()
            writer.writerows(group)
        command = [plan["model_python"], str(Path(plan["repo_root"]) / "validate_h2_results.py"),
            "--results-dir", str(directory), "--expected-hours", str(plan["expected_hours"])]
        process = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, shell=False,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"})
        report = read_json(directory / "validation/validation_report.json")
        if not report["all_checks_passed"]:
            with (directory / "validation/validation_checks.csv").open(encoding="utf-8", newline="") as handle:
                failed = [row["check_id"] for row in csv.DictReader(handle) if row["passed"].lower() == "false"]
            if set(failed) == {"core_scenarios_present"} and not {"reference", "red_monthly", "red_hourly"}.issubset(plan["scenarios"]):
                partial = True
            else:
                raise ValueError(f"Native Validierung fehlgeschlagen ({case}): " + ", ".join(failed))
        elif process.returncode:
            raise ValueError("Native Validierung meldet einen Prozessfehler.")
        results.append({"case_id": case, "directory": str(directory), "all_checks_passed": report["all_checks_passed"],
                        "report_path": str(directory / "validation/validation_report.json")})
    return results, partial


def run_job(job_dir) -> dict:
    """Worker entry point; synchronous for testing, detached when launched by UI."""
    job = Path(job_dir).resolve()
    status = read_json(job / "status.json")
    if status["state"] != "queued":
        raise ValueError("Dieser Auftrag wurde bereits gestartet; vorhandene Outputs werden nicht überschrieben.")
    started = time.monotonic()
    status.update(state="running", started_at_utc=_now(), worker_pid=os.getpid())
    atomic_json(job / "status.json", status)
    completed_before = 0
    validation, partial = [], False
    try:
        if sha256(job / "plan.json") != (job / "plan.sha256").read_text(encoding="ascii").strip():
            raise ValueError("Unveränderlicher GUI-Plan wurde nach Erstellung geändert.")
        record = read_json(job / "plan.json")
        for receipt in record["source_receipts"]:
            if sha256(receipt["copy"]) != receipt["sha256"]:
                raise ValueError("Gefrorene Eingabe oder Modellcode wurde geändert.")
        with (job / "native.log").open("ab", buffering=0) as log:
            for plan in record["execution_plans"]:
                preflight_plan(plan)
                if sha256(plan["cases"]["path"]) != plan["cases"]["sha256"]:
                    raise ValueError("Gefrorene OAT-Falltabelle wurde geändert.")
                command = _command(plan)
                atomic_json(Path(plan["cases"]["path"]).parent / "native_command.json", {"argv": command, "shell": False})
                process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                    shell=False, cwd=plan["repo_root"], creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                    env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"})
                while process.poll() is None:
                    current = _completed(Path(plan["output_directory"]))
                    status.update(current_case={"study_id": plan["study_id"], "site_id": plan["site_id"],
                        "profile_id": plan["profile_id"], "last_completed": str(current[-1]) if current else None},
                        completed_cases=completed_before + len(current), elapsed_seconds=time.monotonic() - started)
                    status["progress"] = status["completed_cases"] / status["total_cases"]
                    atomic_json(job / "status.json", status)
                    time.sleep(.5)
                if process.returncode:
                    raise RuntimeError(f"Nativer Runner beendet mit Code {process.returncode}; Solverfehler, Infeasibilität oder Eingabefehler im Protokoll prüfen.")
                current = _completed(Path(plan["output_directory"]))
                if len(current) != plan["optimization_count"]:
                    raise RuntimeError("Anzahl optimaler nativer Vierdatei-Exporte entspricht nicht dem Plan.")
                completed_before += len(current)
                checked, partly = _validate_outputs(plan, log)
                validation.extend(checked)
                partial = partial or partly
        status.update(state="completed", completed_cases=completed_before, progress=1,
            validation_status="partial_scenario_selection" if partial else "passed", validation=validation,
            finished_at_utc=_now(), elapsed_seconds=time.monotonic() - started)
    except Exception as exc:
        status.update(state="failed", error=str(exc), error_type=type(exc).__name__, finished_at_utc=_now(),
            elapsed_seconds=time.monotonic() - started, validation_status="failed")
    atomic_json(job / "status.json", status)
    return status


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", required=True)
    arguments = parser.parse_args()
    try:
        outcome = run_job(arguments.worker)
        print(json.dumps(outcome, ensure_ascii=False))
        sys.exit(0 if outcome["state"] == "completed" else 1)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
