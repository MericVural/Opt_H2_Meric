# Modellübergabe des H2-Modells

## 1. Zweck und aktueller Stand

Dieses Dokument ist die kurze Arbeitsanleitung für das im Rahmen der Forschungsarbeit entwickelte Modell. Das Modell bestimmt für einen frei wählbaren Einzelstandort die kostenminimale Auslegung und den stündlichen Betrieb einer Wasserstoffproduktionsanlage. Die Koordinate −21,0800° / 14,1610° in Namibia dient als Fallstudie; dieselbe Modellkette kann mit anderen Koordinaten erneut ausgeführt werden.

Eine ausführliche Erklärung sämtlicher Inputs, Datenquellen, Skripte, Outputs und Dateiübergaben für fachfremde Leser steht in `MODELLABLAUF_EINFACH_ERKLAERT.md`.

Der wissenschaftlich formulierte Entwurf zu Forschungsansatz, Systemgrenze, Datengrundlage, Modellgleichungen, RED-III-Abbildung und methodischen Einschränkungen steht in `METHODIK_UND_MODELLFORMULIERUNG.md`.

Eine kompakte, für das Betreuungsgespräch geeignete Abgrenzung des Aussagebereichs steht in `MODELLGRENZEN.md`.

Der geprüfte Stand umfasst Photovoltaik, Windenergie, Netzstrom, PEM-Elektrolyse, Verdichtung, einen 300-bar-H2-Speicher, eine feste H2-Nachfrage, LCOH sowie die monatliche und stündliche RED-III-Zeitkorrelation. S0 ist die Referenz ohne Zeitkorrelation, S1 verwendet monatliche Korrelation und S2 stündliche Korrelation.

## 2. Installation auf einem neuen Rechner

In der Anaconda Prompt werden die folgenden Befehle jeweils als vollständige Zeile eingegeben:

```bat
cd /d C:\Forschungsarbeit\Opt_H2_Meric-h2
conda env create -f environment_h2.yml
conda activate h2-model
python --version
```

Erwartet wird Python 3.11. Ist die Umgebung bereits vorhanden, genügt `conda activate h2-model`. Für Spyder muss anschließend der Interpreter `C:\Users\meric\anaconda3\envs\h2-model\python.exe` eingestellt und der Kernel neu gestartet werden.

Gurobi ist für kleine Vergleichstests enthalten. Die vollständigen Jahresläufe werden mit `--solver scipy-highs` gerechnet und benötigen deshalb keine große Gurobi-Lizenz.

## 3. Die Modellkette

1. `prepare_single_site_h2_input.py` erzeugt aus einer Koordinate eine validierte Stunden-CSV.
2. `run_h2_scenarios.py` optimiert S0, S1 und S2 mit exakt derselben Eingabe.
3. `validate_h2_results.py` rechnet die exportierten Bilanzen und Kennzahlen unabhängig nach.
4. `plot_h2_results.py` erzeugt sechs Ergebnisabbildungen.
5. `run_h2_sensitivity.py` und `plot_h2_sensitivity.py` führen die Einzelfaktor-Sensitivität aus und stellen sie dar.

Die nicht verwendeten Skripte, Notebooks, Stickstoff- und LCA-Daten sowie die alte Ammoniak-Umgebung wurden aus dem H2-Branch entfernt. Die benötigte Profilberechnung bleibt in `calculate_renewable_yield.py`; alle ausführbaren Modellschritte verwenden die oben genannten H2-Dateien.

## 4. Vorhandene Namibia-Fallstudie erneut rechnen

Vom Repositoryordner aus:

```bat
conda activate h2-model
python run_h2_scenarios.py --input outputs_h2\namibia_case_study\namibia_input_1deg.csv --output-dir outputs_h2\namibia_case_study\scenarios_wacc11 --solver scipy-highs --uniform-real-wacc 0.11 --wacc-source "Regionalfallback Subsahara-Afrika nach ursprünglicher Modelllogik" --overwrite
python validate_h2_results.py --results-dir outputs_h2\namibia_case_study\scenarios_wacc11 --expected-hours 8760 --overwrite
python plot_h2_results.py --results-dir outputs_h2\namibia_case_study\scenarios_wacc11 --start 2025-02-10 --hours 168 --overwrite
```

`--overwrite` ersetzt ausschließlich bereits vorhandene Ergebnisdateien im genannten Ausgabeordner. Wird es weggelassen, schützt das Programm bestehende Ergebnisse.

