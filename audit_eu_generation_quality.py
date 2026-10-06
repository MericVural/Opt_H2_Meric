"""Reconcile REE five-minute power diagnostics with official REData daily energy.

The audit never scales, releases or fills a generation/emissions input. Daily
energy is a separate official publication, not proof that instantaneous power
samples are interval means or that both sources have identical coverage.
"""
from __future__ import annotations

import argparse
import calendar
import concurrent.futures
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlencode
from urllib.error import HTTPError

import pandas as pd

from acquire_eu_historical_sources import archive_response
from ree_historical_data import (
    PRIMARY_GENERATION_FIELDS, TIMEZONE, expected_day_index, parse_day,
    primary_generation_fields, report_quality,
)

DIRECT_MAPPING = {
    "gnhd": "10288", "nuc": "1446", "car": "10289", "cc": "1454",
    "eol": "10291", "solFot": "1458", "solTer": "1459", "vap": "1451",
    "gf": "10290",
}
EXPECTED_TITLES = {
    "10288": "Hidráulica", "1446": "Nuclear", "10289": "Carbón",
    "1454": "Ciclo combinado", "10291": "Eólica", "1458": "Solar fotovoltaica",
    "1459": "Solar térmica", "1451": "Turbina de vapor", "10296": "Generación total",
    "10290": "Fuel + Gas",
}
METADATA_URLS = {
    "ree_generation.html": "https://www.ree.es/es/datos/generacion",
    "ree_self_consumption.html": "https://www.ree.es/es/transicion-ecologica/autoconsumo",
    "ree_self_consumption_methodology.pdf": "https://www.ree.es/sites/default/files/2025-12/metodologia-autoconsumo-redelectrica.pdf",
    "ree_annual_generation_2025.html": "https://www.sistemaelectrico-ree.es/es/informe-del-sistema-electrico/generacion/generacion-de-energia-electrica/generacion-total-de-energia-electrica",
    "abono_conversion_environmental_decision_2024.pdf": "https://www.boe.es/boe/dias/2024/05/20/pdfs/BOE-A-2024-10144.pdf",
    "abono_conversion_operator_2025.html": "https://www.edp.com/es/europa/espana/media/news/edp-y-corporacion-masaveu-concluyen-la-conversion-de-la-central-de-abono",
}


class GenerationAuditError(ValueError):
    """Source provenance, schema or a reporting boundary is invalid."""


def redata_url(year: int, month: int, *, trunc: str = "day", day: int | None = None) -> str:
    if trunc not in {"day", "hour"}:
        raise GenerationAuditError("Only explicit day/hour probes are supported")
    first = f"{year}-{month:02d}-{day or 1:02d}"
    last = f"{year}-{month:02d}-{day or calendar.monthrange(year, month)[1]:02d}"
    query = {
        "start_date": first + "T00:00", "end_date": last + "T23:59",
        "time_trunc": trunc, "geo_trunc": "electric_system",
        "geo_limit": "peninsular", "geo_ids": "8741",
    }
    return "https://apidatos.ree.es/es/datos/generacion/estructura-generacion?" + urlencode(query)


def verified_bytes(path: Path, expected_url: str, *, allowed_http_status: tuple[int, ...] = (200,)) -> tuple[bytes, dict]:
    receipt_path = path.with_suffix(path.suffix + ".receipt.json")
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        data = path.read_bytes()
    except (OSError, json.JSONDecodeError) as exc:
        raise GenerationAuditError(f"Missing/invalid archive and receipt: {path}") from exc
    if (receipt.get("source_url") != expected_url or receipt.get("http_status") not in allowed_http_status
            or receipt.get("sha256") != hashlib.sha256(data).hexdigest()
            or receipt.get("bytes") != len(data) or not receipt.get("retrieved_utc")):
        raise GenerationAuditError(f"Archive/receipt provenance mismatch: {path}")
    return data, receipt


