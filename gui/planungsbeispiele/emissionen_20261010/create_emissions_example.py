"""Planning preview from accepted native results; no optimization or GUI change."""
from pathlib import Path
import argparse
import hashlib
import json
import math
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

STAGE = Path(__file__).resolve().parent
candidate = Path(__file__).resolve().parents[3]
default_repo = candidate if (candidate / "gui/result_loader.py").is_file() else Path(r"C:\Forschungsarbeit\Opt_H2_Meric-h2")
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--repo-root", type=Path, default=default_repo)
REPO = parser.parse_args().repo_root.resolve()
sys.path.insert(0, str(REPO))
from gui.result_loader import validation_for_result

BASE = REPO / "outputs_h2/eu_case_studies/historical_2024/verification_runs/basis_20261004_121938UTC/runs/hamburg_moorburg/D0"
source = BASE / "scenario_comparison.csv"
frame = pd.read_csv(source)
assert frame.scenario_id.tolist() == ["S0", "S1", "S2"]
assert frame.solver_status.eq("optimal").all()
assert frame.number_of_hours.eq(8784).all()
assert frame.annual_h2_delivered_kg.eq(3_650_000).all()
op = "operational_emission_intensity_kg_co2e_per_kg_h2"
reg = "regulatory_emission_intensity_kg_co2e_per_kg_h2"
limit = "red_iii_maximum_product_intensity_kg_co2e_per_kg_h2"
limit_mj = "red_iii_maximum_product_intensity_g_co2e_per_mj"
reports = []
for _, row in frame.iterrows():
    result = BASE / row.result_directory
    native = pd.read_csv(result / "summary.csv").iloc[0]
    for key in (op, reg, limit, limit_mj):
        assert math.isfinite(float(row[key]))
        assert math.isclose(float(row[key]), float(native[key]), rel_tol=1e-12, abs_tol=1e-12)
    check = validation_for_result(result, REPO)
    assert check["status"] == "passed", check
    assert check["covers_selected_result"] and check["source_comparison_hash_matches"]
    reports.append({"scenario": row.scenario_id, "result_directory": str(result), "validation": check,
                    "summary_sha256": hashlib.sha256((result / "summary.csv").read_bytes()).hexdigest()})
thresholds = frame[limit].astype(float).tolist()
assert all(math.isclose(value, thresholds[0], rel_tol=0, abs_tol=1e-12) for value in thresholds)
threshold = thresholds[0]

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "axes.titlesize": 13,
                    "axes.labelsize": 11, "axes.spines.top": False, "axes.spines.right": False,
                    "svg.fonttype": "none", "figure.facecolor": "white"})
fig, axes = plt.subplots(1, 2, figsize=(11.6, 6.0), sharey=True)
colors = ["#64748b", "#2563eb", "#16a34a"]
bound = max(frame[op].max(), frame[reg].max(), threshold) * 1.19
for ax, field, title in zip(axes, (op, reg), ("Betriebliche Stromemissionen", "Regulatorische elektrische Teilbilanz")):
    values = frame[field].astype(float).tolist()
    ax.bar(range(3), values, color=colors, width=.57, zorder=3)
    ax.set_xticks(range(3), frame.scenario_id.tolist())
    ax.set_ylim(0, bound)
    ax.set_xlim(-.62, 2.62)
    ax.set_title(title, pad=15)
    ax.set_xlabel("Stromversorgungsszenario", labelpad=9)
    ax.grid(axis="y", color="#e2e8f0", zorder=0)
    for x, value in enumerate(values):
        label = f"{value:.3f}".replace(".", ",")
        ax.annotate(label, (x, value), xytext=(0, 6), textcoords="offset points", ha="center", fontsize=11)
axes[0].set_ylabel("kg CO₂e je kg geliefertem H₂", labelpad=11)
reference = axes[1].axhline(threshold, color="#b91c1c", linewidth=1.8, linestyle="--", zorder=4)
axes[1].annotate(f"THG-Referenz: {threshold:.3f}".replace(".", ","),
                 xy=(.99, threshold), xycoords=("axes fraction", "data"),
                 xytext=(0, 7), textcoords="offset points", ha="right", color="#b91c1c", fontsize=10,
                 bbox={"facecolor": "white", "edgecolor": "none", "alpha": .9, "pad": 1.5})
assert reference.get_linestyle() == "--"
assert len(axes[0].lines) == 0 and len(axes[1].lines) == 1
assert axes[1].get_ylim()[1] > threshold and axes[1].get_ylim()[0] == 0

fig.suptitle("Emissionen je Szenario · Hamburg–Moorburg", fontsize=17, fontweight="bold", y=.96)
fig.text(.5, .895, "Historisches 2024 · Lieferprofil D0 · 3,65 Mio. kg H₂/a · HiGHS", ha="center", color="#475569", fontsize=11)
fig.text(.07, .125, "S0: Referenz     S1: monatliche Zuordnung     S2: stündliche Zuordnung", fontsize=10, color="#475569")
fig.text(.07, .072, "THG-Referenz betrifft die vollständige Produktbilanz; dargestellt ist nur der elektrische Teil.\n"
                  "Regulatorische Null bedeutet keine physische Emissionsfreiheit. Planungsbeispiel aus vorhandenen Ergebnissen.",
         fontsize=9.4, color="#475569", linespacing=1.6)
fig.subplots_adjust(left=.08, right=.98, top=.80, bottom=.25, wspace=.17)

for extension in ("png", "svg"):
    fig.savefig(STAGE / f"Emissionen_Szenarien_Planungsbeispiel.{extension}", dpi=180)
plt.close(fig)

columns = ["scenario_id", "scenario", "solver_name", "annual_h2_delivered_kg", op, reg, limit, limit_mj, "input_sha256"]
export = frame[columns].copy()
export["source_comparison_csv"] = str(source)
export["source_result_directory"] = [str(BASE / directory) for directory in frame.result_directory]
export.to_csv(STAGE / "Emissionen_Szenarien_Planungsbeispiel.csv", index=False, encoding="utf-8-sig")
receipt = {"date": "2026-10-10", "purpose": "planning_preview_not_installed_gui", "new_model_runs": 0,
           "source_csv": str(source), "source_csv_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
           "threshold_source": limit, "threshold_kg_co2e_per_kg_delivered_h2": threshold,
           "reference_line_panel": "regulatory_electrical_partial_balance_only",
           "native_validation": reports,
           "checks": {"3_own_native_summaries_match": True, "3_source_bound_validation_reports_passed": True,
                      "one_dashed_reference_line": True, "consistent_units": True, "zero_baseline": True,
                      "threshold_inside_axis": True},
           "artifacts": {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                         for path in STAGE.glob("Emissionen_Szenarien_Planungsbeispiel.*")}}
(STAGE / "example_receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"status": "passed", "native_cases": 3, "new_runs": 0, "threshold": threshold,
                  "image": str(STAGE / "Emissionen_Szenarien_Planungsbeispiel.png")}, ensure_ascii=False))
