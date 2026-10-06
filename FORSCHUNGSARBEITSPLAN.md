# Forschungsarbeitsplan

**Verbindlicher roter Faden · Stand: 6. Oktober 2026.**

Dieser Plan beantwortet: Was untersuchen wir, wo stehen wir und was folgt?
Allgemeine Gleichungen stehen in [MODELL_UND_METHODIK.md](MODELL_UND_METHODIK.md),
konkrete Standortannahmen und Ergebnisse in den [Fallstudien](fallstudien/README.md).
Bei jeder fachlichen Erweiterung werden dieser Status und das zuständige
Fallstudiendokument zusammen aktualisiert.

**Dokumentationsregel (Nutzerentscheidung vom 04.10.2026):** Nach jedem
Arbeitsschritt werden die betroffenen Markdown-Dateien aktualisiert. Die PDF
wird künftig zu größeren Meilensteinen oder auf ausdrücklichen Wunsch
aktualisiert. Eine vollständige Erklärung des Modells kann bei Bedarf aus
Methodik, dokumentierten Entscheidungen, Quellen, Code und gespeicherten
Ergebnissen erstellt werden.

## 1. Forschungsrahmen

**Arbeitstitel:** Kostenminimale Auslegung der Wasserstoffproduktion unter
RED-III-Stromversorgungskriterien und zeitvariablen Standortbedingungen.

**Forschungsfrage:** Wie beeinflussen RED-III-Stromversorgungskriterien,
zeitvariable Strompreise und standortabhängige Finanzierungsbedingungen die
kostenminimale Auslegung und die Wasserstoffgestehungskosten einer
Elektrolyseanlage, und wie robust sind diese Ergebnisse gegenüber
unterschiedlichen zeitlichen H2-Nachfrageprofilen?

Unterfragen:

1. Wie verändern die Korrelationsregeln PV-, Wind-, Elektrolyseur-, Kompressor-
   und H2-Speicherkapazität?
2. Wie unterscheiden sich LCOH, Volllaststunden, Netzbezug, Abregelung und Emissionen?
3. Welche technischen und wirtschaftlichen Parameter bestimmen diese Unterschiede?
4. Wie unterscheiden sich die beiden EU-Standorte bei gleicher Technologie und Jahresmenge?
5. Wie wirkt eine zeitlich gebündelte H2-Abnahme auf Produktion, Speicherung und Kosten?
6. Wie unterscheiden sich physische Netzemissionen und regulatorische Stromzuordnung?
7. Wie verändern kleinere und größere H2-Jahresmengen Kosten, Auslegung und Betrieb bei unverändertem Lieferprofil?

### Ziel und methodischer Beitrag

Die Arbeit entwickelt das ursprüngliche Energiesystemmodell zu einem
übertragbaren H2-Optimierungsmodell weiter. Der Beitrag liegt in der expliziten
Übersetzung ausgewählter regulatorischer Stromversorgungskriterien in
prüfbare Mengenbedingungen und deren technoökonomischer Quantifizierung.
Zeitlich zusammenpassende Wetter-, Marktpreis- und Erzeugungsdaten,
standortbezogene Finanzierung und Nachfrageprofile ergänzen den Regelvergleich.
Die technische Umsetzung dient dieser Methode; sie ist nicht allein das Forschungsziel.

Die methodischen Arbeiten umfassen Literaturscreening, Prüfung der EU-Primärquellen,
Definition quantifizierbarer Kriterien und Systemgrenzen, Parametrisierung,
Optimierung, unabhängige Validierung, Sensitivität sowie Literaturvergleich.

### Umfang für 15 CP

Pro Lauf wird eine Anlage an einem Einzelstandort optimiert. Aktuell werden zwei
Standorte unabhängig verglichen; das Modell bleibt mit passenden Daten auf weitere
Standorte übertragbar. Es gibt kein Transport- oder Verbundmodell zwischen ihnen.

Komponenten: PV, Onshore-Wind, Netzbezug, PEM-Elektrolyseur, Kompressor,
Druckspeicher und vorgegebene stündliche H2-Abnahme.
Funktionelle Einheit: **1 kg gasförmiger H2 am Ausgang des 300-bar-Druckspeichers**.
Elektrolyse, Verdichtung, Wasser- und Kostenbedarf gehören zur Systemgrenze.

Ausgeschlossen bleiben Ammoniaksynthese, Luftzerlegung, NH3-Transport,
internationaler H2-Handel, globale simultane Standortoptimierung, detaillierte
Degradation/Stackersatz, vollständige LCA und vollständiges Vertrags-/Zertifikatemodell.
Batterie, weitere Wetterjahre oder zusätzliche Standorte sind optionale Erweiterungen.

„Unter Einhaltung von RED III“ meint die **im Modell abgebildeten
Stromversorgungskriterien**, keinen vollständigen RFNBO-Zertifizierungsnachweis.

## 2. Bisheriger Entwicklungs- und Validierungsstand

Die Schritte 1–17 sind die abgeschlossene Namibia-Entwicklung vom September 2026.
Sie werden nicht als neue Aufgabenliste wiederholt.

| Phase | Erarbeiteter Stand |
|---|---|
| Schritte 1–5 | Umgebung, Konfiguration, Stundenformat, H2-Basiskern und Einzelrunner |
| Schritte 6–7 | Koordinatenpipeline, Profile, kleine Testläufe und vollständiger Referenzlauf |
| Schritte 8–11 | RED-Prüfmodul, monatliche/stündliche Korrelation und zwei Emissionsauswertungen |
| Schritte 12–15 | S0/S1/S2-Runner, Grafiken, Sensitivitäten und unabhängige Abnahme |
| Schritte 16–17 | Methodiktext und Interpretation der Namibia-Ergebnisse |

Gurobi wurde für kleine Modelle, SciPy/HiGHS für die vollständigen Jahresfälle
verwendet. Die historische Abnahme dokumentiert **163 bestandene automatisierte
Tests und 61 bestandene unabhängige Ergebnisprüfungen**; 48 Sensitivitätsläufe
wurden ausgeführt. Diese Zahlen beziehen sich auf den damaligen Namibia-Stand
und ersetzen keine Abnahme neuer EU-Daten oder künftiger Codeänderungen.

Der Kern unterstützt bereits stündlich variable Preise, Netzfaktoren und Nachfrage.
Die damalige Fallstudie nutzte überwiegend konstante Länder-/Regionalproxies.
Die Emissionskennzahlen und ihre Eingaben können inzwischen getrennte Faktoren verwenden.
Historische Eingaben ohne regulatorische Zusatzspalte nutzen ausdrücklich
`legacy_shared_factor`; der neue EU-Vertrag verlangt beide Quellen. Details und Entwicklungsschritte bleiben in der
[Namibia-Fallstudie](fallstudien/FALLSTUDIE_NAMIBIA.md) rekonstruierbar.

