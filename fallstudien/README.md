# Fallstudien

Jede Fallstudie beschreibt ihre eigenen Daten, Quellen, Parameter, Zeiträume,
Sensitivitäten, Ergebnisse und Grenzen. Die gemeinsame Modellbeschreibung steht
in [MODELL_UND_METHODIK.md](../MODELL_UND_METHODIK.md); Projektstatus und nächste
Schritte stehen im [Masterplan](../FORSCHUNGSARBEITSPLAN.md).

| Fallstudie | Region | Rolle | Zeitbasis | Status | Datei |
|---|---|---|---|---|---|
| Namibia | Südwestafrika | Historischer Entwicklungs- und Validierungsfall | TMY-Monate 2007–2016; technischer UTC-Index 2025 | Jahresfälle und Sensitivitäten gerechnet und historisch abgenommen | [Namibia](FALLSTUDIE_NAMIBIA.md) |
| Hamburg / Huelva | Deutschland / andalusische Küste, Spanien | Aktuelle vergleichende Untersuchung | Tatsächliches lokales Schaltjahr 2024, 8.784 Stunden | Schritte 19–25 fachlich abgeschlossen; 132 eindeutige EU-Kombinationen nach Ergänzung; Manuskriptentwurf | [Hamburg und Andalusien](FALLSTUDIE_HAMBURG_ANDALUSIEN.md) |

Die beiden europäischen Anlagen werden getrennt optimiert. Namibia bleibt als
reproduzierbare Entwicklungshistorie erhalten; seine Annahmen werden nicht
automatisch auf die europäischen Standorte übertragen.

## Weitere Fallstudie ergänzen

1. Eine `FALLSTUDIE_<NAME>.md` in diesem Ordner anlegen.
2. Aufbau und Quellenstandard der bestehenden Fallstudien verwenden.
3. Diese Übersicht und die Fallstudientabelle im Masterplan ergänzen.
4. Die Projekt-README bei projektweiter Relevanz ergänzen.
5. Die allgemeine Methodik nur bei einer Änderung der Modellmethode anpassen.

Koordinaten, Raster, Jahr, Preise, Faktoren, WACC und Abnahmeprofile werden für
jeden neuen Fall ausdrücklich begründet. Allgemeine Modellgleichungen werden
verlinkt und nicht für jede Fallstudie erneut ausgeschrieben.

**Stand: 4. Oktober 2026.**

Die EU-Fortführung in Schritt 19 ergänzt ein reproduzierbares Faktoren-/KWK-Audit,
den vollständigen Spanien-Tagesenergievergleich und die technische Faktortrennung.
Die [erklärende PDF mit Stand Schritt 24](../output/pdf/Schritt_19_Wissenschaftlicher_Modellausbau.pdf) beschreibt die aktive 2024-Umsetzung, sechs ursprüngliche D0-Fälle und 60 neue abgenommene Nachfrage-/OAT-Ergebnisse. Die frühere dynamische Rekonstruktion bleibt als Quellenhistorie erhalten.

Die aktive EU-Basis verwendet seit der anschließenden Nutzerentscheidung vom
03.10.2026 statische EEA-2024-Länderreferenzen mit dokumentierter eigener
Eurostat-Brutto/Netto-Umrechnung. Die frühere dynamische Faktoren-/KWK-Prüfung
bleibt als offene optionale Untersuchung und Quellenhistorie nachvollziehbar.

Die aktive EU-Zeitbasis wurde danach auf tatsächliches **2024** umgestellt.
Wetter, Marktpreise und betriebliche Emissionsreferenz passen zum selben Jahr.
D0/D1/D2 liegen für beide Standorte mit gleicher Jahresmenge vor. EUR 2023
bleibt gemeinsame Geldbasis; WACC 2021 bleibt ausdrücklich Finanzierungsproxy.
Die frühere 2025-Daten- und Prüfgeschichte wird nicht umbenannt.

Die Ortsmonatkorrelation ist anschließend in Solver, RED-Modul und Validator
implementiert und gezielt geprüft. Die sechs D0-Originalfälle aus Schritt 23 bleiben
unverändert erhalten. **Schritt 24 abgeschlossen:** 60 neue optimale Jahresfälle (12 Nachfrage- und 48 ökonomische Varianten), 2240/2240 unabhängige Exportprüfungen; sechs unveränderte D0-Ergebnisse aus Schritt 23 wiederverwendet.
Tabellen, Ergebnisgrenzen und Reproduktion stehen in der EU-Fallstudie. **Schritt 25 fachlich abgeschlossen:** Ergebnisdiskussion, Primärliteraturvergleich und Fazit stehen im [Manuskriptentwurf](../manuskript/FORSCHUNGSARBEIT_ENTWURF.md). Nächste Aufgabe: Durchsicht mit der Betreuung und formale Manuskriptanpassung. Weitere Modellvarianten sind kein automatisch begonnener Folgeschritt.

## Gemeinsame Vergleichsausgabe

Die [Grafikübersicht](../outputs_h2/cross_case_consistency/alignment_20261004/figures/GRAFIKEN_UEBERSICHT.md) und [144-Fall-Tabelle](../outputs_h2/cross_case_consistency/alignment_20261004/results/common_sensitivity_comparison.csv) verwenden dieselben sieben Sensitivitätsfamilien und relativen Stufen für alle drei Standorte. Die bisherigen 66 EU-Kombinationen bleiben die Step24/25-Basis; 66 neue EU-Varianten erweitern die Vereinigung auf 132. Nachfrage und alte absolute Preis-/WACC-Stufen bleiben Zusatzanalysen. Namibia-Daten und historische Ergebnisse bleiben erhalten.
