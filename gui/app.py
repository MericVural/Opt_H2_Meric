"""Local scientific interface. All optimization is delegated to native runners."""
from __future__ import annotations
import io
import json
import os
from pathlib import Path
import sys
import zipfile

PACKAGE_ROOT=Path(__file__).resolve().parents[1]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0,str(PACKAGE_ROOT))
REPO=Path(os.environ.get('H2_REPO_ROOT',PACKAGE_ROOT)).resolve()
if str(REPO) not in sys.path:
    sys.path.append(str(REPO))
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from gui.case_study_registry import load_registry, contained_path
from gui import model_adapter, jobs, gui_utils, result_loader, plotting, sensitivity_design
from gui.analysis_intent import ANALYSES, SCENARIO_LABELS, PROFILE_LABELS, request_scope, selection_errors, defaults_for

PAGES=['Analyse','Sensitivitätsanalyse','Vergleich','Quellen','Export']
YEAR_LABELS={'study_operation_year':'Betriebsjahr','profile_index_year':'Technisches Indexjahr',
 'weather_year':'Wetterbasis','market_price_year':'Marktpreisjahr',
 'operational_emission_reference_year':'Betriebliche Emissionsreferenz',
 'regulatory_factor_reference_year':'Regulatorischer Faktor: Bezugsjahr',
 'cost_price_year':'Technologische Geldbasis','wacc_source_year':'WACC-Quellenjahr',
 'result_timestamp_utc':'Ergebnis erstellt (UTC)'}
METRIC_LABELS={'lcoh_eur_per_kg_h2':'LCOH [EUR/kg H₂]', 'objective_eur_per_year':'Jahreskosten [EUR/a]',
 'annual_h2_delivered_kg':'Gelieferte H₂-Jahresmenge [kg/a]',
 'pv_capacity_mw':'PV [MW]','wind_capacity_mw':'Wind [MW]','electrolyzer_capacity_mw':'PEM [MW]',
 'compressor_capacity_mw':'Kompressor [MW]','h2_storage_capacity_kg':'H₂-Speicher [kg]',
 'annual_grid_import_mwh':'Netzbezug [MWh/a]',
 'operational_emission_intensity_kg_co2e_per_kg_h2':'Betriebliche Intensität [kg CO₂e/kg H₂]',
 'regulatory_emission_intensity_kg_co2e_per_kg_h2':'Regulatorische elektrische Teilintensität [kg CO₂e/kg H₂]'}
PARAMETER_LABELS={
 'h2_demand_multiplier':'H₂-Jahresnachfrage: Faktor zur Basis',
 'h2_delivery_profile':'H₂-Lieferprofil: D0 / D1 / D2',
 'electricity_price_offset_eur_per_mwh':'Strompreisoffset [EUR 2023/MWh]',
 'real_wacc_shift_fraction':'Alle Komponenten-WACC: Änderung [Prozentpunkte]',
 'real_wacc_multiplier':'Alle Komponenten-WACC: Faktor',
 'uniform_real_wacc_fraction':'Einheitlicher realer WACC [%]',
 'electricity_price_eur_per_mwh':'Konstanter Strompreis [EUR/MWh]',
 'pv_capex_eur_per_kw':'PV-CAPEX [EUR 2023/kW]',
 'wind_capex_eur_per_kw':'Wind-CAPEX [EUR 2023/kW]',
 'h2_storage_capex_eur_per_kg_h2':'Speicher-CAPEX [EUR 2023/kg H₂]',
 'electrolyzer_capex_eur_per_kw':'PEM-CAPEX [EUR 2023/kW]',
 'electrolyzer_specific_electricity_kwh_per_kg_h2':'PEM-Strombedarf [kWh/kg H₂]',
 'electrolyzer_capex_factor':'PEM-CAPEX: Faktor',
 'electrolyzer_specific_electricity_factor':'PEM-Strombedarf: Faktor'}

def show_figure(figure):
    st.pyplot(figure)
    plt.close(figure)

def year_table(site):
    def display(value):
        if value is None:return 'nicht belegt / nicht anwendbar'
        if isinstance(value,float) and value.is_integer():return str(int(value))
        return str(value)
    return pd.DataFrame([{'Bezug':label,'Wert':display(site.year_roles.get(key))}
        for key,label in YEAR_LABELS.items()])

def native_parameter_table(site):
    md=site.metadata.get('baseline_metadata',{})
    records=md.get('model_parameters',{})
    return pd.DataFrame([{'Parameter':k,**v} for k,v in records.items() if isinstance(v,dict)])

def base_kwargs(site,profile,scenarios,solver):
    ref=site.profiles[profile]
    kwargs={'repo_root':REPO,'input_csv':ref.path,'scenarios':scenarios,'solver':solver,
            'profile_id':profile,'study_id':site.study_id,'site_id':site.site_id,
            'runner_kind':site.runner_kind,'can_run':site.can_run,'source_metadata':ref.metadata_path}
    if site.runner_kind=='eu':
        kwargs.update(design_json=site.design_path)
    elif site.runner_kind=='legacy':
        p=site.metadata['baseline_metadata']['model_parameters']['technologies.pv.real_wacc_fraction']
        kwargs.update(uniform_wacc_percent=100*float(p['value']),uniform_wacc_source=p.get('source'),source_note=p.get('note',''))
    return kwargs

def build_analysis_plan(site,profiles,scenarios,solver,variants,compare_solvers=False):
    plans=[]
    for backend in (['scipy-highs','gurobi'] if compare_solvers else [solver]):
        for profile in profiles:
            kw=base_kwargs(site,profile,scenarios,backend)
            if variants:
                plan=model_adapter.build_sensitivity_plan(**kw,variants=variants)
            else:
                plan=model_adapter.build_single_plan(**kw)
            plan['gui_context']={'study_id':site.study_id,'site_id':site.site_id,'profile':profile,
                                 'year_roles':site.year_roles,'historical':site.historical}
            plans.append(plan)
    return model_adapter.combine_plans(plans)

def remember_oat(identity,widget_key):
    st.session_state.setdefault(identity+':oat_editor_state',{})[widget_key]=st.session_state[widget_key]
    st.session_state[identity+':variants']=None

def demand_quantity_table(site,profiles,variants):
    """Display proportional annual delivery assumptions, without any model call."""
    factors=sorted({1.,*(float(v['value']) for v in variants if v['parameter']=='h2_demand_multiplier')})
    rows=[]
    for profile in profiles:
        ref=site.profiles[profile]
        metadata=ref.metadata.get('demand_profile',{})
        annual=metadata.get('annual_h2_requested_kg',metadata.get('annual_kg'))
        if annual is None:
            annual=float(pd.read_csv(ref.path,usecols=['h2_demand']).h2_demand.sum())
        for factor in factors:
            rows.append({'Lieferprofil':profile,'Jahresnachfrage [% der Basis]':100*factor,
                'Jährliche Pflichtlieferung [kg/a]':float(annual)*factor,
                'Fall':'Unveränderter Basisfall' if factor==1 else 'Einzelvariante'})
    return pd.DataFrame(rows)

def demand_quantity_note():
    st.caption('Nachfragemenge und Lieferprofil sind getrennte Fragen: Der Nachfragefaktor skaliert jede Stunde desselben Profils proportional; die Lieferfenster von D0/D1/D2 bleiben erhalten. 100 % ist der einmalige unveränderte Basisfall.')
    st.info('Für jede Nachfragemenge wird die Anlage neu kostenoptimal ausgelegt. Das lineare Modell enthält keine Größendegression der Investitionskosten. Kapazitäten und Jahreskosten können deshalb proportional zur Nachfrage steigen, während LCOH gleich bleiben. Dies untersucht neue Anlagenauslegungen; Engpässe einer fest vorgegebenen Bestandsanlage werden damit nicht geprüft.')