## 3. Fallstudienübersicht

| Fallstudie | Rolle | Status | Detaildokument |
|---|---|---|---|
| Namibia | Historischer Entwicklungs-/Validierungsfall | S0/S1/S2 und Sensitivitäten gerechnet, abgenommen und interpretiert | [Namibia](fallstudien/FALLSTUDIE_NAMIBIA.md) |
| Hamburg–Moorburg / Huelva–La Rábida | Aktuelle vergleichende Untersuchung | Schritte 19–25 und gemeinsamer Namibia-Vergleich archiviert; Nachfragemengenanalyse mit 90 Jahresfällen abgeschlossen (Abschnitt 9); aktuelle fünfteilige GUI-Bedienrevision dokumentiert (Abschnitt 10); Manuskriptarbeit zurückgestellt | [Hamburg und Andalusien](fallstudien/FALLSTUDIE_HAMBURG_ANDALUSIEN.md) |

Weitere Fälle werden hier und im Fallstudienindex registriert. Ihre eigenen
Annahmen stehen jeweils in einer zusätzlichen Datei unter `fallstudien/`.

## 4. Abgenommene Forschungsphase: Schritte 18–25

Für Schritte 19–25 ist Hamburg/Huelva die aktive Fallstudie. Ein Folgeschritt
beginnt fachlich nach Erfüllung des vorherigen Abnahmekriteriums. Als technische
Voraussetzung wurde die Faktortrennung aus Schritt 22 mit Nutzerautorisierung
bereits während Schritt 19 vorgezogen. Diese frühere Teilumsetzung war noch keine
Abnahme von Schritt 22; Ortsmonate und unabhängige Prüfung sind inzwischen umgesetzt.
Konkrete Quellen, Koordinaten, Preis-/Faktor-/WACC-Werte und Versuchsparameter
stehen ausschließlich ausführlich im EU-Fallstudiendokument.

### Schritt 18 – Methodik und Datenentscheidungen

**Status: methodisch abgeschlossen am 2. Oktober 2026; aktive Zeitbasis am 03.10.2026 auf 2024 umgestellt.**
Ziel: einen vergleichbaren Standort-, Kalender-, Kosten-, Emissions- und
Finanzierungsvertrag festlegen. Standorte, Quellenstrategie, RED-Regeln,
Nachfrageformen und Sensitivitätsumfang sind dokumentiert.
Betroffene Teile: Fallstudiendesign, Datenvertrag und Entwurfs-JSON.

Abnahme: Entscheidungen belegt, Quellenstichproben nachvollziehbar, offene
Datenfreigaben benannt. Die 38/38 Entwurfsprüfungen betreffen den ursprünglichen
2023-Entwurf. Die damalige JSON wurde zunächst auf 2025 und anschließend auf tatsächliches 2024 umgestellt; die alten Prüfungen
bleiben als 2023-Historie erhalten. Die Design-JSON wird vom Solver nicht automatisch eingelesen.
Weder vollständige EU-Jahresdaten noch EU-Optimierungsergebnisse wurden damit freigegeben.

### Schritt 19 – Historische Standortdaten aufbereiten

**Status: ABGENOMMEN für die aktive historische 2024-Basis am 03.10.2026.**
Auf ausdrücklichen Nutzerwunsch wurden tatsächliche Wetter-/Preisquellen 2024
neu beschafft; frühere 2025-Daten werden nicht umetikettiert. Beide Standorte
besitzen alle 8.784 Stunden einschließlich 29. Februar und Zeitumstellungen.
Negative Preise bleiben erhalten, nationale HVPI-Jahresmittel 2023/2024 bringen
die Preise auf die gemeinsame reale Geldbasis EUR 2023.

Die konstante betriebliche Referenz stammt ebenfalls aus 2024: EEA-Bruttofaktor
(frühe Schätzung), eigene näherungsweise Eurostat-GEP/NEP-Umrechnung,
DE 304,7 / ES 128,8 kg CO2e/MWh nationale Nettoerzeugung. Die frühere zeitliche
Übertragung 2024→2025 entfällt. Nicht belegter Revisionsgleichstand, nationale
Erzeugung statt Verbrauchsfluss und ES einschließlich Inseln→Huelva bleiben
ausdrücklich begrenzende Annahmen. Keine behauptete stündliche Intensitätsmessung.

Alle sechs vollständigen D0/D1/D2-Inputs enthalten separate betriebliche und
regulatorische Quellenverträge mit CSV-SHA-256. Regulatorische Tabellenwerte
2020 bleiben normative Rechenreferenzen mit Aktualisierungsvorbehalt;
eine neuere operative Direktreferenz ersetzt sie nicht automatisch.
Die historische eigene dynamische Rekonstruktion ist optional offen, ihre
fehlenden Technologieparameter sind keine Datenlücke der statischen Jahresbasis.

Der Kern unterstützt explizite historische Kalenderannualisierung. Für das
vollständige 2024 gilt 8.784 / 8.784 = 1; keine Streichung des Schalttags.
Die feste Jahreslieferung bleibt 3.650.000 kg H2. Legacy-Fälle behalten ihre
365-Tage-Referenz. 583 Modell-/Datentests und 6 Unterprüfungen bestanden. Alle sechs echten Volljahreseingaben sind
gegen Kalender, Quellen, Standorte, Nachfrage und Annualisierung geprüft.
Kleine Solverfälle waren Softwareprüfungen; bei dieser Schritt-19-Abnahme war noch keine EU-Jahresoptimierung ausgeführt. Die späteren sechs D0-Jahresfälle sind unter Schritt 23 dokumentiert.

Belege: [statische 2024-Freigabe](outputs_h2/eu_case_studies/historical_2024/step19/static_factors_20261003/released_inputs/static_factor_release_report.json),
[Volljahresprüfung](outputs_h2/eu_case_studies/historical_2024/step19/validation/full_year_input_preflight.json),
[Jahresrollenprüfung](outputs_h2/eu_case_studies/historical_2024/step19/parameter_consistency_review/PARAMETERKONSISTENZ_2024.md),
[Faktorkatalog](input_data/h2_eu_static_factors.json) und
[erklärende PDF](output/pdf/Schritt_19_Wissenschaftlicher_Modellausbau.pdf).
Die unveränderten 2025-Archive und exakten alten Dokument-/Design-Snapshots
bleiben als nachvollziehbare Entwicklungshistorie erhalten.

### Schritt 20 – Standortbezogenen WACC anwenden

**Status: IMPLEMENTIERT UND ABGENOMMEN am 03.10.2026.**
`eu_site_configuration.py` lädt die Standortwahl ausdrücklich; beide Runner
aktivieren sie über `--eu-site`. Die verwendeten Raten, Quellen, das Finanzierungsjahr
2021 und der Designhash werden in Metadaten gesichert. Technik/Kosten und
Legacy-Standards werden durch die Auswahl nicht still geändert.

