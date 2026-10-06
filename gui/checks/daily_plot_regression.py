"""Local saved-day accounting, DST boundaries and the hourly start timezone."""
import io
import subprocess

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal
import pytest

from gui import plotting
from gui.result_loader import ResultBundle


def hour_frame(timestamps,*,factor=1.):
    count=len(timestamps)
    pv=np.arange(1,count+1,dtype=float)*factor
    wind=np.ones(count)*2*factor
    grid=np.ones(count)*3*factor
    return pd.DataFrame({"timestamp":timestamps,"pv_self_consumption_mwh":pv,
        "wind_self_consumption_mwh":wind,"grid_import_mwh":grid,
        "pv_generation_mwh":pv*2,"wind_generation_mwh":wind*3,
        "rf_nbo_electricity_mwh":pv+wind+grid,"h2_production_kg":np.ones(count)*10,
        "h2_demand_kg":np.ones(count)*10,"h2_storage_level_kg":np.arange(count,dtype=float)})


def local_bundle(day="2024-02-10",timezone="Europe/Berlin"):
    date=pd.Timestamp(day)
    start=date.tz_localize(timezone)
    end=(date+pd.DateOffset(days=1)).tz_localize(timezone)
    times=pd.date_range(start.tz_convert("UTC"),end.tz_convert("UTC"),freq="h",inclusive="left")
    return ResultBundle(pd.DataFrame({"scenario_id":["S0","S1"],"lcoh_eur_per_kg_h2":[4.,5.]}),{},
        hourly={"S0":hour_frame(times),"S1":hour_frame(times,factor=10.)})


@pytest.fixture(autouse=True)
def no_optimization_or_process(monkeypatch):
    def forbidden(*args,**kwargs):pytest.fail("Drawing saved hourly data must not start a process")
    monkeypatch.setattr(subprocess,"run",forbidden)
    monkeypatch.setattr(subprocess,"Popen",forbidden)
    yield
    plt.close("all")


@pytest.mark.parametrize("day,timezone,hours",[
    ("2024-02-10","Europe/Berlin",24),
    ("2024-03-31","Europe/Berlin",23),
    ("2024-10-27","Europe/Madrid",25),
    ("2024-02-29","UTC",24),
])
def test_complete_local_day_has_exact_utc_intervals_and_saved_energy_totals(day,timezone,hours):
    bundle=local_bundle(day,timezone);original=bundle.hourly["S0"].copy(deep=True)
    frame=plotting.daily_electricity_frame(bundle,day=day,scenario_id="S0",timezone=timezone)
    assert len(frame)==hours
    assert frame.display_timestamp.iloc[0].hour==0
    assert frame.display_interval_end.iloc[-1].hour==0
    assert frame.display_interval_end.iloc[-1].date()==(pd.Timestamp(day)+pd.DateOffset(days=1)).date()
    assert (frame.display_interval_end-frame.display_timestamp).eq(pd.Timedelta(hours=1)).all()
    assert frame.cumulative_pv_mwh.iloc[-1]==original.pv_self_consumption_mwh.sum()
    assert frame.cumulative_wind_mwh.iloc[-1]==original.wind_self_consumption_mwh.sum()
    assert frame.cumulative_grid_mwh.iloc[-1]==original.grid_import_mwh.sum()
    assert frame.cumulative_total_mwh.iloc[-1]==original.rf_nbo_electricity_mwh.sum()
    assert frame.selection_day_hours.eq(hours).all() and frame.selection_day_complete.all()
    assert frame.attrs["complete"] is True
    assert_frame_equal(bundle.hourly["S0"],original)
    assert frame.timestamp.tolist()==original.timestamp.tolist()


