"""Supplemental, offline Step 19 factor-boundary evidence.

Resolves two direct zero factors from EEA evidence, describes biomass bounds,
and explicitly withholds the intensity of secondary-heat electricity. This
module never releases a complete technology table or hourly solver input.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
import math
from pathlib import Path
import re

import eu_emission_factor_audit as original_audit_module
from eu_emission_factor_audit import FactorAuditError, JsonStat, load_json, sha256, verified_sources


SOURCE_HASHES = {
    "EU2008_952_CHP_boundaries.pdf": "0b0adc2f83a8aa81b4806fa9e76d44cd6067612e975c4724ed6790e9c5daa31a",
    "IEA_AEHQ_instructions_2024.pdf": "b9e3e38df55c2de72d5107c4874b929b3e0cb2d8987e40e77052ecfc68e41a57",
    "EEA_direct_GHG_electricity_intensity_methodology.html": "2bf24f487991aaebd235476165f3313cb84e1b51e552008e2a8f326fe8a294c5",
}


class _TextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def _html_text(path):
    parser = _TextParser()
    parser.feed(Path(path).read_text(encoding="utf-8"))
    return re.sub(r"\s+", " ", " ".join(parser.parts)).casefold()


def _supplementary_sources(folder):
    sources = verified_sources(folder)
    for name, expected in SOURCE_HASHES.items():
        if sources.get(name, {}).get("sha256") != expected:
            raise FactorAuditError(f"Supplementary statement is not bound to reviewed source: {name}.")
    text = _html_text(sources["EEA_direct_GHG_electricity_intensity_methodology.html"]["path"])
    statement = "a zero co 2 e emission factor was applied to nuclear power and to renewables"
    if statement not in text or "does not take into account life-cycle greenhouse gas emissions" not in text:
        raise FactorAuditError("Archived EEA source does not contain the reviewed direct-zero statement.")
    proof_path = Path(folder) / "statement_extraction_checks.json"
    proof = load_json(proof_path)
    expected_checks = {
        "CHP_generator_terminals_no_internal_consumption_deduction": ("EU2008_952_CHP_boundaries.pdf", 6),
        "secondary_heat_includes_recovered_purchased_waste_heat": ("IEA_AEHQ_instructions_2024.pdf", 8),
        "tide_wave_ocean_is_mechanical_energy": ("IEA_AEHQ_instructions_2024.pdf", 8),
    }
    if set(proof.get("checks", {})) != set(expected_checks):
        raise FactorAuditError("Missing or unexpected independently extracted source statement.")
    for key, (name, page) in expected_checks.items():
        item = proof["checks"][key]
        if item.get("source_file") != name or item.get("source_sha256") != sources[name]["sha256"] or item.get("pdf_page") != page or item.get("matched") is not True:
            raise FactorAuditError(f"Source-statement extraction does not verify {key}.")
    return sources, {"file": proof_path.name, "sha256": sha256(proof_path), "checks": proof["checks"]}


def biomass_reference_envelope(record):
    """No dry/wet composition is imputed; retain the audited endpoint envelope."""
    calculation = record.get("calculation", {})
    rows = calculation.get("scenario_records", [])
    if not rows or {row.get("reference_category") for row in rows} != {"S4", "S5"}:
        raise FactorAuditError("Solid biomass envelope must include both source reference categories.")
    values = [row.get("point_kgCO2e_per_MWh") for row in rows]
    if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0 for value in values):
        raise FactorAuditError("Biomass reference scenarios require finite nonnegative values.")
    lower, upper = min(values), max(values)
    if calculation.get("point_kgCO2e_per_MWh") is not None or calculation.get("reference_point") is not None:
        raise FactorAuditError("Unknown S4/S5 shares cannot imply a reference point.")
    if not math.isclose(lower, calculation.get("lower_kgCO2e_per_MWh", -1), abs_tol=1e-10) or not math.isclose(upper, calculation.get("upper_kgCO2e_per_MWh", -1), abs_tol=1e-10):
        raise FactorAuditError("Audited biomass bounds do not match their scenario records.")
    return {
        "geo": record["geo"], "plant": record["plant"], "siec": record["siec"],
        "point_kgCO2e_per_MWh": None,
        "lower_kgCO2e_per_MWh": lower, "upper_kgCO2e_per_MWh": upper,
        "method_status": "conditional_reference_envelope_without_composition_point",
        "reference_categories": ["S4", "S5"], "scenario_count": len(rows),
        "reported_heat_observation": record.get("reported_heat"),
        "convention": "source reference endpoints across vintages, heat modes, condensate options and allocation-power conventions",
        "mixture_statement": "Any fuel-energy-weighted mixture of the same two reference families lies between their allocation endpoint scenarios; this does not identify a fleet composition.",
        "excluded_uncertainties": ["2024-to-2025 transfer", "national-to-mainland transfer", "fuel-specific auxiliary electricity", "fuel-factor uncertainty", "incomplete fleet/heat-mode coverage"],
        "bounds_are_total_uncertainty": False,
        "degenerate_reference_envelope_is_total_certainty": False,
        "released_for_hourly_mix": False,
    }


def _secondary_heat_record(record, peh):
    plant_code = {"APE": "ELC", "APCHP": "CHP"}.get(record["plant"])
    if record.get("geo") != "ES" or plant_code is None:
        raise FactorAuditError("Unexpected positive secondary-heat balance record.")
    coordinates = dict(freq="A", plants=plant_code, operator="PRR_AUTO", siec="H8000D", unit="GWH", geo="ES", time="2024")
    gross = peh.get(nrg_bal="GEP", **coordinates)
    net = peh.get(nrg_bal="NEP", **coordinates)
    chemical = peh.get(nrg_bal="GEP", **{**coordinates, "siec": "X9900H"})
    if not gross.usable(positive=True) or not net.usable(positive=True) or net.value > gross.value:
        raise FactorAuditError("Secondary heat requires independently published, unflagged gross and net output.")
    if not math.isclose(record["gross_power"]["value"], 3.6 * gross.value, rel_tol=0, abs_tol=.003):
        raise FactorAuditError("Balance H8000 output does not agree with derived-heat electricity.")
    return {
        "geo": "ES", "plant": record["plant"], "siec": "H8000",
        "resolved_product": "H8000D", "resolved_label": "Derived heat and district heating",
        "gross_power_balance_tj": record["gross_power"]["value"],
        "gross_electricity_observation": asdict(gross), "net_electricity_observation": asdict(net),
        "chemical_heat_electricity_observation": asdict(chemical),
        "gross_to_net_factor": gross.value / net.value,
        "input_observation": record["fuel"],
        "point_kgCO2e_per_MWh": None,
        "method_status": "secondary_energy_upstream_intensity_unresolved",
        "source_statement": "AEHQ Table 1, Other sources: electricity from heat supplied via the grid or autoproducers; its derived-heat subset includes recovered, purchased and waste heat.",
        "interpretation": "Secondary heat is not an independently emission-free primary fuel. The zero recorded transformation input is not evidence of zero upstream intensity.",
        "double_counting_rule": "Do not add a second fuel-combustion emission inventory for the same heat; trace originating fuel/process or document a scope-specific recovery allocation.",
        "hourly_scope_assignment": "Requires source category mapping before deciding whether this national annual observation enters the hourly mix.",
        "released_for_hourly_mix": False,
    }


def resolve_factor_boundaries(annual_audit_path, factor_basis_folder, supplementary_folder):
    audit_path = Path(annual_audit_path)
    audit = load_json(audit_path)
    if audit.get("historical_year") != 2025 or audit.get("annual_proxy_year") != 2024 or audit.get("unit") != "kgCO2e_per_MWh_electricity_net":
        raise FactorAuditError("Supplement is scoped to the reviewed 2025/2024 net-electricity audit.")
    if audit.get("software_sha256") != sha256(original_audit_module.__file__):
        raise FactorAuditError("Annual audit software differs from the available reviewed calculation module.")
    original_sources = verified_sources(factor_basis_folder)
    source_map = {source["file"]: source for source in audit.get("sources", [])}
    for name in ("eurostat_nrg_ind_peh_DE_ES_2024.json", "eurostat_nrg_bal_c_DE_ES_2024_TJ.json"):
        if source_map.get(name, {}).get("sha256") != original_sources.get(name, {}).get("sha256"):
            raise FactorAuditError(f"Annual audit does not refer to the verified original source: {name}.")
    sources, statements = _supplementary_sources(supplementary_folder)
    peh = JsonStat(load_json(original_sources["eurostat_nrg_ind_peh_DE_ES_2024.json"]["path"]))
    balance = JsonStat(load_json(original_sources["eurostat_nrg_bal_c_DE_ES_2024_TJ.json"]["path"]))
    records = audit.get("category_records", [])
    zeros, biomass, secondary_heat = [], [], []
    for record in records:
        if record.get("siec") in ("N900H", "RA500", "H8000", "R5110-5150_W6000RI"):
            for key in ("fuel", "gross_power", "reported_heat"):
                observation = record.get(key)
                if observation is not None and observation != asdict(balance.get(**observation.get("coordinates", {}))):
                    raise FactorAuditError(f"Annual audit {key} observation differs from its original JSON-stat source.")
        if record.get("siec") in ("N900H", "RA500"):
            if record.get("geo") != "ES" or record.get("plant") != "MAPE" or record.get("gross_power", {}).get("value", 0) <= 0:
                raise FactorAuditError("Unexpected nuclear/ocean record in reviewed annual audit.")
            zeros.append({
                "geo": record["geo"], "plant": record["plant"], "siec": record["siec"],
                "factor_kgCO2e_per_MWh_electricity_net": 0.0,
                "factor_origin": "EEA direct-GHG electricity-intensity methodology; separate supplementary mapping, no JRC cell",
                "source_file": "EEA_direct_GHG_electricity_intensity_methodology.html",
                "source_sha256": sources["EEA_direct_GHG_electricity_intensity_methodology.html"]["sha256"],
                "method_status": "sourced_direct_noncombustible_zero",
                "scope": "direct generation; upstream/life-cycle emissions excluded",
                "zero_is_source_mapping_not_missing_value_fill": True,
                "renewable_classification_evidence": "AEHQ Table 1 defines ocean electricity as mechanical tidal/wave/current energy" if record["siec"] == "RA500" else None,
                "released_for_hourly_mix": False,
            })
        if record.get("siec") == "H8000":
            secondary_heat.append(_secondary_heat_record(record, peh))
        if record.get("siec") == "R5110-5150_W6000RI" and record.get("plant") in ("MAPCHP", "APCHP"):
            biomass.append(biomass_reference_envelope(record))
    if {item["siec"] for item in zeros} != {"N900H", "RA500"} or len(zeros) != 2 or len(secondary_heat) != 2 or len(biomass) != 3:
        raise FactorAuditError("Reviewed category inventory has changed; re-audit boundary resolutions.")
    return {
        "schema_version": "1.0", "created_utc": datetime.now(timezone.utc).isoformat(),
        "historical_year": 2025, "annual_proxy_year": 2024,
        "annual_audit_sha256": sha256(audit_path), "software_sha256": sha256(__file__),
        "sources": [{key: value for key, value in entry.items() if key != "path"} for entry in sources.values()],
        "statement_extraction_evidence": statements,
        "direct_zero_resolutions": zeros, "biomass_reference_envelopes": biomass,
        "secondary_heat_resolutions": secondary_heat,
        "reference_electricity_basis": {
            "CHP_output_measurement": "gross electricity at generator terminals; internal use not removed, Decision 2008/952/EC Annex II.3 (PDF page 6)",
            "separate_reference_efficiency_output_basis": "not explicitly established by the reviewed Annex I/IV text; NCV specifies fuel calorific basis, not net electricity",
            "adopted_point_convention": "reported gross electricity allocation numerator, proxy net electricity factor denominator, disclosed accounting approximation",
            "alternative_convention": "retain proxy-net electricity allocation numerator as a sensitivity scenario with the same net denominator",
            "gross_reference_efficiency_proven": False,
            "legal_high_efficiency_certification": False,
            "climate_and_avoided_grid_loss_corrections": "not applied; ISO reference parameters used for a common accounting approximation",
        },
        "net_proxy_assessment": {
            "per_fuel_measured_net_output_required_for_conditional_proxy": False,
            "proxy_scope": "country/producer/plant-type combustible gross-to-net ratio transferred to fuel-specific factors",
            "scientific_status": "explicit approximate auxiliary-consumption allocation; source ratios are measured aggregate data, transferred fuel-level ratios are not measurements",
            "sensitivity_requirement": "retain gross/net allocation convention envelope and disclose fuel-specific auxiliary consumption as unquantified transfer uncertainty",
            "secondary_heat_exception": "H8000D supplies its own gross and net observations; do not use CF net proxy for these records",
        },
        "complete_technology_factor_table_released": False,
        "hourly_factors_released": False, "step19_complete": False,
        "remaining_conditions": ["Map actual hourly categories without omissions or duplicate physical generation", "Resolve secondary-heat intensity/scope if it belongs to an included hourly category", "Preserve S4/S5 bounds without inventing a biomass composition point", "Disclose proxy and reference conventions in any conditional factor scenarios"],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--annual-audit", type=Path, required=True)
    parser.add_argument("--factor-basis", type=Path, required=True)
    parser.add_argument("--supplementary-sources", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    report = resolve_factor_boundaries(args.annual_audit, args.factor_basis, args.supplementary_sources)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Boundary resolution written: {args.output}; full technology/hourly release remains false.")


if __name__ == "__main__":
    main()
