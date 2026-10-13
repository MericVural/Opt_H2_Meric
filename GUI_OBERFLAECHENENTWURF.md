# Oberflächenentwurf D1 für die H₂-Analyse-App

**Stand: 12. Oktober 2026 · D1 konkretisiert, U1 und sichtbare U2-Oberfläche umgesetzt. U3 und vollständige U4-Abnahme offen.**

Dieser Entwurf konkretisiert den [Neuaufbauplan](GUI_NEUAUFBAU_PLAN.md) und die dort dokumentierten 19 Mängel. Er legt fest, was auf einer Arbeitsfläche sichtbar ist, welche Angaben eine Untersuchung benötigt und wie ein Ergebnis bis zum Export eindeutig zugeordnet bleibt. Die wissenschaftlichen Gleichungen, Datenjahre und bestehenden Ergebnisdateien werden dadurch nicht verändert. Den erreichten U1-Teilstand beschreibt Abschnitt 14 mit Verweis auf [GUI_U1_ABNAHME.md](GUI_U1_ABNAHME.md); der aktuelle sichtbare U2-Stand ist im [U2-Nachweis](GUI_U2_ABNAHME.md) dokumentiert; verbleibende Entwurfsanforderungen sind dort als offen benannt.

## 1. Die wesentlichen Entwurfsentscheidungen

| Entscheidung D1 | Wirkung für die Bedienung |
|---|---|
| Zuerst eine verständliche Untersuchungsfrage auswählen | Der Nutzer muss die passende Kombination aus Profil, Szenario und Sensitivitätsparameter nicht selbst herleiten. |
| Einstellungen und Ergebnisse auf derselben Arbeitsfläche | Keine zusätzliche Start-, Planungs- oder Ergebnisseite; der aktuelle Bezugsfall bleibt sichtbar. |
| Wenige feste Ergebnisansichten | Keine freie Kombination von 26 Kennzahlen mit beliebigen Diagrammtypen. Jede Ansicht hat eine fachliche Aufgabe. |
| Fachliche Auswahl und technische Details getrennt gewichten | Alle freigegebenen Parameter und Solver bleiben zugänglich; Alltagsaufgaben benötigen wenige Angaben. |
| Gespeicherte passende Untersuchungen zuerst anbieten | Vorhandene Resultate lassen sich öffnen, ohne die Rechnung zu wiederholen. Eine bewusste Neuberechnung bleibt möglich. |
| Untersuchung und angezeigter Ausschnitt ausdrücklich unterscheiden | Eine 90-Fälle-Untersuchung darf beispielsweise auf Hamburg/D0 eingegrenzt dargestellt werden, ohne ihren ursprünglichen Umfang zu verändern. |
| Ein Fallbezug für Tabelle, Betrieb, Quellen, Prüfung und Export | Eine angezeigte Grafik kann nicht versehentlich Daten des vorherigen Standorts exportieren. |

Das ist eine begründete Arbeitsentscheidung für D1, keine bereits vom Nutzer abgenommene neue Bedienung. Die bisherigen offenen Vorschläge werden damit konkret: acht Ziele nach fachlicher Aufgabe, Jahreskosten als erste Nachfragegrafik, Anlagengrößen als zweite Ansicht; beide EU-Standorte können in einer Untersuchung enthalten sein. Gemeinsame neue Standortaufträge erfordern zusätzliche GUI-Orchestrierung, während die vorhandene 90-Fälle-Untersuchung bereits lesbar ist.

## 2. Aufbau der Anwendung

Die fünf Hauptbereiche bleiben **Analyse · Sensitivitätsanalyse · Vergleich · Quellen · Export**. Die Navigation steht auf breiten Bildschirmen links, auf schmalen Bildschirmen oberhalb des Inhalts. Nur der aktive Bereich besitzt fachliche Auswahlfelder; kein globaler Hamburg-Filter über einem standortübergreifenden Vergleich.

Die erste sichtbare Frage im Bereich Analyse lautet **„Was möchten Sie untersuchen?“**. Es erscheinen vier kurze Ziele: Anlage auslegen, Stromregeln vergleichen, Betrieb ansehen, Solver vergleichen. Die Bereichsnavigation führt zu Sensitivitätsanalyse mit drei weiteren Zielen und zu Vergleich mit dem achten Ziel. Eine lokale Zielauswahl ist kein weiterer Navigationsschritt und lädt kein neues Modell.

```text
H₂ Forschungsmodell                  Entwurf / Untersuchung / Ergebnisstatus
Analyse | Sensitivitätsanalyse | Vergleich | Quellen | Export

Was möchten Sie untersuchen?  [fachliche Ziele des aktuellen Bereichs]

[Studie und Standort(e)]   [Lieferprofil(e)]   [passende Szenarien/Variation]
Weitere Einstellungen ▸ Solver · vollständige Parameter · Quellen

Ihre Untersuchung
Was ändert sich? · Was bleibt gleich? · Anzahl der Modellfälle
Vorhandene passende Ergebnisse / nötige neue Berechnungen
[Ergebnisse öffnen]                              [Neu berechnen …]

Auftrag und Fortschritt – nur wenn ein Auftrag existiert

Ergebnis: Name der Untersuchung · Herkunft · Prüfstatus
Angezeigter Ausschnitt: Standort · Profil · Parameter / ausgewählter Fall
[Kosten] [Auslegung] [Betrieb] [Emissionen]
Passende Kennzahlen + eine Hauptgrafik
[Daten / Grafik herunterladen]    [Konkreten Fall öffnen]
Alle Ergebniswerte ▸   Modellprüfung ▸   Quellen und Ausführungen ▸
```

