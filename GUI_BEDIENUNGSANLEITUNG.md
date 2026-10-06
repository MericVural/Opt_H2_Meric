# Bedienungsanleitung zur GUI des wissenschaftlichen H₂-Modells

**Auf einem anderen Rechner:** [GUI_UEBERGABE.md](GUI_UEBERGABE.md) beschreibt
Klonen, Einrichtung, Datensnapshot und normalen GUI-Start. Alle Pfade beziehen
sich auf den eigenen Checkout; Merics bisheriger Projektpfad ist ein Beispiel.

Aktuelle Bedienrevision: **6. Oktober 2026**. Die Oberfläche besitzt fünf
Hauptbereiche. Diese Markdown-Anleitung beschreibt den aktuellen Stand.
Die vorhandene 13-seitige PDF ist die historische Anleitung vom 5. Oktober
und wird auf Wunsch später aktualisiert; sie ist für die neue Navigation
nicht maßgeblich.

## 1. Start und Modellordner

Im Explorer `C:\Forschungsarbeit\Opt_H2_Meric-h2` öffnen und
**H2-Modell starten.cmd** doppelt anklicken. Die GUI läuft unter
<http://127.0.0.1:8510/> im normalen Browser. Codex muss dafür nicht geöffnet
sein. Alternativ im Modellordner `gui/start_gui.ps1` ausführen.

Der aktuelle Modellcode, die GUI, Inputs und Resultate liegen einheitlich im
Modellrepository. `.venv-gui` ist die lokale GUI-Umgebung; der native
Modellprozess nutzt die bestehende Anaconda-Umgebung `h2-model`. Der OneDrive-
Chat-Arbeitsordner ist keine zweite produktive Modellablage. Die GUI liest
Quellen aus den dokumentierten Registry-Pfaden.

Start allein berechnet keine Fälle. Der Server schreibt sein Startprotokoll
nach `outputs_h2/gui_runtime/server.log` und Interpreter/App/URL/PID nach
`outputs_h2/gui_runtime/server.json`. Einen vorhandenen Server verwendet der
Starter weiter; nach einer Installation kann ein dokumentierter Neustart
erforderlich sein. Installationsdetails: [GUI_README.md](GUI_README.md).

## 2. Orientierung: fünf Bereiche

| Bereich | Wann benutzen? |
|---|---|
| **Analyse** | Einzelfall, Szenarien-, Lieferprofil- oder Solververgleich frisch rechnen; anschließend direkt Ergebnisse lesen. Oder gespeicherte Ergebnisse ohne Rechnen ansehen. |
| **Sensitivitätsanalyse** | Einen oder mehrere Einflussfaktoren einzeln um ihre Basis verändern; gespeicherte Versuchsreihen und neue Ergebnisse auswerten. |
| **Vergleich** | Bereits vorhandene Fälle und Sensitivitätsfälle gezielt nebeneinander auswählen und darstellen. |
| **Quellen** | Quellen, Jahre, Annahmen, Modellstatus, native Basiskonfiguration, Solverprobe und unabhängige Prüfung nachlesen. |
| **Export** | Gewählte Tabelle, Grafik und native Ergebnisdateien herunterladen. |

Fallstudie und Standort bleiben ausdrücklich getrennte Einstellungen. Bei
einem Standortwechsel erhalten die jeweiligen Einstellungen eigene Zustände.
Prüfen Sie vor einem Start dennoch die sichtbare Auswahl und Laufanzahl.
Die früheren separaten Seiten für Plan, Laufstart, Ergebnisse und Validierung
sind in diesen Arbeitsablauf integriert. Ihre fachlichen Inhalte bleiben
vorhanden.

## 3. Fallstudien, Profile und Szenarien

EU-Vergleich 2024: **Hamburg–Moorburg** und **Huelva–La Rábida**. Die Jahresreihen
enthalten 8.784 Stunden. **Namibia** bleibt als historische Referenz mit D0
erhalten; eine neue Berechnung setzt die bestehende Kompatibilitätsfreigabe
voraus. Die Oberfläche zeigt den tatsächlichen Status des gewählten Falls.

