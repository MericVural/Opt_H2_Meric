# Bedienprüfung des Oberflächenentwurfs D1

Stand: 11.10.2026. Geprüft wurde die separate Vorschau, nicht eine umgebaute produktive GUI.

| Prüfung | Beobachtung |
|---|---|
| Nachfrage öffnen | 2 Standorte × 3 Profile × 3 Szenarien × 5 Mengen = 90 vorhandene Fälle; keine neue Optimierung. |
| Ergebniszugang | „Ergebnisse ansehen“ öffnet Jahreskosten über der Nachfragemenge auf derselben Arbeitsfläche. |
| Ausschnitt ändern | Hamburg/D0 → Huelva/D2 aktualisiert Standort, Profil und gezeichnete Werte aus dem vorhandenen Datenauszug. |
| Szenarien | D0/S0–S2 mit gleicher Jahresmenge; Standortwechsel und Kostenansicht funktionieren. |
| Emissionen | Betriebliche und regulatorische Größen getrennt; Nullwerte sichtbar; eine durchgehende gestrichelte Referenz im regulatorischen Diagramm. DOM-Prüfung bestätigt genau eine Referenzlinie. |
| Tagesbetrieb | Direkter Wechsel in Analyse → Betrieb ansehen; vorhandener Hamburger D0/S2-Basisfall ist ausdrücklich benannt. |
| Tag und Darstellung | 02.01. → 03.01.2024 sowie Kumulativ → Stündlich verändern Kurve, Titel-/Auswahlkontext und Einheit. |
| Zustand nach Reload | Zuvor gewählte Betriebsansicht, Datum und Darstellungsmodus werden in der Vorschau wiederhergestellt. |
| Vergleich / Quellen / Export | Alle Bereiche erreichbar; Vergleich erklärt konstante und standortabhängige Größen; Quellen zeigen Jahresrollen; Exportanbindung ausdrücklich noch nicht umgesetzt. |
| Browserfehler | Keine JavaScript-Fehler im geprüften Browserprotokoll. |
| Native Freigaben | Lesende Inspektion: 13 native numerische Parameter; elf GUI-Parameter je Studie, zusätzliche EU-Profilvariation. Keine Solverausführung. |

Die Datenaufbereitung prüfte die Größe des Auszugs (90 Nachfragefälle, sechs frische D0-Szenarienfälle, 72 Stunden), jeweils 24 Stunden für die drei ausgewählten Ortstage und die Strombilanz des täglichen Auszugs. Das ersetzt nicht die ergebnisgebundenen unabhängigen Jahresprüfungen. Eine fehlende Jahresnetzbezugsgröße in einem Basisexport wurde als fehlend belassen, nicht als null ersetzt.

Die finale Emissionsansicht ist in [emissionen_vorschau.png](emissionen_vorschau.png) festgehalten; der zugängliche Seitenzustand steht in `emissionen_vorschau.txt`. Die gespeicherte Vorschauquelle ist `entwurf_d1.fragment.html`; der Daten-/Quellenbeleg steht in `entwurfsnachweis.json`.

Nicht durchgeführt: empirische Nutzerstudie, vollständige Tastatur-/Screenreader-Abnahme, Geräte-/Breakpoints-Matrix, produktive Export-/Auftragsanbindung oder neue Solverläufe. Alle 19 Produktmängel bleiben bis zur eigentlichen Umsetzung und Abnahme offen. Die Vorschau illustriert drei Abläufe; der vollständige geplante Funktionsumfang ist in `GUI_OBERFLAECHENENTWURF.md` festgelegt.
