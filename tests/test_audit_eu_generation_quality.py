"""Audit boundaries: official sparse categories, DST, nulls, zeros and hashes."""
import calendar
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from audit_eu_generation_quality import (
    GenerationAuditError, compare_day, parse_redata_daily, redata_url, verified_bytes,
)
from ree_historical_data import KNOWN_NUMERIC_FIELDS, PRIMARY_GENERATION_FIELDS, expected_day_index


def official_month(year=2025, month=1):
    included = []
    for indicator, title, amount in (("10288", "Hidráulica", 24.0), ("10296", "Generación total", 264.0)):
        values = [{"datetime": stamp.isoformat(), "value": amount} for stamp in pd.date_range(f"{year}-{month:02d}-01", periods=calendar.monthrange(year, month)[1], freq="D", tz="Europe/Madrid")]
        included.append({"id": indicator, "attributes": {"title": title, "values": values}})
    return {"data": {"id": "gen1"}, "included": included}


def power(day):
    index = expected_day_index(day)
    frame = pd.DataFrame(1.0, index=index, columns=sorted(KNOWN_NUMERIC_FIELDS))
    frame["ts"] = [stamp.tz_convert("Europe/Madrid").isoformat() for stamp in index]
    return frame


class OfficialEnergyParserTests(unittest.TestCase):
    def test_month_midnight_offsets_preserve_spring_and_autumn_days(self):
        for month in (3, 10):
            frame = parse_redata_daily(official_month(month=month), 2025, month)
            self.assertEqual(len(frame), calendar.monthrange(2025, month)[1] * 2)
            self.assertTrue(frame["source_datetime"].str.contains("\\+01:00").any())
            self.assertTrue(frame["source_datetime"].str.contains("\\+02:00").any())

    def test_sparse_category_remains_sparse_without_inferred_zero(self):
        payload = official_month()
        payload["included"][0]["attributes"]["values"] = payload["included"][0]["attributes"]["values"][10:]
        frame = parse_redata_daily(payload, 2025, 1)
        self.assertEqual(len(frame.loc[frame["indicator"].eq("10288")]), 21)
        self.assertFalse(frame.loc[frame["indicator"].eq("10288"), "published_daily_mwh"].eq(0).any())

    def test_total_gap_duplicate_reordered_invalid_offset_and_bool_fail(self):
        changes = (
            lambda obj: obj["included"][1]["attributes"]["values"].pop(3),
            lambda obj: obj["included"].append(copy.deepcopy(obj["included"][0])),
            lambda obj: obj["included"][0]["attributes"]["values"].reverse(),
            lambda obj: obj["included"][0]["attributes"]["values"][0].update(datetime="2025-01-01T00:00:00+02:00"),
            lambda obj: obj["included"][0]["attributes"]["values"][0].update(value=True),
            lambda obj: obj["included"][0]["attributes"].update(title="Changed boundary label"),
        )
        for change in changes:
            with self.subTest(change=change):
                payload = official_month()
                change(payload)
                with self.assertRaises(GenerationAuditError):
                    parse_redata_daily(payload, 2025, 1)


class DailyComparisonTests(unittest.TestCase):
    def test_rectangle_units_and_dst_day_length_are_explicit(self):
        for day, hours in (("2025-01-01", 24), ("2025-03-30", 23), ("2025-10-26", 25)):
            frame = power(day)
            official = parse_redata_daily(official_month(month=int(day[5:7])), 2025, int(day[5:7]))
            rows, quality = compare_day(frame, official.loc[official["local_day"].eq(day)], day)
            hydro = next(row for row in rows if row["raw_field"] == "gnhd")
            self.assertEqual(hydro["rectangle_diagnostic_mwh"], hours)
            self.assertEqual(quality["civil_hours"], hours)
            self.assertEqual(quality["rectangle_primary_total_mwh"], hours * len(PRIMARY_GENERATION_FIELDS))

    def test_null_is_not_zero_and_unmatched_category_not_split(self):
        frame = power("2025-01-01")
        frame.loc[frame.index[10], "gnhd"] = None
        official = parse_redata_daily(official_month(), 2025, 1)
        rows, quality = compare_day(frame, official.loc[official["local_day"].eq("2025-01-01")], "2025-01-01")
        hydro = next(row for row in rows if row["raw_field"] == "gnhd")
        self.assertIsNone(hydro["rectangle_diagnostic_mwh"])
        self.assertIsNone(hydro["difference_mwh"])
        self.assertIsNone(quality["rectangle_primary_total_mwh"])
        for field in ("bio", "cogenResto"):
            row = next(row for row in rows if row["raw_field"] == field)
            self.assertIsNone(row["published_daily_mwh"])
            self.assertEqual(row["comparison_status"], "UNRECONCILED_TECHNOLOGY_COVERAGE")

    def test_blackout_zeros_remain_flags_not_zero_emission_factors(self):
        frame = power("2025-04-28")
        frame.loc[frame.index[139:146], list(PRIMARY_GENERATION_FIELDS)] = 0
        official = parse_redata_daily(official_month(month=4), 2025, 4)
        _, flags = compare_day(frame, official.loc[official["local_day"].eq("2025-04-28")], "2025-04-28")
        self.assertEqual(flags["zero_primary_sum_count"], 7)
        self.assertEqual(len(flags["zero_primary_sum_times_utc"]), 7)
        self.assertFalse(any("emission_factor" in key for key in flags))

    def test_coverage_change_and_absent_published_category_are_explicit(self):
        official = parse_redata_daily(official_month(month=12), 2025, 12)
        for day, label in (("2025-12-10", "mandatory_telemetry_only"), ("2025-12-11", "includes_estimated_small_self_consumption")):
            rows, flags = compare_day(power(day), official.loc[official["local_day"].eq(day)], day)
            self.assertEqual(flags["source_coverage_period"], label)
            nuclear = next(row for row in rows if row["raw_field"] == "nuc")
            self.assertIsNone(nuclear["published_daily_mwh"])
            self.assertIn("NO_ZERO_INFERRED", nuclear["comparison_status"])


class ProvenanceTests(unittest.TestCase):
    def test_modified_bytes_url_or_status_fail(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "source.json"
            data = b'{"source": 1}'
            path.write_bytes(data)
            receipt = {"source_url": "https://example.org/source", "http_status": 200,
                       "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data), "retrieved_utc": "2026-10-03T00:00:00Z"}
            receipt_path = path.with_suffix(".json.receipt.json")
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            self.assertEqual(verified_bytes(path, receipt["source_url"])[0], data)
            with self.assertRaises(GenerationAuditError):
                verified_bytes(path, "https://example.org/other")
            path.write_bytes(b'{"source": 2}')
            with self.assertRaises(GenerationAuditError):
                verified_bytes(path, receipt["source_url"])
            path.write_bytes(data)
            receipt["http_status"] = 400
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            with self.assertRaises(GenerationAuditError):
                verified_bytes(path, receipt["source_url"])
            self.assertEqual(verified_bytes(path, receipt["source_url"], allowed_http_status=(200, 400))[1]["http_status"], 400)

    def test_country_scope_in_public_url(self):
        url = redata_url(2025, 10)
        self.assertIn("geo_limit=peninsular", url)
        self.assertIn("geo_ids=8741", url)
        self.assertIn("end_date=2025-10-31T23%3A59", url)


if __name__ == "__main__":
    unittest.main()
