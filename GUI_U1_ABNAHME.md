# U1: wissenschaftlicher Ergebnis-, Referenz- und Exportvertrag

Stand: **11. Oktober 2026**. U1 ist implementiert und gezielt geprüft. Die geführten Forschungsfragen und Formulare aus U2 sowie die Auftrags-, Geräte- und Nutzerprüfung aus U3/U4 bleiben offen. Dieser Bericht ist keine vollständige Produktabnahme des Oberflächenentwurfs D1.

## Fachlicher Nutzen und Verhalten

| Befund des Audits | Verhalten nach U1 | Aussage für die Forschung |
|---|---|---|
| M01: Historischer Familienname verdeckt die tatsächliche Preisoperation | Native Provenienz bestimmt Beschriftung und Achse: additive Stundenpreisverschiebung, tatsächlich konstanter Tarif oder WACC-Faktor bleiben unterscheidbar. | Ein Eingriff wird so interpretiert, wie er tatsächlich gerechnet wurde. |
| M02: Eigene Basis fehlt oder kann verwechselt werden | Numerische OAT enthält genau einmal ihre belegte Basis. Konfiguration, Kalender, Software, Herkunft und tatsächliche Eingriffe werden geprüft; fehlende, fremde oder mehrdeutige Basis verhindert die Kurve und ergibt eine Erklärung. | Die Parameterwirkung bezieht sich auf den richtigen Bezugsfall. Gleiche Kosten allein beweisen keine Identität. |
| M03: Referenzen und Diagnostik erscheinen als frei wählbare Ergebnisse | Normale Ergebniswahl enthält Ergebnisgrößen. Native THG-Referenz erscheint nur auf der regulatorischen Intensitätsachse; Diagnostik bleibt in Modellprüfung und vollständigen Tabellen zugänglich. | Grenzwert, Ergebnis und numerischer Prüfnachweis haben verschiedene Aufgaben. |
| M04: Standardvergleich vermischt Grundlagen | Ein vollständig belegter, eigenständig geprüfter S0/S1/S2-Kontext wird bevorzugt; sonst beginnt die Grafik mit einem konkreten Fall. Freie Mischvergleiche erhalten eine deskriptive Kennzeichnung. | Ein Szenarioeffekt wird nicht aus gleichzeitig wechselnden Grundlagen abgeleitet. |
| M06: Grafik und CSV beziehen sich auf verschiedene Daten | Grafik und Export verwenden dieselbe vorbereitete Auswahl inklusive OAT-Basis. Stundenbetrieb exportiert exakt die dargestellten nativen Stunden. CSV enthält Fallbezug, Achsenbedeutung, Operation und Hinweis. | Bild und Daten lassen sich reproduzierbar zusammen auswerten. |
| M07: Alte Exporte verlieren ihren Zusammenhang | Neue oder leere Grafikauswahl verwirft alte Grafikdaten. Export zeigt ausdrücklich seinen Fallkontext; eine standortgebundene Grafik wird bei anderem Standort verworfen. | Eine frühere Grafik wird nicht als Beleg der aktuellen Auswahl angeboten. |
| M11: Mehrdeutige Kategorien führen zum Plotfehler | Eine uneindeutige Fall-/Gruppenwahl wird mit Auswahlhilfe abgefangen; die native Tabelle bleibt zugänglich. | Es wird keine scheinbar eindeutige Grafik aus mehrdeutigen Fällen erzeugt. |

M05 ist teilweise verbessert: Gestapelte Kosten bieten keine wirkungslose Kennzahlwahl mehr. Die vollständige Zuordnung weniger fachlicher Diagramme zu jedem Forschungsziel gehört zu U2. M19 ist für die Nachfrage präzisiert; weitere Zieltexte gehören ebenfalls zu U2. Die historischen 19 Befunde bleiben im [Neuaufbauplan](GUI_NEUAUFBAU_PLAN.md) nachvollziehbar.

Die Nachfrageansicht beginnt mit Jahreskosten. Sie erklärt die Homogenität der kontinuierlichen Neuauslegung: Bei unveränderten Koeffizienten skalieren Kosten mit der Nachfrage, während LCOH konstant bleiben. Eine proportional skalierte optimale Lösung existiert; alternative Optima können einzelne Kapazitäten anders verteilen. Das ist eine Modelleigenschaft, kein Nachweis industrieller Größendegression oder einer festen Bestandsanlage. Betriebliche Emissionen mit statischem Länderfaktor und regulatorische elektrische Teilintensität bleiben getrennt; die Referenzlinie ist keine vollständige Produktzertifizierung.

