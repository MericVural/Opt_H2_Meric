"""Goal-led scientific workspace using the existing native adapters and U1 contracts."""
from __future__ import annotations

import hashlib
import html
import json
from pathlib import Path

import pandas as pd
import streamlit as st

from gui import analysis_contracts as contracts, result_loader, model_adapter, sensitivity_design, plotting, jobs
from gui.research_logic import (GOALS, SCENARIOS, PARAMETER_GROUPS, fmt, baseline_rows,
    baseline_amount, percent_variants, observed_delta, demand_observation, flatten_plans, same_annual_demand)

CSS = """
<style>
.stMainBlockContainer {max-width:1320px; padding-top:3.7rem; padding-bottom:3rem}
h1 {letter-spacing:-.035em; font-size:2.35rem!important; line-height:1.15!important}
h2 {letter-spacing:-.025em; font-size:1.5rem!important}
h3 {font-size:1.12rem!important}
[data-testid="stSidebar"] {border-right:1px solid #94a3b830}
[data-testid="stSidebar"] h1 {font-size:1.35rem!important}
[data-testid="stMetric"] {border:1px solid #94a3b838;border-radius:14px;padding:1rem}
[data-testid="stMetricValue"] {font-size:1.8rem}
[data-testid="stMain"] [data-testid="stRadio"] label {border:1px solid #94a3b845;border-radius:9px;padding:.35rem .7rem;background:#94a3b808}
[data-testid="stMain"] [data-testid="stRadio"] label:has(input:checked) {border-color:#109d90;background:#109d9017}
[data-testid="stVerticalBlockBorderWrapper"] {border-radius:14px}
[data-testid="stToolbar"] [data-testid="stBaseButton-header"] {display:none}
.h2-eyebrow {font-size:.74rem;font-weight:750;letter-spacing:.16em;color:#109d90;margin-bottom:.55rem}
.h2-question {border-left:4px solid #109d90;padding:.3rem 1rem;margin:.7rem 0 1.1rem}
.h2-question strong {font-size:1.18rem}
.h2-context {font-size:.87rem;opacity:.8;margin:.3rem 0 .85rem}
.h2-observation {padding:1rem 1.2rem;border:1px solid #109d9050;border-radius:12px;background:#109d9010;margin:.8rem 0}
.h2-observation b {color:#109d90;font-size:.78rem;letter-spacing:.08em;display:block;margin-bottom:.4rem}
.h2-brand {font-size:1.65rem;font-weight:800;letter-spacing:-.06em;margin-bottom:0}
@media(max-width:750px){.stMainBlockContainer{padding:1rem}h1{font-size:1.8rem!important}}
</style>
"""
SCENARIO_NATIVE = dict(zip(SCENARIOS, ('reference', 'red_monthly', 'red_hourly', 'off_grid')))


def data_stamp(root):
    """Invalidate cached reads when native inputs/results/evidence change.

    Content hashes and provenance are checked by the native loader on each miss.
    No hourly frames are retained by the cache; original files remain authoritative.
    """
    digest = hashlib.sha256()
    for path in (Path(root)/'gui/case_studies.json',):
        if path.is_file(): digest.update(path.read_bytes())
    for directory in ('outputs_h2', 'input_data', 'gui/registry'):
        for path in sorted((Path(root)/directory).rglob('*')):
            if path.suffix.lower() not in ('.csv', '.json', '.py'): continue
            if any(p in path.parts for p in ('gui_validation', 'gui_runtime')): continue
            if not path.is_file(): continue
            info = path.stat()
            digest.update(f'{path}:{info.st_mtime_ns}:{info.st_size}'.encode())
    return digest.hexdigest()


@st.cache_data(show_spinner=False, ttl=60, max_entries=24)
def read_cases(root, study, site, kind, stamp, _registry):
    fn = result_loader.load_sensitivity_comparisons if kind == 'sensitivity' else result_loader.load_registered_results
    return fn(_registry, study, site)


def cases(ui, registry, site, sensitivity=False):
    return read_cases(str(ui.REPO), site.study_id, site.site_id,
                      'sensitivity' if sensitivity else 'base', st.session_state['_research_stamp'], registry)


def note(text, label='MODELLBEFUND'):
    st.markdown(f'<div class="h2-observation"><b>{html.escape(label)}</b>{html.escape(text)}</div>', unsafe_allow_html=True)


def choose(label, values, key, labels=None):
    values = list(values)
    if not values: return None
    if st.session_state.get(key) not in values: st.session_state.pop(key, None)
    return st.selectbox(label, values, key=key, format_func=(lambda x: labels.get(x, str(x))) if labels else str)


def result_details(ui, frame, site, key):
    with st.expander('Daten, Quellen & Modellprüfung'):
        st.caption('Alle nativen Ergebnisgrößen bleiben erhalten. Solveroptimalität und unabhängige Prüfung sind getrennte Nachweise.')
        st.dataframe(frame.drop(columns=['__result_copies'], errors='ignore'), hide_index=True, width='stretch')
        st.download_button('Ausgewählte Ergebnisfälle (CSV)', frame.to_csv(index=False).encode('utf-8-sig'),
                           'ausgewaehlte_ergebnisse.csv', 'text/csv', key=key+':table_download')
        if not st.checkbox('Prüfnachweis und native Dateien eines Falls laden', key=key+':load_evidence'): return
        row = ui.pick_result(frame, key+':evidence', 'Fall für Quellen, Prüfnachweis und native Dateien')
        if row is not None:
            path = ui.result_path(row)
            bundle = result_loader.load_result_directory(path, ui.REPO, include_hourly=False)
            ui.show_validation(bundle)
            st.download_button('Native Ergebnisdateien (ZIP)', ui.zip_result(path), path.name+'.zip',
                               'application/zip', key=key+':zip')
            st.download_button('Metadaten (JSON)', (path/'run_metadata.json').read_bytes(),
                               'run_metadata.json', 'application/json', key=key+':metadata')