def sensitivity_editor(identity,site):
    editor=st.session_state.setdefault(identity+':oat_editor_state',{})
    parameter_labels=dict(PARAMETER_LABELS)
    if site.runner_kind=='legacy':
        parameter_labels['electricity_price_offset_eur_per_mwh']='Strompreisoffset [EUR/MWh; Geldbasis nicht belegt]'
    try:
        parameters=model_adapter.supported_parameters(REPO)
    except TypeError:
        parameters=model_adapter.supported_parameters()
    if isinstance(parameters,dict):parameters=list(parameters)
    parameters=[p for p in parameters if p!='baseline']
    if site.runner_kind=='eu':
        parameters=[p for p in parameters if p not in ('uniform_real_wacc_fraction','electricity_price_eur_per_mwh')]
    else:
        parameters=[p for p in parameters if p!='h2_demand_multiplier']
    choices=[p for p in parameters if p in PARAMETER_LABELS]
    if len(site.profiles)>1:choices.append('h2_delivery_profile')
    baseline=site.metadata.get('baseline_metadata',{}).get('model_parameters',{})
    input_ref=site.profiles[next(iter(site.profiles))]
    mean_price=float(pd.read_csv(input_ref.path,usecols=['electricity_price']).electricity_price.mean())
    def levels(name,factors):
        if name not in baseline:return ''
        base=float(baseline[name]['value'])
        return '; '.join(f'{base*f:.14g}' for f in factors)
    defaults={
       'electricity_price_offset_eur_per_mwh':f'{-.5*mean_price:.14g}; {.5*mean_price:.14g}',
       'real_wacc_shift_fraction':'-1; 1','real_wacc_multiplier':'0.6363636363636364; 1.3636363636363635',
       'uniform_real_wacc_fraction':levels('technologies.pv.real_wacc_fraction',(100*7/11,100*15/11)),
       'electricity_price_eur_per_mwh':f'{.5*mean_price:.14g}; {1.5*mean_price:.14g}',
       'pv_capex_eur_per_kw':levels('technologies.pv.capex_eur_per_kw',(.75,1.25)),
       'wind_capex_eur_per_kw':levels('technologies.wind_onshore.capex_eur_per_kw',(.25,.5,1.5)),
       'h2_storage_capex_eur_per_kg_h2':levels('technologies.h2_storage.capex_eur_per_kg_h2',(.75,1.25)),
       'electrolyzer_capex_eur_per_kw':levels('technologies.electrolyzer.capex_eur_per_kw',(.75,1.25)),
       'electrolyzer_specific_electricity_kwh_per_kg_h2':levels('technologies.electrolyzer.specific_electricity_kwh_per_kg_h2',(.9,1.1)),
       'electrolyzer_capex_factor':'0.75; 1.25','electrolyzer_specific_electricity_factor':'0.9; 1.1'}
    defaults['h2_demand_multiplier']='0.5; 0.75; 1.25; 1.5'
    st.caption('OAT: Jeder ausgewählte Parameter wird einzeln gegen seinen Basisfall variiert. Es gibt keine automatische vollfaktorielle Kombination.')
    common=['electricity_price_offset_eur_per_mwh','real_wacc_multiplier','electrolyzer_capex_eur_per_kw',
            'electrolyzer_specific_electricity_kwh_per_kg_h2','pv_capex_eur_per_kw','wind_capex_eur_per_kw','h2_storage_capex_eur_per_kg_h2']
    if st.button('Gemeinsame Namibia-/EU-Stufen für diesen Standort übernehmen',key=identity+':common_preset'):
        st.session_state[identity+':oat_parameters']=[p for p in common if p in choices]
        editor[identity+':oat_parameters']=st.session_state[identity+':oat_parameters']
        for p in common:
            for saved_key in list(editor):
                if saved_key.startswith(identity+p+':'):editor.pop(saved_key)
            st.session_state[identity+p+':values']=defaults.get(p,'')
            st.session_state[identity+p+':mode']='Explizite Werte'
            st.session_state[identity+p+':meaning']='Direkte Parameterwerte'
            for suffix in (':values',':mode',':meaning'):
                editor[identity+p+suffix]=st.session_state[identity+p+suffix]
    selection_key=identity+':oat_parameters'
    selected=st.multiselect('Aktive Sensitivitätsparameter',choices,default=None if selection_key in st.session_state else editor.get(selection_key,[]),
        format_func=lambda p:parameter_labels[p],key=selection_key,on_change=remember_oat,args=(identity,selection_key))
    variants=[]
    st.session_state[identity+':profile_levels']=[]
    for parameter in selected:
        if parameter=='h2_delivery_profile':
            key=identity+'h2_delivery_profile:levels'
            levels=st.multiselect('Zu vergleichende Lieferprofile',list(site.profiles),default=editor.get(key,list(site.profiles)),format_func=lambda p:PROFILE_LABELS.get(p,p),key=key,on_change=remember_oat,args=(identity,key))
            st.session_state[identity+':profile_levels']=levels
            st.caption('Kategorischer OAT-Vergleich bei unveränderter Jahresmenge. Zusätzliche Lieferprofile erhalten ausschließlich einen Basisfall; numerische Varianten bleiben bei den gewählten Basisprofilen.')
            continue
        with st.expander(parameter_labels[parameter],expanded=True):
            relative_base_names={
              'pv_capex_eur_per_kw':'technologies.pv.capex_eur_per_kw',
              'wind_capex_eur_per_kw':'technologies.wind_onshore.capex_eur_per_kw',
              'h2_storage_capex_eur_per_kg_h2':'technologies.h2_storage.capex_eur_per_kg_h2',
              'electrolyzer_capex_eur_per_kw':'technologies.electrolyzer.capex_eur_per_kw',
              'electrolyzer_specific_electricity_kwh_per_kg_h2':'technologies.electrolyzer.specific_electricity_kwh_per_kg_h2'}
            relative=False
            if parameter in relative_base_names and relative_base_names[parameter] in baseline:
                widget_key=identity+parameter+':meaning'
                meanings=['Direkte Parameterwerte','Änderung zur Basis [%]']
                meaning=st.radio('Eingabebezug',meanings,index=None if widget_key in st.session_state else meanings.index(editor.get(widget_key,meanings[0])),
                    horizontal=True,key=widget_key,on_change=remember_oat,args=(identity,widget_key))
                relative=meaning=='Änderung zur Basis [%]'
            widget_key=identity+parameter+':mode'
            modes=['Explizite Werte','Bereich']
            mode=st.radio('Werte festlegen',modes,index=None if widget_key in st.session_state else modes.index(editor.get(widget_key,modes[0])),
                horizontal=True,key=widget_key,on_change=remember_oat,args=(identity,widget_key))
            percent=parameter in ('real_wacc_shift_fraction','uniform_real_wacc_fraction')
            try:
                if mode=='Explizite Werte':
                    fallback=('-10; 10' if 'specific_electricity' in parameter else '-75; -50; 50' if parameter=='wind_capex_eur_per_kw' else '-25; 25') if relative else defaults[parameter]
                    widget_key=identity+parameter+(':relative_values' if relative else ':values')
                    text=st.text_input('Werte mit Semikolon trennen; Dezimalpunkt oder Dezimalkomma',
                        value=None if widget_key in st.session_state else editor.get(widget_key,fallback),
                        key=widget_key,on_change=remember_oat,args=(identity,widget_key))
                    values=gui_utils.parse_values(explicit_text=text,percent=percent)
                else:
                    a,b,c=st.columns(3)
                    range_defaults=gui_utils.parse_values(explicit_text=('-10; 10' if 'specific_electricity' in parameter else '-25; 25') if relative else defaults[parameter])
                    lo,hi=min(range_defaults),max(range_defaults)
                    range_prefix=identity+parameter+(':relative' if relative else ':absolute')
                    key=range_prefix+':min'
                    lower=a.number_input('Minimum',value=float(editor.get(key,lo)),key=key,on_change=remember_oat,args=(identity,key))
                    key=range_prefix+':max'
                    upper=b.number_input('Maximum',value=float(editor.get(key,hi)),key=key,on_change=remember_oat,args=(identity,key))
                    key=range_prefix+':step'
                    step=c.number_input('Schrittweite',min_value=0.000001,value=float(editor.get(key,max(hi-lo,.000001))),format='%.6f',key=key,on_change=remember_oat,args=(identity,key))
                    values=gui_utils.parse_values(min_value=lower,max_value=upper,step=step,percent=percent)
                if relative:
                    base=float(baseline[relative_base_names[parameter]]['value'])
                    values=[base*(1+v/100) for v in values]
                if parameter=='h2_demand_multiplier':
                    if any(value<=0 for value in values):raise ValueError('Der H₂-Nachfragefaktor muss größer als null sein.')
                    if 1. in values:
                        values=[value for value in values if value!=1.]
                        st.caption('100 % wird bereits als Basisfall berechnet und daher nicht erneut als Einzelvariante angelegt.')
                st.caption('An den nativen Runner übergeben: '+', '.join(f'{v:.8g}' for v in values))
                for index,value in enumerate(values):
                    variants.append({'parameter':parameter,'value':value,'source':'Explizite GUI-OAT-Annahme des Nutzers; keine Prognose oder Konfidenzgrenze',
                        'note':'Eine Intervention; alle übrigen dokumentierten Basisannahmen bleiben erhalten.',
                        'label':f'H₂-Jahresnachfrage: {value*100:.8g} % der Basis' if parameter=='h2_demand_multiplier' else f'{parameter_labels[parameter]}: {value:.8g}', 'case_id':f'oat_{parameter}_{index+1}'})
            except (ValueError,TypeError) as exc:
                st.error(str(exc));return None
    st.info('WACC-Prozent und Prozentpunkte werden vor dem Modellaufruf durch 100 geteilt. Ein Faktor wie 7/11 wird als dimensionslose Zahl eingegeben. Einzelne Technologie-WACC werden nicht angeboten, weil der vorhandene Runner sie nicht separat unterstützt.')
    if 'h2_demand_multiplier' in selected:
        st.caption('Nachfragefaktoren eingeben: 0,5 entspricht 50 %, 1,25 entspricht 125 % der Basis. 100 % kommt automatisch hinzu.')
        demand_quantity_note()
        settings=st.session_state.get(identity+':settings',{})
        st.dataframe(demand_quantity_table(site,st.session_state.get(identity+':sens_profiles') or settings.get('profiles') or list(site.profiles),variants),hide_index=True,width='stretch')
    return variants

