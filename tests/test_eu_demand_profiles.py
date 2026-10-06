"""Real calendar, DST and volume checks for prescribed delivery profiles."""
import numpy as np
import pandas as pd
import pytest

from eu_demand_profiles import ANNUAL_H2_KG, demand_profile


def axis(year, timezone):
    start = pd.Timestamp(year=year, month=1, day=1, tz=timezone).tz_convert("UTC")
    end = pd.Timestamp(year=year + 1, month=1, day=1, tz=timezone).tz_convert("UTC")
    return pd.date_range(start, end, freq="h", inclusive="left")


@pytest.mark.parametrize("timezone", ["Europe/Berlin", "Europe/Madrid"])
@pytest.mark.parametrize("year,counts", [(2024, {"D0":8784,"D1":4392,"D2":3144}), (2025, {"D0":8760,"D1":4380,"D2":3132})])
@pytest.mark.parametrize("profile", ["D0", "D1", "D2"])
def test_actual_calendar_profiles_equal_fixed_annual_volume(timezone, year, counts, profile):
    index = axis(year, timezone)
    data, meta = demand_profile(index, profile=profile, timezone=timezone, historical_year=year)
    assert data.sum() == pytest.approx(ANNUAL_H2_KG)
    assert (data > 0).sum() == counts[profile]
    assert meta["active_delivery_hours"] == counts[profile]
    assert meta["actual_calendar_hours"] == len(index)
    local = data.index.tz_convert(timezone)
    if profile != "D0":
        assert data[(local.hour < 8) | (local.hour >= 20)].eq(0).all()
    if profile == "D2":
        assert data[local.dayofweek >= 5].eq(0).all()


@pytest.mark.parametrize("timezone", ["Europe/Berlin", "Europe/Madrid"])
def test_leap_day_and_dst_utc_hours_preserved(timezone):
    index = axis(2024, timezone)
    d0, _ = demand_profile(index, profile="D0", timezone=timezone, historical_year=2024)
    d2, _ = demand_profile(index, profile="D2", timezone=timezone, historical_year=2024)
    local = index.tz_convert(timezone)
    leap = (local.month == 2) & (local.day == 29)
    spring = (local.month == 3) & (local.day == 31)
    autumn = (local.month == 10) & (local.day == 27)
    assert leap.sum() == 24
    assert (d2[leap] > 0).sum() == 12
    assert spring.sum() == 23 and autumn.sum() == 25
    assert d0[spring].gt(0).all() and d0[autumn].gt(0).all()
    repeated = local[autumn].hour == 2
    assert repeated.sum() == 2
    assert index.is_unique
    assert d0.iloc[0] == pytest.approx(3650000 / 8784)


@pytest.mark.parametrize("bad_volume", [0, -1, np.nan, np.inf, True])
def test_invalid_volume_rejected(bad_volume):
    with pytest.raises(ValueError):
        demand_profile(axis(2024,"Europe/Berlin"), profile="D0", timezone="Europe/Berlin", historical_year=2024, annual_kg=bad_volume)


@pytest.mark.parametrize("defect", ["gap", "duplicate", "wrong_year", "naive"])
def test_noncanonical_calendar_cannot_be_relabelled(defect):
    index = axis(2024,"Europe/Madrid")
    if defect == "gap":
        index = index.delete(1416)
    elif defect == "duplicate":
        index = index.insert(50,index[49])
    elif defect == "wrong_year":
        index = axis(2025,"Europe/Madrid")
    else:
        index = index.tz_localize(None)
    with pytest.raises(ValueError):
        demand_profile(index, profile="D2", timezone="Europe/Madrid", historical_year=2024)
