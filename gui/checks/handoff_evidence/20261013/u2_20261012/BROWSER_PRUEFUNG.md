# U2 – Browserprüfung der installierten Forschungswerkstatt

Prüfdatum: 12. Oktober 2026. Geprüft wurde die aktive Streamlit-App unter **http://127.0.0.1:8510/** aus `C:\Forschungsarbeit\Opt_H2_Meric-h2\gui\app.py`, nicht der HTML-Entwurf und nicht der temporäre Vorschauport. Die Oberfläche trägt die Revision „U2 · 12.10.2026“.

## Im Browser geprüfte Bedienwege

1. **Einstieg und Navigation:** fünf Arbeitsbereiche, Forschungsfrage als Einstieg, Standort/Fallstudie und Jahresbezüge sichtbar. Die Einstellungen für Lieferprofil und Stromregeln sind einklappbar. Der Standard wertet gespeicherte Ergebnisse aus.
2. **Stromregeln:** Hamburg, D0, S0/S1/S2 zeigt 4,220 / 5,564 / 7,186 EUR/kg H₂, einen gemeinsamen Vergleichsvertrag und dateigebundene Prüfnachweise für 3/3 Fälle. Die beobachtete S2–S1-Differenz wird mit 1,622 EUR/kg bzw. 29,15 % ausgewiesen und fachlich eingeordnet.
3. **Emissionen:** zwei getrennte Intensitätsdiagramme; die gestrichelte native Produktreferenz liegt ausschließlich auf der regulatorischen Achse. Betriebliche Emissionen bleiben trotz regulatorisch null getrennt sichtbar. Die Einschränkung auf die elektrische Teilbilanz steht direkt am Diagramm.
4. **Nachfrage:** gespeicherte Mengen 50/75/100/125/150 % für D0 und S0/S1/S2. Die drei eigenen 100-%-Referenzen sind hervorgehoben. Die Oberfläche erläutert proportional steigende Jahreskosten und konstante LCOH im linearen Modell sowie die jeweils neu optimierte Anlagengröße.
5. **Tagesbetrieb eines Versuchspunkts:** `demand_050`, Hamburg, D0, S0 wird unmittelbar in „Analyse“ geöffnet. Der tatsächliche Fallbezug bleibt erhalten. Für den 02.01.2024 werden 24 Stunden in Europe/Berlin und die kumulativen Solar-, Wind- und Netzenergien dargestellt.
6. **Reale Downloads:** Grafikdaten der Nachfrage und Tagesdaten wurden über die sichtbaren Downloadknöpfe heruntergeladen. Der Datenabgleich prüft 15 Nachfragepunkte mit drei eigenen Basen sowie 24 Tageswerte gegen `hourly_operation.csv` des ausgewählten 50-%-Falls. Die Endwerte der kumulativen Reihen entsprechen den jeweiligen Tagessummen.

## Nachweise

- [Einstieg](01_analyse_einstieg.png)
- [Emissionsdarstellung](02_emissionen.png)
- [Nachfrage und Modellbefund](03_nachfrage.png)
- [Kumulative Tagesenergie](04_tagesenergie.png)
- [Szenarienergebnis](05_szenarien_ergebnis.png)
- [Heruntergeladene Nachfragepunkte](browser_quantity.csv)
- [Heruntergeladene Tageswerte](browser_daily.csv)
- [Maschineller Daten- und Installationsabgleich](browser_verification.json)

Die Bildschirmnachweise wurden im In-App-Browser aufgenommen. Der maschinelle Abgleich bestätigt zusätzlich die unveränderten 16 installierten Dateien gegenüber dem Übernahmebeleg und unveränderte native Modelldateien. Die Browserprüfung ergänzt die 107 bestandenen gezielten automatisierten Prüfungen; sie ersetzt keine breite Geräte-, Barrierefreiheits- oder Nutzerabnahme.

## Grenzen und nächste Arbeit

Es wurden ausschließlich vorhandene Resultate gelesen und lokale Nachweise gespeichert; keine neue Jahresoptimierung gestartet. Die 90-Fälle-Auftragsübergabe ist durch den automatisierten Test mit simulierter Auftragsverwaltung geprüft. Eine neue komplette Solverserie wurde nicht ausgeführt. Die bisher vorgesehenen Arbeitspakete U3 (Auftragszustände, Doppelstartschutz, Wiederaufnahme) und U4 (breitere Bedien-/Geräteabnahme und Übergabe) bleiben offen. Die App wurde anschließend auf den Einstieg „Analyse“ zurückgestellt.