def result_table(registry,site,profiles=None):
    frame=result_loader.load_registered_results(registry,site.study_id,site.site_id)
    if profiles and 'profile' in frame:
        frame=frame[frame.profile.isin(profiles)]
    return frame

def sensitivity_collection_label(family):
    row=family.iloc[0];details=[]
    pf=next((c for c in ('demand_profile','profile') if c in family),None)
    if pf:details.append('Lieferprofile '+', '.join(sorted(family[pf].dropna().astype(str).unique())))
    if 'solver_name' in family:details.append('Solver '+', '.join(sorted(family.solver_name.dropna().astype(str).unique())))
    count=saved_count(row,'__collection_execution_count')
    return ' · '.join([str(row['__collection']),*details])+(f' · {count} identische Versuchsreihen' if count>1 else '')

def open_daily_analysis(site,row):
    """Transfer the exact saved result, without requesting a new calculation."""
    identity=site.study_id+':'+site.site_id
    st.session_state['navigation']='Analyse'
    st.session_state[identity+':analysis_source']='Gespeicherte Ergebnisse'
    st.session_state[identity+':pending_daily_result']=str(result_path(row))

def remember_analysis_collection(identity,key):
    st.session_state[identity+':saved_collection']=st.session_state[key]

def analysis_result_table(registry,site,identity):
    """Keep result families distinct while making their native cases analyzable."""
    families={'base_results':result_table(registry,site)}
    labels={'base_results':'Basis- und Szenariofälle'}
    sens=result_loader.load_sensitivity_comparisons(registry,site.study_id,site.site_id)
    if not sens.empty:
        field='__collection_id' if '__collection_id' in sens else '__collection'
        for cid,group in sens.groupby(field,sort=False):
            families[str(cid)]=group.copy()
            labels[str(cid)]='Sensitivität · '+sensitivity_collection_label(group)
    key=identity+':analysis_collection'
    pending=st.session_state.pop(identity+':pending_daily_result',None)
    if pending is not None:
        found=None
        for cid,family in families.items():
            for _,row in family.iterrows():
                if any(str(copy.get('__result_directory'))==pending for copy in saved_copies(row)):
                    found=(cid,row);break
            if found is not None:break
        if found is None:
            st.warning('Der gewählte Fall ist noch keiner gespeicherten Ergebnisreihe zugeordnet. Nach Abschluss des Auftrags erneut öffnen.')
        else:
            cid,row=found
            st.session_state[key]=cid
            st.session_state[identity+':saved_collection']=cid
            st.session_state[identity+':result_v2']=saved_case_id(row)
            st.session_state[identity+':graph']='Tagesstrom: Solar, Wind und Netz'
            filters={'profiles':[row['profile']],'scenarios':[row['scenario_id']],
                     'solvers':[row.get('solver_name','Solver nicht belegt')]}
            st.session_state[identity+':saved_filters']=filters
            for field,values in filters.items():
                st.session_state[identity+':results:saved_'+field]=values
    if st.session_state.get(key) not in families:st.session_state.pop(key,None)
    if key not in st.session_state and st.session_state.get(identity+':saved_collection') in families:
        st.session_state[key]=st.session_state[identity+':saved_collection']
    selected=st.selectbox('Ergebnisreihe',list(families),format_func=lambda cid:labels[cid],key=key,
                         on_change=remember_analysis_collection,args=(identity,key))
    st.session_state[identity+':saved_collection']=selected
    st.caption('Hier wird ein berechneter Fall ausgewertet. Die Herkunft aus einer Sensitivitätsreihe ändert daran nichts; Parameterwirkungen vergleichen Sie unter Sensitivitätsanalyse.')
    return families[selected].copy()

def result_path(row):
    for key in ('__result_directory','result_directory','resolved_result_directory'):
        value=row.get(key)
        if value is not None and not pd.isna(value):
            candidate=Path(str(value))
            if candidate.is_absolute():return contained_path(REPO,candidate,must_exist=True)
    raise ValueError('Ergebnis besitzt keinen geprüften absoluten Exportpfad.')

def saved_case_id(row):
    value=row.get('__analysis_id')
    return str(value) if value is not None and pd.notna(value) else str(row['__result_directory'])

def saved_copies(row):
    value=row.get('__result_copies')
    if isinstance(value,str):
        try:
            copies=json.loads(value)
            if isinstance(copies,list) and all(isinstance(item,dict) for item in copies):return copies
        except (ValueError,TypeError):pass
    return [dict(row)]

def saved_count(row,name,default=1):
    value=row.get(name)
    return int(value) if value is not None and pd.notna(value) else default

def saved_case_label(row):
    parts=[str(row[k]) for k in ('site_id','scenario_id','profile','solver_name','case_id') if k in row and pd.notna(row[k]) and str(row[k])]
    copies=saved_count(row,'__execution_count')
    if copies>1:
        parts.append(f'{copies} identische Ausführungen')
        chosen=str(row['__result_directory'])
        bound=[item.get('validation_evidence',{}) for item in saved_copies(row) if str(item.get('__result_directory'))==chosen]
        passed=any(v.get('status')=='passed' and v.get('covers_selected_result') is True and v.get('source_comparison_hash_matches') is True for v in bound)
        parts.append('validiert' if passed else 'nicht vollständig validiert')
    elif pd.notna(row.get('source_label')):parts.append(str(row['source_label']))
    return ' · '.join(parts)+f' · {float(row.lcoh_eur_per_kg_h2):.4f} EUR/kg'

def show_saved_origins(frame,title='Gespeicherte Ausführungen und Herkunft'):
    records=[];seen=set()
    for _,row in frame.iterrows():
        for copy in saved_copies(row):
            path=str(copy.get('__result_directory',''))
            collection=str(copy.get('source_label',copy.get('__collection','')))
            source=str(copy.get('__source_csv',''))
            key=(path,collection,source)
            if key in seen:continue
            seen.add(key)
            evidence=copy.get('validation_evidence') or {}
            status=evidence.get('status','nicht zugeordnet')
            records.append({'Sammlung':collection,'GUI-Auftrag':copy.get('gui_job_id',''),
                'Exportordner':path,'Gespeicherter Laufstatus':copy.get('gui_job_state',''),
                'Unabhängiger Prüfnachweis':status,'Quellentabelle':source})
    if not records:return
    with st.expander(title):
        st.caption('Alle Originaldateien bleiben gespeichert. Der Prüfnachweis gehört jeweils zur einzelnen Ausführung; er wird nicht auf andere Kopien übertragen.')
        st.dataframe(pd.DataFrame(records).fillna(''),hide_index=True,width='stretch')

def pick_result(frame,identity,label='Gespeicherten Ergebnisfall wählen'):
    if frame.empty:
        st.info('Keine passenden gespeicherten Ergebnisse.');return None
    frame=frame.reset_index(drop=True)
    records={saved_case_id(row):row for _,row in frame.iterrows()}
    def display(result_id):
        return saved_case_label(records[result_id])
    widget_key=identity+':result_v2'
    previous=st.session_state.get(widget_key)
    if previous not in records:
        match=next((key for key,row in records.items() if any(str(copy.get('__result_directory'))==previous for copy in saved_copies(row))),None)
        if match is None:st.session_state.pop(widget_key,None)
        else:st.session_state[widget_key]=match
    selected=st.selectbox(label,list(records),format_func=display,key=widget_key)
    row=records[selected]
    if saved_count(row,'__execution_count')>1:
        st.caption(f'{saved_count(row,"__execution_count")} nachweislich identische gespeicherte Ausführungen werden als ein Ergebnisfall angezeigt. Kennzahlen und nativer Export verwenden die ausgewählte repräsentative Ausführung.')
    show_saved_origins(pd.DataFrame([row]))
    return row

def render_metrics(bundle):
    row=bundle.summary.iloc[0]
    a,b,c,d=st.columns(4)
    a.metric('LCOH',f'{row.lcoh_eur_per_kg_h2:.4f} EUR/kg H₂')
    b.metric('Jahreskosten',f'{row.objective_eur_per_year/1e6:.3f} Mio. EUR/a')
    c.metric('H₂-Lieferung',f'{row.annual_h2_delivered_kg/1e6:.3f} Mio. kg/a')
    d.metric('Solverstatus',str(row.solver_status))
    st.dataframe(pd.DataFrame([{'Größe':label,'Wert':row.get(k)} for k,label in METRIC_LABELS.items() if pd.notna(row.get(k))]),hide_index=True,width='stretch')
    operational=result_loader.derived_operational_metrics(bundle)
    if not operational.empty:
        st.dataframe(operational,hide_index=True,width='stretch')
    for key in ('red_iii_temporal_compliant','red_iii_ghg_compliant'):
        if key in row:
            value=row[key] if pd.notna(row[key]) else 'nicht angewandt / nicht belegt'
            st.caption(f'{key}: {value} (modellierte Teilprüfung)')
    st.caption('Betriebliche Länderreferenz und regulatorische elektrische Teilbilanz werden getrennt bewertet. Diese Prüfung ersetzt keine vollständige RFNBO-Zertifizierung.')

