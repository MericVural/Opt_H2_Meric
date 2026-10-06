import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import pandas as pd

from h2_input_data import HourlyInputError, validate_hourly_input
from prepare_eu_regulatory_inputs import prepare_site_input, release_inputs


class RegulatoryReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.prepared = self.root / "prepared"
        self.prepared.mkdir()
        self.frame = pd.DataFrame({
            "timestamp": pd.date_range("2024-12-31T23:00:00Z", periods=8760, freq="h"),
            "pv_capacity_factor": .2, "wind_capacity_factor": .3,
            "electricity_price_real_eur2023_per_mwh": -12.125,
        })
        self.hashes = {}
        for site in ("hamburg_moorburg", "huelva_la_rabida"):
            name = f"{site}_profiles_prices_unreleased.csv"
            self.frame.to_csv(self.prepared / name, index=False)
            self.hashes[name] = hashlib.sha256((self.prepared / name).read_bytes()).hexdigest()
        (self.prepared / "preparation_report.json").write_text(json.dumps({"historical_year": 2025, "output_hashes": self.hashes}), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def load(self, site="hamburg_moorburg"):
        name = f"{site}_profiles_prices_unreleased.csv"
        return prepare_site_input(self.prepared / name, site_id=site, expected_sha256=self.hashes[name])

    def test_no_fake_operational_emission_and_default_rejects(self):
        data = self.load()
        self.assertNotIn("grid_emission_factor", data)
        self.assertEqual(data.attrs["operational_emissions_status"], "not_evaluated")
        self.assertEqual(set(data.attrs["emission_factor_sources"]), {"regulatory"})
        with self.assertRaises(HourlyInputError):
            validate_hourly_input(data)

    def test_country_regulatory_values_negative_prices_and_volume(self):
        for site, factor in (("hamburg_moorburg", 357.48), ("huelva_la_rabida", 194.76)):
            data = self.load(site)
            self.assertTrue(data["regulatory_grid_emission_factor"].eq(factor).all())
            self.assertTrue(data["electricity_price"].eq(-12.125).all())
            self.assertAlmostEqual(data["h2_demand"].sum(), 3650000)

    def test_changed_source_rejected(self):
        path = self.prepared / "hamburg_moorburg_profiles_prices_unreleased.csv"
        path.write_bytes(path.read_bytes() + b"\n")
        with self.assertRaisesRegex(ValueError, "SHA256"):
            self.load()

    def test_wrong_calendar_rejected_even_with_updated_hash(self):
        path = self.prepared / "hamburg_moorburg_profiles_prices_unreleased.csv"
        self.frame["timestamp"] += pd.Timedelta(hours=1)
        self.frame.to_csv(path, index=False)
        self.hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError, "exact UTC"):
            self.load()

    def test_source_gap_rejected(self):
        path = self.prepared / "hamburg_moorburg_profiles_prices_unreleased.csv"
        self.frame.drop(index=50).to_csv(path, index=False)
        self.hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        with self.assertRaises(HourlyInputError):
            self.load()

    def test_no_output_before_both_sources_validate(self):
        path = self.prepared / "huelva_la_rabida_profiles_prices_unreleased.csv"
        path.write_bytes(b"bad")
        with self.assertRaises(ValueError):
            release_inputs(self.prepared, self.root / "released")
        self.assertFalse((self.root / "released").exists())

    def test_release_contract_bound_to_exact_csv(self):
        result = release_inputs(self.prepared, self.root / "released")
        self.assertTrue(result["cost_inputs_released"])
        self.assertFalse(result["operational_point_factors_released"])
        for site in result["sites"].values():
            csv = self.root / "released" / site["input_file"]
            metadata = json.loads((self.root / "released" / site["metadata_file"]).read_text(encoding="utf-8"))
            self.assertEqual(metadata["input_sha256"], hashlib.sha256(csv.read_bytes()).hexdigest())
            self.assertEqual(metadata["emission_factor_mode"], "regulatory_only")
            self.assertNotIn("grid_emission_factor", pd.read_csv(csv))


if __name__ == "__main__":
    unittest.main()
