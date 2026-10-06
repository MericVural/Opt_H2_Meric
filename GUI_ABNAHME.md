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

## Frühere lokale Abnahmen

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

## Vorherige Abnahme der Tagesfunktionen

# Ergänzung: Tagesstrom für gespeicherte Sensitivitätsfälle

Stand: 6. Oktober 2026. In Analyse und Sensitivitätsanalyse ist die Darstellung
**Tagesstrom: Solar, Wind und Netz** verfügbar. Ein konkreter nativer Fall,
ein lokales Datum, Stundenverlauf oder kumulierte Tagesenergie sowie
Direktversorgung oder gesamte Erzeugung werden ausdrücklich ausgewählt.
Die Stundenexporte werden ausschließlich gelesen; keine neue Optimierung.

Der Tagesbeginn ist null; kumulierte MWh stehen am Stundenende. Lokale
Kalendertage mit 23/24/25 Stunden werden vollständig geprüft. Unvollständige
Randtage werden gemeldet. Naive Startzeiten im bisherigen Stundenbetrieb
werden jetzt in der Standortzeitzone gelesen. Ein fehlender Kennzahlenwert
in alten Fällen löst einen Hinweis statt eines Seitenabbruchs aus.

97 installierte GUI-/Lader-/Diagrammprüfungen bestanden, darunter 27 neue
Tages-, Bilanz- und Zeitprüfungen. Zusätzlich bestanden 5 echte UI-Prüfungen
der neuen Tagesansicht auf registrierten Ergebnisdaten: beide Standorte
und D0/D2 sowie der Fehlerhinweis für fehlende Kennzahlen. Vier finale
Diagramme wurden visuell geprüft; der Bestandsabgleich besteht erneut 46/46.

Modellgleichungen, Runner, Solver und Basisparameter bleiben unverändert.
2.018 vorherige Quellen-/Ergebnis-/Abnahmedateien wurden per SHA geschützt.
Die 90 Nachfragefälle und ihre 3.360 unabhängigen Prüfungen bleiben erhalten.

Nachweise: [aktuelle Tagesansicht-Abnahme](outputs_h2/gui_validation/daily_view_20261006/interface_receipt.json),
[installierte Prüfsuite](outputs_h2/gui_validation/daily_view_20261006/evidence/INSTALLED_DAILY_GUI_SUITE.xml),
[echte Tages-UI](outputs_h2/gui_validation/daily_view_20261006/evidence/DAILY_GUI_TESTS.xml).

## Vorherige Abnahme der GUI-Vereinfachung

# GUI-Abnahme: Bedienrevision vom 6. Oktober 2026

Die aktuelle Oberfläche besitzt genau **Analyse**, **Sensitivitätsanalyse**,
**Vergleich**, **Quellen** und **Export**. Berechnung, Fortschritt und Resultate
sind jeweils im selben Arbeitsbereich integriert. Die vorherigen Abnahmen
stehen unverändert als historischer Nachweis weiter unten; ihre damalige
Navigation und Testzahlen sind kein Prüfbeleg für diese neue Revision.

## Aktuelle Revision und Funktionszuordnung

| Früherer Inhalt | Aktueller Ort |
|---|---|
| Analyse planen, Lauf starten, Ergebnisse | Analyse: direkte Einstellungen, Berechnen, Status und Resultate |
| Separate OAT-Planung und Laufstart | Sensitivitätsanalyse: gewöhnliche Parameter, Sensitivität berechnen und Inline-Ausgabe |
| Fallstudie, Modellkonfiguration, Daten & Quellen | Quellen: fachliche Übersicht und vollständige aufklappbare Details |
| Validierung | Beim nativen Ergebnis und innerhalb Quellen |
| Vergleiche | Vergleich: ausdrückliche Fälle-/Kennzahl-/Darstellungswahl |
| Export | Export: Tabellen, Grafiken, Vergleichsdaten und native Dateien |

Numerische H₂-Jahresnachfrage und kategorisches H₂-Lieferprofil sind Bestandteil
derselben normalen Sensitivitätsauswahl. Ein eigener Nachfrage-Übernahmebutton
und die zusätzliche Navigation zum Laufstart entfallen. Die gemeinsame
Namibia-/EU-Belegungshilfe und alle bisherigen nativen Sensitivitätsparameter
bleiben erhalten. Die [Bestandsliste](GUI_BESTANDSLISTE.md) wird vor und nach
dem Umbau abgeglichen.

