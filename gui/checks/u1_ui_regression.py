"""Scientific selection/export safeguards through the actual Streamlit UI."""
import io

import pandas as pd

from gui.checks.ux_regression import harness, widget, run, page, saved, set_multi, IDENTITY
from gui import plotting


def test_empty_graph_selection_invalidates_previous_picture_and_csv(harness):
    at=harness.at
    saved(at)
    assert at.session_state['last_figure_export']['png'].startswith(b'\x89PNG')
    set_multi(at,IDENTITY+':result:cases',[])
    assert 'last_figure_export' not in at.session_state
    assert 'last_chart_data' not in at.session_state
    page(at,'Export')
    assert not [item for item in at.get('download_button') if item.key=='export_figure_data']
    assert not harness.submitted


def test_graph_export_retains_its_cases_and_is_hidden_at_other_site(harness):
    at=harness.at
    saved(at)
    record=at.session_state['last_figure_export']
    csv=pd.read_csv(io.BytesIO(at.session_state['last_chart_data']))
    assert record['scope']['site_id']=='hamburg_moorburg'
    assert {item['__result_directory'] for item in record['context']}==set(csv['__result_directory'])
    assert csv['__plot_label'].eq(record['label']).all()
    # This harness uses a figure stub; real axis metadata is checked separately.
    assert '__plot_y_labels' in csv
    page(at,'Export')
    widget(at,'selectbox','site:eu_2024').set_value('andalusia_huelva')
    run(at)
    assert 'last_figure_export' not in at.session_state
    assert not harness.calls and not harness.submitted


def test_export_preserves_transformed_axis_unit_and_operation(harness):
    import json
    import matplotlib.pyplot as plt
    import streamlit as st
    from gui import app
    frame=pd.DataFrame({'__plot_x':[50.,100.,150.], 'objective_eur_per_year':[50.,100.,150.]})
    frame.attrs.update(xlabel='H₂-Jahresnachfrage [% der Basis]',operation='multiply_hourly_h2_demand',
                       note='Gleicher Profilverlauf und unveränderte Modellannahmen.',oat_parameter='h2_demand_multiplier')
    fig,axis=plt.subplots();axis.plot(frame.__plot_x,frame.objective_eur_per_year)
    axis.set_xlabel(frame.attrs['xlabel']);axis.set_ylabel('Jahreskosten [EUR/a]')
    try:
        app.remember_figure(fig,frame,'Nachfrage')
        exported=pd.read_csv(io.BytesIO(st.session_state['last_chart_data']))
        assert exported.__plot_x.tolist()==[50.,100.,150.]
        assert exported.__plot_x_label.eq(frame.attrs['xlabel']).all()
        assert exported.__plot_operation.eq(frame.attrs['operation']).all()
        assert exported.__plot_note.eq(frame.attrs['note']).all()
        assert json.loads(exported.__plot_y_labels.iloc[0])==['Jahreskosten [EUR/a]']
    finally:
        plt.close(fig)
        app.clear_chart_export()


def test_cost_components_do_not_offer_ineffective_metric_selection(harness):
    at=harness.at
    saved(at)
    widget(at,'selectbox',IDENTITY+':result:chart_type').set_value('Gestapelte Kosten')
    run(at)
    assert not [item for item in at.selectbox if item.key==IDENTITY+':result:metric']
    assert any('Kostenbestandteile' in item.value for item in at.caption)
    assert not harness.submitted


def test_diagnostic_and_reference_metrics_leave_native_tables_accessible(harness):
    frame=harness.state['frame']
    frame['red_iii_maximum_product_intensity_kg_co2e_per_kg_h2']=3.384
    frame['max_electricity_balance_residual_mwh']=1e-9
    at=harness.at
    saved(at)
    field=widget(at,'selectbox',IDENTITY+':result:metric')
    assert not any('Grenze' in option or 'Residuum' in option for option in field.options)
    assert 'red_iii_maximum_product_intensity_kg_co2e_per_kg_h2' in plotting.METRICS
    assert any('Modellprüfung' in expander.label for expander in at.expander)
    assert not harness.submitted


def test_empty_comparison_invalidates_its_saved_export(harness):
    at=harness.at
    page(at,'Vergleich')
    row=harness.rows[0]
    choice=f"eu_2024:{row['site_id']}:{row['source_label']}:{row['__result_directory']}"
    widget(at,'multiselect','comparison_cases_v2').set_value([choice]);run(at)
    assert len(pd.read_csv(io.BytesIO(at.session_state['comparison_export'])))==1
    widget(at,'multiselect','comparison_cases_v2').set_value([]);run(at)
    assert 'comparison_export' not in at.session_state
    assert 'last_figure_export' not in at.session_state
    assert not harness.calls and not harness.submitted


def test_ambiguous_comparison_is_handled_with_selection_help(harness,monkeypatch):
    def ambiguous(*args,**kwargs):
        raise ValueError('Mehrere Fälle haben dieselbe Diagrammgruppe.')
    monkeypatch.setattr(plotting,'comparison_figure',ambiguous)
    at=harness.at;page(at,'Vergleich')
    row=harness.rows[0]
    choice=f"eu_2024:{row['site_id']}:{row['source_label']}:{row['__result_directory']}"
    widget(at,'multiselect','comparison_cases_v2').set_value([choice]);run(at)
    assert any('eindeutigere Fallauswahl' in info.value for info in at.info)
    assert 'last_figure_export' not in at.session_state
    assert len(pd.read_csv(io.BytesIO(at.session_state['comparison_export'])))==1
    assert not harness.submitted
