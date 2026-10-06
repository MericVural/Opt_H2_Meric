# Lokale GUI für das wissenschaftliche H₂-Modell

**Auf einem anderen Rechner:** [GUI_UEBERGABE.md](GUI_UEBERGABE.md) beschreibt
Klonen, Einrichtung, Datensnapshot und normalen GUI-Start. Alle Pfade beziehen
sich auf den eigenen Checkout; Merics bisheriger Projektpfad ist ein Beispiel.

Stand: 6. Oktober 2026. Die Oberfläche besitzt genau fünf Hauptbereiche:
**Analyse**, **Sensitivitätsanalyse**, **Vergleich**, **Quellen** und **Export**.
Eingabe, Berechnung, Fortschritt und Resultate bleiben jeweils im selben Bereich.
Alle bisher unterstützten Parameter, Szenarien, Fallstudien, Solver und
Ergebnisgrößen bleiben erreichbar. Die GUI enthält keine Modellgleichungen.
Die [aktuelle Bedienungsanleitung](GUI_BEDIENUNGSANLEITUNG.md) beschreibt die neue
Oberfläche; die vorhandene PDF dokumentiert weiterhin die frühere Revision.

Die Tagesansicht **Tagesstrom: Solar, Wind und Netz** gehört zu **Analyse**.
Unter **Gespeicherte Ergebnisse → Ergebnisreihe** sind Basis-/Szenariofälle
und einzelne Fälle aller gespeicherten Sensitivitätsreihen erreichbar. Datum,
konkreter Ergebnisfall sowie Stundenverlauf oder kumulierte Tagesenergie
werden dort gewählt. Die Ansicht unterscheidet Direktversorgung von gesamter
Erzeugung und verwendet vollständige lokale Kalendertage (23/24/25 Stunden).
Sie liest vorhandene Stundenexporte; keine Optimierung oder Inputänderung.
Sensitivitätsanalyse zeigt die Parameterwirkung; ein ausgewählter Fall kann von
dort direkt zur Tagesbetriebsanalyse geöffnet werden. Export nutzt dieselbe
Ergebnisreihenauswahl.

## Start und Installation

**Alltag:** Im Windows-Explorer `C:\Forschungsarbeit\Opt_H2_Meric-h2` öffnen
und **H2-Modell starten.cmd** doppelt anklicken. Die Oberfläche öffnet im
normalen Browser <http://127.0.0.1:8510/>. Der Starter verwendet ausschließlich
`.venv-gui/Scripts/python.exe` im Modellrepository. Es gibt keinen Rückfall auf
den OneDrive-Chat-Arbeitsordner. Codex muss nicht geöffnet sein.

[Vollständige Bedienanleitung](GUI_BEDIENUNGSANLEITUNG.md),
[historische PDF-Fassung vom 5. Oktober](GUI_BEDIENUNGSANLEITUNG.pdf),
[kurze Startanleitung](H2-GUI-START.md), [Ordnerzuständigkeiten](ORDNERSTRUKTUR.md).
Die PDF und die bearbeitbare Anleitung sind auch in der GUI-Seitenleiste
über **GUI-Anleitung (PDF)** und **GUI-Anleitung (Markdown)** abrufbar.

Die GUI verwendet **Streamlit 1.65.0** in einer frisch angelegten eigenen
Umgebung mit `--system-site-packages`. Alle 25 zusätzlich lokalen Paketversionen
wurden aus den zuvor verwendeten, vorhandenen Wheels übernommen. Die wissenschaftliche
Anaconda-Umgebung `C:\Users\meric\anaconda3\envs\h2-model` bleibt unverändert:
Sie stellt Python 3.11.15 und die wissenschaftlichen Pakete sowie den nativen
Modellprozess bereit. Die GUI-Pakete und der GUI-Worker liegen lokal im Repository.

Ein sichtbarer Terminalstart verwendet denselben lokalen Interpreter:

```powershell
Set-Location 'C:\Forschungsarbeit\Opt_H2_Meric-h2'
.\gui\start_gui.ps1
```

Die vollständig gepinnten zusätzlichen GUI-Pakete stehen in
`gui/requirements-local.lock.txt`. Nur bei einer fehlenden Installation wird
eine neue Umgebung angelegt; eine vorhandene Umgebung nicht ungeprüft überschreiben:

```powershell
Set-Location 'C:\Forschungsarbeit\Opt_H2_Meric-h2'
& 'C:\Users\meric\anaconda3\envs\h2-model\python.exe' -m venv --system-site-packages .venv-gui
& .\.venv-gui\Scripts\python.exe -m pip install -r gui/requirements-local.lock.txt
.\gui\start_gui.ps1
```

Der minimale deklarierte GUI-Einstieg bleibt `gui/requirements.txt`; die
Lockdatei bildet den konkret übernommenen Stand ab. Die tatsächliche Migration
verwendete ausschließlich lokale gecachte Wheels und das vorhandene Python-Bundle;
es gab keine neuen Downloads und keine wissenschaftlichen Paketupdates.
Alte Python-Umgebungen werden nicht durch bloßes Verschieben eines Venv-Ordners ersetzt.

Der direkte Start bleibt möglich:

```powershell
& .\.venv-gui\Scripts\python.exe -m streamlit run gui/app.py --server.address 127.0.0.1 --server.port 8510 --server.headless true --browser.gatherUsageStats false --server.fileWatcherType none
```

Die GUI ist ausschließlich lokal erreichbar. Der normale Start berechnet keine
Modellfälle. Hintergrundaufträge besitzen eigene persistente Jobordner und werden
durch das Schließen der Browserseite nicht beendet. Ein PC-Neustart beendet die
Prozesse; er startet unvollständige Aufträge nicht automatisch erneut.

Startprotokoll: `outputs_h2/gui_runtime/server.log`.
Letzter Serverstart: `outputs_h2/gui_runtime/server.json` mit PID, Interpreter,
App-Pfad und URL. Ein vorhandener Server wird vom Starter verwendet; ein
Interpreterwechsel ist erst nach einem belegten Neustart nachgewiesen.

## Die fünf Arbeitsbereiche

| Bereich | Aufgabe und erhaltene Inhalte |
|---|---|
| Analyse | Fallstudie, Standort, Profile, Szenarien und Solver wählen; **Berechnen**; Fortschritt und native Resultate direkt darunter. Gespeicherte Ergebnisse können ohne Neuberechnung geöffnet werden. Solververgleich bleibt vorhanden. |
| Sensitivitätsanalyse | Basisfall und gewöhnliche Sensitivitätsparameter wählen, Werte festlegen und **Sensitivität berechnen**; Tabelle und auswählbare Grafik direkt darunter. Gespeicherte OAT-Reihen bleiben erreichbar. |
| Vergleich | Gespeicherte Fälle ausdrücklich auswählen; Kennzahl, Diagrammtyp und Gruppierung wählen; gezielte Tabelle/Grafik. |
| Quellen | Fallstudienstatus, Quellen und Jahresrollen lesen; native Basiskonfiguration, Input-/Quellenverträge, Solverprobe und unabhängige Validierungsberichte aufklappen. |
| Export | Sichtbare Tabellen, ausgewählte Vergleichsdaten, Grafik und ausgewählten nativen Fall als CSV/JSON/ZIP herunterladen. |

Die früheren Hauptseiten „Analyse planen“, „Lauf starten“ und „Ergebnisse“ sind
in den direkten Arbeitsablauf integriert. „Fallstudie“, „Modellkonfiguration“,
„Daten & Quellen“ und „Validierung“ sind fachliche Inhalte innerhalb der fünf
Bereiche. Die Verringerung der Navigation entfernt keine wissenschaftlichen
Funktionen. Die [Bestandsliste](GUI_BESTANDSLISTE.md) dokumentiert die Zuordnung
vor und nach dem Umbau.

## Fallstudien, Solver und Zeitbezüge

EU-Vergleich: Hamburg–Moorburg und Huelva–La Rábida, D0/D1/D2; vollständiges
historisches Jahr 2024 mit 8.784 Stunden. Namibia bleibt als historische
Referenzfallstudie mit D0 erhalten. Neue Namibia-Läufe setzen die bestehende
Input-/Konfigurationsfreigabe voraus; Quellen und Finanzierungsannahmen werden
nicht von einem vorher gewählten EU-Standort übernommen.

