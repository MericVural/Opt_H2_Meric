"""Prepare strictly aligned EU weather, prices and generation diagnostics.

This Step-19 command does not create a released solver input. In particular it
never supplies a placeholder emission factor. Factor construction, Spanish
source coverage and blackout treatment must be approved before release.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from importlib.metadata import version
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode, urlparse, parse_qs

import numpy as np
import pandas as pd

from acquire_eu_historical_sources import GENERATION_FILTERS
from eu_historical_data import HistoricalDataError, adapt_open_meteo_weather, aggregate_interval_series, local_year_index, validate_design


def verified_bytes(path: Path, expected_url: str | None = None) -> bytes:
    receipt = json.loads(path.with_suffix(path.suffix + ".receipt.json").read_text(encoding="utf-8"))
    raw = path.read_bytes()
    if Path(receipt.get("file", "")).name != path.name or receipt.get("http_status") != 200:
        raise HistoricalDataError(f"Raw receipt file/status mismatch: {path.name}")
    if expected_url is not None and receipt.get("source_url") != expected_url:
        raise HistoricalDataError(f"Raw receipt source URL mismatch: {path.name}")
    if hashlib.sha256(raw).hexdigest() != receipt["sha256"]:
        raise HistoricalDataError(f"Raw source hash differs from receipt: {path.name}")
    return raw


def verified_json(path: Path, expected_url: str | None = None) -> dict:
    return json.loads(verified_bytes(path, expected_url))


def national_hicp_deflators(root: Path, year: int = 2024) -> dict:
    if type(year) is not int or year not in (2024, 2025):
        raise HistoricalDataError("Price source year must explicitly be 2024 or 2025.")
    directory = root / "price_basis"
    path = directory / f"eurostat_prc_hicp_ainr_DE_ES_2023_{year}.json"
    if path.with_suffix(path.suffix + ".receipt.json").exists():
        receipt = json.loads(path.with_suffix(path.suffix + ".receipt.json").read_text(encoding="utf-8"))
        receipt = {**receipt, "url": receipt.get("source_url"), "http_status": receipt.get("http_status")}
    else:
        manifest = json.loads((directory / "source_manifest.json").read_text(encoding="utf-8"))
        matches = [r for r in manifest if Path(r["file"]).name == path.name]
        if len(matches) != 1:
            raise HistoricalDataError("Exactly one HICP receipt is required.")
        receipt = matches[0]
    source_url = urlparse(receipt["url"])
    query = parse_qs(source_url.query)
    if source_url.netloc != "ec.europa.eu" or not source_url.path.endswith("/prc_hicp_ainr") or receipt.get("http_status") != 200:
        raise HistoricalDataError("HICP receipt is not the selected official dataset.")
    expected = {"freq": ["A"], "unit": ["INX_A_AVG"], "coicop18": ["TOTAL"], "sinceTimePeriod": ["2023"], "untilTimePeriod": [str(year)]}
    if any(query.get(key) != value for key, value in expected.items()) or set(query.get("geo", [])) != {"DE", "ES"}:
        raise HistoricalDataError("HICP source URL does not match the approved series.")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != receipt["sha256"]:
        raise HistoricalDataError("HICP source hash mismatch.")
    payload = json.loads(raw)
    dimensions = payload["dimension"]
    if payload["id"] != ["freq", "unit", "coicop18", "geo", "time"]:
        raise HistoricalDataError("Unexpected HICP dimensions.")
    for name, expected in (("freq", "A"), ("unit", "INX_A_AVG"), ("coicop18", "TOTAL")):
        if set(dimensions[name]["category"]["index"]) != {expected}:
            raise HistoricalDataError(f"Incorrect HICP series: {name}")
    def observation(country: str, reference_year: int) -> float:
        coordinates = {"freq": "A", "unit": "INX_A_AVG", "coicop18": "TOTAL", "geo": country, "time": str(reference_year)}
        position = 0
        for name, size in zip(payload["id"], payload["size"]):
            position = position * size + dimensions[name]["category"]["index"][coordinates[name]]
        value = payload["value"][str(position)]
        status = payload.get("status", {})
        flag = status[position] if isinstance(status, list) else status.get(str(position))
        if flag:
            raise HistoricalDataError(f"HICP observation is flagged: {country}/{reference_year}: {flag}")
        if isinstance(value, bool) or not np.isfinite(value) or value <= 0:
            raise HistoricalDataError("HICP observation must be finite and positive.")
        return float(value)
    return {country: {
        "index_2023": observation(country, 2023), f"index_{year}": observation(country, year),
        f"multiplier_nominal_{year}_to_real_2023": observation(country, 2023) / observation(country, year),
        "source_price_year": year, "price_year": 2023,
        "source_url": receipt["url"], "source_sha256": receipt["sha256"],
        "source_updated": payload.get("updated"), "dataset": "prc_hicp_ainr",
        "unit": "INX_A_AVG", "coicop18": "TOTAL", "unit_label": dimensions["unit"]["category"].get("label", {}).get("INX_A_AVG"),
        "interpretation": "National all-items consumer-price annual mean; no claim of a wholesale-electricity price forecast",
    } for country in ("DE", "ES")}


def load_smard(root: Path, label: str, target: pd.DatetimeIndex) -> pd.Series:
    paths = sorted(p for p in (root / "smard" / label).glob("*_DE_hour_*.json") if not p.name.endswith(".receipt.json"))
    if not paths:
        raise HistoricalDataError(f"No archived SMARD series: {label}")
    rows = []
    filter_id = 4169 if label == "price" else GENERATION_FILTERS[label]
    for path in paths:
        payload = verified_json(path, f"https://www.smard.de/app/chart_data/{filter_id}/DE/{path.name}")
        if "series" not in payload or not payload["series"]:
            raise HistoricalDataError(f"Empty SMARD response: {path.name}")
        rows.extend(payload["series"])
    frame = pd.DataFrame(rows, columns=["epoch_ms", "value"])
    index = pd.to_datetime(frame["epoch_ms"], unit="ms", utc=True)
    series = pd.Series(frame["value"].to_numpy(), index=pd.DatetimeIndex(index), name=label)
    if series.index.has_duplicates or not series.index.is_monotonic_increasing:
        raise HistoricalDataError(f"SMARD {label}: raw rows are duplicate or unordered.")
    selected = series[(series.index >= target[0]) & (series.index <= target[-1])]
    if selected.index.has_duplicates or not selected.index.equals(target):
        raise HistoricalDataError(f"SMARD {label}: source does not exactly cover the required UTC hours.")
    # Prices and hourly SMARD energy are both already reported on an hourly grid.
    return aggregate_interval_series(selected, 60, target, value_kind="price")


def load_spanish_prices(root: Path, target: pd.DatetimeIndex, *, year: int | None = None) -> pd.Series:
    local_years = set(target.tz_convert("Europe/Madrid").year)
    if year is None:
        if len(local_years) != 1:
            raise HistoricalDataError("Spanish target must identify a single local source year.")
        year = int(next(iter(local_years)))
    if type(year) is not int or year not in (2024, 2025) or local_years != {year}:
        raise HistoricalDataError("Spanish target and explicitly selected source year disagree.")
    paths = sorted(p for p in (root / "redata/price").glob(f"spot600_{year}*.json") if not p.name.endswith(".receipt.json"))
    if len(paths) != 12:
        raise HistoricalDataError("Expected twelve archived Spanish price months.")
    times, values = [], []
    for path in paths:
        month = int(path.stem[-2:])
        start = pd.Timestamp(year=year, month=month, day=1)
        last = start + pd.offsets.MonthEnd(0)
        query = {"start_date": start.strftime("%Y-%m-%dT00:00"), "end_date": last.strftime("%Y-%m-%dT23:59"), "time_trunc": "hour"}
        payload = verified_json(path, "https://apidatos.ree.es/es/datos/mercados/precios-mercados-tiempo-real?" + urlencode(query))
        matching = [record for record in payload.get("included", []) if str(record.get("id")) == "600"]
        if len(matching) != 1:
            raise HistoricalDataError("Exactly one Spanish spot600 series is required.")
        for record in matching[0]["attributes"]["values"]:
            timestamp = record["datetime"]
            if not isinstance(timestamp, str) or not (timestamp.endswith("Z") or "+" in timestamp[10:] or "-" in timestamp[10:]):
                raise HistoricalDataError("Spanish price timestamp lacks explicit UTC offset.")
            times.append(timestamp)
            values.append(record["value"])
    series = pd.Series(values, index=pd.to_datetime(times, utc=True, format="ISO8601"), name=f"electricity_price_nominal_eur{year}_per_mwh")
    if series.index.has_duplicates or not series.index.is_monotonic_increasing:
        raise HistoricalDataError("Spanish price rows are duplicate or unordered.")
    native_minutes = set(series.index.to_series().diff().dropna().dt.total_seconds() / 60)
    if native_minutes not in ({15.0}, {60.0}):
        raise HistoricalDataError("Spanish source must have a complete native 15- or 60-minute grid.")
    return aggregate_interval_series(series, int(next(iter(native_minutes))), target, value_kind="price")


def renewable_profiles(weather: pd.DataFrame, latitude: float, longitude: float, *, assessment_year: int = 2024) -> tuple[np.ndarray, np.ndarray]:
    from calculate_renewable_yield import pv_profile_generator_tmy, wind_profile_generator_tmy
    # The UTC-aware weather index is already t+30min, the approved solar geometry.
    pv = np.asarray(pv_profile_generator_tmy(weather, latitude, longitude), dtype=float)
    wind = np.asarray(wind_profile_generator_tmy(weather, turbine_spec="V90/2000", hub_height=80, offshore=False, assessment_year=assessment_year), dtype=float)
    for name, array in (("PV", pv), ("wind", wind)):
        if array.shape != (len(weather),) or not np.isfinite(array).all() or ((array < 0) | (array > 1)).any():
            raise HistoricalDataError(f"Invalid real {name} capacity factors.")
    return pv, wind


def write_csv(frame: pd.DataFrame, path: Path, *, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"Existing output: {path}; choose a new directory or explicitly --overwrite.")
    frame.to_csv(path, index_label="timestamp", float_format="%.12g")


def prepare(design_path: Path, sources: Path, output: Path, *, generation: bool = False, overwrite: bool = False) -> dict:
    design = json.loads(design_path.read_text(encoding="utf-8"))
    validate_design(design)
    year = design["time"]["historical_year"]
    if output.resolve() == sources.resolve() or sources.resolve() in output.resolve().parents:
        raise HistoricalDataError("Prepared data must be outside the immutable source archive.")
    report_path = output / "preparation_report.json"
    if report_path.exists() and not overwrite:
        raise FileExistsError("Preparation report already exists.")
    deflators = national_hicp_deflators(sources, year)
    output.mkdir(parents=True, exist_ok=True)
    produced_files = []
    report = {"created_utc": datetime.now(timezone.utc).isoformat(), "historical_year": year,
        "source_weather_year": year, "source_market_year": year, "price_year": 2023,
        "ready_for_model": False, "step19_complete": False, "design_sha256": hashlib.sha256(design_path.read_bytes()).hexdigest(),
        "price_deflators": deflators, "sites": [], "generation": {},
        "unresolved_release_gates": ["Independent release with the separately sourced static operational and regulatory factor contracts"],
        "software": {"packages": {name: version(name) for name in ("numpy", "pandas", "pvlib", "windpowerlib")},
            "file_sha256": {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest() for name in ("prepare_eu_historical_data.py", "eu_historical_data.py", "ree_historical_data.py", "calculate_renewable_yield.py", "acquire_eu_historical_sources.py")}},
    }
    for site in design["sites"]:
        target = local_year_index(year, site["calendar_timezone"])
        weather_path = sources / f"weather/{site['site_id']}_era5_{year}_padded.json"
        from acquire_eu_historical_sources import WEATHER_FIELDS
        query = {"latitude": site["coordinate"]["latitude"], "longitude": site["coordinate"]["longitude"], "start_date": f"{year-1}-12-31", "end_date": f"{year}-12-31", "hourly": ",".join(WEATHER_FIELDS), **design["weather"]["query_options"], "temperature_unit": "celsius"}
        payload = verified_json(weather_path, "https://archive-api.open-meteo.com/v1/archive?" + urlencode(query))
        weather = adapt_open_meteo_weather(payload, target)
        pv, wind = renewable_profiles(weather, payload["latitude"], payload["longitude"], assessment_year=year)
        nominal = load_smard(sources, "price", target) if site["country_code"] == "DE" else load_spanish_prices(sources, target, year=year)
        multiplier = deflators[site["country_code"]][f"multiplier_nominal_{year}_to_real_2023"]
        prepared = pd.DataFrame({"pv_capacity_factor": pv, "wind_capacity_factor": wind,
            f"electricity_price_nominal_eur{year}_per_mwh": nominal.to_numpy(), "electricity_price_real_eur2023_per_mwh": nominal.to_numpy() * multiplier}, index=target)
        write_csv(weather, output / f"{site['site_id']}_weather_midpoints.csv", overwrite=overwrite)
        write_csv(prepared, output / f"{site['site_id']}_profiles_prices_unreleased.csv", overwrite=overwrite)
        produced_files.extend([f"{site['site_id']}_weather_midpoints.csv", f"{site['site_id']}_profiles_prices_unreleased.csv"])
        local = target.tz_convert(site["calendar_timezone"])
        report["sites"].append({"site_id": site["site_id"], "hours": len(target), "start_utc": target[0].isoformat(), "end_utc_exclusive": (target[-1] + pd.Timedelta(hours=1)).isoformat(),
            "calendar_timezone": site["calendar_timezone"], "local_month_hours": {str(m): int(sum(local.month == m)) for m in range(1, 13)},
            "pv_capacity_factor_mean": float(pv.mean()), "wind_capacity_factor_mean": float(wind.mean()), "pv_full_load_hours": float(pv.sum()), "wind_full_load_hours": float(wind.sum()),
            "nominal_price_mean_eur_per_mwh": float(nominal.mean()), "real2023_price_mean_eur_per_mwh": float((nominal * multiplier).mean()), "negative_hourly_prices": int((nominal < 0).sum()),
            "returned_weather_grid": {name: payload[name] for name in ("latitude", "longitude", "elevation")}, "requested_plant_coordinate": site["coordinate"],
            "weather_timing": "Radiation source(t+1h); instantaneous mean of source(t), source(t+1h); solar position t+30min; output hourly interval starts",
            "ready_for_model": False,
        })
    if generation:
        target = local_year_index(year, "Europe/Berlin")
        german = pd.DataFrame({name: load_smard(sources, name, target) for name in GENERATION_FILTERS})
        if not np.isfinite(german.to_numpy()).all() or (german < 0).any().any():
            raise HistoricalDataError("German generation has missing, non-finite or negative energy.")
        write_csv(german, output / "de_generation_hourly_mwh_unreleased.csv", overwrite=overwrite)
        report["generation"]["DE"] = {"hours": len(german), "unit": "MWh per hour, SMARD realized net production", "annual_mwh_by_category": german.sum().to_dict(), "storage_excluded_from_factor": ["pumped_storage_output"], "factor_ready": False}
        from ree_historical_data import parse_day, report_quality, hourly_rectangle_approximation
        frames, quality = [], []
        for day in pd.date_range(f"{year}-01-01", f"{year}-12-31", freq="D"):
            path = sources / f"ree/generation/demandaau_{day:%Y%m%d}.jsonp"
            query = {"callback": "archive", "curva": "DEMANDAAU", "fecha": day.strftime("%Y-%m-%d")}
            raw = verified_bytes(path, "https://demanda.ree.es/WSvisionaMovilesPeninsulaRest/resources/demandaGeneracionPeninsula?" + urlencode(query))
            frame = parse_day(raw.decode("utf-8"), day.strftime("%Y-%m-%d"))
            frames.append(frame)
            quality.append(report_quality(frame))
        spanish = pd.concat(frames)
        write_csv(spanish, output / "es_generation_5min_mw_unreleased.csv", overwrite=overwrite)
        hourly = hourly_rectangle_approximation(spanish)
        write_csv(hourly, output / "es_generation_hourly_rectangle_mwh_unreleased.csv", overwrite=overwrite)
        produced_files.extend(["de_generation_hourly_mwh_unreleased.csv", "es_generation_5min_mw_unreleased.csv", "es_generation_hourly_rectangle_mwh_unreleased.csv"])
        report["generation"]["ES"] = {"raw_rows": len(spanish), "hours": len(hourly), "daily_quality": quality,
            "energy_interpretation": "Five-minute instantaneous power rectangle approximation; diagnostic, not settled interval energy", "factor_ready": False,
            "source_coverage_break": "2025-12-11: provider adds estimated contribution of small self-consumption" if year == 2025 else "Not assessed for 2024; generation is outside the selected static method",
            "blackout_day": "2025-04-28" if year == 2025 else None}
    report["output_hashes"] = {name: hashlib.sha256((output / name).read_bytes()).hexdigest() for name in produced_files}
    report["existing_csvs_not_produced_by_this_run"] = sorted(p.name for p in output.glob("*.csv") if p.name not in produced_files)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ready_for_model": False, "sites": report["sites"], "generation_countries": list(report["generation"])}, ensure_ascii=False), flush=True)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--design", required=True, type=Path)
    parser.add_argument("--sources", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--generation", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    prepare(args.design, args.sources, args.output, generation=args.generation, overwrite=args.overwrite)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
