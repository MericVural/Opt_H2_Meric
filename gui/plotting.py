"""Matplotlib views of saved exports. Plotting never calls an optimization runner."""
from __future__ import annotations

import textwrap
from zoneinfo import ZoneInfo

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import numpy as np
import pandas as pd

from plot_h2_results import COST_COMPONENTS, SCENARIO_COLORS, _apply_plot_style
from .result_loader import ResultBundle, derived_operational_metrics

METRICS = {
    "lcoh_eur_per_kg_h2": "LCOH [EUR/kg gelieferter H₂]",
    "objective_eur_per_year": "Jahreskosten [EUR/a]",
    "pv_capacity_mw": "PV-Leistung [MW]", "wind_capacity_mw": "Windleistung [MW]",
    "electrolyzer_capacity_mw": "PEM-Leistung [MW]", "compressor_capacity_mw": "Kompressorleistung [MW]",
    "h2_storage_capacity_kg": "H₂-Speicher [kg]", "annual_grid_import_mwh": "Netzbezug [MWh/a]",
    "annual_h2_delivered_kg": "Gelieferte H₂-Jahresmenge [kg/a]",
    "annual_h2_produced_kg": "Produzierte H₂-Jahresmenge [kg/a]",
    "annual_grid_emissions_kg_co2e": "Betriebliche Stromemissionen [kg CO₂e/a]",
    "operational_emission_intensity_kg_co2e_per_kg_h2": "Betriebliche Stromteilbilanz [kg CO₂e/kg H₂]",
    "annual_regulatory_non_renewable_electricity_mwh": "Regulatorischer nicht erneuerbarer Strom [MWh/a]",
    "annual_regulatory_emissions_kg_co2e": "Regulatorische Stromemissionen [kg CO₂e/a]",
    "regulatory_emission_intensity_kg_co2e_per_kg_h2": "Regulatorische Stromteilbilanz [kg CO₂e/kg H₂]",
    "regulatory_emission_intensity_g_co2e_per_mj_h2": "Regulatorische Stromteilbilanz [g CO₂e/MJ H₂]",
    "red_iii_ghg_savings_fraction": "Regulatorische THG-Einsparung [Anteil]",
    "red_iii_maximum_product_intensity_kg_co2e_per_kg_h2": "Regulatorische THG-Grenze [kg CO₂e/kg H₂]",
    "red_iii_maximum_product_intensity_g_co2e_per_mj": "Regulatorische THG-Grenze [g CO₂e/MJ H₂]",
    "solver_runtime_seconds": "Solverlaufzeit [s]",
    "optimality_gap_fraction": "Optimalitätslücke [Anteil]",
    "max_electricity_balance_residual_mwh": "Maximales Strombilanzresiduum [MWh]",
    "max_hydrogen_balance_residual_kg": "Maximales H₂-Bilanzresiduum [kg]",
    "annual_cost_balance_residual_eur_per_year": "Kostenbilanzresiduum [EUR/a]",
    "max_red_iii_temporal_deficit_mwh": "Maximales zeitliches EE-Deckungsdefizit [MWh]",
    "physical_direct_renewable_share": "Direkte EE-Nutzung am Bedarf [Anteil]",
    "annual_curtailment_mwh": "PV-/Wind-Abregelung [MWh/a]",
}
PARAMETER_TITLES = {
    "h2_demand_multiplier": "H₂-Jahresnachfrage [% der Basis]",
    "h2_delivery_profile": "H₂-Lieferprofil",
    "demand_profile": "H₂-Lieferprofil",
    "electricity_price_offset_eur_per_mwh": "Strompreisoffset [EUR/MWh]",
    "electricity_price_eur_per_mwh": "Strompreis [EUR/MWh]",
    "real_wacc_shift_fraction": "WACC-Verschiebung [Prozentpunkte]",
    "uniform_real_wacc_fraction": "Einheitlicher realer WACC [%]",
    "real_wacc_multiplier": "WACC-Faktor",
    "pv_capex_eur_per_kw": "PV-CAPEX [EUR 2023/kW]",
    "wind_capex_eur_per_kw": "Wind-CAPEX [EUR 2023/kW]",
    "h2_storage_capex_eur_per_kg_h2": "H₂-Speicher-CAPEX [EUR 2023/kg]",
    "electrolyzer_capex_eur_per_kw": "PEM-CAPEX [EUR 2023/kW]",
    "electrolyzer_specific_electricity_kwh_per_kg_h2": "PEM-Strombedarf [kWh/kg H₂]",
    "electrolyzer_capex_factor": "PEM-CAPEX: Faktor relativ zum Basiswert",
    "electrolyzer_specific_electricity_factor": "PEM-Strombedarf: Faktor relativ zum Basiswert",
}

CHART_TYPES = ("Balkendiagramm", "Liniendiagramm", "Gruppierte Balken")
GROUP_TITLES = {"scenario_id": "Szenario", "demand_profile": "Lieferprofil",
                "site_label": "Standort", "site_id": "Standort", "solver_name": "Solver"}
MAX_COMPARISON_CASES = 12
MAX_SENSITIVITY_CURVES = 12
DAILY_ELECTRICITY_BASES = ("Direktversorgung", "Erzeugung und Netzbezug")
DAILY_ELECTRICITY_MODES = ("Stündlicher Tagesverlauf", "Kumulative Tagesenergie")


def _text(value):
    return "" if pd.isna(value) else str(value).strip()


def _short(value, width=22):
    """Bound category labels; the accompanying table retains their full text."""
    value = _text(value)
    aliases = {"hamburg_moorburg": "Hamburg", "andalusia_huelva": "Huelva",
               "huelva_la_rabida": "Huelva", "reference": "S0",
               "red_monthly": "S1", "red_hourly": "S2", "off_grid": "S3"}
    value = aliases.get(value, value)
    return value[:width-1]+"…" if len(value) > width else value