Die Ergebnisreiter sind Ansichten innerhalb einer Arbeitsfläche, keine weiteren Hauptseiten. Nur sinnvolle Reiter erscheinen; ein Solververgleich beginnt beispielsweise mit seiner Ergebnistabelle. Die vollständigen Werte bleiben überall erreichbar. „Weitere Einstellungen“ ist ein benannter Detailbereich, kein zusätzlicher Bestätigungsdialog.

## 3. Acht Ziele und ihre konkreten Felder

| Ziel / Bereich | Direkt sichtbare Angaben | Weitere Einstellungen | Erste Auswertung |
|---|---|---|---|
| **Anlage auslegen** / Analyse | Studie, ein Standort, ein Lieferprofil, ein Szenario | Mehrere Profile/Szenarien ausdrücklich als Fallgruppe; Solver/Auto; vollständige Basiskonfiguration lesbar | LCOH, Jahreskosten, Lieferung; PV/Wind/PEM/Kompressor in MW und Speicher separat in t |
| **Stromregeln vergleichen** / Analyse | Standort, ein Profil, mindestens zwei Szenarien; S0/S1/S2 vorgewählt | S3 ohne Netzanschluss, zusätzliche Basisprofile, Solver | LCOH-Balken; Auslegung, Kostenbestandteile und Emissionen als weitere Ansichten |
| **Betrieb ansehen** / Analyse | Vorhandene Untersuchung, genau ein Fall, Ortsdatum | Tages-/Stundenzeitraum; Gesamterzeugung statt Direktversorgung; H₂-Betrieb | Stündliche Versorgung bzw. kumulative Tagesenergie |
| **Solver vergleichen** / Analyse | Ein Standort, gleiche Profile/Szenarien für beide Solver | Gemeinsame Modelloptionen; Verfügbarkeits-/Lizenzprobe | Kosten, Optimalitäts-/Prüfstatus und Laufzeit in einer Tabelle; bei Bedarf Kapazitäten |
| **H₂-Nachfragemenge verändern** / Sensitivitätsanalyse | Standort(e), Profil(e), Mengenstufen in % und kg/a, Szenarien | Weitere native Parameter als getrennte OAT-Reihen, direkte Werte/Bereiche, Solver | Jahreskosten über der Jahresnachfrage; Auslegung und LCOH danach |
| **Lieferzeiten verändern** / Sensitivitätsanalyse | Standort(e), mindestens zwei Lieferprofile, Szenarien; feste Jahresmenge sichtbar | Weitere numerische OAT nur für ausdrücklich gewählte Basisprofile | LCOH und Speicher als getrennte, kategorische Diagramme |
| **Kosten, Finanzierung oder Technik verändern** / Sensitivitätsanalyse | Standort(e), Basisprofil(e), Parametergruppe → Parameter und Stufen; Szenarien | Explizite Werte/Bereich, direkte/relative Eingabe, gemeinsame Namibia-/EU-Stufen, Solver | Wirkung des gewählten Parameters auf LCOH, mit eigener Basis; andere fachliche Zielgrößen unter Auslegung/Betrieb/Emissionen |
| **Standorte oder vorhandene Fälle vergleichen** / Vergleich | Vergleichsfrage, vorhandene Studien/Standorte/Fälle; Gemeinsamkeiten und Unterschiede | Freie Fallgegenüberstellung mit ausdrücklich deskriptiver Interpretation | LCOH und Vergleichsgrundlagen; passende weitere Ansichten |

D0 heißt **„Rund um die Uhr“**, D1 **„Täglich 08–20 Uhr“**, D2 **„Mo–Fr 08–20 Uhr“**, jeweils Ortszeit. Kürzel bleiben sichtbar. Lieferzeiten sind keine Produktionsverbote. Namibia bietet nur seinen registrierten D0-Bestand und die dort freigegebenen Parameter. Nicht vorhandene Profile werden nicht als deaktivierte scheinbare Möglichkeiten angeboten.

Der ursprüngliche Standard bleibt ein Solver, **SciPy/HiGHS**. „Gurobi“ und „Auto“ bleiben explizit wählbar. „Solver vergleichen“ bedeutet genau zwei Backend-Ausführungen pro Fall; ein zusätzlicher Vergleichsschalter darf diese Zahl nicht nochmals verdoppeln. Solver-Verfügbarkeit ersetzt weder eine erfolgreiche Lösung noch eine unabhängige Ergebnisprüfung.

## 4. Die Nachfrageanalyse vollständig durchspielen

### 4.1 Einstellungen

```text
Sensitivitätsanalyse / H₂-Nachfragemenge verändern

Standorte       [✓ Hamburg–Moorburg] [✓ Huelva–La Rábida]
Lieferprofile   [✓ D0 Rund um die Uhr] [✓ D1 Täglich] [✓ D2 Mo–Fr]
Szenarien       [✓ S0 Referenz] [✓ S1 Monatlich] [✓ S2 Stündlich]
Jahresnachfrage [50 %] [75 %] [100 % Basis] [125 %] [150 %]
Weitere Stufen / Bereich ▸

100 % = 3.650.000 kg/a je Standort und Profil
Ihre Untersuchung: 2 Standorte × 3 Profile × 3 Szenarien × 5 Mengen = 90 Fälle
Für jede Menge wird eine neue kostenoptimale Anlage ausgelegt.

[Vorhandene Untersuchung öffnen]    Neu berechnen …
```