DE: PV/Wind 1,30 %, PEM/Kompressor/Speicher 3,30 %.
ES: PV 3,60 %, Wind 3,10 %, PEM/Kompressor/Speicher 5,35 %.
Reale Nachsteuerbenchmarks aus IRENA 2023 werden als effektive Annuitätszinssätze
verwendet. `r_H2=(r_PV+r_Wind)/2+0,02` ist die festgelegte Risikoübertragung
aus Brandt. Kein zweiter Inflationsabzug oder zusätzlicher Steuerschutz.
2021→2024 bleibt ausdrücklich ein zeitlicher Finanzierungsproxy. Die Prüfung
neuerer 2024-Quellen findet belegte Alternativen, aber keinen freigegebenen exakt
vergleichbaren Vierersatz realer Nachsteuerwerte: IRENA zeigt Karten ohne genaue
Länderzellen; EurObserv’ER-Zahlen besitzen eine ungeklärte Real-/Nominaldefinition.
Keine Behauptung, dass es keine neueren Daten gibt; keine still erfundene Umrechnung.

Abnahme: Komponentenraten, Annuitäten, Länderzuordnung, unveränderte Legacy-
Defaults sowie S0/S1/S2-Gleichheit und Runner-Weitergabe gezielt geprüft.

### Schritt 21 – Zeitvariable H2-Abnahmeprofile

**Status: IMPLEMENTIERT UND DATENSEITIG ABGENOMMEN am 03.10.2026.**
`eu_demand_profiles.py` erzeugt D0/D1/D2 aus dem tatsächlichen Ortskalender.
Für beide Standorte: 8.784 / 4.392 / 3.144 aktive Lieferstunden und jeweils
3.650.000 kg Jahresmenge. Die Fenster sind synthetische Pflichtlieferungen;
Feiertage werden nicht gesondert ausgeschlossen. UTC-Index, Schalttag,
Wochentage sowie 23-/25-Stunden-Tage sind gezielt geprüft.
Alle sechs vollständigen CSVs mit Quellen-/Kalender-/Profilmetadaten liegen vor.
Bei der damaligen datenseitigen Schritt-21-Abnahme waren die Profilfälle
vorbereitet, aber noch nicht optimiert. Die zwölf D1/D2-Jahreslösungen sind
inzwischen vollständig geliefert und geprüft; ihre gemeinsame Step24-
Ergebnisabnahme und Interpretation stehen unten und in der EU-Fallstudie.

### Schritt 22 – Solver, Regulatorik und Validierung abstimmen

**Status: IMPLEMENTIERT UND SOFTWARESEITIG ABGENOMMEN am 03.10.2026.**
Die EU-Konfiguration setzt `temporal_correlation_timezone` auf Europe/Berlin
bzw. Europe/Madrid. Beide Solverpfade und der RED-Prüfer verwenden lokale
YYYY-MM-Gruppen für S1; S2 behält eindeutige physische UTC-Stunden.
Der unabhängige Validator rekonstruiert Ortsgruppen und Annualisierung aus
gesicherter Konfiguration und gehashter Designquelle. Exportmetadaten nennen
Monatsbasis, Zeitzone und Stundenbasis; widersprüchliche Verträge werden abgewiesen.
Legacy-Fälle verwenden weiterhin ausdrücklich UTC-Monate.

Gezielte Jahres-/Monatsgrenzfälle prüfen den Unterschied gegenüber UTC und
die Übereinstimmung von Gurobi und HiGHS; Schalttag und 23-/25-Stunden-Tage
bleiben erhalten. Alle sechs tatsächlichen 2024-Eingaben besitzen genau zwölf
lokale Monatsgruppen und 8.784 eindeutige S2-Stunden. Quellen- und Ergebnis-
Manipulationsprüfungen sind Teil der Abnahme. 583 Modell-/Datentests und 6 Unterprüfungen bestanden.
Dies war die Software-/Datenabnahme vor den Jahresläufen; die zusätzliche Ergebnisabnahme steht unter Schritt 23.

### Schritt 23 – Europäische Basisfälle rechnen

**Status: ABGENOMMEN am 04.10.2026.** Alle sechs tatsächlichen D0-Jahresfälle
für beide Standorte und S0/S1/S2 sind mit SciPy/HiGHS optimal gelöst.
Jeder Lauf umfasst 8.784 Stunden, Annualisierungsfaktor 1 und vollständig
gelieferte 3.650.000 kg H2. Standorteigene Eingaben und Parameter bleiben
zwischen den Szenarien identisch; Design und Quellen sind unveränderlich gehasht.

Die beiden unabhängigen Ergebnisvalidatoren bestehen je 112, zusammen
**224/224 Prüfungen** zu Bilanzen, Kapazitäten, Kosten, Lieferung, Kalender
und Emissionszuordnung. Ein zusätzlicher Quellen-/Ergebnisaudit besteht
275/275 separat dokumentierte Prüfungen; die Zähler werden nicht zusammengelegt.
Die Kostenordnung S0 ≤ S1 ≤ S2 ist an beiden Standorten bestätigt.
S0→S1 ergänzt EE-Mengendeckung und die dokumentierte Überschussallokation;
S1→S2 vergleicht Ortsmonate mit physischen Stunden bei gleicher Allokationskonvention.

Regulatorische Nullwerte bei S1/S2 betreffen ausschließlich die modellierte
elektrische Teilbilanz unter externen Voraussetzungen. Physischer Netzbezug
und betriebliche Referenzemissionen bleiben positiv. Kein vollständiger RFNBO-Nachweis.
Tabellen, Auslegung und vorläufige Interpretation stehen in der EU-Fallstudie;
die allgemeine Modellmethodik wurde nicht geändert.
Belege: [Laufvertrag](outputs_h2/eu_case_studies/historical_2024/step23/base_cases_20261004/run_contract.json),
[Ergebnistabelle](outputs_h2/eu_case_studies/historical_2024/step23/base_cases_20261004/results/eu_D0_base_cases.csv),
[zusätzlicher Audit](outputs_h2/eu_case_studies/historical_2024/step23/base_cases_20261004/scientific_review/STEP23_WISSENSCHAFTLICHE_ERGEBNISPRUEFUNG.md).

### Schritt 24 – Nachfrage- und Kostensensitivitäten

**Schritt 24 abgeschlossen:** 60 neue optimale Jahresfälle (12 Nachfrage- und 48 ökonomische Varianten), 2240/2240 unabhängige Exportprüfungen; sechs unveränderte D0-Ergebnisse aus Schritt 23 wiederverwendet.