def case_label_table(frame):
    """Mapping for short figure labels, without modifying or aggregating exports."""
    data = _frame(frame)
    rows = []
    for i, row in data.iterrows():
        rows.append({"Diagrammfall": f"F{i+1:02d}",
                     "Standort": _text(row.get("site_label", row.get("site_id", ""))),
                     "Szenario": _text(row.get("scenario_id", row.get("scenario", ""))),
                     "Lieferprofil": _text(row.get("demand_profile", row.get("profile", ""))),
                     "Solver": _text(row.get("solver_name", "")),
                     "Versuchsfall": _text(row.get("case_label", row.get("case_id", ""))),
                     "Ergebnisordner": _text(row.get("__result_directory", row.get("result_directory", "")))})
    return pd.DataFrame(rows)


def available_metrics(frame):
    """Known metric names present in saved exports, in the established order."""
    data = _frame(frame)
    return {column: label for column, label in METRICS.items() if column in data}


def _figure_size(count, *, height=6.0):
    return (max(8.0, min(16.0, 6.4 + count*.7)), height)


def _set_categories(ax, positions, labels):
    rotation = 28 if len(labels) > 6 else 0
    if len(labels) > 8 and all(label.startswith("F") and " · " in label for label in labels):
        labels = [label.split(" · ", 1)[0] for label in labels]
    ax.set_xticks(positions, labels, rotation=rotation,
                  ha="right" if rotation else "center", fontsize=8.5 if len(labels) > 8 else 9)


def _metric_note(metric):
    if "emission" in metric or "co2e" in metric or metric.startswith("red_iii"):
        return ("Betriebliche und regulatorische Stromteilbilanz getrennt betrachten; regulatorische Null bedeutet "
                "keine physische Emissionsfreiheit. Keine vollständige LCA oder RFNBO-Zertifizierung.")
    if "capacity" in metric:
        return ("Gespeicherte optimale Kapazitäten. Gleichwertige optimale Lösungen können unterschiedliche "
                "Kapazitäten und Betriebsverläufe besitzen.")
    return "Gespeicherte Modellwerte; Bezugsjahre, Preisbasis und Proxyannahmen der ausgewählten Fälle beachten."


def _frame(value):
    data = value.summary if isinstance(value, ResultBundle) else value
    if not isinstance(data, pd.DataFrame) or data.empty:
        raise ValueError("Keine gespeicherten Ergebnisfälle ausgewählt.")
    return data.reset_index(drop=True)


def _labels(data):
    labels = []
    varying_solver = "solver_name" in data and data.solver_name.fillna("").nunique() > 1
    for i, row in data.iterrows():
        site = _short(row.get("site_label", row.get("site_id", "")))
        scenario = _short(row.get("scenario_id", row.get("scenario", f"Fall {i+1}")))
        profile = _short(row.get("demand_profile", row.get("profile", "")))
        parts = [f"F{i+1:02d}" + (" · "+site if site else ""), " · ".join(p for p in (scenario, profile) if p)]
        if varying_solver:
            parts.append(_short(row.get("solver_name", "")) or "Solver nicht belegt")
        labels.append("\n".join(parts))
    return labels


def _colors(data):
    return [SCENARIO_COLORS.get(_short(row.get("scenario_id", row.get("scenario", ""))), "#475569") for _, row in data.iterrows()]


def _note(fig, message):
    fig.text(.015, .012, textwrap.fill(message, width=max(65, int(fig.get_figwidth()*13))),
             fontsize=8.3, color="#64748b", va="bottom")


def _require(data, columns):
    missing = sorted(set(columns)-set(data.columns))
    if missing:
        raise ValueError("Größe nicht in diesem Export verfügbar: " + ", ".join(missing))


def _selected_cases(frame, metric):
    data = _frame(frame)
    _require(data, [metric])
    if len(data) > MAX_COMPARISON_CASES:
        raise ValueError(f"Für ein lesbares Diagramm höchstens {MAX_COMPARISON_CASES} Fälle auswählen oder eine weitere Seite anzeigen.")
    values = pd.to_numeric(data[metric], errors="raise")
    if not np.isfinite(values.to_numpy(dtype=float)).all():
        raise ValueError("Für die gewählte Kennzahl liegen nicht für alle ausgewählten Fälle bewertete Werte vor.")
    return data, values


def _type(value):
    mapping = {"bar": "Balkendiagramm", "line": "Liniendiagramm", "grouped": "Gruppierte Balken",
               "Gruppiertes Balkendiagramm": "Gruppierte Balken", "Gruppierter Vergleich": "Gruppierte Balken"}
    chart_type = mapping.get(value, value)
    if chart_type not in CHART_TYPES:
        raise ValueError("Nicht unterstützter Diagrammtyp: " + str(value))
    return chart_type


def _dimension_columns(data, excluded=()):
    columns = []
    for candidates in (("site_label", "site_id"), ("scenario_id", "scenario"),
                       ("demand_profile", "profile"), ("solver_name",), ("case_id", "case_label")):
        if any(candidate in excluded for candidate in candidates):
            continue
        column = next((candidate for candidate in candidates if candidate in data), None)
        if column and column not in excluded and data[column].fillna("").nunique() > 1:
            columns.append(column)
    return columns