def cohort(ui, frame, scenarios, key):
    """Offer complete native contexts instead of an arbitrary mixture of rows."""
    if frame.empty: return frame
    frame = frame[frame.scenario_id.isin(scenarios)].copy()
    if frame.empty: return frame
    group_fields = [c for c in ('__native_input_sha256', '__native_configuration_sha256',
        '__native_calendar_sha256', '__native_software_sha256', 'solver_name') if c in frame]
    options = []
    if len(group_fields) == 5:
        for _, group in frame.groupby(group_fields, dropna=False, sort=False):
            if group.scenario_id.duplicated().any():
                for _, subgroup in group.groupby('source_label', dropna=False, sort=False):
                    if not subgroup.scenario_id.duplicated().any(): options.append(subgroup)
            else: options.append(group)
    if not options:
        options = [group for _, group in frame.groupby('source_label', dropna=False, sort=False)] if 'source_label' in frame else [frame]
    defaults = set(contracts.controlled_scenario_defaults(frame))
    options.sort(key=lambda f: (-sum(ui.saved_case_id(row) in defaults for _, row in f.iterrows()), -f.scenario_id.nunique()))
    ids = [hashlib.sha256('|'.join(ui.saved_case_id(row) for _, row in f.iterrows()).encode()).hexdigest()[:16] for f in options]
    mapping = dict(zip(ids, options))
    labels = {cid: f"{str(f.iloc[0].get('source_label','Gespeicherte Reihe'))} · {f.scenario_id.nunique()} Szenarien · {f.iloc[0].get('solver_name','Solver unbelegt')}" for cid, f in mapping.items()}
    with st.expander('Ergebnisstand & ausgeführter Solver'):
        selected = choose('Gespeicherter Vergleichsstand', ids, key+':cohort', labels)
        st.caption('Eine gemeinsame Daten- und Konfigurationsgrundlage bleibt zusammen. Abweichende Ausführungen stehen separat zur Auswahl.')
    chosen = mapping[selected]
    if chosen.scenario_id.duplicated().any():
        st.info('Dieser Ergebnisstand enthält mehrere Fälle je Szenario. Bitte eine eindeutige Ausführung auswählen.')
        rows = []
        for scenario, group in chosen.groupby('scenario_id', sort=True):
            row = ui.pick_result(group, key+':duplicate:'+scenario, 'Ausführung für '+scenario)
            if row is not None: rows.append(row)
        chosen = pd.DataFrame(rows)
    missing = set(scenarios)-set(chosen.scenario_id)
    if missing: st.info('In diesem Ergebnisstand fehlen: '+', '.join(sorted(missing))+'. Angezeigt werden nur vorhandene Fälle.')
    return chosen.sort_values('scenario_id').copy()


def describe_comparison(frame, goal):
    context = contracts.comparison_design(frame)
    st.caption(context)
    if goal == 'rules':
        delta = observed_delta(frame)
        if delta:
            direction = 'höher' if delta['absolute'] >= 0 else 'niedriger'
            text = f"S2 liegt gegenüber S1 um {fmt(abs(delta['absolute']), 3)} EUR/kg H₂ {direction}"
            if delta['percent'] is not None: text += f" ({fmt(delta['percent'])} %)."
            else: text += '.'
            if not context.startswith('Kontrollierter'): text += ' Das ist eine beobachtete Differenz; ein isolierter Regeleffekt ist mit diesen Verträgen nicht belegt.'
            note(text)
        st.caption('S1 → S2 verändert die zeitliche Zuordnung. S0 → S1 verändert zusätzlich die EE-Mengendeckung und Überschussallokation. Kostenminimalität ist keine Rentabilitätsrechnung mit Absatzpreis.')
    elif goal == 'profile':
        if not same_annual_demand(frame):
            st.warning('Die gespeicherten Jahresmengen sind unterschiedlich. Diese Auswahl isoliert keine Lieferprofilwirkung.')
        st.caption('Lieferfenster beschränken die Abnahme. Produktion und Speicherung bleiben auch außerhalb dieser Fenster möglich; D2 enthält keine Feiertagskorrektur.')
    elif goal == 'sites':
        st.caption('Ein Standortvergleich umfasst gleichzeitig Wetter, Preise und Finanzierung. Die Differenz lässt sich daraus nicht einem einzelnen Standortfaktor zuschreiben.')


def metric_cards(frame):
    if len(frame) <= 4:
        cols = st.columns(max(1, len(frame)))
        for col, (_, row) in zip(cols, frame.iterrows()):
            label = str(row.scenario_id)
            if frame.scenario_id.nunique() == 1 and len(frame) > 1:
                if 'site_id' in frame and frame.site_id.nunique()>1: label=str(row.get('site_label',row.site_id))
                elif 'profile' in frame and frame.profile.nunique()>1: label=str(row.profile)
                else: label=str(row.get('solver_name','Fall'))
            col.metric(label+' · LCOH', fmt(row.get('lcoh_eur_per_kg_h2'), 3)+' €/kg')