Der Versuch ergänzt die sechs abgenommenen D0-Basisfälle um zwölf D1/D2-Fälle
und 48 ökonomische OAT-Varianten. Der Gesamtvergleich enthält **66 eindeutige
Ergebnisfälle**, davon sechs frühere Basisergebnisse; Schritt 24 löst 60 neue Fälle.
Nachfrageformen behalten dieselbe Jahresmenge. Preisoffset, alle fünf WACC-Raten,
PEM-CAPEX und PEM-Strombedarf werden getrennt variiert. Standortwahl, historischer
Kalender und getrennte Faktorquellen bleiben gebunden; akzeptierte Basisergebnisse
werden ohne erneute Optimierung referenziert. Die Erweiterung betrifft Runner und
optionale unabhängige Provenienzprüfungen, keine LP-Gleichungen oder Basisparameter.

Abnahme: vollständige Lieferung, unveränderte Jahresbasis, genau eine Intervention,
2240/2240 neue Exportprüfungen und ein separater 4975/4975-Audit.
Softwareabnahme: 618 Tests und 6 Unterprüfungen. Standort-/Szenariobasisfälle und
Codeversionen sind ausdrücklich zugeordnet. [66-Fall-Tabelle](outputs_h2/eu_case_studies/historical_2024/step24/sensitivities_20261004/results/all66_result_cases.csv); [Abnahmesummary](outputs_h2/eu_case_studies/historical_2024/step24/sensitivities_20261004/results/step24_results_summary.json); [unabhängige Prüfung](outputs_h2/eu_case_studies/historical_2024/step24/sensitivities_20261004/scientific_review/STEP24_UNABHAENGIGE_PRUEFUNG.md).

### Schritt 25 – Vergleich und Forschungsarbeit abschließen

**Status: FACHLICH ABGESCHLOSSEN am 04.10.2026; Manuskriptentwurf erstellt.**
Kosten, Auslegung, Betrieb und Sensitivitäten der 66 akzeptierten EU-Jahresfälle
sind diskutiert und mit Originalstudien verglichen. Der [Manuskriptentwurf](manuskript/FORSCHUNGSARBEIT_ENTWURF.md)
trennt Kosten-/Mengenanalyse, statische Betriebsreferenz und regulatorische
elektrische Teilbilanz. Namibia bleibt historische Entwicklungsreferenz.
Die [reproduzierbaren Ableitungen](outputs_h2/eu_case_studies/historical_2024/step25/discussion_20261004/result_analysis/step25_result_claims.json),
[Literaturbelege](outputs_h2/eu_case_studies/historical_2024/step25/discussion_20261004/literature/STEP25_LITERATURVERGLEICH.md) und
[Manuskriptprüfung](outputs_h2/eu_case_studies/historical_2024/step25/discussion_20261004/acceptance_report.json) tragen die Abnahme.
Keine neuen Solverläufe, keine Modell-/Parameteränderung, keine PDF-Aktualisierung.
Die Schritte 18–25 sind fachlich abgearbeitet; eine Einreichungsfreigabe ist damit
nicht verbunden. Betreuungsdurchsicht und formale Manuskriptanpassung stehen aus;
auf aktuellen Nutzerwunsch werden sie vorerst zurückgestellt.

## 5. Projektweite Entscheidungen und Entwicklung

| Zeitpunkt | Entscheidung / Entwicklung |
|---|---|
| 10.09.2026 | Umfang auf übertragbare Einzelstandort-H2-Produktion für 15 CP eingegrenzt; Ammoniak entfällt |
| 10.09.2026 | Kostenminimum, stündliche Schnittstelle, konsistente funktionelle Einheit und reale Kostenbasis festgelegt |
| 10.–12.09.2026 | H2-Kern schrittweise mit synthetischen Fällen aufgebaut; RED-Zuordnung unabhängig geprüft |
| 12.09.2026 | Namibia als technische Grundlage abgenommen; Szenarien und Sensitivitäten vollständig gerechnet |
| 13.–14.09.2026 | Methodik und Ergebnisinterpretation ausgearbeitet; H2-Branch von nicht benötigten Ammoniakdateien bereinigt |
| 15.09.2026 | Laut historischem Protokoll H2-Branch zu GitHub synchronisiert; `main` blieb unverändert |
| 02.10.2026 | Betreuergespräch erweitert Untersuchung auf zwei EU-Standorte, dynamische Daten, Länder-WACC und Nachfrageformen |
| Nach Schritt 18 | Nutzer entscheidet historisches 2025 statt ursprünglich geplantem 2023 für Hamburg/Huelva |
| 03.10.2026 | Dokumentation reorganisiert; Planung, allgemeine Methodik und Fallstudien getrennt |
| 03.10.2026 | Schritt 19 begonnen: 2025-Design, Quellenarchive, historische Adapter und Wetter-/Preisreihen; nationale HVPI-Deflation und 2024-Faktorenproxy vom Nutzer beschlossen; Datenfreigabe bleibt offen |
| 03.10.2026 | Nutzer autorisiert wissenschaftlich dokumentierte KWK-Näherung; Faktor-/Spanien-Audits und getrennte Faktoreingaben umgesetzt, erklärende PDF ergänzt; keine vollständige EU-Datenfreigabe |
| 03.10.2026 | Nutzer wählt anschließend statische Länderfaktoren; EEA-2024-Quelle und eigene Eurostat-GEP/NEP-Umrechnung belegt, vollständige D0-Faktoreingaben erzeugt, bestehende MD/PDF aktualisiert; dynamische Rekonstruktion bleibt optionale offene Untersuchung |
| 03.10.2026 | Nutzer stellt die aktive Fallstudie auf 2024 um: tatsächliche 8.784-Stunden-Wetter-/Preisreihen, Emissionsreferenz ebenfalls 2024, Kalenderannualisierung und D0/D1/D2 umgesetzt; WACC 2021 nach neuer Quellenprüfung als Finanzierungsproxy behalten |
| 03.10.2026 | Ortsmonatkorrelation aus Schritt 22 anschließend in beiden Solvern, RED-Modul und unabhängigem Validator umgesetzt; Legacy-UTC bleibt erhalten |
| 04.10.2026 | Schritt 23: sechs echte D0-Jahresfälle 2024 optimal; 224/224 Exportprüfungen und zusätzlicher 275/275-Audit; bestehende MD/PDF um Resultate ergänzt, Modellkern unverändert |
| 04.10.2026 | Schritt 24: zwölf Nachfrage- und 48 ökonomische Jahresvarianten optimal, 2240/2240 neue Exportprüfungen, separater 4975/4975-Audit; sechs D0-Originalfälle unverändert referenziert; LP-/Basisparameter unverändert |
| 04.10.2026 | Schritt 25: nachvollziehbarer EU-Manuskriptentwurf, reproduzierbare Standort-/Regelableitungen, Primärliteraturvergleich und Prüfung der Aussagegrenzen; Modell und 66 Jahresresultate unverändert, formale Einreichung offen |