def _grouped_figure(data, metric, *, group_by, x_column=None, title=None, chart_type="Gruppierte Balken"):
    _require(data, [group_by])
    group_values = list(dict.fromkeys(data[group_by].map(_text)))
    if len(group_values) > 6:
        raise ValueError("Höchstens sechs Gruppen auswählen, damit Legende und Balken lesbar bleiben.")
    dimension_columns = [x_column] if x_column else _dimension_columns(data, excluded=(group_by,))
    x_keys = []
    x_labels = []
    entries = {}
    for _, row in data.iterrows():
        key = tuple(_text(row[col]) for col in dimension_columns) if dimension_columns else ("Ausgewählte Fälle",)
        group = _text(row[group_by])
        pair = (key, group)
        if pair in entries:
            raise ValueError("Mehrere Fälle haben dieselbe Diagrammgruppe. Eine Versuchsreihe auswählen oder die Fallauswahl eingrenzen.")
        if key not in x_keys:
            x_keys.append(key)
            x_labels.append("\n".join(_short(part) for part in key))
        entries[pair] = float(row[metric])
    fig, ax = plt.subplots(figsize=_figure_size(len(x_keys), height=6.4))
    x = np.arange(len(x_keys))
    width = .78/max(len(group_values), 1)
    palette = ("#2563eb", "#16a34a", "#7c3aed", "#eab308", "#0891b2", "#db2777")
    markers = ("o", "s", "^", "D", "v", "P")
    for i, group in enumerate(group_values):
        values = np.array([entries.get((key, group), np.nan) for key in x_keys])
        color = SCENARIO_COLORS.get(_short(group), palette[i])
        label = _short(group, width=35) or "Nicht belegt"
        if chart_type == "Liniendiagramm":
            ax.plot(x, values, color=color, marker=markers[i], linestyle=":", label=label)
        else:
            ax.bar(x+(i-(len(group_values)-1)/2)*width, values, width=width, color=color, label=label)
    _set_categories(ax, x, x_labels)
    ax.set_ylabel(METRICS.get(metric, metric))
    ax.set_xlabel(PARAMETER_TITLES.get(x_column, "Ausgewählte Vergleichsfälle") if x_column else "Ausgewählte Vergleichsfälle")
    ax.set_title(title or METRICS.get(metric, metric))
    ax.legend(title=GROUP_TITLES.get(group_by, group_by), frameon=False,
              loc="upper center", bbox_to_anchor=(.5, 1.18), ncols=min(3, len(group_values)), fontsize=8.5)
    _note(fig, _metric_note(metric) + (" Punktverbindungen zeigen nur die ausgewählten Kategorien." if chart_type == "Liniendiagramm" else ""))
    fig.tight_layout(rect=(0, .13, 1, .94))
    return fig


def comparison_figure(frame, *, metric="lcoh_eur_per_kg_h2", chart_type="Balkendiagramm", group_by=None, title=None):
    """One selected metric and explicit cases; no model calculations or averaging."""
    data, values = _selected_cases(frame, metric)
    chart_type = _type(chart_type)
    _apply_plot_style()
    if chart_type == "Gruppierte Balken":
        grouping = group_by or next((column for column in ("scenario_id", "demand_profile", "site_label", "solver_name")
                                    if column in data and data[column].nunique() > 1), None)
        if grouping is None:
            raise ValueError("Für gruppierte Balken eine vorhandene Vergleichsdimension auswählen.")
        return _grouped_figure(data, metric, group_by=grouping, title=title)
    if chart_type == "Liniendiagramm" and group_by:
        return _grouped_figure(data, metric, group_by=group_by, title=title, chart_type=chart_type)
    fig, ax = plt.subplots(figsize=_figure_size(len(data)))
    x = np.arange(len(data))
    if chart_type == "Liniendiagramm":
        ax.plot(x, values, marker="o", linestyle=":", color="#2563eb")
        ax.scatter(x, values, color=_colors(data), zorder=3)
    else:
        bars = ax.bar(x, values, color=_colors(data), width=.65)
        if len(data) <= 6:
            ax.bar_label(bars, fmt="%.3g", padding=5, fontsize=9)
    _set_categories(ax, x, _labels(data))
    ax.set_ylabel(METRICS.get(metric, metric))
    ax.set_xlabel("Ausgewählte Vergleichsfälle · vollständige Namen in der Fallzuordnung")
    ax.set_title(title or METRICS.get(metric, metric))
    ax.margins(y=.18)
    _note(fig, _metric_note(metric) + (" Punktverbindungen dienen nur der Orientierung zwischen Kategorien." if chart_type == "Liniendiagramm" else ""))
    fig.tight_layout(rect=(0, .13, 1, 1))
    return fig


def profile_comparison_figure(frame, *, metric="lcoh_eur_per_kg_h2", chart_type="Gruppierte Balken", group_by="scenario_id", title=None):
    """Categorical D0/D1/D2 sensitivity; x positions are no numeric interpolation."""
    data, _ = _selected_cases(frame, metric)
    profile_column = "demand_profile" if "demand_profile" in data else "profile"
    _require(data, [profile_column])
    chart_type = _type(chart_type)
    if group_by == profile_column:
        raise ValueError("Das Lieferprofil steht bereits auf der x-Achse; eine andere Gruppierung wählen.")
    _apply_plot_style()
    data = data.sort_values(profile_column, kind="stable")
    return _grouped_figure(data, metric, group_by=group_by, x_column=profile_column,
                           chart_type="Liniendiagramm" if chart_type == "Liniendiagramm" else "Gruppierte Balken",
                           title=title or "Kategorischer Vergleich der H₂-Lieferprofile")


def lcoh_figure(frame, *, title="Wasserstoffgestehungskosten"):
    data = _frame(frame)
    _require(data, ["lcoh_eur_per_kg_h2"])
    _apply_plot_style()
    fig, ax = plt.subplots(figsize=_figure_size(len(data), height=5.8))
    vals = data.lcoh_eur_per_kg_h2.to_numpy(dtype=float)
    bars = ax.bar(np.arange(len(data)), vals, color=_colors(data), width=.65)
    ax.bar_label(bars, labels=[f"{v:.3f}".replace(".", ",") for v in vals], padding=5)
    _set_categories(ax, np.arange(len(data)), _labels(data))
    ax.set_ylim(0, max(vals)*1.22)
    ax.set_ylabel(METRICS["lcoh_eur_per_kg_h2"])
    ax.set_title(title)
    _note(fig, "Gespeicherte Modellkosten je geliefertem kg; Bezugsjahre/Preisproxygrenzen in Fallstudie und Vergleichskontext beachten.")
    fig.tight_layout(rect=(0,.12,1,1))
    return fig