Numerische Varianten verändern jeweils nur einen Faktor für ihre gewählten
Basisprofile. Zusätzliche kategorische Profile werden ausschließlich bei
unveränderten numerischen Basiswerten berechnet. Ein vollfaktorielles Experiment
wird nicht still erzeugt. Die ausdrückliche Auswahl mehrerer Basisprofile bleibt
als wissenschaftlicher Gruppenvergleich möglich.

Die direkte Ausgabe eines neuen Auftrags lädt ausschließlich dessen eigenen
hashgebundenen Plan und native Ergebnisdateien. Sie bindet Quell-CSV, Plan-Hash
und unabhängig zugeordneten Prüfbericht pro Fall. Ein globaler Jobstatus
ersetzt keine Einzelvalidierung. Teilweise fehlgeschlagene Aufträge und alle
Originalausführungen identischer gespeicherter Fälle bleiben nachvollziehbar.

Aktueller wissenschaftlicher Nachfragemengenstand: 90 frische 8.784-Stunden-
Jahresfälle, 30 gebundene unabhängige Berichte und 3.360 bestandene Prüfungen;
zwölf PNG-/SVG-Abbildungen. Das gesonderte wissenschaftliche Ergebnisarchiv
wird durch den Oberflächenumbau nicht verändert.

## Prüfbelege der neuen Revision

Die aktuelle installierte GUI-Suite besteht **123/123 Prüfungen** ohne
Fehler, Fehlschläge oder übersprungene Fälle. Separat bestanden **40/40
gezielte Kompatibilitätsprüfungen** der vorhandenen Adapter-, Job- und
Ergebniswege. Der Bestandsabgleich besteht **46/46 Kriterien**: an jedem der
drei Standorte bleiben alle elf zuvor angebotenen numerischen Sensitivitäts-
parameter erhalten; die EU-Standorte erhalten zusätzlich das kategorische
Lieferprofil. Die 46 Katalogprüfungen sind innerhalb der 123 GUI-Tests
enthalten und werden nicht ein zweites Mal addiert.

Die vorherige vollständige wissenschaftliche Nachfrage-Suite besteht aus
839 regulären Tests und sechs Subtests, insgesamt **845 JUnit-Prüfungen**;
die 141 Nachfrageprüfungen sind darin enthalten. Die aktuelle 40er-Prüfung
ist ein gezielter Kompatibilitätsnachweis des Oberflächenumbaus und keine
erneute 845er-Gesamtsuite. Die zusätzliche wissenschaftliche Auswertung
besitzt 50 eigene bestandene Postprocessingtests, 30 Inputeingriffsprüfungen
und 90 gebundene Exportgruppen. Alle 90 vollständigen Jahreslösungen
bestehen die 30 eigenen S0/S1/S2-Berichte mit 3.360 Einzelprüfungen.

Ein erneuter SHA-256-Abgleich vom 6. Oktober bestätigt 1.170 ursprüngliche
geschützte Dateien unverändert. Zusätzlich wurde der neue Loader an neun
bestehenden GUI-Aufträgen ausschließlich lesend geprüft: 42 native Fälle
aus acht Aufträgen und ein korrekt leerer vorbereiteter Auftrag, sämtliche
651 vorhandenen Jobdateien unverändert. Bestehende `not_found` und
`failed_or_changed`-Nachweise bleiben erhalten; ein globaler Jobstatus wird
nicht als unabhängige Einzelvalidierung übernommen.

[Aktueller Installations- und Abschlussbeleg](outputs_h2/gui_validation/simplified_20261006/interface_receipt.json),
[installierte GUI-Suite](outputs_h2/gui_validation/simplified_20261006/evidence/INSTALLED_GUI_SUITE.xml),
[gezielte native Kompatibilität](outputs_h2/gui_validation/simplified_20261006/evidence/NATIVE_COMPATIBILITY_SUITE.xml),
[Bestandsliste](GUI_BESTANDSLISTE.md).
Browseransicht und Exportumfang sind zusätzlich im aktuellen Abschlussbeleg
gebunden. Historische Testzahlen werden als historische Nachweise erhalten;
sie werden nicht als neue Abnahme umbenannt.