def parse_redata_daily(payload: Mapping[str, Any], year: int, month: int) -> pd.DataFrame:
    """Preserve only explicitly published observations; never synthesize zeros.

    A technology omitted for an entire month or individual days remains absent.
    Only the independent total must have every day. Sparse technology dates
    must remain ordered, unique and inside the requested month.
    """
    if payload.get("data", {}).get("id") != "gen1":
        raise GenerationAuditError("Expected REData generation structure gen1")
    items = payload.get("included")
    if not isinstance(items, list) or not items:
        raise GenerationAuditError("Missing REData included technologies")
    local_days = pd.date_range(f"{year}-{month:02d}-01", periods=calendar.monthrange(year, month)[1], freq="D")
    expected = [stamp.date().isoformat() for stamp in local_days]
    seen = set()
    rows = []
    for item in items:
        indicator = str(item.get("id"))
        if indicator in seen:
            raise GenerationAuditError(f"Duplicate official indicator {indicator}")
        seen.add(indicator)
        attrs = item.get("attributes", {})
        title = attrs.get("title")
        if not isinstance(title, str) or not title:
            raise GenerationAuditError(f"Missing technology title: {indicator}")
        if indicator in EXPECTED_TITLES and title != EXPECTED_TITLES[indicator]:
            raise GenerationAuditError(f"Official title changed: {indicator}: {title}")
        values = attrs.get("values")
        if not isinstance(values, list):
            raise GenerationAuditError(f"Missing observations: {indicator}")
        days = []
        for observation in values:
            try:
                stamp = pd.Timestamp(observation["datetime"])
            except (KeyError, ValueError, TypeError) as exc:
                raise GenerationAuditError(f"Invalid official datetime: {indicator}") from exc
            if stamp.tzinfo is None:
                raise GenerationAuditError("Official timestamps must carry their local offset")
            local = stamp.tz_convert(TIMEZONE)
            # Reject offset errors rather than silently moving source observations.
            if local.isoformat() != stamp.isoformat() or (local.hour, local.minute, local.second) != (0, 0, 0):
                raise GenerationAuditError("Official day must start at Madrid midnight with matching offset")
            value = observation.get("value")
            if isinstance(value, bool) or value is None or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise GenerationAuditError(f"Explicit finite daily energy required: {indicator}")
            days.append(local.date().isoformat())
            rows.append({
                "local_day": days[-1], "indicator": indicator, "title": title,
                "published_daily_mwh": float(value),
                "source_datetime": observation["datetime"],
                "source_last_update": attrs.get("last-update"),
            })
        if len(set(days)) != len(days) or days != sorted(days) or not set(days) <= set(expected) or (indicator == "10296" and days != expected):
            raise GenerationAuditError(f"Missing, reordered or duplicate days in {indicator}: {len(days)}")
    if "10296" not in seen:
        raise GenerationAuditError("Official total generation is required as an independent check")
    return pd.DataFrame(rows)


def compare_day(frame: pd.DataFrame, official_day: pd.DataFrame, day: str) -> tuple[list[dict], dict]:
    """Compute transparent same-label diagnostics; unresolved residuals stay explicit."""
    if not frame.index.equals(expected_day_index(day)):
        raise GenerationAuditError("Five-minute power must cover the complete local civil day")
    fields = primary_generation_fields(frame)
    if official_day.empty or official_day["local_day"].nunique() != 1 or official_day["local_day"].iloc[0] != day:
        raise GenerationAuditError("Official comparison must use the same unique local day")
    if official_day["indicator"].duplicated().any():
        raise GenerationAuditError("Duplicate official comparison indicator")
    official = official_day.set_index("indicator")
    if "10296" not in official.index:
        raise GenerationAuditError("Missing official total")
    # min_count preserves nulls and rejects the seductive missing-is-zero sum.
    rectangles = frame.loc[:, list(fields)].sum(min_count=len(frame)) * (5 / 60)
    result = []
    for field in fields:
        indicator = DIRECT_MAPPING.get(field)
        published = None
        status = "UNRECONCILED_TECHNOLOGY_COVERAGE"
        if indicator is not None and indicator in official.index:
            published = float(official.loc[indicator, "published_daily_mwh"])
            status = "SAME_LABEL_DIAGNOSTIC_COVERAGE_NOT_PROVEN_IDENTICAL"
        elif indicator is not None:
            status = "OFFICIAL_CATEGORY_NOT_PUBLISHED_THIS_DAY_NO_ZERO_INFERRED"
        approx = None if pd.isna(rectangles[field]) else float(rectangles[field])
        difference = None if published is None or approx is None else approx - published
        result.append({
            "local_day": day, "raw_field": field, "redata_indicator": indicator,
            "rectangle_diagnostic_mwh": approx, "published_daily_mwh": published,
            "difference_mwh": difference,
            "relative_difference_percent": None if published in (None, 0) or difference is None else 100 * difference / published,
            "comparison_status": status,
            "null_samples": int(frame[field].isna().sum()),
            "positive_samples": int(frame[field].gt(0).sum()),
            "negative_samples": int(frame[field].lt(0).sum()),
        })
    quality = report_quality(frame)
    total = float(official.loc["10296", "published_daily_mwh"])
    raw_total = None if rectangles.isna().any() else float(rectangles.sum())
    details = {
        "local_day": day, "samples": len(frame), "civil_hours": len(frame) / 12,
        "weekday_monday_zero": pd.Timestamp(day).weekday(),
        "iso_week": pd.Timestamp(day).isocalendar().week,
        "rectangle_primary_total_mwh": raw_total, "published_total_mwh": total,
        "difference_mwh": None if raw_total is None else raw_total - total,
        "relative_difference_percent": None if total == 0 or raw_total is None else 100 * (raw_total / total - 1),
        "zero_primary_sum_count": quality["zero_primary_sum_count"],
        "zero_primary_sum_times_utc": quality["zero_primary_sum_times_utc"],
        "null_primary_sum_count": quality["null_primary_sum_count"],
        "source_coverage_period": "includes_estimated_small_self_consumption" if day >= "2025-12-11" else "mandatory_telemetry_only",
        "blackout_demand_curve_advisory": "yellow_demand_curve_estimated_from_12:33_local" if day == "2025-04-28" else "yellow_demand_curve_restoration_end_unspecified" if day == "2025-04-29" else "not_flagged_by_blackout_help",
        "comparison_status": "DIFFERENT_COVERAGE_TOTALS_DIAGNOSTIC_ONLY",
    }
    return result, details


