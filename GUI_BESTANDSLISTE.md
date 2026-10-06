# Bestandsabgleich der GUI vom 6. Oktober 2026

Alle **46/46 Bestandsprüfungen** bestanden. Keine vorher freigegebene numerische Sensitivität wurde entfernt: weiterhin elf je Fallstudie, zusätzlich die kategorische Lieferprofil-Auswahl in den EU-Fällen. Der native Gesamtkatalog umfasst 13 numerische Parameter; die bestehenden studienspezifischen Freigabegrenzen bleiben dokumentiert.

Vorher- und Nachher-Inventar sowie der maschinenlesbare Abgleich stehen im Prüfarchiv: [Vorher](outputs_h2/gui_validation/simplified_20261006/evidence/GUI_INVENTORY_BEFORE.json), [Nachher](outputs_h2/gui_validation/simplified_20261006/evidence/GUI_INVENTORY_AFTER.json), [Abgleich](outputs_h2/gui_validation/simplified_20261006/evidence/GUI_INVENTORY_COMPARISON.json).

Die tatsächliche Bedienbarkeit ist zusätzlich durch 123 bestandene installierte GUI-/Adapter-/Diagrammprüfungen belegt.

# GUI-Bestandsliste

Lesende Bestandsaufnahme vor bzw. nach dem GUI-Umbau. Kein Modelllauf; keine Datenänderung.

Erfasst (UTC): 2026-10-06T12:03:53.564743+00:00

## Navigation und fachlicher Funktionsumfang

Analyse, Sensitivitätsanalyse, Vergleich, Quellen, Export

| Bisheriger Bereich | Integration |
|---|---|
| Analyse planen | Analyse / Sensitivitätsanalyse |
| Fallstudie | Quellen |
| Modellkonfiguration | Quellen; Solverwahl in Analyse / Sensitivitätsanalyse |
| Sensitivitätsanalyse | Sensitivitätsanalyse |
| Lauf starten | Analyse / Sensitivitätsanalyse, direkt unter den Eingaben |
| Ergebnisse | Analyse; gespeicherte Sensitivitäten in Sensitivitätsanalyse |
| Vergleiche | Vergleich |
| Daten & Quellen | Quellen |
| Validierung | Ergebnisbezogen in Analyse / Sensitivitätsanalyse; Detailprüfung in Quellen |
| Export | Export |

## Sensitivitätsparameter

Alle 13 numerischen nativen Parameter werden inventarisiert. Die tatsächliche GUI-Freigabe je Fallstudie bleibt erhalten; ein nativ vorhandener, bisher nicht allgemein freigegebener Parameter wird nicht stillschweigend aktiviert.

| Nativer Parameter | Einheit | EU-GUI | Namibia-GUI |
|---|---|---|---|
| `electricity_price_eur_per_mwh` | EUR_2023/MWh | nein | ja |
| `electrolyzer_capex_eur_per_kw` | EUR_2023/kW | ja | ja |
| `electrolyzer_specific_electricity_kwh_per_kg_h2` | kWh/kg_H2 | ja | ja |
| `pv_capex_eur_per_kw` | EUR_2023/kW | ja | ja |
| `wind_capex_eur_per_kw` | EUR_2023/kW | ja | ja |
| `h2_storage_capex_eur_per_kg_h2` | EUR_2023/kg_H2 | ja | ja |
| `uniform_real_wacc_fraction` | fraction | nein | nein |
| `electricity_price_offset_eur_per_mwh` | EUR_2023/MWh | ja | ja |
| `real_wacc_shift_fraction` | fraction | ja | ja |
| `real_wacc_multiplier` | factor | ja | ja |
| `electrolyzer_capex_factor` | factor | ja | ja |
| `electrolyzer_specific_electricity_factor` | factor | ja | ja |
| `h2_demand_multiplier` | factor | ja | nein |