def case_operation(ui, frame, site, key):
    row = ui.pick_result(frame, key+':operation', 'Welchen berechneten Fall möchten Sie im Betrieb ansehen?')
    if row is None: return
    if row.get('site_id') != site.site_id:
        site = ui.load_registry(ui.REPO).get_site(str(row.get('study_id', site.study_id)), str(row.site_id))
    mode = st.radio('Betriebsansicht', ['Solar, Wind & Netz am Tag', 'H₂-Produktion & Speicher', 'Jahreskennzahlen'], horizontal=True, key=key+':operation_view')
    if mode == 'Solar, Wind & Netz am Tag':
        ui.render_daily_electricity(frame, site, key+':daily', selected_row=row)
        return
    bundle = result_loader.load_result_directory(ui.result_path(row), ui.REPO, include_hourly=True)
    timezone = site.metadata.get('input_metadata', {}).get('calendar_timezone', 'UTC')
    if mode == 'Jahreskennzahlen':
        data = plotting.derived_operational_metrics(bundle)
        ui.remember_figure(plotting.operational_figure(bundle, title='Wie wird die Anlage genutzt?'), data, 'Betriebskennzahlen')
    else:
        year = int(site.year_roles.get('study_operation_year') or site.year_roles.get('profile_index_year'))
        c1, c2 = st.columns(2)
        beginning = c1.text_input('Beginn in Ortszeit', f'{year}-02-10 00:00', key=key+':start')
        hours = c2.number_input('Stunden anzeigen', 1, int(row.get('number_of_hours', 8784)), 168, key=key+':hours')
        data = plotting.hourly_frame(bundle, start=beginning, hours=int(hours), timezone=timezone)
        data['source_result_directory'] = str(ui.result_path(row))
        data['case_label'] = ui.saved_case_label(row)
        st.caption(str(data.selection_description.iloc[0]))
        ui.remember_figure(plotting.hourly_figure(data, timezone=timezone), data, 'H₂-Produktion und Speicher · Stundenbetrieb')


def result_workspace(ui, frame, site, key, goal='rules'):
    ui.clear_chart_export()
    if frame.empty:
        st.info('Für diese Auswahl sind noch keine Ergebnisse gespeichert. Unter „Neu berechnen“ können Sie die Untersuchung anlegen.'); return
    st.subheader('Ergebnis Ihrer Untersuchung')
    bound = sum(contracts._bound_validated(row) for _, row in frame.iterrows())
    st.caption(f'{len(frame)} gespeicherte Fälle · unabhängiger Prüfnachweis mit passendem Dateibezug für {bound}/{len(frame)} Fälle')
    if goal == 'dispatch':
        case_operation(ui, frame, site, key)
        result_details(ui, frame, site, key)
        return
    metric_cards(frame)
    describe_comparison(frame, goal)
    views = ['Kosten', 'Auslegung', 'Netz & Emissionen', 'Betrieb']
    view = st.radio('Was möchten Sie aus dem Ergebnis lernen?', views, horizontal=True, key=key+':view')
    if len(frame) > 12:
        st.info('Bitte den Ausschnitt auf höchstens 12 Fälle begrenzen. Die vollständige Tabelle bleibt verfügbar.')
    elif view == 'Kosten':
        cost = st.radio('Kostenansicht', ['Wasserstoffkosten (LCOH)', 'Kostenbestandteile', 'Jahreskosten'], horizontal=True, key=key+':cost')
        if cost == 'Kostenbestandteile': figure = plotting.cost_components_figure(frame, title='Welche Kostenbestandteile erklären die Unterschiede?')
        elif cost == 'Jahreskosten': figure = plotting.comparison_figure(frame, metric='objective_eur_per_year', title='Annualisierte Gesamtkosten')
        else: figure = plotting.lcoh_figure(frame, title='Was kostet ein Kilogramm gelieferter Wasserstoff?')
        ui.remember_figure(figure, frame, cost+' · '+site.label)
        st.caption('Kostenbasis und Annahmen gehören zur Fallstudie. LCOH sind Modellkosten je geliefertem kg H₂ am Ausgang des 300-bar-Speichers.')
    elif view == 'Auslegung':
        ui.remember_figure(plotting.capacity_figure(frame, title='Wie verändert sich die optimale Anlage?'), frame, 'Optimale Auslegung · '+site.label)
        st.caption('Leistung in MW und Speicher in t stehen auf getrennten Achsen. Abweichende Kapazitäten können bei gleichen Kosten alternative Optima sein.')
    elif view == 'Netz & Emissionen':
        focus = st.radio('Bilanz betrachten', ['Emissionsintensitäten', 'Netzbezug', 'Absolute Jahresemissionen'], horizontal=True, key=key+':emissions')
        if focus == 'Emissionsintensitäten':
            figure = plotting.emissions_figure(frame, title='Physische Strombilanz und regulatorische Zuordnung')
            st.caption('Betrieblich: statischer Länderfaktor auf den physischen Netzbezug. Regulatorisch: gesonderte elektrische Teilbilanz. Die gestrichelte Produktreferenz gehört ausschließlich zur regulatorischen Intensität; keine vollständige RFNBO-Zertifizierung.')
        else:
            metric = 'annual_grid_import_mwh' if focus == 'Netzbezug' else choose('Emissionsbilanz',
                ['annual_grid_emissions_kg_co2e', 'annual_regulatory_emissions_kg_co2e'], key+':absolute',
                {'annual_grid_emissions_kg_co2e':'Betriebliche Stromemissionen', 'annual_regulatory_emissions_kg_co2e':'Regulatorische Stromemissionen'})
            figure = plotting.comparison_figure(frame, metric=metric, title=focus)
        ui.remember_figure(figure, frame, focus+' · '+site.label)
    elif view == 'Betrieb':
        case_operation(ui, frame, site, key)
    result_details(ui, frame, site, key)


