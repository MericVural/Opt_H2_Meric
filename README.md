# Kostenoptimierte Wasserstoffproduktion unter RED-III-Stromversorgungskriterien

Dieses Forschungsprojekt entwickelt ein lineares Optimierungsmodell für die
Auslegung und den stündlichen Betrieb einer Wasserstoffproduktionsanlage.
Das Modell wählt PV-, Onshore-Wind-, Elektrolyseur-, Kompressor- und
H2-Speicherkapazität so, dass eine vorgegebene Wasserstoffnachfrage zu minimalen
annualisierten Kosten erfüllt wird.

Die Forschungsfrage lautet:

> Wie beeinflussen die modellierten RED-III-Stromversorgungskriterien die
> kostenminimale Auslegung und die Wasserstoffgestehungskosten an unterschiedlichen
> Standorten, und wie verändern Strompreise, Finanzierung und zeitliche
> Wasserstoffabnahme diese Ergebnisse?

Pro Lauf wird ein Standort betrachtet. Weitere Standorte benötigen passende
Eingaben und können mit demselben Modellkern untersucht werden.

## GUI auf dem eigenen Rechner

Der Branch `h2-single-site` enthält die vollständige GUI, den nativen Modellkern
und einen gehashten Snapshot der registrierten wissenschaftlichen Inputs und
Ergebnisse für Hamburg, Huelva und Namibia. Einrichtung nach dem Klonen:
**H2-Modell einrichten.cmd**, danach **H2-Modell starten.cmd**.
Die GUI öffnet unter <http://127.0.0.1:8510/>; Codex wird nicht benötigt.

[Einrichtung und Datenübergabe](GUI_UEBERGABE.md) ·
[Bedienungsanleitung](GUI_BEDIENUNGSANLEITUNG.md) ·
[Technik und Funktionsumfang](GUI_README.md).

Tagesbetrieb einzelner Fälle: **Analyse → Gespeicherte Ergebnisse → Ergebnisreihe**.
Parameterwirkungen: **Sensitivitätsanalyse**. Alle bisherigen Modellparameter,
Szenarien und Solver bleiben vorhanden.

## Aktueller Stand

- Der H2-Kern einschließlich S0/S1/S2, zwei Solverpfaden, Szenarienlauf,
  Sensitivitäten, Ergebnisprüfung und Grafiken wurde mit Namibia entwickelt.
- Hamburg–Moorburg und Huelva–La Rábida sind die aktuelle vergleichende
  Untersuchung. Schritt 18 ist methodisch abgeschlossen.
- **Aktive EU-Basis auf 2024 umgestellt:** je Standort alle 8.784 Stunden des
  historischen lokalen Schaltjahrs, tatsächliche Wetter- und Strompreisquellen
  2024 sowie statische Emissionsreferenzen 2024. Preise sind in reale EUR 2023 umgerechnet.
- Betriebliche Bewertung: DE **304,7**, ES **128,8 kg CO2e/MWh**. Gemeinsame
  EEA-Quelle und eigene näherungsweise Eurostat-Brutto/Netto-Umrechnung;
  nationale Erzeugungsreferenz mit dokumentierten Raum-/Nennergrenzen.
- Betriebliche und regulatorische Faktoren haben getrennte gehashte Quellenverträge.
  Die 2025-Archive und die frühere `regulatory_only`-Freigabe bleiben als Historie erhalten.
- **Schritte 19–22 umgesetzt und Schritt 23 abgenommen:** sechs vollständige Inputs für D0/D1/D2,
  beide EU-Runner und kalendarische Annualisierung. Volles 2024 hat Faktor 1;
  die feste Jahreslieferung bleibt 3.650.000 kg H2 je Standort und Profil.
- Zeitliche Konsistenz von Wetter, Markt und Betriebsreferenz ist hergestellt.
  WACC 2021 bleibt ein ausdrücklicher Finanzierungsproxy für 2024;
  normative Rechtswerte 2020 und die Geldbasis EUR 2023 sind getrennte Jahresrollen.