Jeder Parameter benötigt Einheit, Quelle, Bezugsjahr und Bilanz-/Raumebene.
Wetter-/Marktjahr, Kostenjahr, Finanzierungsjahr und Rechtsregel werden getrennt angegeben.
Offene Annahmen werden nicht durch unbelegte Werte ersetzt.
Regulatorische Primärquellen haben Vorrang vor Literaturinterpretationen.
Extern vorausgesetzte Kriterien bleiben als Annahmen erkennbar.

Die frühere Absicht „zunächst kein Push“ ist eine historische Arbeitsentscheidung,
keine Beschreibung des gesamten heutigen Branchverlaufs. Diese Reorganisation
führt keinen Commit, Push oder Branchwechsel aus.

### Erneuter Jahreslauf auf Nutzerwunsch

Am 04.10.2026 wurden Hamburg und Huelva mit D0 und S0/S1/S2 nochmals tatsächlich
optimiert: sechs neue Volljahresausführungen mit aktuellem Code, 8.784 Stunden,
Faktor 1 und 3.650.000 kg H2 je Fall. Alle Ergebnisse sind optimal und bestehen
224/224 Exportprüfungen; der [zusätzliche Vergleich](outputs_h2/eu_case_studies/historical_2024/verification_runs/basis_20261004_121938UTC/independent_review/fresh_run_review.json)
bestätigt die Übereinstimmung mit den akzeptierten D0-Kosten.
[Laufvertrag](outputs_h2/eu_case_studies/historical_2024/verification_runs/basis_20261004_121938UTC/run_contract.json) und
[frische Ergebnisse](outputs_h2/eu_case_studies/historical_2024/verification_runs/basis_20261004_121938UTC/fresh_D0_results.csv) sind separat archiviert.
Die ursprünglichen 66 unterschiedlichen Fälle und die Abnahmen der Schritte
23–25 bleiben erhalten. Der Lauf ändert keine wissenschaftlichen Modellannahmen.

## 6. Ergebnis- und Schreibstruktur

Vorgesehene Nachweise: Annahmen-/Quellentabellen, Szenarien-LCOH,
Anlagenkapazitäten, Kostenkomponenten, Betriebsausschnitt, Emissionskennzahlen,
RED-Teilprüfung und Sensitivitäten. Alle Grafiken entstehen aus gespeicherten Tabellen.

Manuskriptfolge: Einleitung/Forschungsfrage; RED/RFNBO-Hintergrund;
Stand der Forschung; Methodik/Systemgrenze; Modell/Datengrundlage;
Fallstudien/Szenarien; Ergebnisse; Sensitivitäten; Diskussion/Limitationen;
Fazit/Ausblick.

## 7. Aktueller Auftrag

Der Nutzer hat die Manuskriptarbeit zurückgestellt. Die beauftragte
**H2-Jahresmengenanalyse** mit 50 / 75 / 100 / 125 / 150 %, beiden EU-Standorten,
D0/D1/D2 und S0/S1/S2 ist mit 90 frisch gelösten und unabhängig geprüften
Jahresfällen abgeschlossen (Abschnitt 9). Anschließend wurde die GUI auf fünf
direkte Arbeitsbereiche vereinfacht; der vollständige Funktionsumfang bleibt
erhalten (Abschnitt 10). Es ist keine weitere wissenschaftliche Variante
gestartet. Das Manuskript wird auf Nutzerwunsch weiterhin nicht bearbeitet;
eine neue fachliche Modellfrage ist noch nicht festgelegt.

## 8. Nach Schritt 25: Vergleichskonsistenz mit Namibia

**Nutzerauftrag vom 04.10.2026: gemeinsame Sensitivitäts- und Grafikmethoden.**

Die Einzelfaktoranalysen verwenden seit der Nutzerentscheidung vom 04.10.2026
ein gemeinsames Diagnoseprogramm für Namibia, Hamburg und Huelva: je ein Basisfall
und 15 Varianten für S0/S1/S2, also **48 Kombinationen je Standort und 144 insgesamt**.
Die funktionelle Einheit, Jahreslieferung und technischen Kostenannahmen bleiben
erhalten. 66 fehlende EU-Jahresvarianten wurden neu optimiert; 78 passende,
nachweislich gleich definierte Kombinationen werden aus geprüften Exporten übernommen.
Die früheren EU-Preis-/WACC-Bänder und Nachfragefälle bleiben ergänzende Auswertungen.
Die Vereinigung umfasst 132 eindeutige EU-Kombinationen und 48 Namibia-Kombinationen;
erneute Basisrechnungen zählen nicht als weitere wissenschaftliche Varianten.

| Einfluss | Gemeinsame Stufen gegenüber dem jeweiligen Basisfall |
|---|---|
| Strompreisniveau | Jede Stunde um ±50 % des arithmetischen Jahresmittels verschieben |
| Komponenten-WACC | Jede der fünf realen Raten ×7/11 bzw. ×15/11 (±36,36 %) |
| PEM-CAPEX | 75 / 125 % |
| PEM-Strombedarf | 90 / 110 % |
| PV-CAPEX | 75 / 125 % |
| Wind-CAPEX | 25 / 50 / 150 %; die ersten beiden Stufen sind explorativ |
| H2-Speicher-CAPEX | 75 / 125 % |

Diese Stufen sind methodische Diagnoseannahmen, keine empirischen
Unsicherheitsverteilungen, Preisprognosen oder Konfidenzintervalle. Ein Einfluss
wird geändert und Kapazitäten sowie Betrieb werden jeweils neu optimiert.
Fixe absolute PV-/Wind-/PEM-OPEX bleiben bei deren CAPEX-Variation unverändert;
proportionale Speicher-OPEX folgen wie bisher dem Speicher-CAPEX.

Für eine Preisreihe mit arithmetischem Mittel μ gilt `p_t' = p_t ± 0,5 μ`.
Damit betragen die jährlichen Mittelwerte 50 / 150 % des Basiswerts. Preisabstände
bleiben unverändert; einzelne Vorzeichen dürfen wechseln, es wird nicht bei null
gekappt. Es handelt sich nicht um `p_t' = 0,5 p_t` bzw. `1,5 p_t` und nicht um eine
Variation des nach der Optimierung gezahlten, strommengengewichteten Einkaufspreises.
Namibias konstanter Wert 128 ergibt genau die bisherigen 64 / 192 EUR/MWh.

Der WACC-Faktor wird erst nach der Standortwahl auf PV, Wind, PEM, Kompressor und
Speicher angewandt. Er erhält die Verhältnisse der Komponentenraten; ihre absoluten
Prozentpunktabstände skalieren mit. Der H2-Aufschlag von 2 Prozentpunkten im
EU-Basisfall beträgt im niedrigen/hohen Sensitivitätsfall deshalb 1,2727 / 2,7273
Prozentpunkte. Dies ist eine Finanzierungssensitivität des gesamten Ratensatzes;
die ursprünglichen Länderbenchmarks und der Basisaufschlag werden nicht neu geschätzt.
Namibias einheitliche 11 % ergeben unverändert die bisherigen 7 / 15 %.