def solver_results(ui, frame, site, key):
    st.subheader('Lösungsgüte und Rechenaufwand')
    if frame.empty:
        st.info('Kein gespeicherter Solververgleich für diese Auswahl.'); return
    fields = ['scenario_id', 'profile', 'solver_name', 'solver_status', 'lcoh_eur_per_kg_h2',
              'objective_eur_per_year', 'solver_runtime_seconds', 'optimality_gap_fraction']
    st.dataframe(frame[[c for c in fields if c in frame]].rename(columns=plotting.METRICS), hide_index=True, width='stretch')
    st.caption('Laufzeiten sind nur bei vergleichbarer Hardware und Umgebung vergleichbar. Gleiche Zielfunktionswerte erlauben unterschiedliche Kapazitäten bei alternativen Optima.')
    if frame.solver_name.nunique() < 2: st.info('Für diesen Fall liegt bisher nur ein Solver vor; daraus folgt noch kein Solververgleich.')
    with st.expander('Kapazitäten gegenüberstellen'):
        if len(frame) <= 12: ui.remember_figure(plotting.capacity_figure(frame), frame, 'Solververgleich · Auslegung')
    result_details(ui, frame, site, key)


def source_context(ui, site):
    roles = site.year_roles
    if site.historical:
        st.caption('Namibia · historischer Referenzfall mit TMY-Wetter und dokumentierten Proxies. Ein Vergleich mit EU 2024 ist deskriptiv.')
    else:
        st.markdown('<div class="h2-context">'+html.escape(
            f"Historischer Betrieb {roles.get('study_operation_year')} · Kostenbasis EUR {roles.get('cost_price_year')} · WACC-Quelle {roles.get('wacc_source_year')} · betriebliche Emissionen: statische Länderreferenz")+'</div>', unsafe_allow_html=True)


def scope_note(goal, site, profiles, scenarios):
    _, question, changes, fixed = GOALS[goal]
    st.markdown(f'<div class="h2-question"><strong>{html.escape(question)}</strong></div>', unsafe_allow_html=True)
    st.caption('Verändert: '+changes+'. Gleich gehalten: '+fixed+'.')
    if profiles:
        amount = baseline_amount(site, profiles[0])
        st.caption(f"Bezugsmenge: {fmt(amount, 0)} kg H₂/a · {', '.join(profiles)} · {', '.join(scenarios)}. Gespeicherte Ergebnisse behalten ihre tatsächlichen Mengen und Quellen.")


def scenario_select(key, default=None):
    return st.multiselect('Stromversorgungsregeln', list(SCENARIOS), default=default or ['S0','S1','S2'], format_func=SCENARIOS.get, key=key)


def analysis_page(ui, registry, site, key):
    goal = st.radio('Was möchten Sie untersuchen?', ['rules','plant','dispatch','solver'], format_func=lambda x:GOALS[x][0], horizontal=True, key=key+':goal')
    with st.expander('Untersuchung einstellen · Lieferprofil & Stromregeln'):
        left,right=st.columns([1,1.3])
        with left: profile = choose('H₂-Lieferprofil', site.profiles, key+':profile', ui.PROFILE_LABELS)
        with right: scenarios = scenario_select(key+':rules') if goal == 'rules' else [choose('Stromversorgungsregel', SCENARIOS, key+':rule', SCENARIOS)]
    scope_note(goal, site, [profile], scenarios)
    mode = 'Ergebnisse auswerten' if goal == 'dispatch' else st.radio('Arbeitsmodus', ['Ergebnisse auswerten','Neu berechnen'], horizontal=True, key=key+':mode')
    if mode == 'Neu berechnen':
        calculation(ui, registry, [site], key+':new:'+goal, goal, [profile], scenarios)
        return
    if goal == 'dispatch':
        frame = ui.analysis_result_table(registry, site, site.study_id+':'+site.site_id)
        if not frame.empty: frame = frame[frame.profile.eq(profile) & frame.scenario_id.isin(scenarios)]
    else:
        frame = cases(ui, registry, site)
        if not frame.empty: frame = frame[frame.profile.eq(profile)]
        if goal == 'solver':
            frame = frame[frame.scenario_id.isin(scenarios)] if not frame.empty else frame
            solver_results(ui, frame, site, key+':solver'); return
        frame = cohort(ui, frame, scenarios, key+':saved')
    result_workspace(ui, frame, site, key+':result', goal)


def select_family(ui, sens, key, parameter=None):
    if sens.empty: return sens
    field = '__collection_id' if '__collection_id' in sens else '__collection'
    families = {}
    for name, frame in sens.groupby(field, sort=False):
        if parameter is None or parameter in set(frame.sensitivity_parameter): families[str(name)] = frame
    if not families: return sens.iloc[0:0]
    labels = {name: ui.sensitivity_collection_label(frame) for name, frame in families.items()}
    with st.expander('Gespeicherte Versuchsreihe & Herkunft'):
        chosen = choose('Versuchsreihe', families, key+':family', labels)
        st.caption('Jede Kurve verwendet ausschließlich ihre belegte eigene Basis. Andere Versuchsreihen werden nicht angefügt.')
    return families[chosen].copy()