Mengenfelder akzeptieren in der normalen Bedienung Prozentwerte. Die GUI zeigt parallel kg/a und übergibt erst intern Faktoren an den bestehenden Runner. 100 % ist genau einmal Bestandteil jeder Referenzreihe. Eine weitere Stufe wird auf positive, endliche Werte geprüft; doppelte Stufen werden mit verständlichem Hinweis zusammengeführt. Benutzerdefinierte Stufen sind Szenarien, keine prognostizierten Unsicherheitsgrenzen.

Die vorgeschlagenen fünf Mengen entsprechen **1.825.000 / 2.737.500 / 3.650.000 / 4.562.500 / 5.475.000 kg/a**. Für einen Standort/D0/S0–S2 entstehen 15 Fälle; für beide Standorte/D0–D2/S0–S2 90. Die gesamte Untersuchung wird nicht in eine Grafik mit 18 Kurven gedrängt.

### 4.2 Ergebnisse

Die Kopfzeile nennt **„H₂-Jahresnachfrage 50–150 % · EU 2024 · 90 Fälle“** samt tatsächlicher Herkunft und Prüfdeckung. Darunter steht **„Angezeigt: Hamburg · D0 · S0/S1/S2“**. Standort und Profil wechseln den sichtbaren Ausschnitt, nicht die Definition der gespeicherten Studie. „Beide Standorte nebeneinander“ zeigt zwei Panels mit derselben Achsengrundlage, sofern die Werte vergleichbar sind.

Die Hauptgrafik zeigt Jahreskosten in Mio. EUR 2023/a über der Nachfrage in %; die zugehörigen kg/a stehen in der Tabelle und Punktinformation. Weitere Ansichten:

- **Kosten:** Jahreskosten zuerst, LCOH direkt erreichbar; Kostenbestandteile nur für einen konkreten Nachfragepunkt oder einen gezielten kleinen Vergleich.
- **Auslegung:** Leistungsgrößen in MW; H₂-Speicher separat in t. Keine gemeinsame Achse für MW und kg.
- **Betrieb:** Jahresnetzbezug und weitere betriebliche Kennzahlen; bei Auswahl eines konkreten Punktes „Tagesbetrieb öffnen“.
- **Emissionen:** betriebliche und regulatorische Größen getrennt; eigene Basis und passende Referenz.

Unter der Grafik bleibt kurz sichtbar: **„Jede Menge wird neu ausgelegt. Das lineare Modell enthält keine Größendegression; LCOH können nahezu konstant bleiben.“** Die GUI zieht keine Aussage über Engpässe einer feststehenden Bestandsanlage. Ein Punkt darf per zugänglicher Fallauswahl oder direkt aus einer Grafik geöffnet werden; die Tabelle bleibt eine vollständige Alternative zur Mausbedienung.

## 5. Szenarien und Emissionen vollständig durchspielen

Standort Hamburg, D0 und Basisnachfrage wählen, dann S0/S1/S2. Die Vorschau lautet **„3 Fälle, nur Stromversorgungsregel verändert“**. Ein abweichender Preis-/Inputvertrag verhindert die Beschriftung als kontrollierter Szenarienvergleich und wird als Unterschied ausgewiesen.

Die Ansicht **Emissionen** enthält zwei getrennte Diagramme: betriebliche Stromemissionsintensität und regulatorische elektrische Teilintensität, beide in kg CO₂e/kg gelieferter H₂. Nur im zweiten Diagramm steht die passende gestrichelte Produktreferenz aus dem nativen Ergebnis. Bei gleicher Referenz erscheint eine Linie. Nullwerte erhalten eine sichtbare Beschriftung; die Achse zeigt auch bei null liegenden Ergebnisbalken den Grenzwert.

Der kurze Hinweis lautet: **„Produktgrenzwert als Referenz; dargestellt ist nur die elektrische Teilbilanz.“** Absolute Jahresemissionen besitzen eine eigene Ansicht ohne Intensitätsgrenzlinie. Bei mehreren inkompatiblen Referenzen werden die Kontexte getrennt. Bereits erarbeitetes Beispiel: [Emissionen je Szenario](gui/planungsbeispiele/emissionen_20261010/Emissionen_Szenarien_Planungsbeispiel.png).

## 6. Tagesbetrieb vollständig durchspielen

Der Einstieg **„Betrieb ansehen“** sowie „Tagesbetrieb öffnen“ an jedem berechneten Fall führen auf dieselbe Ansicht. Sie übernimmt Studie, Standort, Profil, Szenario, Variante, Solver und ausgewählte Ausführung. Ein Nachfragepunkt mit 75 % bleibt derselbe Punkt; es wird nicht stillschweigend der 100-%-Basisfall geöffnet.

