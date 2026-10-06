"""Prescribed local-time EU demand profiles with one fixed annual H2 volume."""
from __future__ import annotations

from numbers import Real
import numpy as np
import pandas as pd

ANNUAL_H2_KG = 3_650_000.0
PROFILES = ("D0", "D1", "D2")


def demand_profile(index: pd.DatetimeIndex, *, profile: str, timezone: str,
                   historical_year: int, annual_kg: float = ANNUAL_H2_KG) -> tuple[pd.Series, dict]:
    """Return kg per actual hourly interval, retaining DST and leap-day hours.

    D0: every hour. D1:08:00≤local hour<20:00 daily. D2: same window Mon-Fri.
    These are controlled comparison assumptions, not measured refinery demand.
    """
    if profile not in PROFILES:
        raise ValueError("Demand profile must be D0,D1 orD2")
    if isinstance(historical_year, bool) or historical_year not in (2024, 2025):
        raise ValueError("Historical demand calendar must be2024 or2025")
    if isinstance(annual_kg, bool) or not isinstance(annual_kg, Real) or not np.isfinite(annual_kg) or annual_kg <= 0:
        raise ValueError("Prescribed annual H2 volume must be finite and positive")
    if not isinstance(index, pd.DatetimeIndex) or index.tz is None:
        raise ValueError("Demand profile requires timezone-aware UTC intervals")
    start = pd.Timestamp(year=historical_year, month=1, day=1, tz=timezone).tz_convert("UTC")
    end = pd.Timestamp(year=historical_year + 1, month=1, day=1, tz=timezone).tz_convert("UTC")
    expected = pd.date_range(start, end, freq="h", inclusive="left")
    if not index.tz_convert("UTC").equals(expected):
        raise ValueError("Demand timestamps must equal the complete declared local-year UTC axis")
    local = index.tz_convert(timezone)
    weights = np.ones(len(index), dtype=float)
    if profile != "D0":
        weights = ((local.hour >= 8) & (local.hour < 20)).astype(float)
    if profile == "D2":
        weights *= (local.dayofweek < 5).astype(float)
    active_hours = int(weights.sum())
    if active_hours == 0:
        raise ValueError("Demand profile has no active delivery hours")
    values = annual_kg * weights / active_hours
    data = pd.Series(values, index=index, name="h2_demand")
    metadata = {
        "profile": profile, "historical_year": historical_year,
        "calendar_timezone": timezone, "annual_kg": float(annual_kg),
        "actual_calendar_hours": len(index), "active_delivery_hours": active_hours,
        "kg_per_active_hour": float(annual_kg / active_hours),
        "zero_demand_hours": int((values == 0).sum()),
        "normalization": "annual_kg*weight_t/sum(weight)",
        "synthetic_prescribed_comparison": True, "holiday_adjustment": False,
        "interval_unit": "kg/h", "demand_optimized_or_shiftable": False,
    }
    return data, metadata