S0 = ohne zeitliche EE-Korrelation; S1 = monatliche EE-Mengendeckung;
S2 = stündliche EE-Mengendeckung; S3 = vorhandenes natives Insel-/Off-grid-Szenario.
Eine Auswahl mehrerer Profile/Szenarien ist ausdrücklich als Gruppenvergleich
sichtbar. Solver: **scipy-highs**, **gurobi** und der vorhandene **auto**-Pfad.
Gurobi benötigt für Jahresmodelle eine ausreichende Lizenz; ein ausdrückliches
Gurobi wird nicht still durch HiGHS ersetzt. Die Lizenzprobe wird nur auf Wunsch
unter Quellen gestartet.

EU-Wetter und Marktpreise stammen aus 2024. Reale EUR 2023 sind eine monetäre
Basis, kein anderes Betriebsjahr. Betriebliche Emissionen verwenden die
dokumentierten statischen nationalen 2024-Faktoren; die regulatorische elektrische
Teilbilanz hat eine separate rechtliche Referenz 2020. Der WACC-Quellenjahrgang
2021 bleibt als Finanzierungsproxy offengelegt. Namibia nutzt TMY-Wetter
2007–2016 mit technischem Indexjahr 2025 und eigene historische Annahmen.

## Gewöhnliche Sensitivitätsauswahl und OAT

Die normale Auswahl umfasst die bisherigen Preis-, WACC-, PV-/Wind-/PEM-/Speicher-
CAPEX- und PEM-Strombedarfsparameter einschließlich vorhandener Faktorvarianten.
Nur standortverträgliche native Eingriffe werden angeboten: Der EU-Pfad ersetzt
keine Länderpreise/-WACC durch historische einheitliche Namibia-Eingriffe.
Der historische Namibia-Pfad besitzt keinen freigegebenen Jahresnachfrage-
Override; dieser bleibt für EU verfügbar. Diese bestehenden Grenzen sind keine
Parameterverluste durch den Oberflächenumbau.

**H₂-Jahresnachfrage** wird als normaler numerischer Parameter
`h2_demand_multiplier` gewählt. Faktor 0,5 = 50 % der Basis; 1 = 100 %;
1,5 = 150 %. Die einmalig berechnete Basis wird nicht als zusätzliche Variante
dupliziert. Positive endliche Faktoren skalieren jede Stunde desselben
Lieferprofils proportional. Es gibt keinen besonderen Nachfrage-Button.

**H₂-Lieferprofil** ist eine normale kategorische Sensitivitätsdimension mit
D0/D1/D2, soweit am Standort registriert. Numerische OAT-Eingriffe werden nur
auf die ausdrücklich gewählten Basisprofile angewendet. Zusätzlich ausgewählte
Profilstufen werden bei unveränderten numerischen Basiswerten berechnet.
Die Auswahl beider Dimensionen erzeugt keine unbemerkte vollfaktorielle Studie.
Wer Nachfragemengen für jedes Profil untersuchen möchte, wählt D0/D1/D2 bewusst
als Basisprofile und die Nachfragefaktoren als numerischen OAT-Eingriff.

Explizite Werte verwenden Semikolontrennung, Dezimalkomma ist erlaubt.
Alternativ: Minimum, Maximum und Schrittweite. Technische Parameter können als
absolute Werte oder Änderung zur Basis [%] angegeben werden. WACC-Prozent/
Prozentpunkte werden in native Bruchteile umgerechnet; ein Faktor bleibt
dimensionslos. Die gemeinsamen Namibia-/EU-Stufen bleiben als allgemeine
Belegungshilfe erhalten: 15 Einzelvarianten plus einmalige Basis pro Szenario.

Die abgeschlossene Nachfragemengenstudie enthält **90 Jahresfälle**: zwei
Standorte × drei Profile × drei Szenarien × fünf Mengenniveaus. Sie besitzt
30 unabhängig gebundene Prüferberichte mit 3.360 bestandenen Einzelprüfungen.
Die [Ergebniserklärung](outputs_h2/eu_case_studies/historical_2024/demand_quantity_20261005/results/NACHFRAGEMENGEN_ERGEBNISSE.md)
und der [Abbildungsindex](outputs_h2/eu_case_studies/historical_2024/demand_quantity_20261005/results/figures/ABBILDUNGSINDEX.md)
sind im Modellordner erhalten. Die lineare Neuauslegung enthält keine
Größendegression; gleiche LCOH bei proportionalen Jahreskosten sind hier ein
begründetes Modellergebnis. Alternative gleich teure Optima können andere
Kapazitäten zeigen. Dies untersucht keine fest installierte Bestandsanlage.

