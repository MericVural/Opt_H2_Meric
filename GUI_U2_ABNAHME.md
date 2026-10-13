# U2 – sichtbarer Neuaufbau der H₂-Forschungswerkstatt

**12. Oktober 2026.** Auf ausdrücklichen Auftrag wird die aktive App umgebaut. U1 vom 11. Oktober verbesserte die Ergebnisverträge, ließ aber den bisherigen Formulareinstieg bestehen. U2 macht die Forschungsfrage zum sichtbaren Einstieg. Dies ist Implementierung im Modellrepository, keine weitere Vorschaugrafik.

## Was sich für die Forschung und Bedienung ändert

- Acht Ziele führen zu passenden Eingaben und wenigen sinnvollen Ergebnisansichten. Standard ist die Auswertung gespeicherter Fälle; nur der ausdrückliche Startknopf beginnt eine Optimierung.
- Stromregeln: gemeinsame native Ergebnisstände bleiben zusammen. LCOH und beobachtete S1→S2-Differenz werden sichtbar beziffert; ein nicht belegter isolierter Effekt wird nicht als kausal interpretiert.
- Nachfrage: Prozent- und Jahresmengen, eigene 100-%-Basis, Jahreskosten zuerst und empirischer Homogenitätscheck der ausgewählten Punkte. Keine Behauptung industrieller Größendegression.
- Lieferprofile: kategorialer Vergleich von D0/D1/D2 bei gleicher Jahresmenge, mit Rundungstoleranz. Lieferzeiten und Produktion bleiben begrifflich getrennt.
- Emissionen: zwei getrennte Intensitätsbilanzen; die native gestrichelte Produktreferenz erscheint ausschließlich auf der regulatorischen Achse. Absolute Emissionen und Netzbezug haben eigene Ansichten.
- Tagesbetrieb: direkter Einstieg und Weiterleitung eines exakten Sensitivitätsfalls. Ortszeit, vollständige Tage und kumulative MWh bleiben erhalten.
- Standortvergleich: beide EU-Standorte bei gleichem Profil/Szenario; keine irreführende globale Auswahl nur eines Standorts. Historische und freie Gegenüberstellungen bleiben erreichbar.
- Neue Untersuchungen: bestehende Runner, sichtbare Fallanzahl, flache Zusammenstellung der nativen Standort-/Profil-/Solverpläne. Beide EU-Standorte × drei Profile × drei Szenarien × fünf Mengen ergeben 90 Fälle.
- Darstellung und Ladeverhalten: neue Gestaltung, einklappbare Einstellungen, fachliche Kategorien, bedarfsweise Detail-/ZIP-Dateien und dateigebundener Ergebniscache. Alle nativen Tabellen, Quellen, Prüfungen und bisherigen Parameter bleiben erreichbar.

## Bestand und Prüfungen

Der ausführbare Bestandsabgleich bestätigt 13 native numerische Parameter und elf vorher freigegebene numerische Parameter je Fallstudie/Standort, zusätzlich die EU-Lieferprofile. Alle drei Standorte, vier Szenarien, drei Solveroptionen, Solververgleich, Werte-/Bereichseingaben, Ergebnisgrößen und nativen Quellen bleiben erhalten. Der native Modellcode wird vor und nach der Übernahme per SHA-256 abgeglichen.

Nachweise stehen unter `outputs_h2/gui_validation/u2_20261012/`:

- **107/107 gezielte automatisierte Prüfungen bestanden:** 19 Prüfungen der aktiven Forschungsoberfläche und 88 bestehende Prüfungen der Referenz-, Diagramm-, Tages- und Versuchsplanverträge. Keine Fehler oder übersprungenen Fälle in diesen abschließenden Berichten.
- [19 U2-Prüfungen](outputs_h2/gui_validation/u2_20261012/research_ui.xml): reale gespeicherte S0/S1/S2-Ergebnisse, eigene Nachfragebasen, Lieferprofile, Preisoperation, 90-Fälle-Vorschau, leerer Exportzustand, exakter Tagespunkt, Standortvergleich, Quellen und Export. Der ausdrückliche Start übergibt genau einen flachen 90-Fälle-Plan an eine simulierte Auftragsverwaltung; kein echter Solverstart.
- [88 Vertragsprüfungen](outputs_h2/gui_validation/u2_20261012/contracts.xml): insbesondere keine fremden OAT-Basen, korrekte Preis-/WACC-Achsen, native THG-Referenz nur auf der passenden Achse, 23/24/25 Stunden und tatsächliche native Vorabprüfung der Versuchspläne. Der gesonderte Test mit echtem 24-Stunden-Modelllauf wurde für diesen Auftrag ausdrücklich nicht ausgewählt.
- [Bestandsabgleich](outputs_h2/gui_validation/u2_20261012/inventory_after.json): 13 native Parameter; elf freigegebene numerische GUI-Parameter je Standort sowie vorhandene Profile.
- [Installation und Dateiprüfsummen](outputs_h2/gui_validation/u2_20261012/installation_receipt.json): explizite Übernahmeliste, vorherige Dateien gesichert, native Modelldateien unverändert.