| Lieferprofil | Verpflichtende H₂-Lieferung |
|---|---|
| D0 | Rund um die Uhr |
| D1 | Täglich 08–20 Uhr Ortszeit |
| D2 | Montag–Freitag 08–20 Uhr Ortszeit; ohne zusätzliche Feiertagskorrektur |

Dies sind Lieferfenster. Die H₂-Produktion kann auch außerhalb dieser Fenster
erfolgen; der Speicher verbindet Produktion und Lieferung. Alle drei EU-
Basisprofile haben dieselbe Jahresmenge von **3.650.000 kg**. Bei 366 Tagen ist
die Kalendertagesmenge 3.650.000 / 366; die Lieferstundenwerte hängen vom Profil ab.

| Szenario | Elektrische zeitliche Bedingung |
|---|---|
| S0 | Keine zeitliche EE-Korrelation |
| S1 | Monatliche EE-Mengendeckung |
| S2 | Stündliche EE-Mengendeckung |
| S3 | Vorhandenes natives Off-grid-Szenario ohne Netzbezug |

S2 mit historischen 2024-Inputs ist eine Regeluntersuchung und keine
2030-Prognose. Die RED-Anzeigen sind elektrische Teilprüfungen und keine
vollständige Zertifizierung. Solver **scipy-highs** ist standardmäßig verfügbar;
**gurobi** und **auto** bleiben auswählbar. Gurobi-Jahresläufe benötigen eine
ausreichende Lizenz. Die GUI ersetzt ein ausdrücklich gewähltes Gurobi nicht
still durch HiGHS.

## 4. Analyse: auswählen, berechnen, darunter lesen

1. **Analyse** öffnen und **Neue Berechnung** wählen.
2. Fallstudie und Standort wählen.
3. Lieferprofile und Szenarien ausdrücklich wählen. Ein Profil und ein
   Szenario ergeben einen Einzelfall. Mehrere Szenarien vergleichen die
   Stromversorgungsregeln; mehrere Profile vergleichen die Lieferzeit.
4. Solver wählen. Für einen bewussten HiGHS-/Gurobi-Vergleich die vorhandene
   Solververgleichsoption aktivieren; dabei werden beide Solver ausdrücklich
   berechnet.
5. Quellen-/Basisangaben und angezeigte Anzahl neuer Optimierungsläufe prüfen.
6. **Berechnen** anklicken. Fortschritt und aktuelle Berechnung bleiben hier
   sichtbar. Nach Abschluss erscheinen die Resultate direkt darunter.

Beispiele: D0 + S0/S1/S2 = drei Fälle. D0/D1/D2 + S0 = drei Lieferprofilfälle.
D0/D1/D2 + S0/S1/S2 = neun ausdrücklich gewählte Gruppenfälle. Ein Solververgleich
verdoppelt die entsprechenden Fälle. Es gibt keine zusätzliche Laufstartseite.

Unter den Ergebnissen den nativen Fall wählen. Kennzahlen umfassen LCOH,
Jahreskosten, PV, Wind, PEM, Kompressor, H₂-Speicher, Netzbezug, getrennte
Emissionsgrößen, RED-Teilprüfung und Solverdiagnostik. Die vollständige native
Ergebnistabelle und der gebundene unabhängige Bericht bleiben zugänglich.

Die Grafikauswahl legt Ergebnisgröße, Diagrammtyp und gezeigte Fälle fest.
Zusätzliche Darstellungen für Kostenkomponenten, Kapazitäten, Betriebskennzahlen,
Emissionen und Stundenbetrieb bleiben erreichbar. Lange Fallbezeichnungen werden
kompakt mehrzeilig gezeigt; die vollständigen Kennungen stehen in der Tabelle.
Bei vielen Fällen begrenzt oder verteilt die Auswahl die Grafik. Es wird keine
automatische Folge repetitiver Grafiken ausgegeben.

Für vorhandene Auswertungen **Gespeicherte Ergebnisse** wählen. Anschließend
Profile, Szenarien und Solver filtern und den Ergebnisfall wählen. Eine leere
Filterauswahl ergibt bewusst keine Fälle; es wird kein neuer Lauf gestartet.
Filter- und native Exportauswahl beziehen sich auf die angezeigten Fälle.