def capacity_figure(frame, *, title="Optimale Anlagenkapazitäten"):
    data = _frame(frame)
    cols = ["pv_capacity_mw", "wind_capacity_mw", "electrolyzer_capacity_mw", "compressor_capacity_mw", "h2_storage_capacity_kg"]
    _require(data, cols)
    _apply_plot_style()
    fig, (ax, tank) = plt.subplots(1, 2, figsize=(14, 6.1), gridspec_kw={"width_ratios": [2,1]})
    x = np.arange(len(data))
    for i, (col, name, color) in enumerate(zip(cols[:-1], ("PV", "Wind", "PEM", "Kompressor"), ("#eab308", "#0891b2", "#2563eb", "#8b5cf6"), strict=True)):
        ax.bar(x+(i-1.5)*.18, data[col], width=.18, color=color, label=name)
    ax.set_ylabel("Installierte Leistung [MW]")
    ax.legend(ncols=2, frameon=False)
    tank.bar(x, data.h2_storage_capacity_kg/1000, color=_colors(data), width=.64)
    tank.set_ylabel("Nutzbarer H₂-Speicher [t]")
    for a in (ax, tank):
        _set_categories(a, x, _labels(data))
        a.set_ylim(bottom=0)
    fig.suptitle(title, fontsize=15, fontweight="bold")
    _note(fig, "Kontinuierliche optimale Modellkapazitäten. Gleichwertige Lösungen können abweichende Kapazitäten/Dispatchwerte besitzen.")
    fig.tight_layout(rect=(0,.12,1,.94))
    return fig


def cost_components_figure(frame, *, title="LCOH-Kostenbestandteile"):
    data = _frame(frame)
    _require(data, ["annual_h2_delivered_kg", "lcoh_eur_per_kg_h2", *[col for _,_,cols,_ in COST_COMPONENTS for col in cols]])
    _apply_plot_style()
    fig, ax = plt.subplots(figsize=_figure_size(len(data), height=6.8))
    x, positive, negative = np.arange(len(data)), np.zeros(len(data)), np.zeros(len(data))
    for _, name, columns, color in COST_COMPONENTS:
        vals = data[list(columns)].sum(axis=1).to_numpy()/data.annual_h2_delivered_kg.to_numpy()
        ax.bar(x, vals, bottom=np.where(vals >= 0, positive, negative), color=color, label=name, width=.65)
        positive += np.maximum(vals, 0)
        negative += np.minimum(vals, 0)
    for i, value in enumerate(data.lcoh_eur_per_kg_h2):
        ax.text(i, positive[i]+.025, f"Σ {value:.3f}".replace(".", ","), ha="center", va="bottom")
    ax.axhline(0, color="#64748b", linewidth=.8)
    ax.set_ylim(min(-.25, negative.min()*1.5), positive.max()*1.22)
    _set_categories(ax, x, _labels(data))
    ax.set_ylabel("Kostenbeitrag [EUR/kg gelieferter H₂]")
    ax.set_title(title)
    ax.legend(ncols=3, frameon=False, loc="upper center", bbox_to_anchor=(.5,-.14))
    _note(fig, "Σ: Nettosumme. Positive und negative Kosten getrennt ab null; negative Importkosten sind keine Exportvergütung.")
    fig.tight_layout(rect=(0,.18,1,1))
    return fig


def emissions_figure(frame, *, title="Emissionen mit getrennten Bilanzgrenzen"):
    data = _frame(frame)
    _apply_plot_style()
    fig, axes = plt.subplots(1, 2, figsize=(14, 6.3))
    specifications = [("operational_emission_intensity_kg_co2e_per_kg_h2", "Betriebliche Stromteilbilanz"),
        ("regulatory_emission_intensity_kg_co2e_per_kg_h2", "Regulatorische Stromteilbilanz")]
    maxima = []
    for field, _ in specifications:
        if field in data:
            maxima.extend(pd.to_numeric(data[field], errors="coerce").dropna())
    bound = max(max(maxima, default=0), .1)*1.22
    for ax, (field, label) in zip(axes, specifications, strict=True):
        if field in data:
            vals = pd.to_numeric(data[field], errors="coerce").to_numpy()
            shown = np.where(np.abs(vals) < 1e-10, 0, vals)
            bars = ax.bar(np.arange(len(data)), shown, color=_colors(data), width=.65)
            for i, (bar, val) in enumerate(zip(bars, shown, strict=True)):
                if np.isfinite(val):
                    ax.annotate(f"{val:.3f}".replace(".", ","), (bar.get_x()+bar.get_width()/2,val), xytext=(0,5), textcoords="offset points", ha="center", va="bottom", fontsize=9)
                else:
                    ax.text(i,.03*bound,"nicht bewertet",rotation=90,ha="center",va="bottom",fontsize=8)
        else:
            ax.text(.5,.5,"Nicht exportiert",ha="center",transform=ax.transAxes)
        _set_categories(ax, np.arange(len(data)), _labels(data))
        ax.set_ylim(0,bound)
        ax.set_title(label)
        ax.set_ylabel("kg CO₂e/kg gelieferter H₂")
    fig.suptitle(title,fontsize=15,fontweight="bold")
    _note(fig,"Regulatorische Null bedeutet keine physische Emissionsfreiheit. Fallbezogene Faktoren/Quellenjahre; keine vollständige LCA oder RFNBO-Zertifizierung.")
    fig.tight_layout(rect=(0,.15,1,.93))
    return fig


def operational_figure(bundle: ResultBundle, *, title="Betriebliche Kennzahlen"):
    derived=derived_operational_metrics(bundle)
    _require(derived,["annual_grid_import_mwh","physical_direct_renewable_share","annual_curtailment_mwh"])
    _apply_plot_style()
    fig,axes=plt.subplots(1,3,figsize=(14.4,6.0))
    for ax,col,label,divisor in zip(axes,("annual_grid_import_mwh","physical_direct_renewable_share","annual_curtailment_mwh"),
        ("Physischer Netzbezug [GWh/a]","Direkte EE-Nutzung am Bedarf [%]","PV-/Wind-Abregelung [GWh/a]"),(1000,.01,1000),strict=True):
        vals=derived[col]/divisor
        ax.bar(np.arange(len(derived)),vals,color=_colors(derived),width=.65)
        ax.set_xticks(np.arange(len(derived)),derived.scenario_id)
        ax.set_ylabel(label)
        ax.set_ylim(bottom=0)
    fig.suptitle(title,fontsize=15,fontweight="bold")
    _note(fig,"Aus gespeicherten Stundenwerten annualisierte Summen. Direkte EE-Nutzung ist keine regulatorische Überschusszuordnung.")
    fig.tight_layout(rect=(0,.12,1,.94))
    return fig


