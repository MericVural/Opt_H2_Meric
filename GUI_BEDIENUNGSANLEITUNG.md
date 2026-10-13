# H₂-Forschungswerkstatt – Bedienungsanleitung

**Oberfläche U2 · 12. Oktober 2026.** Die App dient der Forschungsfrage: Wie verändern modellierte Stromversorgungskriterien, Standortbedingungen und H₂-Nachfrage die kostenminimale Anlage und die Wasserstoffkosten? Sie wertet Modellrechnungen aus; sie bewertet keine Investitionsrendite ohne Absatzpreis und keinen vollständigen RFNBO-Zertifizierungsnachweis.

## 1. Öffnen und orientieren

Im Modellordner `C:\Forschungsarbeit\Opt_H2_Meric-h2` die Datei **H2-Modell starten.cmd** öffnen. Die App ist unter <http://127.0.0.1:8510/> erreichbar. Codex wird zum normalen Betrieb nicht benötigt. Die Kopfzeile lautet **H₂-Forschungswerkstatt**, die Seitenleiste trägt **H₂ / Research** und die Revisionsangabe **Oberfläche U2 · 12.10.2026**. Beim Öffnen werden vorhandene Ergebnisse angezeigt; es startet keine Optimierung.

| Arbeitsbereich | Aufgabe |
|---|---|
| Analyse | Stromregeln vergleichen, Anlage auslegen, Tagesbetrieb verstehen, Solver vergleichen |
| Sensitivitätsanalyse | H₂-Menge, Lieferzeiten sowie Preis-, Finanzierungs- und Technikannahmen verändern |
| Vergleich | EU-Standorte bei gleicher Aufgabe oder eigene gespeicherte Fälle gegenüberstellen |
| Quellen | Quellen, Annahmen, Bezugsjahre, Basiskonfiguration und Modellprüfungen nachlesen |
| Export | Tabellen, aktuelle Grafikdaten, native Ergebnisdateien und Nachweise herunterladen |

Die Auswahl von Fallstudie und Standort gilt für den jeweiligen Bereich. **Vergleich** hat eine eigene Fallauswahl; darüber steht kein irreführender einzelner Standortfilter. **Ergebnisstand aktualisieren** liest Änderungen erneut ein. Die Ergebnislisten sind kurzzeitig zwischengespeichert; Dateiänderungen invalidieren den Cache.

## 2. Kosten der Stromregeln untersuchen

1. **Analyse → Stromregeln vergleichen** wählen.
2. Fallstudie **EU-Vergleich 2024** und Standort auswählen.
3. Unter **Untersuchung einstellen · Lieferprofil & Stromregeln** das Profil und die Szenarien festlegen. Vorgabe: D0 und S0/S1/S2.
4. **Ergebnisse auswerten** zeigt gespeicherte Ergebnisse. **Ergebnisstand & ausgeführter Solver** erlaubt die Wahl einer anderen vorhandenen Ausführung.
5. Die LCOH-Karten zeigen die Szenarioergebnisse. **Modellbefund** nennt die tatsächliche Differenz von S2 gegenüber S1. Die Kennzeichnung darunter erklärt, ob ein gemeinsamer nativer Vergleichskontext belegt ist.
6. Zwischen **Kosten**, **Auslegung**, **Netz & Emissionen** und **Betrieb** wechseln.

Für eine neue Rechnung **Neu berechnen** wählen. Das oben gewählte Profil
ist bereits enthalten; unter **Weitere Einstellungen** können zusätzliche
Profile und Stromregeln ergänzt werden. Die Startübersicht nennt die gesamte
Auswahl. Beispiel: ein Standort × D0/D1/D2 × S0/S1/S2/S3 × ein Solver ergibt
**12 Modellfälle**. Ein Stromregelvergleich benötigt keinen numerischen
Sensitivitätsparameter. Die entsprechende fehlerhafte Startprüfung wurde am
13. Oktober 2026 korrigiert; danach die geöffnete App einmal neu laden.

**Lesart:** S1 → S2 vergleicht monatliche mit stündlicher Zuordnung. S0 → S1 verändert zusätzlich EE-Mengendeckung und Überschussallokation. Die Differenz darf nicht pauschal ausschließlich als Stundenkorrelationseffekt beschrieben werden. Eine freie oder unvollständig belegte Gegenüberstellung wird als deskriptiv gekennzeichnet.

**Kosten** zeigt LCOH, annualisierte Kostenbestandteile oder Jahreskosten. **Auslegung** trennt Leistungen in MW vom Speicher in t. Alternative kostenoptimale Lösungen können unterschiedliche Kapazitätsaufteilungen besitzen. Das Modell minimiert Kosten je geliefertem kg H₂ am Ausgang des 300-bar-Speichers; Verkaufserlöse und Investitionsrenditen sind keine berechneten Ergebnisse.

## 3. Emissionen sinnvoll vergleichen

Im Ergebnis **Netz & Emissionen → Emissionsintensitäten** öffnen. Zwei nebeneinanderliegende Diagramme unterscheiden:

- **Betrieblich:** physischer Netzbezug mit statischer nationaler Emissionsreferenz. Es werden keine stündlich dynamischen oder marginalen Länderfaktoren unterstellt.
- **Regulatorisch:** elektrische Teilbilanz nach der gespeicherten Stromzuordnung. Die native THG-Produktreferenz wird ausschließlich hier als gestrichelte Linie in passender Einheit gezeigt.

Regulatorische Null bedeutet keine physische Emissionsfreiheit. Die elektrische Teilbilanz allein belegt keine vollständige Zertifizierung. **Netzbezug** und **Absolute Jahresemissionen** bieten andere sachgerechte Achsen ohne unpassenden Intensitätsgrenzwert.

## 4. Tageskurven für Solar, Wind und Netz

**Analyse → Tagesbetrieb verstehen** führt direkt zur Betriebsansicht. In **Untersuchung einstellen** Profil und Szenario wählen, dann Ergebnisreihe und konkreten berechneten Fall auswählen. Alternativ ist **Betrieb** aus einem Szenarienergebnis erreichbar.

Bei **Solar, Wind & Netz am Tag**:

1. **Tag auswählen** setzt den Kalendertag in Ortszeit des Standorts.
2. **Stündlicher Tagesverlauf** zeigt die Stundenwerte; **Kumulative Tagesenergie** summiert ab Tagesbeginn in MWh.
3. **Direktversorgung** zeigt direkt genutzte PV-/Windenergie und Netzstrom. **Erzeugung und Netzbezug** enthält auch erneuerbare Überschüsse; deren Summe entspricht nicht dem Anlagenbedarf.
4. Tages- und Grafik-CSV enthalten die ausgewählten nativen Stunden. Zeitumstellungstage haben 23 bzw. 25 Stunden. Fehlende Stunden werden nicht interpoliert.

**H₂-Produktion & Speicher** erlaubt einen längeren Stundenausschnitt. **Jahreskennzahlen** enthält betriebliche Kennzahlen. Sensitivitätspunkte besitzen zusätzlich **Einen Versuchspunkt im Tagesbetrieb öffnen**: Die Weiterleitung erhält exakt den gewählten Fall, einschließlich Nachfrage-/Technikvariante, und ersetzt ihn nicht durch die Basis.

## 5. H₂-Jahresmenge untersuchen

**Sensitivitätsanalyse → H₂-Jahresmenge verändern → Ergebnisse auswerten** zeigt die vorhandenen Mengenpunkte. Standort, Profil und Szenarien wählen den sichtbaren Ausschnitt. **Gespeicherte Versuchsreihe & Herkunft** bestimmt die zugehörige Untersuchung.

Die Vorgabe zeigt Jahreskosten über der Nachfrage mit **50 / 75 / 100 / 125 / 150 %**. 100 % ist einmal als eigene Basis enthalten. Bei einer Basis von 3.650.000 kg/a entspricht dies 1.825.000 / 2.737.500 / 3.650.000 / 4.562.500 / 5.475.000 kg/a. Weitere Ansichten zeigen LCOH, Leistungen, Speicher, Netzbezug und Emissionen.

**Wissenschaftliche Lesart:** Für jede Menge wird eine Anlage neu ausgelegt. Das homogene lineare Modell enthält keine Größendegression. Bei unveränderten Koeffizienten können Jahreskosten proportional wachsen und LCOH konstant bleiben. Die App prüft diese Aussage an den dargestellten Punkten. Daraus folgt keine Aussage über Engpässe einer fest installierten Anlage. Eine andere Kapazitätsaufteilung kann zu einem alternativen Optimum gehören.

Für eine neue Rechnung **Neu berechnen** wählen. Standort(e), Profil(e), Szenarien und Mengenstufen festlegen. Prozentwerte werden intern in Faktoren umgerechnet; **Weitere Nachfragestufen** akzeptiert zusätzliche positive Prozentwerte. 100 % bleibt automatisch einmal enthalten. Beide Standorte × D0/D1/D2 × S0/S1/S2 × fünf Mengen ergeben **90 Modellfälle**. Der Start erfolgt ausschließlich mit **Untersuchung jetzt berechnen**.

## 6. Lieferzeiten vergleichen

**Sensitivitätsanalyse → Lieferzeiten verändern** vergleicht bei gleicher Jahresmenge:

- D0: Lieferung rund um die Uhr.
- D1: täglich 08–20 Uhr Ortszeit.
- D2: Montag bis Freitag 08–20 Uhr Ortszeit, ohne Feiertagskorrektur.

Zunächst eine Stromregel auswählen, dann LCOH und Speicher vergleichen. Lieferzeiten sind Abnahmebedingungen; Produktion ist außerhalb dieser Zeiten erlaubt. Kleine Rundungsabweichungen der Jahressummen werden innerhalb `rtol=1e-9`, `atol=0,001 kg` toleriert. Unterschiedliche Mengen werden ausdrücklich als Einschränkung angezeigt. Die allgemeine Kontextprüfung unterscheidet einen belegten isolierten Vergleich von einer deskriptiven Gegenüberstellung.

## 7. Preis, Finanzierung und Technik untersuchen