@pytest.mark.parametrize("day",["2024-03-31","2024-10-27"])
def test_cumulative_lines_begin_at_zero_and_end_at_true_local_midnight(day):
    bundle=local_bundle(day);frame=plotting.daily_electricity_frame(bundle,day=day,scenario_id="S0",timezone="Europe/Berlin")
    fig=plotting.daily_electricity_figure(frame,mode="Kumulative Tagesenergie",timezone="Europe/Berlin")
    ax=fig.axes[0]
    assert len(fig.axes)==1 and len(ax.lines)==4
    for line,column in zip(ax.lines,("cumulative_pv_mwh","cumulative_wind_mwh","cumulative_grid_mwh","cumulative_total_mwh")):
        assert line.get_ydata()[0]==0.
        assert line.get_ydata()[-1]==frame[column].iloc[-1]
        assert len(line.get_xdata())==len(frame)+1
        assert pd.Timestamp(line.get_xdata()[0])==frame.display_timestamp.iloc[0]
        assert pd.Timestamp(line.get_xdata()[-1])==frame.display_interval_end.iloc[-1]
    assert ax.get_ylabel()=="Kumulierte Tagesenergie [MWh]"
    if day=="2024-10-27":
        labels=[label.get_text() for label in ax.get_xticklabels()]
        assert "02:00\nCEST" in labels and "02:00\nCET" in labels
    fig.canvas.draw()


@pytest.mark.parametrize("mode",plotting.DAILY_ELECTRICITY_MODES)
def test_generation_basis_uses_native_generation_and_never_a_demand_total(mode):
    bundle=local_bundle();frame=plotting.daily_electricity_frame(bundle,day="2024-02-10",scenario_id="S1",timezone="Europe/Berlin",basis="Erzeugung und Netzbezug")
    native=bundle.hourly["S1"]
    assert frame.selected_pv_mwh.tolist()==native.pv_generation_mwh.tolist()
    assert frame.selected_wind_mwh.tolist()==native.wind_generation_mwh.tolist()
    assert frame.selected_grid_mwh.tolist()==native.grid_import_mwh.tolist()
    assert frame.cumulative_pv_mwh.iloc[-1]==native.pv_generation_mwh.sum()
    assert "cumulative_total_mwh" not in frame
    assert frame.attrs["basis"]=="Erzeugung und Netzbezug"
    figure=plotting.daily_electricity_figure(frame,mode=mode,timezone="Europe/Berlin")
    labels=[line.get_label() for line in figure.axes[0].lines]
    assert labels==["PV-Erzeugung","Winderzeugung","Netzimport"]
    assert "keine Strombedarfsbilanz" in "\n".join(text.get_text() for text in figure.texts)


def test_hourly_direct_supply_is_stacked_and_keeps_native_demand_line():
    bundle=local_bundle();frame=plotting.daily_electricity_frame(bundle,day="2024-02-10",scenario_id="reference",timezone="Europe/Berlin")
    assert frame.selection_scenario_id.eq("S0").all()
    figure=plotting.daily_electricity_figure(frame,timezone="Europe/Berlin")
    ax=figure.axes[0]
    assert len(figure.axes)==1 and len(ax.collections)==3
    assert len(ax.lines)==1 and ax.lines[0].get_label()=="Strombedarf"
    assert list(ax.lines[0].get_ydata()[:-1])==frame.rf_nbo_electricity_mwh.tolist()
    assert ax.get_ylabel()=="Stündliche Strommenge [MWh]"
    assert list(ax.lines[0].get_xdata())[-1]==frame.display_interval_end.iloc[-1]


def test_explicit_scenario_selection_does_not_take_first_saved_scenario():
    bundle=local_bundle();frame=plotting.daily_electricity_frame(bundle,day="2024-02-10",scenario_id="red_monthly",timezone="Europe/Berlin")
    assert frame.selected_pv_mwh.tolist()==bundle.hourly["S1"].pv_self_consumption_mwh.tolist()
    assert frame.selection_scenario_id.eq("S1").all()
    with pytest.raises(ValueError,match="eindeutigen"):
        plotting.daily_electricity_frame(bundle,day="2024-02-10",scenario_id="S2",timezone="Europe/Berlin")
    bundle.hourly["red_monthly"]=bundle.hourly["S1"].copy()
    with pytest.raises(ValueError,match="eindeutigen"):
        plotting.daily_electricity_frame(bundle,day="2024-02-10",scenario_id="S1",timezone="Europe/Berlin")


