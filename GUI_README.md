# Lokale H₂-Forschungswerkstatt

**Stand: 12. Oktober 2026 · aktive Oberfläche U2.** Der sichtbare Einstieg erfolgt
über Forschungsfragen. Der Standard zeigt bestehende Ergebnisse; eine neue
Berechnung startet erst durch den ausdrücklichen Startknopf. Der vollständige
freigegebene wissenschaftliche Funktionsumfang bleibt erhalten.

[Bedienungsanleitung](GUI_BEDIENUNGSANLEITUNG.md) ·
[U2-Prüfstand](GUI_U2_ABNAHME.md) · [Bestand](GUI_BESTANDSLISTE.md) ·
[Weitergabe auf einen anderen Rechner](GUI_UEBERGABE.md).

Analyse: Stromregeln, Anlage, Tagesbetrieb, Solver. Sensitivitätsanalyse:
H₂-Menge, Lieferzeiten, Preis/Finanzierung/Technik. Vergleich: Standorte oder
eigene Fälle. Quellen und Export bleiben eigene Bereiche. Die aktuelle Anleitung
beschreibt die genauen Wege; die frühere PDF ist als historisch gekennzeichnet.

## Start und Installation

**Alltag:** Im Windows-Explorer `C:\Forschungsarbeit\Opt_H2_Meric-h2` öffnen
und **H2-Modell starten.cmd** doppelt anklicken. Die Oberfläche öffnet im
normalen Browser <http://127.0.0.1:8510/>. Der Starter verwendet ausschließlich
`.venv-gui/Scripts/python.exe` im Modellrepository. Es gibt keinen Rückfall auf
den OneDrive-Chat-Arbeitsordner. Codex muss nicht geöffnet sein.

[Vollständige Bedienanleitung](GUI_BEDIENUNGSANLEITUNG.md),
[historische PDF-Fassung vom 5. Oktober](GUI_BEDIENUNGSANLEITUNG.pdf),
[kurze Startanleitung](H2-GUI-START.md), [Ordnerzuständigkeiten](ORDNERSTRUKTUR.md).
Die PDF und die bearbeitbare Anleitung sind auch in der GUI-Seitenleiste
über **Frühere Anleitung** und **Bedienungsanleitung** abrufbar.

Die GUI verwendet **Streamlit 1.65.0** in einer frisch angelegten eigenen
Umgebung mit `--system-site-packages`. Alle 25 zusätzlich lokalen Paketversionen
wurden aus den zuvor verwendeten, vorhandenen Wheels übernommen. Die wissenschaftliche
Anaconda-Umgebung `C:\Users\meric\anaconda3\envs\h2-model` bleibt unverändert:
Sie stellt Python 3.11.15 und die wissenschaftlichen Pakete sowie den nativen
Modellprozess bereit. Die GUI-Pakete und der GUI-Worker liegen lokal im Repository.

Ein sichtbarer Terminalstart verwendet denselben lokalen Interpreter:

```powershell
Set-Location 'C:\Forschungsarbeit\Opt_H2_Meric-h2'
& .\.venv-gui\Scripts\python.exe gui/start_local_gui.py --no-browser
```

Die vollständig gepinnten zusätzlichen GUI-Pakete stehen in
`gui/requirements-local.lock.txt`. Nur bei einer fehlenden Installation wird
eine neue Umgebung angelegt; eine vorhandene Umgebung nicht ungeprüft überschreiben:

```powershell
Set-Location 'C:\Forschungsarbeit\Opt_H2_Meric-h2'
& 'C:\Users\meric\anaconda3\envs\h2-model\python.exe' -m venv --system-site-packages .venv-gui
& .\.venv-gui\Scripts\python.exe -m pip install -r gui/requirements-local.lock.txt
& .\.venv-gui\Scripts\python.exe gui/start_local_gui.py
```

Der minimale deklarierte GUI-Einstieg bleibt `gui/requirements.txt`; die
Lockdatei bildet den konkret übernommenen Stand ab. Die tatsächliche Migration
verwendete ausschließlich lokale gecachte Wheels und das vorhandene Python-Bundle;
es gab keine neuen Downloads und keine wissenschaftlichen Paketupdates.
Alte Python-Umgebungen werden nicht durch bloßes Verschieben eines Venv-Ordners ersetzt.