def influence_metric(ui, frame, parameter, key):
    view = st.radio('Wirkung auf', ['Kosten', 'Auslegung', 'Betrieb', 'Emissionen'], horizontal=True, key=key+':view')
    groups = {
        'Kosten': ['objective_eur_per_year','lcoh_eur_per_kg_h2'] if parameter == 'h2_demand_multiplier' else ['lcoh_eur_per_kg_h2','objective_eur_per_year'],
        'Auslegung': ['electrolyzer_capacity_mw','h2_storage_capacity_kg','pv_capacity_mw','wind_capacity_mw','compressor_capacity_mw'],
        'Betrieb': ['annual_grid_import_mwh','annual_h2_delivered_kg','annual_h2_produced_kg'],
        'Emissionen': ['operational_emission_intensity_kg_co2e_per_kg_h2','regulatory_emission_intensity_kg_co2e_per_kg_h2',
                      'annual_grid_emissions_kg_co2e','annual_regulatory_emissions_kg_co2e']}
    return choose('Ergebnisgröße', [m for m in groups[view] if m in plotting.available_metrics(frame)], key+':metric:'+view,
                  {m:ui.metric_label(m) for m in groups[view]})


def sensitivity_page(ui, registry, site, key):
    goals = ['quantity','profile','drivers'] if site.runner_kind == 'eu' else ['drivers']
    goal = st.radio('Was möchten Sie verändern?', goals, format_func=lambda x:GOALS[x][0], horizontal=True, key=key+':goal')
    mode = st.radio('Arbeitsmodus', ['Ergebnisse auswerten','Neu berechnen'], horizontal=True, key=key+':mode')
    if mode == 'Neu berechnen':
        study = registry.studies[site.study_id]
        sites = st.multiselect('Standorte der Untersuchung', list(study.sites), default=[site.site_id], format_func=lambda x:study.sites[x].label, key=key+':sites')
        profiles = st.multiselect('Lieferprofile der Untersuchung', list(site.profiles), default=list(site.profiles) if goal == 'profile' else ['D0'], format_func=ui.PROFILE_LABELS.get, key=key+':profiles:'+goal)
        scenarios = scenario_select(key+':scenarios')
        scope_note(goal, site, profiles, scenarios)
        calculation(ui, registry, [study.sites[s] for s in sites], key+':new:'+goal, goal, profiles, scenarios)
        return
    sens = cases(ui, registry, site, sensitivity=True)
    if goal == 'profile':
        sens = select_family(ui, sens, key+':profile', 'h2_demand_multiplier')
        frame = baseline_rows(sens) if not sens.empty else baseline_rows(cases(ui, registry, site))
        if frame.empty: st.info('Keine gespeicherten Profilbasisfälle.'); return
        profiles = st.multiselect('Lieferprofile vergleichen', list(site.profiles), default=list(site.profiles), format_func=ui.PROFILE_LABELS.get, key=key+':profile_levels')
        scenario = choose('Stromversorgungsregel', SCENARIOS, key+':profile_scenario', SCENARIOS)
        scope_note(goal, site, profiles, [scenario])
        frame = frame[frame.profile.isin(profiles)&frame.scenario_id.eq(scenario)].sort_values('profile')
        if not frame.empty and frame.profile.duplicated().any():
            selected = [ui.pick_result(g, key+':profile:'+str(p), 'Ausführung '+str(p)) for p,g in frame.groupby('profile')]
            frame = pd.DataFrame([r for r in selected if r is not None])
        result_workspace(ui, frame, site, key+':profile_result', goal)
        return
    if sens.empty: st.info('Für diesen Standort ist noch keine Sensitivitätsreihe gespeichert.'); return
    if goal == 'quantity':
        parameter = 'h2_demand_multiplier'
        family = select_family(ui, sens, key+':quantity', parameter)
    else:
        family = select_family(ui, sens, key+':drivers')
        params = [p for p in family.sensitivity_parameter.dropna().unique() if p not in ('baseline','h2_demand_multiplier')]
        groups = {k:[p for p in v if p in params] for k,v in PARAMETER_GROUPS.items()}
        # Historical aliases are interpreted by native operation, never by their name alone.
        extras = [p for p in params if not any(p in values for values in groups.values())]
        if extras: groups['Weitere unterstützte Parameter'] = extras
        group = choose('Einflussbereich', [g for g,p in groups.items() if p], key+':group')
        if group is None: st.info('Diese Reihe enthält keine passende numerische Parametervariation.'); return
        labels = {p:contracts.parameter_presentation(family,p)['label'] for p in groups[group]}
        parameter = choose('Untersuchter Parameter', groups[group], key+':parameter', labels)
    if family.empty: st.info('Keine gespeicherte Reihe für diesen Einfluss.'); return
    left,right=st.columns([1,1.3])
    with left: profile = choose('Angezeigtes Lieferprofil', sorted(family.profile.dropna().unique()), key+':profile', ui.PROFILE_LABELS)
    with right: scenarios = scenario_select(key+':plot_scenarios')
    scope_note(goal, site, [profile], scenarios)
    frame = family[family.profile.eq(profile)&family.scenario_id.isin(scenarios)].copy()
    st.caption(f'{len(family)} Fälle in dieser Standort-Versuchsreihe. Der angezeigte Ausschnitt ändert nicht die gespeicherte Untersuchung.')
    metric = influence_metric(ui, frame, parameter, key+':influence')
    if frame.empty or metric is None: st.info('Für diesen Ausschnitt fehlen bewertete Ergebnisse.'); return
    prepared = contracts.prepare_oat_frame(frame, parameter=parameter, metric=metric)
    if parameter == 'h2_demand_multiplier':
        observation = demand_observation(prepared)
        if observation: note(observation)
        st.caption('Jede Menge erhält eine neu optimierte Anlage. Das lineare Modell enthält keine Größendegression; dies ist kein Engpasstest einer festen Bestandsanlage.')
    else:
        changes = []
        for group_values, group in prepared.groupby(prepared.attrs['group_columns'], dropna=False):
            base = group[group.__oat_is_baseline.eq(True)]
            if len(base)==1 and float(base.iloc[0][metric]) != 0:
                percentages = 100*(group[metric]/float(base.iloc[0][metric])-1)
                changes.append(f"{group.iloc[0].scenario_id}: {fmt(percentages.min())} bis {fmt(percentages.max())} %")
        if changes: note('Änderung gegenüber der jeweiligen eigenen Basis: '+'; '.join(changes)+'. Die Spannweite gilt nur für die berechneten Parameterstufen.')
    st.caption(prepared.attrs.get('note',''))
    ui.remember_figure(plotting.oat_curve_figure(prepared, parameter=parameter, metric=metric,
        title=GOALS[goal][1]), prepared, GOALS[goal][0]+' · '+site.label+' · '+ui.metric_label(metric))
    if 'regulatory' in metric: st.caption('Regulatorische elektrische Teilbilanz; eine Referenzlinie ist kein vollständiger Produktnachweis.')
    with st.expander('Einen Versuchspunkt im Tagesbetrieb öffnen'):
        point = ui.pick_result(prepared, key+':point', 'Berechneter Versuchspunkt')
        if point is not None:
            st.button('Diesen Tagesbetrieb öffnen', key=key+':open_point',on_click=open_point,args=(site,point.to_dict()))
    result_details(ui, prepared, site, key+':details')