- Monatliche Stromkorrelation verwendet jetzt Europe/Berlin bzw. Europe/Madrid
  in beiden Solvern, RED-Prüfer und unabhängigem Validator.
- **Schritt 23 abgeschlossen:** alle sechs D0-Jahresfälle optimal gelöst;
  224/224 unabhängige Exportprüfungen bestanden. Ergebnisse stehen in der EU-Fallstudie.
- **Schritt 24 abgeschlossen:** 60 neue optimale Jahresfälle (12 Nachfrage- und 48 ökonomische Varianten), 2240/2240 unabhängige Exportprüfungen; sechs unveränderte D0-Ergebnisse aus Schritt 23 wiederverwendet.
- **GUI und H₂-Nachfragemengenstudie:** fünf Hauptbereiche, gespeicherte Tagesauswertung sowie 90 validierte Jahresfälle mit 50/75/100/125/150 % der Basisnachfrage.
- **Erneuter Modelllauf am 04.10.2026:** sechs frische D0-Jahreslösungen mit aktuellem Code optimal gerechnet und mit 224/224 Exportprüfungen bestätigt; [Ergebnistabelle](outputs_h2/eu_case_studies/historical_2024/verification_runs/basis_20261004_121938UTC/fresh_D0_results.csv). Die 66 wissenschaftlichen Ergebnisfälle werden dadurch nicht um neue Szenariokombinationen erweitert.


Die [Grafikübersicht der frischen EU-Basisfälle](outputs_h2/eu_case_studies/historical_2024/verification_runs/basis_20261004_121938UTC/figures_20261004/GRAFIKEN_UEBERSICHT.md) enthält
Kosten, Auslegung, Kostenanteile, Betriebskennzahlen, Stundenverläufe und die
getrennte Emissionsdarstellung für Hamburg und Huelva.

Die Ergebnisflags des RED-Moduls belegen modellinterne Teilprüfungen. Sie sind
kein vollständiger RFNBO-Zertifizierungsnachweis.

## Wo steht welche Information?

| Dokument | Zweck |
|---|---|
| [FORSCHUNGSARBEITSPLAN.md](FORSCHUNGSARBEITSPLAN.md) | Forschungsrahmen, Fortschritt, Reihenfolge und nächste Aufgaben |
| [MODELL_UND_METHODIK.md](MODELL_UND_METHODIK.md) | Allgemeiner Modellkern, Gleichungen, Datenfluss, RED-Abbildung und Grenzen |
| [Fallstudienübersicht](fallstudien/README.md) | Index aller bestehenden und späteren Fallstudien |
| [Namibia](fallstudien/FALLSTUDIE_NAMIBIA.md) | Historische Daten, Entwicklung, Abnahme, Ergebnisse und Reproduktion |
| [Hamburg und Andalusien](fallstudien/FALLSTUDIE_HAMBURG_ANDALUSIEN.md) | EU-Datenvertrag 2024, Quellen, Jahresbasis- und Sensitivitätsergebnisse mit Aussagegrenzen |

## Wichtigste Modellskripte