### 4.1 Tagesgrafik für Solar, Wind und Netzbezug

Die Tagesgrafik ist die Betriebsanalyse eines einzelnen berechneten Falls.
Sie gehört in **Analyse**, auch wenn der Fall aus einer Sensitivitätsreihe stammt.

1. **Analyse → Gespeicherte Ergebnisse** öffnen.
2. Unter **Ergebnisreihe** die Basis-/Szenariofälle oder die gewünschte
   Sensitivitätsreihe (z. B. **H₂-Jahresnachfrage: 50–150 % (2024)**) auswählen.
3. Lieferprofil, Szenario und Solver filtern und den konkreten Ergebnisfall wählen.
4. **Darstellung → Tagesstrom: Solar, Wind und Netz** einstellen.
5. Unter **Tag auswählen** das Datum und die Tagesdarstellung wählen.

Alle gespeicherten Varianten bleiben erreichbar. Die Ergebnisreihen werden
getrennt ausgewählt; sie werden nicht doppelt in eine gemeinsame Fallliste kopiert.
Der bisherige **Stundenbetrieb** mit frei wählbarem Ausschnitt sowie H₂-Produktion
und Speicher bleibt erhalten. Unter **Export** steht dieselbe Ergebnisreihenauswahl
für native Dateien, Metadaten und Prüfnachweise zur Verfügung.

In **Sensitivitätsanalyse** vergleichen Sensitivitätskurven und gruppierte Balken
die Wirkung geänderter Parameter. Unter **Einzelnen Sensitivitätsfall und Prüfnachweis
öffnen** führt **Tagesbetrieb dieses Falls in Analyse öffnen** direkt zum selben
nativen Fall mit passender Reihe, Profil, Szenario und Solver. Es startet keinen Lauf.

**Stündlicher Tagesverlauf** zeigt die Energie jeder einzelnen Stunde.
**Kumulative Tagesenergie** summiert ab der lokalen Mitternacht; die Kurven
beginnen bei null und enden mit der Tagesenergie in MWh. Ein Kalendertag
umfasst bei Zeitumstellung 23 bzw. 25 Stunden. Unvollständig vorhandene
Tage werden als solche gemeldet und nicht ergänzt. Die Startzeit im
bisherigen Stundenbetrieb wird ebenfalls in der angezeigten Ortszeit gelesen.

Die Auswahl **Stromgrößen** trennt zwei fachliche Bedeutungen:

- **Direktversorgung:** direkt genutzter Solar-/Windstrom und Netzbezug;
  die gestapelten Stundenwerte bilden die physische Stromversorgung ab.
- **Erzeugung und Netzbezug:** gesamte Solar-/Winderzeugung einschließlich
  Überschüssen sowie Netzbezug als getrennte Kurven. Ihre Summe ist keine
  Anlagenstrombedarfsbilanz.

**Tagesdaten als CSV herunterladen** enthält die Originalstunden, die
ausgewählten Größen, die kumulierten Energien und den konkreten Ergebnisbezug.
Die zuletzt angezeigte Grafik lässt sich unter **Export** als PNG/SVG speichern.

## 5. Sensitivitätsanalyse: gewöhnliche Parameter und OAT

1. **Sensitivitätsanalyse** öffnen; Fallstudie und Standort wählen.
2. Basisprofile, Szenarien und Solver festlegen. Mehrere Basisprofile sind
   ausdrücklich mehrere Referenzkontexte, keine automatische neue Dimension.
3. Die aktiven Sensitivitätsparameter normal auswählen.
4. Je Parameter explizite Werte oder einen Bereich eingeben; Einheit und
   Eingabebezug prüfen.
5. Die Anzahl Basis- und Einzelvarianten prüfen und **Sensitivität berechnen**
   anklicken.
6. Im selben Bereich die resultierende Tabelle und eine gezielt gewählte
   Sensitivitätsgrafik lesen.