def show_validation(bundle):
    validation=bundle.validation
    if not validation:
        st.warning('Kein zugeordneter unabhängiger Validierungsbericht gefunden. Ein optimaler Solverstatus allein ist keine Exportabnahme.')
    else:
        st.json(validation)
    st.dataframe(pd.DataFrame([{'Datei / Vertrag':k,'Nachweis':str(v)} for k,v in bundle.provenance.items()]),hide_index=True,width='stretch')

def zip_result(path):
    memory=io.BytesIO()
    with zipfile.ZipFile(memory,'w',zipfile.ZIP_DEFLATED) as archive:
        for name in ('summary.csv','hourly_operation.csv','validated_input.csv','run_metadata.json'):
            file=path/name
            if file.is_file():archive.write(file,arcname=name)
    return memory.getvalue()

@st.fragment(run_every='3s')
def progress_panel(job_dir):
    try:
        state=jobs.read_status(job_dir)
        st.write('**Laufstatus:**',state.get('status','unbekannt'))
        total=int(state.get('total_runs',state.get('planned_runs',0)))
        done=int(state.get('completed_runs',state.get('completed',0)))
        if total:st.progress(min(1.0,done/total),text=f'{done} / {total} Fälle abgeschlossen')
        for field in ('current_case','solver','elapsed_seconds','message','error'):
            if state.get(field) is not None:st.write(field+':',state[field])
        if state.get('status') in ('failed','error','interrupted'):st.error(state.get('error','Der Lauf wurde nicht erfolgreich beendet.'))
        elif state.get('status') in ('completed','succeeded'):st.success('Optimierungen abgeschlossen. Den unabhängigen Validierungsstatus im Ergebnis prüfen.')
        st.json(state,expanded=False)
        if state.get('log_tail'):
            with st.expander('Natives Laufprotokoll'):st.code(state['log_tail'],language=None)
    except (OSError,ValueError) as exc:st.error(str(exc))

def navigate(page):
    st.session_state['navigation']=page

def change_analysis(identity,site):
    kind=st.session_state[identity+':analysis_type']
    st.session_state[identity+':settings']=defaults_for(kind,site.profiles)
    for suffix in (':profiles',':scenarios',':profile_choice',':scenario_choice',':solver'):
        st.session_state.pop(identity+suffix,None)

def use_sensitivity(identity,site):
    st.session_state[identity+':analysis_type']='sensitivity'
    current=st.session_state[identity+':settings']
    current['kind']='sensitivity'
    st.session_state['navigation']='Lauf starten'

def store_setting(identity,field,widget,single=False):
    value=st.session_state[widget]
    st.session_state[identity+':settings'][field]=[value] if single else value

def configure_analysis(identity,site):
    settings=st.session_state[identity+':settings']
    kinds=[k for k in ANALYSES if k!='demand_comparison' or len(site.profiles)>1]
    st.selectbox('Welche Analyse möchten Sie durchführen?',kinds,
        index=kinds.index(settings['kind']),format_func=lambda k:ANALYSES[k]['label'],
        key=identity+':analysis_type',on_change=change_analysis,args=(identity,site))
    settings=st.session_state[identity+':settings']
    kind=settings['kind']
    st.write(ANALYSES[kind]['goal'])
    roles=site.year_roles
    if roles.get('study_operation_year'):
        st.caption('Datengrundlage: historischer Betrieb '+str(roles['study_operation_year'])+' · technische Geldbasis EUR '+str(roles.get('cost_price_year'))+' · WACC-Quelle '+str(roles.get('wacc_source_year')))
    else:
        st.caption('Datengrundlage: dokumentierte TMY-Wetterbasis · technisches Indexjahr '+str(roles.get('profile_index_year'))+' · Strompreisjahr nicht belegt')
    if kind=='saved_results':
        st.caption('Ergebnisfälle wählen Sie im Ergebnisbereich. Diese Auswahl startet keinen Solver.')
        return
    scenario_ids=list(SCENARIO_LABELS)
    profile_ids=list(site.profiles)
    single_scenario=kind in ('single_case','demand_comparison','solver_comparison')
    single_profile=kind in ('single_case','scenario_comparison','solver_comparison')
    if single_scenario:
        widget=identity+':scenario_choice'
        st.selectbox('Stromversorgungsszenario',scenario_ids,index=scenario_ids.index(settings['scenarios'][0]),
            format_func=lambda s:SCENARIO_LABELS[s],key=widget,on_change=store_setting,args=(identity,'scenarios',widget,True))
    else:
        widget=identity+':scenarios'
        st.multiselect('Stromversorgungsszenarien',scenario_ids,default=settings['scenarios'],
            format_func=lambda s:SCENARIO_LABELS[s],key=widget,on_change=store_setting,args=(identity,'scenarios',widget))
    if single_profile:
        widget=identity+':profile_choice'
        st.selectbox('H₂-Lieferprofil',profile_ids,index=profile_ids.index(settings['profiles'][0]),
            format_func=lambda p:PROFILE_LABELS.get(p,p),key=widget,on_change=store_setting,args=(identity,'profiles',widget,True))
    else:
        widget=identity+':profiles'
        st.multiselect('H₂-Lieferprofile',profile_ids,default=settings['profiles'],format_func=lambda p:PROFILE_LABELS.get(p,p),
            key=widget,on_change=store_setting,args=(identity,'profiles',widget))
    if kind=='solver_comparison':
        st.info('Geplant sind HiGHS und Gurobi mit denselben Eingaben. Gurobi benötigt eine ausreichende Lizenz.')
    else:
        widget=identity+':solver'
        solvers=['scipy-highs','gurobi','auto']
        st.selectbox('Solver',solvers,index=solvers.index(settings['solver']),key=widget,on_change=store_setting,args=(identity,'solver',widget))
    if site.runner_kind=='eu':
        st.caption('Lieferprofile: synthetisch vorgegebene Abnahme bei gleicher Jahresmenge. H₂-Produktion und Speicherung sind auch außerhalb der Lieferfenster möglich; D2 enthält keine Feiertagskorrektur.')
    if kind=='scenario_comparison':
        st.caption('S1 → S2 vergleicht monatliche mit stündlicher Zuordnung. S0 → S1 verändert zusätzlich die EE-Mengendeckung und Überschussallokation. Betriebliche Netzemissionen verwenden weiterhin den dokumentierten Jahresfaktor.')
    if kind=='sensitivity':
        st.button('Sensitivitätsparameter festlegen',key=identity+':edit_oat',on_click=navigate,args=('Sensitivitätsanalyse',))

def intent_preview(identity,site,settings,*,compact=False):
    kind=settings['kind'];definition=ANALYSES[kind]
    st.subheader('Ihre geplante Analyse: '+definition['label'])
    st.write('**Ziel:** '+definition['goal'])
    if kind=='saved_results':
        st.info('Gespeicherte Ergebnisse auswerten · 0 neue Optimierungen')
        return None
    variants=st.session_state.get(identity+':variants')
    errors=selection_errors(kind,settings['profiles'],settings['scenarios'],variants)
    rows=[{'Auswahl':'Standort','Geplant':site.label},
          {'Auswahl':'Szenarien','Geplant':', '.join(SCENARIO_LABELS[s] for s in settings['scenarios']) or 'keine'},
          {'Auswahl':'H₂-Lieferprofile','Geplant':', '.join(PROFILE_LABELS.get(p,p) for p in settings['profiles']) or 'keine'},
          {'Auswahl':'Solver','Geplant':'HiGHS und Gurobi' if kind=='solver_comparison' else settings['solver']},
          {'Auswahl':'Was wird variiert?','Geplant':definition['changes']},
          {'Auswahl':'Was bleibt fest?','Geplant':definition['fixed']}]
    st.dataframe(pd.DataFrame(rows),hide_index=True,width='stretch')
    if errors:
        for error in errors:st.warning(error)
        return None
    scope=request_scope(kind,settings['profiles'],settings['scenarios'],variants)
    st.metric('Neue Optimierungsläufe',scope['optimization_count'])
    count_scope=f"{len(scope['profiles'])} Lieferprofil(e) × {len(scope['scenarios'])} Szenario/Szenarien"
    if kind=='sensitivity':count_scope+=f" × (1 unveränderter Fall + {len(scope['variants'])} Einzelvarianten)"
    if scope['compare_solvers']:count_scope+=' × 2 Solver'
    st.caption(count_scope+f" = {scope['optimization_count']} Läufe am gewählten Standort.")
    if kind=='sensitivity':
        st.dataframe(pd.DataFrame(scope['variants'])[['label','parameter','value']],hide_index=True,width='stretch')
        if any(v['parameter']=='h2_demand_multiplier' for v in scope['variants']):
            demand_quantity_note()
            st.dataframe(demand_quantity_table(site,scope['profiles'],scope['variants']),hide_index=True,width='stretch')
    if not {'reference','red_monthly','red_hourly'}.issubset(scope['scenarios']):
        st.caption('Diese Auswahl liefert eine Teilvalidierung. Die bestehende vollständige Szenarioabnahme verlangt S0, S1 und S2 gemeinsam.')
    if 'off_grid' in scope['scenarios']:st.caption('S3 ist technisch implementiert und eine zusätzliche Untersuchung außerhalb des bisherigen EU-Kernversuchs S0/S1/S2.')
    return scope