def _utc_start(value, timezone):
    """Interpret a naive UI timestamp in its display timezone, never as UTC."""
    try:
        local_zone=ZoneInfo(str(timezone))
        stamp=pd.Timestamp(value)
        if pd.isna(stamp):raise ValueError("Leere Startzeit")
        if stamp.tzinfo is None:
            stamp=stamp.tz_localize(local_zone,ambiguous="raise",nonexistent="raise")
        return stamp.tz_convert("UTC")
    except Exception as exc:
        error_name=type(exc).__name__
        if not isinstance(exc,(ValueError,TypeError,KeyError)) and error_name not in ("AmbiguousTimeError","NonExistentTimeError"):
            raise
        message=str(exc).lower()
        if error_name=="AmbiguousTimeError" or "ambiguous" in message or "infer dst" in message:
            raise ValueError("Die lokale Startzeit ist bei der Zeitumstellung mehrdeutig. Einen Zeitpunkt mit eindeutigem UTC-Offset angeben.") from exc
        if error_name=="NonExistentTimeError" or "nonexistent" in message or "does not exist" in message:
            raise ValueError("Die lokale Startzeit existiert wegen der Zeitumstellung nicht. Eine vorhandene Uhrzeit wählen.") from exc
        raise ValueError("Startzeit oder Zeitzone ist ungültig: "+str(exc)) from exc


def _local_day_bounds(day,timezone):
    try:
        stamp=pd.Timestamp(day)
        if pd.isna(stamp) or stamp.time()!=pd.Timestamp("00:00").time():
            raise ValueError("Tag als Kalenderdatum ohne Uhrzeit auswählen.")
        midnight=pd.Timestamp(stamp.date())
        start=_utc_start(midnight,timezone)
        # A calendar date offset is deliberately applied before localisation;
        # a fixed 24-hour offset would be wrong on both DST transition dates.
        end=_utc_start(midnight+pd.DateOffset(days=1),timezone)
        return start.tz_convert(timezone),end.tz_convert(timezone)
    except (ValueError,TypeError) as exc:
        raise ValueError("Lokaler Kalendertag kann nicht ausgewählt werden: "+str(exc)) from exc


def _day_axis(timestamps,start,end,timezone):
    """Use absolute tick positions and mark both occurrences of repeated hours."""
    boundaries=pd.DatetimeIndex([*timestamps,end])
    picks=set(range(0,len(boundaries),4))|{len(boundaries)-1}
    wall=boundaries.tz_localize(None)
    picks.update(np.flatnonzero(wall.duplicated(keep=False)))
    picks={index for index in picks if index==len(boundaries)-1 or end-boundaries[index]>=pd.Timedelta(hours=2)}
    ticks=boundaries[sorted(picks)]
    return ticks,[tick.strftime("%H:%M\n%Z")+("\nFolgetag" if tick==end else "") for tick in ticks]


def daily_electricity_frame(bundle: ResultBundle, *, day, scenario_id, timezone="UTC",basis="Direktversorgung"):
    """Select one complete local calendar day from one saved native scenario.

    Cumulative values are sums of the selected native hourly MWh and refer to
    interval ends. No annualisation, interpolation or optimisation is done.
    """
    if basis not in DAILY_ELECTRICITY_BASES:
        raise ValueError("Unbekannte Stromgrößen: "+str(basis))
    if not bundle.hourly:
        raise ValueError("Stundenexport wurde nicht geladen.")
    aliases={"reference":"S0","red_monthly":"S1","red_hourly":"S2","off_grid":"S3"}
    requested=aliases.get(str(scenario_id),str(scenario_id))
    matches=[key for key in bundle.hourly if aliases.get(str(key),str(key))==requested]
    if len(matches)!=1:
        raise ValueError("Das gewählte Szenario besitzt keinen eindeutigen geladenen Stundenexport.")
    native_key=matches[0]
    source=bundle.hourly[native_key]
    fields=("pv_self_consumption_mwh","wind_self_consumption_mwh","grid_import_mwh") if basis=="Direktversorgung" else ("pv_generation_mwh","wind_generation_mwh","grid_import_mwh")
    _require(source,["timestamp",*fields])
    try:timestamps=pd.to_datetime(source.timestamp,utc=True,errors="raise",format="mixed")
    except (ValueError,TypeError) as exc:raise ValueError("Der native Stundenexport enthält ungültige Zeitstempel.") from exc
    if timestamps.isna().any() or timestamps.duplicated().any() or not timestamps.is_monotonic_increasing:
        raise ValueError("Der native Stundenexport benötigt eindeutige aufsteigende Zeitstempel.")
    start,end=_local_day_bounds(day,timezone)
    start_utc,end_utc=start.tz_convert("UTC"),end.tz_convert("UTC")
    mask=(timestamps>=start_utc)&(timestamps<end_utc)
    selected=source.loc[mask].copy().reset_index(drop=True)
    chosen=pd.DatetimeIndex(timestamps.loc[mask])
    expected=pd.date_range(start_utc,end_utc,freq="h",inclusive="left")
    if not chosen.equals(expected):
        raise ValueError(f"Für den lokalen Tag {start.date()} liegen {len(selected)} von {len(expected)} erwarteten Stunden vor. Der Tag ist unvollständig; einen vollständig gespeicherten Tag wählen.")
    selected["display_timestamp"]=chosen.tz_convert(timezone)
    selected["display_interval_end"]=(chosen+pd.Timedelta(hours=1)).tz_convert(timezone)
    for name,field in zip(("pv","wind","grid"),fields,strict=True):
        values=pd.to_numeric(selected[field],errors="raise")
        if not np.isfinite(values.to_numpy(dtype=float)).all():
            raise ValueError("Die ausgewählten Stromwerte sind nicht vollständig bewertet.")
        selected["selected_"+name+"_mwh"]=values
        selected["cumulative_"+name+"_mwh"]=values.cumsum()
    if basis=="Direktversorgung":
        selected["cumulative_total_mwh"]=selected[["selected_pv_mwh","selected_wind_mwh","selected_grid_mwh"]].sum(axis=1).cumsum()
    selected["selection_day"]=str(start.date())
    selected["selection_timezone"]=str(timezone)
    selected["selection_scenario_id"]=requested
    selected["selection_native_scenario_key"]=str(native_key)
    selected["selection_basis"]=basis
    selected["selection_start_local"]=start.isoformat()
    selected["selection_end_local"]=end.isoformat()
    selected["selection_day_hours"]=len(expected)
    selected["selection_day_complete"]=True
    selected.attrs.update(basis=basis,scenario_id=requested,day=str(start.date()),timezone=str(timezone),
                          day_start=start,day_end=end,day_hours=len(expected),complete=True)
    return selected