## 5. Einen anderen Standort untersuchen

Das folgende Beispiel zeigt die vollständige Vorbereitung für Namibia. Die beiden Koordinaten können durch einen anderen Punkt ersetzt werden. Für ein anderes Land muss ein belegter Netzemissionsfaktor entweder in `input_data/h2_country_factors.json` ergänzt oder mit `--grid-emission-factor` und `--grid-emission-source` übergeben werden.

```bat
python prepare_single_site_h2_input.py --latitude -21.0800 --longitude 14.1610 --country-code NA --spatial-resolution 1 --grid-emission-factor 220 --grid-emission-source "Electricity Control Board of Namibia, Integrated Annual Report 2025; Berichtsjahr 2024" --output outputs_h2\eigener_lauf\input\h2_input.csv
python run_h2_scenarios.py --input outputs_h2\eigener_lauf\input\h2_input.csv --output-dir outputs_h2\eigener_lauf\scenarios --solver scipy-highs --uniform-real-wacc 0.11 --wacc-source "Regionalproxy Subsahara-Afrika"
python validate_h2_results.py --results-dir outputs_h2\eigener_lauf\scenarios --expected-hours 8760
python plot_h2_results.py --results-dir outputs_h2\eigener_lauf\scenarios --start 2025-02-10 --hours 168
```

Die Datenaufbereitung ruft PVGIS auf und benötigt deshalb Internetzugang. Mit `--spatial-resolution 1` wird die eingegebene Koordinate wie im ursprünglichen Ammoniakmodell dem Mittelpunkt eines 1°-Pixels zugeordnet. Bei der Fallstudie wird aus −21,0800° / 14,1610° der Modellpunkt −21,5° / 14,5°.

## 6. Sensitivitätsanalyse

Die 16 Fälle stehen in `input_data/h2_sensitivity_cases.csv`. Alle drei Szenarien werden so gerechnet und anschließend für S2 dargestellt:

```bat
python run_h2_sensitivity.py --input outputs_h2\namibia_case_study\namibia_input_1deg.csv --cases input_data\h2_sensitivity_cases.csv --output-dir outputs_h2\namibia_case_study\sensitivity_step14 --scenarios all --solver scipy-highs --base-uniform-real-wacc 0.11 --base-wacc-source "Regionalfallback Subsahara-Afrika nach ursprünglicher Modelllogik" --overwrite
python plot_h2_sensitivity.py --comparison outputs_h2\namibia_case_study\sensitivity_step14\sensitivity_comparison.csv --scenario red_hourly --overwrite
```

## 7. Wo die Ergebnisse liegen

Jeder Szenarienlauf erzeugt:

- `scenario_comparison.csv`: direkte Gegenüberstellung von S0, S1 und S2,
- `scenario_comparison_metadata.json`: gemeinsamer Eingabe-Hash und Laufmetadaten,
- `S0_reference`, `S1_red_monthly` und `S2_red_hourly`: je Szenario validierte Eingabe, Zusammenfassung, Stundenbetrieb und Metadaten,
- `validation`: unabhängige Prüfprotokolle,
- `figures`: sechs PNG-Abbildungen und deren Quellenmanifest.

`outputs_h2/` ist von Git ausgeschlossen. Modellläufe verändern deshalb weder den Quellcode noch GitHub.

## 8. Abnahmeergebnis vom 12. September 2026

Die drei Namibia-Kernszenarien wurden mit 8.760 Stunden frisch über SciPy/HiGHS gelöst. Alle Solverstatus sind optimal. Die Ergebnisse lauten:

| Szenario | LCOH [EUR/kg H2] | Änderung zu S0 | PV [MW] | Wind [MW] | H2-Speicher [t] |
|---|---:|---:|---:|---:|---:|
| S0 Referenz | 6,965735 | 0,000 % | 36,50 | 0,00 | 0,3 |
| S1 RED III monatlich | 7,032868 | +0,964 % | 97,27 | 0,00 | 5,7 |
| S2 RED III stündlich | 7,426891 | +6,620 % | 102,73 | 0,00 | 18,5 |

Der unabhängige Validator besteht 61 von 61 Prüfungen. Die größten absoluten Residuen liegen bei rund `1,8e-14 MWh` in der Strombilanz und `2,3e-10 kg H2` in der Speicherbilanz. Die Abweichungen sind numerisches Solverrauschen und deutlich kleiner als die Prüftoleranzen.