```text
Hamburg · D0 · S2 · 100 % Nachfrage · gewählte gespeicherte Ausführung
Betrieb  |  Stromversorgung

Tag: [02.01.2024]                 [Stündlich] [Kumulativ]
Direktversorgung                 Weitere Darstellung ▸

Solar direkt · Wind direkt · Netzbezug · Strombedarf
Ortszeit Europe/Berlin · 24 Stunden · Energie in MWh

[Grafik herunterladen] [Genau diese Tagesdaten]
H₂-Produktion, Lieferung und Speicher ▸
```

„Stündlich“ verwendet native MWh pro Stundenintervall. „Kumulativ“ beginnt am lokalen Tagesanfang bei null und summiert bis zum Ende des Tages. Kumulativer Strombedarf wird ebenfalls kumuliert; kein Mischen mit stündlicher Leistung. Bei Direktversorgung summieren sich direkte PV-/Windnutzung und Netzimport zum Prozessstrombedarf innerhalb der Modellgenauigkeit. Die Alternative „Gesamterzeugung und Netzbezug“ benennt Überschüsse ausdrücklich.

Frühjahrs-/Herbsttage besitzen 23/25 Stunden; wiederholte Uhrzeiten erhalten UTC-Offset. Start- und Endzeit sind Intervallgrenzen. Tage ohne vollständige native Stunden bekommen eine konkrete Meldung. Bei frei gewählten mehrtägigen Stundenfenstern sind tatsächliche Dauer und Kürzung am Jahresende sichtbar. Die H₂-Ansicht trennt Produktion/Lieferung von Speicherbestand und benennt den Zeitpunkt des Speicherwerts.

## 7. Vollständige Parameter und Ergebnisgrößen erhalten

Der Parametereditor wird nach **Strompreis**, **Finanzierung**, **Technik**, **Nachfrage** gegliedert. Ein gewähltes Analyseziel belegt denselben Editor vor. Die Kategorien sind keine neuen Sensitivitätsmethoden.

| Gruppe | Freigegebene Eingaben | D1-Darstellung |
|---|---|---|
| Strompreis | Konstanter Preis, wo freigegeben; Preisreihenoffset | EUR/MWh und tatsächliche Geldbasis; historische EU-Reihe als additive Verschiebung; Herkunftsvertrag entscheidet auch bei alten gespeicherten Familiennamen |
| Finanzierung | Komponenten-WACC verschieben oder multiplizieren | Prozentpunkte bzw. Faktor; für gemeinsamen Vergleich 7/11 und 15/11 plus tatsächliche Komponentenwerte |
| Technik | PV-, Wind-, PEM-, Speicher-CAPEX; spezifischer PEM-Strombedarf; native PEM-Faktoren | Einheit/Bezugswert sichtbar; direkte Werte oder relative Prozentänderung; explizite Stufen oder Bereich |
| Nachfrage | Jahresnachfragefaktor und Lieferprofil | Prozent + kg/a; Profile mit Ortsfenster und gleicher Jahresmenge |

