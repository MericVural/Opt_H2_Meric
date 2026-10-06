"""Offline integrity tests for source loading and unreleased preparation."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from urllib.parse import urlencode

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import prepare_eu_historical_data as prepare_module
from acquire_eu_historical_sources import archive_response
from eu_historical_data import HistoricalDataError, local_year_index
from prepare_eu_historical_data import (
    load_smard, load_spanish_prices, national_hicp_deflators, verified_json, verified_bytes,
)


def archive_json(root, relative, payload, *, url="https://example.org/fixture"):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    path.write_bytes(raw)
    receipt = {"file": relative, "source_url": url, "sha256": hashlib.sha256(raw).hexdigest(),
               "bytes": len(raw), "http_status": 200, "data_release_status": "RAW_UNAPPROVED"}
    path.with_suffix(path.suffix + ".receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
    return path


def hicp_archive(root, year=2025):
    # Country and year coordinates deliberately differ from label order;
    # numeric flat keys follow JSON-stat dimension ordering, not dict order.
    dimension = {
        "freq": {"category": {"index": {"A": 0}}},
        "unit": {"category": {"index": {"INX_A_AVG": 0}}},
        "coicop18": {"category": {"index": {"TOTAL": 0}}},
        "geo": {"category": {"index": {"DE": 1, "ES": 0}}},
        "time": {"category": {"index": {"2023": 1, "2024": 2, "2025": 0}}},
    }
    payload = {"id": ["freq", "unit", "coicop18", "geo", "time"], "size": [1, 1, 1, 2, 3],
               "dimension": dimension,
               "value": {"0": 120., "1": 95., "2": 110., "3": 125., "4": 100., "5": 115.}}
    directory = root / "price_basis"
    directory.mkdir()
    path = directory / f"eurostat_prc_hicp_ainr_DE_ES_2023_{year}.json"
    raw = json.dumps(payload).encode("utf-8")
    path.write_bytes(raw)
    receipt = {"file": str(path), "url": f"https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/prc_hicp_ainr?freq=A&unit=INX_A_AVG&coicop18=TOTAL&geo=DE&geo=ES&sinceTimePeriod=2023&untilTimePeriod={year}",
               "http_status": 200,
               "sha256": hashlib.sha256(raw).hexdigest()}
    (directory / "source_manifest.json").write_text(json.dumps([receipt]), encoding="utf-8")
    return path


def test_national_hicp_ratio_resolves_country_year_coordinates(tmp_path):
    hicp_archive(tmp_path)
    result = national_hicp_deflators(tmp_path, 2025)
    assert result["DE"]["index_2023"] == 100
    assert result["DE"]["index_2025"] == 125
    assert result["DE"]["multiplier_nominal_2025_to_real_2023"] == pytest.approx(100 / 125)
    assert result["ES"]["multiplier_nominal_2025_to_real_2023"] == pytest.approx(95 / 120)
    assert result["DE"]["source_sha256"] == result["ES"]["source_sha256"]


def test_hicp_hash_mismatch_is_rejected(tmp_path):
    path = hicp_archive(tmp_path)
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(HistoricalDataError, match="hash"):
        national_hicp_deflators(tmp_path, 2025)


def test_2024_hicp_uses_2023_and_2024_cells_not_2025(tmp_path):
    hicp_archive(tmp_path, 2024)
    result = national_hicp_deflators(tmp_path, 2024)
    assert result["DE"]["index_2023"] == 100
    assert result["DE"]["index_2024"] == 115
    assert result["DE"]["multiplier_nominal_2024_to_real_2023"] == pytest.approx(100 / 115)
    assert result["ES"]["multiplier_nominal_2024_to_real_2023"] == pytest.approx(95 / 110)
    assert all(row["source_price_year"] == 2024 and row["price_year"] == 2023 for row in result.values())
    assert "index_2025" not in result["DE"]


def test_flagged_hicp_observation_is_not_silently_accepted(tmp_path):
    path = hicp_archive(tmp_path, 2024)
    payload = json.loads(path.read_bytes())
    payload["status"] = {"5": "p"}
    raw = json.dumps(payload).encode("utf-8")
    path.write_bytes(raw)
    manifest_path = path.parent / "source_manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    manifest[0]["sha256"] = hashlib.sha256(raw).hexdigest()
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(HistoricalDataError, match="flagged"):
        national_hicp_deflators(tmp_path, 2024)


def test_raw_hash_mismatch_is_rejected_before_parsing(tmp_path):
    path = archive_json(tmp_path, "weather/source.json", {"hourly": {}})
    path.write_bytes(b"not even json")
    with pytest.raises(HistoricalDataError, match="hash"):
        verified_json(path)


@pytest.mark.parametrize("defect", ["different_url", "file", "status"])
def test_valid_raw_bytes_still_require_matching_source_receipt(tmp_path, defect):
    path = archive_json(tmp_path, "source.json", {"value": 1}, url="https://example.org/expected")
    receipt_path = path.with_suffix(path.suffix + ".receipt.json")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if defect == "different_url":
        receipt["source_url"] = "https://example.org/another_dataset"
    elif defect == "file":
        receipt["file"] = "other.json"
    else:
        receipt["http_status"] = 404
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(HistoricalDataError, match="mismatch"):
        verified_bytes(path, "https://example.org/expected")


@pytest.mark.parametrize("changed", ["url", "hash", "incomplete"])
def test_archive_resume_refuses_changed_url_bytes_or_missing_receipt(tmp_path, changed):
    url = "https://example.org/original"
    path = archive_json(tmp_path, "source.json", {"value": 1}, url=url)
    if changed == "url":
        url = "https://example.org/other"
    elif changed == "hash":
        path.write_bytes(b"corrupted")
    else:
        path.with_suffix(path.suffix + ".receipt.json").unlink()
    with pytest.raises(ValueError, match="mismatch|Incomplete"):
        archive_response(tmp_path, "source.json", url)


def smard_archive(root, index, values):
    relative = "smard/price/4169_DE_hour_1735513200000.json"
    rows = [[int(stamp.timestamp() * 1000), float(value)] for stamp, value in zip(index, values)]
    return archive_json(root, relative, {"series": rows}, url="https://www.smard.de/app/chart_data/4169/DE/4169_DE_hour_1735513200000.json")


def test_smard_keeps_exact_utc_timestamps_negative_prices_and_ignores_receipts(tmp_path):
    target = pd.date_range("2024-12-31T23:00Z", periods=4, freq="h")
    smard_archive(tmp_path, target, [-20, 0, 10, 30])
    result = load_smard(tmp_path, "price", target)
    assert result.index.equals(target)
    np.testing.assert_allclose(result, [-20, 0, 10, 30])


@pytest.mark.parametrize("defect", ["wrong_year", "gap", "duplicate", "one_hour_shift", "unordered"])
def test_smard_rejects_wrong_year_missing_duplicate_and_shifted_hours(tmp_path, defect):
    target = pd.date_range("2024-12-31T23:00Z", periods=4, freq="h")
    index = target
    if defect == "wrong_year":
        index = target - pd.DateOffset(years=1)
    elif defect == "gap":
        index = target.delete(2)
    elif defect == "duplicate":
        index = target[:2].append(target[1:3])
    elif defect == "unordered":
        index = target[[0, 2, 1, 3]]
    else:
        index = target + pd.Timedelta(hours=1)
    smard_archive(tmp_path, index, np.arange(len(index)))
    with pytest.raises(HistoricalDataError, match="exactly cover|duplicate or unordered"):
        load_smard(tmp_path, "price", target)


def spanish_url(month, year=2025):
    start = pd.Timestamp(year=year, month=month, day=1)
    last = start + pd.offsets.MonthEnd(0)
    query = {"start_date": start.strftime("%Y-%m-%dT00:00"), "end_date": last.strftime("%Y-%m-%dT23:59"), "time_trunc": "hour"}
    return "https://apidatos.ree.es/es/datos/mercados/precios-mercados-tiempo-real?" + urlencode(query)


@pytest.fixture
def spanish_archive(tmp_path):
    start = pd.Timestamp("2025-01-01", tz="Europe/Madrid").tz_convert("UTC")
    end = pd.Timestamp("2026-01-01", tz="Europe/Madrid").tz_convert("UTC")
    index = pd.date_range(start, end, freq="15min", inclusive="left")
    local = index.tz_convert("Europe/Madrid")
    values = np.arange(len(index), dtype=float) - 20000
    for month in range(1, 13):
        mask = local.month == month
        rows = [{"datetime": stamp.isoformat(), "value": float(value)} for stamp, value in zip(local[mask], values[mask])]
        payload = {"included": [{"id": "600", "attributes": {"values": rows}}]}
        archive_json(tmp_path, f"redata/price/spot600_2025{month:02d}.json", payload,
                     url=spanish_url(month))
    return tmp_path, pd.Series(values, index=index)


def test_spanish_autumn_repeated_civil_quarters_remain_distinct_utc_instants(spanish_archive):
    root, native = spanish_archive
    start = pd.Timestamp("2025-10-26", tz="Europe/Madrid").tz_convert("UTC")
    end = pd.Timestamp("2025-10-27", tz="Europe/Madrid").tz_convert("UTC")
    target = pd.date_range(start, end, freq="h", inclusive="left")
    result = load_spanish_prices(root, target)
    assert len(result) == 25
    assert result.index.equals(target)
    assert not result.index.has_duplicates
    quarters = native[(native.index >= start) & (native.index < end)]
    assert len(quarters) == 100
    expected = quarters.to_numpy().reshape(25, 4).mean(axis=1)
    np.testing.assert_allclose(result, expected)
    local = target.tz_convert("Europe/Madrid")
    repeated = result[local.hour == 2]
    assert len(repeated) == 2 and repeated.iloc[0] != repeated.iloc[1]


def test_spanish_full_local_year_and_negative_prices_survive(spanish_archive):
    root, native = spanish_archive
    target = local_year_index(2025, "Europe/Madrid")
    result = load_spanish_prices(root, target)
    assert len(result) == 8760 and result.index.equals(target)
    assert result.iloc[0] == pytest.approx(native.iloc[:4].mean())
    assert result.iloc[-1] == pytest.approx(native.iloc[-4:].mean())
    assert (result < 0).any()


@pytest.fixture
def spanish_archive_2024(tmp_path):
    index = local_year_index(2024, "Europe/Madrid")
    local = index.tz_convert("Europe/Madrid")
    values = np.arange(len(index), dtype=float) - 4000
    for month in range(1, 13):
        mask = local.month == month
        rows = [{"datetime": stamp.isoformat(), "value": float(value)} for stamp, value in zip(local[mask], values[mask])]
        archive_json(tmp_path, f"redata/price/spot600_2024{month:02d}.json",
                     {"included": [{"id": "600", "attributes": {"values": rows}}]}, url=spanish_url(month, 2024))
    return tmp_path, pd.Series(values, index=index)


def test_2024_spanish_hourly_source_preserves_leap_and_repeated_autumn_hours(spanish_archive_2024):
    root, native = spanish_archive_2024
    target = local_year_index(2024, "Europe/Madrid")
    actual = load_spanish_prices(root, target, year=2024)
    assert len(actual) == 8784
    assert actual.index.equals(target)
    np.testing.assert_array_equal(actual, native)
    local = actual.index.tz_convert("Europe/Madrid")
    assert sum(local.strftime("%Y-%m-%d") == "2024-02-29") == 24
    autumn = actual[local.strftime("%Y-%m-%d") == "2024-10-27"]
    assert len(autumn) == 25
    repeated = autumn[autumn.index.tz_convert("Europe/Madrid").hour == 2]
    assert len(repeated) == 2 and repeated.iloc[0] != repeated.iloc[1]
    assert actual.name == "electricity_price_nominal_eur2024_per_mwh"
    assert (actual < 0).any()


def test_2024_spanish_target_rejects_explicit_2025_source_selection(spanish_archive_2024):
    root, _ = spanish_archive_2024
    with pytest.raises(HistoricalDataError, match="disagree"):
        load_spanish_prices(root, local_year_index(2024, "Europe/Madrid"), year=2025)


def test_real_archived_2024_preparation_preserves_primary_price_cells_and_source_hashes():
    root = Path(__file__).resolve().parents[1]
    raw = root / "outputs_h2/eu_case_studies/historical_2024/step19/raw"
    prepared = raw.parent / "prepared"
    report = json.loads((prepared / "preparation_report.json").read_bytes())
    assert report["historical_year"] == report["source_weather_year"] == report["source_market_year"] == 2024
    assert report["price_year"] == 2023
    acquisition = json.loads((raw / "acquisition_prices_weather.json").read_bytes())
    assert not acquisition["errors"] and acquisition["successes"] == acquisition["requests"]
    for receipt in acquisition["receipts"] + acquisition["index_receipts"]:
        assert hashlib.sha256((raw / receipt["file"]).read_bytes()).hexdigest() == receipt["sha256"]
    for site_id, country, zone in [("hamburg_moorburg", "DE", "Europe/Berlin"),
                                  ("huelva_la_rabida", "ES", "Europe/Madrid")]:
        source = prepared / f"{site_id}_profiles_prices_unreleased.csv"
        assert hashlib.sha256(source.read_bytes()).hexdigest() == report["output_hashes"][source.name]
        frame = pd.read_csv(source)
        index = pd.DatetimeIndex(pd.to_datetime(frame["timestamp"], utc=True))
        assert index.equals(local_year_index(2024, zone))
        assert len(frame) == 8784
        assert sum(index.tz_convert(zone).strftime("%Y-%m-%d") == "2024-02-29") == 24
        if country == "DE":
            rows = []
            for path in sorted((raw / "smard/price").glob("4169_DE_hour_*.json")):
                if not path.name.endswith(".receipt.json"):
                    rows.extend(json.loads(path.read_bytes())["series"])
            original = pd.Series([row[1] for row in rows], index=pd.to_datetime([row[0] for row in rows], unit="ms", utc=True)).loc[index]
        else:
            rows = []
            for path in sorted((raw / "redata/price").glob("spot600_2024*.json")):
                if not path.name.endswith(".receipt.json"):
                    block = [row for row in json.loads(path.read_bytes())["included"] if str(row["id"]) == "600"][0]
                    rows.extend(block["attributes"]["values"])
            original = pd.Series([row["value"] for row in rows], index=pd.to_datetime([row["datetime"] for row in rows], utc=True)).loc[index]
        np.testing.assert_allclose(frame["electricity_price_nominal_eur2024_per_mwh"], original.to_numpy(), rtol=1e-11, atol=1e-11)
        multiplier = report["price_deflators"][country]["index_2023"] / report["price_deflators"][country]["index_2024"]
        np.testing.assert_allclose(frame["electricity_price_real_eur2023_per_mwh"], original.to_numpy() * multiplier, rtol=1e-11, atol=1e-10)
        assert int((frame["electricity_price_real_eur2023_per_mwh"] < 0).sum()) == int((original < 0).sum())
        assert "electricity_price_nominal_eur2025_per_mwh" not in frame


@pytest.mark.parametrize("defect", ["duplicate", "missing", "offset_missing", "unordered"])
def test_spanish_source_quarter_defects_are_rejected(spanish_archive, defect):
    root, _ = spanish_archive
    path = root / "redata/price/spot600_202510.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload["included"][0]["attributes"]["values"]
    if defect == "duplicate":
        rows.insert(10, dict(rows[9]))
    elif defect == "missing":
        rows.pop(10)
    elif defect == "unordered":
        rows[10], rows[11] = rows[11], rows[10]
    else:
        rows[10]["datetime"] = rows[10]["datetime"][:-6]
    archive_json(root, "redata/price/spot600_202510.json", payload,
                 url=spanish_url(10))
    with pytest.raises(HistoricalDataError):
        load_spanish_prices(root, local_year_index(2025, "Europe/Madrid"))


def test_preparation_outputs_explicitly_unreleased_profiles_without_emission_fallback(tmp_path, monkeypatch):
    contract = {
        "consumed_by_current_model": False,
        "time": {"historical_year": 2025, "resolution_hours": 1, "storage_timezone": "UTC",
                 "interval_semantics": "start, [t,t+1h)", "expected_hours": 8760,
                 "reject_positional_year_remapping": True, "start_utc_inclusive": "2024-12-31T23:00:00Z",
                 "end_utc_exclusive": "2025-12-31T23:00:00Z", "year_basis": "local calendar year at each site",
                 "monthly_grouping": "site local timezone", "demand_profile_grouping": "site local timezone"},
        "sites": [{"site_id": name, "country_code": country, "calendar_timezone": zone,
                   "coordinate": {"latitude": 50., "longitude": 8.}}
                  for name, country, zone in (("hamburg_moorburg", "DE", "Europe/Berlin"), ("huelva_la_rabida", "ES", "Europe/Madrid"))],
        "hydrogen_demand": {"profiles": {"D2": {"weight": "1 ifMonday-Friday and08<=local_hour<20 else0"}}},
        "weather": {"query_options": {"models": "era5", "cell_selection": "land", "wind_speed_unit": "ms", "timezone": "UTC"}},
    }
    design_path = tmp_path / "design.json"
    design_path.write_text(json.dumps(contract), encoding="utf-8")
    target = pd.date_range("2024-12-31T23:00Z", periods=2, freq="h")
    monkeypatch.setattr(prepare_module, "local_year_index", lambda *_: target)
    monkeypatch.setattr(prepare_module, "national_hicp_deflators", lambda *_: {country: {"multiplier_nominal_2025_to_real_2023": .95} for country in ("DE", "ES")})
    monkeypatch.setattr(prepare_module, "verified_json", lambda *_: {"latitude": 50., "longitude": 8., "elevation": 10.})
    monkeypatch.setattr(prepare_module, "adapt_open_meteo_weather", lambda *_: pd.DataFrame({"temp_air": [10, 11]}, index=target + pd.Timedelta(minutes=30)))
    monkeypatch.setattr(prepare_module, "renewable_profiles", lambda *_, **__: (np.array([.1, .2]), np.array([.3, .4])))
    monkeypatch.setattr(prepare_module, "load_smard", lambda *_: pd.Series([-10., 20.], index=target))
    monkeypatch.setattr(prepare_module, "load_spanish_prices", lambda *_, **__: pd.Series([-10., 20.], index=target))
    report = prepare_module.prepare(design_path, tmp_path / "sources", tmp_path / "prepared")
    assert report["ready_for_model"] is False and report["step19_complete"] is False
    for site in report["sites"]:
        assert site["ready_for_model"] is False
        path = tmp_path / "prepared" / f"{site['site_id']}_profiles_prices_unreleased.csv"
        frame = pd.read_csv(path)
        assert "grid_emission_factor" not in frame and "h2_demand" not in frame
        np.testing.assert_allclose(frame.electricity_price_real_eur2023_per_mwh, [-9.5, 19.])