## Nachweise

**159/159 Regressionstests bestanden**, ohne Fehler oder übersprungene Fälle, mit der vorhandenen lokalen `.venv-gui`-Umgebung. Die neun Prüfdateien decken tatsächliche Streamlit-Interaktionen, Ergebnis-/OAT-Verträge, Plotrollen, Stunden- und Tagesdaten, native Loader, Nachfrage und vorsichtige Duplikatzuordnung ab. Modell-/Jobgrenzen sind gesperrt oder simuliert; kein Solverlauf wurde ausgelöst. Eine zunächst unpassende Achsenerwartung an einen Grafikstub wurde korrigiert; ein gesonderter Test prüft echte Achsenmetadaten im CSV. Der abschließende Nachweis ist vollständig erfolgreich.

- [Abschließender JUnit-Nachweis](outputs_h2/gui_validation/u1_20261011/verification/u1_regression.xml)
- [Wissenschaftlicher Audit des installierten Codes: 14/14 reale Checks](outputs_h2/gui_validation/u1_20261011/verification/scientific_audit_final/SCIENTIFIC_AUDIT.md)
- [Wissenschaftlicher Review und Kriterien](GUI_D1_WISSENSCHAFTLICHER_REVIEW.md)
- [Installation, Dateihashes und Sicherung](outputs_h2/gui_validation/u1_20261011/u1_receipt.json)

Der reale Audit umfasst ausgewählte Hamburger Preis-/WACC-/PV- und Nachfragereihen, ursprüngliche EU-Reihen, den Namibia-Konstanttarif und S0/S1/S2-Jahresfälle. Er bestätigt eigene Basen, Fremdbasisablehnung, native Grafikpunkte und 72 native Stunden, passende Emissionsreferenz sowie Kosten-/Mengenproportionalität und konstante LCOH innerhalb `rtol=1e-6`. Die **189 gelesenen Originaldateien** blieben hashidentisch. Der Auditcode und genaue ausgewertete Tabellen sind im neuen Nachweisarchiv erhalten; es wurden keine neuen wissenschaftlichen Jahreslösungen gerechnet.

Der unabhängige erste Audit bleibt unter `verification/scientific_audit/` erhalten. Die abschließende Wiederholung unter `verification/scientific_audit_final/` verwendet exakt die installierten Module einschließlich der später ergänzten Eingriffs-/Achsenprüfung. Wiederum bestehen 14/14 Checks; ihre vier GUI-Modulhashes stimmen mit den installierten Dateien überein. Die Browserdownloads wurden zusätzlich gegen die native Punkttabelle geprüft.

Die Installation verwendet eine explizite Liste von GUI-, Test- und Dokumentationsdateien. Vorhandene geänderte Dateien werden unter `pre_u1/` gesichert, ursprüngliche Hashes vor der Übernahme geprüft und installierte Hashes danach verglichen. Native Modell- und Runnerdateien sowie die Registry werden separat vor und nach der Installation geprüft. Bestehende wissenschaftliche CSVs, Inputs und Abnahmearchive sind keine Installationsziele. Kein Commit oder Push.

## Nächste Etappe

U2 verbindet die acht Forschungsziele mit passenden Eingaben, einem sichtbaren Bezugsfall und wenigen sinnvollen Ergebnisansichten. U3 prüft Auftragszustände, Doppelstarts und Abbrüche. U4 prüft Geräteansichten, Zugänglichkeit und Aufgaben mit Nutzern. Die heutige gezielte Prüfung ersetzt weder diese Schritte noch eine vollständige wissenschaftliche Validierung jeder historischen Familie. Manuskript und neue PDF sind weiterhin zurückgestellt.

Die Revision ist im Modellordner installiert und hashgeprüft; der lokale Server läuft mit diesem Stand. Die [abschließende Browserkontrolle](outputs_h2/gui_validation/u1_20261011/verification/browser/BROWSER_PRUEFUNG.md) bestätigt kontrollierte D0-Szenarienvorgaben, die tatsächliche Preisoperation und neun Grafikpunkte einschließlich drei eigener Basen. Direkter Grafikdownload und Download auf der Exportseite sind byteidentisch und bewahren die Achsenbedeutung. Ein [Bildnachweis](outputs_h2/gui_validation/u1_20261011/verification/browser/price_graph.jpg) zeigt die installierte Preisansicht. Diese drei Wege ersetzen keine vollständige Nutzerabnahme.
