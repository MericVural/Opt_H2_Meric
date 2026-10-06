"""Scientific boundary tests for the unreleased annual factor audit."""

import copy
import hashlib
import json

import pytest

from eu_emission_factor_audit import (
    FactorAuditError, JsonStat, apchp_envelope, electricity_only_factor,
    efficiency_allocation, finite_number, net_proxy, reference_scenarios,
    verified_sources, PDF_TABLE3_FACTORS,
)


def dataset(ids=("geo", "fuel"), codes=(("DE", "ES"), ("GAS", "COAL")), values=None, flags=None):
    return {"class": "dataset", "id": list(ids), "size": [len(c) for c in codes],
            "dimension": {key: {"category": {"index": {code: n for n, code in enumerate(categories)}}}
                          for key, categories in zip(ids, codes)},
            "value": values if values is not None else {"0": 10, "1": 0, "2": 20},
            "status": flags if flags is not None else {"3": "m"}}


def test_sparse_row_major_order_and_missing_zero_flag_are_distinct():
    source = JsonStat(dataset())
    assert source.get(geo="DE", fuel="GAS").value == 10
    zero = source.get(geo="DE", fuel="COAL")
    missing = source.get(geo="ES", fuel="COAL")
    assert zero.state == "published_zero" and zero.usable()
    assert missing.state == "missing" and missing.flag == "m" and not missing.usable()
    assert source.inventory() == {"grid_cells": 4, "published_number": 2,
                                  "published_zero": 1, "missing": 1, "flagged_cells": 1}


def test_dimension_order_is_read_from_source_instead_of_fixed_country_stride():
    source = JsonStat(dataset(ids=("fuel", "geo"), codes=(("GAS", "COAL"), ("ES", "DE")),
                             values={"0": 70, "1": 30, "2": 80, "3": 40}, flags={}))
    assert source.get(geo="DE", fuel="COAL").value == 40
    assert source.get(geo="ES", fuel="GAS").flat_index == 0


def test_list_category_index_and_dense_values():
    document = dataset(values=[10, 0, 20, None], flags=[None, None, "e", "m"])
    document["dimension"]["geo"]["category"]["index"] = ["DE", "ES"]
    source = JsonStat(document)
    assert source.get(geo="ES", fuel="GAS").flag == "e"
    assert not source.get(geo="ES", fuel="GAS").usable()


@pytest.mark.parametrize("change", [
    lambda d: d["value"].update({"4": 1}),
    lambda d: d["value"].update({"01": 1}),
    lambda d: d["value"].update({"0": True}),
    lambda d: d["value"].update({"0": float("nan")}),
    lambda d: d["status"].update({"0": 4}),
    lambda d: d["dimension"]["geo"]["category"]["index"].update({"DE": 1}),
    lambda d: d.update(size=[2, True]),
    lambda d: d.update(value=[1]),
])
def test_malformed_source_is_rejected(change):
    document = copy.deepcopy(dataset())
    change(document)
    with pytest.raises(FactorAuditError):
        JsonStat(document)


def test_lookup_requires_all_dimensions_and_known_codes():
    source = JsonStat(dataset())
    with pytest.raises(FactorAuditError):
        source.get(geo="DE")
    with pytest.raises(FactorAuditError):
        source.get(geo="FR", fuel="GAS")


@pytest.mark.parametrize("invalid", [True, None, "0.2", float("inf"), -1])
def test_bad_scientific_numbers_are_rejected(invalid):
    with pytest.raises(FactorAuditError):
        finite_number(invalid, "scientific input")


def test_tonnes_to_kg_and_same_energy_unit_ratio():
    # 0.2 t/MWh fuel at 50% gross efficiency, 10% gross/net multiplier.
    assert electricity_only_factor(.2, 200, 100, 1.1) == pytest.approx(440)


def test_efficiency_method_multiplies_emission_share():
    result = efficiency_allocation(.2, 200, 80, 80, 1.1, .4, .8)
    assert result["allocation_share_electricity"] == pytest.approx(2 / 3)
    assert result["point_kgCO2e_per_MWh"] == pytest.approx(.2 * 200 / 80 * 1.1 * 1000 * 2 / 3)


@pytest.mark.parametrize("args", [(.2, 80, 100, 1), (.2, 200, 0, 1), (.2, 200, 100, .99)])
def test_incompatible_electricity_only_boundaries_are_rejected(args):
    with pytest.raises(FactorAuditError):
        electricity_only_factor(*args)


def test_chp_output_energy_cannot_exceed_full_fuel_input():
    with pytest.raises(FactorAuditError):
        efficiency_allocation(.2, 100, 80, 80, 1.1, .4, .8)


def test_apchp_no_credit_is_stress_not_adopted_point_and_excludes_self_heat():
    result = apchp_envelope(.2, 200, 100, 20, 1.1)
    assert "point_kgCO2e_per_MWh" not in result
    assert result["no_heat_credit_stress_kgCO2e_per_MWh"] == pytest.approx(440)
    assert result["lower_kgCO2e_per_MWh"] == pytest.approx(220)
    assert result["upper_kgCO2e_per_MWh"] == pytest.approx(440)
    assert result["heat_credit_at_100pct_efficiency_diagnostic_kgCO2e_per_MWh"] == pytest.approx(396)
    assert any("self-used heat" in note for note in result["excluded"])


