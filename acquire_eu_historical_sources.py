"""Archive public historical EU sources; never fill gaps or release model inputs.

Responses are retained as received, with URLs, retrieval times and SHA-256.
Resume verifies the saved receipt before reusing a response. Sources remain
unapproved until their units, intervals, categories and release gates are checked.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd

GENERATION_FILTERS = {
    "lignite": 1223, "wind_offshore": 1225,
    "hydro": 1226, "other_conventional": 1227, "other_renewable": 1228,
    "biomass": 4066, "wind_onshore": 4067, "solar": 4068,
    "hard_coal": 4069, "pumped_storage_output": 4070, "gas": 4071,
}
WEATHER_FIELDS = (
    "temperature_2m", "surface_pressure", "wind_speed_10m",
    "shortwave_radiation", "direct_normal_irradiance", "diffuse_radiation",
)


def archive_response(root: Path, relative: str, url: str) -> dict:
    destination = root / relative
    receipt_path = destination.with_suffix(destination.suffix + ".receipt.json")
    if destination.exists() or receipt_path.exists():
        if not destination.exists() or not receipt_path.exists():
            raise ValueError(f"Incomplete existing archive: {relative}")
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if receipt["source_url"] != url or hashlib.sha256(destination.read_bytes()).hexdigest() != receipt["sha256"]:
            raise ValueError(f"Existing source/receipt mismatch: {relative}")
        return receipt
    with urlopen(Request(url, headers={"User-Agent": "H2-academic-historical-data/1.0"}), timeout=60) as response:
        data = response.read()
        receipt = {
            "file": relative, "source_url": url,
            "retrieved_utc": datetime.now(timezone.utc).isoformat(),
            "http_status": response.status, "content_type": response.headers.get("Content-Type"),
            "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data),
            "data_release_status": "RAW_UNAPPROVED",
        }
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return receipt


def smard_requests(root: Path, filter_id: int, label: str, year: int) -> list[tuple[str, str]]:
    base = f"https://www.smard.de/app/chart_data/{filter_id}/DE"
    index_name = f"smard/{label}/index_hour.json"
    archive_response(root, index_name, base + "/index_hour.json")
    weeks = json.loads((root / index_name).read_text(encoding="utf-8"))["timestamps"]
    start = pd.Timestamp(f"{year}-01-01", tz="Europe/Berlin").tz_convert("UTC")
    end = pd.Timestamp(f"{year + 1}-01-01", tz="Europe/Berlin").tz_convert("UTC")
    candidates = [int(t) for t in weeks if start - pd.Timedelta(days=7) <= pd.Timestamp(t, unit="ms", tz="UTC") < end]
    if not candidates:
        raise ValueError(f"No SMARD weekly files covering {year}: {label}")
    return [(f"smard/{label}/{filter_id}_DE_hour_{t}.json", f"{base}/{filter_id}_DE_hour_{t}.json") for t in candidates]


def acquire(design_path: Path, root: Path, groups: set[str]) -> dict:
    design = json.loads(design_path.read_text(encoding="utf-8"))
    from eu_historical_data import validate_design
    validate_design(design)
    year = design["time"]["historical_year"]
    requests: list[tuple[str, str]] = []
    if "weather" in groups:
        for site in design["sites"]:
            query = {
                "latitude": site["coordinate"]["latitude"], "longitude": site["coordinate"]["longitude"],
                "start_date": f"{year-1}-12-31", "end_date": f"{year}-12-31", "hourly": ",".join(WEATHER_FIELDS),
                **design["weather"]["query_options"], "temperature_unit": "celsius",
            }
            requests.append((f"weather/{site['site_id']}_era5_{year}_padded.json", "https://archive-api.open-meteo.com/v1/archive?" + urlencode(query)))
    if "prices" in groups:
        hicp_query = {"freq": "A", "unit": "INX_A_AVG", "coicop18": "TOTAL", "geo": ["DE", "ES"], "sinceTimePeriod": "2023", "untilTimePeriod": str(year)}
        requests.append((f"price_basis/eurostat_prc_hicp_ainr_DE_ES_2023_{year}.json", "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/prc_hicp_ainr?" + urlencode(hicp_query, doseq=True)))
        requests.extend(smard_requests(root, 4169, "price", year))
        for month in range(1, 13):
            start = pd.Timestamp(year=year, month=month, day=1)
            last = start + pd.offsets.MonthEnd(0)
            query = {"start_date": start.strftime("%Y-%m-%dT00:00"), "end_date": last.strftime("%Y-%m-%dT23:59"), "time_trunc": "hour"}
            requests.append((f"redata/price/spot600_{year}{month:02d}.json", "https://apidatos.ree.es/es/datos/mercados/precios-mercados-tiempo-real?" + urlencode(query)))
    if "de_generation" in groups:
        for label, filter_id in GENERATION_FILTERS.items():
            requests.extend(smard_requests(root, filter_id, label, year))
    if "es_generation" in groups:
        for day in pd.date_range(f"{year}-01-01", f"{year}-12-31", freq="D"):
            day_string = day.strftime("%Y-%m-%d")
            query = {"callback": "archive", "curva": "DEMANDAAU", "fecha": day_string}
            requests.append((f"ree/generation/demandaau_{day:%Y%m%d}.jsonp", "https://demanda.ree.es/WSvisionaMovilesPeninsulaRest/resources/demandaGeneracionPeninsula?" + urlencode(query)))
    receipts, errors = [], []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        pending = {pool.submit(archive_response, root, relative, url): relative for relative, url in requests}
        for n, future in enumerate(concurrent.futures.as_completed(pending), 1):
            try:
                receipts.append(future.result())
            except Exception as exc:
                errors.append({"file": pending[future], "error": f"{type(exc).__name__}: {exc}"})
            if n % 50 == 0:
                print(f"Archived {n}/{len(requests)} responses; failures {len(errors)}", flush=True)
    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(), "historical_year": year,
        "design_sha256": hashlib.sha256(design_path.read_bytes()).hexdigest(),
        "groups": sorted(groups), "data_release_status": "RAW_UNAPPROVED",
        "requests": len(requests), "successes": len(receipts), "errors": errors,
        "receipts": sorted(receipts, key=lambda x: x["file"]),
        "index_receipts": [json.loads(p.read_text(encoding="utf-8")) for p in root.glob("smard/*/index_hour.json.receipt.json")],
        "german_nuclear_category": {"status": f"not_a_{year}_domestic_generation_series", "no_synthetic_zero_column": True, "source_url": "https://www.destatis.de/EN/Themes/Economic-Sectors-Enterprises/Energy/Production/Tables/gross-electricity-production.html"},
    }
    root.mkdir(parents=True, exist_ok=True)
    (root / ("acquisition_" + "_".join(sorted(groups)) + ".json")).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: manifest[k] for k in ("groups", "requests", "successes", "errors")}, ensure_ascii=False), flush=True)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--design", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--groups", default="weather,prices", help="weather,prices,de_generation,es_generation")
    args = parser.parse_args()
    groups = set(args.groups.split(","))
    if not groups or not groups <= {"weather", "prices", "de_generation", "es_generation"}:
        parser.error("Unknown acquisition group.")
    return 1 if acquire(args.design, args.output, groups)["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