Der Basiseintrag `baseline` ist die unveränderte Referenz, kein zusätzlicher Eingriff. WACC-Eingaben in Prozent/Prozentpunkten werden vor der nativen Schnittstelle durch 100 geteilt. Technische Parameter erlauben direkte Werte oder relative Prozentänderungen; Faktoren bleiben dimensionslos.

Numerische Varianten bleiben OAT. Die neue kategoriale Dimension `h2_delivery_profile` verändert ausschließlich die Lieferstunden bei gleicher Jahresmenge: native Originalinputs D0/D1/D2, keine numerischen Varianten auf zusätzlichen Profilstufen. Mehrere ausdrücklich ausgewählte Basisprofile bleiben getrennte parallele OAT-Kontexte.

## Studien, Standorte, Szenarien und Solver

- EU-Vergleich 2024 (`eu_2024`), Rolle current:
  - Hamburg–Moorburg (`hamburg_moorburg`): Profile D0, D1, D2; 11 numerische GUI-Parameter; 43 lesbare native Basisparameter; Neu-Ausführung freigegeben.
  - Huelva–La Rábida / Palos de la Frontera (`huelva_la_rabida`): Profile D0, D1, D2; 11 numerische GUI-Parameter; 43 lesbare native Basisparameter; Neu-Ausführung freigegeben.
- Namibia (`namibia`), Rolle historical:
  - Dokumentierter Namibia-Referenzstandort (1°-Zelle) (`namibia`): Profile D0; 11 numerische GUI-Parameter; 42 lesbare native Basisparameter; Neu-Ausführung freigegeben.

Szenarien: S0 · Referenz; S1 · monatliche Zuordnung; S2 · stündliche Zuordnung; S3 · ohne Netzanschluss

Solver: SciPy/HiGHS, Gurobi und expliziter Auto-Pfad; zusätzlicher HiGHS-/Gurobi-Vergleich und lesende Installations-/Lizenzprobe.

## Erhaltene Funktionen

- `direct_model_execution`: Einzelmodell, Szenarien-/Lieferprofilvergleich.
- `numeric_oat`: Native Einzelparameter; explizite Werte und Wertebereiche.
- `relative_technical_values`: Relative Prozentänderung für technische Kosten und PEM-Strombedarf.
- `common_namibia_eu_levels`: Gemeinsame relative Namibia-/EU-Parameterstufen.
- `solver_comparison`: Identische Eingaben mit HiGHS und Gurobi vergleichen.
- `solver_availability_probe`: Verfügbarkeit und Gurobi-Lizenzgrößenprobe.
- `registered_historical_results`: Namibia und EU; validierte gespeicherte Basisfälle und Versuchsreihen.
- `conservative_duplicate_grouping`: Identische Fälle und vollständige identische Versuchsreihen zusammenfassen.
- `original_execution_provenance`: Jede originale Ausführung, native Datei und Quellenbindung zugänglich.
- `saved_result_filters`: Standort, Studie, Lieferprofil, Szenario, Solver.
- `saved_sensitivity_filters`: Vollständige Versuchsreihe, Lieferprofil, Parameter, Kennzahl.
- `cross_study_comparison`: Gezielte Vergleiche mit Jahres-/Annahmen-/Historikwarnungen.
- `all_baseline_parameters_readonly`: Vollständige native Basiskonfiguration mit Einheiten, Quellen und Jahren.
- `source_provenance`: Wetter, Preise, Emissionsfaktoren, Kosten, WACC und synthetische Nachfrage.
- `year_roles`: Betrieb, Index, Wetter, Markt, Emissionen, Geldbasis, WACC, Ergebniszeitpunkt getrennt.
- `study_status_documentation`: Rolle, Standorte, Inputverfügbarkeit, Kompatibilität und Fallstudiendokumentation.
- `independent_validation`: Ergebnisgebundener Bericht mit eigenem Tabellen-SHA und Teilvalidierung.
- `input_hash_checks`: Originalinput, Quellenvertrag und Modellparameter-Provenienz.
- `red_partial_checks`: Zeitliche und elektrische THG-Teilprüfung; keine Vollzertifizierung.
- `live_job_status_logs`: Fortschritt, native Logs, Fehler und bisherige GUI-Läufe.
- `lcoh_chart`: LCOH.
- `capacity_chart`: PV, Wind, PEM, Kompressor, Speicher mit getrennten Einheiten.
- `cost_components_chart`: Native annualisierte und laufende Kostenbestandteile.
- `operational_metrics_chart`: Abgeleitete betriebliche Kennzahlen.
- `separate_emission_charts`: Betriebliche und regulatorische Emissionen getrennt.
- `hourly_operation_chart`: Gewählter lokaler Start und Stundenumfang; Erzeugung, Lieferung, Speicher.
- `numeric_sensitivity_curve`: Ein Parameter mit passenden eigenen Basisfällen.
- `filtered_results_csv`: Gefilterte native Ergebnistabelle.
- `sensitivity_table_csv`: Gefilterte Tabelle einer gespeicherten Versuchsreihe.
- `native_result_zip`: summary.csv, hourly_operation.csv, validated_input.csv, run_metadata.json.
- `native_metadata_json`: Native Ergebnis-Metadaten.
- `all_execution_tables_json`: Ausführungen-/Herkunftstabellen inklusive gespeicherter Kopien.
- `manual_md_pdf_download`: Markdown-Anleitung und bereits vorhandene historische PDF.