## Ergebnisdarstellung, Quellenbindung und Export

Der gewählte native Fall liefert LCOH, Jahreskosten, PV, Wind, PEM, Kompressor,
H₂-Speicher, Netzbezug, getrennte Emissionsgrößen, RED-Teilprüfungen und
Solverdiagnostik. Betriebskennzahlen stammen aus den nativen Stundenexports;
die GUI optimiert oder rekonstruiert keine alternative Lösung.

Die Grafik zeigt ausschließlich die ausgewählten Fälle und Größen. Kompakte
mehrzeilige Kategorien, sinnvolle Rotation, begrenzte Fallmengen und eigene
Fall-/Kennzahl-/Diagrammwahl verhindern überladene Achsen. Vollständige
Fallidentität und Herkunft stehen weiterhin in Tabelle und Export.

Nachweislich identische gespeicherte Analysen werden einmal angezeigt. Alle
Originalausführungen, Hashes, Quellen und Prüfbelege bleiben in
`__result_copies` verfügbar. Vollständige Sensitivitätsreihen werden nur als
Ganzes zusammengefasst; teilweise überlappende Reihen bleiben erhalten.
Ein Validierungsbericht gilt nur für seine belegte Quelle. „optimal“ oder
Jobstatus „completed“ ersetzt keine gebundene unabhängige Prüfung.

Neue Jobs verwenden eigene UUID-Ordner unter `outputs_h2/gui_runs/` und frieren
Code, Plan, Design, Profile und Quellen ein. Die Resultate eines gestarteten
Auftrags erscheinen direkt auf derselben Seite; die Anzeige bleibt auf genau
diesen Auftrag begrenzt. Fehlgeschlagene/teilweise Jobs dürfen gespeicherte
optimale Einzelfälle anzeigen, bleiben aber ausdrücklich unvollständig.
Alte Resultate werden nicht überschrieben. Ein Schließen des Browsers beendet
den Worker nicht; kein automatischer Neustart unvollständiger Aufträge.

CSV exportiert die sichtbare Filtermenge einschließlich Originalbelegen;
JSON/ZIP betreffen den ausgewählten nativen Fall. Ein Ergebnis-ZIP ist kein
vollständiges Reproduktionsarchiv: Eingefrorene Jobquellen und Prüfberichte
liegen zusätzlich im ursprünglichen Jobordner.

## Native Architektur und Prüfung

`gui/app.py` orchestriert Eingabe und Darstellung. `gui/model_adapter.py`
übersetzt die Auswahl in vorhandene native Pläne. `gui/jobs.py` startet den
bestehenden Runner und unabhängigen Prüfer. `gui/result_loader.py` liest
ausschließlich native Exporte und zugeordnete Belege; `gui/plotting.py`
zeichnet die gewählten Resultate. Zahleneingabe und Quellen-/Pfadprüfung
bleiben in `gui/gui_utils.py` und `gui/case_study_registry.py`.

Native Modellfolge: `run_h2_sensitivity.py` → `run_single_site_h2.py` →
`opt_hydrogen_functions.py`; Prüfung: `validate_h2_results.py`. CLI-Nutzung bleibt
unabhängig von der GUI. Diese Bedienrevision ändert weder LP noch Zielfunktion,
Nebenbedingungen, RED-Regeln, native Runner oder wissenschaftliche Basiswerte.
Aktuelle Prüfnachweise werden im separaten Abnahmebericht dokumentiert.
Die GUI-Prüfung des historischen Namibia-Pfads belegt die unveränderte
Weitergabe seiner registrierten Inputs und ausdrücklich dokumentierten
WACC-Annahme. Sie behauptet keine zusätzliche vollständige Namibia-
Jahresoptimierung. Die 90 frischen Jahreslösungen gehören ausdrücklich zur
separat geprüften EU-Nachfragemengenstudie.

Grenzen: statische nationale Emissionen, historische vollständige Voraussicht,
finanzielle Proxies und elektrische regulatorische Teilprüfung. Eine komplette
RFNBO-Zertifizierung oder Lebenszyklusbilanz wird nicht behauptet. Namibia/EU-
Vergleiche zeigen die unterschiedlichen Referenzen ausdrücklich an.

[Aktuelle Abnahme und historische Nachweise](GUI_ABNAHME.md).