@pytest.mark.parametrize("missing",[0,7,23])
def test_partial_day_or_internal_gap_is_never_labelled_complete(missing):
    bundle=local_bundle();bundle.hourly["S0"]=bundle.hourly["S0"].drop(index=missing)
    with pytest.raises(ValueError,match="23 von 24.*unvollständig"):
        plotting.daily_electricity_frame(bundle,day="2024-02-10",scenario_id="S0",timezone="Europe/Berlin")


def test_partial_calendar_year_edge_requires_a_complete_available_day():
    times=pd.date_range("2024-01-01T00:00:00Z",periods=48,freq="h")
    bundle=ResultBundle(pd.DataFrame({"scenario_id":["S0"]}),{},hourly={"S0":hour_frame(times)})
    with pytest.raises(ValueError,match="23 von 24.*unvollständig"):
        plotting.daily_electricity_frame(bundle,day="2024-01-01",scenario_id="S0",timezone="Europe/Berlin")
    complete=plotting.daily_electricity_frame(bundle,day="2024-01-02",scenario_id="S0",timezone="Europe/Berlin")
    assert len(complete)==24
    assert complete.timestamp.iloc[0]==pd.Timestamp("2024-01-01T23:00:00Z")


def test_repeated_local_fall_hour_is_not_deduplicated_as_a_wall_clock_string():
    frame=plotting.daily_electricity_frame(local_bundle("2024-10-27"),day="2024-10-27",scenario_id="S0",timezone="Europe/Berlin")
    repeated=frame[frame.display_timestamp.dt.hour.eq(2)]
    assert len(repeated)==2
    assert repeated.display_timestamp.dt.strftime("%z").tolist()==["+0200","+0100"]
    assert not frame.timestamp.duplicated().any()
    assert frame.cumulative_pv_mwh.iloc[-1]==sum(range(1,26))


def test_export_keeps_selection_stamp_native_hourly_values_and_interval_end_sums():
    frame=plotting.daily_electricity_frame(local_bundle("2024-10-27"),day="2024-10-27",scenario_id="S0",timezone="Europe/Berlin")
    exported=pd.read_csv(io.StringIO(frame.to_csv(index=False)))
    assert len(exported)==25
    assert exported.selection_day.eq("2024-10-27").all()
    assert exported.selection_timezone.eq("Europe/Berlin").all()
    assert exported.selection_basis.eq("Direktversorgung").all()
    assert exported.selection_day_complete.all()
    assert pd.to_datetime(exported.timestamp,utc=True,format="mixed").tolist()==frame.timestamp.tolist()
    assert exported.cumulative_pv_mwh.iloc[-1]==exported.pv_self_consumption_mwh.sum()
    # Rendering the exact exported values must not depend on DataFrame attrs.
    figure=plotting.daily_electricity_figure(exported,mode="Kumulative Tagesenergie",timezone="Europe/Berlin")
    assert len(figure.axes)==1


@pytest.mark.parametrize("bad",["duplicate","unsorted","nan"])
def test_native_hourly_axis_and_finite_flow_values_are_required(bad):
    bundle=local_bundle();frame=bundle.hourly["S0"]
    if bad=="duplicate":bundle.hourly["S0"]=pd.concat([frame.iloc[[0]],frame],ignore_index=True)
    elif bad=="unsorted":bundle.hourly["S0"]=frame.iloc[::-1]
    else:bundle.hourly["S0"].loc[0,"grid_import_mwh"]=np.nan
    with pytest.raises(ValueError):
        plotting.daily_electricity_frame(bundle,day="2024-02-10",scenario_id="S0",timezone="Europe/Berlin")