Gleiche Diagnose- und Grafikmethoden machen die Eingabedaten nicht identisch:
Namibia verwendet TMY-Monate 2007–2016 mit technischem UTC-Index 2025 und 8.760
Stunden, die EU tatsächliches lokales 2024 mit 8.784 Stunden. Beide liefern
3.650.000 kg H2/a und verwenden die gleiche funktionelle Einheit. Namibia nutzt
11 % Regional-WACC, die EU dokumentierte komponentenspezifische 2021-Proxies.
Das Preisjahr des Namibia-Konstantpreises ist nicht vollständig belegt; EUR-2023-
Technologiekosten allein belegen keine Deflation dieses Strompreises.
Ein LCOH-Unterschied zwischen Ländern isoliert daher keinen kausalen Standorteffekt.
Namibias historische regulatorische 220er-Proxybewertung und die EU-Table-A-Faktoren
sind in den Emissionsbildern als unterschiedliche Quellenrollen bezeichnet.
Regulatorische Nullwerte betreffen die elektrische Teilbilanz, keine vollständige
RFNBO-Zertifizierung oder physische Emissionsfreiheit.

[Grafikübersicht](outputs_h2/cross_case_consistency/alignment_20261004/figures/GRAFIKEN_UEBERSICHT.md); [144-Fall-Tabelle](outputs_h2/cross_case_consistency/alignment_20261004/results/common_sensitivity_comparison.csv); [Laufvertrag](outputs_h2/cross_case_consistency/alignment_20261004/experiment_contract.json); [Abnahme](outputs_h2/cross_case_consistency/alignment_20261004/completion_receipt.json).

Schritt-23/24/25-Abnahmen bleiben historische Nachweise ihres damaligen Umfangs.
Die ergänzende Vergleichsabnahme wird separat geführt. Die Manuskriptarbeit
ist auf Nutzerwunsch zurückgestellt; die Nachfragemengenanalyse folgt in Abschnitt 9.


### Bedienprüfung der GUI am 5. Oktober 2026

Die Oberfläche besitzt jetzt eine ausdrückliche Analyseauswahl mit Ziel,
veränderten/festen Größen und genauer Laufanzahl. Neue Modellaufträge,
Einzelfaktorversuche und gespeicherte Auswertungen sind erkennbar getrennt;
Ergebnisfilter, Kennzahlen, Grafiken und Exporte verwenden den angegebenen
Umfang. Zwölf Interaktionstests und eine Prüfung aller zehn Seiten an drei
Standorten mit realen Forschungsdaten bestanden ohne neue Optimierung.
Modellbasis, wissenschaftliche Daten und historische Abnahmen bleiben erhalten.
[Bedienanleitung](GUI_README.md), [Prüfbeleg](outputs_h2/gui_validation/interface_20261005/interface_receipt.json).


### Einheitliche GUI-Umgebung und vollständige Anleitung am 5. Oktober 2026

Maßgeblicher Modellordner bleibt `C:\Forschungsarbeit\Opt_H2_Meric-h2`.
Die GUI-Umgebung ist frisch unter `.venv-gui` angelegt, mit denselben zusätzlichen
Paketversionen und unveränderter wissenschaftlicher Anaconda-Umgebung. Starter,
GUI-Code, aktuelle Anleitung und neue Ausgaben verwenden diesen Modellordner;
frühere Chat-Starter sind nur Weiterleitungen. Historische Quellen, Ergebnisse,
Prüfverträge und Git-Worktree-Struktur bleiben erhalten.

Die vollständige [Bedienanleitung](GUI_BEDIENUNGSANLEITUNG.md) mit
[PDF-Fassung](GUI_BEDIENUNGSANLEITUNG.pdf) beschreibt Start/Ordner, alle sechs
Analysearten mit konkreten Einstellungen und Laufzahlen, die zehn GUI-Bereiche,
Sensitivitäten, gespeicherte Grafiken, Validierung und Export. Beide Fassungen
sind in der GUI-Seitenleiste abrufbar. Der Migrationsumfang verändert keine
wissenschaftlichen Basisannahmen oder Ergebnisse.
[Migrationsbeleg](outputs_h2/gui_validation/unification_20261005/unification_receipt.json).

## 9. Nach Schritt 25: Sensitivität der H2-Jahresmenge

**Status: ABGENOMMEN am 6. Oktober 2026.** Dies ist eine ergänzende Untersuchung nach den
abgenommenen Schritten 23–25 und dem harmonisierten Namibia-/EU-Vergleich.
Die früheren Abnahmen behalten ihren damaligen Umfang.

Die Forschungsfrage lautet: Was verändert sich, wenn dieselbe hypothetische
Anlage für eine kleinere oder größere Jahreslieferung neu kostenoptimal
ausgelegt wird? Der Parameter `h2_demand_multiplier` multipliziert jede
Stundenmenge eines fest gewählten Lieferprofils mit demselben Faktor.
Die Lieferfenster und ihre Nullstunden bleiben erhalten. Damit wird die
**Nachfragemenge** geändert; der frühere D0/D1/D2-Vergleich änderte die
**Nachfrageform bei gleicher Jahresmenge**.

| Anteil der Basis | Faktor | Vorgeschriebene H2-Jahreslieferung |
|---|---:|---:|
| 50 % | 0,50 | 1.825.000 kg/a |
| 75 % | 0,75 | 2.737.500 kg/a |
| 100 % | 1,00 | 3.650.000 kg/a |
| 125 % | 1,25 | 4.562.500 kg/a |
| 150 % | 1,50 | 5.475.000 kg/a |

Hamburg und Huelva × D0/D1/D2 × S0/S1/S2 × fünf Mengen ergeben
**90 Jahresfälle**, davon 18 Referenzfälle bei 100 % und 72 Mengenvarianten.
Die vorhandenen 18 Basisexporte passen in Eingaben, skalaren Parametern und
Solver; ihr gebundener Design-Dateihash entspricht jedoch nicht dem aktuellen
Versuchsvertrag. Deshalb umfasst der neue Vertrag **90 frische Optimierungen**; die
Wiederverwendung wird nicht durch eine abgeschwächte Identitätsprüfung erzwungen.

Die Stundenbasis bleibt historisches 2024 mit **8.784 Stunden und 366 Tagen**.
Wetter, Preise, nationale statische Betriebsreferenz und regulatorischer Faktor
bleiben innerhalb eines Standort-/Profilvergleichs unverändert. Geldbasis ist
real EUR 2023, WACC bleibt der dokumentierte 2021-Proxy und die regulatorische
Tabellenreferenz hat Bezugsjahr 2020. Die Tagesdurchschnittsmenge eines
vollständigen 2024-Falls ist seine Jahresmenge geteilt durch 366; keine neue
365-Tage-Normalisierung und keine Änderung der ursprünglichen Basisdateien.