Vorhanden bleiben Strompreisoffset, vorhandener konstanter Strompreis für den
historischen Pfad, gemeinsame WACC-Faktoren und WACC-Verschiebungen,
PV-/Wind-/PEM-/H₂-Speicher-CAPEX, PEM-Strombedarf sowie vorhandene PEM-Faktor-
varianten. Die Auswahl entspricht den freigegebenen nativen Fähigkeiten des
jeweiligen Fallstudienpfads. Individuelle Komponenten-WACC sind keine freie
GUI-Eingabe. EU-Standorte behalten ihre länder-/technologiespezifischen Raten.
Die vor und nach dem Umbau abgeglichene [Bestandsliste](GUI_BESTANDSLISTE.md)
zeigt alle Parameter.

**OAT bedeutet:** Jeder ausgewählte numerische Parameter wird einzeln verändert;
alle übrigen numerischen Parameter behalten ihren Basiswert. Zwei Faktoren mit
je zwei Varianten erzeugen vier Einzelvarianten und eine gemeinsame Basis,
keine vier gekoppelten Kombinationen. Pro Szenario und Basisprofil gilt diese
eigene Referenz. Die Laufanzahl ist vor dem Start sichtbar.

### 5.1 H₂-Jahresnachfrage

**H₂-Jahresnachfrage: Faktor zur Basis** als gewöhnlichen Sensitivitätsparameter
wählen. Beispielwerte: `0,5; 0,75; 1; 1,25; 1,5`. Sie entsprechen 50/75/100/125/150 %.
100 % ist der einmalige unveränderte Basisfall und wird nicht doppelt berechnet.
Faktoren müssen endlich und größer als null sein. Es gibt keinen gesonderten
Nachfrage-Übernahmebutton.

| Anteil | Verpflichtende Jahresmenge [kg/a] |
|---|---:|
| 50 % | 1.825.000 |
| 75 % | 2.737.500 |
| 100 % | 3.650.000 |
| 125 % | 4.562.500 |
| 150 % | 5.475.000 |

Jede Stunde desselben Lieferprofils wird proportional skaliert. Zeiten und
Liefermasken bleiben erhalten; Wetter, Preise und Emissionsfaktoren werden
dabei nicht verändert. Neue EU-Jahresnachfragesensitivitäten sind freigegeben;
für den historischen Namibia-Pfad wird kein unbelegter Override angeboten.

Die bereits durchgeführte Studie hat für Hamburg und Huelva alle drei Profile
und S0/S1/S2 bei diesen fünf Mengen untersucht: **90 frische Jahresfälle**,
30 unabhängig gebundene Berichte, **3.360/3.360 Prüfungen bestanden**. Die
gespeicherte Reihe „H₂-Jahresnachfrage: 50–150 % (2024)“ auswählen und danach
genau ein Lieferprofil für die Kurve wählen. Der CSV-Download hat dieselbe
Kurvenauswahl. Alle 90 Originalfälle bleiben im Ergebnisordner erhalten.

Das Modell entwirft für jede Menge eine neue Anlage und besitzt lineare
Investitionskosten ohne Größendegression. Proportionale Jahreskosten mit
weitgehend konstantem LCOH sind daher wissenschaftlich erwartbar. Unterschiedliche
gleich teure Optima können Kapazitätskurven beeinflussen. Hieraus folgt keine
Aussage über Engpässe einer bereits fest installierten Anlage.

[Ergebnisbegründung](outputs_h2/eu_case_studies/historical_2024/demand_quantity_20261005/results/NACHFRAGEMENGEN_ERGEBNISSE.md),
[zwölf Abbildungen mit PNG/SVG](outputs_h2/eu_case_studies/historical_2024/demand_quantity_20261005/results/figures/ABBILDUNGSINDEX.md).

### 5.2 H₂-Lieferprofil als kategorische Dimension

**H₂-Lieferprofil** in derselben normalen Sensitivitätsauswahl wählen und die
verfügbaren Stufen D0/D1/D2 markieren. Diese Variation verändert Lieferzeit,
behält aber die Jahresmenge und alle numerischen Basiswerte bei.