def open_point(site, row):
    st.session_state['research_daily_case'] = {'study':site.study_id,'site':site.site_id,'row':row}
    st.session_state['study_selection'] = site.study_id
    st.session_state['site:'+site.study_id] = site.site_id
    st.session_state['navigation'] = 'Analyse'


def calculation(ui, registry, sites, key, goal, profiles, scenarios):
    """Only the explicit submit invokes adapters; visiting a page never solves."""
    variants = []
    valid = bool(sites and profiles and scenarios)
    if goal == 'rules' and len(scenarios)<2:
        st.info('Für einen Regelvergleich mindestens zwei Stromregeln wählen.'); valid=False
    if goal == 'profile' and len(profiles)<2:
        st.info('Für einen Lieferprofilvergleich mindestens zwei Profile wählen.'); valid=False
    if goal == 'quantity':
        levels = st.multiselect('H₂-Jahresmenge [% der Basis]', [50,75,100,125,150], default=[50,75,100,125,150], key=key+':levels')
        with st.expander('Weitere Nachfragestufen'):
            extra = st.text_input('Zusätzliche Prozentwerte, durch Semikolon getrennt', key=key+':extra')
        try:
            additional = ui.gui_utils.parse_values(explicit_text=extra) if extra.strip() else []
            variants = percent_variants([*levels,*additional])
            if not variants: valid=False; st.info('Mindestens eine Nachfragestufe zusätzlich zur 100-%-Basis wählen.')
        except ValueError as exc: st.error(str(exc)); valid=False
        st.caption('100 % ist immer genau einmal als Bezugsfall enthalten. Alle Stunden desselben Lieferprofils werden proportional skaliert.')
        if sites and profiles:
            rows=[]
            for site in sites:
                amount=baseline_amount(site, profiles[0])
                for factor in [1,*[v['value'] for v in variants]]:
                    rows.append({'Standort':site.label, 'Nachfrage [%]':factor*100, 'Lieferung [kg/a]':amount*factor})
            with st.expander('Mengen in kg pro Jahr'): st.dataframe(pd.DataFrame(rows),hide_index=True,width='stretch')
    elif goal == 'drivers':
        if not sites: st.info('Mindestens einen Standort wählen.'); return
        st.caption('Alle bisherigen Parameter, Wertebereiche und relativen Eingaben sind hier erreichbar. Bei mehreren Standorten gelten eingegebene absolute Werte für jeden Standort; für standortrelative Studien getrennte Aufträge verwenden.')
        variants = ui.sensitivity_editor(key+':editor', sites[0])
        profile_levels=st.session_state.get(key+':editor:profile_levels',[])
        selected=st.session_state.get(key+':editor:oat_parameters',[])
        category='h2_delivery_profile' in selected
        valid=valid and variants is not None and bool(variants or category)
        if category and len(set(profiles+profile_levels))<2: valid=False
    with st.expander('Weitere Einstellungen · Solver, Parameter und Quellen'):
        if sites and goal in ('plant','rules','solver'):
            additional_profiles=st.multiselect('Zusätzliche Lieferprofile als getrennte Fallgruppe',
                [p for p in sites[0].profiles if p not in profiles],key=key+':additional_profiles')
            profiles=list(dict.fromkeys([*profiles,*additional_profiles]))
            additional_scenarios=st.multiselect('Zusätzliche Stromregeln als getrennte Fallgruppe',
                [s for s in SCENARIOS if s not in scenarios],format_func=SCENARIOS.get,key=key+':additional_scenarios')
            scenarios=list(dict.fromkeys([*scenarios,*additional_scenarios]))
        solver=choose('Solver',['scipy-highs','gurobi','auto'],key+':solver',{'scipy-highs':'SciPy / HiGHS','gurobi':'Gurobi','auto':'Auto · nativer Auswahlpfad'})
        both=True if goal=='solver' else st.checkbox('Mit HiGHS und Gurobi rechnen',key=key+':both')
        if both: st.caption('Zwei Solver je Fall. Gurobi benötigt eine geeignete Lizenz.')
        for site in sites:
            st.write(site.label)
            st.dataframe(ui.native_parameter_table(site),hide_index=True,width='stretch')
            st.dataframe(ui.year_table(site),hide_index=True,width='stretch')
        if st.button('Solver-Verfügbarkeit prüfen', key=key+':probe'): st.json(model_adapter.probe_solvers(ui.REPO))
    extra_profiles=profile_levels if goal=='drivers' and category else []
    count=(len(profiles)*(1+len(variants or []))+len(set(extra_profiles)-set(profiles)))*len(scenarios)*len(sites)*(2 if both else 1)
    with st.container(border=True):
        st.subheader('Ihre Untersuchung vor dem Start')
        st.write(f"**{count} Modellfälle** · {len(sites)} Standort(e) · {len(profiles)} Basisprofil(e) · {len(scenarios)} Stromregel(n)")
        st.caption('Lieferprofile: '+', '.join(dict.fromkeys([*profiles,*extra_profiles]))+' · Stromregeln: '+', '.join(scenarios))
        if variants:
            st.caption('Je Basisprofil: ein unveränderter Fall plus '+str(len(variants))+' einzelne Parameteränderungen. Zusätzliche Lieferprofile erhalten nur Basisfälle.')
        else:
            st.caption('Je Standort, Lieferprofil, Stromregel und Solver wird genau ein Basisfall berechnet. Dafür ist kein numerischer Sensitivitätsparameter erforderlich.')
        st.caption('Es werden Anlagen neu ausgelegt. Vorhandene Ergebnisdateien werden nicht überschrieben.')
        if st.button('Untersuchung jetzt berechnen', type='primary', key=key+':submit', disabled=not valid or not all(s.can_run for s in sites)):
            plans=[]
            for site in sites:
                native_scenarios=[SCENARIO_NATIVE[s] for s in scenarios]
                if goal in ('quantity','drivers','profile'):
                    plans.append(sensitivity_design.build_oat_profile_plan(ui.REPO,site,profiles,
                        native_scenarios,solver,variants=variants or [],
                        profile_levels=profiles if goal=='profile' else extra_profiles,
                        compare_solvers=both))
                else:
                    plans.append(ui.build_analysis_plan(site,profiles,native_scenarios,
                        solver,[],compare_solvers=both))
            plan=model_adapter.combine_plans(flatten_plans(plans))
            if plan['optimization_count']!=count: raise ValueError('Laufanzahl stimmt nicht mit der sichtbaren Untersuchung überein.')
            plan['analysis_intent']={'type':goal,'label':GOALS[goal][0],'optimization_count':count}
            path=jobs.submit_job(plan,ui.REPO/'outputs_h2/gui_runs',ui.sys.executable)
            st.session_state[key+':job']=str(path)
            st.success('Untersuchung gestartet. Der Auftrag erscheint unten.')
    if st.session_state.get(key+':job'):
        ui.progress_panel(st.session_state[key+':job'])
        if st.button('Ergebnisse dieses Auftrags laden', key=key+':job_results'):
            frame=result_loader.load_job_results(st.session_state[key+':job'],ui.REPO)
            if len(sites)>1: st.dataframe(frame.drop(columns=['__result_copies'],errors='ignore'),hide_index=True,width='stretch'); st.caption('Die einzelnen Standorte sind nach dem Lauf unter Ergebnisse auswerten verfügbar.')
            elif variants: ui.render_sensitivity_frame(frame,key+':live',sites[0])
            else: result_workspace(ui,frame,sites[0],key+':live',goal)


