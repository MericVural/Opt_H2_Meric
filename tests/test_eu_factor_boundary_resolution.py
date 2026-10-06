import json

import pytest

from eu_emission_factor_audit import FactorAuditError, Observation
from eu_factor_boundary_resolution import biomass_reference_envelope, resolve_factor_boundaries, _supplementary_sources, _secondary_heat_record


def biomass_record():
    return {"geo": "DE", "plant": "MAPCHP", "siec": "R5110-5150_W6000RI", "calculation": {
        "scenario_records": [
            {"reference_category": "S4", "point_kgCO2e_per_MWh": 8.0},
            {"reference_category": "S5", "point_kgCO2e_per_MWh": 9.5},
        ], "point_kgCO2e_per_MWh": None, "reference_point": None,
        "lower_kgCO2e_per_MWh": 8.0, "upper_kgCO2e_per_MWh": 9.5}}


def test_biomass_preserves_uncertainty_without_inventing_point():
    result = biomass_reference_envelope(biomass_record())
    assert result["point_kgCO2e_per_MWh"] is None
    assert result["lower_kgCO2e_per_MWh"] == 8.0
    assert result["upper_kgCO2e_per_MWh"] == 9.5
    assert result["bounds_are_total_uncertainty"] is False
    assert result["released_for_hourly_mix"] is False


@pytest.mark.parametrize("mutation", ["single_family", "invented_point", "invented_reference", "mismatched_bound", "nan_factor", "negative_factor"])
def test_biomass_rejects_unsupported_or_corrupt_reference_envelopes(mutation):
    record = biomass_record()
    c = record["calculation"]
    if mutation == "single_family": c["scenario_records"][1]["reference_category"] = "S4"
    if mutation == "invented_point": c["point_kgCO2e_per_MWh"] = 8.5
    if mutation == "invented_reference": c["reference_point"] = {"eta_el": .33}
    if mutation == "mismatched_bound": c["upper_kgCO2e_per_MWh"] = 10.0
    if mutation == "nan_factor": c["scenario_records"][1]["point_kgCO2e_per_MWh"] = float("nan")
    if mutation == "negative_factor": c["scenario_records"][1]["point_kgCO2e_per_MWh"] = -1.0
    with pytest.raises(FactorAuditError): biomass_reference_envelope(record)


def test_supplementary_sources_rejects_hash_mismatch(tmp_path):
    p = tmp_path / "dummy.txt"
    p.write_text("unaudited")
    (tmp_path / "source_manifest.json").write_text(json.dumps([{"file": p.name, "url": "https://example.com/primary", "http_status": 200, "bytes": p.stat().st_size, "sha256": "0" * 64}]))
    with pytest.raises(FactorAuditError, match="hash/length"):
        _supplementary_sources(tmp_path)


def test_wrong_year_never_releases(tmp_path):
    p = tmp_path / "audit.json"
    p.write_text(json.dumps({"historical_year": 2024, "annual_proxy_year": 2024, "unit": "kgCO2e_per_MWh_electricity_net"}))
    with pytest.raises(FactorAuditError, match="scoped"):
        resolve_factor_boundaries(p, tmp_path, tmp_path)


class HeatDataset:
    def __init__(self, net=160.05, flag=None):
        self.net = net
        self.flag = flag

    def get(self, **coordinates):
        chemical = coordinates["siec"] == "X9900H"
        net = coordinates["nrg_bal"] == "NEP"
        value = 0.0 if chemical else self.net if net else 164.806
        return Observation(coordinates, 0, value, self.flag if net else None, "published_zero" if value == 0 else "published_number")


def heat_record():
    return {"geo": "ES", "plant": "APE", "siec": "H8000", "gross_power": {"value": 593.302}, "fuel": {"value": 0.0, "state": "published_zero"}}


def test_secondary_heat_is_not_promoted_to_primary_zero():
    result = _secondary_heat_record(heat_record(), HeatDataset())
    assert result["resolved_product"] == "H8000D"
    assert result["point_kgCO2e_per_MWh"] is None
    assert result["method_status"] == "secondary_energy_upstream_intensity_unresolved"
    assert result["gross_to_net_factor"] == pytest.approx(164.806 / 160.05)
    assert result["released_for_hourly_mix"] is False


@pytest.mark.parametrize("net,flag", [(170.0, None), (0.0, None), (160.05, "e")])
def test_secondary_heat_rejects_incompatible_or_flagged_measurement(net, flag):
    with pytest.raises(FactorAuditError, match="gross and net"):
        _secondary_heat_record(heat_record(), HeatDataset(net, flag))


def test_secondary_heat_rejects_mismatched_product_link():
    record = heat_record()
    record["gross_power"]["value"] = 257.231
    with pytest.raises(FactorAuditError, match="does not agree"):
        _secondary_heat_record(record, HeatDataset())