Wenn zusätzlich numerische Sensitivitätsparameter ausgewählt sind, werden deren
Varianten nur für die ausdrücklich gewählten **Basisprofile** berechnet.
Zusätzliche Kategorien werden als eigene unveränderte Basisfälle ergänzt.
Das hält OAT ein. Beispiel: Basis D0 + zwei Preisvarianten + Profilstufen
D0/D1/D2 ergibt pro Szenario fünf Fälle: Basis D0, zwei Preisvarianten auf D0,
Basis D1, Basis D2. Es werden keine Preisvarianten auf D1/D2 still ergänzt.

Wer Nachfragemengen für alle drei Profile untersuchen möchte, wählt D0/D1/D2
ausdrücklich als Basisprofile plus Nachfragefaktoren. Fünf Mengenniveaus ×
drei Basisprofile × drei Szenarien = 45 Fälle je Standort. Zwei Standorte
erfordern zwei ausdrücklich gewählte Standortaufträge.

### 5.3 Werte und gemeinsame Belegungshilfe

Explizite Werte mit Semikolon trennen. Dezimalkomma ist erlaubt; beispielsweise
`750; 1.250` ist kein verlässliches Tausenderformat, verwenden Sie **`750; 1250`**.
Alternativ Minimum, Maximum und Schrittweite wählen. Ungültige Entwürfe bleiben
sichtbar und dürfen keinen älteren gültigen Parametersatz starten.

Technische Parameter können mit **Direkte Parameterwerte** oder
**Änderung zur Basis [%]** eingegeben werden. Die GUI hält absolute und relative
Entwürfe getrennt. WACC-Verschiebungen sind Prozentpunkte, ein einheitlicher
WACC ist Prozent; native Bruchteile entstehen durch nachvollziehbare Umrechnung.
WACC-Faktoren und Nachfragefaktoren sind dimensionslos.

Die allgemeine Belegungshilfe **Gemeinsame Namibia-/EU-Stufen** bleibt erhalten.
Sie belegt 15 OAT-Varianten: sieben bisherige Parameterfamilien, relative
technische Änderungen wie im Namibia-Fall; Preisoffset ±50 % des jeweiligen
Jahresmittels und WACC-Faktoren 7/11 bzw. 15/11. Standortpreise werden getrennt
gelesen. Bei einem Basisprofil und S0/S1/S2 sind es 48 Läufe einschließlich
je einmaliger Basis. Die Belegungshilfe setzt absolute/relative Interpretation
konsistent zurück; prüfen Sie die sichtbaren Werte vor dem Rechnen.

### 5.4 Gespeicherte Sensitivitäten

Die gespeicherte Versuchsreihe, deren Profil, berechneten Einfluss und Zielgröße
wählen. Bei mehreren Profilen zeigt eine Kurve nur das ausdrücklich gewählte
Profil. Nachfragekurven enthalten die passende 100-%-Basis desselben Versuchs;
eine andere historische Referenz wird nicht ersatzweise hineinkopiert.
Andere OAT-Familien behalten ihre bestehenden Basis-/Variantensemantik.
Vollständig identische Versuchsreihen erscheinen einmal; teilweise überlappende
Familien bleiben getrennt.

## 6. Vergleich: gezielt nebeneinander

**Vergleich** öffnen. Die gewünschten gespeicherten Fälle ausdrücklich wählen,
dann Ergebnisgröße, Diagrammtyp und optional Gruppierung festlegen. Beispiele:
Hamburg S0/S1/S2; Hamburg/Huelva mit demselben D0/S0; D0/D1/D2 bei derselben
Standort-/Szenariobasis; Basisfall und einzelne Sensitivitätsfälle.

Eine Grafik zeigt nur diese Auswahl. Vollständige Fallbezeichnungen und
Einheiten bleiben in der danebenstehenden Tabelle. Bei vielen Fällen die
Auswahl verkleinern oder die vorhandene Begrenzung/Seiteneinteilung nutzen.
Es wird nicht automatisch der gesamte Datenbestand geplottet.