Prüfumfang: fünf Hauptbereiche; direkte Analyse-/Sensitivitätsstarts und
Inline-Ergebnisse; normale Nachfrage-/Profilparameter; OAT-Laufanzahl und
Weitergabe an native Pläne; siteabhängige Eingaben; ungültige Entwürfe;
gezielter Vergleich; lesbare Grafiklabels; gespeicherte Quellen, eigene
Validierung, identische Originalausführungen und native Exporte. Die
Streamlit-Interaktionstests simulieren nur Modell-/Workergrenzen und sind
keine Ersatzbehauptung für echte numerische Solvertests.

## Bestätigung für diese GUI-Bedienrevision

| Frage | Antwort |
|---|---|
| Mathematische Modelllogik verändert? | **NEIN** |
| Wissenschaftliche Basisparameter verändert? | **NEIN** |
| Bestehende Ergebnisse überschrieben? | **NEIN** |
| Bestehende CLI-Runner gebrochen? | **NEIN** |

Die davor genehmigte Einführung der numerischen Nachfragemengenvariante gehört
zum getrennten wissenschaftlichen Schritt. Diese Oberflächenrevision ändert
keine LP-Gleichungen, nativen Runner, Solverregeln oder wissenschaftlichen
Basiswerte. Die vorhandene PDF bleibt eine klar gekennzeichnete historische
Anleitung; aktuelle Bedienung steht in Markdown.

## Historische Abnahmen bis zum 5. Oktober 2026

Die folgenden Originalnachweise werden für Nachvollziehbarkeit erhalten.
Sie beschreiben ihre damaligen Revisionen und Menüstrukturen.

# GUI-Abnahme vom 4. Oktober 2026

Die installierte Streamlit-GUI startet lokal unter <http://127.0.0.1:8510>.
Sie bedient die bestehenden Runner und verwendet keine eigenen Modellgleichungen.
[Startanleitung und Architektur](GUI_README.md).

| Ergebnis | Nachweis |
|---|---|
| Vollständige installierte Suite | 704 JUnit-Prüfungen, 0 Fehler, 0 Fehlschläge, 0 übersprungen |
| Bedien-/Grafikprüfungen | 65 tatsächliche Streamlit-AppTest-Prüfungen; alle zehn Bereiche und sechs Grafiktypen an drei Standorten |
| Abschließende UI-Reparaturprüfung | 6 Prüfungen, an finalen `app.py`-Hash gebunden |
| Native CLI gegen GUI | Echter 24-Stunden-Test, S0/S1/S2, Zielfunktionsdifferenz jeweils 0; LCOH, fünf Kapazitäten, Mengen, effektive Parameter/Einheiten/Jahre und Bilanzen stimmen überein |
| HiGHS | Verfügbar; Standard |
| Gurobi | Installiert, Jahresgrößenprobe scheitert an beschränkter Lizenz; kein stiller Ersatz für ausdrücklich gewähltes Gurobi |
| Historische Belege | 361 bisherige Quellen-/Ergebnisdateien mit unveränderten SHA-256 |

Die erste Gesamtprüfung bestand 681 Tests und sechs Subtests; bei 17 weiteren
Fällen überschritt der Zielpfad einer bestehenden Testfixture die Windows-
Pfadlängengrenze. Das betroffene Modul wurde unverändert in einem kurzen
temporären Verzeichnis wiederholt: 23/23 bestanden, einschließlich aller 17
betroffenen Fälle. Der finale Gesamtbeleg ersetzt ausschließlich diese
Setupfehler; beide Originalberichte bleiben archiviert. Modellcode und
Testassertionen wurden dafür nicht geändert.

## Dateien und Modellwege

Neu: `gui/` mit Oberfläche, Registry, Adapter, Jobverwaltung, Ergebnisloader,
Plotmodul, Zahleneingabe, Launcher und separater GUI-Abhängigkeit; `GUI_README.md`,
dieser Bericht und fünf neue GUI-Testmodule. Für die GUI wurde lediglich ein
kompakter GUI-Verweis in `README.md` ergänzt; kein bestehender Modellrunner wurde
durch die GUI bearbeitet. Die davor ausdrücklich genehmigte WACC-Erweiterung und
die sieben aktualisierten wissenschaftlichen MD-Dateien gehören zum separaten
[Namibia-/EU-Vergleich](outputs_h2/cross_case_consistency/alignment_20261004/completion_receipt.json).

