# GUI und Modell auf einem anderen Rechner

Der Branch `h2-single-site` enthält den vollständigen Modell-/GUI-Quellcode,
die Bedienungsanleitung, eine gemeinsame Abhängigkeitsliste und einen mit
SHA-256 gebundenen Datensnapshot. Es ist keine Codex-Installation notwendig.

## Windows: einmal einrichten, danach normal starten

1. Python 3.11 und Git installieren bzw. vorhandene Installationen verwenden.
2. Diesen Branch klonen:

   ```powershell
   git clone --branch h2-single-site https://github.com/MericVural/Opt_H2_Meric.git
   cd Opt_H2_Meric
   ```

3. **H2-Modell einrichten.cmd** öffnen. Das legt `.venv-gui` an, installiert
   die GUI und wissenschaftlichen Pakete und entpackt die Daten.
4. **H2-Modell starten.cmd** öffnen. Browseradresse: <http://127.0.0.1:8510/>.

Alternativ die Einrichtung sichtbar im Terminal ausführen:

```powershell
py -3.11 -m venv .venv-gui
.\.venv-gui\Scripts\python.exe -m pip install -r requirements-h2-gui.txt
.\.venv-gui\Scripts\python.exe -B gui\restore_shared_data.py
.\.venv-gui\Scripts\python.exe -B gui\start_local_gui.py
```

Mit **Analyse → Gespeicherte Ergebnisse → Ergebnisreihe** vorhandene Basisfälle
oder einzelne Sensitivitätsfälle auswählen. **Darstellung → Tagesstrom:
Solar, Wind und Netz** bietet Datum, Stundenverlauf oder kumulierte Tagesenergie.
**Sensitivitätsanalyse** vergleicht die Wirkung geänderter Parameter.
Die ausführliche Bedienung steht in [GUI_BEDIENUNGSANLEITUNG.md](GUI_BEDIENUNGSANLEITUNG.md).

## Inhalt und Quellenbindung

`gui/data_snapshot/manifest.json` dokumentiert jede Originaldatei und alle
ZIP-Prüfsummen. Enthalten sind die freigegebenen EU-2024-Inputs D0/D1/D2,
der historische Namibia-Input, alle in der GUI registrierten wissenschaftlichen
Ergebnisreihen, deren native Stundenwerte, Metadaten und vorhandene unabhängige
Prüfnachweise. Die 90 H₂-Nachfragefälle mit 50/75/100/125/150 % sind enthalten.
Lokale GUI-Aufträge, Laufprozesse und Python-Umgebungen sind rechnergebunden.

Die ZIP-Dateien sind in Teilen gespeichert und werden ausschließlich lokal
unter ihren ursprünglichen relativen Pfaden entpackt. Die Originalbytes und
Prüfsummen bleiben erhalten. Absolute historische Projektpfade werden beim
Lesen nur für im Manifest benannte Dateien/Ordner auf den aktuellen Checkout
abgebildet. Alle anderen externen Pfade bleiben abgewiesen. Bestehende abweichende
Dateien werden nicht überschrieben. Nach dem Entpacken kann geprüft werden:

```powershell
.\.venv-gui\Scripts\python.exe -B gui\restore_shared_data.py --check
```

Die freigegebenen Modellinputs reichen für neue Optimierungen. Der Snapshot
ist eine GUI-/Modellübergabe; zusätzliche historische Rohdatenarchive können
bei einer vollständigen Wiederholung der Datenbeschaffung separat erzeugt werden.
Die vorhandenen Quellenangaben bleiben in Metadaten und **Quellen** sichtbar.

## Solver und Modellumgebung

**SciPy/HiGHS** ist für neue Jahresfälle verfügbar, ohne Gurobi-Lizenz.
`gurobipy` wird mitinstalliert, weil der vorhandene native Modellkern das Paket
auch für den HiGHS-Pfad importiert. Gurobi-Jahresläufe benötigen eine ausreichende
eigene Lizenz. Die gespeicherten Ergebnisse benötigen keine neue Optimierung.

Auf einem Rechner mit eigener wissenschaftlicher Python-Umgebung kann vor dem
GUI-Start `H2_MODEL_PYTHON` auf deren Interpreter gesetzt werden. Sonst verwendet
der Adapter den vorhandenen lokalen Modellinterpreter oder den GUI-Interpreter.
Ein Benutzerkonto oder fester Ordnername ist für den Checkout nicht erforderlich.

Die PDF-GUI-Anleitung ist die historische Fassung vom 5. Oktober; die
Markdown-Anleitung beschreibt die aktuelle Oberfläche. Lokale Optimierungen
schreiben weiterhin in das von Git ausgeschlossene `outputs_h2/`.