| Datei | Aufgabe |
|---|---|
| [config_h2.py](config_h2.py) | Validierte technische und wirtschaftliche Konfiguration |
| [prepare_single_site_h2_input.py](prepare_single_site_h2_input.py) | Bisherige Standortdatenaufbereitung mit TMY-/Länderproxies |
| [calculate_renewable_yield.py](calculate_renewable_yield.py) | Wetter in PV- und Windprofile umrechnen |
| [acquire_eu_historical_sources.py](acquire_eu_historical_sources.py) | Historische EU-Rohquellen mit Abrufnachweisen archivieren |
| [prepare_eu_historical_data.py](prepare_eu_historical_data.py) | EU-Wetter/Preise und Erzeugungsdiagnostik; noch kein freigegebener Solverinput |
| [eu_emission_factor_audit.py](eu_emission_factor_audit.py) | 2024-Bilanzen und direkte Brennstofffaktoren prüfen; bedingte KWK-Szenarien berechnen |
| [audit_eu_generation_quality.py](audit_eu_generation_quality.py) | REE-Momentanleistung mit offiziellen Tagesenergien vergleichen |
| [prepare_eu_regulatory_inputs.py](prepare_eu_regulatory_inputs.py) | Frühere Kosten-/Regulatorik-Freigabe ohne betriebliche Bewertung |
| [prepare_eu_static_inputs.py](prepare_eu_static_inputs.py) | Aktive EU-Inputs mit belegten statischen Länderreferenzen und getrennten regulatorischen Faktoren |
| [eu_demand_profiles.py](eu_demand_profiles.py) | Synthetische D0/D1/D2-Abnahme im tatsächlichen Ortskalender mit gleicher Jahresmenge |
| [eu_site_configuration.py](eu_site_configuration.py) | Explizite EU-Standortwahl und belegte WACC-Komponenten |
| [h2_input_data.py](h2_input_data.py) | Stündliche Eingaben und getrennte Faktorquellen prüfen |
| [opt_hydrogen_functions.py](opt_hydrogen_functions.py) | Kapazitäten und Betrieb optimieren; Kosten und Kennzahlen berechnen |
| [red_iii_data.py](red_iii_data.py) | Regulatorische Parameter und unabhängige Teilprüfung |
| [run_single_site_h2.py](run_single_site_h2.py) | Einen Standort und ein Szenario rechnen |
| [run_h2_scenarios.py](run_h2_scenarios.py) | S0/S1/S2 mit gemeinsamer Eingabe rechnen |
| [validate_h2_results.py](validate_h2_results.py) | Gespeicherte Ergebnisse unabhängig nachrechnen |
| [plot_h2_results.py](plot_h2_results.py) | Szenariengrafiken aus vorhandenen Ergebnissen erzeugen |
| [run_h2_sensitivity.py](run_h2_sensitivity.py) | Einzelfaktorvarianten mit gebundenen Quellen rechnen; akzeptierte Basisläufe wiederverwenden |
| [plot_h2_sensitivity.py](plot_h2_sensitivity.py) | Sensitivitäten darstellen |

Konfigurations-, Prüf- und Funktionsmodule werden von den Startskripten importiert.
Man muss sie nicht einzeln starten.

## Grundlegender Ablauf

1. Standortdaten beschaffen, zeitlich abstimmen und eine Stunden-CSV erzeugen.
2. S0/S1/S2 mit `run_h2_scenarios.py` rechnen.
3. Die gespeicherten Ergebnisse mit `validate_h2_results.py` prüfen.
4. Mit `plot_h2_results.py` darstellen und danach Sensitivitäten auswerten.

Eine Validierung oder Grafik kann auch alte Ergebnisse lesen, wenn ein neuer
Modelllauf fehlgeschlagen ist. Ein erfolgreicher Plot belegt daher keinen neuen Lauf.
Exakte Namibia- und EU-Befehle stehen in den jeweiligen Fallstudien.

## Entwicklungsumgebung

Die lokale Umgebung heißt `h2-model` und nutzt Python 3.11. Die Abhängigkeiten
stehen in [environment_h2.yml](environment_h2.yml).

```cmd
cd /d C:\Forschungsarbeit\Opt_H2_Meric-h2
conda env create -f environment_h2.yml
conda activate h2-model
```

Bei bereits vorhandener Umgebung genügt die Aktivierung. In Spyder muss dieselbe
Umgebung als Interpreter eingestellt sein. Hinweise dazu sowie zu Gurobi/HiGHS
stehen in der allgemeinen Methodik. Volljahresrechnungen nutzten lokal SciPy/HiGHS.

## Herkunft und ergänzende Artefakte

Das Projekt entwickelt den Ansatz des ursprünglichen Ammoniakmodells von
Terlouw et al. (2026) zu einem H2-Modell weiter. Die erneuerbare Profilberechnung
wurde übernommen und angepasst; H2-Kern, RED-Prüfung und Runner wurden neu aufgebaut.
Ammoniak- und vollständige LCA-Bausteine gehören nicht zum H2-Kern.