def remember_saved_filter(base_identity,field,widget_key):
    st.session_state.setdefault(base_identity+':saved_filters',{})[field]=st.session_state[widget_key]

def saved_result_filters(frame,identity):
    st.subheader('Gespeicherte Fälle für diese Ansicht auswählen')
    st.caption('Diese Filter gelten für die Fallauswahl, angezeigte Vergleichsgrafiken und den Tabellenexport dieser Seite.')
    if frame.empty:return frame
    profiles=sorted(frame['profile'].dropna().unique())
    scenarios=sorted(frame['scenario_id'].dropna().unique())
    base_identity=identity.rsplit(':',1)[0]
    saved=st.session_state.setdefault(base_identity+':saved_filters',{})
    profile_key=identity+':saved_profiles';scenario_key=identity+':saved_scenarios'
    chosen_profiles=st.multiselect('Gespeicherte Lieferprofile',profiles,default=[p for p in saved.get('profiles',profiles) if p in profiles],
        key=profile_key,on_change=remember_saved_filter,args=(base_identity,'profiles',profile_key))
    chosen_scenarios=st.multiselect('Gespeicherte Szenarien',scenarios,default=[s for s in saved.get('scenarios',scenarios) if s in scenarios],
        key=scenario_key,on_change=remember_saved_filter,args=(base_identity,'scenarios',scenario_key))
    selected=frame[frame['profile'].isin(chosen_profiles)&frame['scenario_id'].isin(chosen_scenarios)].copy()
    if 'solver_name' in frame:
        solver_values=frame['solver_name'].fillna('Solver nicht belegt')
        solvers=sorted(solver_values.unique())
        key=identity+':saved_solvers'
        selected_solvers=st.multiselect('Gespeicherte Solver',solvers,default=[s for s in saved.get('solvers',solvers) if s in solvers],
            key=key,on_change=remember_saved_filter,args=(base_identity,'solvers',key))
        selected=selected[solver_values.loc[selected.index].isin(selected_solvers)]
    st.caption(f'{len(selected)} eindeutige passende Ergebnisfälle · identische Wiederholungen zusammengefasst · 0 neue Optimierungen')
    return selected


def metric_options(frame):
    # Scientific metrics first; full native outputs remain in table/export.
    return [k for k in dict.fromkeys([*METRIC_LABELS,*plotting.METRICS]) if k in frame]

def metric_label(key):
    return METRIC_LABELS.get(key,plotting.METRICS.get(key,key))

def remember_figure(figure,frame,label):
    png=io.BytesIO();svg=io.BytesIO()
    figure.savefig(png,format='png',dpi=160,bbox_inches='tight')
    figure.savefig(svg,format='svg',bbox_inches='tight')
    st.session_state['last_figure_export']={'png':png.getvalue(),'svg':svg.getvalue(),'label':label}
    st.session_state['last_chart_data']=frame.to_csv(index=False).encode('utf-8-sig')
    show_figure(figure)

def selected_chart(frame,identity,title):
    if frame.empty:return
    options=metric_options(frame)
    if not options:
        st.info('Keine numerische Kennzahl für diese Auswahl vorhanden.');return
    metric=st.selectbox('Kennzahl',options,format_func=metric_label,key=identity+':metric')
    chart=st.selectbox('Diagrammtyp',['Balkendiagramm','Liniendiagramm','Gruppierte Balken','Gestapelte Kosten'],key=identity+':chart_type')
    labels={saved_case_id(row):saved_case_label(row) for _,row in frame.iterrows()}
    selected=st.multiselect('Fälle in der Grafik',list(labels),default=list(labels)[:min(3,len(labels))],format_func=lambda k:labels[k],key=identity+':cases')
    chosen=frame[frame.apply(saved_case_id,axis=1).isin(selected)].copy()
    if chosen.empty:
        st.caption('Mindestens einen Fall für die Grafik auswählen.');return
    if len(chosen)>12:
        st.info('Für eine lesbare Grafik höchstens 12 Fälle auswählen. Alle Fälle bleiben in Tabelle und Export verfügbar.');return
    grouping=None
    if chart=='Gruppierte Balken':
        groups=[k for k in ('scenario_id','demand_profile','profile','site_id','solver_name') if k in chosen]
        grouping=st.selectbox('Gruppierung',groups,key=identity+':group') if groups else None
    try:
        figure=plotting.cost_components_figure(chosen,title=title) if chart=='Gestapelte Kosten' else plotting.comparison_figure(chosen,metric=metric,chart_type=chart,group_by=grouping,title=title)
    except (ValueError,KeyError,TypeError) as exc:
        st.info('Für diese Fall-/Kennzahlauswahl ist die Grafik nicht verfügbar: '+str(exc))
        return
    remember_figure(figure,chosen,title)
    with st.expander('Vollständige Fallnamen der Grafik'):
        st.dataframe(plotting.case_label_table(chosen),hide_index=True,width='stretch')

def render_daily_electricity(frame,site,identity,*,selected_row=None):
    """Read a saved native case and display its complete local calendar day."""
    row=selected_row if selected_row is not None else pick_result(
        frame,identity+':daily_case',label='Ergebnisfall für den Tagesverlauf')
    if row is None:return
    try:
        bundle=result_loader.load_result_directory(result_path(row),REPO,include_hourly=True)
        scenario=str(row['scenario_id'])
        if scenario not in bundle.hourly:raise ValueError('Für den gewählten Szenariofall fehlen die Stundenwerte.')
        timezone=site.metadata.get('input_metadata',{}).get('calendar_timezone','UTC')
        local=pd.to_datetime(bundle.hourly[scenario]['timestamp'],utc=True).dt.tz_convert(timezone)
        lower=local.min().date();upper=local.max().date()
        default=(pd.Timestamp(lower)+pd.Timedelta(days=1)).date() if lower<upper else lower
        day_key=identity+':daily_day'
        existing=st.session_state.get(day_key)
        if existing is not None and not lower<=existing<=upper:st.session_state.pop(day_key,None)
        day=st.date_input('Tag auswählen',value=default,min_value=lower,max_value=upper,key=day_key,
                          help='Kalendertag in der Ortszeit des Standorts. Zeitumstellungstage enthalten 23 oder 25 Stunden.')
        mode=st.radio('Tagesdarstellung',['Stündlicher Tagesverlauf','Kumulative Tagesenergie'],
                      horizontal=True,key=identity+':daily_mode')
        basis=st.radio('Stromgrößen',['Direktversorgung','Erzeugung und Netzbezug'],
                       horizontal=True,key=identity+':daily_basis')
        if basis=='Direktversorgung':
            st.caption('Direkt genutzter Solar-/Windstrom und Netzbezug versorgen den elektrischen Anlagenbedarf. Kumulative Energie zählt ab Tagesbeginn in MWh.')
        else:
            st.caption('Gesamte Solar-/Winderzeugung einschließlich Überschüssen und der Netzbezug werden getrennt dargestellt. Ihre Summe ist kein Anlagenstrombedarf.')
        daily=plotting.daily_electricity_frame(bundle,day=day,scenario_id=scenario,timezone=timezone,basis=basis)
        daily['source_result_directory']=str(result_path(row))
        daily['case_label']=saved_case_label(row)
        title=f'{site.label} · {scenario} · {day.isoformat()}'
        st.caption(f'{len(daily)} gespeicherte Stunden · Ortszeit {timezone} · keine neue Optimierung')
        figure=plotting.daily_electricity_figure(daily,mode=mode,timezone=timezone,title=title)
        remember_figure(figure,daily,'Tagesstrom: Solar, Wind und Netz')
        totals=daily.iloc[-1]
        a,b,c=st.columns(3)
        a.metric('Solarenergie des Tages',f'{totals.cumulative_pv_mwh:,.2f} MWh')
        b.metric('Windenergie des Tages',f'{totals.cumulative_wind_mwh:,.2f} MWh')
        c.metric('Netzbezug des Tages',f'{totals.cumulative_grid_mwh:,.2f} MWh')
        st.download_button('Tagesdaten als CSV herunterladen',daily.to_csv(index=False).encode('utf-8-sig'),
                           f'tagesstrom_{site.site_id}_{scenario}_{day.isoformat()}.csv','text/csv',key=identity+':daily_download')
        with st.expander('Stundenwerte des ausgewählten Tages'):
            st.dataframe(daily,hide_index=True,width='stretch')
    except (OSError,ValueError,KeyError) as exc:
        st.error('Tagesgrafik kann für diese Auswahl nicht angezeigt werden: '+str(exc))

