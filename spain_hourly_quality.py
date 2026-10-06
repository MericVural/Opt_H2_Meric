"""Audit Spain's prepared snapshot proxy without releasing energy or factors.

The hour numerator and denominator can be aggregated before taking a ratio.
Individual zero-power snapshots consequently need no factor interpolation.
This does not establish measured interval energy or site supply availability.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

FIELDS = ("eol", "nuc", "gf", "car", "cc", "gnhd", "solFot", "solTer", "bio", "cogenResto", "vap")
TIMEZONE = "Europe/Madrid"
SOURCE_HELP_URL = "https://demanda.ree.es/visiona/l10n/es_ES.js?v=4.1.1.2"
GENERATION_URL = "https://www.ree.es/es/datos/generacion"
ENTSOE_URL = "https://transparencyplatform.zendesk.com/hc/en-us/articles/16648290299284-Actual-Generation-per-Production-Type-16-1-B-C"


class SpainQualityError(ValueError):
    """An input violates the explicit source-calendar or snapshot contract."""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_generation_csv(path: Path) -> pd.DataFrame:
    data = pd.read_csv(path)
    if "timestamp" not in data or not set(FIELDS) <= set(data):
        raise SpainQualityError("Timestamp and all eleven primary categories are required")
    # utc=True alone would also accept naive timestamps; reject those first.
    try:
        stamps = [pd.Timestamp(value) for value in data.pop("timestamp")]
    except (TypeError, ValueError) as exc:
        raise SpainQualityError("Invalid source timestamps") from exc
    if any(stamp.tzinfo is None for stamp in stamps):
        raise SpainQualityError("Each source timestamp must carry its UTC offset")
    data.index = pd.DatetimeIndex(stamps).tz_convert("UTC")
    data.index.name = "timestamp"
    if data.index.has_duplicates or not data.index.is_monotonic_increasing:
        raise SpainQualityError("Source index must be unique and chronological")
    if any(pd.api.types.is_bool_dtype(data[field]) for field in FIELDS):
        raise SpainQualityError("Boolean values are not generation measurements")
    try:
        values = data.loc[:, list(FIELDS)].apply(pd.to_numeric, errors="raise").astype(float)
    except (TypeError, ValueError) as exc:
        raise SpainQualityError("Finite numeric generation values are required") from exc
    if not np.isfinite(values.to_numpy()).all():
        raise SpainQualityError("Missing or nonfinite primary generation is never filled")
    if values.lt(0).any().any():
        raise SpainQualityError("Negative primary generation needs its own source review")
    return values


def expected_index(year: int, frequency: str) -> pd.DatetimeIndex:
    if year != 2025:
        raise SpainQualityError("This source-event contract is explicitly for 2025")
    return pd.date_range(
        pd.Timestamp("2025-01-01", tz=TIMEZONE).tz_convert("UTC"),
        pd.Timestamp("2026-01-01", tz=TIMEZONE).tz_convert("UTC"),
        freq=frequency, inclusive="left", name="timestamp",
    )


def audit_frames(power: pd.DataFrame, hourly: pd.DataFrame, *, year: int = 2025) -> tuple[dict[str, Any], pd.DataFrame]:
    """Audit complete hours, aggregating published zeros without inventing an EF."""
    if not power.index.equals(expected_index(year, "5min")):
        raise SpainQualityError("Power must contain the exact 105120-point local 2025 calendar")
    if not hourly.index.equals(expected_index(year, "h")):
        raise SpainQualityError("Hour proxy must contain the exact 8760-hour local 2025 calendar")
    for frame in (power, hourly):
        if (tuple(frame.columns) != FIELDS
                or any(pd.api.types.is_bool_dtype(frame[field]) for field in FIELDS)
                or not np.isfinite(frame.to_numpy()).all() or frame.lt(0).any().any()):
            raise SpainQualityError("Eleven ordered, finite, nonnegative primary categories required")
    counts = power.groupby(power.index.floor("h")).size()
    if not counts.eq(12).all():
        raise SpainQualityError("Each UTC hour requires twelve unfilled published snapshots")
    recomputed = power.resample("h").sum(min_count=12) * (5 / 60)
    # Existing preparer writes CSV floats with %.12g: this tests only output
    # serialization, not physical agreement with measured energy.
    if not np.allclose(recomputed.to_numpy(), hourly.to_numpy(), rtol=1e-10, atol=1e-7):
        raise SpainQualityError("Prepared hour proxy does not reproduce twelve left rectangles")
    snapshot_total = power.sum(axis=1, min_count=len(FIELDS))
    hour_total = hourly.sum(axis=1, min_count=len(FIELDS))
    flags = pd.DataFrame(index=hourly.index)
    flags["primary_generation_rectangle_mwh"] = hour_total
    flags["zero_primary_snapshot_count"] = snapshot_total.eq(0).resample("h").sum().astype(int)
    flags["mix_factor_denominator_defined"] = hour_total.gt(0)
    event_start = pd.Timestamp("2025-04-28T12:33:00+02:00").tz_convert("UTC")
    # The source says restoration ended on 29 April, without an exact time.
    # The flag covers possible overlap through local midnight as an advisory.
    event_end_exclusive = pd.Timestamp("2025-04-30", tz=TIMEZONE).tz_convert("UTC")
    flags["related_yellow_curve_blackout_advisory"] = (flags.index < event_end_exclusive) & (flags.index + pd.Timedelta(hours=1) > event_start)
    change = pd.Timestamp("2025-12-11", tz=TIMEZONE).tz_convert("UTC")
    flags["small_self_consumption_estimate_in_mix_coverage"] = flags.index >= change
    summary = {
        "historical_year": year,
        "release_status": "SOURCE_QUALITY_AUDIT_ONLY_NO_MODEL_INPUT_RELEASE",
        "samples": len(power), "hours": len(hourly),
        "null_snapshot_values": 0, "null_hour_values": 0,
        "zero_primary_snapshot_count": int(snapshot_total.eq(0).sum()),
        "zero_primary_snapshot_times_utc": [stamp.isoformat() for stamp in power.index[snapshot_total.eq(0)]],
        "zero_hour_denominator_count": int(hour_total.eq(0).sum()),
        "undefined_hour_denominator_times_utc": [stamp.isoformat() for stamp in hourly.index[~hour_total.gt(0)]],
        "minimum_primary_hour_rectangle_mwh": float(hour_total.min()),
        "minimum_hour_utc": hour_total.idxmin().isoformat(),
        "maximum_reconstruction_difference_mwh": float(np.abs(recomputed.to_numpy() - hourly.to_numpy()).max()),
        "serialization_tolerance": {"rtol": 1e-10, "atol_mwh": 1e-7, "meaning": "%.12g CSV rounding, not an energy-release tolerance"},
        "rectangle_semantics": "sum of twelve instantaneous MW snapshots times 5/60 h; explicitly a proxy, not verified measured interval energy",
        "mix_ratio_rule": "aggregate technology-weighted numerator and total generation denominator over the hour before dividing; a zero snapshot contributes zero weight, not a zero emissions factor",
        "factor_interpolation_performed": False, "energy_scaling_performed": False,
        "source_blackout_advisory": {
            "source_url": SOURCE_HELP_URL,
            "estimated_variable_explicitly_named": "yellow real-time demand curve, not each individual technology generation value",
            "start_utc": event_start.isoformat(),
            "restoration_end_local_date": "2025-04-29", "exact_restoration_end_time_available": False,
            "conservative_advisory_end_exclusive_utc": event_end_exclusive.isoformat(),
            "flagged_hour_count": int(flags["related_yellow_curve_blackout_advisory"].sum()),
            "generation_estimation_status_of_each_sample": "NOT_ESTABLISHED_BY_THIS_DEMAND_CURVE_STATEMENT",
        },
        "coverage_break": {
            "source_url": SOURCE_HELP_URL, "effective_local_date": "2025-12-11",
            "hours_with_extended_mix_coverage": int(flags["small_self_consumption_estimate_in_mix_coverage"].sum()),
            "meaning": "mix includes estimated instantaneous small-scale self-consumption from this date; earlier inclusion covers mandatory telemetry",
            "removal_or_calibration_performed": False,
        },
        "site_grid_availability": {
            "observed_for_huelva_la_rabida": False,
            "inferable_from_country_generation_denominator": False,
            "model_boundary": "Supply availability is a distinct operating assumption or site outage input; no outage is inferred from snapshots and no availability value is created here",
        },
        "uncertainty_limits": [
            "Hourly rectangles cannot have a proven measurement-error bound from instantaneous snapshots alone without additional physical assumptions.",
            "Official daily-energy differences also include unresolved reporting coverage, revision and net/gross differences; they are diagnostics, not confidence intervals.",
            "A declared generation-mix proxy is scientifically usable for exploratory modeling, but is not identical to realized-energy accounting and needs a separate method acceptance.",
        ],
        "alternative_source_findings": {
            "redata_generation_and_balance_hourly": "Targeted public 2025-01-01 probes returned HTTP 400; no global proof that all hourly data is unavailable",
            "esios_real_measured_energy_api": "Unauthenticated targeted candidate indicator 10035 and catalogues returned HTTP 403; the candidate's full semantics cannot be verified without its metadata, and public API documentation requests a personal token",
            "esios_archive32_i3dia": "Public ZIP succeeds, but source workbook content identifies generation programmes PVP/P48/PHF/PHFC and energy unavailable; not a substitute for realized technology generation",
            "entsoe": "Official Spain clarification: real-time aggregated public-grid set points, not updated; access routes require credentials and no measured-energy upgrade is established",
            "entsoe_source_url": ENTSOE_URL,
        },
        "model_ready": False,
    }
    return summary, flags


def build_report(power_path: Path, hourly_path: Path, output: Path, *, alternative_audit_root: Path | None = None) -> dict:
    power = read_generation_csv(power_path)
    hourly = read_generation_csv(hourly_path)
    summary, flags = audit_frames(power, hourly)
    summary["created_utc"] = datetime.now(timezone.utc).isoformat()
    summary["software_sha256"] = sha256(Path(__file__))
    summary["prepared_source_files"] = [{"path": str(path.resolve()), "sha256": sha256(path)} for path in (power_path, hourly_path)]
    if alternative_audit_root is not None:
        manifest_path = alternative_audit_root / "acquisition_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        references = []
        for receipt in manifest["receipts"]:
            path = alternative_audit_root / receipt["file"]
            if sha256(path) != receipt["sha256"] or len(path.read_bytes()) != receipt["bytes"]:
                raise SpainQualityError("Alternative source archive changed after acquisition")
            references.append(receipt)
        summary["alternative_source_archive_manifest"] = {"path": str(manifest_path.resolve()), "sha256": sha256(manifest_path), "verified_receipts": references}
    output.mkdir(parents=True, exist_ok=True)
    flags_path = output / "hourly_generation_quality_flags.csv"
    flags.to_csv(flags_path, float_format="%.12g")
    summary["hourly_flags_sha256"] = sha256(flags_path)
    (output / "hourly_generation_quality_report.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--power-csv", required=True, type=Path)
    parser.add_argument("--hourly-csv", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--alternative-audit-root", type=Path)
    args = parser.parse_args()
    result = build_report(args.power_csv, args.hourly_csv, args.output, alternative_audit_root=args.alternative_audit_root)
    print(json.dumps({key: result[key] for key in ("hours", "zero_primary_snapshot_count", "zero_hour_denominator_count", "minimum_primary_hour_rectangle_mwh", "model_ready")}, indent=2))


if __name__ == "__main__":
    main()