Namibia/EU besitzen unterschiedliche Wetter-, Preis-, Finanzierungs- und
Faktorreferenzen. Der Quellenkontext und die Vergleichswarnung sind Bestandteil
der Interpretation. Ein bloß ähnlicher LCOH beweist keine Gleichheit der
Annahmen oder der wissenschaftlichen Fälle.

## 7. Quellen und unabhängige Validierung

**Quellen** zeigt Wetter, Strompreise, Emissionsfaktoren, Kosten, WACC und
Nachfrageannahmen mit Herkunft und Jahresrollen. Details zur nativen
Basiskonfiguration, Quellen-/Inputverträgen, Hashes, Fallstudiendokumentation
und Solverprobe stehen in aufklappbaren Abschnitten. Die GUI aktualisiert
Quellen nicht automatisch.

| EU-Jahresrolle | Bezug |
|---|---|
| Wetter, Betrieb, Marktpreise | Historisch 2024; 8.784 Stunden |
| Kosten und reale Stundenpreise | Reale EUR 2023 |
| Betriebliche Emissionen | Nationaler statischer Jahresfaktor 2024 |
| WACC | Quellenjahr 2021 als dokumentierter Finanzierungsproxy |
| Regulatorische elektrische Teilbilanz | Gesonderte rechtliche Referenz 2020 |
| Ergebniserstellung | Tatsächlicher Berechnungszeitpunkt in UTC |

Reale EUR 2023 sind keine Wetterdaten aus 2023. Namibia-TMY 2007–2016 mit
technischem Indexjahr 2025 ist kein gemessenes 2025-Wetterjahr. Die statischen
Emissionsfaktoren sind keine stündlichen, marginalen oder standortgenauen
Verbrauchsfaktoren; die spanische nationale Produktionsreferenz ist ein
offengelegter Proxy für Huelva.

Die Validierung ist beim gewählten Ergebnis und unter Quellen erreichbar.
Drei Aussagen sind zu trennen:

| Anzeige | Bedeutung |
|---|---|
| Solver **optimal** | Der Solver meldet eine optimale Lösung seines Modellfalls. |
| Auftrag **completed** | Der Hintergrundauftrag ist technisch abgeschlossen; die unabhängige Prüfung muss separat gelesen werden. |
| Gebundene Prüfung **passed** | Der unabhängige native Bericht deckt den ausgewählten Fall ab und sein Quellenvergleichs-Hash stimmt. |
| **partial_scenario_selection** | Keine vollständige S0/S1/S2-Abnahme aufgrund bewusst begrenzter Szenarioauswahl. |
| **not_found / not_run** | Kein zugeordneter unabhängiger Bericht beziehungsweise Prüfung nicht durchgeführt. |
| **failed_or_changed** | Bericht scheitert oder seine Vergleichsquelle wurde verändert. |

Eine vollständige Szenarioabnahme setzt S0/S1/S2 gemeinsam voraus. Ein einzelner
S0-Lauf kann Teilvalidierung haben; dies entschuldigt keine sonstigen Prüfungs-
oder Bilanzfehler. Ein globaler Jobstatus wird nicht als Validierungsnachweis
auf einzelne Fälle oder identische Kopien übertragen.

## 8. Laufstatus, Ablage und identische Ausführungen

Fortschritt steht unmittelbar im Berechnungsbereich. **3/3 abgeschlossen**
bezieht sich auf drei Modellfälle, nicht automatisch auf alle Prüfungen.
Nachfolgende Validierung und endgültiger Status bleiben sichtbar; die
Resultate folgen darunter. Jeder Auftrag schreibt einen eigenen Ordner unter
`outputs_h2/gui_runs/<Job-ID>/`, einschließlich Plan/Hash, eingefrorener Quellen,
nativer Resultate, Status und Protokolle. Die angezeigten neuen Resultate sind
auf diesen Auftrag begrenzt und werden nicht mit allen älteren Jobs vermischt.

Der Browser kann geschlossen werden, während der Worker weiterarbeitet.
Ein PC-Neustart beendet Prozesse; unvollständige Aufträge starten danach nicht
automatisch. Ein komfortables Stoppen/Fortsetzen laufender Jobs ist nicht
hinzugefügt worden. Fehlgeschlagene Jobs können bereits einzelne optimale
native Exporte besitzen. Sie bleiben als teilweise/unvollständig gekennzeichnet.

