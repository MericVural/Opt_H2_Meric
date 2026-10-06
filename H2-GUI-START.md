# H₂-Modell normal starten

Nach dem Klonen auf einem neuen Rechner einmal **H2-Modell einrichten.cmd**
ausführen; ausführliche Einrichtung: [GUI_UEBERGABE.md](GUI_UEBERGABE.md).

1. Den eigenen Projektordner öffnen. Auf Merics Rechner ist dies
   `C:\Forschungsarbeit\Opt_H2_Meric-h2`; andere Checkoutpfade sind unterstützt.
2. **H2-Modell starten.cmd** doppelt anklicken.
3. Der Browser öffnet <http://127.0.0.1:8510/>.
4. Fallstudie, Standort und **Analyse**, **Sensitivitätsanalyse**, **Vergleich**,
   **Quellen** oder **Export** wählen.

Gespeicherte Tageskurven: **Analyse → Gespeicherte Ergebnisse → Ergebnisreihe →
Darstellung → Tagesstrom: Solar, Wind und Netz**. Vorhandene Ergebnisse können
ohne Optimierung gelesen werden. Neue Berechnungen starten nur mit **Berechnen**
bzw. **Sensitivität berechnen**.

Die GUI verwendet `.venv-gui` im eigenen Projektordner. Auf dem bisherigen
Rechner bleibt die wissenschaftliche Anaconda-Umgebung unverändert. Der Start
benötigt Codex und den Chat-Arbeitsordner nicht. Ein vorhandener lokaler Server
wird wiederverwendet; das Schließen des Browsers beendet keine Modellaufträge.
Startprotokoll: `outputs_h2/gui_runtime/server.log`.

[Bedienungsanleitung](GUI_BEDIENUNGSANLEITUNG.md),
[Technische Einrichtung](GUI_README.md).