def test_published_zero_sold_heat_does_not_assert_absence_or_confidence():
    result = apchp_envelope(.2, 200, 100, 0, 1.1)
    assert result["published_zero_heat"] is True
    assert result["lower_kgCO2e_per_MWh"] is None


def test_gas_reference_point_and_published_scenario_envelope():
    result = reference_scenarios("G3000", .2, 200, 80, 80, 1.1)
    point = result["reference_point"]
    expected_share = (80 / .53) / (80 / .53 + 80 / .87)
    assert point["eta_el"] == .53 and point["eta_heat"] == .87
    assert result["point_kgCO2e_per_MWh"] == pytest.approx(550 * expected_share)
    assert result["lower_kgCO2e_per_MWh"] <= result["point_kgCO2e_per_MWh"] <= result["upper_kgCO2e_per_MWh"]
    assert len(result["scenario_records"]) == 24
    assert any(row["condensate_return_not_accounted"] for row in result["scenario_records"])
    assert "not a legal high-efficiency CHP assessment" in result["reference_limits"]


def test_apchp_applies_only_to_reported_subsystem():
    result = reference_scenarios("G3000", .2, 150, 100, 2, 1.05, autoproducer=True)
    assert result["method"] == "partial_reported_APCHP_subsystem_allocation_approximation"


def test_gross_net_allocation_comparison_keeps_same_net_denominator():
    result = reference_scenarios("G3000", .2, 200, 80, 80, 1.1)
    rows = [r for r in result["scenario_records"] if r["reference_vintage"] == "2016_2023"
            and r["heat_mode"] == "steam" and not r["condensate_return_not_accounted"]]
    assert len(rows) == 2
    gross, net = rows
    assert gross["allocation_power_tj"] == 80
    assert net["allocation_power_tj"] == pytest.approx(80 / 1.1)
    assert gross["denominator_power_net_tj"] == net["denominator_power_net_tj"]
    assert net["allocation_share_electricity"] < gross["allocation_share_electricity"]
    assert net["point_kgCO2e_per_MWh"] < gross["point_kgCO2e_per_MWh"]


def test_pdf_supplement_uses_direct_ghg_column_with_printed_precision():
    assert PDF_TABLE3_FACTORS["W6100"][3] == .522  # direct GHG, not CO2-only .515
    assert PDF_TABLE3_FACTORS["O4680"][3] == .280  # direct GHG, not LC .341
    assert PDF_TABLE3_FACTORS["O4610"][3] == .208  # direct GHG, not LC .281


def test_solid_biomass_has_range_but_no_invented_dry_wet_blend_point():
    result = reference_scenarios("R5110-5150_W6000RI", .0068472, 200, 50, 90, 1.05)
    assert result["point_kgCO2e_per_MWh"] is None
    assert result["reference_point"] is None
    assert len(result["scenario_records"]) == 48
    assert result["lower_kgCO2e_per_MWh"] < result["upper_kgCO2e_per_MWh"]


def test_unmapped_positive_reference_fuel_is_not_zeroed():
    with pytest.raises(FactorAuditError):
        reference_scenarios("X9900", .2, 200, 50, 90, 1.05)


def test_manifest_requires_original_bytes_and_successful_https_source(tmp_path):
    path = tmp_path / "source.json"
    path.write_bytes(b'{"value": 1}')
    entry = {"file": path.name, "url": "https://example.org/source", "http_status": 200,
             "bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    (tmp_path / "source_manifest.json").write_text(json.dumps([entry]))
    assert verified_sources(tmp_path)[path.name]["sha256"] == entry["sha256"]
    path.write_bytes(b'{"value": 2}')
    with pytest.raises(FactorAuditError, match="hash/length"):
        verified_sources(tmp_path)


@pytest.mark.parametrize("name", ["../outside.json", "a\\outside.json", "a/source.json"])
def test_manifest_path_escape_rejected(tmp_path, name):
    (tmp_path / "source_manifest.json").write_text(json.dumps([{"file": name}]))
    with pytest.raises(FactorAuditError):
        verified_sources(tmp_path)


def test_missing_net_correction_remains_missing():
    ids = ("freq", "plants", "operator", "nrg_bal", "siec", "unit", "geo", "time")
    codes = (("A",), ("ELC",), ("PRR_MAIN",), ("GEP", "NEP"), ("CF",), ("GWH",), ("DE",), ("2024",))
    proxy = net_proxy(JsonStat(dataset(ids, codes, {"0": 100}, {})), "DE", "MAPE")
    assert proxy["gross_to_net_factor"] is None
    assert proxy["net"]["state"] == "missing"


def test_net_correction_not_derived_from_customer_self_consumption():
    ids = ("freq", "plants", "operator", "nrg_bal", "siec", "unit", "geo", "time")
    codes = (("A",), ("CHP",), ("PRR_AUTO",), ("GEP", "NEP"), ("CF",), ("GWH",), ("ES",), ("2024",))
    proxy = net_proxy(JsonStat(dataset(ids, codes, {"0": 105, "1": 100}, {})), "ES", "APCHP")
    assert proxy["gross_to_net_factor"] == pytest.approx(1.05)
    assert proxy["source_dataset"] == "nrg_ind_peh"