def daily_electricity_figure(frame, *, mode="Stündlicher Tagesverlauf",timezone="UTC",title=None,include_total=True):
    """Draw one saved day; cumulative traces begin at zero and end at midnight."""
    data=_frame(frame)
    if mode not in DAILY_ELECTRICITY_MODES:
        raise ValueError("Unbekannte Tagesdarstellung: "+str(mode))
    required=["display_timestamp","display_interval_end","selection_day","selection_timezone","selection_basis",
              "selection_scenario_id","selected_pv_mwh","selected_wind_mwh","selected_grid_mwh",
              "cumulative_pv_mwh","cumulative_wind_mwh","cumulative_grid_mwh"]
    _require(data,required)
    for field in ("selection_day","selection_timezone","selection_basis","selection_scenario_id"):
        if data[field].nunique(dropna=False)!=1:
            raise ValueError("Für eine Tagesgrafik genau einen Tag, ein Szenario und einen Strombezug auswählen.")
    if str(data.selection_timezone.iloc[0])!=str(timezone):
        raise ValueError("Die Grafikzeitzone muss mit der Tagesauswahl übereinstimmen.")
    basis=str(data.selection_basis.iloc[0])
    if basis not in DAILY_ELECTRICITY_BASES:raise ValueError("Unbekannter Strombezug der Tagesauswahl.")
    start,end=_local_day_bounds(data.selection_day.iloc[0],timezone)
    starts=pd.DatetimeIndex(pd.to_datetime(data.display_timestamp,utc=True,format="mixed")).tz_convert(timezone)
    ends=pd.DatetimeIndex(pd.to_datetime(data.display_interval_end,utc=True,format="mixed")).tz_convert(timezone)
    expected=pd.date_range(start.tz_convert("UTC"),end.tz_convert("UTC"),freq="h",inclusive="left")
    if not starts.tz_convert("UTC").equals(expected) or not ends.equals(starts+pd.Timedelta(hours=1)):
        raise ValueError("Die Tagesgrafik benötigt alle gespeicherten Stunden des vollständigen lokalen Tages.")
    values=[]
    for name in ("pv","wind","grid"):
        flow=pd.to_numeric(data["selected_"+name+"_mwh"],errors="raise").to_numpy(dtype=float)
        cumulative=pd.to_numeric(data["cumulative_"+name+"_mwh"],errors="raise").to_numpy(dtype=float)
        if not np.isfinite(flow).all() or not np.isfinite(cumulative).all() or not np.allclose(cumulative,np.cumsum(flow),rtol=1e-12,atol=1e-9):
            raise ValueError("Kumulative Tagesenergie stimmt nicht mit den gespeicherten Stundenwerten überein.")
        values.append(flow)
    labels=("PV direkt","Wind direkt","Netzimport") if basis=="Direktversorgung" else ("PV-Erzeugung","Winderzeugung","Netzimport")
    colors=("#eab308","#0891b2","#f87171")
    _apply_plot_style()
    fig,ax=plt.subplots(figsize=(10.4,6.1))
    if mode=="Kumulative Tagesenergie":
        positions=pd.DatetimeIndex([start,*ends])
        for name,label,color in zip(("pv","wind","grid"),labels,colors,strict=True):
            ax.plot(positions,np.r_[0.,data["cumulative_"+name+"_mwh"].to_numpy(dtype=float)],label=label,color=color,linewidth=1.8)
        if include_total and basis=="Direktversorgung":
            ax.plot(positions,np.r_[0.,np.cumsum(np.sum(values,axis=0))],label="Direktversorgung gesamt",color="#111827",linestyle="--",linewidth=1.4)
        ax.set_ylabel("Kumulierte Tagesenergie [MWh]")
    else:
        positions=pd.DatetimeIndex([*starts,end])
        if basis=="Direktversorgung":
            ax.stackplot(positions,*[np.r_[flow,flow[-1]] for flow in values],step="post",labels=labels,colors=colors,alpha=.85)
            if "rf_nbo_electricity_mwh" in data:
                demand=pd.to_numeric(data.rf_nbo_electricity_mwh,errors="raise").to_numpy(dtype=float)
                if not np.isfinite(demand).all():raise ValueError("Strombedarf des ausgewählten Tages ist nicht vollständig bewertet.")
                ax.step(positions,np.r_[demand,demand[-1]],where="post",label="Strombedarf",color="#111827",linestyle="--",linewidth=1.25)
        else:
            for flow,label,color in zip(values,labels,colors,strict=True):
                ax.step(positions,np.r_[flow,flow[-1]],where="post",label=label,color=color,linewidth=1.6)
        ax.set_ylabel("Stündliche Strommenge [MWh]")
    ticks,tick_labels=_day_axis(starts,start,end,timezone)
    ax.set_xticks(ticks,tick_labels,fontsize=8.5)
    ax.set_xlim(start,end)
    ax.set_ylim(bottom=min(0.,min(float(np.min(flow)) for flow in values)))
    ax.set_xlabel("Lokale Zeit · "+str(timezone))
    sid=str(data.selection_scenario_id.iloc[0])
    fig.suptitle(title or f"{mode} · {start.date()} · {sid}",fontsize=14,fontweight="bold",y=.985)
    handles,legend_labels=ax.get_legend_handles_labels()
    fig.legend(handles,legend_labels,frameon=False,ncols=2,loc="upper center",bbox_to_anchor=(.5,.938),fontsize=9)
    meaning=("Direkte Stromversorgung des Modellbedarfs; Erzeugungsüberschüsse und Abregelung sind nicht enthalten." if basis=="Direktversorgung" else "Gesamte PV-/Winderzeugung und Netzimport getrennt; ihre Summe ist keine Strombedarfsbilanz.")
    timing=("Kumulierte Werte: 0 am Tagesbeginn, native MWh-Summe am jeweiligen Stundenende." if mode=="Kumulative Tagesenergie" else "Native Stundenwerte gelten ab Intervallbeginn; Folgetag 00:00 schließt den lokalen Tag ab.")
    _note(fig,f"Vollständiger lokaler Tag mit {len(data)} Stunden. {meaning} {timing} Ausgewählter Tag, kein repräsentatives Jahr.")
    fig.tight_layout(rect=(0,.16,1,.83))
    return fig