def comparison_page(ui,registry,key):
    style=st.radio('Vergleichsfrage',['EU-Standorte bei gleicher Aufgabe','Eigene Fallgegenüberstellung'],horizontal=True,key=key+':style')
    if style=='Eigene Fallgegenüberstellung':
        st.caption('Erweiterte Auswahl für historische, studienübergreifende und frei zusammengestellte Vergleiche. Unterschiede in den Grundlagen werden ausgewiesen.')
        ui.comparison_view(registry); return
    study=registry.studies.get('eu_2024')
    if study is None: st.info('Die EU-Studie ist nicht registriert.'); return
    c1,c2=st.columns(2)
    with c1: profile=choose('Gleiches Lieferprofil',['D0','D1','D2'],key+':profile',ui.PROFILE_LABELS)
    with c2: scenario=choose('Gleiche Stromregel',SCENARIOS,key+':scenario',SCENARIOS)
    rows=[]
    for site in study.sites.values():
        frame=cases(ui,registry,site)
        if not frame.empty: frame=frame[frame.profile.eq(profile)&frame.scenario_id.eq(scenario)]
        selected=cohort(ui,frame,[scenario],key+':'+site.site_id)
        if not selected.empty: rows.append(selected.iloc[0])
    if not rows: st.info('Keine passenden Standortfälle vorhanden.'); return
    frame=pd.DataFrame(rows)
    context,warnings=result_loader.comparison_context(registry,frame)
    for warning in warnings: st.warning(warning)
    st.session_state['comparison_export']=frame.to_csv(index=False).encode('utf-8-sig')
    st.session_state['comparison_export_context']=context.to_dict('records')
    result_workspace(ui,frame,next(iter(study.sites.values())),key+':result','sites')
    with st.expander('Vergleichsgrundlagen beider Standorte'): st.dataframe(context.astype(str),hide_index=True,width='stretch')