Die [Lizenz](LICENSE) ist BSD 3-Clause; vorhandene Urheberhinweise bleiben erhalten.
Die [Erklärung als PDF mit Stand Schritt 24](output/pdf/Schritt_19_Wissenschaftlicher_Modellausbau.pdf) erläutert die Daten-/Faktorenprüfung
und Schritte 20–24 einschließlich der tatsächlichen Basis-, Nachfrage- und
ökonomischen Jahresresultate sowie ihrer Aussagegrenzen.

Die betroffenen Markdown-Dateien werden nach jedem Arbeitsschritt gepflegt.
Seit der Nutzerentscheidung vom 04.10.2026 werden PDFs zu größeren
Meilensteinen oder auf ausdrücklichen Wunsch aktualisiert. Eine vollständige
Modellerklärung kann bei Bedarf anhand der dokumentierten Methodik, Quellen,
Entscheidungen, des Codes und der gespeicherten Ergebnisse erstellt werden.

Die [frühere Modellübersicht als PDF](H2_Modell_Uebersicht_Einfach_Erklaert.pdf),
das [Übersichtsbild](modell_uebersicht.svg) und die
[Präsentation](Systemgrenzen%20der%20Forschungsarbeit.pptx) sind ergänzende Artefakte.
Sie wurden bei der Dokumentationsreorganisation nicht aktualisiert und ersetzen
den aktuellen Masterplan und die Fallstudiendokumente nicht.

**Dokumentationsstand: 4. Oktober 2026.** Schritte 19–25 fachlich abgeschlossen; 66 Ergebnisfälle einschließlich sechs unveränderter D0-Basisfälle und wissenschaftlicher Manuskriptentwurf. Die formale Einreichung bleibt offen.
Die aktuelle Softwareabnahme umfasst 618 Tests und 6 Unterprüfungen; sie ist
von der jährlichen Ergebnisabnahme getrennt. Die 60 neuen Step24-Fälle bestehen 2240/2240 Exportprüfungen und einen
separaten 4975/4975 Quellen-/Ergebnisaudit. Die ursprünglichen sechs D0-Fälle und ihre 224/224 Exportprüfungen bleiben
unverändert erhalten. Quellenbelege, Aussagegrenzen und Reproduktion stehen
in der EU-Fallstudie; Namibia-Ergebnisse und frühere EU-Archive bleiben erhalten.

## Gemeinsame Namibia-/EU-Sensitivitäten und Grafiken

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

[Grafikübersicht](outputs_h2/cross_case_consistency/alignment_20261004/figures/GRAFIKEN_UEBERSICHT.md); [144-Fall-Tabelle](outputs_h2/cross_case_consistency/alignment_20261004/results/common_sensitivity_comparison.csv); [Laufvertrag](outputs_h2/cross_case_consistency/alignment_20261004/experiment_contract.json); [Abnahme](outputs_h2/cross_case_consistency/alignment_20261004/completion_receipt.json).

Die neue gemeinsame Ausgabe ist die aktive Vergleichsdarstellung; frühere Schritt-24-Bänder bleiben Zusatzanalysen. PDFs werden wie vereinbart nicht nach jedem Arbeitsschritt neu erzeugt.

## Lokale Forschungsmodell-GUI

Die lokale Streamlit-Oberfläche bedient die vorhandenen Runner und lädt gespeicherte EU-/Namibia-Ergebnisse. [GUI-Start, Architektur und Grenzen](GUI_README.md); [GUI-Abnahme](GUI_ABNAHME.md). Neue Aufträge erhalten eigene Ergebnisordner.

Normaler Einstieg: **H2-Modell starten.cmd** im Modellordner doppelt anklicken.
Die GUI-Umgebung liegt ebenfalls hier unter `.venv-gui`; der Chat-Arbeitsordner
ist für den normalen Start nicht erforderlich.
[Vollständige Bedienanleitung](GUI_BEDIENUNGSANLEITUNG.md),
[PDF](GUI_BEDIENUNGSANLEITUNG.pdf), [Ordnerstruktur](ORDNERSTRUKTUR.md).