Die vollständige verbindliche Liste bleibt in [Neuaufbauplan, Abschnitt 6](GUI_NEUAUFBAU_PLAN.md#6-bestandsliste-der-parameter-vor-dem-neuen-umbau) und [GUI_BESTANDSLISTE.md](GUI_BESTANDSLISTE.md). D1 hat die gesamte Liste gegen `sensitivity_parameter_choices` und die Registry lesend abgeglichen: 13 native numerische Parameter, elf freigegebene je Studie, kategorische EU-Profile. Der einheitliche freie WACC bleibt nativ dokumentiert und wie bisher nicht allgemein als GUI-Regler angeboten. Der EU-Konstantpreis und die Namibia-Nachfrageskalierung werden nicht stillschweigend freigegeben.

**OAT-Regel:** Mehrere numerische Parameter erzeugen getrennte Einzelfaktorvarianten, keinen Kreuzversuch. Innerhalb eines Standorts gilt bei einheitlicher Szenarienwahl:

`Anzahl = (Basisprofile × (1 + numerische Varianten) + zusätzliche reine Profilstufen) × Szenarien × Solver`

Die 100-%-Nachfragebasis zählt in der „1“, nicht nochmals in Varianten. Standortabhängig unterstützte Kontexte werden einzeln gezählt und dann addiert. Zusätzliche Profilstufen ohne numerischen Basisauftrag erhalten ausschließlich ihren eigenen unveränderten Basisfall. Gleiche numerische Wirkung mit unterschiedlichen Quellen-/Versuchsverträgen wird nicht nur aufgrund gleicher Werte zusammengelegt.

Sämtliche Ergebniskennzahlen bleiben als Tabelle/Export erhalten. Ergebnisgrößen besitzen fachliche Ansichten; Referenzen ergänzen diese; Prüfgrößen stehen unter **Modellprüfung**. Sinnvolle Diagrammformen werden automatisch bestimmt. Die Möglichkeit zu technischen Diagnoseauswertungen bleibt erhalten, ohne dass der normale Nutzer Grenzwerte oder Residuen als Wirtschaftlichkeitskurven auswählen muss.

## 8. Ergebnisse, Quellen und Exporte

### 8.1 Wiederfinden und Vergleichbarkeit

Die Ergebnisliste zeigt fachliche Kurznamen wie **„Hamburg · D0 · S2 · Nachfrage 75 %“** mit Solver- und Prüfstatus. Identische belegte Ausführungen sind eine Hauptzeile mit aufklappbarer Ausführungshistorie. Der Nutzer kann jede Originalausführung weiterhin öffnen; eigene Hashes und Prüfberichte bleiben erhalten. Gleiche gerundete Kosten reichen nicht als Identitätsbeweis.

Gespeicherte Resultate werden nur als passend bezeichnet, wenn der relevante Input-/Modell-/Parameter-/Szenario-/Solververtrag übereinstimmt. Ein ähnlicher historischer Fall darf lesend geöffnet werden, wird aber als solcher benannt. Teilweise verfügbare Untersuchungen nennen vorhandene, fehlende und ungeprüfte Fälle separat. Keine automatische Neuberechnung fehlender Fälle.

Der Standortvergleich verwendet eigene Auswahlfelder und eine kompakte Tabelle **„Gleich gehalten / Unterschiedlich“**. Unvergleichbare historische Grundlagen bleiben zugänglich, aber die Darstellung behauptet keinen isolierten Standorteffekt. Alternative Solveroptima werden erklärt, statt unterschiedliche Kapazitäten bei nahezu gleichen Kosten automatisch als Modellfehler zu bewerten.

### 8.2 Quellen und Modellprüfung

Am Ergebnis steht eine Basiszeile: **„Betriebsjahr 2024 · reale EUR 2023 · WACC-Proxy 2021 · 300-bar-Lieferpunkt“**, soweit diese Angaben zum konkreten Fall gehören. Namibia erhält seine eigene Basiszeile. „Quellen dieses Falls“ übernimmt die Ergebnisidentität. Der Hauptbereich Quellen erlaubt zusätzlich eine ausdrückliche unabhängige Studien-/Standortwahl.

Wetter, Preise, Emissionsfaktoren, technische Kosten, WACC und Nachfrage erscheinen mit verständlicher Bezeichnung, Wert/Einheit, Herkunft, Jahr und Einschränkung. Native Parameter und vollständige Verträge bleiben aufklappbar. Die regulatorische Referenz ist eine eigene normative Jahresrolle; sie wird nicht an den operativen Faktor angeglichen. Quellenabweichungen werden erklärt, nicht kosmetisch umdatiert.

Die Modellprüfung nennt separat Solverergebnis, physische Bilanzprüfungen, regulatorische Teilprüfungen und unabhängige Exportprüfung. Vollständige Residuen, Toleranzen, Prüfumfang, Hashbindung und Originalbericht bleiben erreichbar. „Optimal gelöst“ ist keine vollständige Validierung; regulatorische Teilprüfung ist keine vollständige Zertifizierung.

### 8.3 Export

Direkt bei einer Grafik: **PNG · SVG · Grafikdaten CSV**. Bei der Untersuchung: **angezeigte Ergebnistabelle** oder ausdrücklich **vollständige Untersuchung**. Bei einem konkreten Fall: **native Dateien ZIP · Metadaten JSON · Prüfnachweis JSON**. Der Hauptbereich Export bündelt dieselben kontextgebundenen Aktionen und bietet keinen losgelösten „letzten“ Zustand an.

Die Exportkarte nennt Untersuchung, Standort, Profil, Szenarien/Variante, Größe, Zeitfenster und Datenbasis. Diagramm und CSV entstehen aus demselben vorbereiteten Datensatz. Daten ohne sichtbare Kurve gehören nur in einen separat bezeichneten Gesamtexport. Dateinamen sind verständlich, z. B. `hamburg_D0_S2_100pct_2024-01-02_kumulativ.csv`; die Metadaten tragen vollständige IDs und Hashes. Fehlende Werte werden nicht als null ausgegeben.

## 9. Zustände und Fehlersituationen

| Zustand | Sichtbare Rückmeldung / erlaubte Aktion |
|---|---|
| Noch keine Untersuchung | Ziel wählen; keine scheinbar zugehörigen alten Kennzahlen oder Exporte |
| Gültige Einstellungen | Variationsübersicht und Fallanzahl; passende Ergebnisse öffnen oder ausdrücklich rechnen |
| Ungültige Eingabe | Meldung direkt am Feld mit Einheit und zulässigem Bereich; Entwurf bleibt erhalten |
| Eingabe seit Ergebnisanzeige geändert | Altes Ergebnis klar als vorherige Untersuchung benennen; neue Einstellungen haben noch kein Ergebnis; keine stillschweigende Umbeschriftung |
| Auftrag läuft | Auftragstitel, abgeschlossene/vorgesehene Fälle, aktueller Standort/Fall; denselben Auftrag öffnen statt versehentlich nochmals starten |
| Berechnung beendet, Prüfung läuft | Beides sichtbar trennen; vorhandene Werte mit echtem Prüfstatus öffnen |
| Vollständig geprüft | Übersicht der eigenen Prüfdeckung; keine automatische Aussage über die vollständige wissenschaftliche Realweltgültigkeit |
| Unterbrochen oder teilweise vorhanden | Ursache soweit belegt, Zahl nutzbarer/fehlender Fälle; vorhandene Resultate öffnen, bewusste neue Ausführung vorbereiten |
| Kein passendes Ergebnis / Kennzahl fehlt | Konkrete Information; keine erfundene Null, keine veraltete Grafik und kein dazu irreführender Download |
| Quelle verändert / Hash passt nicht | Reproduzierbarkeit als ungeklärt benennen; gespeicherten Originalnachweis zugänglich halten |

Aufträge bleiben nach Browser-Reload auffindbar. Ein Worker wird anhand PID **und** Prozessstartzeit/Heartbeat identifiziert. Wiederholung und eventueller Abbruch beziehen sich auf den eindeutig bestimmten Auftrag; ein Rechnerneustart erzeugt keinen automatischen Wiederholungsauftrag. Fertige Aufträge werden nicht weiterhin im Drei-Sekunden-Takt neu geladen.

## 10. Technischer Vertrag für die spätere Umsetzung

Vier getrennte, versionierte Datensätze sind vorgesehen; diese Namen sind konzeptionell und noch keine implementierten Klassen:

| Vertrag | Mindestinhalt | Schutzwirkung |
|---|---|---|
| **Untersuchungsentwurf** | Ziel, Studien/Standorte, Basisprofile, Szenarien, native Parameter/Operationen/Stufen, Solver, Input-/Code-/Quellenbezug, berechneter Fallumfang | Reproduzierbare Vorschau; keine versteckten Kreuzkombinationen |
| **Auftrag** | eingefrorener Untersuchungsvertrag, untergeordnete native Pläne, Planhash, Ausführungs-ID, Prozessidentität, Fallstatus, Zeitstempel | Doppelte aktive Starts erkennen, Fortschritt wiederfinden; Revisionen erhalten |
| **Ergebnisauswahl** | Untersuchung/Familie, konkrete Fall- und Ausführungs-IDs, native Pfade/Hashes, Filter, Referenzzuordnung, Prüfdeckung | Keine Vermischung ähnlicher Fälle oder fremder Basiswerte |
| **Diagramm und Export** | Ergebnisauswahl, fachliche Ansicht, Kennzahlen/Einheiten, Zeitfenster, Transformation, exakte dargestellte Datentabelle, Referenzwerte | Bild und CSV entsprechen sich; Kontextwechsel invalidiert alten Export |

Die UI erzeugt keine Modellgleichungen. Neue Rechnungen verwenden vorhandene native Planbauer/Runner. Für mehrere Standorte komponiert die GUI je Standort den passenden Plan und fasst die **flachen** ausführbaren Teilpläne unter einer gemeinsamen Untersuchung zusammen. Nicht ungeprüft verschachtelte `combined`-Pläne an den bisherigen Worker geben. Standort-, Profil- und Solveridentität jedes Kindes sowie Summierung der Fallzahl müssen erhalten bleiben; das ist ein vor Umsetzung zu prüfender Integrationspunkt.

Quellen und unveränderte Ergebnisdateien werden bedarfsgerecht gelesen. Caches beachten Dateizustand und den relevanten Hash-/Validierungsvertrag; ein reiner Datumswechsel lädt keine sämtlichen Sensitivitätsfamilien. Native Änderungen werden erkannt. Kein Cache darf einen fehlgeschlagenen Nachweis in einen bestandenen verwandeln.

Die fachliche Analysezieldefinition, der vorhandene OAT-Planer und die Parameterfreigaben werden zusammengeführt. Die alten engeren `analysis_intent.request_scope`-Regeln dürfen den aktuell unterstützten Mehrfachprofil-/OAT-Umfang nicht begrenzen. Grafikfunktionen erhalten bereits gefilterte, referenzgebundene Tabellen und liefern die verwendeten Daten zusammen mit der Grafik zurück.

## 11. Erster klickbarer Entwurf und seine Grenzen

Der begleitende Entwurf D1 in diesem Chat zeigt drei Beispielabläufe: Nachfrage, Szenarien/Emissionen und Tagesbetrieb. Seine Auswahl wirkt ausschließlich auf eine lokale Vorschau vorhandener Daten. Die fünf Hauptbereiche sind räumlich angeordnet; vollständige Rechneranbindung, Auftragsverwaltung und alle technischen Sensitivitätsdialoge sind noch kein Produktstand.

Die Vorschau verwendet einen eingefrorenen Auszug der registrierten Nachfrageergebnisse und der vorhandenen D0-Basisfälle. Für Tagesbetrieb wird ein ausdrücklich benannter Basisfall mit wenigen vorhandenen Beispieltagen verwendet. Ein solcher Ausschnitt beansprucht keine Abnahme aller 23/24/25-Stunden-Fälle. Keine Demo-Kurve wird als neu berechnetes Ergebnis ausgegeben. Quellenpfade und Hashes des Auszugs stehen im [Entwurfsnachweis](gui/planungsbeispiele/oberflaeche_20261011/entwurfsnachweis.json).

Die Textspezifikation dieses Dokuments ist vollständig genug für die nächste Umsetzungsetappe; die Vorschau zeigt gezielt die häufigen Wege. Eine im Beispiel noch nicht ausführbare Funktion ist deshalb nicht aus dem geplanten Funktionsumfang entfernt. Der [Bestandsabgleich des Entwurfs](gui/planungsbeispiele/oberflaeche_20261011/entwurfsabgleich.json) ordnet alle 19 Auditpunkte und die Bestandsgruppen den vorgesehenen Komponenten zu.

## 12. Umsetzungsetappen und Review

| Etappe | Konkretes Ergebnis | Freigabekriterium |
|---|---|---|
| **D1 – ausgearbeitet** | Diese Spezifikation, Beispielabläufe, klickbare Vorschau, Bestands-/Mängelzuordnung und aktualisierte Kern-MDs | Fachlich durchgesehen; Nutzerreview und vollständige Produktabnahme offen |
| **U1 – implementiert, gezielt geprüft** | Eigene Referenzzuordnung, tatsächliche Preisoperation, kontrollierte Vorgaben, Größenrollen sowie gemeinsame Grafik-/Exportdaten | M01/M02/M03/M04/M05/M06/M07/M11: Ergebnisse und Grenzen in [GUI_U1_ABNAHME.md](GUI_U1_ABNAHME.md) |
| **U2 – Gemeinsame Arbeitsfläche** | Ziele, kontextabhängige Formulare, vorhandene Untersuchung und Ergebnisansichten | Nachfrage, Emissionen und Tagesbetrieb ohne technische Dateisuche; vollständiges Parameterinventar |
| **U3 – Aufträge** | Planidentität, Mehrstandortkomposition, Status/Heartbeat und wiederauffindbare Ausführungen | Kein unbeabsichtigter Doppelstart; Reload und Unterbrechung mit kleinem Modell geprüft |
| **U4 – Abnahme und Übergabe** | Fehlersituationen, Cache-/Export-/Zeitzonenprüfung, Bedienprobe, aktualisierte echte Anleitung | Alle Bestandsgruppen erhalten, 19 Mängel mit eigenem Abschlussnachweis; Geräte-/Nutzertest gesondert dokumentiert |

Die Besprechung von D1 sollte sich auf drei konkrete Fragen konzentrieren: Ist das gewünschte Ziel sofort auffindbar? Reichen die direkt sichtbaren Angaben für die drei Beispiele? Sind Ergebnis und Export eindeutig zugeordnet? Farben und Abstände sind nachrangig. D1 setzt keine neue wissenschaftliche Annahme fest und startet die Implementierung nicht automatisch.

## 13. Wissenschaftlicher Review und konkrete U1-Kriterien – 11. Oktober 2026

Der aktuelle Nutzerauftrag autorisiert die Fortsetzung des nächsten Schritts. Der [wissenschaftliche D1-Review](GUI_D1_WISSENSCHAFTLICHER_REVIEW.md) bestätigt die Analyseziele und präzisiert die Auswertungen anhand der lokalen Methodik; er ist keine neue Rechtsprüfung und keine Produktabnahme. Wissenschaftlicher Mehrwert bedeutet hier kontrollierte Fragen, erklärte Wirkungen und reproduzierbare Grafiken.

- **Vergleichsannahmen:** Szenarienvergleich bei gleichem Standort, Profil, tatsächlicher Jahreslieferung, Kalender, Preis-/Technik-/Finanzierungsgrundlagen und Solver; Profilvergleich bei gleicher Jahreslieferung; OAT mit genau einer dokumentierten Intervention. Abgeleitete Inputhashes benötigen einen belegten Herkunfts- und Transformationsbezug. Freie Mischvergleiche bleiben deskriptiv; Prüfdeckung gilt je Ausführung.
- **Operation und Referenz:** Historische Familiennamen legen die Intervention nicht fest. EU-Preisreihenverschiebung bedeutet additives Offset, keine Stundenpreismultiplikation oder Konstantpreisannahme. Jede numerische Reihe erhält genau einmal ihre eigene belegte Basis: Offset 0, Faktor 1 oder direkter Basiswert. WACC-Prozentpunkte und Komponentenfaktoren bleiben unterscheidbar.
- **Nachfrage:** Die dokumentierten homogenen LP-Gleichungen erwarten bei unveränderten Koeffizienten, positiver Skalierung und ohne zusätzliche absolute Grenzen proportionale optimale Jahreskosten und konstante LCOH. Eine skalierte optimale Lösung existiert; alternative Optima können unterschiedliche Kapazitätsaufteilungen erzeugen. Diese Modelleigenschaft ist ein sinnvoller Skalierungstest, kein Nachweis realer Größendegression oder einer Bestandsanlagenkapazität.
- **Emissionen:** Bei statischem Länderfaktor 2024 folgen betriebliche Emissionen dem Netzbezug; die Wahl einer anderen Bezugsstunde allein bewirkt hier keinen zeitabhängigen Emissionsvorteil. Regulatorische Null bei erzwungener Mengendeckung bleibt eine elektrische Teilbewertung. Die native Produktreferenz erscheint nur in der passenden regulatorischen Intensitätsansicht, Prüfgrößen unter Modellprüfung.
- **Wirkung und Export:** Kosten-/OAT-Änderungen beziehen sich auf die eigene Basis. Relative Änderung bei Basis null ist nicht definiert. Grafik und CSV verwenden exakt dieselben Fälle, Basiswerte, Größen, Einheiten und Zeitfenster; Gesamtexporte werden separat bezeichnet. Ein Kontextwechsel entfernt irreführende alte Exportzuordnungen.
- **Reichweite:** Lieferprofile sind synthetisch, Fenster betreffen Lieferung; eine separate Tankentnahmeleistungsgrenze fehlt. EU 2024 belegt keine mehrjährige Robustheit; Namibia/TMY ist kein isolierter Standorteffekt. Solververgleich zeigt numerische Reproduzierbarkeit, einzelne Laufzeiten keinen allgemeinen Leistungsbenchmark. Szenariostufen sind keine Konfidenzintervalle.

Für U1 gilt damit die Prüfungskette **Fallidentität → kontrollierter Vergleich → tatsächliche Operation/eigene Referenz → fachliche Größenrolle → identische Grafik-/CSV-Daten**. Der Review enthält konkrete Nachweise für M01/M02/M03/M04/M05/M06/M07/M11 und die relevanten Interpretationsgrenzen. Der Umsetzungsnachweis wird gesondert geführt; U2–U4 und Produktabnahme bleiben eigenständige Etappen.

## 14. Erreichter U1-Teilstand – 11. Oktober 2026

Die lokale U1-Revision ist implementiert und gezielt geprüft.
Der [U1-Abnahmenachweis](GUI_U1_ABNAHME.md) dokumentiert den konkreten Umfang,
Prüfergebnisse und Einschränkungen. Die Vorschau aus Abschnitt 11 bleibt ein
historischer Entwurfsausschnitt; die gezielten U1-Korrekturen sind im GUI-Code
der lokalen Revision vorhanden.

Preisoperationen werden aus nativer Provenienz gelesen und fachlich bezeichnet,
auch bei alten Familiennamen. Jede numerische OAT-Reihe verwendet genau einmal
ihre eigene belegte Referenz: Faktor 1, Offset 0 oder direkter nativer Basiswert.
Sammlung, Standort, Profil, Szenario, Solver, Konfiguration und unveränderte
Inputs sichern die Zuordnung. Ähnliche Kosten ersetzen keinen Vertrag.

Standardvergleiche wählen S0/S1/S2 gemeinsam nur bei belegter gleicher übriger
Basis. Sonst beginnt die Auswahl mit einem Fall; freie Gegenüberstellungen
werden als deskriptiv erläutert. Ergebnis-, Referenz- und Diagnosegrößen haben
getrennte Rollen. Die native Produktreferenz ergänzt nur die passende
regulatorische Intensitätsansicht; Kostenkomponenten besitzen eine feste Größe.

Grafik und Grafik-CSV nutzen denselben vorbereiteten Datensatz einschließlich
OAT-Basis. Stundenexporte enthalten den tatsächlich angezeigten nativen Zeitraum
mit Fall- und Zeitbezug. Kontextwechsel und fehlerhafte Darstellungen entfernen
alte Grafikexporte; fehlende oder mehrdeutige Daten erhalten eine konkrete
Meldung. Dadurch sind Ergebnisinterpretation und Export genauer nachvollziehbar.

Der vollständige Entwurf wird damit nicht als umgesetzt abgenommen. U2 mit
Analyseziel und gemeinsamer Arbeitsfläche, U3 mit Auftragsverwaltung und U4 mit
vollständiger Abnahme/Übergabe bleiben offen. Wissenschaftliche Originalinputs,
Modellgleichungen und vorhandene Exporte wurden nicht geändert; U1 erforderte
keine neue Modelloptimierung. Die Übernahme des geprüften GUI-Stands wird im
U1-Nachweis dokumentiert.


## U2: aktive Forschungswerkstatt – 12. Oktober 2026

Die Oberfläche wird jetzt tatsächlich über acht Untersuchungsziele bedient.
Gespeicherte Ergebnisse stehen am Anfang; nur „Untersuchung jetzt berechnen“
startet einen nativen Auftrag. Die Frage, der Bezugsfall und die beobachteten
Unterschiede stehen direkt beim Ergebnis. Kosten, Auslegung, Netz/Emissionen
und Betrieb haben passende feste Ansichten. Daten, Quellen, Solveroptionen,
sämtliche freigegebenen Parameter und Prüfungen bleiben erreichbar.

H₂-Menge und Lieferzeiten sind gewöhnliche Sensitivitätsziele. Die Mengenansicht
beginnt mit Jahreskosten, enthält einmal die eigene 100-%-Basis und erläutert
die Homogenität der Neuauslegung. Beide EU-Standorte können in einer neuen
Untersuchung enthalten sein; die gewählten Standorte/Profiles/Solver werden
zu flachen nativen Einzelplänen zusammengesetzt. Das Beispiel 50/75/100/125/150 %,
Hamburg/Huelva, D0/D1/D2, S0/S1/S2 umfasst 90 Fälle.

Die Emissionsansicht trennt betriebliche und regulatorische elektrische Bilanz.
Der Grenzwert erscheint nur als passende Referenz. Tagesbetrieb ist direkt in
Analyse sowie vom exakten Sensitivitätspunkt aus erreichbar. Standortvergleiche
haben eine eigene Auswahl; kein globaler Einzelstandortfilter täuscht deren
Umfang vor. Grafiken und Daten behalten die U1-Fall-/Referenzbindung.

Aktuelle Bedienung: [GUI_BEDIENUNGSANLEITUNG.md](GUI_BEDIENUNGSANLEITUNG.md).
Bestand, Prüfungen und Grenzen: [GUI_U2_ABNAHME.md](GUI_U2_ABNAHME.md).
U3-Auftragsverwaltung und die umfassende U4-Nutzer-/Geräteabnahme bleiben offen.
Keine Änderung an Modellgleichungen, wissenschaftlichen Inputs oder vorhandenen
Jahresergebnissen; keine neue Jahresoptimierung, PDF oder Manuskriptbearbeitung.