Nachweislich identische gespeicherte Analysen erscheinen einmal; unterschiedliche
Eingaben, Parameter, Jahre, Solver, Stundenlösungen oder Prüfkontexte bleiben
getrennt. Bei einem zusammengefassten Fall können Sie sämtliche ursprünglichen
Ausführungen und Herkunfts-/Prüfbelege ansehen. `__result_copies` bewahrt sie
auch im CSV. Kein Ergebnis oder Originaljob wird hierfür gelöscht. Eine neue
ausdrücklich gestartete Berechnung verwendet weiterhin ihren eigenen Auftrag.

## 9. Export und wissenschaftliche Reproduktion

Unter **Export** die sichtbaren Profil-, Szenario- und Solverfilter kontrollieren,
gewünschten nativen Fall wählen und dann herunterladen:

- **CSV**: genau die sichtbare Ergebnistabelle, einschließlich aller Original-
  belege in `__result_copies`.
- **Native Metadaten (JSON)**: `run_metadata.json` des gewählten Falls.
- **Native Ergebnisdateien (ZIP)**: `summary.csv`, `hourly_operation.csv`,
  `validated_input.csv` und `run_metadata.json`, soweit vorhanden.
- **Grafik**: die ausdrücklich gewählte Darstellung als eigenständige Datei.
- **Vergleichsdaten**: die gezielt ausgewählten Vergleichsfälle.

Downloads gehen in den Browser-Downloadordner; Originaldateien werden nicht
verschoben. Ein nativer Ergebnis-ZIP enthält keinen vollständigen eingefrorenen
Job. Für Reproduzierbarkeit zusätzlich ursprünglichen Jobordner mit Quellen,
Plan/Hash, Konfigurationsbelegen und gebundenen Prüfberichten aufbewahren.

## 10. Fehlerbehebung und wissenschaftliche Grenzen

| Problem | Nächster Schritt |
|---|---|
| Browserverbindung fehlt | Zentralen CMD-Starter öffnen; `outputs_h2/gui_runtime/server.log` prüfen. |
| Alte Oberfläche sichtbar | Nach dokumentiertem Serverneustart Browser neu laden. |
| Berechnen ist nicht möglich | Sichtbare Warnungen lösen: mindestens Profil/Szenario, freigegebener Standort und gültige Werte. |
| Kein gespeichertes Ergebnis | Standort und gespeicherte Filter prüfen; leere Auswahl ergibt bewusst keine Fälle. |
| Gurobi-Jahresmodell scheitert | Lizenzprobe unter Quellen lesen; ausreichende Lizenz oder ausdrücklich HiGHS wählen. |
| Auftrag bleibt unvollständig | Jobstatus und `worker.log`/`native.log` lesen; keinen automatischen Neustart annehmen. |
| Optimal, aber Validierung fehlt | Den ausgewählten unabhängigen Bericht und Quellenbindung prüfen. |
| Unerwartet gleicher Nachfrage-LCOH | Lineare Neuauslegung und fehlende Größendegression beachten; Jahreskosten und alternative Optima lesen. |
| Kurve wirkt vermischt | Dieselbe gespeicherte Familie und genau ein Lieferprofil wählen; Herkunftstabelle prüfen. |

Die Optimierung besitzt vollständige Kenntnis des historischen Jahresverlaufs;
sie ist keine Preisprognose. Nationale statische Emissionen, WACC-Proxies und
elektrische RED-Teilprüfung bleiben offengelegte Grenzen. Neue Länder,
Technologien, Jahresdatensätze oder freie Komponenten-WACC benötigen ein neues
wissenschaftlich geprüftes Design und vorbereitete Inputs.

Vor einer Berechnung Forschungsfrage, Standort, Profile, Szenarien, Solver,
Jahresrollen und Laufanzahl prüfen. Vor einer Interpretation native Fallidentität,
Einheiten, Bilanzgrenzen und unabhängige Belege lesen. Vor dem Export die
sichtbare Tabelle und ausgewählte native Datei kontrollieren.