Der direkte Start bleibt möglich:

```powershell
& .\.venv-gui\Scripts\python.exe -m streamlit run gui/app.py --server.address 127.0.0.1 --server.port 8510 --server.headless true --browser.gatherUsageStats false --server.fileWatcherType none
```

Die GUI ist ausschließlich lokal erreichbar. Der normale Start berechnet keine
Modellfälle. Hintergrundaufträge besitzen eigene persistente Jobordner und werden
durch das Schließen der Browserseite nicht beendet. Ein PC-Neustart beendet die
Prozesse; er startet unvollständige Aufträge nicht automatisch erneut.

Startprotokoll: `outputs_h2/gui_runtime/server.log`.
Letzter Serverstart: `outputs_h2/gui_runtime/server.json` mit PID, Interpreter,
App-Pfad und URL. Ein vorhandener Server wird vom Starter verwendet; ein
Interpreterwechsel ist erst nach einem belegten Neustart nachgewiesen.

**Startkorrektur vom 12.10.2026:** Unter Windows fordert der Starter einen
unsichtbaren Server mit eigener Prozesslebensdauer an (`CREATE_BREAKAWAY_FROM_JOB`).
Damit kann der Server nach Ende des startenden Terminals weiterlaufen.
Verweigert Windows diesen Start aus einer verwalteten Prozessumgebung, meldet
der Starter den Fehler und verweist auf den Start im Windows-Explorer.
Ein bereits erreichbarer Server wird weiterverwendet; ein PC-Neustart erfordert
erneutes Öffnen von **H2-Modell starten.cmd**. Der angeforderte Startmodus steht
als `creation_flags` im Startnachweis.

## Architektur und wissenschaftliche Bindung

- `gui/app.py`: produktiver Einstieg und erhaltene Hilfsansichten/Exporte.
- `gui/research_workspace.py`: Fragen, fachliche Formulare, Ergebnisansichten,
  bedarfsweise Detaildaten und dateigebundener Ergebniscache.
- `gui/research_logic.py`: Analyseziele, Mengenstufen und vorsichtige Beschreibung
  tatsächlich gespeicherter Ergebnisunterschiede; keine Optimierungsgleichungen.
- `gui/analysis_contracts.py`: U1-Vertrag für tatsächliche Eingriffe, eigene
  Basen und kontrollierte Vergleichsidentität.
- `gui/plotting.py` und `gui/result_loader.py`: native Auswertungen, Bilanzen,
  eindeutige Zeitfenster und bestehende wissenschaftliche Diagramme.
- `gui/sensitivity_design.py`, `model_adapter.py`, `jobs.py`: bestehende native
  Runner. Mehrere Standorte werden vor der Übergabe in flache Einzelpläne zerlegt.
- `.streamlit/config.toml`: helle Projektgestaltung mit hoher Textlesbarkeit.

EU: historischer Betrieb/Wetter/Markt 2024, reale Kostenbasis EUR 2023,
statische betriebliche Länderfaktoren und WACC-Proxy 2021. Namibia bleibt ein
historischer TMY-Referenzfall. Die Darstellung behauptet keine vollständige
RFNBO-Zertifizierung, keine vollständige LCA und keine Investitionsrentabilität.

## Entwicklung und Nachweise

Der Änderungsumfang umfasst Oberfläche, Tests, Gestaltung und Dokumentation.
Native Gleichungen, Inputs und Jahreslösungen werden nicht geändert.
U3-Auftragsverwaltung und umfassende U4-Nutzer-/Geräteabnahme bleiben offen.
Die alten explizit aufgerufenen UI-Regressionsdateien beschreiben den früheren
Formularablauf; die aktive U2-Bedienung wird in
`gui/checks/research_workspace_regression.py` geprüft. U1-Referenz-, Diagramm-,
Tages- und Versuchsplanverträge werden separat weitergeprüft.

Die Nachweise und die verwendeten Testbefehle stehen in
[GUI_U2_ABNAHME.md](GUI_U2_ABNAHME.md). Neue Jahresläufe sind keine Voraussetzung
für einen Darstellungstest. Der letzte externe GitHub-Übergabestand ist gesondert
dokumentiert; eine lokale U2-Installation behauptet keinen erneuten Push.