def test_chart_rejects_changed_cumulative_values_partial_data_and_wrong_timezone():
    frame=plotting.daily_electricity_frame(local_bundle(),day="2024-02-10",scenario_id="S0",timezone="Europe/Berlin")
    altered=frame.copy();altered.loc[10,"cumulative_pv_mwh"]+=1.
    with pytest.raises(ValueError,match="stimmt nicht"):
        plotting.daily_electricity_figure(altered,mode="Kumulative Tagesenergie",timezone="Europe/Berlin")
    with pytest.raises(ValueError,match="vollständigen lokalen Tages"):
        plotting.daily_electricity_figure(frame.iloc[:-1],timezone="Europe/Berlin")
    with pytest.raises(ValueError,match="Grafikzeitzone"):
        plotting.daily_electricity_figure(frame,timezone="UTC")


@pytest.mark.parametrize("start",["2024-07-01 00:00","2024-06-30T22:00:00Z","2024-07-01T00:00:00+02:00"])
def test_hourly_start_naive_is_local_and_aware_remains_an_absolute_instant(start):
    times=pd.date_range("2024-06-30T21:00:00Z",periods=8,freq="h")
    bundle=ResultBundle(pd.DataFrame({"scenario_id":["S0"]}),{},hourly={"S0":hour_frame(times)})
    figure=plotting.hourly_figure(bundle,start=start,hours=2,timezone="Europe/Berlin")
    production_line=figure.axes[1].lines[0]
    chosen=pd.Timestamp(production_line.get_xdata()[0])
    assert chosen.hour==0 and chosen.tz_convert("UTC")==pd.Timestamp("2024-06-30T22:00:00Z")
    assert len(production_line.get_xdata())==3  # two hourly intervals and their final boundary


@pytest.mark.parametrize("start,match",[("2024-03-31 02:30","existiert"),("2024-10-27 02:30","mehrdeutig")])
def test_hourly_naive_start_at_dst_transition_has_a_clear_error(start,match):
    bundle=local_bundle(start[:10])
    with pytest.raises(ValueError,match=match):
        plotting.hourly_figure(bundle,start=start,hours=2,timezone="Europe/Berlin")


def test_aware_repeated_fall_hour_selects_the_requested_dst_occurrence():
    bundle=local_bundle("2024-10-27")
    first=plotting.hourly_figure(bundle,start="2024-10-27T02:00:00+02:00",hours=1,timezone="Europe/Berlin")
    second=plotting.hourly_figure(bundle,start="2024-10-27T02:00:00+01:00",hours=1,timezone="Europe/Berlin")
    a=pd.Timestamp(first.axes[1].lines[0].get_xdata()[0]).tz_convert("UTC")
    b=pd.Timestamp(second.axes[1].lines[0].get_xdata()[0]).tz_convert("UTC")
    assert b-a==pd.Timedelta(hours=1)


def test_optional_total_can_be_hidden_and_zero_day_still_exports_and_renders():
    bundle=local_bundle()
    for field in ("pv_self_consumption_mwh","wind_self_consumption_mwh","grid_import_mwh","rf_nbo_electricity_mwh"):
        bundle.hourly["S0"][field]=0.
    frame=plotting.daily_electricity_frame(bundle,day="2024-02-10",scenario_id="S0",timezone="Europe/Berlin")
    figure=plotting.daily_electricity_figure(frame,mode="Kumulative Tagesenergie",timezone="Europe/Berlin",include_total=False)
    assert len(figure.axes[0].lines)==3
    assert all(np.equal(line.get_ydata(),0.).all() for line in figure.axes[0].lines)
    buffer=io.BytesIO();figure.savefig(buffer,format="png")
    assert buffer.getvalue().startswith(b"\x89PNG")