Bei der Prüfung wurde eine irreführende Ungleichheitsmeldung für numerisch nahezu identische Profil-Jahressummen korrigiert (`rtol=1e-9`, `atol=0,001 kg`). Profilansichten sind nun D0/D1/D2 sortiert. Quellen-/Prüfdateien werden bedarfsweise geladen. Die Tests enthalten lediglich Bibliothekswarnungen und Hinweise zur nicht serialisierbaren DataFrame-Attributmetadaten; CSV-Spalten und Fallbezüge werden separat geprüft.

Reproduzierbare gezielte Prüfaufrufe im Modellordner (mit beschreibbarem pytest-Temporärordner):

```powershell
& .\.venv-gui\Scripts\python.exe -B -m pytest gui/checks/research_workspace_regression.py -q -p no:cacheprovider
& .\.venv-gui\Scripts\python.exe -B -m pytest gui/checks/u1_contracts_regression.py gui/checks/u1_plotting_regression.py gui/checks/daily_plot_regression.py gui/checks/sensitivity_design_regression.py -q -k 'not actual_24h' -p no:cacheprovider
```

Die Browserprüfung des installierten Stands wird gesondert in [BROWSER_PRUEFUNG.md](outputs_h2/gui_validation/u2_20261012/BROWSER_PRUEFUNG.md) dokumentiert. Die Prüfungen verwenden vorhandene Jahresresultate und kleine synthetische Testdaten. Neue Jahresoptimierungen sind für diesen Oberflächenumbau nicht erforderlich.

## Grenzen und verbleibende Arbeit

U2 ist keine vollständige Erledigung aller historischen Auditmängel. U3 (verlässliche Prozess-/Auftragszustände, über Sitzungen hinweg wirksamer Doppelstartschutz und Wiederaufnahme) bleibt separat offen. Alte laufende Jobmeldungen werden deshalb ausdrücklich als ungeprüfter gespeicherter Status bezeichnet. U4 umfasst die breitere Geräte-/Zugänglichkeits- und Nutzerabnahme sowie eine aktualisierte externe Übergabe.

Die allgemeine Vertragsprüfung kann Lieferprofil- und Standortvergleiche konservativ als deskriptiv einstufen. Gleiche Jahresmenge allein wird nicht als Beweis identischer übriger Annahmen verwendet. Mehrere absolute Parametereingaben bei mehreren Standorten gelten unverändert je Standort; unterschiedliche standortrelative Basen brauchen getrennte Aufträge. Modellgleichungen, Originalinputs, historische Ergebnisdateien und Manuskript werden nicht geändert. Keine neue PDF, kein automatischer Git-Commit oder Push.

## Nachprüfung des Untersuchungsstarts – 13. Oktober 2026

Der zuvor dokumentierte U2-Test des Startknopfs prüfte eine numerische
Nachfragesensitivität. Nicht geprüft war ein Start ohne numerische Varianten.
Der Nutzer meldete deshalb einen echten Fehler: Ein gültiger Stromregelvergleich
mit Hamburg, D0/D1/D2 und S0/S1/S2/S3 (12 Fälle) erreichte irrtümlich die
OAT-Prüfung und wurde wegen eines fehlenden Sensitivitätsparameters abgewiesen.

Korrigiert in `gui/research_workspace.py`: Basisfall-, Stromregel- und
Solververgleiche verwenden den bestehenden `build_analysis_plan`; der
Lieferzeitvergleich übergibt die gewählten Profile als kategorische Stufen.
Numerische OAT-Prüfungen und wissenschaftliche Quellenverträge bleiben aktiv.
Die Startübersicht nennt alle enthaltenen Lieferprofile und Stromregeln.

**52/52 gezielte Prüfungen bestanden:**

- 23 Oberflächenprüfungen, einschließlich vier neuer Startprüfungen mit
  realer nativer Eingabe-/Quellenvorabprüfung: Stromregeln (12 Fälle),
  Anlage (1), Solver (2), Lieferzeiten (9). Auftragsübergabe und Laufstatus
  sind simuliert; es wird kein Worker gestartet. Die Gurobi-Verfügbarkeit
  ist im Weiterleitungstest simuliert, keine Lizenzabnahme.
- 29 bestehende Sensitivitäts-/Profilvertragsprüfungen. Der separate Test
  `actual_24h` wurde nicht ausgewählt; keine Jahresoptimierung.
- Verbleibende Warnungen betreffen Bibliotheksabkündigungen und die
  Streamlit-Serialisierung von DataFrame-Attributen, keine fehlgeschlagene Prüfung.

Nachweise: `outputs_h2/gui_validation/startfix_20261013/research_ui.xml`,
`contracts.xml` sowie `installation_receipt.json` mit Dateiprüfsummen und
gesicherten Vorversionen. Modellcode und historische Jahresergebnisse wurden
nicht verändert. Neuaufbauplan, Forschungsarbeitsplan und Bedienungsanleitung
enthalten die Korrektur; U3/U4 werden damit nicht als abgeschlossen erklärt.