## Quellen, Validierung und Ergebnisgrößen

Alle Quellenverträge, Originalinputs, native Basisparameter und deren Quellen-/Jahresangaben sind im JSON vollständig gebunden. Die GUI-Ergebniskennzahlen werden vollständig aufgeführt:

- `lcoh_eur_per_kg_h2`: LCOH [EUR/kg H₂].
- `objective_eur_per_year`: Jahreskosten [EUR/a].
- `annual_h2_delivered_kg`: Gelieferte H₂-Jahresmenge [kg/a].
- `pv_capacity_mw`: PV [MW].
- `wind_capacity_mw`: Wind [MW].
- `electrolyzer_capacity_mw`: PEM [MW].
- `compressor_capacity_mw`: Kompressor [MW].
- `h2_storage_capacity_kg`: H₂-Speicher [kg].
- `annual_grid_import_mwh`: Netzbezug [MWh/a].
- `operational_emission_intensity_kg_co2e_per_kg_h2`: Betriebliche Intensität [kg CO₂e/kg H₂].
- `regulatory_emission_intensity_kg_co2e_per_kg_h2`: Regulatorische elektrische Teilintensität [kg CO₂e/kg H₂].

Hinzu kommen native vollständige Ergebnistabellen, abgeleitete Betriebskennzahlen, Kostenbestandteile, RED-Teilprüfungen, Solverstatus sowie stündliche Erzeugung, Netzbezug, Lieferung, Produktion und Speicher. Quellen-, Hash- und Validierungsinformationen bleiben zugänglich; ein optimaler Solverstatus ist kein unabhängiger Validierungsnachweis. Die historische PDF ist als vorherige Fassung gekennzeichnet; die aktuelle Bedienung steht im Markdown.

Die JSON-Bestandsliste enthält SHA-256 aller nativen Python-Dateien, Profil-CSV, Quellenmetadaten und Designs sowie die vollständigen standortspezifischen nativen Basisparameter. Der spätere Vergleich verlangt deren unveränderte Übereinstimmung.


## Ergänzte Tagesdarstellung

Der Bestand bleibt unverändert; zusätzlich ist Tagesstrom direkt in Analyse
und Sensitivitätsanalyse auswählbar. Datum, konkreter Fall, stündliche oder
kumulierte Energie und Direktversorgung bzw. Erzeugung werden getrennt
gewählt. Der bisherige Stundenbetrieb bleibt erhalten. Der erneute
Bestandsabgleich besteht 46/46; Nachweis im Archiv daily_view_20261006.


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