Auch die Sensitivitätsanalyse wurde vollständig gerechnet: 16 Fälle mal 3 Szenarien ergeben 48 optimale Jahresläufe. Im S2-Basisfall ist der WACC der stärkste untersuchte LCOH-Treiber. Wind wird im Basiskostenfall nicht gebaut; bei dem rein explorativen Wert von 444,875 EUR/kW treten 19,98 MW Wind in die Lösung ein.

## 9. Drei manuell lesbare Stundenbilanzen

Die Werte stammen aus den frisch erzeugten CSV-Dateien. Rundungsdifferenzen entstehen nur durch die dargestellten Nachkommastellen.

**S0, 1. Januar 2025, 00:00 UTC – Strom:**

`PV 0 + Wind 0 + Netz 25,518246 = Elektrolyseur 24,678018 + Kompressor 0,840228 MWh`

**S0, 1. Januar 2025, 00:00 UTC – H2-Speicher:**

`alter Bestand 0 + Produktion 467,707197 − Nachfrage 416,666667 = neuer Bestand 51,040530 kg`

**S2, 1. Januar 2025, 09:00 UTC – Strom und H2-Speicher:**

`PV 66,045353 = Elektrolyseur 63,870707 + Kompressor 2,174646 MWh`

`alter Bestand 4.333,363867 + Produktion 1.210,501978 − Nachfrage 416,666667 = neuer Bestand 5.127,199179 kg`

## 10. Quellenhierarchie

1. Die rechtlichen RED-III-Annahmen stammen aus der Richtlinie (EU) 2023/2413 sowie den Delegierten Verordnungen (EU) 2023/1184 und 2023/1185. Der Rechtsstand des Modells ist in `red_iii_data.py` festgehalten.
2. Die technischen und wirtschaftlichen H2-Annahmen stammen vorrangig aus Brandt et al. (2024).
3. Die Wetterprofile stammen aus PVGIS-TMY-Daten; die verwendeten Auswahljahre werden in den Eingabemetadaten gespeichert.
4. Der Namibia-Netzfaktor von 220 kg CO2e/MWh stammt aus dem Integrated Annual Report 2025 des Electricity Control Board of Namibia und bezieht sich auf 2024.
5. Der reale WACC von 11 % ist ein regionaler Fallback für Subsahara-Afrika aus der ursprünglichen Modelllogik, keine direkt beobachtete Namibia-Finanzierung.

Jeder konkrete Lauf speichert Parameter, Einheiten, Quellen, Bezugsjahre und den SHA-256-Hash seiner Eingabe in den JSON-Metadaten.

## 11. Fachliche Grenzen

- Der Netzstrompreis ist in der Fallstudie ein konstanter Länderproxy und keine stündliche Day-Ahead-Preisreihe.
- Der Namibia-Netzemissionsfaktor ist ein landesweiter Jahreswert. Er ändert sich innerhalb des Jahres und zwischen Pixeln nicht.
- Der 11-%-WACC ist ein regionaler Proxy und wird deshalb in der Sensitivitätsanalyse variiert.
- Das Modell bildet den RED-III-THG-Teiltest sowie monatliche und stündliche Zeitkorrelation ab.
- Zusätzlichkeit, geografische Korrelation, Gebotszone, Vertragsgestaltung und eindeutige Stromallokation bleiben externe Nachweise.
- Die Niedrigpreis-Ausnahme ist deaktiviert, weil keine geeigneten Day-Ahead- und ETS-Preisreihen vorliegen.
- Die Systemgrenze endet beim verdichteten H2 am Produktionsstandort. Transport, Verteilung und spätere Nutzung sind nicht enthalten.
- Ein bestandener Modelltest ist keine vollständige rechtliche RFNBO-Zertifizierung.

## 12. Abschluss der technischen Modellarbeit

Schritt 15 ist abgeschlossen, wenn `pytest -q` erfolgreich ist, der Validator 61 von 61 Prüfungen besteht und die drei Szenarien mit demselben Eingabe-Hash optimal gelöst werden. Dieser Zustand wurde am 12. September 2026 erreicht. Die nächste Arbeit betrifft die wissenschaftliche Beschreibung, Ergebnisinterpretation und Abstimmung mit dem Betreuer. Änderungen werden erst nach einer bewussten Entscheidung committed oder zu GitHub übertragen.