def render_result_display(frame,site,identity):
    if frame.empty:
        st.info('Noch keine passenden Ergebnisdateien vorhanden.');return
    row=pick_result(frame,identity)
    if row is None:return
    bundle=result_loader.load_result_directory(result_path(row),REPO,include_hourly=True)
    render_metrics(bundle)
    with st.expander('Unabhängige Validierung und Herkunft'):
        show_validation(bundle)
        st.caption('Eine Szenarioteilauswahl kann die vollständige S0/S1/S2-Prüfung nicht erfüllen. Bilanz- und Quellenfehler bleiben davon getrennt sichtbar.')
    view=st.selectbox('Darstellung',['Kennzahl vergleichen','Kapazitäten','Kostenkomponenten','Betriebskennzahlen','Emissionen','Stundenbetrieb','Tagesstrom: Solar, Wind und Netz'],key=identity+':graph')
    if view=='Kennzahl vergleichen':selected_chart(frame,identity+':result','Ergebnisvergleich')
    elif view=='Tagesstrom: Solar, Wind und Netz':render_daily_electricity(frame,site,identity,selected_row=row)
    elif view=='Stundenbetrieb':
        roles=site.year_roles;year=int(roles.get('study_operation_year') or roles.get('profile_index_year'))
        timezone=site.metadata.get('input_metadata',{}).get('calendar_timezone','UTC')
        beginning=st.text_input('Beginn des Ausschnitts (lokale Zeit)',f'{year}-02-10 00:00',key=identity+':hourly_start')
        hours=st.number_input('Stunden im Ausschnitt',min_value=1,max_value=int(row.number_of_hours),value=min(168,int(row.number_of_hours)),step=24,key=identity+':hourly_length')
        try:remember_figure(plotting.hourly_figure(bundle,start=beginning,hours=int(hours),timezone=timezone),pd.DataFrame([row]),'Stundenbetrieb')
        except (ValueError,KeyError) as exc:st.error(str(exc))
    elif view=='Betriebskennzahlen':remember_figure(plotting.operational_figure(bundle,title=site.label),pd.DataFrame([row]),view)
    else:
        funcs={'Kapazitäten':plotting.capacity_figure,'Kostenkomponenten':plotting.cost_components_figure,'Emissionen':plotting.emissions_figure}
        remember_figure(funcs[view](pd.DataFrame([row]),title=site.label),pd.DataFrame([row]),view)
    with st.expander('Alle Kennzahlen und Ergebnisfälle'):
        st.dataframe(frame.drop(columns=['__result_copies'],errors='ignore'),hide_index=True,width='stretch')
        st.dataframe(bundle.summary,hide_index=True,width='stretch')

@st.fragment(run_every='3s')
def inline_job_results(job_dir,site,identity):
    state=jobs.read_status(job_dir)
    total=int(state.get('total_runs',0));done=int(state.get('completed_runs',0))
    status=state.get('status','unbekannt')
    st.write('**Laufstatus:**',status)
    if total:st.progress(min(1.,done/total),text=f'{done} / {total} Fälle abgeschlossen')
    if status in ('queued','running'):
        st.caption('Der Fortschritt aktualisiert sich automatisch. Ergebnisse erscheinen nach Abschluss direkt hier.')
    else:
        if status in ('failed','error','interrupted'):
            st.error(state.get('error','Der Lauf wurde nicht vollständig beendet.'))
            st.caption('Bereits gespeicherte native Fälle werden mit ihrem eigenen Prüfnachweis angezeigt. Der Auftrag bleibt als unvollständig gekennzeichnet.')
        else:st.success('Berechnung abgeschlossen · Prüfnachweise stehen bei jedem Ergebnisfall.')
        try:
            frame=result_loader.load_job_results(job_dir,REPO)
            if identity.endswith(':sensitivity_live'):
                render_sensitivity_frame(frame,identity,site)
            else:render_result_display(frame,site,identity)
        except (OSError,ValueError,KeyError) as exc:st.warning('Ergebnisdateien dieses Auftrags sind noch nicht vollständig lesbar: '+str(exc))
    with st.expander('Laufdetails und natives Protokoll'):
        st.json(state,expanded=False)
        if state.get('log_tail'):st.code(state['log_tail'],language=None)

def launch(plan,identity,slot,kind):
    plan['analysis_intent']={'type':kind,'label':kind,'optimization_count':plan['optimization_count']}
    response=jobs.submit_job(plan,REPO/'outputs_h2/gui_runs',sys.executable)
    st.session_state[identity+slot]=str(response)
    st.success('Berechnung gestartet. Fortschritt und Ergebnisse folgen unten.')

def run_controls(site,identity,sensitivity=False):
    prefix=':sens_' if sensitivity else ':'
    defaults=st.session_state.setdefault(identity+':sens_controls',defaults_for('sensitivity',site.profiles)) if sensitivity else st.session_state[identity+':settings']
    profiles=st.multiselect('Basis-Lieferprofile' if sensitivity else 'H₂-Lieferprofile',list(site.profiles),
        default=defaults.get('profiles',list(site.profiles)[:1]),format_func=lambda p:PROFILE_LABELS.get(p,p),key=identity+prefix+'profiles')
    scenarios=st.multiselect('Stromversorgungsszenarien',list(SCENARIO_LABELS),default=defaults.get('scenarios',['reference','red_monthly','red_hourly']),
        format_func=lambda s:SCENARIO_LABELS[s],key=identity+prefix+'scenarios')
    a,b=st.columns(2)
    solver=a.selectbox('Solver',['scipy-highs','gurobi','auto'],index=['scipy-highs','gurobi','auto'].index(defaults.get('solver','scipy-highs')),key=identity+prefix+'solver')
    both=b.checkbox('HiGHS und Gurobi vergleichen',value=defaults.get('compare_solvers',False),key=identity+prefix+'compare_solvers')
    if both:st.caption('Dieselben Eingaben werden mit beiden Solvern gerechnet. Gurobi benötigt eine ausreichende Lizenz.')
    defaults.update(profiles=profiles,scenarios=scenarios,solver=solver,compare_solvers=both)
    if sensitivity and len(profiles)>1:st.caption('Jedes Basisprofil erhält eine eigene OAT-Reihe. Zusätzliche Profilstufen werden ausschließlich mit unveränderten Basisparametern verglichen.')
    if site.runner_kind=='eu':st.caption('Synthetische Lieferprofile bei gleicher Jahresmenge; Produktion auch außerhalb der Lieferfenster. D2 enthält keine Feiertagskorrektur.')
    if not site.can_run:st.warning(site.run_limitation or 'Neue Läufe sind für diese Fallstudie nicht freigegeben.')
    return profiles,scenarios,solver,both

def render_sensitivity_frame(sens,identity,site):
    if sens.empty:
        st.info('Keine gespeicherten Sensitivitäten vorhanden.');return
    st.subheader('Ergebnisse der Sensitivitätsanalyse')
    # A categorical comparison uses original profile baselines, never numeric variants.
    profile_field=next((c for c in ('demand_profile','profile') if c in sens),None)
    numeric=list(sens.get('sensitivity_parameter',pd.Series(dtype=str)).dropna().unique())
    parameters=[p for p in numeric if p!='baseline']
    if profile_field and sens[profile_field].dropna().nunique()>1:parameters.append('h2_delivery_profile')
    if not parameters:
        st.dataframe(sens.drop(columns=['__result_copies'],errors='ignore'),hide_index=True,width='stretch');return
    parameter=st.selectbox('Berechneter Einfluss',parameters,format_func=lambda p:PARAMETER_LABELS.get(p,p),key=identity+':oat_view_parameter')
    if parameter!='h2_delivery_profile' and profile_field:
        profiles=sorted(sens[profile_field].dropna().astype(str).unique())
        key=identity+':oat_view_profile'
        if st.session_state.get(key) not in profiles:st.session_state.pop(key,None)
        profile=st.selectbox('Lieferprofil der Sensitivitätskurven',profiles,format_func=lambda p:PROFILE_LABELS.get(p,p),key=key)
        sens=sens[sens[profile_field].astype(str)==profile].copy()
        st.caption('Grafik und Download zeigen dieses Lieferprofil; die Profile werden nicht zu einer Nachfragekurve vermischt.')
    elif parameter=='h2_delivery_profile':
        if 'sensitivity_parameter' in sens:
            baseline=sens.sensitivity_parameter.eq('baseline')
            if 'case_id' in sens:baseline=baseline|sens.case_id.eq('baseline')
            sens=sens[baseline].copy()
        st.caption('Basisfälle mit gleicher Jahresmenge. Numerische OAT-Varianten gehören nicht in diesen Lieferprofilvergleich.')
    charts=['Sensitivitätskurve','Gruppierte Balken']
    if st.session_state.get(identity+':oat_chart') not in charts:st.session_state.pop(identity+':oat_chart',None)
    chart=st.selectbox('Sensitivitätsdarstellung',charts,key=identity+':oat_chart')
    metrics=metric_options(sens)
    metric=st.selectbox('Ergebnisgröße',metrics,format_func=metric_label,key=identity+':oat_metric')
    st.caption('Tages- und Stundenbetrieb eines einzelnen Falls: Analyse → Gespeicherte Ergebnisse → Ergebnisreihe. Dort sind auch alle Sensitivitätsfälle auswählbar.')
    if 'scenario_id' in sens:
        scenarios=sorted(sens.scenario_id.dropna().unique())
        chosen=st.multiselect('Szenarien in der Grafik',scenarios,default=scenarios,key=identity+':oat_scenarios')
        graph_frame=sens[sens.scenario_id.isin(chosen)].copy()
    else:graph_frame=sens.copy()
    if not graph_frame.empty:
        figure=None
        if parameter=='h2_demand_multiplier':demand_quantity_note()
        if parameter=='h2_delivery_profile':figure=plotting.profile_comparison_figure(graph_frame,metric=metric,chart_type='Gruppierte Balken' if chart=='Gruppierte Balken' else 'Liniendiagramm')
        elif chart=='Sensitivitätskurve':figure=plotting.oat_curve_figure(graph_frame,parameter=parameter,metric=metric)
        else:
            graph_frame=graph_frame[graph_frame.sensitivity_parameter.isin([parameter,'baseline'])]
            if len(graph_frame)>12:
                st.info('Für gruppierte Balken höchstens 12 Fälle wählen oder die Sensitivitätskurve verwenden.')
            else:figure=plotting.comparison_figure(graph_frame,metric=metric,chart_type='Gruppierte Balken',group_by='scenario_id')
        if figure is not None:remember_figure(figure,graph_frame,'Sensitivität')
    st.dataframe(sens.drop(columns=['__result_copies'],errors='ignore'),hide_index=True,width='stretch')
    st.download_button('Gespeicherte Sensitivitätstabelle herunterladen',sens.to_csv(index=False).encode('utf-8-sig'),'sensitivities.csv','text/csv',key=identity+':sens_download')
    show_saved_origins(sens,'Ausführungen und Herkunft der Versuchsreihe')
    with st.expander('Einzelnen Sensitivitätsfall und Prüfnachweis öffnen'):
        row=pick_result(sens,identity+':sens_details')
        if row is not None:
            bundle=result_loader.load_result_directory(result_path(row),REPO)
            render_metrics(bundle);show_validation(bundle)
            st.button('Tagesbetrieb dieses Falls in Analyse öffnen',key=identity+':daily_analysis',
                      on_click=open_daily_analysis,args=(site,row))

