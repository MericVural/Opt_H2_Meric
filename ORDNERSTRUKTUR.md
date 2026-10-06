# Einheitliche Ordnerstruktur des H2-Modells

Stand: 5. Oktober 2026. Maßgeblicher Projektordner:
**C:\Forschungsarbeit\Opt_H2_Meric-h2**.

| Bereich | Zuständigkeit |
|---|---|
| Native `.py` im Hauptordner | Wissenschaftlicher Modellkern, Datenaufbereitung, native Runner, Validierung |
| `gui/` | Benutzeroberfläche, Registry, Adapter, Ergebnisloader, Launcher und explizite GUI-Tests |
| `.venv-gui/` | Lokaler GUI-Interpreter und zusätzliche GUI-Pakete; von Git ausgeschlossen |
| `input_data/` | Modellkonfiguration und dokumentiertes Fallstudiendesign |
| `outputs_h2/` | Freigegebene Stundeninputs, Ergebnisse, Grafiken und nachvollziehbare Verträge |
| `outputs_h2/gui_runs/` | Neue Berechnungsaufträge mit eingefrorenem Plan/Code/Inputs und nativen Exporten |
| `outputs_h2/gui_runtime/` | Aktueller Serverbeleg und Startprotokoll |
| `outputs_h2/gui_validation/` | Historische und aktuelle GUI-Prüfbelege, Sicherungen und Migrationsnachweise |
| `tests/` und `gui/checks/` | Native Tests beziehungsweise explizite Bedienprüfungen im GUI-Interpreter |
| `fallstudien/` | Namibia-/EU-Dokumentation und Abnahmen |
| `manuskript/` | Wissenschaftlicher Manuskriptentwurf |
| Aktuelle MD/PDF im Hauptordner | Plan, Methodik, Übersicht, Startanleitung und vollständige GUI-Anleitung |

## Was außerhalb bleibt

`C:\Users\meric\anaconda3\envs\h2-model` ist die vorhandene wissenschaftliche
Python-Installation. Sie ist eine bewusst separat installierte Laufzeitumgebung;
die GUI-Migration verändert ihre Pakete nicht.

`C:\Forschungsarbeit\Opt_H2_Meric-main-git` hält die gemeinsame Git-Verwaltung
des Worktrees. Die `.git`-Datei im Modellordner verweist dorthin. Diese notwendige
Git-Struktur wird nicht verschoben oder zusammengeführt.

Der frühere OneDrive-Chat-Arbeitsordner enthält Entwürfe, temporäre Prüfungen und
Hilfsunterlagen. Er ist kein zweites aktives Modellrepository. Die dortigen
Starter wurden durch Weiterleitungen ersetzt. Ihre Originale sind samt Hashes
unter `outputs_h2/gui_validation/unification_20261005/prior_workspace/` gesichert.
Die alte GUI-Venv und alte temporäre Pfade bleiben für historische Belege und
frühere eingefrorene Jobverträge erhalten; neue normale GUI-Aufträge verwenden
die lokale Venv. Das alte `output/` im Modellrepository bleibt ein historischer
Bereich; neue H2-Modellaufträge schreiben unter `outputs_h2/`.

Historische Ergebnispfade und Quellenverträge werden nicht nachträglich
umgeschrieben. Aktuelle Anleitung und Startdatei sind eindeutig hier im Modellordner.

[GUI-Bedienung](GUI_BEDIENUNGSANLEITUNG.md), [technische Einrichtung](GUI_README.md),
[Migrationsnachweis](outputs_h2/gui_validation/unification_20261005/unification_receipt.json).
