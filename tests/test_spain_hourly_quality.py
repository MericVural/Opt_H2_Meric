from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from spain_hourly_quality import FIELDS, SpainQualityError, audit_frames, expected_index, read_generation_csv


def frames():
    index = expected_index(2025, "5min")
    power = pd.DataFrame(1.0, index=index, columns=FIELDS)
    hourly = power.resample("h").sum() * (5 / 60)
    return power, hourly


def test_seven_zero_snapshots_do_not_require_factor_fill():
    power, _ = frames()
    power.loc["2025-04-28 10:35:00+00:00":"2025-04-28 11:05:00+00:00", :] = 0
    summary, flags = audit_frames(power, power.resample("h").sum() * (5 / 60))
    assert summary["zero_primary_snapshot_count"] == 7
    assert summary["zero_hour_denominator_count"] == 0
    assert flags["mix_factor_denominator_defined"].all()
    assert not summary["factor_interpolation_performed"]
    assert not summary["model_ready"]


def test_wholly_zero_hour_is_flagged_as_undefined_without_replacement():
    power, _ = frames()
    power.loc["2025-04-28 11:00:00+00:00":"2025-04-28 11:55:00+00:00", :] = 0
    hourly = power.resample("h").sum() * (5 / 60)
    summary, flags = audit_frames(power, hourly)
    assert summary["zero_hour_denominator_count"] == 1
    assert summary["undefined_hour_denominator_times_utc"] == ["2025-04-28T11:00:00+00:00"]
    assert not flags.loc[pd.Timestamp("2025-04-28T11:00Z"), "mix_factor_denominator_defined"]
    assert hourly.loc[pd.Timestamp("2025-04-28T11:00Z")].eq(0).all()


def test_event_flags_are_advisories_with_civil_dates_and_no_site_availability():
    summary, flags = audit_frames(*frames())
    assert flags.loc[pd.Timestamp("2025-12-10T22:00Z"), "small_self_consumption_estimate_in_mix_coverage"] == False
    assert flags.loc[pd.Timestamp("2025-12-10T23:00Z"), "small_self_consumption_estimate_in_mix_coverage"] == True
    assert summary["coverage_break"]["hours_with_extended_mix_coverage"] == 504
    assert summary["source_blackout_advisory"]["flagged_hour_count"] == 36
    assert not summary["site_grid_availability"]["observed_for_huelva_la_rabida"]
    assert "NOT_ESTABLISHED" in summary["source_blackout_advisory"]["generation_estimation_status_of_each_sample"]


def test_dst_calendar_keeps_actual_elapsed_hours():
    summary, flags = audit_frames(*frames())
    local = flags.index.tz_convert("Europe/Madrid")
    assert len(flags[local.strftime("%Y-%m-%d") == "2025-03-30"]) == 23
    assert len(flags[local.strftime("%Y-%m-%d") == "2025-10-26"]) == 25
    assert summary["hours"] == 8760


@pytest.mark.parametrize("kind", ["missing_sample", "duplicate_hour", "nan", "negative", "changed_hour", "missing_category", "wrong_year"])
def test_bad_sources_are_rejected(kind):
    power, hourly = frames()
    kwargs = {}
    if kind == "missing_sample": power = power.iloc[1:]
    elif kind == "duplicate_hour": hourly = pd.concat([hourly.iloc[:1], hourly])
    elif kind == "nan": power.iloc[5, 0] = np.nan
    elif kind == "negative": power.iloc[5, 0] = -1
    elif kind == "changed_hour": hourly.iloc[5, 0] += 1
    elif kind == "missing_category": power = power.drop(columns="vap")
    elif kind == "wrong_year": kwargs["year"] = 2024
    with pytest.raises(SpainQualityError): audit_frames(power, hourly, **kwargs)


def test_csv_naive_timestamp_is_not_silently_made_utc(tmp_path: Path):
    path = tmp_path / "bad.csv"
    pd.DataFrame({"timestamp": ["2025-01-01 00:00"], **{field: [1] for field in FIELDS}}).to_csv(path, index=False)
    with pytest.raises(SpainQualityError, match="offset"): read_generation_csv(path)


def test_boolean_csv_measurement_is_rejected(tmp_path: Path):
    path = tmp_path / "bool.csv"
    pd.DataFrame({"timestamp": ["2025-01-01T00:00:00Z"], **{field: [True] for field in FIELDS}}).to_csv(path, index=False)
    with pytest.raises(SpainQualityError, match="Boolean"): read_generation_csv(path)
