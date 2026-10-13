"""Read-only U1 audit against selected registered original H2 exports.

No optimizer is imported or called. Artifacts must be written outside source-root.
Use the GUI's existing Python environment and PYTHONDONTWRITEBYTECODE=1.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import sys

STAGE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(STAGE))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    source = args.source_root.resolve()
    out = args.output_dir.resolve()
    if out.is_relative_to(source):
        raise ValueError("Audit artifacts must be outside the original source root.")
    out.mkdir(parents=True, exist_ok=True)
    os.environ["MPLCONFIGDIR"] = str(out / "matplotlib_cache")

    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd
    from gui import analysis_contracts as contracts, plotting, result_loader
    from gui.case_study_registry import load_registry
    from gui.result_duplicates import collapse_duplicate_results

    checks = []
    tracked = {}
    artifacts = []

    def remember(path):
        path = Path(path).resolve()
        if not path.is_relative_to(source):
            raise ValueError("Native audit source leaves the original repository.")
        if path.is_file():
            tracked[str(path)] = sha(path)
        return path

    def check(name, action):
        try:
            detail = action()
            checks.append({"name": name, "passed": True, "detail": detail})
        except Exception as exc:
            checks.append({"name": name, "passed": False,
                           "detail": f"{type(exc).__name__}: {exc}"})

    def require(condition, message):
        if not condition:
            raise AssertionError(message)

    def roundtrip(frame, filename, numeric_fields):
        path = out / filename
        frame.to_csv(path, index=False, encoding="utf-8-sig")
        artifacts.append(filename)
        restored = pd.read_csv(path)
        require(len(restored) == len(frame), "CSV changed the number of plotted rows.")
        for field in numeric_fields:
            np.testing.assert_allclose(restored[field], pd.to_numeric(frame[field]),
                                       rtol=1e-12, atol=1e-12, equal_nan=True)
        for field in ("scenario_id", "__result_directory", "__oat_reference_id",
                      "selection_result_directory", "timestamp"):
            if field in frame:
                require(restored[field].astype(str).tolist() == frame[field].astype(str).tolist(),
                        f"CSV changed native identity field {field}.")
        return restored

    registry_path = remember(source / "gui/case_studies.json")
    registry = load_registry(source, registry_path)
    site = registry.get_site("eu_2024", "hamburg_moorburg")
    common_ref = next(ref for ref in site.sensitivity_sources
                      if ref.label == "Gemeinsames 3-Fallstudien-Versuchsdesign")
    remember(common_ref.path)
    # Read precisely this registered family, rather than discover all old jobs.
    common = result_loader._read_registered_reference(registry, common_ref, site)
    common = common.loc[common.demand_profile.eq("D0")].copy()
    price_parameter = "electricity_price_eur_per_mwh"
    price_input = common.loc[common.sensitivity_parameter.isin((price_parameter, "baseline"))].copy()
    for directory in price_input["__result_directory"].drop_duplicates():
        for filename in ("summary.csv", "run_metadata.json", "validated_input.csv"):
            remember(Path(directory) / filename)

    holder = {}

    def price_operation():
        presentation = contracts.parameter_presentation(price_input, price_parameter)
        require(presentation["operation"] == "add_to_hourly_price_profile",
                "The historical EU price family was interpreted as a constant tariff.")
        require("verschobenen Preisreihe" in presentation["xlabel"]
                or "Verschiebung der Preisreihe" in presentation["xlabel"],
                "Axis does not state the actual price intervention.")
        prepared = contracts.prepare_oat_frame(price_input, parameter=price_parameter,
                                              metric="lcoh_eur_per_kg_h2")
        holder["price"] = prepared
        require(len(prepared) == 9, "Expected three scenarios times own base and two price levels.")
        require(set(prepared.scenario_id) == {"S0", "S1", "S2"}, "The exact scenario family changed.")
        for sid, rows in prepared.groupby("scenario_id"):
            require(int(rows.__oat_is_baseline.sum()) == 1, f"{sid} has no unique own base.")
            np.testing.assert_allclose(sorted(rows.__plot_x), [.5, 1., 1.5])
            baseline = rows.loc[rows.__oat_is_baseline].iloc[0]
            require(rows.__oat_reference_id.nunique() == 1, "A curve combines different references.")
            require(str(baseline.__result_directory) == str(rows.__oat_reference_id.iloc[0]),
                    "A reference ID points to another native case.")
        variants = prepared.loc[~prepared.__oat_is_baseline]
        np.testing.assert_allclose(sorted(variants.applied_value.unique()),
                                   [-38.300608915158155, 38.300608915158155], rtol=1e-8)
        return {"operation": presentation["operation"], "xlabel": presentation["xlabel"],
                "rows": len(prepared), "own_baselines": int(prepared.__oat_is_baseline.sum())}

    check("real_eu_price_operation_and_own_baseline", price_operation)

    def price_plot_export():
        frame = holder["price"]
        restored = roundtrip(frame, "price_graph_data.csv", ("__plot_x", "lcoh_eur_per_kg_h2"))
        fig = plotting.oat_curve_figure(frame, parameter=price_parameter)
        lines = fig.axes[0].lines
        require(len(lines) == 3, "The plot changed the number of scientific curves.")
        expected = [rows.sort_values("__plot_x") for _, rows in
                    frame.groupby(frame.attrs["group_columns"], dropna=False)]
        for line, rows in zip(lines, expected, strict=True):
            np.testing.assert_allclose(line.get_xdata(), rows.__plot_x)
            np.testing.assert_allclose(line.get_ydata(), rows.lcoh_eur_per_kg_h2)
        require(set(restored.__result_directory) == set(frame.__result_directory),
                "The CSV exported unrelated native cases.")
        fig.savefig(out / "price_graph.png", dpi=150)
        artifacts.append("price_graph.png")
        plt.close(fig)
        return "Three plotted curves reproduce the nine exported native points exactly."

    check("real_price_figure_matches_csv", price_plot_export)

    def foreign_baseline_rejected():
        invalid = price_input.copy(deep=True)
        invalid.loc[invalid.sensitivity_parameter.eq("baseline"),
                    "__native_configuration_sha256"] = "different_unchanged_configuration"
        try:
            contracts.prepare_oat_frame(invalid, parameter=price_parameter,
                                        metric="lcoh_eur_per_kg_h2")
        except ValueError:
            return "Equal saved costs cannot admit a baseline with a different native configuration."
        raise AssertionError("A baseline with unrelated native configuration was accepted.")

    check("foreign_price_reference_is_rejected", foreign_baseline_rejected)

    def verify_native_points(frame):
        for _, row in frame.iterrows():
            directory = Path(str(row.__result_directory))
            for filename in ("summary.csv", "run_metadata.json", "validated_input.csv"):
                remember(directory / filename)
            native = pd.read_csv(directory / "summary.csv")
            require(len(native) == 1, "Expected one native result per OAT point.")
            for field in ("lcoh_eur_per_kg_h2", "objective_eur_per_year", "annual_h2_delivered_kg"):
                np.testing.assert_allclose(float(row[field]), float(native[field].iloc[0]), rtol=1e-12)
        for _, rows in frame.groupby(frame.attrs["group_columns"], dropna=False):
            require(int(rows.__oat_is_baseline.sum()) == 1, "Native OAT curve has no unique own base.")

    def harmonized_wacc_pv():
        details = []
        for parameter, expected_operation in (("uniform_real_wacc_fraction", "multiply_all_five_real_wacc_rates"),
                                              ("pv_capex_eur_per_kw", "replace_baseline_scalar")):
            frame = contracts.prepare_oat_frame(common, parameter=parameter, metric="lcoh_eur_per_kg_h2")
            verify_native_points(frame)
            require(len(frame) == 9, "Common WACC/PV family lost variants or own references.")
            require(frame.attrs["operation"] == expected_operation,
                    "Harmonized family name hid the native WACC/PV intervention.")
            roundtrip(frame, "common_" + parameter + ".csv", ("__plot_x", "lcoh_eur_per_kg_h2"))
            details.append({"family": parameter, "operation": frame.attrs["operation"],
                            "points": len(frame), "own_references": int(frame.__oat_is_baseline.sum())})
        return details

    check("real_harmonized_wacc_and_pv_preserve_native_points", harmonized_wacc_pv)

    def original_eu_oat():
        ref = next(ref for ref in site.sensitivity_sources if ref.label == "Schritt 24: ursprüngliche OAT-Varianten")
        remember(ref.path)
        data = result_loader._read_registered_reference(registry, ref, site)
        data = data.loc[data.demand_profile.eq("D0")].copy()
        details = []
        for parameter in ("electricity_price_offset_eur_per_mwh", "real_wacc_shift_fraction"):
            frame = contracts.prepare_oat_frame(data, parameter=parameter, metric="lcoh_eur_per_kg_h2")
            verify_native_points(frame)
            require(len(frame) == 9, "Original EU OAT lost variants or own references.")
            np.testing.assert_allclose(frame.loc[frame.__oat_is_baseline, "__plot_x"], 0)
            roundtrip(frame, "original_eu_" + parameter + ".csv", ("__plot_x", "lcoh_eur_per_kg_h2"))
            details.append({"family": parameter, "xlabel": frame.attrs["xlabel"], "own_reference_x": 0})
        return details

    check("real_original_eu_price_and_wacc_oat", original_eu_oat)

    def original_namibia_oat():
        historical_site = registry.get_site("namibia", "namibia")
        ref = next(ref for ref in historical_site.sensitivity_sources if ref.label == "Historische Namibia-OAT-Varianten")
        remember(ref.path)
        data = result_loader._read_registered_reference(registry, ref, historical_site)
        frame = contracts.prepare_oat_frame(data, parameter="electricity_price_eur_per_mwh",
                                            metric="lcoh_eur_per_kg_h2")
        verify_native_points(frame)
        require(frame.attrs["operation"] == "replace_hourly_prices_with_constant",
                "The real historical constant tariff was confused with the EU price offset.")
        require(len(frame) == 9, "Original Namibia price family lost native points.")
        base_prices = []
        for _, base in frame.loc[frame.__oat_is_baseline].iterrows():
            native_input = pd.read_csv(Path(str(base.__result_directory)) / "validated_input.csv")
            require(native_input.electricity_price.nunique() == 1, "The native Namibia base is not a constant tariff.")
            actual_price = float(native_input.electricity_price.iloc[0])
            np.testing.assert_allclose(float(base.__plot_x), actual_price)
            base_prices.append(actual_price)
        roundtrip(frame, "original_namibia_constant_price.csv", ("__plot_x", "lcoh_eur_per_kg_h2"))
        return {"operation": frame.attrs["operation"], "points": len(frame), "own_base_prices_eur_per_mwh": base_prices}

    check("real_original_namibia_constant_tariff_and_own_base", original_namibia_oat)

    def quantity_homogeneity():
        ref = next(ref for ref in site.sensitivity_sources if ref.label == "H₂-Jahresnachfrage: 50–150 % (2024)")
        remember(ref.path)
        data = result_loader._read_registered_reference(registry, ref, site)
        data = data.loc[data.demand_profile.eq("D0")].copy()
        frame = contracts.prepare_oat_frame(data, parameter="h2_demand_multiplier", metric="objective_eur_per_year")
        holder["quantity_input"] = data
        verify_native_points(frame)
        require(len(frame) == 15, "Expected three scenarios and five demand levels.")
        for sid, rows in frame.groupby("scenario_id"):
            np.testing.assert_allclose(sorted(rows.__plot_x), [50, 75, 100, 125, 150])
            base = rows.loc[rows.__oat_is_baseline].iloc[0]
            require(float(base.__plot_x) == 100, "The unique embedded quantity basis is not 100%.")
            factors = rows.__plot_x / 100
            np.testing.assert_allclose(rows.annual_h2_delivered_kg, factors * base.annual_h2_delivered_kg, rtol=1e-10)
            np.testing.assert_allclose(rows.objective_eur_per_year, factors * base.objective_eur_per_year, rtol=1e-6)
            np.testing.assert_allclose(rows.lcoh_eur_per_kg_h2, base.lcoh_eur_per_kg_h2, rtol=1e-6)
        roundtrip(frame, "quantity_graph_data.csv", ("__plot_x", "objective_eur_per_year", "annual_h2_delivered_kg", "lcoh_eur_per_kg_h2"))
        fig = plotting.oat_curve_figure(frame, parameter="h2_demand_multiplier", metric="objective_eur_per_year",
                                        title="Hamburg · D0 · Nachfrage-Neuauslegung 2024")
        fig.savefig(out / "quantity_graph.png", dpi=150)
        artifacts.append("quantity_graph.png")
        plt.close(fig)
        return {"native_points": len(frame), "unique_embedded_100_percent_bases": 3,
                "homogeneous_cost_rtol": 1e-6, "claim": "Linear model scaling, not industrial economies of scale."}

    check("real_quantity_embedded_basis_and_linear_model_scaling", quantity_homogeneity)

    def quantity_foreign_basis():
        data = holder["quantity_input"].copy(deep=True)
        base_rows = pd.to_numeric(data.sensitivity_value).eq(1)
        require(int(base_rows.sum()) == 3, "Expected three native demand 100% rows before rejection probe.")
        data.loc[base_rows, "__native_configuration_sha256"] = "unrelated_quantity_configuration"
        try:
            contracts.prepare_oat_frame(data, parameter="h2_demand_multiplier", metric="objective_eur_per_year")
        except ValueError:
            return "An embedded 100% row also needs its own native unchanged configuration."
        raise AssertionError("A foreign embedded quantity basis was accepted.")

    check("foreign_embedded_quantity_basis_is_rejected", quantity_foreign_basis)

    basis_dir = source / "outputs_h2/eu_case_studies/historical_2024/verification_runs/basis_20261004_121938UTC/runs/hamburg_moorburg/D0"
    remember(basis_dir / "scenario_comparison.csv")
    bundle = result_loader.load_result_directory(basis_dir, source, include_hourly=True)
    for directory in bundle.summary.__result_directory:
        for filename in ("summary.csv", "run_metadata.json", "hourly_operation.csv"):
            remember(Path(directory) / filename)

    def controlled_cases():
        ref = next(ref for ref in site.result_sources if ref.profile == "D0")
        frame = result_loader._read_registered_reference(registry, ref, site)
        frame = collapse_duplicate_results(frame, source, validation_lookup=lambda path:
                                           result_loader.validation_for_result(path, source))
        caption = contracts.comparison_design(frame)
        require(caption.startswith("Kontrollierter Szenarienvergleich"),
                "True native same-input S0/S1/S2 is not recognized.")
        defaults = contracts.controlled_scenario_defaults(frame)
        require(len(defaults) == 3, "Default is not the proven complete three-scenario group.")
        mixed = frame.copy(deep=True)
        mixed.loc[mixed.index[-1], "demand_profile"] = "D2"
        require(contracts.comparison_design(mixed).startswith("Deskriptive"),
                "Changing the profile still claims an isolated scenario effect.")
        return caption

    check("real_scenario_design_and_mixed_profile_classification", controlled_cases)

    def emission_reference():
        frame = bundle.summary
        fig = plotting.emissions_figure(frame)
        operational, regulatory = fig.axes
        limits = [line for line in regulatory.lines if line.get_linestyle() == "--"]
        require(not [line for line in operational.lines if line.get_linestyle() == "--"],
                "A product reference was added to the operational electricity partial balance.")
        require(len(limits) == 1, "Identical native references produce multiple limit lines.")
        native_reference = float(frame.red_iii_maximum_product_intensity_kg_co2e_per_kg_h2.iloc[0])
        np.testing.assert_allclose(limits[0].get_ydata(), [native_reference, native_reference])
        require(regulatory.get_ylim()[1] >= native_reference, "The reference is outside the visible axis.")
        for ax, field in ((operational, "operational_emission_intensity_kg_co2e_per_kg_h2"),
                          (regulatory, "regulatory_emission_intensity_kg_co2e_per_kg_h2")):
            np.testing.assert_allclose([bar.get_height() for bar in ax.patches], frame[field])
        roundtrip(frame, "emission_graph_data.csv",
                  ("operational_emission_intensity_kg_co2e_per_kg_h2",
                   "regulatory_emission_intensity_kg_co2e_per_kg_h2",
                   "red_iii_maximum_product_intensity_kg_co2e_per_kg_h2"))
        fig.savefig(out / "emission_graph.png", dpi=150)
        artifacts.append("emission_graph.png")
        plt.close(fig)
        return {"regulatory_reference": native_reference, "operational_reference_lines": 0}

    check("real_emissions_native_reference_and_data", emission_reference)

    def static_emission_factor():
        details = []
        for sid, hourly in bundle.hourly.items():
            require(hourly.grid_emission_factor_kg_co2e_per_mwh.nunique() == 1,
                    "The selected real historical case does not have the stated static factor.")
            row = bundle.summary.loc[bundle.summary.scenario_id.eq(sid)].iloc[0]
            expected = float(hourly.grid_import_mwh.sum()) * float(hourly.grid_emission_factor_kg_co2e_per_mwh.iloc[0])
            np.testing.assert_allclose(expected, float(row.annual_grid_emissions_kg_co2e), rtol=1e-9)
            details.append({"scenario": sid, "static_factor": float(hourly.grid_emission_factor_kg_co2e_per_mwh.iloc[0]),
                            "native_annual_emissions": float(row.annual_grid_emissions_kg_co2e)})
        return details

    check("real_static_operational_emissions_follow_grid_import", static_emission_factor)

    def native_hourly_export():
        frame = plotting.hourly_frame(bundle, start="2024-01-02 00:00", hours=24,
                                      timezone="Europe/Berlin")
        require(len(frame) == 72, "Expected 24 native intervals per scenario.")
        native_fields = list(next(iter(bundle.hourly.values())).columns)
        for sid, rows in frame.groupby("selection_scenario_id"):
            native = bundle.hourly[sid]
            t = pd.to_datetime(native.timestamp, utc=True)
            selected = native.loc[t >= pd.Timestamp("2024-01-02", tz="Europe/Berlin").tz_convert("UTC")].head(24)
            for field in native_fields:
                if field != "timestamp":
                    np.testing.assert_allclose(rows[field], selected[field], rtol=1e-12, atol=1e-12)
            require(set(rows.selection_scenario_id) == {sid}, "Hourly selection changes its case.")
        roundtrip(frame, "hourly_graph_data.csv", tuple(field for field in native_fields if field != "timestamp"))
        fig = plotting.hourly_figure(frame, timezone="Europe/Berlin")
        require(len(fig.axes) == 9, "Expected three native scenario rows and three physical panels.")
        fig.savefig(out / "hourly_graph.png", dpi=120)
        artifacts.append("hourly_graph.png")
        plt.close(fig)
        return {"native_intervals": len(frame), "scenarios": 3, "hours_per_scenario": 24}

    check("real_hourly_graph_frame_matches_native_csv", native_hourly_export)

    def metric_roles():
        offered = plotting.available_metrics(bundle.summary)
        require(not set(offered).intersection(plotting.REFERENCE_METRICS), "Reference is offered as an ordinary result curve.")
        require(not set(offered).intersection(plotting.DIAGNOSTIC_METRICS), "Diagnostic is offered as an ordinary result curve.")
        all_roles = plotting.available_metrics(bundle.summary, roles=("result", "reference", "diagnostic"))
        require(set(all_roles) == set(plotting.METRICS).intersection(bundle.summary.columns),
                "Native result/reference/diagnostic values were lost.")
        return {"ordinary_result_metrics": len(offered), "preserved_native_metrics": len(all_roles)}

    check("result_reference_and_diagnostic_roles", metric_roles)

    def original_hashes_unchanged():
        changed = [path for path, before in tracked.items() if sha(path) != before]
        require(not changed, "Original source files changed during the read-only audit: " + str(changed))
        return {"checked_original_files": len(tracked), "changed_files": 0}

    check("original_files_unchanged", original_hashes_unchanged)
    report = {"date": "2026-10-11", "purpose": "Independent scientific U1 audit of selected real native exports",
              "source_root": str(source), "code_root": str(STAGE), "python": sys.executable,
              "no_new_optimizations": True, "not_product_acceptance": True,
              "scope": "Hamburg D0 common price/WACC/PV OAT, original EU price/WACC OAT, original Namibia constant price, 50-150% demand and fresh historical 2024 S0/S1/S2 exports",
              "checks": checks, "passed": sum(item["passed"] for item in checks), "total": len(checks),
              "source_sha256": tracked,
              "code_sha256": {name: sha(STAGE / "gui" / name) for name in
                              ("analysis_contracts.py", "plotting.py", "result_loader.py", "app.py")},
              "artifacts": artifacts,
              "limits": ["No browser or user acceptance test.", "No multi-year robustness or new legal verification.",
                         "No U2-U4 job lifecycle, installation or exhaustive family acceptance."]}
    (out / "scientific_audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown = ["# Unabhängige wissenschaftliche U1-Prüfung", "", "**11. Oktober 2026 · Gezielte reale Ergebnisprüfung; keine Produktabnahme.**", "",
                f"Bestanden: **{report['passed']}/{report['total']}**. Quellen: bestehende Hamburger D0-Preis-/WACC-/PV-OAT, ursprüngliche EU-/Namibia-OAT, 50–150-%-Nachfrage und frische historische S0/S1/S2-Fälle 2024. Keine neue Optimierung.", "",
                "| Prüfung | Ergebnis |", "|---|---|"]
    markdown += [f"| {item['name']} | {'Bestanden' if item['passed'] else 'FEHLER'} |" for item in checks]
    markdown += ["", "Vollständige Einzelbefunde, Quellhashes und geprüfter Codestand stehen in [scientific_audit.json](scientific_audit.json).",
                 "", "Grenzen: keine Browser-/Nutzerabnahme, keine neue Rechtsprüfung, keine mehrjährige Robustheit, keine U2–U4-Auftrags- oder Geräteprüfung.", ""]
    (out / "SCIENTIFIC_AUDIT.md").write_text("\n".join(markdown), encoding="utf-8")
    print(json.dumps({"passed": report["passed"], "total": report["total"],
                      "failed": [item for item in checks if not item["passed"]],
                      "report": str(out / "scientific_audit.json")}, ensure_ascii=False))
    return 0 if report["passed"] == report["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
