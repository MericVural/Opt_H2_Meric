"""Explicit archived 2021 finance fixtures isolate calendar tests from defaults."""
import json
from pathlib import Path

def write_calendar_design(source: Path, destination: Path, year: int) -> Path:
    design=json.loads(source.read_text(encoding="utf-8-sig"))
    hours=8784 if year==2024 else 8760
    design["time"].update(historical_year=year,source_weather_year=year,source_market_year=year,
        expected_hours=hours,start_utc_inclusive=f"{year-1}-12-31T23:00:00Z",
        end_utc_exclusive=f"{year}-12-31T23:00:00Z",annualization_basis="historical_calendar_year")
    design["hydrogen_demand"]["annual_kg"]=3650000
    design["financing"].update(reference_year=2021,appendix_publication_year=2023)
    design["sources"]["WACC"]="https://www.irena.org/Publications/2023/May/The-cost-of-financing-for-renewable-power"
    for row in design["sites"]:
        rates=(.013,.013,.033) if row["country_code"]=="DE" else (.036,.031,.0535)
        row["real_wacc_fraction_per_year"]={"pv":rates[0],"wind_onshore":rates[1],
            "electrolyzer":rates[2],"compressor":rates[2],"h2_storage":rates[2]}
    destination.write_text(json.dumps(design),encoding="utf-8")
    return destination