Für den neuen Eingriff wurden `h2_sensitivity_overrides.py`,
`run_h2_sensitivity.py`, `run_single_site_h2.py` und `validate_h2_results.py`
erweitert. Abgeleitete Stundeninputs und ihre effektive Jahresmenge werden
an Parent-CSV, Quellenmetadaten und Basiskonfiguration gebunden; der unabhängige
Validator rekonstruiert den Eingriff. LP-Gleichungen, Basiskonfiguration und
aktive Design-JSON bleiben erhalten.

Das bestehende Modell ist ein homogenes lineares Modell für eine vollständig
neu dimensionierte Anlage. Nachfrage ist die einzige nicht null gesetzte
rechte Seite; spezifische Kosten und Effizienzen sind größenunabhängig.
Ohne Projektfixkosten, Mindestanlagenwerte oder absolute Kapazitätsgrenzen gilt
theoretisch `J(f) = f × J(1)` und `LCOH(f) = LCOH(1)` für positive Faktoren.
Eine entsprechend skalierte Basislösung ist zulässig und optimal. Einzelne
frisch gefundene Kapazitäts-/Betriebswerte können bei alternativen Kostenoptima
abweichen; ihre exakte Proportionalität ist deshalb eine Diagnose und kein
zusätzlich erfundenes Abnahmekriterium. Die Untersuchung belegt innerhalb
dieser Modellannahmen keine Größendegression oder Engpässe einer Bestandsanlage.

Abnahme verlangt alle 90 optimalen Jahreslösungen, vollständige Lieferung,
die vorhandene unabhängige S0/S1/S2-Prüfung für jede Menge und jedes Profil,
unveränderte exogene Reihen, gebundene Quellen und die Prüfung von
Kostenproportionalität/LCOH. Softwaretests, Jahresprüfungen und zusätzliche
Audits werden getrennt ausgewiesen: **839 reguläre Softwaretests plus sechs Subtests, zusammen 845 JUnit-Prüfungen bestanden; die 141 Nachfrageprüfungen sind darin enthalten, nicht zusätzlich gezählt**;
**90 optimale vollständige 8.784-Stunden-Jahresfälle mit vollständiger Pflichtlieferung; 30 an ihre eigenen Drei-Szenario-CSV-Dateien gebundene unabhängige Berichte, 3.360/3.360 Einzelprüfungen bestanden**; **zusätzlicher erfolgreicher Quell-/Ergebnisaudit mit 30 Inputeingriffsprüfungen und 90 gebundenen nativen Exportgruppen; 50 gesonderte Postprocessingtests bestanden; diese Prüfungen ergänzen und ersetzen die unabhängigen Jahresberichte nicht**.

Die 90 tatsächlich neu gelösten Fälle bestätigen Kostenproportionalität und konstanten minimalen LCOH innerhalb der Prüftoleranz. Über alle Standorte, Profile und Szenarien reicht der LCOH von 3,888595 bis 7,422546 EUR 2023/kg H2; innerhalb jedes festen Standort-/Profil-/Szenariokontexts ändert er sich durch die Mengenstufe numerisch höchstens um 2.2524205e-12 EUR/kg. Die größte absolute Abweichung der Jahreskosten von `f × J(1)` beträgt 1.2330711e-05 EUR/a. Damit handelt es sich um ein geprüftes Ergebnis tatsächlicher Neuberechnungen, nicht um synthetisch skalierte Exporte. Kapazitäts-, Netzbezugs- und Emissionskurven verwenden die jeweils tatsächlich gelöste Variante; alternative gleich teure LP-Optima bleiben eine Diagnosegrenze.

In der normalen Sensitivitätsauswahl wird **H2-Jahresnachfrage** gewählt;
die expliziten Faktoren sind 0,5 / 0,75 / 1 / 1,25 / 1,5. Der Faktor 1
verwendet genau eine native 100-%-Basis, die vier anderen Werte sind
Einzelvarianten. D0/D1/D2 ausdrücklich als Basisprofile mit S0/S1/S2 ergeben
**45 neue Fälle je Standort**. Es gibt keinen separaten Nachfragepreset.
Die zusätzlich normale kategorische Auswahl **H2-Lieferprofil** vergleicht
unveränderte Mengenbasisfälle und erzeugt keine gekoppelten Mengen-/Profil-
Varianten. Gespeicherte Auswertung: **Sensitivitätsanalyse → Gespeicherte
Versuchsreihe → H₂-Jahresnachfrage: 50–150 % (2024)** und genau ein Lieferprofil.
Kurve und Download verwenden denselben Profilumfang. Die allgemeine gemeinsame
Namibia-/EU-Belegungshilfe bleibt bei 15 Varianten plus Basis, also 48 Fällen
je Standort und Basisprofil bei S0/S1/S2.

Das eigene Archiv liegt unter
`outputs_h2/eu_case_studies/historical_2024/demand_quantity_20261005/`.
[Versuchsvertrag](outputs_h2/eu_case_studies/historical_2024/demand_quantity_20261005/experiment_contract.json),
[90-Fall-Vergleich](outputs_h2/eu_case_studies/historical_2024/demand_quantity_20261005/results/demand_quantity_comparison.csv),
[Erklärung der Ergebnisse](outputs_h2/eu_case_studies/historical_2024/demand_quantity_20261005/results/NACHFRAGEMENGEN_ERGEBNISSE.md),
[wissenschaftlicher Abschlussbeleg](outputs_h2/eu_case_studies/historical_2024/demand_quantity_20261005/completion_receipt.json)
und [GUI-Installationsbeleg](outputs_h2/gui_validation/demand_quantity_20261005/demand_quantity_receipt.json)
halten diesen ergänzenden Umfang getrennt fest.
Grafiken und deren geprüfte Quellen: [zwölf PNG-/SVG-Abbildungen mit Quellenindex](outputs_h2/eu_case_studies/historical_2024/demand_quantity_20261005/results/figures/ABBILDUNGSINDEX.md).
Ein erneuter SHA-256-Abgleich vom 6. Oktober 2026 bestätigt alle **1.170 zuvor geschützten Quellen-, Ergebnis- und GUI-Abnahmedateien unverändert**. Die aktuelle Oberflächenrevision wird separat abgelegt; alte Exporte, Quellenverträge und frühere Abnahmen werden nicht ersetzt.

Die betroffenen Markdown-Dateien werden aktualisiert. Eine zusätzliche PDF
und Manuskriptbearbeitung gehören nicht zu diesem Auftrag.


## 10. Bedienrevision: fünf Bereiche mit erhaltenem Funktionsumfang