Native Wege: `run_h2_sensitivity.py` → `run_single_site_h2.py` →
`opt_hydrogen_functions.py`; unabhängige Prüfung `validate_h2_results.py`.
Der direkte Regressionsweg verwendet `run_h2_scenarios.py`.

## Wissenschaftlicher und technischer Umfang

EU-Vergleich 2024: Hamburg–Moorburg und Huelva–La Rábida, D0/D1/D2.
Namibia: dokumentierter Referenzstandort, D0; weiterhin historischer Fall,
gegenwärtig mit nachgewiesener Input-/Konfigurationskompatibilität neu ausführbar.
Aktuell besitzt keine registrierte Fallstudie ausschließlich einen Lesestatus.
S0/S1/S2 und S3 sind als vorhandene native Szenarien auswählbar. Solver: HiGHS,
optionales Gurobi und vorhandener expliziter Auto-Pfad.

Sensitivitäten: vorhandene Preis-, WACC-, CAPEX- und PEM-Strombedarfseingriffe,
explizite Werte oder Bereich, absolute oder dokumentierte relative Angaben;
OAT-Laufzahl vor dem Start. Das gemeinsame Diagnoseprogramm erzeugt 15 Varianten
und einen Basisfall je Szenario. WACC-Prozent wird in einen Bruchteil umgerechnet;
ein WACC-Faktor bleibt dimensionslos. Individuelle Komponenten-WACC-Eingriffe
werden nicht angeboten, weil der native Runner sie nicht separat unterstützt.

Ergebnisse: LCOH, Jahreskosten, Kapazitäten, reale Betriebskennzahlen aus
Stundenexporten, getrennte Emissionsbilanzen, Teilprüfungen, Solverstatus/Runtime/
Gap, Quellen, Jahre, Hashes und gespeicherte Validierung. CSV/JSON/ZIP-Export und
Vergleich gespeicherter Fälle benötigen keine Neuberechnung. Neue Aufträge
frieren Code/Inputs/Design ein und schreiben eigene UUID-Ausgabeordner.

Grenzen bleiben sichtbar: Namibia-TMY und unbelegtes Strompreisjahr gegenüber
EU-Betrieb 2024; verschiedene Finanzierung-/Faktorreferenzen; jährliche statische
Emissionen und elektrische regulatorische Teilbilanz; keine vollständige RFNBO-
oder Lebenszyklusprüfung. Unvollständige S0/S1/S2-Auswahl bleibt Teilvalidierung.
Gurobi-Jahresläufe benötigen eine ausreichende Lizenz. Kein komfortables
Abbrechen/Fortsetzen gestarteter Jobs in dieser ersten Oberfläche.

## Ausdrückliche Bestätigung

| Frage | Antwort |
|---|---|
| Mathematische Modelllogik verändert? | **NEIN** |
| Basisparameter verändert? | **NEIN** |
| Vorhandene Fallstudiendaten verändert? | **NEIN** |
| Bestehende Ergebnisse überschrieben? | **NEIN** |
| Git commit ausgeführt? | **NEIN** |
| Git push ausgeführt? | **NEIN** |
| Branch gewechselt? | **NEIN** |

Projektdokumentation und Design-Fortschrittsstatus wurden gemäß vorherigem Auftrag
aktualisiert; wissenschaftliche Basisfelder und Eingabezeitreihen blieben erhalten.
Die genehmigte zusätzliche WACC-Sensitivität verändert nur ausdrücklich gewählte
Varianten, keine Basisgleichungen oder Basiskonfiguration.

[Maschinenlesbare Abnahme](outputs_h2/gui_validation/gui_20261004/gui_acceptance_receipt.json),
[vollständiger Testbericht](outputs_h2/gui_validation/gui_20261004/full_installed_suite.xml),
[CLI-/GUI-Regressionsbeleg](outputs_h2/gui_validation/gui_20261004/GUI_CLI_REGRESSION_installed.json).


## Bedienrevision vom 5. Oktober 2026

