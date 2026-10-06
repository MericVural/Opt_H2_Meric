"""Offline, unreleased Step 19 audit of 2024 fuel-to-electricity factors.

This writes evidence and conditional calculations, never solver input or a
complete technology factor table. Missing observations, published zeros,
flags, hierarchies, incompatible CHP boundaries and unmapped positive fuels
remain visible. The 2024 national observations are proxies for 2025 and,
for ES, for mainland production; neither transfer uncertainty is quantified.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import itertools
import json
import math
from numbers import Real
from pathlib import Path, PurePosixPath
from typing import Mapping
import xml.etree.ElementTree as ET
import zipfile


class FactorAuditError(ValueError):
    """Evidence is malformed, unverifiable, or incompatible with a formula."""


def finite_number(value, name, *, positive=False):
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
        raise FactorAuditError(f"{name} must be a finite number, not {value!r}.")
    if value < 0 or (positive and value <= 0):
        raise FactorAuditError(f"{name} must be {'positive' if positive else 'non-negative'}.")
    return float(value)


@dataclass(frozen=True)
class Observation:
    coordinates: dict
    flat_index: int
    value: float | None
    flag: str | None
    state: str

    def usable(self, *, positive=False):
        """No flag is silently accepted; published zero is not physical absence."""
        return self.flag is None and self.value is not None and self.value >= 0 and (
            not positive or self.value > 0
        )


class JsonStat:
    """Decode the Eurostat row-major index without assuming dimension order."""

    def __init__(self, document):
        if not isinstance(document, Mapping) or document.get("class") != "dataset":
            raise FactorAuditError("Expected a JSON-stat dataset.")
        self.document = document
        self.ids = document.get("id")
        self.sizes = document.get("size")
        if not isinstance(self.ids, list) or len(set(self.ids)) != len(self.ids):
            raise FactorAuditError("JSON-stat dimension IDs must be unique.")
        if not isinstance(self.sizes, list) or len(self.ids) != len(self.sizes):
            raise FactorAuditError("JSON-stat dimensions and sizes disagree.")
        self.codes = {}
        self.indices = {}
        self.labels = {}
        for key, size in zip(self.ids, self.sizes):
            if isinstance(size, bool) or not isinstance(size, int) or size < 1:
                raise FactorAuditError("JSON-stat sizes must be positive integers.")
            category = document.get("dimension", {}).get(key, {}).get("category", {})
            index = category.get("index")
            if isinstance(index, list):
                if len(set(index)) != len(index):
                    raise FactorAuditError("Duplicate category codes.")
                index = {code: position for position, code in enumerate(index)}
            if not isinstance(index, dict) or len(index) != size or any(
                isinstance(i, bool) or not isinstance(i, int) for i in index.values()
            ) or set(index.values()) != set(range(size)):
                raise FactorAuditError(f"Invalid category index: {key}.")
            self.indices[key] = index
            self.codes[key] = [code for code, _ in sorted(index.items(), key=lambda pair: pair[1])]
            self.labels[key] = category.get("label", {})
        self.count = math.prod(self.sizes)
        self.values = self._field(document.get("value", {}), "value")
        self.flags = self._field(document.get("status", {}), "status")
        for value in self.values.values():
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value)
            ):
                raise FactorAuditError("Published observations must be finite numbers or null.")
        for flag in self.flags.values():
            if flag is not None and not isinstance(flag, str):
                raise FactorAuditError("Observation flags must be strings or null.")

    def _field(self, field, name):
        if isinstance(field, list):
            if len(field) != self.count:
                raise FactorAuditError(f"Dense {name} length disagrees with dimensions.")
            return dict(enumerate(field))
        if not isinstance(field, dict):
            raise FactorAuditError(f"{name} must be sparse object or dense array.")
        result = {}
        for key, value in field.items():
            if not isinstance(key, str) or not key.isdecimal() or str(int(key)) != key:
                raise FactorAuditError(f"Invalid sparse index: {key!r}.")
            index = int(key)
            if not 0 <= index < self.count:
                raise FactorAuditError("Sparse index outside dataset dimensions.")
            result[index] = value
        return result

    def get(self, **coordinates):
        if set(coordinates) != set(self.ids):
            raise FactorAuditError("Every dimension must be selected explicitly.")
        index = 0
        for key, size in zip(self.ids, self.sizes):
            try:
                index = index * size + self.indices[key][coordinates[key]]
            except KeyError as exc:
                raise FactorAuditError(f"Unknown {key} code: {coordinates[key]!r}.") from exc
        value = self.values.get(index)
        flag = self.flags.get(index) or None
        state = "missing" if value is None else "published_zero" if value == 0 else "published_number"
        return Observation(coordinates, index, None if value is None else float(value), flag, state)

    def inventory(self):
        observations = (self.get(**dict(zip(self.ids, codes))) for codes in itertools.product(
            *(self.codes[key] for key in self.ids)
        ))
        counts = Counter(observation.state for observation in observations)
        counts["flagged_cells"] = sum(bool(flag) for flag in self.flags.values())
        return {"grid_cells": self.count, **dict(counts)}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def verified_sources(folder):
    """Verify every primary manifest entry before any numerical computation."""
    folder = Path(folder).resolve()
    manifest = load_json(folder / "source_manifest.json")
    if not isinstance(manifest, list):
        raise FactorAuditError("Source manifest must be a list.")
    result = {}
    for entry in manifest:
        if not isinstance(entry, dict):
            raise FactorAuditError("Invalid manifest entry.")
        name = entry.get("file")
        if not isinstance(name, str) or Path(name).name != name or "\\" in name or "/" in name:
            raise FactorAuditError("Source manifest must contain simple file names.")
        if name in result:
            raise FactorAuditError(f"Duplicate source manifest entry: {name}.")
        path = (folder / name).resolve()
        if path.parent != folder or not path.is_file():
            raise FactorAuditError(f"Missing or escaped source: {name}.")
        if entry.get("http_status") != 200 or not str(entry.get("url", "")).startswith("https://"):
            raise FactorAuditError(f"Unsuccessful or unidentified source download: {name}.")
        if entry.get("bytes") != path.stat().st_size or entry.get("sha256") != sha256(path):
            raise FactorAuditError(f"Source hash/length mismatch: {name}.")
        result[name] = {**entry, "path": str(path)}
    return result


def workbook_cells(path):
    """Read unmodified XLSX cells with the standard library; no Excel authoring."""
    main = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    relns = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    with zipfile.ZipFile(path) as archive:
        shared = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            shared = ["".join(item.itertext()) for item in root]
        relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        targets = {item.attrib["Id"]: item.attrib["Target"] for item in relationships}
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        result = {}
        for sheet in workbook.find(f"{{{main}}}sheets"):
            target = targets[sheet.attrib[f"{{{relns}}}id"]]
            target = target.lstrip("/") if target.startswith("/") else str(PurePosixPath("xl") / target)
            sheetroot = ET.fromstring(archive.read(target))
            cells = {}
            for cell in sheetroot.iter(f"{{{main}}}c"):
                kind = cell.attrib.get("t")
                value = cell.find(f"{{{main}}}v")
                if kind == "inlineStr":
                    value = "".join(cell.find(f"{{{main}}}is").itertext())
                elif value is None:
                    continue
                elif kind == "s":
                    value = shared[int(value.text)]
                elif kind in ("str", "e"):
                    value = value.text
                elif kind == "b":
                    value = bool(int(value.text))
                else:
                    value = float(value.text)
                cells[cell.attrib["r"]] = value
            result[sheet.attrib["name"]] = cells
        return result


# Exact source-label mapping only. Unlisted fossil gases, oils and waste do
# not inherit a nearby fuel's value. NCV fuel inputs are used consistently.
FUEL_CELLS = {
    "C0110": ("Table1_NRES", "D11", "Anthracite"),
    "C0129": ("Table1_NRES", "D12", "Other Bituminous Coal"),
    "C0210": ("Table1_NRES", "D13", "Sub-Bituminous Coal"),
    "C0220": ("Table1_NRES", "D10", "Lignite"),
    "P1100": ("Table1_NRES", "D14", "Peat"),
    "G3000": ("Table1_NRES", "D4", "Natural gas"),
    "O4200": ("Table1_NRES", "D6", "Natural Gas Liquids"),
    "O4630": ("Table1_NRES", "D5", "Liquefied Petroleum Gases"),
    "O4652XR5210B": ("Table1_NRES", "D9", "Motor gasoline"),
    "O4671XR5220B": ("Table1_NRES", "D7", "Gas/diesel oil"),
    "R5210P": ("Table2_RES", "E6", "Bio-gasoline"),
    "R5220P": ("Table2_RES", "E8", "Biodiesel"),
    "R5290": ("Table2_RES", "E4", "Other liquid biofuels"),
    "R5300": ("Table2_RES", "E16", "Biogas"),
    "W6210": ("Table2_RES", "E12", "Municipal wastes (biomass fraction)"),
    "W6220": ("Table1_NRES", "D15", "Municipal Wastes (non-biomass fraction)"),
}
NONCOMBUSTIBLE_CELLS = {
    "RA100": ("Table3_RES_electricity", "C5", "Hydroelectric"),
    "RA300": ("Table3_RES_electricity", "C4", "Wind"),
    "RA420": ("Table3_RES_electricity", "C6", "Photovoltaic"),
    "RA410": ("Table2_RES", "E18", "Solar thermal"),
    "RA200": ("Table2_RES", "E19", "Geothermal"),
}
# These are overlapping totals, not a partition of fuel inputs.
AGGREGATES = {"TOTAL", "C0000X0350-0370", "C0350-0370", "P1000", "O4000XBIO",
              "RA000", "W6100_6220", "BIOE", "FE"}
PLANTS = {"MAPE": ("ELC", "PRR_MAIN"), "APE": ("ELC", "PRR_AUTO"),
          "MAPCHP": ("CHP", "PRR_MAIN"), "APCHP": ("CHP", "PRR_AUTO")}

# Explicit transcriptions of the hashed consolidated regulation, Annex I
# (PDF p4) and Annex II (PDF p6-8), NCV/uncorrected ISO references. These
# values define accounting scenarios, never actual fleet ages or a legal
# high-efficiency test. Columns: before 2016, 2016-2023, from 2024.
REFERENCE_TABLE = {
    "S1": ((.442, .442, .530), ((.88, .83, .80), (.88, .83, .80), (.92, .87, .84))),
    "S2": ((.418, .418, .530), ((.86, .81, .78), (.86, .81, .78), (.92, .87, .84))),
    "S3": ((.390, .390, .530), ((.86, .81, .78), (.86, .81, .78), (.92, .87, .84))),
    "S4": ((.330, .370, .370), ((.86, .81, .78), (.86, .81, .78), (.86, .81, .78))),
    "S5": ((.250, .300, .300), ((.80, .75, .72), (.80, .75, .72), (.80, .75, .72))),
    "S6": ((.250, .250, .250), ((.80, .75, .72), (.80, .75, .72), (.80, .75, .72))),
    "L7": ((.442, .442, .530), ((.89, .84, .81), (.85, .80, .77), (.92, .87, .84))),
    "L8": ((.442, .442, .442), ((.89, .84, .81), (.85, .80, .77), (.85, .80, .77))),
    "G10": ((.525, .530, .530), ((.90, .85, .82), (.92, .87, .84), (.92, .87, .84))),
    "G12": ((.420, .420, .420), ((.70, .65, .62), (.80, .75, .72), (.80, .75, .72))),
    "G11B": ((.442, .442, .442), ((.89, .84, .81), (.90, .85, .82), (.90, .85, .82))),
    "G13": ((.350, .350, .350), ((.80, .75, .72), (.80, .75, .72), (.80, .75, .72))),
}
REFERENCE_CODES = {"C0110": ("S1",), "C0129": ("S1",), "C0210": ("S1",),
                   "C0220": ("S2",), "P1100": ("S3",), "G3000": ("G10",),
                   "O4630": ("G10",), "O4671XR5220B": ("L7",),
                   "R5290": ("L8",), "R5210P": ("L8",), "R5220P": ("L8",),
                   "R5300": ("G12",), "W6210": ("S6",), "W6220": ("S6",),
                   "R5110-5150_W6000RI": ("S4", "S5"),
                   "C0121": ("S1",), "C0330": ("S2",), "C0311": ("S1",),
                   "C0350": ("G13",), "C0371": ("G13",), "C0379": ("G13",),
                   "O4610": ("G11B",), "O4680": ("L7",), "O4694": ("S1",),
                   "O4699": ("L7",), "W6100": ("S6",)}

# Supporting Table 3 explicitly maps these Eurostat categories to direct
# fuel values. They are printed to 0.001 t/MWh, so they cannot be presented
# as the full-precision workbook values. Values are the GHG activity-based
# column, not the adjacent CO2-only or life-cycle columns.
PDF_TABLE3_FACTORS = {
    "C0121": (30, "Coking coal", "Coking coal", .342),
    "C0330": (30, "Brown coal briquettes", "Brown coal briquettes", .353),
    "C0311": (30, "Coke oven coke", "Coke oven coke and lignite coke", .387),
    "C0350": (30, "Coke oven gas", "Coke oven gas", .160),
    "C0371": (30, "Blast furnace gas", "Blast furnace gas", .936),
    "C0379": (31, "Other recovered gases", "Gas works gas", .160),
    "O4610": (31, "Refinery gas", "Refinery gas", .208),
    "O4680": (30, "Fuel oil", "Residual fuel oil", .280),
    "O4694": (31, "Petroleum coke", "Petroleum coke", .352),
    "O4699": (31, "Other oil products", "Refinery feedstocks", .265),
    "W6100": (30, "Industrial waste (non-renewable)", "Industrial wastes", .522),
}
VERIFIED_PDF_HASHES = {
    "JRC136272_2024_report.pdf": "0253e1a453fccf1646cd508b3fd21f86cefa05355a33c12cdf1a64868feceafd",
    "EU2015_2402_consolidated_20240101.pdf": "fd75aa7bba33b031df93819d1628ecee17bd8b2c49d5caf090ec05d4595d21e9",
    "Eurostat_Energy_Balance_Guide_2019.pdf": "0bb5bbbfcc2911a219dd076fac9a08d770e5437d374e32330a44053f764981ea",
}
VERIFIED_JRC_TABLE_TEXT_HASH = "c7d66adfdd61c6e6166318a44f4f3988f9b0b85cba886208c8c0cf96e77840d3"


def jrc_factors(folder, sources):
    name = "JRC_CoM_Emission_factors_for_local_energy_use_2024.xlsx"
    if name not in sources:
        raise FactorAuditError("Missing original JRC workbook manifest entry.")
    extraction_path = Path(folder) / "JRC_local_energy_2024_source_cells.json"
    extracted = load_json(extraction_path)
    if extracted.get("source_file") != name or extracted.get("source_sha256") != sources[name]["sha256"]:
        raise FactorAuditError("JRC extraction points to a different workbook.")
    actual = workbook_cells(sources[name]["path"])
    for sheet, rows in extracted.get("sheets", {}).items():
        for row in rows:
            for address, value in row["cells"].items():
                found = actual.get(sheet, {}).get(address)
                equal = (math.isclose(found, value, rel_tol=1e-12, abs_tol=1e-15)
                         if isinstance(value, Real) and not isinstance(value, bool)
                         and isinstance(found, Real) and not isinstance(found, bool) else found == value)
                if not equal:
                    raise FactorAuditError(f"Extracted JRC cell differs from source: {sheet}!{address}.")
    result = {}
    for code, (sheet, address, label) in {**FUEL_CELLS, **NONCOMBUSTIBLE_CELLS}.items():
        row = ''.join(character for character in address if character.isdigit())
        source_label = actual[sheet].get(("A" if sheet == "Table3_RES_electricity" else "B") + row)
        if ' '.join(str(source_label).split()).casefold() != ' '.join(label.split()).casefold() and not (
            code in ("RA410", "RA200") and actual[sheet].get("A" + row) == label
        ):
            raise FactorAuditError(f"JRC mapped source label does not match {code}: {source_label!r}.")
        result[code] = {
            "value_tCO2e_per_MWh": finite_number(actual[sheet][address], f"JRC {code}"),
            "source_file": name, "source_sha256": sources[name]["sha256"],
            "sheet": sheet, "cell": address, "label": label,
            "basis": "direct_activity_based_GHG_AR6_GWP100_NCV",
            "biogenic_CO2": "excluded; non-CO2 retained" if sheet == "Table2_RES" else "not_applicable",
        }
    # Primary solid biofuels combine wood and other solid primary biomass.
    # Both source categories publish the identical direct value; no blend
    # proportion is invented. Industrial waste is not included in this code.
    wood, other = actual["Table2_RES"]["E10"], actual["Table2_RES"]["E14"]
    if wood != other:
        raise FactorAuditError("Primary solid biomass source factors differ; composition is required.")
    result["R5110-5150_W6000RI"] = {
        "value_tCO2e_per_MWh": finite_number(wood, "primary solid biofuels"),
        "source_file": name, "source_sha256": sources[name]["sha256"],
        "sheet": "Table2_RES", "cells": ["E10", "E14"],
        "label": "Wood / wood waste and other primary solid biomass; identical source factors",
        "basis": "direct_activity_based_GHG_AR6_GWP100_NCV",
        "biogenic_CO2": "excluded; non-CO2 retained",
    }
    text_path = Path(folder) / "JRC136272_supporting_tables_1_2_3_source_text.txt"
    report_name = "JRC136272_2024_report.pdf"
    if sources.get(report_name, {}).get("sha256") != VERIFIED_PDF_HASHES[report_name] or sha256(text_path) != VERIFIED_JRC_TABLE_TEXT_HASH:
        raise FactorAuditError("Supporting Table 3 must use the previously verified report and extracted text bytes.")
    for code, (page, eurostat_label, ipcc_label, value) in PDF_TABLE3_FACTORS.items():
        result[code] = {
            "value_tCO2e_per_MWh": value, "source_file": report_name,
            "source_sha256": sources[report_name]["sha256"], "pdf_page": page,
            "table": "Supporting Table 3", "label": eurostat_label, "ipcc_label": ipcc_label,
            "basis": "direct_activity_based_GHG_AR6_GWP100_NCV",
            "biogenic_CO2": "not_applicable", "precision": "printed to 0.001 tCO2e/MWh; not full-precision workbook data",
            "display_rounding_half_step_tCO2e_per_MWh": .0005,
            "rounding_limit_is_not_physical_uncertainty": True,
            "source_extraction_file": text_path.name, "source_extraction_sha256": VERIFIED_JRC_TABLE_TEXT_HASH,
        }
    return result, {"file": extraction_path.name, "sha256": sha256(extraction_path),
                    "verification": "every extracted workbook cell agrees with the hashed original; PDF Table 3 values bound to independently verified original PDF and text hashes",
                    "pdf_extraction_file": text_path.name, "pdf_extraction_sha256": VERIFIED_JRC_TABLE_TEXT_HASH}


def net_proxy(peh, geo, plant):
    plants, operator = PLANTS[plant]
    coordinates = dict(freq="A", plants=plants, operator=operator, siec="CF", unit="GWH", geo=geo, time="2024")
    gross = peh.get(nrg_bal="GEP", **coordinates)
    net = peh.get(nrg_bal="NEP", **coordinates)
    ratio = None
    if gross.usable(positive=True) and net.usable(positive=True):
        if net.value > gross.value:
            raise FactorAuditError(f"Net production exceeds gross for {geo}/{plant}.")
        ratio = gross.value / net.value
    return {"geo": geo, "balance_plant": plant, "source_dataset": "nrg_ind_peh",
            "gross": asdict(gross), "net": asdict(net), "gross_to_net_factor": ratio,
            "scope": "combustible fuels total; proxy transferred to individual fuels",
            "uncertainty": "fuel-specific auxiliary consumption is not supplied"}


def electricity_only_factor(fuel_factor, fuel_tj, power_tj, net_multiplier):
    """TJ cancel; tCO2e/MWh is numerically kgCO2e/kWh, not kgCO2e/MWh."""
    factor = finite_number(fuel_factor, "fuel_factor")
    fuel = finite_number(fuel_tj, "fuel_tj", positive=True)
    power = finite_number(power_tj, "power_tj", positive=True)
    correction = finite_number(net_multiplier, "net_multiplier", positive=True)
    if correction < 1 or power > fuel:
        raise FactorAuditError("Incompatible electricity-only energy boundary or net multiplier.")
    return factor * fuel / power * correction * 1000  # kgCO2e / MWh electricity


def efficiency_allocation(fuel_factor, fuel_tj, power_tj, heat_tj, net_multiplier, eta_el, eta_heat):
    """Only for full, unallocated B/P/H with explicit compatible reference efficiencies."""
    point_without_heat = electricity_only_factor(fuel_factor, fuel_tj, power_tj, net_multiplier)
    heat = finite_number(heat_tj, "heat_tj")
    electricity_ref = finite_number(eta_el, "eta_el", positive=True)
    heat_ref = finite_number(eta_heat, "eta_heat", positive=True)
    if electricity_ref > 1 or heat_ref > 1 or power_tj + heat > fuel_tj * (1 + 1e-9):
        raise FactorAuditError("Incompatible full CHP boundary or reference efficiency.")
    allocation = (power_tj / electricity_ref) / (power_tj / electricity_ref + heat / heat_ref)
    return {"allocation_share_electricity": allocation,
            "point_kgCO2e_per_MWh": point_without_heat * allocation}


def apchp_envelope(fuel_factor, allocated_fuel_tj, power_tj, sold_heat_tj, net_multiplier):
    """Conditional accounting envelope, not a confidence interval.

    B contains fuel attributed to electricity plus SOLD heat. Fuel for
    self-used heat has already been excluded from B. The deliberately
    conservative point credits no sold heat. At H>0, a theoretical lower
    scenario allocates at least P fuel-energy to power (100% conversion),
    while the upper equals the no-credit point. This broad envelope needs
    no invented reference efficiency and says nothing about temporal or
    geographical transfer errors. If H is published zero, no physical
    absence is inferred and the lower is withheld rather than falsely
    narrowing to a point. A separate diagnostic tests a 100% heat-credit
    scenario without treating it as an adopted electricity allocation.
    """
    point = electricity_only_factor(fuel_factor, allocated_fuel_tj, power_tj, net_multiplier)
    heat = finite_number(sold_heat_tj, "sold_heat_tj")
    if power_tj + heat > allocated_fuel_tj * (1 + 1e-9):
        raise FactorAuditError("Reported APCHP electricity plus sold heat exceeds attributed input.")
    lower = float(fuel_factor) * float(net_multiplier) * 1000 if heat > 0 else None
    return {"no_heat_credit_stress_kgCO2e_per_MWh": point, "lower_kgCO2e_per_MWh": lower,
            "upper_kgCO2e_per_MWh": point,
            "stress_convention": "all reported B attributed to power; conservative no-sold-heat-credit scenario, not adopted point",
            "bound_convention": "conditional physical accounting envelope, not measured uncertainty or confidence interval",
            "published_zero_heat": heat == 0,
            "heat_credit_at_100pct_efficiency_diagnostic_kgCO2e_per_MWh":
                float(fuel_factor) * (float(allocated_fuel_tj) - heat) / float(power_tj) * float(net_multiplier) * 1000,
            "excluded": ["self-used heat excluded from B is never reallocated",
                         "2024-to-2025 uncertainty", "fuel-specific net transfer uncertainty",
                         "national-to-mainland ES uncertainty", "fuel-factor uncertainty"]}


def reference_scenarios(code, fuel_factor, fuel_tj, power_tj, heat_tj, net_multiplier, *, autoproducer=False):
    categories = REFERENCE_CODES.get(code)
    if not categories:
        raise FactorAuditError("No compatible EU reference category for this fuel.")
    rows = []
    for category in categories:
        electricity, heat = REFERENCE_TABLE[category]
        for vintage, (eta_el, heat_modes) in enumerate(zip(electricity, heat)):
            for mode, eta_heat in enumerate(heat_modes):
                for condensate_add in ((0, .05) if mode == 1 else (0,)):
                    for allocation_basis in ("reported_gross_power", "proxy_net_power"):
                        # Both calculations have the same net denominator.
                        # The PDF does not explicitly establish whether its
                        # reference electrical efficiency is gross or net.
                        # Evaluate that unresolved numerator convention too.
                        allocation_power = power_tj if allocation_basis == "reported_gross_power" else power_tj / net_multiplier
                        denominator_multiplier = net_multiplier if allocation_basis == "reported_gross_power" else 1
                        calculation = efficiency_allocation(fuel_factor, fuel_tj, allocation_power, heat_tj,
                                                            denominator_multiplier, eta_el, eta_heat + condensate_add)
                        rows.append({"reference_category": category,
                                     "reference_vintage": ("before_2016", "2016_2023", "from_2024")[vintage],
                                     "heat_mode": ("hot_water", "steam", "direct_exhaust_at_least_250C")[mode],
                                     "allocation_electricity_basis": allocation_basis,
                                     "allocation_power_tj": allocation_power,
                                     "denominator_power_net_tj": power_tj / net_multiplier,
                                     "condensate_return_not_accounted": condensate_add > 0,
                                     "eta_el": eta_el, "eta_heat": eta_heat + condensate_add, **calculation})
    # If the source category spans S4/S5 and contains no dry/non-dry shares,
    # both reference families are evaluated, but no composition point is
    # invented. The envelope remains a scenario comparison only.
    point = next(row for row in rows if row["reference_category"] == categories[0]
                 and row["reference_vintage"] == "2016_2023" and row["heat_mode"] == "steam"
                 and row["allocation_electricity_basis"] == "reported_gross_power"
                 and not row["condensate_return_not_accounted"])
    values = [row["point_kgCO2e_per_MWh"] for row in rows]
    return {
        "point_kgCO2e_per_MWh": point["point_kgCO2e_per_MWh"] if len(categories) == 1 else None,
        "reference_point": point if len(categories) == 1 else None,
        "lower_kgCO2e_per_MWh": min(values), "upper_kgCO2e_per_MWh": max(values),
        "scenario_records": rows,
        "method": "partial_reported_APCHP_subsystem_allocation_approximation" if autoproducer else "MAPCHP_full_reported_balance_efficiency_allocation",
        "point_convention": "provisional reported-gross allocation numerator, proxy-net denominator, declared 2016-2023 steam reference with condensate return accounted; no claim about actual plant vintage or heat mode",
        "bound_convention": "range across published reference vintages, heat modes, condensate options and gross/net allocation numerators; not statistical confidence or total uncertainty",
        "reference_limits": ["uncorrected ISO references", "not a legal high-efficiency CHP assessment",
                             "no actual plant age or heat-mode identification", "no climatic or avoided-grid-loss correction",
                             "reference electricity gross/net boundary unverified; both allocation conventions compared",
                             "2024-to-2025 and fuel-specific net/geographical transfer uncertainty excluded"],
        "multiple_reference_families_without_composition_point": len(categories) > 1,
    }


def build_audit(folder):
    folder = Path(folder)
    sources = verified_sources(folder)
    balance_name = "eurostat_nrg_bal_c_DE_ES_2024_TJ.json"
    peh_name = "eurostat_nrg_ind_peh_DE_ES_2024.json"
    reference_name = "EU2015_2402_consolidated_20240101.pdf"
    guide_name = "Eurostat_Energy_Balance_Guide_2019.pdf"
    jrc_report_name = "JRC136272_2024_report.pdf"
    for name in (balance_name, peh_name, reference_name, guide_name, jrc_report_name):
        if name not in sources:
            raise FactorAuditError(f"Required source absent from manifest: {name}.")
        if name in VERIFIED_PDF_HASHES and sources[name]["sha256"] != VERIFIED_PDF_HASHES[name]:
            raise FactorAuditError(f"Method transcription has not been verified against this version: {name}.")
    balance = JsonStat(load_json(folder / balance_name))
    peh = JsonStat(load_json(folder / peh_name))
    factors, extraction_evidence = jrc_factors(folder, sources)
    records, proxies, aggregates = [], [], []
    for geo, plant in itertools.product(("DE", "ES"), PLANTS):
        proxy = net_proxy(peh, geo, plant)
        proxies.append(proxy)
        for code in balance.codes["siec"]:
            coords = dict(freq="A", siec=code, unit="TJ", geo=geo, time="2024")
            fuel = balance.get(nrg_bal=f"TI_EHG_{plant}_E", **coords)
            power = balance.get(nrg_bal=f"GEP_{plant}", **coords)
            heat = balance.get(nrg_bal=f"GHP_{plant}", **coords) if "CHP" in plant else None
            if not ((fuel.value is not None and fuel.value > 0) or (power.value is not None and power.value > 0)):
                continue
            record = {"geo": geo, "plant": plant, "siec": code, "siec_label": balance.labels["siec"].get(code),
                      "fuel": asdict(fuel), "gross_power": asdict(power),
                      "reported_heat": asdict(heat) if heat else None,
                      "balance_source_file": balance_name, "balance_source_sha256": sources[balance_name]["sha256"],
                      "net_correction": proxy, "fuel_factor": factors.get(code),
                      "method_status": "blocked", "reasons": [], "released_for_hourly_mix": False,
                      "scope_flags": ["2024_proxy_for_2025"] + (["ES_national_proxy_for_mainland"] if geo == "ES" else [])}
            if code in AGGREGATES:
                record["method_status"] = "hierarchy_aggregate_excluded"
                aggregates.append(record)
                continue
            if code not in factors:
                record["reasons"].append("No exact direct JRC source mapping for this positive fuel or production category.")
            elif code in NONCOMBUSTIBLE_CELLS and power.usable(positive=True):
                record.update(method_status="sourced_direct_noncombustible_factor",
                              calculation={"point_kgCO2e_per_MWh": factors[code]["value_tCO2e_per_MWh"] * 1000,
                                           "lower_kgCO2e_per_MWh": None, "upper_kgCO2e_per_MWh": None,
                                           "uncertainty": "direct source point only; not a statistical interval"})
            elif not fuel.usable(positive=True) or not power.usable(positive=True):
                record["reasons"].append("Positive, unflagged, compatible B and P observations are required.")
            elif proxy["gross_to_net_factor"] is None:
                record["reasons"].append("No positive, unflagged combustible gross/net pair for country and operator/plant type.")
            elif "CHP" in plant and (not heat or not heat.usable()):
                record["reasons"].append("Reported sold-heat observation is missing or flagged; cannot assume zero.")
            else:
                try:
                    if "CHP" in plant:
                        record["calculation"] = reference_scenarios(
                            code, factors[code]["value_tCO2e_per_MWh"], fuel.value,
                            power.value, heat.value, proxy["gross_to_net_factor"], autoproducer=plant == "APCHP")
                        record["calculation"]["reference_source_file"] = reference_name
                        record["calculation"]["reference_source_sha256"] = sources[reference_name]["sha256"]
                        record["calculation"]["reference_source_pages"] = [4, 6, 7, 8]
                        record["calculation"]["published_zero_heat_assumption"] = heat.state == "published_zero"
                        record["method_status"] = "conditional_APCHP_subsystem_approximation" if plant == "APCHP" else "conditional_MAPCHP_reference_allocation"
                        if plant == "APCHP":
                            record["calculation"]["no_heat_credit_stress"] = apchp_envelope(
                                factors[code]["value_tCO2e_per_MWh"], fuel.value,
                                power.value, heat.value, proxy["gross_to_net_factor"])
                            record["calculation"]["self_used_heat"] = "excluded by Eurostat before reported B; never reintroduced or reallocated"
                        if len(REFERENCE_CODES[code]) > 1:
                            record["reasons"].append("Source spans multiple reference families; no blend point selected without shares.")
                        if heat.state == "published_zero":
                            record["scope_flags"].append("published_zero_sold_heat_used_as_explicit_calculation_assumption_not_physical_absence")
                        record["scope_flags"].append("reference_electricity_gross_net_boundary_unverified_both_allocation_conventions_compared")
                    else:
                        point = electricity_only_factor(factors[code]["value_tCO2e_per_MWh"], fuel.value, power.value,
                                                        proxy["gross_to_net_factor"])
                        record["calculation"] = {"point_kgCO2e_per_MWh": point,
                                                 "lower_kgCO2e_per_MWh": None, "upper_kgCO2e_per_MWh": None,
                                                 "uncertainty": "source point plus combustible net proxy; interval not yet evidenced"}
                        record["method_status"] = "conditional_electricity_only_factor"
                    record["calculation"]["fuel_source_precision"] = factors[code].get("precision", "full-precision published workbook cell")
                    if "display_rounding_half_step_tCO2e_per_MWh" in factors[code]:
                        record["scope_flags"].append("printed_fuel_factor_rounded_to_0.001_tCO2e_per_MWh")
                except FactorAuditError as exc:
                    record["reasons"].append(str(exc))
            records.append(record)
    return {
        "schema_version": 1, "created_utc": datetime.now(timezone.utc).isoformat(),
        "historical_year": 2025, "annual_proxy_year": 2024,
        "scope": "direct activity-based CO2e; production, excluding biogenic CO2 and upstream life-cycle emissions",
        "unit": "kgCO2e_per_MWh_electricity_net",
        "factor_table_released": False, "hourly_factors_released": False, "step19_complete": False,
        "status": "reproducible annual audit and conditional scenarios; no completed technology factor release",
        "sources": [{key: value for key, value in source.items() if key != "path"} for source in sources.values()],
        "cell_extraction": extraction_evidence,
        "software_sha256": sha256(__file__),
        "dataset_inventories": {balance_name: balance.inventory(), peh_name: peh.inventory()},
        "calorific_basis_evidence": {
            "balance": {"file": guide_name, "sha256": sources[guide_name]["sha256"], "pdf_page": 8,
                        "statement": "all energy balance flows use NCV; 1 GWh equals 3.6 TJ"},
            "fuel_factors": {"file": jrc_report_name, "sha256": sources[jrc_report_name]["sha256"], "pdf_page": 9,
                             "statement": "direct fuel factors use a net-calorific basis"},
            "references": {"file": reference_name, "sha256": sources[reference_name]["sha256"], "pdf_pages": [4, 6],
                           "statement": "Annex I and II references use NCV and standard atmospheric ISO conditions"},
            "CHP_supplementary_table": "GCV and NCV observations in nrg_chp_f are not mixed into the energy-balance calculation",
        },
        "zero_semantics": "Published zero is retained as a numeric observation, never proof of physical absence; Eurostat zeros may also cover unavailable/confidential/negligible quantities.",
        "national_net_proxies": proxies,
        "category_records": records, "excluded_hierarchy_records": aggregates,
        "summary": dict(Counter(record["method_status"] for record in records)),
        "remaining_release_conditions": [
            "Complete exact mappings for every positive source generation category without double-counting hierarchies.",
            "Validate reference-family and heat-mode approximation against fleet information; scenario envelope is not full uncertainty.",
            "Resolve the reference electricity gross/net boundary before adopting the provisional CHP point; both conventions are evaluated as scenarios.",
            "Evaluate APCHP sold-heat scenarios and ambiguous published zeros; do not reallocate excluded self-used heat.",
            "Quantify or explicitly limit fuel-specific net, 2024-to-2025, fuel-factor and ES geographical transfer uncertainty.",
            "Reconcile SMARD/REE production boundaries, residual categories, and Spanish instantaneous-power quality/outage coverage.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--factor-basis", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    audit = build_audit(args.factor_basis)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / "annual_factor_audit_2024_proxy.json"
    output.write_text(json.dumps(audit, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output.resolve()), "summary": audit["summary"],
                      "factor_table_released": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