def hourly_figure(bundle: ResultBundle, *, start=None, hours=168, timezone="UTC", title="Stündlicher Betrieb"):
    if isinstance(hours,bool) or not isinstance(hours,int) or hours < 1:
        raise ValueError("hours muss eine positive ganze Zahl sein.")
    data=_frame(bundle)
    if not bundle.hourly:
        raise ValueError("Stundenexport wurde nicht geladen.")
    selected={}
    required=["timestamp","pv_self_consumption_mwh","wind_self_consumption_mwh","grid_import_mwh","rf_nbo_electricity_mwh","h2_production_kg","h2_demand_kg","h2_storage_level_kg"]
    for sid,h in bundle.hourly.items():
        _require(h,required)
        t=pd.to_datetime(h.timestamp,utc=True)
        chosen_start=_utc_start(start,timezone) if start is not None else t.iloc[0]
        w=h.loc[t >= chosen_start].head(hours).copy()
        if w.empty:
            raise ValueError("Keine Stundenwerte im gewählten Zeitraum.")
        w["display_timestamp"]=pd.to_datetime(w.timestamp,utc=True).dt.tz_convert(timezone)
        selected[sid]=w
    _apply_plot_style()
    fig,axes=plt.subplots(len(selected),3,figsize=(16,3*len(selected)+2),squeeze=False,sharex=True)
    emax=max(w.rf_nbo_electricity_mwh.max() for w in selected.values())*1.12
    hmax=max(w[["h2_production_kg","h2_demand_kg"]].max().max() for w in selected.values())/1000*1.12
    smax=max(w.h2_storage_level_kg.max() for w in selected.values())/1000*1.12
    for i,(sid,w) in enumerate(selected.items()):
        ending=w.display_timestamp.iloc[-1]+pd.Timedelta(hours=1)
        t=pd.DatetimeIndex(w.display_timestamp.tolist()+[ending])
        def stepped(col):return np.r_[w[col].to_numpy(),w[col].iloc[-1]]
        e,h,tank=axes[i]
        e.stackplot(t,stepped("pv_self_consumption_mwh"),stepped("wind_self_consumption_mwh"),stepped("grid_import_mwh"),step="post",colors=["#eab308","#0891b2","#f87171"],alpha=.83)
        e.step(t,stepped("rf_nbo_electricity_mwh"),where="post",color="#111827",linestyle="--",linewidth=1)
        e.set_ylim(0,max(emax,1))
        e.set_ylabel(sid+" · Strom [MWh/h]")
        h.step(t,stepped("h2_production_kg")/1000,where="post",color="#2563eb",linewidth=1.2)
        h.step(t,stepped("h2_demand_kg")/1000,where="post",color="#111827",linestyle="--",linewidth=1)
        h.set_ylim(0,max(hmax,.01))
        h.set_ylabel("H₂ [t/h]")
        state_time=w.display_timestamp+pd.Timedelta(hours=1)
        tank.plot(state_time,w.h2_storage_level_kg/1000,color="#7e22ce",linewidth=1.2)
        tank.set_ylim(0,max(smax,.01))
        tank.set_ylabel("Speicherfüllstand [t]")
        for ax in axes[i]:
            ax.set_xlim(w.display_timestamp.iloc[0],ending)
            # Absolute UTC tick placement avoids a zero wall-clock span for
            # 02:00 CEST -> 02:00 CET; labels retain the selected local zone.
            ax.xaxis.set_major_locator(mdates.AutoDateLocator(tz=ZoneInfo("UTC"),minticks=3,maxticks=7))
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m.\n%H:%M %Z",tz=ZoneInfo(str(timezone))))
            ax.tick_params(axis="x",rotation=25,labelsize=8)
    for ax,label in zip(axes[0],("Direkte Versorgung und Bedarf","H₂ vor Verlust / Lieferung","Stundenendbestand"),strict=True):
        ax.set_title(label)
    for ax in axes[-1]:ax.set_xlabel(timezone)
    fig.suptitle(title,fontsize=15,fontweight="bold")
    handles=[Patch(facecolor="#eab308",label="PV direkt"),Patch(facecolor="#0891b2",label="Wind direkt"),Patch(facecolor="#f87171",label="Netzimport"),Line2D([0],[0],color="#111827",linestyle="--",label="Strombedarf / H₂-Lieferung"),Line2D([0],[0],color="#2563eb",label="H₂ vor Verlust"),Line2D([0],[0],color="#7e22ce",label="Speicherfüllstand")]
    fig.legend(handles=handles,ncols=3,loc="upper center",bbox_to_anchor=(.5,.925),frameon=False,fontsize=9)
    _note(fig,"Gewählter Ausschnitt ist kein repräsentatives Jahr. Flüsse ab Stundenbeginn; Speicher am Stundenende t+1h; direkte EE-Nutzung getrennt von Zuordnung.")
    fig.tight_layout(rect=(0,.12,1,.82))
    return fig