**Sensitivitätsanalyse → Preis, Finanzierung & Technik** öffnet gespeicherte Einzelparameterreihen. Die Auswahl erfolgt über Einflussbereich und Parameter. **Wirkung auf** ordnet Ergebnisgrößen den Themen Kosten, Auslegung, Betrieb oder Emissionen zu. Die Kurve enthält ihre eigene geprüfte Basis; eine fehlende oder fremde Basis wird nicht ersetzt. Prozentänderungen beziehen sich auf diese Basis und die tatsächlich berechneten Stufen, nicht auf eine Wahrscheinlichkeitsverteilung.

Beim EU-Strompreis kann eine historische Parameterbezeichnung einen **additiven Offset** meinen. Die Oberfläche liest die wirkliche Operation aus den nativen Daten: Ein Offset wird zu jeder Stunde addiert. Ein Faktor des Jahresmittels bedeutet dabei keine Multiplikation jedes Stundenpreises. Ein Namibia-Konstanttarif bleibt davon getrennt. WACC-Faktor und WACC-Prozentpunkte bleiben ebenfalls unterschiedliche Eingriffe.

Unter **Neu berechnen** bleiben alle bisher freigegebenen Parameter erreichbar: elf numerische Parameter je Studie, direkte Werte, relative technische Änderungen, Wertebereiche, gemeinsame Namibia-/EU-Stufen und die kategorischen EU-Lieferprofile. Jeder numerische Parameter wird einzeln variiert. Zusätzliche Profile erhalten nur ihre Basisfälle; mehrere ausdrücklich gewählte Basisprofile erhalten getrennte OAT-Reihen.

Bei mehreren Standorten gelten eingegebene absolute Parameterwerte für jeden Standort. Für individuell relative Werte mit verschiedenen Standortbasen getrennte Aufträge anlegen. Die spezielle Nachfrageauswahl ist relativ zur Basis jedes Standorts.

## 8. Solver, Fallgruppen und neue Untersuchungen

**Analyse → Solver vergleichen** zeigt Zielfunktionswerte, Status, Laufzeiten und Optimalitätslücke vorhandener Fälle. Eine einzelne vorhandene Solverlösung ist noch kein Solververgleich. Laufzeiten setzen vergleichbare Hardware und Umgebung voraus; gleiche Kosten können unterschiedliche alternative Optima besitzen.

**Weitere Einstellungen · Solver, Parameter und Quellen** enthält SciPy/HiGHS, Gurobi und Auto, den expliziten Vergleich beider Solver, die Verfügbarkeitsprobe sowie native Basisparameter und Jahresrollen. Zusätzliche Profile/Szenarien können dort als getrennte Fallgruppe gerechnet werden. Der sichtbare Fallumfang wird vor Übergabe an die nativen Runner mit deren Plan verglichen.

Nach einem Start zeigt die App den Auftrag und dessen Fortschritt. **Ergebnisse dieses Auftrags laden** liest dessen Resultate. Bei mehreren Standorten steht zunächst die Gesamttabelle zur Verfügung; die einzelnen Standortansichten öffnen anschließend unter **Ergebnisse auswerten**. Unter **Berechnungen & Laufprotokolle** in der Seitenleiste bleiben ältere Jobdaten und Logs zugänglich. Historische „running“-Meldungen sind gespeicherte Statusangaben und kein verifizierter Nachweis eines aktiven Prozesses. Die vollständige Auftragsüberarbeitung U3 bleibt offen.

## 9. Quellen, Prüfungen und Downloads

**Quellen** enthält Wetter, Preise, Emissionsfaktoren, Technik, WACC, Nachfrage, Eingabeverträge und Hashnachweise. Betriebs-/Marktjahr 2024, Geldbasis EUR 2023 und WACC-Quelle 2021 werden nicht zu einem einzigen „Datenjahr“ zusammengezogen. Namibia bleibt historisch und nur eingeschränkt mit EU 2024 vergleichbar.

Jede Ergebnisansicht besitzt **Diese Grafik herunterladen**: PNG, SVG und exakte Grafikdaten als CSV. **Daten, Quellen & Modellprüfung** enthält die vollständige Ergebnistabelle; per **Prüfnachweis und native Dateien eines Falls laden** werden die zugehörigen Nachweise, ZIP und Metadaten geladen. Das verhindert unnötiges Laden großer Betriebsdateien bei jeder Einstellung.

**Export** bietet weitere Tabellen, native Ergebnisdateien und die zuletzt vorbereitete Grafik mit eigenem Auswahlkontext. Bei einer leeren oder nicht darstellbaren Auswahl wird ein alter Grafikexport verworfen. Ein optimaler Solverstatus ersetzt nicht die unabhängige Validierung. Fehlende Werte sind keine Nullen.

Die ältere PDF-Anleitung vom 5. Oktober bleibt ausdrücklich historisch. Maßgeblich ist diese Markdown-Anleitung. Prüfstand und Grenzen: [GUI_U2_ABNAHME.md](GUI_U2_ABNAHME.md). Einrichtung auf einem anderen Rechner: [GUI_UEBERGABE.md](GUI_UEBERGABE.md).