Das Analyseziel wird jetzt ausdrücklich gewählt: Szenarienvergleich,
Lieferprofilvergleich, Einzelfaktor-Sensitivität, Einzelfall, Solververgleich oder
gespeicherte Auswertung. Die Vorschau nennt veränderte und feste Größen sowie
die exakte Laufanzahl. Gespeicherte Fälle und neue OAT-Entwürfe sind eindeutig
getrennt. Kennzahlen, Grafikfall und native Exportauswahl stimmen überein;
Ergebnis-/Exportfilter erhalten auch eine ausdrücklich leere Auswahl.

Der aktuelle Stand besteht **12/12 echte Streamlit-Interaktionstests** ohne
Fehler oder übersprungene Fälle sowie **54 Prüfungen mit realen
registrierten Daten**, darunter alle zehn Seiten an drei Standorten,
Analysearten und das gemeinsame 15-Varianten-Programm mit 48 Läufen pro
Lieferprofil/Standort. Bei diesen Bedienprüfungen wurde kein Optimierungsauftrag
gestartet. Die Interaktionstests isolieren Modell-/Jobgrenzen; sie sind keine
zusätzlichen numerischen Solvertests.

Die oben beschriebenen 704 wissenschaftlichen/Adapterprüfungen und der echte
24-Stunden-CLI-/GUI-Vergleich bleiben historische Nachweise des 4. Oktober.
Native Modell-/Runner-/Adapter-/Worker-/Plotdateien sind gegenüber diesem
abgenommenen Stand SHA-256-identisch. Die aktuelle Revision ändert lediglich
`gui/app.py`, ergänzt `gui/analysis_intent.py` und GUI-Interaktionstests unter
`gui/checks/ux_regression.py`. Sie verändert keine Modellgleichungen,
Basisparameter, Quellen, alten Forschungsresultate oder Solverregeln.

[Reproduzierbare Anleitung](GUI_README.md),
[separater aktueller Beleg](outputs_h2/gui_validation/interface_20261005/interface_receipt.json).
Der frühere Abnahmeordner und der wissenschaftliche Vergleichsordner wurden
nicht überschrieben; die sieben Bestätigungen bleiben NEIN.


## Vereinheitlichte Umgebung und Anleitung vom 5. Oktober 2026

Die zusätzliche GUI-Laufzeit wurde im Modellrepository neu angelegt und mit
denselben lokal vorhandenen Paketversionen installiert. Die wissenschaftliche
Anaconda-Umgebung, native Python-Dateien, freigegebene Inputs, Forschungsresultate
und historische Abnahmeordner bleiben erhalten. Neue normale GUI-Starts verwenden
`.venv-gui/Scripts/python.exe` im Modellrepository. Frühere Workspace-Starter
sind nach Sicherung ihrer Originale lediglich Weiterleitungen.

Die einzige zusätzliche Änderung der Oberfläche sind zwei Downloads für die
vollständige 13-seitige PDF-Anleitung und ihre Markdown-Quelle. Analyseauswahl,
native Runner, Parameter, Quellenverträge und Solverregeln wurden dabei nicht
geändert. Starthelfer und Protokolle verwenden `outputs_h2/gui_runtime/`.

[Vollständige Anleitung](GUI_BEDIENUNGSANLEITUNG.md),
[Ordnerzuständigkeiten](ORDNERSTRUKTUR.md),
[aktueller Beleg und neue Prüfungen](outputs_h2/gui_validation/unification_20261005/unification_receipt.json).


Abschlussprüfung der vereinheitlichten Installation: **12/12 Interaktionstests**
ohne Fehler oder übersprungene Fälle und **54/54 Prüfungen mit registrierten
Falldaten** bestanden, ausdrücklich mit der neuen lokalen GUI-Umgebung.
Importpfade, Paketkonsistenz, alle 14 registrierten Profil-/Metadatenpfade und
ein nativer Drei-Fälle-Plan wurden geprüft. Der Plan wurde ausschließlich im
Prüfordner vorbereitet; kein Worker und kein Optimierer wurden gestartet.

