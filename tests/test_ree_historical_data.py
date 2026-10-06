"""Meaningful calendar/schema/zero-denominator checks against saved REE data."""

import copy
import json
from pathlib import Path
import sys
import unittest

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ree_historical_data import (
    AGGREGATE_FIELDS, KNOWN_NUMERIC_FIELDS, PRIMARY_GENERATION_FIELDS,
    REEDataError, STORAGE_FIELDS, expected_day_index,
    hourly_rectangle_approximation, parse_day, primary_generation_fields,
    report_quality,
)

SNAPSHOTS = Path(__file__).resolve().parent / "fixtures" / "ree_2025"


def fixture(day):
    rows = []
    for utc in expected_day_index(day):
        local = utc.to_pydatetime().astimezone(__import__("zoneinfo").ZoneInfo("Europe/Madrid"))
        suffix = local.strftime("%H")
        if local.hour == 2 and day == "2025-10-26":
            suffix = "2B" if local.fold else "2A"
        row = {"ts": f"{day} {suffix}:{local.minute:02d}"}
        row.update({key: 1.0 for key in sorted(KNOWN_NUMERIC_FIELDS)})
        rows.append(row)
    return {"valoresHorariosGeneracion": rows}


class REEParserTests(unittest.TestCase):
    def test_normal_day_preserves_raw_fields_and_trims_padding(self):
        payload = fixture("2025-01-01")
        payload["valoresHorariosGeneracion"].insert(0, {"ts": "2024-12-31 23:55", "dem": 2})
        df = parse_day("sample(" + json.dumps(payload) + ");", "2025-01-01")
        self.assertEqual(len(df), 288)
        self.assertEqual(df.attrs["trimmed_padding_rows"], 1)
        self.assertIn("ts", df)
        self.assertEqual(str(df.index[0]), "2024-12-31 23:00:00+00:00")
        self.assertEqual(str(df.index[-1]), "2025-01-01 22:55:00+00:00")

    def test_spring_and_autumn_have_real_23_and_25_hours(self):
        spring = parse_day(fixture("2025-03-30"), "2025-03-30")
        autumn = parse_day(fixture("2025-10-26"), "2025-10-26")
        self.assertEqual(len(spring), 276)
        self.assertEqual(len(autumn), 300)
        self.assertFalse(autumn.index.has_duplicates)
        self.assertEqual(autumn.loc[autumn["ts"].eq("2025-10-26 2A:00")].index[0], pd.Timestamp("2025-10-26T00:00:00Z"))
        self.assertEqual(autumn.loc[autumn["ts"].eq("2025-10-26 2B:00")].index[0], pd.Timestamp("2025-10-26T01:00:00Z"))
        self.assertEqual(len(hourly_rectangle_approximation(spring)), 23)
        self.assertEqual(len(hourly_rectangle_approximation(autumn)), 25)

    def test_missing_duplicate_unordered_and_invalid_dst_fail(self):
        for transform in (
            lambda rows: rows.pop(5),
            lambda rows: rows.insert(5, copy.deepcopy(rows[4])),
            lambda rows: rows.reverse(),
            lambda rows: rows[0].update(ts="2025-01-01 2A:00"),
        ):
            payload = fixture("2025-01-01")
            transform(payload["valoresHorariosGeneracion"])
            with self.assertRaises(REEDataError):
                parse_day(payload, "2025-01-01")
        payload = fixture("2025-10-26")
        payload["valoresHorariosGeneracion"][24]["ts"] = "2025-10-26 02:00"
        with self.assertRaises(REEDataError):
            parse_day(payload, "2025-10-26")

    def test_nulls_remain_null_and_actual_zero_is_preserved(self):
        payload = fixture("2025-01-01")
        payload["valoresHorariosGeneracion"][0]["cc"] = None
        payload["valoresHorariosGeneracion"][1]["cc"] = 0
        df = parse_day(payload, "2025-01-01")
        self.assertTrue(pd.isna(df.iloc[0]["cc"]))
        self.assertEqual(df.iloc[1]["cc"], 0)
        report = report_quality(df)
        self.assertEqual(report["nulls_by_field"]["cc"], 1)
        self.assertEqual(report["zeros_by_field"]["cc"], 1)
        self.assertTrue(pd.isna(hourly_rectangle_approximation(df).iloc[0]["cc"]))

    def test_storage_parent_aggregates_and_unknown_fields(self):
        payload = fixture("2025-01-01")
        for row in payload["valoresHorariosGeneracion"]:
            for key in STORAGE_FIELDS + AGGREGATE_FIELDS:
                row[key] = 100_000
        df = parse_day(payload, "2025-01-01")
        fields = primary_generation_fields(df)
        self.assertFalse(set(fields) & set(STORAGE_FIELDS + AGGREGATE_FIELDS))
        hourly = hourly_rectangle_approximation(df)
        self.assertEqual(hourly.iloc[0]["gnhd"], 1)
        self.assertNotIn("hid", hourly)
        self.assertNotIn("turb", hourly)
        for row in payload["valoresHorariosGeneracion"]:
            row["new_source_category"] = 1
        preserved = parse_day(payload, "2025-01-01")
        self.assertIn("new_source_category", preserved)
        with self.assertRaises(REEDataError):
            primary_generation_fields(preserved)

    def test_boolean_and_nonfinite_source_power_are_rejected(self):
        for value in (True, False, float("inf"), float("-inf"), float("nan")):
            payload = fixture("2025-01-01")
            payload["valoresHorariosGeneracion"][0]["cc"] = value
            with self.assertRaises(REEDataError):
                parse_day(payload, "2025-01-01")

    def test_live_saved_transition_days_and_outage_evidence(self):
        for day, count in (("2025-03-30", 276), ("2025-10-26", 300)):
            df = parse_day((SNAPSHOTS / f"ree_demandaau_{day}.jsonp").read_bytes(), day)
            self.assertEqual(len(df), count)
        outage = parse_day((SNAPSHOTS / "ree_demandaau_2025-04-28.jsonp").read_bytes(), "2025-04-28")
        quality = report_quality(outage)
        self.assertEqual(quality["zero_primary_sum_count"], 7)
        self.assertEqual(quality["zero_primary_sum_times_utc"][0], "2025-04-28T10:35:00+00:00")
        self.assertEqual(quality["zero_primary_sum_times_utc"][-1], "2025-04-28T11:05:00+00:00")
        hourly = hourly_rectangle_approximation(outage)
        self.assertFalse(hourly.attrs["approved_emissions_factor"])
        self.assertEqual(hourly.attrs["energy_release_status"], "DIAGNOSTIC_ONLY_NOT_APPROVED_ENERGY")
        self.assertNotIn("EF", hourly.columns)

    def test_redata_saved_autumn_prices_have_unique_utc_instants(self):
        # Raw offset strings are correct; PowerShell Select-Object -Unique is
        # not evidence of duplicate physical intervals on a repeated civil hour.
        payload = json.loads((SNAPSHOTS / "redata_prices_2025-10-26.json").read_text(encoding="utf-8"))
        values = next(series for series in payload["included"] if series["id"] == "600")["attributes"]["values"]
        index = pd.to_datetime([row["datetime"] for row in values], utc=True)
        self.assertEqual(len(index), 100)
        self.assertFalse(index.has_duplicates)
        self.assertTrue(index.is_monotonic_increasing)
        self.assertIn("2025-10-26T02:00:00.000+02:00", [row["datetime"] for row in values])
        self.assertIn("2025-10-26T02:00:00.000+01:00", [row["datetime"] for row in values])


if __name__ == "__main__":
    unittest.main()