def acquire_official(root: Path, year: int) -> dict:
    requests = [(f"redata/generation_daily_{year}{month:02d}.json", redata_url(year, month)) for month in range(1, 13)]
    requests += [(f"metadata/{name}", url) for name, url in METADATA_URLS.items()]
    # Probe rather than assume daily API admits genuine hourly measured energy.
    probe_relative = f"probes/generation_hour_probe_{year}0101.json"
    probe_url = redata_url(year, 1, trunc="hour", day=1)
    receipts, failures = [], []
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        pending = {executor.submit(archive_response, root, relative, url): relative for relative, url in requests}
        for future in concurrent.futures.as_completed(pending):
            try:
                receipts.append(future.result())
            except Exception as exc:
                failures.append({"file": pending[future], "error": f"{type(exc).__name__}: {exc}"})
    try:
        receipts.append(archive_response(root, probe_relative, probe_url))
    except HTTPError as exc:
        # The documented endpoint may reject hour truncation. Archive that
        # evidence; a rejected probe does not invalidate valid daily archives.
        if exc.code != 400:
            failures.append({"file": probe_relative, "error": f"HTTPError: {exc}"})
        else:
            data = exc.read()
            receipt = {"file": probe_relative, "source_url": probe_url,
                       "retrieved_utc": datetime.now(timezone.utc).isoformat(),
                       "http_status": exc.code, "content_type": exc.headers.get("Content-Type"),
                       "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data),
                       "data_release_status": "REJECTED_HOURLY_PROBE_NOT_DATA"}
            destination = root / probe_relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
            destination.with_suffix(destination.suffix + ".receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
            receipts.append(receipt)
    except Exception as exc:
        failures.append({"file": probe_relative, "error": f"{type(exc).__name__}: {exc}"})
    manifest = {"created_utc": datetime.now(timezone.utc).isoformat(), "historical_year": year,
                "receipts": sorted(receipts, key=lambda item: item["file"]), "failures": failures,
                "requests": len(requests) + 1, "successes": len(receipts), "release_status": "RAW_UNAPPROVED"}
    root.mkdir(parents=True, exist_ok=True)
    (root / "acquisition_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def audit(raw_power_root: Path, audit_root: Path, year: int = 2025) -> dict:
    if year != 2025:
        raise GenerationAuditError("This documented comparison concerns 2025 and its dated coverage change")
    source_refs = []
    official_frames = []
    raw_root = audit_root / "raw"
    for month in range(1, 13):
        path = raw_root / "redata" / f"generation_daily_{year}{month:02d}.json"
        data, receipt = verified_bytes(path, redata_url(year, month))
        official_frames.append(parse_redata_daily(json.loads(data), year, month))
        source_refs.append({**receipt, "archive_group": "audit_raw"})
    official = pd.concat(official_frames, ignore_index=True)
    comparisons, days = [], []
    for day_stamp in pd.date_range(f"{year}-01-01", f"{year}-12-31", freq="D"):
        day = day_stamp.date().isoformat()
        path = raw_power_root / "ree" / "generation" / f"demandaau_{day_stamp:%Y%m%d}.jsonp"
        url = "https://demanda.ree.es/WSvisionaMovilesPeninsulaRest/resources/demandaGeneracionPeninsula?" + urlencode({"callback": "archive", "curva": "DEMANDAAU", "fecha": day})
        data, receipt = verified_bytes(path, url)
        frame = parse_day(data, day)
        current, daily = compare_day(frame, official.loc[official["local_day"].eq(day)], day)
        comparisons.extend(current)
        days.append(daily)
        source_refs.append({**receipt, "archive_group": "existing_step19_raw"})
    for name, url in METADATA_URLS.items():
        _, receipt = verified_bytes(raw_root / "metadata" / name, url)
        source_refs.append({**receipt, "archive_group": "audit_raw"})
    # These archived help texts substantiate the dated coverage/blackout flags.
    legacy_manifest_path = raw_power_root / "spain_checks" / "source_manifest.json"
    legacy_manifest = json.loads(legacy_manifest_path.read_text(encoding="utf-8"))
    help_entries = [item for item in legacy_manifest.get("items", []) if item.get("file") == "ree_frontend_es.js"]
    if len(help_entries) != 1:
        raise GenerationAuditError("Unique archived official Spanish help source required")
    help_entry = help_entries[0]
    help_bytes = (raw_power_root / "spain_checks" / help_entry["file"]).read_bytes()
    help_url = "https://demanda.ree.es/visiona/l10n/es_ES.js?v=4.1.1.2"
    if help_entry.get("url") != help_url or hashlib.sha256(help_bytes).hexdigest() != help_entry.get("sha256"):
        raise GenerationAuditError("Archived official help has invalid provenance")
    help_text = help_bytes.decode("utf-8-sig")
    if "11 de diciembre de 2025" not in help_text or "12:33h del 28 de abril de 2025" not in help_text:
        raise GenerationAuditError("Dated self-consumption/blackout metadata must be re-reviewed")
    source_refs.append({"file": "spain_checks/ree_frontend_es.js", "source_url": help_url,
                       "sha256": help_entry["sha256"], "retrieved_utc": help_entry["retrieved_utc"],
                       "bytes": len(help_bytes), "archive_group": "existing_step19_raw",
                       "receipt_format": "Legacy source_manifest.json; HTTP status not recorded"})
    probe_data, probe_receipt = verified_bytes(raw_root / "probes" / f"generation_hour_probe_{year}0101.json", redata_url(year, 1, trunc="hour", day=1), allowed_http_status=(200, 400))
    probe = json.loads(probe_data)
    probe_counts = {str(item["id"]): len(item.get("attributes", {}).get("values", [])) for item in probe.get("included", [])}
    source_refs.append({**probe_receipt, "archive_group": "audit_raw"})
    compared = pd.DataFrame(comparisons)
    day_frame = pd.DataFrame(days)
    summaries = []
    for field, group in compared.groupby("raw_field", sort=False):
        matched = group.dropna(subset=["published_daily_mwh", "rectangle_diagnostic_mwh"])
        ratio_rows = matched.dropna(subset=["relative_difference_percent"])
        approx = float(matched["rectangle_diagnostic_mwh"].sum()) if len(matched) else None
        published = float(matched["published_daily_mwh"].sum()) if len(matched) else None
        summaries.append({
            "raw_field": field, "matched_days": len(matched), "positive_power_days": int(group["positive_samples"].gt(0).sum()),
            "null_sample_days": int(group["null_samples"].gt(0).sum()),
            "rectangle_mwh_all_days": None if group["rectangle_diagnostic_mwh"].isna().any() else float(group["rectangle_diagnostic_mwh"].sum()),
            "first_positive_power_day": None if not group["positive_samples"].gt(0).any() else group.loc[group["positive_samples"].gt(0), "local_day"].iloc[0],
            "first_matched_day": None if matched.empty else matched["local_day"].iloc[0],
            "last_matched_day": None if matched.empty else matched["local_day"].iloc[-1],
            "rectangle_mwh_on_matched_days": approx, "official_mwh_on_matched_days": published,
            "relative_difference_of_matched_sums_percent": None if published in (None, 0) else 100 * (approx / published - 1),
            "daily_relative_difference_min_percent": None if ratio_rows.empty else float(ratio_rows["relative_difference_percent"].min()),
            "daily_relative_difference_max_percent": None if ratio_rows.empty else float(ratio_rows["relative_difference_percent"].max()),
            "daily_absolute_relative_difference_median_percent": None if ratio_rows.empty else float(ratio_rows["relative_difference_percent"].abs().median()),
        })
    source_refs.sort(key=lambda item: (item["archive_group"], item["file"]))
    published_ids = sorted(official["indicator"].unique())
    unmatched_ids = sorted(set(published_ids) - set(DIRECT_MAPPING.values()) - {"10296"})
    zero_times = [stamp for day in days for stamp in day["zero_primary_sum_times_utc"]]
    report = {
        "created_utc": datetime.now(timezone.utc).isoformat(), "historical_year": year,
        "release_status": "DIAGNOSTIC_ONLY_NO_EMISSIONS_OR_MODEL_INPUT_RELEASE",
        "days": len(days), "five_minute_samples": int(day_frame["samples"].sum()),
        "daily_energy_source": "Official REData published daily peninsular generation, not a proven common settled/telemetry boundary",
        "daily_energy_unit": "MWh interpretation consistent with official annual GWh scale; API magnitude is null, not an explicit unit declaration",
        "power_energy_conversion": "Each instantaneous MW sample times 5/60 h; diagnostic left rectangles only",
        "unchanged_raw_power": True, "no_calibration_or_scaling": True,
        "no_arbitrary_numeric_release_threshold": True,
        "comparison_interpretation": "Same technology label does not establish identical net/gross, telemetry, metering or self-consumption coverage. Daily differences cannot alone identify integration error.",
        "uncertainty_interpretation": "Observed discrepancies are source diagnostics, not confidence intervals or valid technology-factor uncertainty bounds.",
        "annual_total_diagnostics": {
            "official_published_total_mwh": float(day_frame["published_total_mwh"].sum()),
            "rectangle_primary_total_mwh": None if day_frame["rectangle_primary_total_mwh"].isna().any() else float(day_frame["rectangle_primary_total_mwh"].sum()),
            "status": "DIFFERENT_COVERAGE_DIAGNOSTIC_ONLY",
            "official_annual_report_peninsular_gwh": 257991,
            "annual_report_reference": "2025 report, provisional January 2026; daily API was later updated, so versions need not match exactly",
            "annual_report_source_url": METADATA_URLS["ree_annual_generation_2025.html"]},
        "metadata": {
            "generation_page_url": METADATA_URLS["ree_generation.html"],
            "generation_page_statement": "Generation section excludes estimated generation by self-consumption installations; includes surplus feed-in without compensation. Net/gross glossary does not assign one universal boundary to every technology/endpoint.",
            "coverage_change_date": "2025-12-11",
            "coverage_change_basis": "Previously archived official DEMANDAAU frontend Spanish help; estimated small self-consumption is added from this date.",
            "self_consumption_methodology_url": METADATA_URLS["ree_self_consumption_methodology.pdf"],
            "same_boundary_status": "NOT_PROVEN",
            "dated_coverage_and_blackout_help_url": help_url,
            "blackout_yellow_demand_curve_advisory": {
                "start_local": "2025-04-28T12:33:00+02:00", "start_utc": "2025-04-28T10:33:00+00:00",
                "restoration_end_local_date": "2025-04-29", "exact_end_time_status": "NOT_SPECIFIED_IN_ARCHIVED_HELP",
                "interpretation": "Official help explicitly names the yellow real-time demand curve as estimated. This is not evidence that every technology generation value was estimated, and does not establish Huelva site import availability.",
                "correction_of_prior_interpretation": "Earlier 2026-10-03 audit described real-time data too broadly; archived original report retained for provenance."},
            "steam_turbine_2025_classification_change": {
                "source_url": METADATA_URLS["ree_annual_generation_2025.html"],
                "reference_year": 2025,
                "annual_report_data_status": "Provisional at January 2026, per archived 2025 page heading; saved URL/SHA256 fixes this version",
                "meaning": "REE attributes the 2025 steam-turbine category to conversion of Aboño II from coal around mid-July; its direct-factor fuel mapping needs specific evidence, not a generic steam-turbine assumption.",
                "actual_operation_evidence": METADATA_URLS["abono_conversion_operator_2025.html"],
                "operator_publication_date": "2025-07-29",
                "operator_fuel_statement": "Coal replaced by natural gas, with steel-industry gases still used. A fuel ratio is not supplied.",
                "permitted_project_evidence": METADATA_URLS["abono_conversion_environmental_decision_2024.pdf"],
                "permitted_project_fuel_statement": "BOE pages 1 and 3 describe blast-furnace gas (GHA) supported by natural gas; page 4 describes deactivation of the coke-oven-gas system. This is a permitted design, not measured 2025 annual fuel consumption.",
                "not_used_as_factor": "BOE page 5's 38 percent GHA air-quality scenario is not an observed 2025 annual fuel-energy share; no such numerical mix is inferred."},
        },
        "direct_label_mapping": DIRECT_MAPPING,
        "unmatched_positive_power_fields": [item["raw_field"] for item in summaries if item["matched_days"] == 0 and item["positive_power_days"] > 0],
        "unmatched_official_indicators": [{"id": indicator, "title": official.loc[official["indicator"].eq(indicator), "title"].iloc[0]} for indicator in unmatched_ids],
        "residual_mapping_action": "Resolve bio versus other renewable/waste and cogenResto versus cogeneration/waste explicitly; no factor-zero or inferred split.",
        "technology_diagnostics": summaries,
        "official_technology_coverage": [{"indicator": str(indicator), "title": group["title"].iloc[0],
            "published_days": len(group), "first_published_day": group["local_day"].iloc[0],
            "last_published_day": group["local_day"].iloc[-1], "positive_days": int(group["published_daily_mwh"].gt(0).sum()),
            "negative_days": int(group["published_daily_mwh"].lt(0).sum()),
            "sum_of_explicit_published_mwh": float(group["published_daily_mwh"].sum())}
            for indicator, group in official.groupby("indicator", sort=False)],
        "blackout_source_zero_observations": {"samples": len(zero_times), "utc_times": zero_times,
            "factor_policy": "A zero five-minute primary generation denominator yields unavailable instantaneous EF, never zero EF. Sum hourly emission numerator and generation denominator before division; the seven zero samples do not imply a zero hourly denominator.",
            "grid_availability_policy": "No plant/site grid outage schedule inferred from national zero telemetry; availability requires a separate documented source/scenario."},
        "dst_day_samples": {day["local_day"]: day["samples"] for day in days if day["samples"] != 288},
        "hourly_api_probe": {"source_url": probe_receipt["source_url"], "http_status": probe_receipt["http_status"], "response": probe if probe_receipt["http_status"] != 200 else None, "observations_by_indicator": probe_counts,
            "genuine_24_hour_series_returned": bool(probe_counts) and all(count == 24 for count in probe_counts.values()),
            "interpretation": "Probe is evidence about this endpoint, not an assertion about all public hourly REE/ENTSO-E sources."},
        "sources": source_refs,
        "software_sha256": {name: hashlib.sha256((Path(__file__).parent / name).read_bytes()).hexdigest() for name in (Path(__file__).name, "ree_historical_data.py", "acquire_eu_historical_sources.py")},
        "remaining_actions": ["Resolve positive residual technology mapping", "Define compatible net/gross and self-consumption boundary", "Complete country and technology direct factors and documented uncertainty", "Define blackout availability scenario separately"],
    }
    audit_root.mkdir(parents=True, exist_ok=True)
    outputs = {
        "official_daily_energy.csv": official,
        "daily_technology_comparison.csv": compared,
        "daily_coverage_flags.csv": day_frame.drop(columns="zero_primary_sum_times_utc"),
    }
    for name, frame in outputs.items():
        frame.to_csv(audit_root / name, index=False)
    report["output_sha256"] = {name: hashlib.sha256((audit_root / name).read_bytes()).hexdigest() for name in outputs}
    (audit_root / "generation_quality_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-power-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--acquire", action="store_true", help="Archive public official daily energy and primary metadata first")
    args = parser.parse_args()
    if args.acquire:
        manifest = acquire_official(args.output / "raw", 2025)
        if manifest["failures"]:
            print(json.dumps(manifest["failures"], ensure_ascii=False), flush=True)
            return 1
    report = audit(args.raw_power_root, args.output)
    print(json.dumps({key: report[key] for key in ("release_status", "days", "five_minute_samples", "unmatched_positive_power_fields", "dst_day_samples", "hourly_api_probe")}, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