Der echte Kaltstart über die zentrale CMD-Datei ist nachgewiesen. Der lokale
Server lauscht ausschließlich auf `127.0.0.1:8510`; die Windows-Prozesskette
enthält den Starter aus `.venv-gui` und das GUI-Skript aus dem Modellrepository.
Der unveränderte Anaconda-Basisinterpreter erscheint dabei als Kindprozess des
Windows-Venv-Starters. Auch die frühere Workspace-CMD funktioniert als
Weiterleitung. Beide Anleitung-Downloads wurden in der laufenden Oberfläche
ausgelöst; die heruntergeladenen Dateien stimmen per SHA-256 mit den installierten
Dateien überein. Die PDF hat 13 Seiten, wurde vollständig visuell geprüft und
weist keine Wörter außerhalb des sicheren Seitenbereichs auf.

Erneut geprüft: 26 native Python-Dateien, 18 aktive Quellen-/Design-Dateien,
361 bisherige wissenschaftliche Quellen-/Ergebnisdateien und die früheren
Abnahmemanifeste sind unverändert. Die Paketliste der wissenschaftlichen
Anaconda-Umgebung ist identisch. Git-Branch und HEAD sind erhalten; es gab
keinen Commit oder Push und keine neue Modelloptimierung.

## Ergänzung: identische gespeicherte Ausführungen am 5. Oktober 2026

Die GUI fasst nachweislich identische gespeicherte Analysen einmal zusammen. Eingaben, Parameter, wissenschaftlicher Kontext, native Kennzahlen und Stundenexports sind Bestandteil der Zuordnung. Abweichende Fälle bleiben getrennt. Vollständige Sensitivitätsreihen werden nur als Ganzes zusammengefasst; teilweise überlappende Reihen bleiben erhalten.

Alle ursprünglichen Herkunfts- und Prüfnachweise bleiben pro Ausführung erhalten. Die bevorzugte repräsentative Ausführung und deren nativer JSON-/ZIP-Export sind nachvollziehbar; ein gebundener Prüfbericht wird nicht auf andere Kopien übertragen. CSV bewahrt alle Originalbelege im Feld `__result_copies`. Der neue Anzeigeumfang ersetzt keine fehlende unabhängige Validierung bestehender Aufträge.

**36/36 gezielte Tests** bestanden: 23 Gruppierungsprüfungen und 13 tatsächliche Streamlit-Interaktionstests, einschließlich Auswahlmigration, Wechsel der repräsentativen Ausführung, Grafikmenge und CSV-/JSON-Exportbindung. Die Modell- und Jobgrenzen sind in diesen Tests gesperrt beziehungsweise gezielt simuliert; kein Optimierer wurde gestartet. Die zuvor dokumentierten wissenschaftlichen Abnahmestände bleiben historische Nachweise.

[Neuer Installationsbeleg und Prüfarchiv](outputs_h2/gui_validation/unique_results_20261005/unique_results_receipt.json).

Die zusätzliche Prüfung mit realen registrierten Daten bestätigt Hamburg **27 → 16** Ergebnisfälle, Huelva **12 → 12** und Namibia **3 → 3**. Hamburgs zwei D1-Aufträge sind in jedem ihrer drei gemeinsamen Basisfälle zusammengefasst; abweichende historische D1-Fälle bleiben getrennt. Hamburgs 81 Sensitivitätszeilen in drei Sammlungen und Huelvas 75 in zwei Sammlungen bleiben vollständig. Die zwei identischen Namibia-Referenzen auf dieselbe Versuchsreihe werden von 96 auf 48 Zeilen in einer Sammlung zusammengefasst. Die sechs neuen Hamburg-PEM-Varianten bleiben erhalten.

Reale Streamlit-Prüfungen für Ergebnisse, Validierung, Export, Vergleiche und gespeicherte Sensitivitäten bestätigen die Fallauswahl und Downloads. 895 beobachtete Export-/Jobdateien blieben während dieser Prüfung unverändert. Außerdem sind 26 native Python-Dateien, 18 aktive Quellen-/Design-Dateien, 361 frühere wissenschaftliche Quellen-/Ergebnisdateien und die vorhandenen GUI-Nachweise unverändert. Es wurde kein Optimierer gestartet. Die lokale Browseransicht bestätigt einen gemeinsamen D1-Fall mit zwei erhaltenen Originalausführungen; deren fehlender unabhängiger Prüfbericht bleibt sichtbar.
