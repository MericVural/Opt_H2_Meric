"""Explicit GUI analysis scope; no optimization or scientific parameter logic."""
ANALYSES = {
 'scenario_comparison': {'label':'Stromversorgungsszenarien vergleichen',
   'goal':'Vergleichen, wie die Stromversorgungsregeln Anlagen, Jahresbetrieb und Wasserstoffkosten beeinflussen.',
   'changes':'Stromversorgungsszenario', 'fixed':'Standort, Lieferprofil, Jahresmenge und technische/finanzielle Basisannahmen',
   'action':'Szenarienvergleich starten'},
 'demand_comparison': {'label':'H₂-Lieferprofile vergleichen',
   'goal':'Untersuchen, wie die zeitliche Pflichtlieferung bei gleicher Jahresmenge Kosten und Speicherbedarf verändert.',
   'changes':'Zeitlicher Verlauf der H₂-Lieferung', 'fixed':'Standort, Stromversorgungsszenario, Jahresmenge und Basisannahmen',
   'action':'Lieferprofilvergleich starten'},
 'sensitivity': {'label':'Einzelfaktor-Sensitivität untersuchen',
   'goal':'Je Variante einen Parameter ändern, etwa die H₂-Jahresnachfrage, und Anlagen sowie Betrieb mit dem passenden unveränderten Fall vergleichen.',
   'changes':'Je Variante genau eine ausgewählte Parameterfamilie', 'fixed':'Alle übrigen Parameter und Stundeninputs; eigene unveränderte Basis je Profil/Szenario',
   'action':'Sensitivitätsanalyse starten'},
 'single_case': {'label':'Einen Modellfall berechnen',
   'goal':'Kostenoptimale Anlagen und Jahresbetrieb für einen Standort, ein Lieferprofil und ein Szenario bestimmen.',
   'changes':'Keine Sensitivitätsparameter', 'fixed':'Dokumentierte Basisannahmen des ausgewählten Falls',
   'action':'Modellfall starten'},
 'solver_comparison': {'label':'HiGHS und Gurobi vergleichen',
   'goal':'Dieselben Modelleingaben mit beiden Solvern lösen und Kosten, Laufzeit und mögliche alternative Optima prüfen.',
   'changes':'Solver', 'fixed':'Standort, Lieferprofil, Szenario und sämtliche Modelleingaben',
   'action':'Solververgleich starten'},
 'saved_results': {'label':'Gespeicherte Ergebnisse auswerten',
   'goal':'Vorhandene Ergebnisse auswählen, darstellen und exportieren.',
   'changes':'Angezeigte Ergebnisfälle und Darstellungen', 'fixed':'Gespeicherte Modellresultate; keine neue Optimierung',
   'action':'Gespeicherte Ergebnisse öffnen'},
}
SCENARIO_LABELS={'reference':'S0 · Referenz', 'red_monthly':'S1 · monatliche Zuordnung',
 'red_hourly':'S2 · stündliche Zuordnung', 'off_grid':'S3 · ohne Netzanschluss'}
PROFILE_LABELS={'D0':'D0 · Lieferung rund um die Uhr',
 'D1':'D1 · Lieferung täglich 08–20 Uhr', 'D2':'D2 · Lieferung Mo–Fr 08–20 Uhr'}

def selection_errors(kind,profiles,scenarios,variants):
    if kind not in ANALYSES:return ['Analyseziel ist unbekannt.']
    if kind=='saved_results':return []
    errors=[]
    if not profiles:errors.append('Mindestens ein H₂-Lieferprofil auswählen.')
    if not scenarios:errors.append('Mindestens ein Stromversorgungsszenario auswählen.')
    if kind in ('single_case','scenario_comparison','solver_comparison') and len(profiles)>1:
        errors.append('Für dieses Analyseziel genau ein Lieferprofil auswählen.')
    if kind in ('single_case','demand_comparison','solver_comparison') and len(scenarios)>1:
        errors.append('Für dieses Analyseziel genau ein Szenario auswählen.')
    if kind=='scenario_comparison' and len(scenarios)<2:
        errors.append('Für den Szenarienvergleich mindestens zwei Szenarien auswählen.')
    if kind=='demand_comparison' and len(profiles)<2:
        errors.append('Für den Lieferprofilvergleich mindestens zwei Profile auswählen.')
    if kind=='sensitivity' and not variants:
        errors.append('Zuerst gültige Sensitivitätsparameter und Werte festlegen.')
    return errors

def request_scope(kind,profiles,scenarios,variants=None):
    errors=selection_errors(kind,profiles,scenarios,variants)
    if errors:raise ValueError(' '.join(errors))
    if kind=='saved_results':return {'profiles':[],'scenarios':[],'variants':[], 'compare_solvers':False,'optimization_count':0}
    active=list(variants) if kind=='sensitivity' else []
    both=kind=='solver_comparison'
    return {'profiles':list(profiles),'scenarios':list(scenarios),'variants':active,
            'compare_solvers':both,'optimization_count':len(profiles)*len(scenarios)*(1+len(active))*(2 if both else 1)}

def defaults_for(kind,profile_ids):
    profiles=list(profile_ids)
    return {'kind':kind,'profiles':profiles if kind=='demand_comparison' else profiles[:1],
        'scenarios':['reference','red_monthly','red_hourly'] if kind in ('scenario_comparison','sensitivity') else ['reference'],
        'solver':'scipy-highs'}