def stored_sensitivities(registry,identity,site):
    sens=result_loader.load_sensitivity_comparisons(registry,site.study_id,site.site_id)
    if sens.empty:
        st.info('Keine gespeicherten Sensitivitäten vorhanden.');return
    field='__collection_id' if '__collection_id' in sens else '__collection'
    families={str(cid):group for cid,group in sens.groupby(field,sort=False)}
    def label(cid):
        return sensitivity_collection_label(families[cid])
    key=identity+':oat_collection'
    if st.session_state.get(key) not in families:st.session_state.pop(key,None)
    selected=st.selectbox('Gespeicherte Versuchsreihe',list(families),format_func=label,key=key)
    st.caption('Nur vollständig identische Versuchsreihen werden zusammengefasst. Originaldateien und eigene Prüfnachweise bleiben erhalten.')
    render_sensitivity_frame(families[selected].copy(),identity,site)

def sources_view(registry,study,site,identity):
    st.write('**Modellstatus:**',study.role)
    st.dataframe(year_table(site),hide_index=True,width='stretch')
    sources=result_loader.describe_case_sources(registry,site.study_id,site.site_id)
    human={'source':'Quelle','source_url':'Quellenlink','year':'Jahr','note':'Hinweis','method':'Methode','description':'Beschreibung','value':'Wert','unit':'Einheit'}
    def readable(value,prefix=''):
        rows=[]
        if isinstance(value,dict):
            for k,v in value.items():
                label=human.get(k,k.replace('_',' '));key=(prefix+' · '+label).strip(' ·')
                if isinstance(v,dict):rows.extend(readable(v,key))
                elif isinstance(v,(list,tuple)):rows.append({'Angabe':key,'Wert':'; '.join(map(str,v))})
                else:rows.append({'Angabe':key,'Wert':str(v)})
        else:rows.append({'Angabe':prefix or 'Beschreibung','Wert':str(value)})
        return rows
    for key,label in [('weather','Wetter'),('electricity_price','Strompreise'),('emission_factors','Emissionsfaktoren'),('technical_costs','Technische Kosten'),('wacc','WACC'),('demand','H₂-Nachfrage')]:
        with st.expander(label,expanded=key in ('weather','electricity_price','demand')):
            rows=readable(sources.get(key,{}))
            st.dataframe(pd.DataFrame(rows),hide_index=True,width='stretch')
    with st.expander('Basiskonfiguration und Solver-Verfügbarkeit'):
        st.dataframe(native_parameter_table(site),hide_index=True,width='stretch')
        st.caption('Basiswerte bleiben unverändert. Sensitivitätswerte werden an den vorhandenen nativen Runner übergeben.')
        if st.button('Solver-Verfügbarkeit und Gurobi-Lizenz prüfen',key=identity+':probe'):st.json(model_adapter.probe_solvers(REPO))
    with st.expander('Fallstudienstatus und Dokumentation'):
        st.dataframe(pd.DataFrame([{'Standort':x.label,'Dokumentiert':x.documentation_path.is_file(),'Inputs vorhanden':all(i.exists for i in x.profiles.values()),'Neue Läufe freigegeben':x.can_run,'Historisch':x.historical} for x in study.sites.values()]),hide_index=True,width='stretch')
        st.markdown(site.documentation_path.read_text(encoding='utf-8'))
        for profile,ref in site.profiles.items():st.write('**'+profile+'**',ref.description)
    with st.expander('Vollständige Quellenverträge, Datenfluss und Hashnachweise'):
        st.json(sources)
        st.code(sources.get('dataflow',{}),language=None)
        for profile,ref in site.profiles.items():
            st.write('**'+profile+'**');st.json(ref.metadata,expanded=False)
    with st.expander('Validierungsnachweis eines gespeicherten Falls'):
        filtered=saved_result_filters(result_table(registry,site),identity+':validation')
        row=pick_result(filtered,identity+':validation')
        if row is not None:show_validation(result_loader.load_result_directory(result_path(row),REPO))

def comparison_view(registry):
    st.caption('Gespeicherte Analyse- und Sensitivitätsfälle gezielt gegenüberstellen. Es startet keine Berechnung.')
    frames=[]
    for sid,study in registry.studies.items():
        for tid in study.sites:
            for frame in [result_loader.load_registered_results(registry,sid,tid),result_loader.load_sensitivity_comparisons(registry,sid,tid)]:
                if not frame.empty:
                    frame=frame.copy();frame['study_id']=sid;frame['study_label']=study.label
                    frames.append(frame)
    if not frames:
        st.info('Keine gespeicherten Vergleichsfälle.');return
    comp=pd.concat(frames,ignore_index=True)
    comp['__choice_id']=[str(r.study_id)+':'+str(r.site_id)+':'+str(r.get('__collection_id',r.get('source_label','')))+':'+saved_case_id(r) for _,r in comp.iterrows()]
    comp=comp.drop_duplicates('__choice_id')
    studies=st.multiselect('Fallstudien im Vergleich',list(registry.studies),default=list(registry.studies),format_func=lambda k:registry.studies[k].label,key='comparison_studies')
    comp=comp[comp.study_id.isin(studies)]
    if comp.empty:return
    labels={r['__choice_id']:r.study_label+' · '+saved_case_label(r) for _,r in comp.iterrows()}
    selected=st.multiselect('Gespeicherte Ergebnisfälle nebeneinander vergleichen',list(labels),default=[],format_func=lambda k:labels[k],key='comparison_cases_v2')
    chosen=comp[comp['__choice_id'].isin(selected)].copy()
    if chosen.empty:
        st.info('Vergleichsfälle auswählen; anschließend Kennzahl, Diagrammtyp und Gruppierung festlegen.');return
    context,warnings=result_loader.comparison_context(registry,chosen)
    for warning in warnings:st.warning(warning)
    metric=st.selectbox('Vergleichskennzahl',metric_options(chosen),format_func=metric_label,key='comparison_metric')
    chart=st.selectbox('Vergleichsdiagramm',['Balkendiagramm','Liniendiagramm','Gruppierte Balken','Gestapelte Kosten'],key='comparison_chart_type')
    groups=[None,*[c for c in ('scenario_id','site_id','demand_profile','profile','solver_name','study_id') if c in chosen]]
    group=st.selectbox('Gruppierung',groups,format_func=lambda x:'Keine' if x is None else x.replace('_',' '),key='comparison_group')
    if len(chosen)>12:st.info('Für eine lesbare Grafik höchstens 12 Fälle auswählen. Tabelle und Export enthalten die gesamte Auswahl.')
    else:
        figure=plotting.cost_components_figure(chosen,title='Kostenvergleich') if chart=='Gestapelte Kosten' else plotting.comparison_figure(chosen,metric=metric,chart_type=chart,group_by=group,title='Ausgewählte Vergleichsfälle')
        remember_figure(figure,chosen,'Vergleich')
        with st.expander('Fallnamen der Grafik'):st.dataframe(plotting.case_label_table(chosen),hide_index=True,width='stretch')
    st.dataframe(chosen.drop(columns=['__result_copies'],errors='ignore'),hide_index=True,width='stretch')
    st.session_state['comparison_export']=chosen.to_csv(index=False).encode('utf-8-sig')
    with st.expander('Jahre, Bezugsbasen und Vergleichbarkeit'):st.dataframe(context.astype(str),hide_index=True,width='stretch')
    show_saved_origins(chosen,'Gespeicherte Ausführungen der Vergleichsfälle')