**Stand: 6. Oktober 2026.** Die aktuelle Oberfläche besitzt genau **Analyse**,
**Sensitivitätsanalyse**, **Vergleich**, **Quellen** und **Export**.
Analyse und Sensitivitätsanalyse verbinden Einstellungen → Berechnen →
Fortschritt → Resultate unmittelbar im selben Bereich. Alte Hauptseiten für
Planung, separaten Laufstart und Ergebnisse sind integriert; Fallstudienstatus,
Basiskonfiguration, Quellen und Validierung bleiben unter Quellen und beim
nativen Ergebnis zugänglich. Vergleich und Export erlauben gezielte Fall-,
Kennzahl-, Grafik- und Dateiauswahl.

Die vor und nach dem Umbau abgeglichene [Bestandsliste](GUI_BESTANDSLISTE.md)
bestätigt **46/46 Kriterien**. An jedem der drei registrierten Standorte bleiben
alle zuvor angebotenen **elf numerischen Sensitivitätsparameter** erhalten.
Die EU-Standorte erhalten zusätzlich die gewöhnliche kategorische Dimension
`h2_delivery_profile`; Namibia besitzt weiterhin ausschließlich sein
registriertes D0-Profil. Szenarien S0/S1/S2/S3, HiGHS/Gurobi/auto,
Solververgleich, native Kennzahlen, Quellen- und Prüfnachweise bleiben erhalten.

H2-Jahresnachfrage ist ein normaler numerischer Parameter. Profile sind normale
kategorische Stufen; es gibt keinen besonderen Nachfrage-Button. Numerische
OAT-Varianten gelten nur für die ausdrücklich gewählten Basisprofile;
zusätzliche Profilstufen werden mit unveränderten numerischen Basiswerten
ergänzt. Dadurch entsteht kein stilles vollfaktorielles Experiment.
Ein gemeinsamer OAT-Auftrag bildet eine gespeicherte Familie über seine
Profil-CSV-Dateien. Jede Quelle behält ihren eigenen Hash und gebundenen
Prüfbericht. Vollständig identische Familien werden nur als Ganzes
zusammengefasst; teilweise überlappende Familien bleiben getrennt.

Die aktuelle installierte GUI-Prüfung besteht **123/123 Tests** ohne Fehler,
Fehlschläge oder übersprungene Fälle. Separat bestanden **40/40 Prüfungen**
der vorhandenen Adapter-, Job- und Ergebniswege. Diese 40 sind der gezielte
Kompatibilitätsnachweis des GUI-Umbaus; sie sind keine neue vollständige
845er-Gesamtsuite. Die zuvor aufgeführten 845 Softwareprüfungen gehören zur
gesonderten wissenschaftlichen Nachfrageerweiterung. Tatsächliche neue
Jahreslösungen sind die 90 EU-Nachfragemengenfälle; GUI-Interaktionstests mit
simulierter Workergrenze behaupten keine weitere Jahresoptimierung.

Mathematische Modelllogik geändert? **NEIN**. Wissenschaftliche Basisparameter
geändert? **NEIN**. Vorhandene Ergebnisse überschrieben? **NEIN**. Bestehende
CLI-Runner gebrochen? **NEIN**. Diese Aussagen beziehen sich auf den
Oberflächenumbau; der davor genehmigte neue Nachfrageparameter ist separat
in diesem Dokument beschrieben.

[Aktuelle Anleitung](GUI_BEDIENUNGSANLEITUNG.md),
[aktueller GUI-Abnahmebericht](GUI_ABNAHME.md),
[Installations- und Abschlussbeleg](outputs_h2/gui_validation/simplified_20261006/interface_receipt.json).
Die vorhandene PDF dokumentiert ausdrücklich die vorherige Bedienrevision;
eine neue PDF und Manuskriptbearbeitung wurden nicht ausgeführt.


## 11. Tagesansicht der gespeicherten Ergebnisse (6. Oktober 2026)

Die GUI stellt nun auch einzelne Sensitivitätsfälle tageweise dar:
Solar-/Wind-Direktversorgung und Netzbezug oder gesamte Erzeugung und Netz
als Stundenverlauf bzw. kumulierte Tagesenergie. Ortszeit und vollständige
23/24/25-Stunden-Kalendertage werden berücksichtigt. Die Kurven sind reine
Auswertungen der vorhandenen Stundenexporte; Optimierungsmodell, Basis,
Jahreslösungen und unabhängige Validierung werden nicht geändert.
Bedienweg: Sensitivitätsanalyse → gespeicherte Versuchsreihe → Tagesstrom:
Solar, Wind und Netz → Ergebnisfall und Tag. Die aktualisierte GUI-Anleitung
und GUI_ABNAHME dokumentieren die geprüfte Ergänzung.


## Tagesbetrieb fachlich nach Analyse zugeordnet (6. Oktober 2026)

Die Tages-/Stundenansicht eines einzelnen berechneten Falls liegt unter
**Analyse → Gespeicherte Ergebnisse → Ergebnisreihe → Darstellung**.
Auch alle gespeicherten Sensitivitätsreihen sind dort auswählbar; jede behält
ihre Familienidentität, eigenen Exportpfade und eigenen Prüfnachweise.
Sensitivitätsanalyse zeigt die Wirkung der Parameteränderung. Die bisherige
doppelte Tagesoption ist in Analyse integriert. Eine Weiterleitung des
gewählten Sensitivitätsfalls öffnet dessen Tagesbetrieb dort, ohne Berechnung.
Alle Tagesmodi, Größen, Exporte, Modellparameter und wissenschaftlichen
Ergebnisse bleiben erhalten. Die Registry und das Optimierungsmodell werden
für diese Zuordnung nicht geändert.
Nachweise: outputs_h2/gui_validation/daily_analysis_20261006.


## GitHub-Übergabe der GUI (6. Oktober 2026)

Der Branch enthält GUI, nativen Modellcode, Einrichtung und einen gehashten
Datensnapshot mit 1.468 Dateien und 279 nativen Ergebnissen. Ein separater
frischer Checkout lädt alle registrierten Fallstudien ohne Warnungen. Es
bestanden 43 Checkout-/Adapter-/Lader-/Pfadprüfungen, sechs EU-Eingangsprüfungen
und die Auswertung von sechs eigenen Stundenfällen. Die Zuordnung der Tages-
ansicht nach Analyse wurde separat mit 66 GUI-Prüfungen geprüft.
Die wissenschaftlichen Jahresfälle werden dabei nicht erneut gerechnet.
Die Prüfung verwendete die vorhandene verifizierte Python-Umgebung; eine
erneute Internetinstallation aller Pakete wurde nicht ausgeführt.

[Einrichtung auf einem anderen Rechner](GUI_UEBERGABE.md),
[Übergabeprüfungen](gui/handoff_validation.json).
Ältere Abnahmeabschnitte dokumentieren den ursprünglichen Projektstand.