def oat_curve_figure(frame, *, parameter: str, metric: str="lcoh_eur_per_kg_h2", title=None):
    data=_frame(frame)
    parameter_col="sensitivity_parameter" if "sensitivity_parameter" in data else "parameter"
    _require(data,[parameter_col,metric])
    selected=data.loc[data[parameter_col] == parameter].copy()
    if selected.empty:
        raise ValueError("Für diesen Parameter liegen keine berechneten Varianten vor.")
    if "__collection" in selected and selected["__collection"].nunique() > 1:
        raise ValueError("Eine Versuchsreihe auswählen: absolute Werte und relative Parameterfaktoren verschiedener Designs dürfen nicht dieselbe x-Achse teilen.")
    if parameter == "h2_demand_multiplier":
        # The native runner already computes the unmodified baseline once.
        # Include it at 100 % without producing another optimization or
        # double-adding accepted tables that already label it as demand 1.0.
        baseline=data.loc[data[parameter_col] == "baseline"].copy()
        if "__collection" in selected and selected["__collection"].nunique() == 1:
            baseline=baseline.loc[baseline["__collection"] == selected["__collection"].iloc[0]]
        for column in ("relative_level","sensitivity_value","value"):
            if column in data:baseline[column]=1.
        group_fields=[column for column in ("site_label","scenario_id","demand_profile","profile","solver_name") if column in selected]
        value_column="relative_level" if "relative_level" in selected and selected.relative_level.notna().all() else "sensitivity_value" if "sensitivity_value" in selected and selected.sensitivity_value.notna().all() else "value"
        already=selected.loc[pd.to_numeric(selected[value_column],errors="raise") == 1.]
        if group_fields and not already.empty:
            keys=set(tuple(row) for row in already[group_fields].fillna("").itertuples(index=False,name=None))
            baseline=baseline.loc[[tuple(row) not in keys for row in baseline[group_fields].fillna("").itertuples(index=False,name=None)]]
        elif not already.empty:
            baseline=baseline.iloc[:0]
        selected=pd.concat([selected,baseline],ignore_index=True)
    _apply_plot_style()
    profile_column="demand_profile" if "demand_profile" in selected else "profile"
    group_columns=[col for col in ("site_label","scenario_id",profile_column,"solver_name") if col in selected]
    if not group_columns:
        selected["__all"]="Berechnete Fälle"
        group_columns=["__all"]
    curves=list(selected.groupby(group_columns,dropna=False))
    if len(curves) > MAX_SENSITIVITY_CURVES:
        raise ValueError(f"Für ein lesbares Sensitivitätsdiagramm höchstens {MAX_SENSITIVITY_CURVES} Kurven auswählen; Standort, Profil oder Szenario eingrenzen.")
    fig,ax=plt.subplots(figsize=(10.6,6.1+max(0,len(curves)-3)*.13))
    x_column="relative_level" if "relative_level" in selected and selected.relative_level.notna().all() else ("sensitivity_value" if "sensitivity_value" in selected and selected.sensitivity_value.notna().all() else "value")
    _require(selected,[x_column])
    plotted_levels=set()
    for keys,group in curves:
        keys=keys if isinstance(keys,tuple) else (keys,)
        group=group.sort_values(x_column)
        x=pd.to_numeric(group[x_column],errors="raise")
        if parameter == "h2_demand_multiplier" or (x_column != "relative_level" and parameter in ("uniform_real_wacc_fraction","real_wacc_shift_fraction")):
            x=x*100
        y=pd.to_numeric(group[metric],errors="raise")
        if not np.isfinite(x).all() or not np.isfinite(y).all():
            raise ValueError("Die gewählte Versuchsreihe enthält unbewertete Versuchspunkte.")
        if x.duplicated().any():
            raise ValueError("Mehrere Versuchspunkte besitzen dieselbe Parameterstufe. Eine eindeutige Versuchsreihe auswählen.")
        plotted_levels.update(float(level) for level in x)
        sid=str(group.scenario_id.iloc[0]) if "scenario_id" in group else ""
        profile=str(group[profile_column].iloc[0]) if profile_column in group else ""
        marker={"D0":"o","D1":"s","D2":"^"}.get(profile,"o")
        label=" · ".join(_short(k,width=22) or "Nicht belegt" for k in keys)
        ax.plot(x,y,marker=marker,linestyle=":",color=SCENARIO_COLORS.get(sid),label=textwrap.fill(label,width=48))
    ax.set_xlabel(PARAMETER_TITLES[parameter] if parameter == "h2_demand_multiplier" else "Faktor relativ zum Basisparameter" if x_column == "relative_level" else PARAMETER_TITLES.get(parameter,parameter))
    ax.set_ylabel(METRICS.get(metric,metric))
    if len(plotted_levels) <= 12:
        ax.set_xticks(sorted(plotted_levels))
    ax.set_title(title or "OAT: gespeicherte Versuchspunkte")
    ax.legend(frameon=False,fontsize=8,loc="upper center",bbox_to_anchor=(.5,-.19),ncols=min(3,len(curves)))
    _note(fig,"Nur tatsächlich berechnete Punkte; gepunktete Verbindungen dienen der Orientierung, keine genaue Schwelle/Prognose. Unterschiedliche Versuchsreihen getrennt.")
    fig.tight_layout(rect=(0,.23+max(0,len(curves)-3)*.012,1,1))
    return fig


__all__=["METRICS","PARAMETER_TITLES","CHART_TYPES","GROUP_TITLES","MAX_COMPARISON_CASES",
         "case_label_table","available_metrics","comparison_figure","profile_comparison_figure",
         "lcoh_figure","capacity_figure","cost_components_figure","emissions_figure",
         "hourly_figure","operational_figure","oat_curve_figure","DAILY_ELECTRICITY_BASES",
         "DAILY_ELECTRICITY_MODES","daily_electricity_frame","daily_electricity_figure"]