def render(ui):
    st.set_page_config(page_title='H₂ Forschungswerkstatt',page_icon='⚗️',layout='wide')
    st.markdown(CSS,unsafe_allow_html=True)
    registry=ui.load_registry(ui.REPO)
    st.session_state['_research_stamp']=data_stamp(ui.REPO)
    st.sidebar.markdown('<div class="h2-brand">H₂ / Research</div>',unsafe_allow_html=True)
    st.sidebar.caption('Kosten · Auslegung · Stromversorgung')
    if st.session_state.get('navigation') not in ui.PAGES: st.session_state['navigation']='Analyse'
    page=st.sidebar.radio('Arbeitsbereich',ui.PAGES,key='navigation')
    st.sidebar.divider()
    st.sidebar.caption('FORSCHUNGSFRAGE')
    st.sidebar.write('Wie verändern Stromregeln, Standortbedingungen und Nachfrage die kostenoptimale H₂-Produktion?')
    if st.sidebar.button('Ergebnisstand aktualisieren',key='research_refresh'):
        read_cases.clear();st.rerun()
    manual=ui.REPO/'GUI_BEDIENUNGSANLEITUNG.md'
    if manual.is_file(): st.sidebar.download_button('Bedienungsanleitung',manual.read_bytes(),manual.name,'text/markdown',key='research_manual')
    old_pdf=ui.REPO/'GUI_BEDIENUNGSANLEITUNG.pdf'
    if old_pdf.is_file():
        with st.sidebar.expander('Frühere Anleitung'): st.download_button('Historische PDF-Anleitung',old_pdf.read_bytes(),old_pdf.name,'application/pdf')
    with st.sidebar.expander('Berechnungen & Laufprotokolle'):
        if st.checkbox('Gespeicherte Aufträge anzeigen',key='research_jobs_visible'):
            previous=jobs.list_jobs(ui.REPO/'outputs_h2/gui_runs')
            choices={j['job_path']:j for j in previous}
            if choices:
                labels={p:f"{Path(p).name} · {v.get('completed_runs',0)}/{v.get('total_runs',0)} Fälle · gemeldet: {v.get('status','unbekannt')}" for p,v in choices.items()}
                selected=choose('Gespeicherter Auftrag',choices,'research_job_selection',labels)
                state=choices[selected]
                if state.get('status') in ('running','queued'):
                    st.caption('Gespeicherte Statusmeldung; Prozessaktivität ist hier nicht geprüft. Ein alter laufend-Status beweist keine aktive Berechnung.')
                st.json(state,expanded=False)
                if state.get('log_tail'):st.code(state['log_tail'],language=None)
            else:st.caption('Keine lokalen GUI-Aufträge vorhanden.')
    st.sidebar.caption('Oberfläche U2 · 12.10.2026')
    st.markdown('<div class="h2-eyebrow">WASSERSTOFF · WISSENSCHAFTLICHE ANALYSE</div>',unsafe_allow_html=True)
    titles={'Analyse':'Stromregeln verstehen. Anlagen vergleichen.','Sensitivitätsanalyse':'Was treibt die Wasserstoffkosten?',
            'Vergleich':'Gleiche Aufgabe. Andere Bedingungen.','Quellen':'Auf welcher Grundlage rechnen wir?', 'Export':'Ergebnisse nachvollziehbar weitergeben.'}
    st.title(titles[page])
    st.caption('Kostenminimale H₂-Produktion unter modellierten RED-III-Stromversorgungskriterien')
    if page=='Vergleich':
        ui.clear_chart_export();st.session_state.pop('comparison_export',None);st.session_state.pop('comparison_export_context',None)
        st.session_state['chart_scope']={'page':'Vergleich'}
        comparison_page(ui,registry,'research:comparison');return
    c1,c2=st.columns(2)
    with c1: study_id=choose('Fallstudie',registry.studies,'study_selection',{k:v.label for k,v in registry.studies.items()})
    study=registry.studies[study_id]
    if not study.sites: st.info('Für diese dokumentierte Studie ist noch kein Standort registriert.');return
    with c2: site_id=choose('Standort',study.sites,'site:'+study_id,{k:v.label for k,v in study.sites.items()})
    site=registry.get_site(study_id,site_id);key='research:'+study_id+':'+site_id+':'+page
    source_context(ui,site)
    if page in ('Analyse','Sensitivitätsanalyse'):
        ui.clear_chart_export();st.session_state['chart_scope']={'page':page,'study_id':study_id,'site_id':site_id}
    elif page=='Export':
        fig=st.session_state.get('last_figure_export',{});scope=fig.get('scope',{})
        if fig and scope.get('page')!='Vergleich' and (scope.get('site_id')!=site_id or scope.get('study_id')!=study_id): ui.clear_chart_export()
    try:
        pending=st.session_state.get('research_daily_case')
        if page=='Analyse' and pending:
            selected_site=registry.get_site(pending['study'],pending['site'])
            st.subheader('Geöffneter Versuchspunkt · '+selected_site.label)
            st.write(ui.saved_case_label(pd.Series(pending['row'])))
            st.caption('Dieser Punkt behält die im Experiment gespeicherten Parameter und seine Ausführung.')
            if st.button('Zur Analyseauswahl zurück',key='research_close_daily'):
                st.session_state.pop('research_daily_case');st.rerun()
            st.session_state['chart_scope']={'page':'Analyse','study_id':pending['study'],'site_id':pending['site']}
            ui.render_daily_electricity(pd.DataFrame([pending['row']]),selected_site,key+':point',selected_row=pd.Series(pending['row']))
        elif page=='Analyse': analysis_page(ui,registry,site,key)
        elif page=='Sensitivitätsanalyse': sensitivity_page(ui,registry,site,key)
        elif page=='Quellen': ui.sources_view(registry,study,site,key)
        elif page=='Export': ui.export_view(registry,site,study_id+':'+site_id)
    except (OSError,ValueError,KeyError,TypeError) as exc:
        ui.clear_chart_export()
        st.warning('Für diese Auswahl ist die Auswertung noch nicht verfügbar: '+str(exc))
        st.caption('Fehlende oder widersprüchliche Daten werden nicht durch geschätzte Ergebniswerte ersetzt.')
    for warning in registry.warnings: st.sidebar.caption(warning)