def export_view(registry,site,identity):
    available=analysis_result_table(registry,site,identity)
    filtered=saved_result_filters(available,identity+':export')
    st.download_button('Genau diese gefilterte Ergebnistabelle (CSV)',filtered.to_csv(index=False).encode('utf-8-sig'),'h2_results.csv','text/csv',key=identity+':export_results')
    st.dataframe(filtered.drop(columns=['__result_copies'],errors='ignore'),hide_index=True,width='stretch')
    row=pick_result(filtered,identity+':export')
    if row is not None:
        path=result_path(row)
        st.download_button('Native Ergebnisdateien (ZIP)',zip_result(path),path.name+'_native_results.zip','application/zip',key=identity+':native_zip')
        st.download_button('Native Metadaten (JSON)',(path/'run_metadata.json').read_bytes(),'run_metadata.json','application/json',key=identity+':native_json')
        report=result_loader.validation_for_result(path,REPO)
        st.download_button('Validierungsnachweis (JSON)',json.dumps(report,ensure_ascii=False,indent=2).encode('utf-8'),'validation_evidence.json','application/json',key=identity+':validation_json')
    sens=result_loader.load_sensitivity_comparisons(registry,site.study_id,site.site_id)
    if not sens.empty:st.download_button('Alle gespeicherten Sensitivitätsfälle dieses Standorts (CSV)',sens.to_csv(index=False).encode('utf-8-sig'),'all_sensitivities.csv','text/csv',key=identity+':export_sensitivities')
    if 'comparison_export' in st.session_state:st.download_button('Ausgewählte Vergleichsfälle (CSV)',st.session_state['comparison_export'],'comparison.csv','text/csv',key='export_comparison')
    figure=st.session_state.get('last_figure_export')
    if figure:
        st.caption('Zuletzt angezeigte Grafik: '+figure['label'])
        for extension,mime in [('png','image/png'),('svg','image/svg+xml')]:
            st.download_button('Grafik als '+extension.upper(),figure[extension],'h2_figure.'+extension,mime,key='export_figure_'+extension)
        st.download_button('Daten der zuletzt angezeigten Grafik (CSV)',st.session_state['last_chart_data'],'figure_data.csv','text/csv',key='export_figure_data')
    else:st.caption('Eine Grafik in Analyse, Sensitivitätsanalyse oder Vergleich anzeigen; danach hier als PNG/SVG exportieren.')

def main():
    st.set_page_config(page_title='H₂ | Forschungsmodell',page_icon='🔬',layout='wide')
    st.markdown('<style>.stMainBlockContainer{padding-top:1.5rem} h1{letter-spacing:-.02em} [data-testid="stSidebar"] h1{font-size:1.3rem}</style>',unsafe_allow_html=True)
    try:registry=load_registry(REPO)
    except (OSError,ValueError,KeyError) as exc:
        st.error('Fallstudien-Registry kann nicht geladen werden: '+str(exc));st.stop()
    st.sidebar.title('H₂ Forschungsmodell')
    if st.session_state.get('navigation') not in PAGES:st.session_state['navigation']='Analyse'
    page=st.sidebar.radio('Bereich',PAGES,key='navigation')
    st.sidebar.caption('Einstellungen → Berechnen → Ergebnisse auf derselben Seite')
    st.title(page)
    a,b=st.columns(2)
    study_id=a.selectbox('Fallstudie',list(registry.studies),format_func=lambda k:registry.studies[k].label,key='study_selection')
    study=registry.studies[study_id]
    if not study.sites:
        st.info('Diese Fallstudie ist dokumentiert; Eingaben und Runner sind noch nicht registriert.');return
    site_id=b.selectbox('Standort',list(study.sites),format_func=lambda k:study.sites[k].label,key='site:'+study_id)
    site=registry.get_site(study_id,site_id);identity=study_id+':'+site_id
    st.session_state.setdefault(identity+':settings',defaults_for('scenario_comparison',site.profiles))
    if site.historical:st.info('Historische Namibia-Fallstudie: TMY-Wetterbasis und dokumentierte Proxies. Vergleichbarkeit mit EU 2024 ist eingeschränkt.')
    for warning in registry.warnings:st.sidebar.caption(warning)
    if page=='Analyse':
        source=st.radio('Analysemodus',['Neue Berechnung','Gespeicherte Ergebnisse'],horizontal=True,key=identity+':analysis_source')
        if source=='Neue Berechnung':
            st.caption('Kostenoptimale Anlagen und Jahresbetrieb für die ausgewählten Fälle berechnen.')
            profiles,scenarios,solver,both=run_controls(site,identity)
            count=len(profiles)*len(scenarios)*(2 if both else 1)
            st.caption(f'{len(profiles)} Lieferprofil(e) × {len(scenarios)} Szenario/Szenarien'+(' × 2 Solver' if both else '')+f' = {count} neue Modellläufe.')
            with st.expander('Basisparameter und Jahresrollen'):st.dataframe(native_parameter_table(site),hide_index=True,width='stretch');st.dataframe(year_table(site),hide_index=True,width='stretch')
            if st.button('Berechnen',type='primary',key=identity+':analysis_start',disabled=not site.can_run or count==0):
                try:launch(build_analysis_plan(site,profiles,scenarios,solver,[],both),identity,':analysis_job_dir','analysis')
                except (ValueError,TypeError,KeyError,OSError) as exc:st.error(str(exc))
            if st.session_state.get(identity+':analysis_job_dir'):inline_job_results(st.session_state[identity+':analysis_job_dir'],site,identity+':analysis_live')
            with st.expander('Frühere GUI-Aufträge und Status'):
                previous=jobs.list_jobs(REPO/'outputs_h2/gui_runs')
                if previous:st.dataframe(pd.DataFrame(previous).astype(str),hide_index=True,width='stretch')
        else:
            available=saved_result_filters(analysis_result_table(registry,site,identity),identity+':results')
            render_result_display(available,site,identity)
    elif page=='Sensitivitätsanalyse':
        mode=st.radio('Sensitivitätsmodus',['Neue Sensitivität','Gespeicherte Versuchsreihe'],horizontal=True,key=identity+':sensitivity_source')
        if mode=='Neue Sensitivität':
            profiles,scenarios,solver,both=run_controls(site,identity,sensitivity=True)
            variants=sensitivity_editor(identity,site);st.session_state[identity+':variants']=variants
            levels=st.session_state.get(identity+':profile_levels',[])
            selected=st.session_state.get(identity+':oat_parameters',[])
            category='h2_delivery_profile' in selected
            extra=[p for p in levels if p not in profiles] if category else []
            count=(len(profiles)*(1+len(variants or []))+len(extra))*len(scenarios)*(2 if both else 1)
            valid=variants is not None and bool(variants or category) and bool(profiles and scenarios) and (not category or bool(levels) and len(set(profiles+levels))>=2)
            st.caption(f'{count} neue Modellläufe: Basis + einzelne Parameteränderungen; zusätzliche Lieferprofile nur mit unveränderten Basiswerten.')
            if variants:
                with st.expander('An den Runner übergebene Einzelvarianten'):st.dataframe(pd.DataFrame(variants),hide_index=True,width='stretch')
            if category and not valid:st.info('Für den Lieferprofilvergleich mindestens zwei verschiedene Profile einschließlich Basis wählen.')
            if st.button('Sensitivität berechnen',type='primary',key=identity+':sensitivity_start',disabled=not site.can_run or not valid):
                try:
                    plan=sensitivity_design.build_oat_profile_plan(REPO,site,profiles,scenarios,solver,variants=variants or [],profile_levels=levels if category else [],compare_solvers=both)
                    if int(plan['optimization_count'])!=count:raise ValueError('Sichtbarer Umfang stimmt nicht mit dem nativen Plan überein.')
                    launch(plan,identity,':sensitivity_job_dir','sensitivity')
                except (ValueError,TypeError,KeyError,OSError) as exc:st.error(str(exc))
            if st.session_state.get(identity+':sensitivity_job_dir'):inline_job_results(st.session_state[identity+':sensitivity_job_dir'],site,identity+':sensitivity_live')
        else:stored_sensitivities(registry,identity,site)
    elif page=='Vergleich':comparison_view(registry)
    elif page=='Quellen':sources_view(registry,study,site,identity)
    elif page=='Export':export_view(registry,site,identity)
    manual=REPO/'GUI_BEDIENUNGSANLEITUNG.md'
    if manual.is_file():st.sidebar.download_button('GUI-Anleitung (Markdown)',manual.read_bytes(),manual.name,'text/markdown',key='download_GUI_BEDIENUNGSANLEITUNG.md')
    previous_pdf=REPO/'GUI_BEDIENUNGSANLEITUNG.pdf'
    if previous_pdf.is_file():st.sidebar.download_button('Frühere GUI-Anleitung (PDF)',previous_pdf.read_bytes(),previous_pdf.name,'application/pdf',key='download_GUI_BEDIENUNGSANLEITUNG.pdf')
    st.sidebar.caption('Eine Modellimplementierung · native Runner · getrennte Jahres- und Quellenrollen')

if __name__=='__main__':main()
