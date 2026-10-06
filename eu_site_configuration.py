"""Explicit EU site and real-WACC selection for the historical study.

Importing this module performs no file I/O and does not change legacy defaults.
The selected design is read only when ``load_eu_site_configuration`` is called.
Country/technology benchmarks refer to 2021; they are already real after-tax
rates. The fixed H2 premium is a modelling assumption, not a financing quote.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import calendar
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
import json
from math import isclose, isfinite
from pathlib import Path
from typing import Any, Final
from zoneinfo import ZoneInfo

from config_h2 import ModelConfig, ScalarParameter, SiteConfig, default_model_config

EU_SITE_IDS: Final[tuple[str, ...]] = ("hamburg_moorburg", "huelva_la_rabida")
DEFAULT_EU_DESIGN_PATH: Final[Path] = Path(__file__).resolve().parent / "input_data" / "h2_eu_case_studies.json"
_COMPONENTS: Final[tuple[str, ...]] = ("pv", "wind_onshore", "electrolyzer", "compressor", "h2_storage")
_APPROVED: Final[dict[str, tuple[str,str,float,float]]] = {
    "hamburg_moorburg": ("DE", "Europe/Berlin", .013, .013),
    "huelva_la_rabida": ("ES", "Europe/Madrid", .036, .031),
}
_FINANCING_BENCHMARKS = {
    2021: {"publication_year": 2023, "DE": (.013, .013), "ES": (.036, .031),
           "title": "IRENA Cost of financing renewable power, Appendix 2023, Figure A1 (2021)"},
}


@dataclass(frozen=True, slots=True)
class EuSiteConfiguration:
    """Selected immutable model/site configuration and its source metadata."""

    config: ModelConfig
    site: SiteConfig
    site_id: str
    calendar_timezone: str
    metadata: dict[str, Any]


def _number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int,float)) or not isfinite(value):
        raise ValueError(f"{name} requires a finite numeric value.")
    return float(value)


def _require(mapping: dict, key: str, expected: object, prefix: str) -> None:
    actual=mapping.get(key)
    wrong_type=(isinstance(expected,bool) and type(actual) is not bool) or (isinstance(expected,int) and not isinstance(expected,bool) and type(actual) is not int)
    if actual != expected or wrong_type:
        raise ValueError(f"{prefix}.{key} must be {expected!r}; got {actual!r}.")


def load_eu_site_configuration(
    site_id: str,
    *,
    base_config: ModelConfig | None = None,
    design_path: str | Path | None = None,
) -> EuSiteConfiguration:
    """Apply the approved site WACC and historical-year metadata to a copy.

    The existing scenario, demand, costs, lifetimes and technical parameters
    remain those of ``base_config`` (or the literature default). This function
    validates the selected design convention, not the contents of a hourly
    CSV. Runners must independently verify a CSV and its source contract.
    """
    if not isinstance(site_id,str) or site_id not in EU_SITE_IDS:
        raise ValueError(f"Unknown EU site {site_id!r}; choose one of {EU_SITE_IDS}.")
    path=Path(design_path) if design_path is not None else DEFAULT_EU_DESIGN_PATH
    raw=path.read_bytes()
    design=json.loads(raw.decode("utf-8-sig"))
    if not isinstance(design,dict):
        raise ValueError("EU design must be a JSON object.")
    records=design.get("sites")
    if not isinstance(records,list):
        raise ValueError("EU design requires a sites list.")
    if any(not isinstance(s,dict) for s in records):
        raise ValueError("Every EU site must be an object.")
    selected=[s for s in records if s.get("site_id")==site_id]
    if len(selected)!=1:
        raise ValueError(f"EU design must contain exactly one {site_id} record.")
    row=selected[0]
    country,zone,pv_rate,wind_rate=_APPROVED[site_id]
    _require(row,"country_code",country,site_id)
    _require(row,"calendar_timezone",zone,site_id)
    _require(row,"bidding_zone","DE_LU" if country=="DE" else "ES",site_id)

    financing=design.get("financing")
    time=design.get("time")
    weather=design.get("weather")
    sources=design.get("sources")
    if not all(isinstance(x,dict) for x in [financing,time,weather,sources]):
        raise ValueError("EU design requires financing, time, weather and sources objects.")
    financing_year=financing.get("reference_year")
    if type(financing_year) is not int or financing_year not in _FINANCING_BENCHMARKS:
        raise ValueError("financing.reference_year requires independently reviewed real after-tax benchmarks.")
    benchmark=_FINANCING_BENCHMARKS[financing_year]
    publication_year=benchmark["publication_year"]
    pv_rate,wind_rate=benchmark[country]
    for key,expected in {
        "rate_type":"real after-tax annual discount-rate proxy", "reference_year":financing_year,
        "appendix_publication_year":publication_year,
        "cost_price_year":2023, "no_inflation_conversion":True,
        "rates_vary_hourly":False, "H2_premium_fraction":.02,
        "mean_convention":"Unweighted and fixed before optimization",
    }.items():
        _require(financing,key,expected,"financing")
    year=time.get("historical_year")
    if type(year) is not int or year not in (2024,2025):
        raise ValueError("time.historical_year must be an approved 2024 or archived 2025 calendar year.")
    annual_hours=24*(366 if calendar.isleap(year) else 365)
    start=datetime(year,1,1,tzinfo=ZoneInfo(zone)).astimezone(timezone.utc).isoformat().replace("+00:00","Z")
    end=datetime(year+1,1,1,tzinfo=ZoneInfo(zone)).astimezone(timezone.utc).isoformat().replace("+00:00","Z")
    for key,expected in {
        "historical_year":year,"source_weather_year":year,"source_market_year":year,
        "expected_hours":annual_hours,"resolution_hours":1,"storage_timezone":"UTC",
        "interval_semantics":"start, [t,t+1h)",
        "start_utc_inclusive":start,
        "end_utc_exclusive":end,
        "year_basis":"local calendar year at each site",
        "reject_positional_year_remapping":True,
        "monthly_grouping":"site local timezone",
    }.items():
        _require(time,key,expected,"time")
    if "annualization_basis" in time:
        _require(time,"annualization_basis","historical_calendar_year","time")
    annual_demand=_number(design.get("hydrogen_demand",{}).get("annual_kg"),"hydrogen_demand.annual_kg")
    if annual_demand != 3_650_000.0:
        raise ValueError("hydrogen_demand.annual_kg must retain the approved fixed 3650000 kg yearly delivery.")
    _require(weather,"provider","Open-Meteo Historical Weather API","weather")
    _require(weather,"underlying_dataset","ECMWF ERA5","weather")
    for key in ["WACC","hydrogen_risk_premium","weather_api","weather_underlying"]:
        if not isinstance(sources.get(key),str) or not sources[key].strip():
            raise ValueError(f"sources.{key} must identify its source.")

    stored_rates=row.get("real_wacc_fraction_per_year")
    if not isinstance(stored_rates,dict) or set(stored_rates)!=set(_COMPONENTS):
        raise ValueError(f"{site_id} requires exactly the five component WACC values.")
    h2_rate=float((Decimal(str(pv_rate))+Decimal(str(wind_rate)))/2+Decimal("0.02"))
    approved_rates={"pv":pv_rate,"wind_onshore":wind_rate,
                    "electrolyzer":h2_rate,"compressor":h2_rate,"h2_storage":h2_rate}
    for name,expected in approved_rates.items():
        actual=_number(stored_rates[name],f"{site_id}.WACC.{name}")
        if not 0 <= actual < 1 or not isclose(actual,expected,rel_tol=0,abs_tol=1e-12):
            raise ValueError(f"{site_id}.WACC.{name} contradicts the approved real benchmark/H2 rule.")

    coordinates=row.get("coordinate")
    if not isinstance(coordinates,dict) or coordinates.get("crs")!="EPSG:4326":
        raise ValueError(f"{site_id} requires EPSG:4326 site coordinates.")
    label=row.get("label")
    if not isinstance(label,str) or not label.strip():
        raise ValueError(f"{site_id} requires a nonempty site label.")
    site=SiteConfig(_number(coordinates.get("latitude"),"latitude"),
                    _number(coordinates.get("longitude"),"longitude"),label,country,row["bidding_zone"])
    site.validate()
    base=default_model_config() if base_config is None else base_config
    if not isinstance(base,ModelConfig):
        raise TypeError("base_config must be a ModelConfig.")
    base.validate()
    technology=base.technologies
    replacements={}
    for name,rate in approved_rates.items():
        note=(f"Historical {financing_year} {country} real after-tax benchmark; effective capital-recovery proxy. "
              "No further inflation adjustment, tax shield or WACC gross-up.")
        source=f"{benchmark['title']}; {sources['WACC']}"
        if name in ("electrolyzer","compressor","h2_storage"):
            source+=f"; Brandt et al. 2024 Supplementary Tables 2-4; {sources['hydrogen_risk_premium']}"
            note+=" H2 rate = unweighted PV/wind mean + 0.02, fixed before optimization; modelling assumption."
        replacements[name]=replace(getattr(technology,name),real_wacc_fraction=ScalarParameter(rate,"fraction",source,financing_year,note))
    updated_technology=replace(technology,**replacements)
    weather_source=f"Historical {year} ECMWF ERA5 processed through Open-Meteo; {sources['weather_api']}; {sources['weather_underlying']}"
    year_param=ScalarParameter(float(year),"calendar_year",weather_source,year,
                               "Historical local calendar year; not TMY and no positional year remapping. Hourly source contract validated separately.")
    daily_demand=annual_demand/(annual_hours/24)
    demand_parameter=(base.study.h2_demand_kg_per_day if base.study.h2_demand_kg_per_day.value == daily_demand
                      else ScalarParameter(daily_demand,"kg_H2/day","Fixed prescribed annual delivery from approved EU design",year,
                                           "Calendar-average rate; annual delivery stays 3650000 kg in either year."))
    study=replace(base.study,weather_start_year=year_param,weather_end_year=year_param,profile_calendar_year=year_param,
                  number_of_time_steps=ScalarParameter(float(annual_hours),"time_steps/year",weather_source,year,"Complete local calendar year, including every leap-day hour; hourly UTC interval starts."),
                  annual_hours=ScalarParameter(float(annual_hours),"h/year","Explicit historical calendar year; Gregorian leap-year rule",year),
                  annualization_basis="historical_calendar_year",
                  temporal_correlation_timezone=zone,
                  h2_demand_kg_per_day=demand_parameter)
    config=replace(base,technologies=updated_technology,study=study)
    config.validate()
    metadata={
        "schema_version":"1.1","site_id":site_id,"country_code":country,"calendar_timezone":zone,
        "design_path":str(path.resolve()),"design_sha256":sha256(raw).hexdigest(),
        "historical_year":year,"source_weather_year":year,"source_market_year":year,
        "annualization":{"basis":"historical_calendar_year","annual_hours":annual_hours,"annual_h2_delivery_kg":annual_demand},
        "temporal_correlation":{"monthly_basis":"site_local_timezone","timezone":zone,"hourly_basis":"physical_utc_hour"},
        "time_contract":dict(time),"coordinate":dict(coordinates),
        "wacc":{"rate_type":"real after-tax annual discount-rate proxy","reference_year":financing_year,
                "appendix_publication_year":publication_year,"real_wacc_fraction_per_year":approved_rates,
                "H2_rule":"(country_PV_real_WACC+country_onshore_wind_real_WACC)/2+0.02",
                "H2_premium_fraction":.02,"mean_convention":"Unweighted and fixed before optimization",
                "no_additional_inflation_conversion":True,"no_second_tax_shield":True,
                "cost_price_year":2023,"rates_invariant_across_scenarios":True,
                "tax_scope":financing.get("tax_scope"),"interpretation":financing.get("interpretation"),
                "sources":{"WACC":sources['WACC'],"hydrogen_risk_premium":sources['hydrogen_risk_premium']}},
        "weather_sources":{"weather_api":sources['weather_api'],"weather_underlying":sources['weather_underlying']},
        "hourly_input_verified_by_this_function":False,
    }
    return EuSiteConfiguration(config,site,site_id,zone,metadata)


__all__=["EU_SITE_IDS","DEFAULT_EU_DESIGN_PATH","EuSiteConfiguration","load_eu_site_configuration"]
