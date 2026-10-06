# Fallstudie Hamburg–Moorburg und Huelva–La Rábida

**Aktuelle vergleichende Untersuchung · Stand: 6. Oktober 2026.**

Schritt 18 ist methodisch abgeschlossen. Auf ausdrücklichen Nutzerwunsch ist
die aktive Zeitbasis jetzt **historisches 2024** mit allen **8.784 Stunden**.
**Schritte 19–22 sind umgesetzt:** tatsächliche Wetter-/Preisquellen 2024,
statische Betriebsreferenzen ebenfalls 2024, Länder-WACC und sechs vollständige
D0/D1/D2-Inputs. Jahreslieferung je Profil: 3.650.000 kg H2; Volljahrannualisierung 1.
WACC 2021 bleibt ausdrücklich ein Finanzierungsproxy; Geldbasis EUR 2023 und
normative Emissionswerte 2020 erfüllen andere Jahresrollen. Frühere 2025-Archive
bleiben erhalten. Ortsmonate sind durchgängig umgesetzt; **Schritt 23 mit sechs optimalen D0-Jahresfällen und 224/224 Exportprüfungen abgenommen**. **Schritt 24 abgeschlossen:** 60 neue optimale Jahresfälle (12 Nachfrage- und 48 ökonomische Varianten), 2240/2240 unabhängige Exportprüfungen; sechs unveränderte D0-Ergebnisse aus Schritt 23 wiederverwendet.

**Schritt 25 ist fachlich abgeschlossen:** Die EU-Ergebnisse sind mit Primärliteratur
verglichen und in einen [wissenschaftlichen Manuskriptentwurf](../manuskript/FORSCHUNGSARBEIT_ENTWURF.md)
überführt (Abschnitt 18b); formale Einreichung und Betreuungsfreigabe stehen aus.
Auf aktuellen Nutzerwunsch ist die Manuskriptarbeit zurückgestellt. Die abgeschlossene
Erweiterung untersuchte fünf H2-Jahresmengen für beide Standorte, alle drei
Profile und S0/S1/S2; ihr gesonderter Status steht in Abschnitt 24.

Allgemeine Gleichungen, RED-Abbildung und Grenzen:
[MODELL_UND_METHODIK.md](../MODELL_UND_METHODIK.md).
Verbindliche Reihenfolge: [FORSCHUNGSARBEITSPLAN.md](../FORSCHUNGSARBEITSPLAN.md).
Historischer Entwicklungsfall: [Namibia](FALLSTUDIE_NAMIBIA.md).

## 1. Rolle und Ziel

Nach dem Betreuergespräch vom 2. Oktober 2026 untersucht die Arbeit zwei
unterschiedliche europäische Küsten-/Hafenkontexte. Die Wasserstoffproduktion
bleibt die Hauptfrage. Das vorhandene Modell wird um konsistente historische
Stundenreihen, standortbezogene Finanzierung und zeitvariable Abnahme erweitert.

Die Fälle bilden **standardisierte hypothetische Anlagen** ab, keine vollständigen
Nachbildungen der realen Projekte. Kapazitäten werden optimiert; tatsächliche
Projektgrößen, Bauflächen, Anschlüsse und Genehmigungen werden nicht übernommen.
Beide Standorte werden unabhängig gerechnet; H2-Transport oder Stromverbund fehlen.

## 2. Forschungsbeitrag

Bei gleicher Modellstruktur, Technik und Jahreslieferung werden die Wirkungen
von erneuerbarem Ertrag, Day-Ahead-Preisen, Finanzierung und Lieferprofil untersucht.
S0→S1 ergänzt EE-Mengendeckung und die Zuordnung erzeugter Überschüsse; S1→S2 isoliert Monats- gegenüber Stundenkorrelation bei gleicher Allokationskonvention.
Der Vergleich zwischen Ländern verändert bewusst mehrere Standortbedingungen;
er ist keine Einzelfaktor-Kausalanalyse.

Der statische Betriebsfaktor bewertet den physischen Netzbezug mit einer dokumentierten nationalen Jahresreferenz.
Die regulatorische Bewertung bleibt davon getrennt. Eine neue betriebliche
CO2-Obergrenze oder ein CO2-Preis wurde nicht als Forschungsumfang beschlossen.

## 3. Standorte und räumliche Ebenen

| Eigenschaft | Hamburg–Moorburg | Huelva–La Rábida / Palos de la Frontera |
|---|---|---|
| Anlagenreferenz, Breite / Länge | 53,488000° / 9,949000° | 37,184329° / −6,894507° |
| Koordinatensystem | WGS84 | WGS84 |
| Herkunft | Eigener repräsentativer Landpunkt des ehemaligen Kraftwerksareals | Amtlicher Referenzpunkt des bestehenden Raffineriekomplexes PRTR 1482 |
| Land / Preisgebiet | DE / DE-LU | ES / ES |
| Betriebsfaktor-System | Deutsche nationale Nettoerzeugungsreferenz | Spanische nationale Referenz einschließlich Inseln, als Proxy für Huelva/Festland |
| Ortszeit | Europe/Berlin | Europe/Madrid |
| API-Wetterpunkt der geprüften Stichprobe | 53,5° / 10,0° | 37,25° / −7,0° |
| API-Höhe der Stichprobe | 10 m | 17 m |

Moorburg ist durch den [Hamburg Green Hydrogen Hub](https://hghh.eu/en) als
Wasserstoffstandort dokumentiert. Für Huelva belegen das
[PRTR-Register](https://prtr-es.miteco.gob.es/Informes/fichacomplejo.aspx?Id_Complejo=1316)
den bestehenden Anlagenpunkt und die
[Junta de Andalucía](https://www.juntadeandalucia.es/boja/2025/131/BOJA25-131-00001-8974-01_00322573.pdf)
den Wasserstoffprojektbezug. Keiner der Punkte wird als vermessener Standort
einer zukünftigen Elektrolyseanlage ausgegeben.

BKG-/IGN-Karten wurden in Schritt 18 geprüft und mit Manifest gespeichert.
Wetterzellen sind keine Anlagenkoordinaten. Der Namibia-1°-Rastermittelpunkt
wird für diese Hafenfälle nicht verwendet; Land/Preisgebiet werden explizit gesetzt.
Küstenlage führt nicht zu einer Offshore-Windannahme.

Preis ist gebotszonenbezogen, Faktor stromsystembezogen und WACC ein Länder-/
Technologieproxy. Eine präzise Koordinate macht diese Größen nicht pixelgenau.

## 4. Zeitbasis: tatsächliches historisches 2024

| Konvention | Festlegung |
|---|---|
| Untersuchungszeitraum | Lokales Kalenderjahr 2024, 01.01.00:00 bis 01.01.2025 00:00 |
| Modellauflösung | Eine Stunde; alle 8.784 Intervalle einschließlich 29. Februar |
| Interne Zeit | UTC; Intervallbeginn `[t,t+1 h)` |
| Erster Beginn, inklusive | 2023-12-31T23:00:00Z |
| Ende, exklusiv | 2024-12-31T23:00:00Z |
| Letzter Stundenbeginn | 2024-12-31T22:00:00Z |
| Nachfrage / aktive Monatszuordnung | Europe/Berlin bzw. Europe/Madrid |
| Jahresreferenz | `historical_calendar_year`, 8.784 Stunden; Volljahrfaktor 1 |
| Informationsannahme | Historischer Verlauf mit perfekter Voraussicht |

Sommerzeit beginnt am 31. März und endet am 27. Oktober 2024.
Die lokalen Tage enthalten 23 bzw. 25 Stunden; März hat 743, Oktober 745 und
Februar 696 Stunden. Die Quellen wurden für 2024 neu beschafft. Weder TMY
noch alte 2025-Zeilen werden positionsweise umbenannt; der Schalttag wird nicht gelöscht.

Die Annualisierung verwendet `H_Jahr/(N × Δt)`. Volles 2024 ergibt 1;
kurze EU-Softwaretests werden ausdrücklich auf 8.784 Stunden hochgerechnet.
Historische Namibia-/Legacy-Fälle behalten ihre 8.760-Stunden-Referenz.
Die Jahreslieferung bleibt 3.650.000 kg, statt durch 366 Tage auf 3.660.000 kg zu steigen.

**Schritt 22 umgesetzt:** Beide Solver, RED-Modul und unabhängiger Validator
verwenden die Ortsmonate. Erste/letzte UTC-Stunde gehören korrekt zum Januar/
Dezember 2024; es gibt zwölf lokale Monatsgruppen. Nachfragefenster verwenden
dieselbe Ortszeit. S2 unterscheidet jede physische UTC-Stunde, auch am Herbsttag. S2 ist ein Regelvergleich mit historischen 2024-Daten,
keine 2030-Prognose oder rückwirkende Projektzertifizierung.

### Jahresrollen und maximale Konsistenz

| Eingabe | Aktive Referenz | Bedeutung / Grenze |
|---|---|---|
| Wetter, Kalender, dynamische Marktpreise | 2024 | Tatsächliche zusammenpassende Stundenreihen |
| Statischer Betriebsfaktor und GEP/NEP | 2024 | Gleicher Jahresbezug; jährliche nationale Näherung |
| WACC | 2021, auf 2024 übertragen | Verbleibender zeitlicher Finanzierungsproxy |
| Technikkosten | Brandt-Publikation 2024, reale EUR 2023 | Gemeinsames Literaturpaket, keine lokalen 2024-Angebote |
| Geldmaßstab | EUR 2023 | Gleiche reale Maßeinheit für CAPEX/OPEX und deflationierte Preise |
| Regulatorische Länderwerte | Tabelle A, Datenjahr 2020 | Normative Rechenannahme mit Aktualisierungsvorbehalt |
| D0/D1/D2 | Ortskalender 2024 | Synthetische Pflichtlieferung, keine gemessene Nachfrage |

EUR 2023 ist eine Geldeinheit; sie verhindert nicht einen konsistenten historischen
2024-Vergleich. Ein älterer WACC ist dagegen eine tatsächliche zeitliche Näherung.
Die neue [Quellenprüfung](../outputs_h2/eu_case_studies/historical_2024/step19/parameter_consistency_review/PARAMETERKONSISTENZ_2024.md)
trennt diese Rollen und dokumentiert alternative 2024-Finanzierungsdaten.

### Unveränderte Entwurfs- und 2025-Historie

Die ursprünglichen 2023-Stichproben und 38 Entwurfsprüfungen bleiben unverändert.
Die zwischenzeitliche 2025-Basis bleibt unter [historical_2025](../outputs_h2/eu_case_studies/historical_2025/step19/).
Exakte vorherige Design-/Faktorkatalog-/MD-Snapshots stehen im
[Migrationsarchiv](../outputs_h2/eu_case_studies/historical_2024/step19/year_migration_20261003/).
Diese Prüfungen werden nicht als 2024-Abnahme ausgegeben.

## 5. Wetter und erneuerbare Erzeugung

Primärquelle ist **ECMWF ERA5, aufbereitet über die Open-Meteo Historical Weather API**.
Feste Optionen: `models=era5`, `cell_selection=land`, `wind_speed_unit=ms`, `timezone=UTC`.
Die API nutzt Verarbeitung und Höhenanpassung; ihre Ausgabe wird als verarbeitetes
ERA5 dokumentiert, nicht als unveränderte Rohreanalyse.
[Open-Meteo](https://open-meteo.com/en/docs/historical-weather-api),
[Copernicus/ECMWF](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels-timeseries?tab=download)

| Quellfeld | Ziel der bestehenden Profilberechnung | Einheit / Umrechnung |
|---|---|---|
| `temperature_2m` | `temp_air` | °C |
| `surface_pressure` | `pressure` | hPa × 100 → Pa |
| `wind_speed_10m` | `wind_speed` | m/s |
| `shortwave_radiation` | `ghi` | W/m² |
| `direct_normal_irradiance` | `dni` | W/m² |
| `diffuse_radiation` | `dhi` | W/m² |

Zeitvertrag: Strahlung am Quellzeitpunkt ist das Mittel der vorherigen Stunde.
Für Modellintervall `[t,t+1 h)` wird deshalb Strahlung am Quellzeitpunkt `t+1 h`
zugeordnet. Temperatur, Wind und Druck werden als Zeitpunktgrößen zwischen
Randbeobachtungen auf die Intervallmitte interpoliert. Die Sonnenposition wird
bei `t+30 min` berechnet. Eine pauschale Verschiebung der ganzen Tabelle ist unzulässig.

Die PV-/Windannahmen des vorhandenen Profilmoduls bleiben erhalten; Wind entspricht
Vestas V90/2000 mit 80 m Nabenhöhe und bestehender Hochrechnung aus 10-m-Wind.
ERA5 ist kein konkretes lokales Windgutachten. PVGIS kann als historische
Solargegenprüfung dienen; dessen TMY wird nicht als gleichzeitiges Wetter eingesetzt.

**Umgesetzt in Schritt 19:** Volljahrabruf mit Randbeobachtungen, strikter
Zeit-/Einheitenadapter und reale Profilberechnung mit dem bestehenden Technikpaket.
Je Standort liegen 8.784 Profilstunden ohne NaN vor; die API bestätigt die oben
stehenden Wetterzellen. Als Datenkontrolle ergeben sich PV-/Wind-Volllaststunden
von 1.127,24 / 1.959,64 für Hamburg und 1.846,30 / 1.284,89 für Huelva.
Dies sind modellierte Wetterprofile, keine gemessenen Anlagenjahreserträge
und keine H2-Optimierungsergebnisse. CSVs und Hashes stehen im Aufbereitungsbericht.

## 6. Dynamische Strompreise und Preisjahr

| Standort | Gewählte Quelle / Größe | Abgrenzung |
|---|---|---|
| Hamburg | SMARD Filter 4169, Day-Ahead DE-LU | Großhandelspreis, kein Endkundentarif |
| Huelva | Öffentliches REData, Spotindikator 600 | Spanien; PVPC-Indikator 1001 wird nicht verwendet |

[SMARD](https://www.smard.de/en/downloadcenter/download-market-data/),
[REData-Beispiel für 2024](https://apidatos.ree.es/es/datos/mercados/precios-mercados-tiempo-real?start_date=2024-01-01T00:00&end_date=2024-01-01T23:59&time_trunc=hour),
[OMIE-Marktdateien](https://www.omie.es/en/file-access-list?dir=+Day-ahead+market+hourly+prices+in+Spain&parents=%2FDay-ahead+Market%2F1.+Prices&realdir=marginalpdbc).
OMIE bleibt ursprüngliche Marktquelle und Gegenprüfungsmöglichkeit.

Negative Preise bleiben erhalten. Netzentgelte, Steuern/Abgaben, Beschaffungsmarge
und feste Leistungsentgelte sind im Basisvergleich ausgeschlossen; zusätzlicher
Arbeitspreisaufschlag 0 EUR/MWh. Das ist eine Kosten-Systemgrenze, kein Nachweis
einer tatsächlichen Kostenbefreiung. LCOH enthält hier vergleichende Großhandelskosten.

Der ursprüngliche 2023-Entwurf diskutierte gesondert die spanische Verbraucher-
Gasdeckelanpassung. Dies ist historische 2023-Abgrenzung und wird nicht ohne
Prüfung als konkreter fehlender 2024-Preisbestandteil übernommen.
[REE, Endpreisbestandteile 2023](https://www.sistemaelectrico-ree.es/en/2023/spanish-electricity-system/markets/average-final-price)

### Tatsächliche Quellenauflösung und reale Geldbasis

Die 2024-Antwort des REE-Spotindikators 600 liefert native 60-Minuten-Werte.
Der Adapter prüft die konkrete Auflösung und akzeptiert belegte 15-/60-Minuten-
Quellen. Viertelstunden werden gegebenenfalls dauergewichtet gemittelt.
Der 15-Minuten-Marktstart 2025 bleibt historische Information und wird nicht
auf die 2024-Daten übertragen. Die Quelloffsets erhalten doppelte Herbststunden.

Originalpreise bleiben nominale EUR 2024. Die genehmigte nationale HVPI-Deflation
nutzt Eurostat `prc_hicp_ainr`, Gesamtindex `TOTAL`, Jahresmittel `INX_A_AVG`.
Die archivierte aktuelle Antwort ergibt:

| Land | Index 2023 | Index 2024 | Multiplikator EUR 2024 → EUR 2023 |
|---|---:|---:|---:|
| DE | 95,41 | 97,79 | 0,975662133142448 |
| ES | 94,66 | 97,38 | 0,9720681864859314 |

`Preis_EUR2023(t) = Preis_nominal2024(t) × Index_2023 / Index_2024`.
Gemeinsame Kaufkraftbasis, keine Strompreisprognose oder WACC-Inflationskorrektur.
[Eurostat-Originalantwort](https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/prc_hicp_ainr?freq=A&unit=INX_A_AVG&coicop18=TOTAL&geo=DE&geo=ES&sinceTimePeriod=2023&untilTimePeriod=2024).
Eine Neubasierung des Index verändert die verwendeten Jahresverhältnisse nicht.
Die ±20-EUR-Sensitivität wird erst auf die EUR-2023-Reihe angewandt.

Beide Reihen besitzen exakt 8.784 Stunden. Nominale Jahresmittel:
DE 78,5120 / ES 63,0408 EUR_2024/MWh; reale Mittel:
DE 76,6012 / ES 61,2799 EUR_2023/MWh. Negative Stundenpreise:
**DE 457 / ES 247**. Das sind Stundenwerte, keine Zählung nativer Viertelstunden.
Die Stromkosten werden mit der tatsächlichen stündlichen Netzmenge nachgerechnet.

## 7. Statischer betrieblicher Länderfaktor – aktive Basis

**Nutzerentscheidung vom 03.10.2026:** Die betriebliche Basisrechnung verwendet
einen konstanten Jahresfaktor pro Land. Die ursprünglich gewünschte stündliche
Technologierekonstruktion wird als optionale Untersuchung mit offenen Nachweisen
aufbewahrt. Ihre fehlenden Kategorieparameter werden nicht mit null ersetzt.

### Gemeinsame Quelle und eigene Nennerumrechnung

Die [offizielle EEA-Länder-CSV](https://www.eea.europa.eu/en/analysis/indicators/greenhouse-gas-emission-intensity-of-1/greenhouse-gas-emission-intensity-of-electricity-generation/@@download/file)
enthält **2024 als frühe Schätzung**: Deutschland 291, Spanien 125 g CO2e/kWh.
Das entspricht numerisch 291 bzw. 125 kg CO2e/MWh **Bruttoerzeugung**.
Die Werte wurden exakt aus CSV-Zellen AI23/AI13 entnommen und gegen die
eingebetteten numerischen EEA-Diagrammdaten geprüft; keine grafische Ablesung.

Für die Netto-Erzeugungsreferenz führen wir eine eigene näherungsweise Umrechnung
mit [Eurostat nrg_ind_peh](https://ec.europa.eu/eurostat/databrowser/view/nrg_ind_peh/default/table?lang=en)
des Jahres 2024 durch:

\[
EF_{Land,net}^{Proxy}=EF_{EEA,gross}\frac{GEP_{Land,2024}}{NEP_{Land,2024}}.
\]

| Land | EEA-Bruttofaktor [kg CO2e/MWh] | GEP [GWh] | NEP [GWh] | Modellreferenz [kg CO2e/MWh] |
|---|---:|---:|---:|---:|
| DE | 291 | 514.009 | 490.978 | **304,7** |
| ES | 125 | 287.914,758 | 279.398,166 | **128,8** |

Ungerundete Rechenwerte im Katalog: DE 304,65034889546985,
ES 128,81023975654873. Die Dezimalstellen dienen der reproduzierbaren Rechnung;
sie sind keine zusätzliche Messgenauigkeit gegenüber den gerundeten EEA-Werten.
Die vier Gruppen Hauptproduzenten/Eigenerzeuger, jeweils Strom-only/KWK, summieren
sich exakt zum jeweiligen GEP-/NEP-TOTAL. EEA und Eurostat beziehen sich damit
auf kompatible Erzeugerumfänge. Die Eurostat-Energiebilanz wurde zusätzlich
gegen diese Bruttozellen geprüft. Anlageneigenbedarf und Verluste in Haupttransformatoren unterscheiden
Brutto- und Nettoerzeugung; eine Netzverlustkorrektur wird nicht damit behauptet.

**Datenrevision:** Der ursprüngliche EEA-Nenner und sein Revisionsstand wurden
nicht rekonstruiert. Die verwendeten Eurostat-Daten sind eine später archivierte
2024-Revision. Daher ist die Umrechnung eine eigene Nennernäherung und kein
veröffentlichter EEA-Nettofaktor. Pump-/Batterieausstoß bleibt entsprechend
dem veröffentlichten TOTAL enthalten; keine unbelegte Speicherbereinigung.

### Bilanzgrenze und verbleibende Unsicherheit

Die [ausführliche EEA-Methodik](https://www.eea.europa.eu/en/analysis/indicators/greenhouse-gas-emission-intensity-of-1)
umfasst nationale Erzeugung einschließlich geschätzter Eigenerzeuger-Emissionen;
KWK-Wärme wird bereits nach der EEA-Methode zugeordnet. Wir übernehmen die
veröffentlichten Faktoren und behaupten keine eigene Rekonstruktion dieses Inventars.
EEA setzt Kernkraft und Erneuerbare einschließlich Biomasse im Indikator auf null.
Diese Inventarkonvention ersetzt in der aktiven Basis die frühere JRC-Methode
mit separaten Biomasse-CH4/N2O-Ansätzen. Es werden keine fremden Faktoren addiert;
Null bedeutet hier keine vollständige Emissionsfreiheit oder Nachhaltigkeitsprüfung.

- Jahresreferenz und Modelljahr sind jetzt **beide 2024**; die frühere zeitliche Übertragung entfällt.
- **Spanien national einschließlich Inseln → Huelva/Festland**: räumlicher Proxy.
- Nationale Erzeugungsreferenz wird auf modellierten Netzimport angewendet;
  Import-/Exportflusszuordnung und Netzverluste fehlen.
- Keine Brennstoffvorketten, Anlagenherstellung, marginale oder gemessene Stundenintensität.
- Frühe EEA-Schätzung, gerundete Quelle und nicht belegter Revisionsgleichstand;
  keine publizierte numerische Unsicherheit, daher keine erfundenen Konfidenzintervalle.

Diese Annahmen bleiben in jeder betrieblichen Auswertung in den Quellenmetadaten
sichtbar. Die fehlenden Technologien der alten dynamischen Reihe sind keine
Eingabelücke des statischen Faktors und kein Prozentfehler dieses Faktors.

### Berechnung und ausführbare Eingaben

Für jedes Land gilt in allen Stunden derselbe Wert. Zum Beispiel werden 1 MWh
Netzbezug in Hamburg mit rund 304,7 kg CO2e bewertet, unabhängig von der Uhrzeit.
Der Netzbezug selbst wird weiterhin stündlich optimiert:

\[
GHG_{op,a}=EF_{Land,2024}^{Proxy}\sum_t E_{Netz,t},\qquad
I_{op}=GHG_{op,a}/Q_{H2,a}.
\]

Ohne CO2-Preis oder betriebliche Emissionsobergrenze ändert der Faktor nur die
Berichterstattung. Er beeinflusst das Kostenminimum nicht. Ein Vorteil zeitlich
emissionsarmer Netzstunden lässt sich mit dieser Basis nicht quantifizieren.

`prepare_eu_static_inputs.py` prüft Katalog, Quellenhashes, echte EEA-Zellen,
Eurostat-Zellen/Flags und GEP/NEP-Umrechnung vor jeder Freigabe. Beide Standorte
werden geprüft, bevor Ausgaben entstehen; bestehende Ausgaben werden nicht überschrieben.
Die sechs Dateien heißen `<site>_D0_static_factors.csv`, entsprechend D1/D2,
mit jeweiliger `.metadata.json`; sie liegen in der [2024-Freigabe](../outputs_h2/eu_case_studies/historical_2024/step19/static_factors_20261003/released_inputs/static_factor_release_report.json).
`explicit_separate_factors` enthält beide Quellen, tatsächliches Kalenderjahr,
Annualisierung, Profil und CSV-Hash. Wetter/Markt/Referenzjahr sind 2024;
Preise sind reale EUR 2023, Jahresnachfrage bleibt unverändert.

## 7a. Frühere dynamische Rekonstruktion – optionale offene Untersuchung

Die folgende Methode und die beschriebenen Erzeugungs-/Ausfallbefunde betreffen die archivierte **2025-Rekonstruktion**, nicht die neuen 2024-Preis-/Wetterinputs. Sie waren vor der statischen Entscheidung vorgesehen. Die
Quellen-/Rechenbelege bleiben historische Forschungsergebnisse; sie werden
in der aktuellen Basis nicht zur Berechnung der Betriebsfaktoren verwendet.

Ursprünglich vorgesehen war für beide Länder dieselbe stündliche, erzeugungsgewichtete
**durchschnittliche direkte CO2e-Intensität der inländischen Stromproduktion**:

\[
EF_{op,t}=\frac{\sum_k E_{k,t}\,f_k}{\sum_k E_{k,t}},
\]

mit Erzeugung \(E_{k,t}\) in MWh und Technologiefaktor \(f_k\) in kg CO2e/MWh.

Deutschland nutzt veröffentlichte Nettoerzeugung nach Technologie aus SMARD.
Spanien nutzt historische Fünfminuten-Leistungswerte des offiziellen REE-
Festlandportals. Nach Prüfung ihrer Intervallbedeutung werden MW-Werte über
`MW × 5/60 h` in Stunden-MWh integriert. REData-Tageserzeugung dient zur
Gegenprüfung; Tageswerte werden nicht in scheinbar gemessene Stunden interpoliert.
[REE-Historienbeispiel](https://demanda.ree.es/WSvisionaMovilesPeninsulaRest/resources/demandaGeneracionPeninsula?curva=DEMANDAAU&fecha=2025-01-01)

Die Bilanz enthält keine Import-/Exportflusszuordnung, Netzverluste,
Brennstoffvorketten oder Anlagenherstellung. Sie ist kein Verbrauchsmix am Hafen
und kein marginaler Emissionsfaktor. Speicherentladung/Pumpspeicher wird aus
primärer Erzeugung ausgeschlossen, um gespeicherten Strom nicht erneut als
neue emissionsfreie Erzeugung zu zählen. Ladung und Entladung sind getrennt zu prüfen.
Biogenes CO2 wird kenntlich gemacht; belegte CH4-/N2O-Emissionen werden berücksichtigt.

### Dynamische Technologiefaktoren: weiterhin keine Freigabe

Für beide Länder ist dieselbe Brennstoff-/Wirkungsgrad-/KWK-Methode vorgesehen.
Quellenkandidaten sind [JRC-Brennstofffaktoren](https://data.europa.eu/doi/10.2760/014585),
[Eurostat-Energiebilanzen](https://ec.europa.eu/eurostat/databrowser/view/nrg_bal_c/default/table?lang=en)
und belegte KWK-Allokation; die
[FfE-Methodik](https://www.ffe.de/wp-content/uploads/2025/02/GGC_Methodology-report_en.pdf)
dient als Methodenreferenz. Ein vollständiges Verbrauchsflussverfahren nach
Green Grid Compass wird damit nicht behauptet.

**OFFEN vor Freigabe:** vollständige numerische Faktortabelle, Quellenjahre,
Netto-/Bruttobasis, GWP-/Brennstoffkonvention, KWK-Allokation und Zuordnung
aller positiven Kategorien einschließlich Kohle, Gas, Biomasse, Abfall und Resten.
Fehlende Faktoren erhalten niemals automatisch null. Restkategorien benötigen
begründete Unsicherheitsgrenzen. Die geprüfte Eurostat-Antwort enthält noch keine 2025-Jahresbilanzen. Der Nutzer
hat am 3. Oktober 2026 **2024-Bilanzen als ausdrücklichen Proxy mit Unsicherheit**
zugelassen. Sie sind gehasht gesichert; dadurch ist noch keine Faktortabelle freigegeben.

Die Quellenprüfung zeigt fachliche Restfragen: Die FfE-Referenz beschreibt
Effizienzallokation von KWK; ihre gedruckte Umrechnungsformel ist gegenüber der
Definition des Emissionsanteils zu prüfen. Autoproduzenten-Brennstoff in Eurostat
ist bereits von selbst genutzter Wärme abgegrenzt und darf nicht ungeprüft nochmals
auf gesamte Nutzwärme aufgeteilt werden. Nationale Brutto-/Nettodaten liefern
keine eindeutige technologiespezifische Eigenbedarfszuordnung; spanische nationale
Faktoren entsprechen nicht automatisch dem Festlandspark. Aktuelle Brennstofflabels
werden benutzt: `C0220` ist Braunkohle, `C0210` subbituminöse Kohle.
Die JRC-, KWK-, Eurostat- und GHG-Protocol-Belege liegen im
[Faktorprüfbericht](../outputs_h2/eu_case_studies/historical_2025/step19/raw/factor_basis/FAKTORPRUEFUNG.md).

Der Quellcode belegt `gnhd` als Hydro; `hid` sowie `sol/aut` werden nicht zusätzlich
als primäre Erzeugung summiert. `turb/conb/bat/consBat` gehören zum Speicherbereich.
`bio` bezeichnet Biobrennstoff, `cogenResto` KWK und Abfall; `vap` Dampfturbinen.
Die Rohfelder bleiben erhalten; unbekannte Kategorien werden abgewiesen.

Das vollständige REE-Jahr hat 105.120 Fünfminutenwerte auf genau 8.760 Stunden.
Die Quelle beschreibt **Momentanleistung**, weshalb `Summe(MW × 5/60 h)`
als diagnostische Rechteckapproximation und nicht als abgerechnete Intervallenergie
gespeichert wird. Hydro-Abweichungen zur offiziell veröffentlichten REData-Tagesenergie betragen in fünf
Prüftagen −6,08 % bis +18,25 %; es erfolgt keine pauschale Skalierung.
Ab 11. Dezember 2025 erweitert REE die Abdeckung um geschätzte kleine
Eigenverbrauchsanlagen. Dieser Quellenbruch erfordert eine fachliche Bewertung.
[Amtlicher Frontendtext](https://demanda.ree.es/visiona/l10n/es_ES.js?v=4.1.1.2).
**Eine freigegebene betriebliche Stundenfaktorreihe liegt weiterhin nicht vor.**

Für den spanischen Ausfall vom 28. April 2025 zeigt das Volljahresarchiv **sieben
Fünfminutenwerte mit primärem Erzeugungsnenner null**, von 10:35 bis 11:05 UTC.
Es fehlen keine Zeitstempel; die publizierten Nullwerte bleiben sichtbar. Auch
nach der Stundenaggregation sind diese Quellsegmente nicht automatisch valide.
Ein Nenner null liefert keinen belegten Faktor null. **UNGEKLÄRT:** Quellbehandlung
und Netzverfügbarkeit im Modell; es wurde keine Ausfallrestriktion beschlossen
oder implementiert und keine Interpolation als Freigabe verwendet.
[ENTSO-E-Abschlussbericht](https://www.entsoe.eu/news/2026/03/20/entso-e-publishes-expert-panel-final-report-on-28-april-2025-blackout-in-spain-and-portugal/)

Die Betriebsrechnung lautet `Summe(Netzimport(t) × EF_op(t))`.
Sie dient zunächst der Ergebnisbewertung, ohne zusätzliche Kosten-/CO2-Restriktion.

## 8. Gesonderte regulatorische Emissionsbewertung

Für diagnostisch nicht erneuerbar zugeordnete Strommengen sind die veröffentlichten
Länderwerte aus **Anhang, Teil C, Tabelle A, Verordnung 2023/1185, Bezugsjahr 2020** festgelegt:

| Land | Tabellenwert | Umrechnung | Regulatorischer Faktor |
|---|---:|---|---:|
| Deutschland | 99,3 g CO2e/MJ Strom | × 3,6 | 357,48 kg CO2e/MWh |
| Spanien | 54,1 g CO2e/MJ Strom | × 3,6 | 194,76 kg CO2e/MWh |

Dies sind datierte regulatorische Standardwerte, keine gemessenen 2024-Betriebsfaktoren.
Der Absatz vor Tabelle A verlangt die Tabellenwerte bis neuere Daten für die
vorgeschriebene Intensitätsberechnung verfügbar sind. Aktualisierung und
Anwendbarkeit bleiben vor einer Zertifizierung zu prüfen. Die operative EEA-
Direktreferenz hat andere Vorketten-/Pumpgrenzen und ersetzt die Normwerte nicht automatisch. [Rechtsquelle](https://eur-lex.europa.eu/eli/reg_del/2023/1185/oj/eng)

Vollständig qualifiziert zugeordneter EE-Strom erhält im untersuchten Pfad Faktor null.
Der vorhandene THG-Teiltest verwendet **3,384 kg CO2e/kg H2**, entsprechend 28,2 g/MJ
bei 120 MJ/kg und 70 % Minderung. Die elektrische Teilbilanz ist kein vollständiger
Produktnachweis. Zusätzlichkeit, geografische Korrelation und exklusive Allokation
bleiben externe Szenarioannahmen. Die Niedrigpreis-Ausnahme bleibt deaktiviert.

**Während Schritt 19 umgesetzt:** Die neue Schnittstelle trennt die Faktoren.
`grid_emission_factor` bleibt betrieblich, `regulatory_grid_emission_factor`
ist regulatorisch. Beide Quellen benötigen den beschriebenen CSV-Vertrag.
Historische Eingaben verwenden ausdrücklich `legacy_shared_factor`.
Vollständige D0/D1/D2-Stundeninputs mit statischen Betriebsreferenzen sind freigegeben;
die eigene dynamische Faktorenreihe bleibt offen.

## 9. H2-Nachfrageprofile

In der **Basis** liefern beide Standorte **3.650.000 kg H2 pro Jahr**.
Die ergänzende Mengenvariation in Abschnitt 24 skaliert diese Jahresmenge
innerhalb desselben Lieferprofils; sie ändert die ursprünglichen Basisinputs nicht.
Die Profile sind synthetische Vergleichsannahmen, keine gemessene Hafen-/
Raffinerienachfrage und keine frei verschiebbare Abnahme.

| Profil im lokalen Kalender 2024 | Abnahmefenster | Aktive Stunden | Menge je aktiver Stunde (gerundet) |
|---|---|---:|---:|
| D0 | Jede Stunde | 8.784 | 415,528 kg/h |
| D1 | Täglich 08:00 ≤ Ortszeit < 20:00 | 4.392 | 831,056 kg/h |
| D2 | Montag–Freitag, 08:00 ≤ Ortszeit < 20:00 | 3.144 | 1.160,941 kg/h |

D2 hat 262 Wochentage; Feiertage werden nicht separat ausgeschlossen.
Die Jahresmenge wird durch die tatsächliche Zahl aktiver Stunden geteilt.
`eu_demand_profiles.py` prüft die vollständige UTC-Achse und wendet Ortsfenster
an; außerhalb des Fensters beträgt die Abnahme null. Generator, Metadaten,
Schalttag, Wochentage und DST-Grenzen sind implementiert und geprüft.
Die sechs freigegebenen Inputs haben identische exogene Wetter-/Preis-/Faktorreihen
je Standort, aber unterschiedliche Abnahmefenster. Die zwölf zusätzlichen D1/D2-
Jahreslösungen sind geprüft; ihre Kosten-, Produktions- und Speicherwirkung
wird in Abschnitt 18a mit der passenden D0-Basis verglichen.

## 10. WACC und Finanzierung

Gewählt sind **reale Nachsteuer-Länder-/Technologiebenchmarks mit Bezugsjahr 2021**
aus dem IRENA-Anhang 2023. Sie sind historische nationale Proxies, keine aktuellen
lokalen Finanzierungsangebote für diese Projekte. Kein weiterer Inflationsabzug
wird auf bereits reale Zinssätze angewandt.
[IRENA, Figure A1, PDF-Seiten 1–2](https://www.irena.org/-/media/Files/IRENA/Agency/Publication/2023/May/IRENA_Cost_of_financing_renewable_power_Appendix_2023.pdf)

| Investitionskomponente | Hamburg / DE | Huelva / ES |
|---|---:|---:|
| PV | 1,30 % | 3,60 % |
| Onshore-Wind | 1,30 % | 3,10 % |
| PEM | 3,30 % | 5,35 % |
| Kompressor | 3,30 % | 5,35 % |
| Druckspeicher | 3,30 % | 5,35 % |

Für H2-Komponenten gilt `r_H2 = (r_PV + r_Wind)/2 + 0,02`.
Der ungewichtete Mittelwert ist unsere vor der Optimierung festgelegte Konvention;
er hängt nicht vom optimierten Anlagenmix ab. Die zwei Prozentpunkte übertragen
die Literaturannahme höheren H2-Finanzierungsrisikos aus Brandt et al.
[Supplement, Tabellen 2–4, PDF-Seiten 15–17](https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41560-024-01511-z/MediaObjects/41560_2024_1511_MOESM1_ESM.pdf)

Nachsteuerbenchmarks dienen als effektive Annuitätszinssätze; Steuercashflows,
Abschreibungssteuerschilde und eine Investorenbewertung fehlen. Brandts Steuerkonvention
ist in den geprüften Tabellen nicht spezifiziert. Der übertragene Aufschlag ist
eine offengelegte Annahme, keine beobachtete Projektfinanzierung.

Die nominalen Steffen-/IRENA-2020-Werte wurden geprüft, aber nicht übernommen:
DE PV 2,16 %, Wind 2,44 %; ES PV 5,09 %, Wind 4,26 %.
Sie dürfen nicht direkt mit der gewählten realen Reihe vermischt werden.
Für 2024 wurden neue Primärquellen geprüft. IRENA *Renewable power generation
costs in 2024* zeigt Karten ohne exakte DE-/ES-Punktzellen und widersprüchliche
Real-/Nominalbeschriftung. EurObserv’ER Edition 2024 belegt Nachsteuerwerte
DE PV 3,9 / Wind 4,5 %, ES PV 4,1 / Wind 4,8 %, definiert aber den Real-/Nominalmaßstab
nicht ausreichend. Diese Alternativen sind archiviert und **nicht aktiviert**.
Die Steffen-2025-Datenbank endet für DE/ES im Beobachtungsjahr 2020;
Publikationsjahre werden nicht als Finanzierungsjahre ausgegeben.
Damit bleibt 2021→2024 ein offener zeitlicher Finanzierungsproxy; keine erfundene
Inflationskorrektur. Namibia 11 % wird nicht übertragen.
[Originalquellen und genaue Zellen](../outputs_h2/eu_case_studies/historical_2024/step19/parameter_consistency_review/PARAMETERKONSISTENZ_2024.md).

**In Schritt 20 umgesetzt:** `eu_site_configuration.py` und `--eu-site` in beiden
Runnern aktivieren diese fünf Raten ausdrücklich. Quellenjahr, Konvention und
Designhash werden gespeichert; S0/S1/S2 erhalten je Standort gleiche Raten.
Die allgemeinen Python-Defaults gelten weiter für Läufe ohne EU-Standortwahl.

## 11. Gemeinsames technisch-ökonomisches Paket

Das Brandt-Paket wird für beide EU-Fälle bewusst gleich gehalten.
Die Kostenbasis ist real EUR 2023; Werte sind Literaturparameter, keine lokalen Angebote.

| Komponente | CAPEX | Fixe OPEX pro Jahr | Lebensdauer |
|---|---:|---:|---:|
| PV | 921 EUR/kW | 15,10 EUR/kW | 30 Jahre |
| Onshore-Wind | 1.779,50 EUR/kW | 22,64 EUR/kW | 25 Jahre |
| PEM | 1.297 EUR/kW | 20,20 EUR/kW | 30 Jahre |
| Kompressor | 4.577,50 EUR/kW | 4 % CAPEX | 15 Jahre |
| Druckspeicher | 733,50 EUR/kg | 2 % CAPEX | 25 Jahre |

PEM-Verbrauch: 52,5 kWh/kg H2; Wasserbedarf: 14 kg/kg H2;
Wasserpreis: 3,74 EUR/m³, **kein belegter lokaler Wassertarif**.
Isentroper Verdichtungsbedarf: 1,287 kWh/kg; Wirkungsgrade 80 % / 90 %;
effektiver Strombedarf: 1,7875 kWh/kg; H2-Verlust vor Speicherung: 0,5 %.
Wind-variable OPEX: 9 EUR/MWh erzeugter Energie.
Druckannahmen: PEM 30 bar, Verdichtung 350 bar, Tank/Übergabe 300 bar.
Eine separate Ersatzkostenrechnung und zeitabhängiger Tankverlust fehlen.

Die Gemeinsamkeit betrifft Technik/Kosten, nicht Namibia-Wetter, Raster, Preise,
Faktoren oder WACC. Parametersicherheit wird durch ausgewählte Sensitivitäten geprüft.

## 12. Szenarien

Pro Standort: S0 Referenz, S1 monatlich, S2 stündlich.
Innerhalb eines Standorts sind Stundeninput, Nachfrageprofil, Technik und WACC
gleich. S0 ist die freie Referenz ohne zusätzliche EE-Mengendeckung und mit Erzeugung gleich Direktnutzung. S1/S2 erlauben zusätzlich die dokumentierte Zuordnung erzeugter EE-Mengen oberhalb der Direktnutzung; zwischen S1 und S2 wechselt ausschließlich die zeitliche Mengenkorrelation.
S1/S2 decken Elektrolyse **und** Verdichtung durch zugeordnete EE-Mengen.
S3 ist technisch implementiert, gehört aber nicht zum geplanten EU-Kernversuch.

Separate regulatorische Faktoren wurden während Schritt 19 technisch vorgezogen.
Ortsmonatkorrelation ist mit expliziter EU-Konfigurationszeitzone implementiert.
Beide Solver und RED-Prüfer verwenden dieselben Gruppen; der unabhängige Validator
rekonstruiert sie selbst. Ohne EU-Auswahl bleibt die Legacy-UTC-Konvention aktiv.
Gesicherte Quellen-/Zeitmetadaten erlauben die Nachrechnung; die vollständige
D0-Jahresergebnisabnahme ist in Schritt 23 erfolgt. Die Profil- und Kostensensitivitäten sind in Schritt 24 abgenommen (Abschnitt 18a).

## 13. Sensitivitäten und Versuchsanzahl

Einzelfaktorverfahren: pro Variante ein Einfluss, Vergleich mit passendem
Standort-/Szenariobasisfall. Nachfrageform und ökonomische Variation bleiben getrennt.

| Einfluss | Festgelegte Varianten | Festgehalten |
|---|---|---|
| Nachfrageform | D1 und D2 gegen D0 | Gleiche Jahresmenge, übrige Parameter |
| Strompreisniveau | −20 / +20 EUR_2023/MWh auf jede Stunde | Zeitlicher Verlauf der umgerechneten Reihe |
| Realer WACC | −1 / +1 Prozentpunkt für sämtliche Komponenten | Technologieabstände innerhalb des Landes |
| PEM-CAPEX | −25 / +25 % | Übrige Kosten/Technik |
| PEM-Strombedarf | −10 / +10 % | Verdichtungsparameter und übrige Technik |

WACC-Bänder: DE EE 0,30–2,30 %, DE H2 2,30–4,30 %;
ES PV 2,60–4,60 %, ES Wind 2,10–4,10 %, ES H2 4,35–6,35 %.
Die frühere offene Idee ±2 Prozentpunkte wurde zugunsten ±1 ersetzt, um
negative deutsche EE-Zinsen zu vermeiden. Bänder sind keine Konfidenzintervalle.

| Laufgruppe | Rechnung | Jahresläufe |
|---|---|---:|
| D0-Basis | 2 Standorte × 3 RED-Szenarien | 6 |
| Zusätzliche Profile | 2 Profile × 2 Standorte × 3 Szenarien | 12 |
| Ökonomische Varianten mit D0 | 4 Einflüsse × 2 Varianten × 2 Standorte × 3 Szenarien | 48 |
| Gesamter Kernumfang einschließlich wiederverwendeter D0-Basis | | **66 Ergebnisfälle** |

Kein vollständiges Faktorkombinationsraster. Optionale EE-/Speicher-CAPEX,
weitere Wetterjahre, Vergleich mit einheitlichem WACC und Restfaktor-Stressfälle
werden nur begründet ergänzt. Die später ausdrücklich beauftragte
Mengenvariation ist als gesonderte Ergänzung in Abschnitt 24 dokumentiert. **Schritt 24 abgeschlossen:** 60 neue optimale Jahresfälle (12 Nachfrage- und 48 ökonomische Varianten), 2240/2240 unabhängige Exportprüfungen; sechs unveränderte D0-Ergebnisse aus Schritt 23 wiederverwendet.
Schritt 24 führt keine sechs zusätzlichen Basissolves aus; die Gesamtzahl 66
bezeichnet sechs ursprüngliche und 60 neue Jahresergebnisse.

## 14. Datenpipeline

1. **Erledigt:** Aktiver Standort-/Zeitvertrag auf tatsächliches 2024 umgestellt.
2. **Erledigt:** Wetter, Preise und HVPI-Antworten mit URL, Abrufnachweis und Hash archiviert.
3. **Erledigt:** Zeit-/Einheitenadapter, Profile und nationale EUR-2023-Deflation.
4. **Erledigt:** Original-EEA-/Eurostat-Zellen 2024 geprüft; eigene statische Netto-Näherung.
5. **Erledigt:** Sechs vollständige D0/D1/D2-CSVs und getrennte Quellenverträge.
6. **Erledigt:** Länder-WACC ausdrücklich aktiviert; älteres Finanzierungsjahr dokumentiert.
7. **Erledigt:** Faktortrennung, historische Kalenderannualisierung und Ortsmonate
   in beiden Solvern, RED-Prüfer und unabhängigem Validator.
8. **Erledigt:** Sechs D0-Jahresbasisfälle, unabhängige Ergebnisabnahme und tabellarischer Standortvergleich.
9. **Erledigt:** Abgeleitete EU-Quellenverträge, OAT-Konfigurationsbindung und Wiederverwendung akzeptierter Basisläufe ohne erneuten Solve.
10. **Erledigt:** Zwölf D1/D2- und 48 ökonomische Jahresvarianten samt unabhängiger Abnahme.

Die Profile-/Preisaufbereitung allein bleibt bewusst `unreleased`, weil sie noch
keine Faktoren enthält. Erst `prepare_eu_static_inputs.py --profiles D0,D1,D2`
stellt den vollständigen freigegebenen Solverinput her. Die optionale historische
Technologie-/KWK-Rekonstruktion gehört nicht zur aktiven statischen Berechnung.

## 15. Historische Quellenprüfungen und frühere Freigabekriterien

Dieser Abschnitt bewahrt die 2023-/2025-Entwicklung. Frühere Kriterien,
Prüfzahlen und Lücken werden nicht als aktueller 2024-Stand ausgegeben.

### Gesicherte historische Schritt-18-Belege für 2023

Unter [design_checks/step18](../outputs_h2/eu_case_studies/design_checks/step18/)
liegen Rohstichproben, Karten, Quellbelege, Abruf-/Übertragungsmanifeste und
[verification_checks.json](../outputs_h2/eu_case_studies/design_checks/step18/verification_checks.json).

| Prüfung vom 02.10.2026 | Tatsächlicher Beleg | Aussagegrenze |
|---|---|---|
| ERA5, 21.06.2023 | Je 24 Stunden × sechs Felder, keine Lücken | Kein Volljahr und keine 2025-Abnahme |
| Preise, lokaler 01.01.2023 | Je 24 gleiche UTC-Stunden, DE mit negativen Preisen | Kein Endkundentarif/Volljahr |
| DE-Erzeugung | Zwölf Technologie-Stichproben mit je 24 Stunden | Faktoren noch offen |
| ES-Erzeugung | 288 Fünfminuten-Beobachtungen technisch abrufbar | Hydro-/Speicherabgleich offen |
| Finanzierungsquellen | IRENA Seiten 1–2 und Brandt Seiten 15–17 textuell/visuell geprüft | Historische Proxies, keine lokalen Angebote |
| Entwurfs-/Stichprobenprüfung | **38/38 bestanden** | Keine Solver-/Volljahresabnahme |

Die Übertragungsmanifeste nennen alte Dokumentpfade und deren damalige Hashes.
Sie bleiben unveränderte historische Belege, keine aktuelle Dokumentnavigation.
`outputs_h2/` ist lokal und von Git ausgeschlossen.

### Technische Machbarkeitsstichproben für 2025

Im vorausgehenden Chat wurden für Jahresanfang/-ende kleine Abrufe geprüft:
Wetter je Standort/Tag 24 Stunden × sechs Felder ohne fehlende Werte;
DE-Preis/Erzeugungs-Wochen abrufbar; ES-Spotantworten mit 96 Viertelstundenwerten
sowie 288 Fünfminuten-Erzeugungswerten pro geprüften Tag.
Dies stützt die Auswahl von 2025, belegt aber keine lückenlose Jahresabdeckung.
Diese früheren Stichproben bleiben historische Machbarkeitsbelege. In Schritt 19
wurden neu 67 Wetter-/Preisantworten und 948 Erzeugungsantworten erfolgreich
archiviert, dazu Indexantworten und Faktor-/Deflatorquellen. SHA-256, URLs und
Abrufzeiten liegen im separaten 2025-Archiv. Die vollständige Stundenaufbereitung
ersetzt weiterhin nicht die fachliche Faktor-/Erzeugungsfreigabe.

### Ursprüngliche Abnahme in Schritt 19 (unten ausdrücklich geändert)

- Exakt deckungsgleiche 8.760 UTC-Intervalle beider Ortskalender.
- Dokumentierte Quellintervalle, 15-/5-Minuten-Aggregation und Strahlungszuordnung.
- Keine NaN, Duplikate, stillen Jahresverschiebungen oder unbegründeten Füllwerte.
- Vollständige Faktoren für jede positive Kategorie; Speicher/Doppelsummen geklärt.
- Belegtes Preisjahr und Umrechnungsfaktor auf EUR 2023.
- Spanische Ausfall-/Nullwerte und Kalendergrenzen ausdrücklich geprüft.
- Quellen, Rohdaten, Raumebenen, Einheiten und Hashes in Metadaten nachvollziehbar.

## 16. Tatsächlicher Implementierungsstand

| Teil | Aktiver Stand 2024 | Offen |
|---|---|---|
| Wetter / Preise | Beide Standorte: 8.784 echte Stunden, reale EUR 2023 | Keine Lücke in freigegebenen Reihen |
| Betriebliche Referenz | Statische Jahresquelle 2024, Quellenzellen und Eigenumrechnung geprüft | Dokumentierte Raum-/Nenner-/Revisionsgrenzen |
| Regulatorischer Faktor | Separate normative Quelle und CSV-Vertrag | Zertifizierungs-/Aktualisierungsprüfung außerhalb des Teilmodells |
| WACC | Ausgewählte reale 2021-Raten aktiv | Zeitliche Übertragung auf 2024; vergleichbare neue Rate nicht freigegeben |
| D0/D1/D2 | Alle sechs Volljahresinputs; sechs D0- und zwölf D1/D2-Szenarien geliefert und validiert | Synthetische Lieferannahmen in Abschnitt 18b und Manuskript diskutiert |
| Annualisierung | Alle 66 Ergebnisfälle: 8.784 Stunden, Faktor 1, gleiche Jahreslieferung | Keine neue Jahreskonvention |
| Monatsbildung | Zwölf Europe/Berlin- bzw. Europe/Madrid-Gruppen in den geprüften S1-Lösungen | Keine offene Kalenderprüfung der 66 Fälle |
| Eigene dynamische Faktoren | Alte 2025-Audits bleiben optional | Vollständige Kategorie-/KWK-Punktwerte |

583 Modell-/Datentests und 6 Unterprüfungen bestanden. Die [Volljahresprüfung](../outputs_h2/eu_case_studies/historical_2024/step19/validation/full_year_input_preflight.json)
bestätigt alle sechs echten Inputs einschließlich unveränderter exogener Reihen,
Schalttag, Quellenbindung und 3.650.000 kg H2 pro Profil.
Die nachfolgenden sechs tatsächlichen D0-Jahreslösungen bestehen zusätzlich
**224/224 Exportprüfungen** und einen getrennten **275/275 Quellen-/Ergebnisaudit**.
Der Audit prüft 70 archivierte Rohquellenbelege, rekonstruierte Annuitäten,
Strom-/Wasserkosten und Emissionen. Die größte separat nachgerechnete jährliche
Kostenabweichung beträgt rund 0,000004642 EUR bei unveränderter Toleranz 0,05 EUR.
Solver-Optimalität ist durch Originalprotokolle belegt; diese Nachrechnung
ist kein zweiter unabhängiger Optimallösungslauf.
[Zusätzlicher Audit](../outputs_h2/eu_case_studies/historical_2024/step23/base_cases_20261004/scientific_review/STEP23_WISSENSCHAFTLICHE_ERGEBNISPRUEFUNG.md).


### Historische wissenschaftliche Fortführung im 2025-Archiv vor der statischen Entscheidung

Der Nutzer bestätigt die Empfehlung: historisches 2025 beibehalten, den genehmigten
2024-Proxy nutzen, eine belegte KWK-Näherung entwickeln und deren Aussagegrenzen
gesondert prüfen. Die frühere offene Frage nach Zulässigkeit dieser Näherung ist
damit entschieden. Die numerische Datenfreigabe folgt daraus nicht automatisch.

**Faktorenaudit:** `eu_emission_factor_audit.py` ist offline reproduzierbar. Es prüft
die unveränderten Eurostat-/JRC-Quellen, NCV-Basis und Quellenzellen, trennt
Aggregate und berechnet bedingte Netto-/KWK-Szenarien. 117 positive, nicht überlappende Bilanzdatensätze geprüft; 51 überlappende Aggregate gesondert ausgeschlossen. Der Audit enthält 54 Strom-only-Berechnungen, 13 belegte nicht brennbare Erzeugungsfaktoren, 15 MAPCHP- und 31 APCHP-Szenarien. Vier Bilanzdatensätze sind nicht zugeordnet; drei KWK-Biomasse-Datensätze besitzen mangels Brennstoff-Untergruppenmix nur einen Szenariobereich ohne Punkt.
Das Referenzszenario verwendet die ausdrücklich deklarierte Baujahrkonvention
2016-2023 und Dampf mit Kondensatrückführung aus den archivierten EU-Tabellen.
Andere Referenzkonventionen und Brutto-/Netto-Allokationsvarianten dienen der
methodischen Sensitivität. Unbekannte tatsächliche Baujahre, Wärmeformen und
die Referenz-Strombilanzgrenze werden damit nicht behauptet. APCHP ist eine
Näherung des gemeldeten Teilprozesses; verkaufte Wärme bleibt berücksichtigt.

**Spanien-Volljahresvergleich:** 365 Tage und 105.120 Fünfminutenwerte geprüft. Die diagnostische jährliche Differenz zur offiziellen Tagesenergie beträgt für Wind -3,17 %, für Hydro -1,03 %, für PV -0,24 % und für Kohle -7,07 %. Das belegt unterschiedliche Quellenwerte, keine identische Bilanzabdeckung.
Die REData-Tageswerte werden als offiziell veröffentlichte Energiequelle bezeichnet;
eine identische Netto-/Brutto-, Mess- oder Abrechnungsgrenze zur Momentanleistung
ist nicht belegt. Die Abweichungen sind Quellenvergleiche, keine vollständigen
Fehler- oder Konfidenzintervalle. Die Daten wurden nicht automatisch skaliert.
Positive `bio` und `cogenResto` benötigen weiterhin eine Aufteilung auf die
offiziellen Erzeugungskategorien. `vap` ist ab Juli positiv: Der REE-Bericht und
EDP/BOE-Belege erklären die Umstellung Aboño II von Kohle auf Erdgas plus
Stahlwerksgase. Der tatsächliche Brennstoff-Energiemix 2025 ist dadurch noch
nicht quantifiziert. Eine 38-Prozent-Angabe im Genehmigungsszenario ist kein
nachgewiesenes Jahres-Brennstoffgewicht.

**Korrektur des früheren Befunds:** Die offizielle Quellenhilfe bezeichnet
ausdrücklich die gelbe Echtzeit-Nachfragekurve ab 28.04.2025, 12:33 Ortszeit
(10:33 UTC), bis zum 29.04. als geschätzt. Sie beweist keine pauschale Schätzung
aller Technologie-Erzeugungswerte. Die genaue Endzeit ist dort nicht angegeben.
Sieben Proben haben einen Nullnenner, aber keine der 8.760 Stunden. Zähler und
Nenner werden für einen bedingten Stundenfaktor zuerst aggregiert; keine Null
oder Interpolation wird ergänzt. Der minimale Stundennenner beträgt 86,92 MWh.
Eine nationale Quellenangabe beweist keine Huelva-Netzverfügbarkeit. Der
Abdeckungsbruch vom 11.12. bleibt gesondert ausgewiesen.

**Modellschnittstelle:** Betriebliche und regulatorische Faktoren sind in beiden Solverpfaden, Einzel- und Szenarienrunner sowie unabhängigem Validator technisch getrennt. Der getrennte Modus verlangt zwei dokumentierte Quellen und einen an die CSV gebundenen SHA-256-Vertrag. Historische Eingaben bleiben ausdrücklich als Legacy-Modus nutzbar.
`grid_emission_factor` bleibt betrieblich; `regulatory_grid_emission_factor`
erhält eigene Quellen mit Einheit `kg_CO2e/MWh`, Bezugsjahr und Raumebene.
Der Quellenvertrag ist an die konkreten CSV-Bytes gebunden. Der zusätzlich
implementierte Modus `regulatory_only` verlangt nur eine regulatorische Quelle;
die betriebliche Eingabespalte fehlt und die operative Auswertung ist `null`/
`not_evaluated`. Ohne ausdrückliche Moduswahl bleibt die komplette Faktorprüfung. **Im damaligen historischen Stand** wurden Sensitivitätsläufe mit dem
neuen Vertrag zurückgewiesen. Schritt 24 erweitert diesen Weg um explizite
abgeleitete CSV-Quellenverträge; die aktive 2024-Rechnung verwendet `complete`.

**Prüfung:** 332 automatisierte Tests und sechs zusätzliche Unterprüfungen bestanden. Es wurden keine EU-Jahresfälle optimiert.
Die vollständige betriebliche Faktor-/Quellenfreigabe bleibt offen. Kosten-/
Regulatorik-Inputs sind nach der späteren Nutzerentscheidung separat abgenommen. Die [PDF-Erklärung](../output/pdf/Schritt_19_Wissenschaftlicher_Modellausbau.pdf)
stellt Rechenweg, Annahmen und nächste Freigabeschritte für die Nachvollziehbarkeit dar.
Neue Einzelnachweise stehen unter [followup_20261003](../outputs_h2/eu_case_studies/historical_2025/step19/followup_20261003/).

Reproduktion der neuen Offline-Audits nach Quellenbeschaffung:

```powershell
python eu_emission_factor_audit.py --factor-basis outputs_h2/eu_case_studies/historical_2025/step19/raw/factor_basis --output-dir outputs_h2/eu_case_studies/historical_2025/step19/factor_reproduction
python audit_eu_generation_quality.py --raw-power-root outputs_h2/eu_case_studies/historical_2025/step19/raw --output outputs_h2/eu_case_studies/historical_2025/step19/followup_20261003/spain
```

Der zweite Befehl verwendet das bereits geprüfte neue Roharchiv in seinem
Ausgabeordner. Für einen neuen Ordner ist zuerst `--acquire` erforderlich;
Primärquellen, Abrufe und Hashes werden erneut archiviert. Quellenjahre und
abgeleitete Größen bleiben in beiden Berichten ausdrücklich unterschieden.

## 17. Abgenommene D0-Jahresergebnisse 2024

**Schritt 23 abgeschlossen am 04.10.2026.** Alle sechs Fälle sind mit
SciPy 1.17.1 mit HiGHS 1.12.0 optimal gelöst. Je Fall: 8.784 physische Stunden,
Annualisierungsfaktor 1 und vollständig gelieferte 3.650.000 kg H2.
Die Zahlen stammen aus den tatsächlichen gespeicherten Jahreslösungen.
Geldwerte sind reale EUR 2023; der datierte WACC-2021-Finanzierungsproxy bleibt aktiv.

| Standort | Fall | LCOH [EUR 2023/kg H2] | Mehrkosten gegenüber S0 | Netzbezug [GWh/a] | Betriebliche Referenz [kg CO2e/kg H2] | Regulatorische elektrische Teilintensität [kg CO2e/kg H2] |
|---|---|---:|---:|---:|---:|---:|
| Hamburg–Moorburg | S0 | 4,2203 | 0,00 % | 199,145 | 16,622 | 19,504 |
| Hamburg–Moorburg | S1 | 5,5641 | 31,84 % | 44,869 | 3,745 | 0,000 |
| Hamburg–Moorburg | S2 | 7,1859 | 70,27 % | 24,542 | 2,048 | 0,000 |
| Huelva–La Rábida | S0 | 3,8886 | 0,00 % | 137,882 | 4,866 | 7,357 |
| Huelva–La Rábida | S1 | 4,8640 | 25,08 % | 69,566 | 2,455 | 0,000 |
| Huelva–La Rábida | S2 | 6,4696 | 66,37 % | 40,642 | 1,434 | 0,000 |

| Standort | Fall | PV [MW] | Wind [MW] | PEM [MW] | Kompressor [MW] | H2-Speicher [t] |
|---|---|---:|---:|---:|---:|---:|
| Hamburg–Moorburg | S0 | 0,000 | 0,000 | 43,131 | 1,469 | 11,063 |
| Hamburg–Moorburg | S1 | 84,902 | 76,448 | 38,655 | 1,316 | 15,641 |
| Hamburg–Moorburg | S2 | 91,145 | 73,653 | 49,664 | 1,691 | 126,537 |
| Huelva–La Rábida | S0 | 43,467 | 0,000 | 33,149 | 1,129 | 6,116 |
| Huelva–La Rábida | S1 | 138,633 | 0,000 | 48,088 | 1,637 | 9,450 |
| Huelva–La Rábida | S2 | 151,032 | 10,435 | 75,783 | 2,580 | 34,000 |


Die betriebliche Spalte ist physischer Netzbezug mal statischer nationaler
Erzeugungsreferenz 2024, dividiert durch gelieferte H2-Masse. Die regulatorische
Spalte umfasst nur die modellierte elektrische Teilintensität. Sie ist kein
vollständiger Produkt-Fußabdruck. Kapazitäten sind kontinuierliche nutzbare
Modellgrößen, keine fertig ausgelegten Anlagen oder Behälter.

Originale: [Hamburg](../outputs_h2/eu_case_studies/historical_2024/step23/base_cases_20261004/runs/hamburg_moorburg/D0/scenario_comparison.csv),
[Huelva](../outputs_h2/eu_case_studies/historical_2024/step23/base_cases_20261004/runs/huelva_la_rabida/D0/scenario_comparison.csv),
[gemeinsame Ergebnistabelle](../outputs_h2/eu_case_studies/historical_2024/step23/base_cases_20261004/results/eu_D0_base_cases.csv).

![D0-LCOH-Vergleich beider Standorte 2024](../outputs_h2/eu_case_studies/historical_2024/step23/base_cases_20261004/results/eu_D0_lcoh_comparison.png)

Alle folgenden Darstellungen betreffen D0, historisches 2024 und 3,65 Mio. kg
Jahreslieferung; Kosten in realen EUR 2023. Der [Figurenindex](../outputs_h2/eu_case_studies/historical_2024/step23/base_cases_20261004/results/FIGUREN_UND_GRENZEN.md)
enthält Auslegung, Kostenkomponenten und Betrieb beider Standorte mit ihren Quellenhashes.
Die generische RED-/Emissionsgrafik wurde für diesen EU-Bericht durch eine
getrennte Darstellung der beiden Bilanzgrenzen ersetzt.

![Getrennte betriebliche Referenz und regulatorische elektrische Teilbilanz](../outputs_h2/eu_case_studies/historical_2024/step23/base_cases_20261004/results/eu_D0_emission_intensities.png)

## 18. Interpretation der Basisfälle

An beiden Standorten gilt die beobachtete Kostenordnung **S0 ≤ S1 ≤ S2**.
Gegenüber S0 steigen die LCOH in Hamburg um 31,84 % / 70,27 %, in Huelva
um 25,08 % / 66,37 %. S0→S1 ergänzt EE-Mengendeckung und erlaubt dabei die
Mengenallokation erzeugter Überschüsse. S1→S2 vergleicht monatliche mit stündlicher
Deckung unter derselben Allokationskonvention. Daher wird der erste Unterschied
nicht allein als isolierter Monats-/Stunden-Effekt bezeichnet.

Huelva ist in allen drei festgelegten Basisfällen günstiger. Wetter, Marktpreise
und Finanzierung unterscheiden sich gleichzeitig; die Tabelle weist keinem
einzelnen Einfluss einen kausalen Kostenanteil zu. Die Robustheit gegenüber
Nachfrageform und ökonomischen Parametern wird durch die OAT-Ergebnisse in Abschnitt 18a eingegrenzt; eine kausale Zerlegung der Standortdifferenz folgt daraus nicht.

Hamburg S0 besitzt tatsächlich null PV und Wind. Dies ist das optimale
Modellresultat und kein fehlender Profileintrag. Der H2-Speicher erlaubt flexible
Produktion bei fester stündlicher Lieferung. Der tatsächlich bezugsgewichtete
Strompreis beträgt 49,645 EUR/MWh gegenüber 76,601 EUR/MWh ungewichtetem
Jahresmittel; rund 20.381,911 MWh werden bei negativen Preisen bezogen.
Diese überprüften Größen belegen zeitlich selektiven Netzbetrieb in der
gewählten Großhandelskonfiguration mit perfekter historischer Voraussicht.
Sie begründen keine allgemeine Empfehlung für ein reales Projekt.

Der H2-Speicher wächst von S1 zu S2 in Hamburg von 15,641 auf 126,537 t,
in Huelva von 9,450 auf 34,000 t. Stundenkorrelation geht hier mit größerer
PEM-Leistung und mehr H2-Speicherung einher. Es handelt sich um Resultate
dieser historischen Profile und Annahmen, keinen universellen Standortbedarf.
Die S2-Netzstromkosten sind aufgrund der bewahrten negativen Stundenpreise
in beiden Fällen negativ (Hamburg rund −261.348, Huelva −7.466 EUR/a).
Das ist der nachgerechnete Importkostenposten, keine Exportvergütung.

**Regulatorische Null bedeutet keine physische Emissionsfreiheit.** S1/S2
rechnen die erzeugten Mengen `pv_generation + wind_generation` einschließlich
des nicht direkt verbrauchten `renewable_surplus` an. Verfügbares, aber nicht
erzeugtes `curtailment` wird nicht angerechnet. S1 hat 1.317 Hamburger bzw.
1.488 Huelva-Stunden mit stündlicher EE-Mengenlücke; die Monatsbilanz gleicht
diese aus. S2 erfüllt jede physische Stundenmengendeckung, besitzt aber ebenfalls
Netzimport, weil erzeugte EE-Mengen oberhalb der Direktnutzung zugeordnet werden.

Dadurch ist die regulatorische elektrische Teilintensität für S1/S2 null,
während physischer Netzbezug und betriebliche Referenzemissionen positiv bleiben.
EE-Eignung und exklusive Allokation sind externe Voraussetzungen. Reale
Einspeisung, Abnehmer, Vertragsallokation und Vermeidung einer Doppelzählung
sind damit nicht nachgewiesen. Exportgrenzen, Exporterlöse und zusätzliche
PPA-/Netzkosten fehlen im bestehenden Modell. Dies ist die bereits dokumentierte
Allokationskonvention, keine neue Änderung in Schritt 23 und kein vollständiger
RFNBO-Zertifizierungsnachweis oder vollständige LCA.

## 18a. Abgenommene Nachfrage- und Kostensensitivitäten – Schritt 24

**Schritt 24 abgeschlossen:** 60 neue optimale Jahresfälle (12 Nachfrage- und 48 ökonomische Varianten), 2240/2240 unabhängige Exportprüfungen; sechs unveränderte D0-Ergebnisse aus Schritt 23 wiederverwendet.
Alle 66 Ergebnisfälle enthalten 8.784 Stunden, Annualisierungsfaktor 1 und
3.650.000 kg gelieferte H2-Jahresmenge. Wetter/Markt und statische Betriebsreferenz
betreffen historisches 2024; Kosten sind reale EUR 2023, Finanzierung behält
den dokumentierten realen 2021-Proxy. S3 gehört nicht zu diesem Versuch.

### Nachfrage bei fester Jahresmenge

LCOH in EUR 2023/kg H2; Änderungen beziehen sich auf den passenden D0-Basisfall
**derselben Standort-/Szenariokombination**. D1 gilt täglich, D2 Montag–Freitag,
jeweils 08:00 ≤ Ortszeit < 20:00; Feiertage werden nicht separat ausgeschlossen.

| Standort | Profil | S0 LCOH | S1 LCOH | S2 LCOH | S0 Änderung | S1 Änderung | S2 Änderung |
|---|---|---:|---:|---:|---:|---:|---:|
| Hamburg | D0 | 4,2203 | 5,5641 | 7,1859 | 0,00 % | 0,00 % | 0,00 % |
| Hamburg | D1 | 4,2456 | 5,5777 | 7,2083 | 0,60 % | 0,25 % | 0,31 % |
| Hamburg | D2 | 4,4736 | 5,7700 | 7,4225 | 6,00 % | 3,70 % | 3,29 % |
| Huelva | D0 | 3,8886 | 4,8640 | 6,4696 | 0,00 % | 0,00 % | 0,00 % |
| Huelva | D1 | 3,9075 | 4,8415 | 6,4080 | 0,49 % | -0,46 % | -0,95 % |
| Huelva | D2 | 4,1809 | 5,0930 | 6,8340 | 7,52 % | 4,71 % | 5,63 % |

Das Tagesfenster D1 verändert die LCOH hier nur um -0,95 % bis +0,60 %. In Huelva sinken die Kosten bei S1/S2 leicht; in Hamburg steigen sie in allen drei Szenarien leicht. D2 erhöht die Kosten in allen sechs Standort-/Szenariokombinationen um +3,29 % bis +7,52 %. Die tatsächliche Auslegungsantwort hängt vom Szenario ab: Huelva S2 benötigt bei D1 30,752 statt 34,000 t H2-Speicher, bei D2 52,017 t. Die zugehörige PEM-Leistung beträgt 75,806 / 75,045 MW gegenüber 75,783 MW bei D0. Diese Ergebnisse belegen keine allgemeine monotone Kapazitätsregel für engere Abnahmefenster.
Die Lieferung bleibt vollständig, während Produktion und zyklische Speicherung
auf das vorgegebene Abnahmefenster reagieren. Ein engeres Fenster erzwingt keine
gleich große prozentuale Kostenänderung in jedem Szenario. Die H2-Abnahme wird
nicht optimiert; ihre Fenster sind synthetische Vergleichsannahmen.

![Nachfrage-LCOH bei gleicher Jahreslieferung](../outputs_h2/eu_case_studies/historical_2024/step24/sensitivities_20261004/results/eu_demand_lcoh.png)

![Nachfrageabhängige PEM-Leistung und H2-Speicherung](../outputs_h2/eu_case_studies/historical_2024/step24/sensitivities_20261004/results/eu_demand_storage_pem.png)

### Ökonomische Einzelfaktorvarianten mit D0

Die 16 Tabellenzeilen enthalten je drei Szenarien, also 48 neue Jahreslösungen.
Preisoffsets werden auf jede reale historische Stundenpreiszahl addiert;
Preisabstände bleiben erhalten, ohne Nullkappung. Vorzeichenwechsel einzelner
Stunden durch die additive Verschiebung sind zulässig.
Die WACC-Verschiebung folgt erst nach der EU-Standortwahl und betrifft alle fünf
Raten bei erhaltenen Technologieabständen. Die PEM-Faktoren verändern nur CAPEX
beziehungsweise spezifischen Strombedarf; fixe PEM-OPEX, Kompressorwirkungsgrade,
Verdichtungsparameter und H2-Verlustparameter bleiben unverändert. Der aus dem
PEM-Strombedarf abgeleitete LHV-Wirkungsgrad ändert sich mit diesem Skalar;
er ist keine zweite unabhängig gesetzte Intervention. Bänder sind OAT-Annahmen,
keine Prognosen oder Konfidenzintervalle. LCOH in EUR 2023/kg H2; Änderungen gegen das zugehörige D0.

| Standort | Einfluss | Stufe | S0 LCOH | S1 LCOH | S2 LCOH | S0 Änderung | S1 Änderung | S2 Änderung |
|---|---|---|---:|---:|---:|---:|---:|---:|
| Hamburg | Preisoffset | -20 EUR/MWh | 3,1291 | 5,2414 | 6,9663 | -25,86 % | -5,80 % | -3,06 % |
| Hamburg | Preisoffset | +20 EUR/MWh | 4,9703 | 5,7245 | 7,2279 | 17,77 % | 2,88 % | 0,58 % |
| Hamburg | WACC-Verschiebung | -1 pp | 4,0586 | 5,1174 | 6,5710 | -3,83 % | -8,03 % | -8,56 % |
| Hamburg | WACC-Verschiebung | +1 pp | 4,3469 | 6,0373 | 7,8437 | 3,00 % | 8,51 % | 9,15 % |
| Hamburg | PEM-CAPEX | ×0,75 | 4,0019 | 5,3787 | 6,9494 | -5,17 % | -3,33 % | -3,29 % |
| Hamburg | PEM-CAPEX | ×1,25 | 4,4121 | 5,7421 | 7,4176 | 4,55 % | 3,20 % | 3,23 % |
| Hamburg | PEM-Strombedarf | ×0,90 | 3,8517 | 5,0705 | 6,7120 | -8,73 % | -8,87 % | -6,59 % |
| Hamburg | PEM-Strombedarf | ×1,10 | 4,5862 | 6,0547 | 7,6578 | 8,67 % | 8,82 % | 6,57 % |
| Huelva | Preisoffset | -20 EUR/MWh | 2,8532 | 4,3199 | 6,0093 | -26,63 % | -11,19 % | -7,12 % |
| Huelva | Preisoffset | +20 EUR/MWh | 4,4516 | 5,0330 | 6,4716 | 14,48 % | 3,47 % | 0,03 % |
| Huelva | WACC-Verschiebung | -1 pp | 3,7004 | 4,4777 | 5,9175 | -4,84 % | -7,94 % | -8,53 % |
| Huelva | WACC-Verschiebung | +1 pp | 4,0498 | 5,2685 | 7,0523 | 4,15 % | 8,32 % | 9,01 % |
| Huelva | PEM-CAPEX | ×0,75 | 3,6781 | 4,5686 | 6,0088 | -5,41 % | -6,07 % | -7,12 % |
| Huelva | PEM-CAPEX | ×1,25 | 4,0794 | 5,1439 | 6,9223 | 4,91 % | 5,75 % | 7,00 % |
| Huelva | PEM-Strombedarf | ×0,90 | 3,5436 | 4,4380 | 5,9467 | -8,87 % | -8,76 % | -8,08 % |
| Huelva | PEM-Strombedarf | ×1,10 | 4,2320 | 5,2884 | 6,9923 | 8,83 % | 8,73 % | 8,08 % |

Über beide Standorte und alle drei Szenarien reichen die beobachteten Änderungen
gegen D0 innerhalb der jeweiligen Bänder wie folgt: Preisoffset: -26,63 % bis +17,77 %; WACC-Verschiebung: -8,56 % bis +9,15 %; PEM-CAPEX: -7,12 % bis +7,00 %; PEM-Strombedarf: -8,87 % bis +8,83 %.
Diese Spannweiten gehören zu unterschiedlich breiten festgelegten Interventionen;
sie sind keine standardisierten Elastizitäten oder Wahrscheinlichkeitsintervalle.
Kostenreaktionen auf die beiden Stufen müssen nicht symmetrisch sein. Die
kontinuierlichen LP-Optima erlauben keine pauschale monotone Interpretation von
PEM- oder Speicherkapazitäten; die tatsächlichen Lösungen sind fallweise zu lesen.

Huelva S2 reagiert auf den Preisoffset asymmetrisch: Bei −20 EUR/MWh sinken die LCOH um 7,12 %; bei +20 EUR/MWh steigen sie nur von 6,4696 auf 6,4716 EUR/kg (+0,03 %). Der physische Netzbezug geht dabei von 40,642 GWh/a auf 0,000 GWh/a zurück; die fünf Kapazitäten bleiben in diesen beiden Lösungen gleich. Das ist eine fallbezogene Reaktion des optimalen Betriebs auf die neue Preisreihe, keine allgemeine Unempfindlichkeit der Stundenkorrelation gegenüber Strompreisen.

![Ökonomische LCOH-Änderungen gegenüber der passenden D0-Basis](../outputs_h2/eu_case_studies/historical_2024/step24/sensitivities_20261004/results/eu_economic_oat_deltas.png)

Die Kostenordnung **S0 ≤ S1 ≤ S2** bleibt in allen Profil- und ökonomischen Varianten erhalten. Huelva bleibt in allen gemeinsam variierten Standort-/Szenariopaaren günstiger.
Das belegt die beobachtete Ordnung innerhalb der geprüften gemeinsamen OAT-Bänder,
keinen universellen Standortvorteil und keine Robustheit gegenüber Kombinationen
mehrerer Parameter, asymmetrischen Standortänderungen oder weiteren Wetterjahren.
Die Quellen Wetter, Markt und Finanzierung sind damit nicht kausal voneinander isoliert.

### Quellenbindung, Ergebnisflags und Abnahme

Die Original-CSVs und die ursprünglichen sechs D0-Exports bleiben unverändert.
Jeder ökonomische Fall besitzt CSV und Schema-1.0-Sidecar mit eigenem SHA-256,
Parent-CSV-/Parent-Metadatenhash, `case_transformation` und gebundener
`baseline_configuration`. Der gemeinsame Sensitivitätsvergleich je Standort hat
27 Zeilen: 24 neue Varianten und drei wiederverwendete akzeptierte D0-Ergebnisse;
`number_of_optimization_runs=24`, `number_of_reused_baseline_runs=3`.
Basis-WACC und effektive Sensitivitätsraten bleiben im Metadatenvertrag getrennt.

Die neue jährliche Exportabnahme besteht **2240/2240 Prüfungen**; zusätzliche
optionale Provenienzprüfungen sind darin enthalten. Der Zähler folgt den tatsächlich
vorhandenen Prüfzeilen: Ökonomische Drei-Szenario-Ansichten besitzen keine separate
Szenarienrunner-Vergleichsmetadatei und werden nicht aus alten Zählern hochgerechnet.
Der getrennte unabhängige Quellen-/Ergebnisaudit besteht **4975/4975
Prüfungen** mit 509 unterschiedlichen SHA-256-gebundenen Dateien.
Die Softwareabnahme umfasst **618 Tests und 6 Unterprüfungen**
(624 JUnit-Einträge); diese Zähler werden nicht mit Jahresprüfungen addiert.
Die ursprüngliche Schritt-23-Abnahme 224/224 und ihr 275/275-Audit bleiben historische
eigene Nachweise. Nachrechnung vorhandener Lösungen ist kein zweiter unabhängiger
Optimallösungslauf und ersetzt den dokumentierten Solverstatus nicht.

`red_iii_temporal_compliant` bewertet ausschließlich die modellierte Ortsmonats-
beziehungsweise physische Stundenmengenkorrelation; S0 hat keine solche Zusatzregel.
`red_iii_ghg_compliant` ist der THG-Test der regulatorischen elektrischen Teilbilanz.
Regulatorische Nullwerte bei S1/S2 dürfen weder als physische Emissionsfreiheit
noch als vollständiger Produkt-Fußabdruck gelesen werden. Zusätzlichkeit,
geografische Korrelation und exklusive EE-Allokation bleiben externe Annahmen;
`low_price_exception=disabled` und `full_RFNBO_certification_claim=false` bleiben bestehen.
S0→S1 verändert auch die Überschussallokation; ausschließlich S1→S2 variiert deren
zeitliche Korrelation unter derselben Allokationskonvention.

Nachweise: [66-Fall-Ergebnistabelle](../outputs_h2/eu_case_studies/historical_2024/step24/sensitivities_20261004/results/all66_result_cases.csv),
[Nachfragevergleich](../outputs_h2/eu_case_studies/historical_2024/step24/sensitivities_20261004/results/demand_profile_comparison.csv),
[OAT-Vergleich](../outputs_h2/eu_case_studies/historical_2024/step24/sensitivities_20261004/results/economic_OAT_comparison.csv),
[Abnahmesummary](../outputs_h2/eu_case_studies/historical_2024/step24/sensitivities_20261004/results/step24_results_summary.json),
[separater Audit](../outputs_h2/eu_case_studies/historical_2024/step24/sensitivities_20261004/scientific_review/STEP24_UNABHAENGIGE_PRUEFUNG.md),
[Softwarebericht](../outputs_h2/eu_case_studies/historical_2024/step24/sensitivities_20261004/validation/pytest_full_suite_summary.json) und
[Figuren-/Quellenmanifest](../outputs_h2/eu_case_studies/historical_2024/step24/sensitivities_20261004/results/figure_manifest.json);
[Figurenindex und Aussagegrenzen](../outputs_h2/eu_case_studies/historical_2024/step24/sensitivities_20261004/results/FIGUREN_UND_GRENZEN.md).

## 18b. Wissenschaftliche Diskussion und Manuskript – Schritt 25

**Fachlich abgeschlossen am 04.10.2026.** Der [Manuskriptentwurf](../manuskript/FORSCHUNGSARBEIT_ENTWURF.md)
verbindet Forschungsfrage, Methodik, Daten, Resultate, Literaturvergleich und Fazit.
Die [unabhängige Ergebnisableitung](../outputs_h2/eu_case_studies/historical_2024/step25/discussion_20261004/result_analysis/step25_result_claims.json)
rechnet die 66 Tabellenzeilen gegen Original-Summaries und die Basisbetriebsgrößen
gegen sechs Stundenexporte nach. Die Standortordnung gilt in 33/33 gepaarten
Fällen, die Kostenordnung S0 ≤ S1 ≤ S2 in 22/22 Standort-/Varianten-Gruppen.

Der isolierte D0-Wechsel S1→S2 erhöht die LCOH um **29,15 % in Hamburg** und
**33,01 % in Huelva**. Der Speicher wächst um Faktoren **8,09 bzw. 3,60**.
Die Standortdifferenz verändert Wetter, Markt und WACC gemeinsam; sie ist keine
kausale Wetterzerlegung. D1/D2 sind andere stündliche Lieferpflichten, keine
ineinander geschachtelten Flexibilitätsrestriktionen. Die OAT-Bänder bleiben
Einzelfaktorannahmen und tragen keine kombinierte oder probabilistische Robustheit.

Der [Primärliteraturvergleich](../outputs_h2/eu_case_studies/historical_2024/step25/discussion_20261004/literature/STEP25_LITERATURVERGLEICH.md)
ordnet Brandt et al., Zeyen et al., Ricks et al. sowie Ruhnau/Schiele nach Modell-
und Emissionsgrenze ein. Die IRENA-Finanzierungsquelle wird dem realen 2021-Anhang
zugeordnet; nominale Umfragewerte des Hauptberichts werden nicht vermischt.
Literaturzahlen dienen keinem direkten Gleichheitsnachweis unserer LCOH.

Betriebliche Jahresreferenz und regulatorische elektrische Null bleiben getrennt.
Statische Faktoren können keinen Vorteil einzelner Emissionsstunden belegen;
konsequenzielle Netzeffekte, vollständige LCA und RFNBO-Zertifizierung bleiben
außerhalb des Nachweises. S2 auf 2024-Daten ist ein Regelvergleich, keine 2030-Prognose.
Die [Scope-Prüfung](../outputs_h2/eu_case_studies/historical_2024/step25/discussion_20261004/scope_review/STEP25_SCOPE_REVIEW.md) und
[Manuskriptabnahme](../outputs_h2/eu_case_studies/historical_2024/step25/discussion_20261004/acceptance_report.json) dokumentieren diese Grenzen.
Dieser Schritt erzeugt keine neuen Jahresoptimierungen oder Parameteränderungen.
Der Entwurf benötigt vor Einreichung eine Betreuungsdurchsicht und formale Anpassung.

## 19. Grenzen dieser Fallstudie

- Repräsentative Anlagenpunkte und Reanalysezellen ersetzen keine Projektvermessung.
- Historisches 2024 mit perfekter Voraussicht ist keine künftige Marktbewertung. Die geprüften OAT-Bänder beschränken die Robustheitsaussage auf diesen Versuchsraum; kombinierte Risiken und weitere Wetterjahre sind nicht geprüft.
- Großhandelskosten ohne Anschluss-/Tarifbestandteile sind keine vollständigen Projektstromkosten.
- Produktionsmix-Direktfaktor ist kein Hafenverbrauchsmix oder marginaler Faktor.
- Historische regulatorische Länderwerte sind von 2024-Betriebsdaten getrennt.
- WACC ist national/technologisch und mit eigener H2-Zuordnung, keine Finanzierungszusage.
- Nachfrageprofile und gemeinsamer Wasserpreis sind Vergleichsannahmen.
- Zusätzlichkeit, geografische Korrelation und exklusive Allokation sind extern vorausgesetzt; erzeugter EE-Überschuss wird zugeordnet, aber reale Export-/Vertragsgrenzen sind nicht modelliert.
- Nationale HVPI-Deflation, Netto-/Raumnäherung und Finanzierungsproxy 2021→2024 sind dokumentierte Vergleichsannahmen.
- Statische Betriebsreferenzen sind Jahres-/Raum-/Nennerproxies; eigene dynamische
  Technologiefaktoren und ES-Erzeugungsfreigabe bleiben optional offen.

## 20. Reproduzierbarkeit und nächster Schritt

Die [aktive Design-JSON](../input_data/h2_eu_case_studies.json),
[2024-Rohquellen](../outputs_h2/eu_case_studies/historical_2024/step19/raw/),
[Aufbereitungsbericht](../outputs_h2/eu_case_studies/historical_2024/step19/prepared/preparation_report.json),
[statische Freigabe](../outputs_h2/eu_case_studies/historical_2024/step19/static_factors_20261003/released_inputs/static_factor_release_report.json)
und [Volljahresprüfung](../outputs_h2/eu_case_studies/historical_2024/step19/validation/full_year_input_preflight.json)
belegen die aktuelle Datenbasis. Abrufnachweise nennen Original-URL und SHA-256.
`profiles_prices_unreleased.csv` bleibt ausdrücklich eine vorgelagerte Ausgabe;
die sechs `<site>_D0|D1|D2_static_factors.csv` sind die vollständigen Inputs.

Reproduktion mit `h2-model` aus dem Repository; neue Ausgabeordner verwenden:

```powershell
python acquire_eu_historical_sources.py --design input_data/h2_eu_case_studies.json --output outputs_h2/eu_case_studies/historical_2024/step19/reproduction_raw --groups weather,prices
python prepare_eu_historical_data.py --design input_data/h2_eu_case_studies.json --sources outputs_h2/eu_case_studies/historical_2024/step19/reproduction_raw --output outputs_h2/eu_case_studies/historical_2024/step19/reproduction_prepared
python prepare_eu_static_inputs.py --prepared outputs_h2/eu_case_studies/historical_2024/step19/reproduction_prepared --catalog input_data/h2_eu_static_factors.json --source-root . --profiles D0,D1,D2 --output outputs_h2/eu_case_studies/historical_2024/step19/reproduction_released
```

Der bestehende Rohquellenbestand kann offline nach Hashprüfung benutzt werden.
Die Faktorquellen liegen separat gehasht im 2024-Archiv; sie werden vor Freigabe
gegen ihre Originalzellen geprüft. Die [Finanzierungs-/Jahresrollenprüfung](../outputs_h2/eu_case_studies/historical_2024/step19/parameter_consistency_review/PARAMETERKONSISTENZ_2024.md)
hat neun Originalquellen überprüft und erklärt die nicht aktivierten Alternativen.
Die alte 2025-Design-JSON, der alte Faktorkatalog und die bisherigen MD-Dateien
sind exakt im Migrationsarchiv gesichert; bestehende 2025-Outputs bleiben unverändert.
Eine 2025-Reproduktion benötigt ausdrücklich diese alten Design-/Katalogdateien,
statt den aktuellen 2024-Vertrag auf alte Reihen anzuwenden.

Die ausgeführten Runner verwenden passende `--eu-site`,
`--emission-factor-metadata <input>.metadata.json` und
`--require-separate-emission-factors`. Der Modus `complete` bewertet beide Quellen.
Die anschließende Ergebnisprüfung mit `validate_h2_results.py` erhält ausdrücklich
`--expected-hours 8784`; dieses Argument gehört zum Validator. Sein Default
8.760 bleibt für historische Nicht-Schaltjahr-/Legacy-Prüfungen erhalten.
Ein deklariertes Volljahr wird auch durch den Sidecar-Vertrag gegen die Zeilenzahl geprüft.
Die gespeicherte Annualisierung wird im Ergebnisvalidator aus Kalender
und Konfiguration nachgerechnet. Kleine zyklische Solvertests sind keine Jahresergebnisse.

Die sechs akzeptierten Läufe verwenden eine [unveränderliche Designkopie](../outputs_h2/eu_case_studies/historical_2024/step23/base_cases_20261004/evidence/h2_eu_case_studies_run_design.json)
mit SHA-256 `33c5502965022aaa38f9f0be6a54f18bb8be16462d1e8a6daf90668d89223cb3`.
Der [Laufvertrag](../outputs_h2/eu_case_studies/historical_2024/step23/base_cases_20261004/run_contract.json) hält Interpreter, Paketversionen,
neun Codehashes, beide Eingabe-/Sidecarhashes und Git-Referenzen fest.
Die aktuelle Master-JSON darf ihren Fortschrittsstatus weiterentwickeln; die
gefrorene Laufquelle bleibt für genau diese Resultate unverändert. Schritt 24
verwendet eine byteidentische Kopie dieses Designs mit demselben SHA-256.
Die neun Schritt-23-Quellen liegen in `evidence/code_snapshot`; Schritt 24
trennt `evidence/initial_code` für D1/D2 von `evidence/economic_code` für die
erweiterten ökonomischen Runner und Provenienzprüfungen. Der heutige Runner-/
Validatorcode stimmt daher nicht mit sämtlichen ursprünglichen Codehashes überein.
Unverändert bleiben LP, Basiskonfiguration, RED-Rechnung und ursprüngliche Ergebnisse.

Reproduktion der Basisfälle aus dem bestehenden Quellenbestand in neuen
Ergebnisordnern nach Aktivierung von `h2-model`. Die folgenden Aufrufe stellen
die neun archivierten Quellen aus `evidence/code_snapshot` vor den heutigen
Modulen in den Suchpfad; damit gelten die Originalversionen aus Schritt 23:

```powershell
python -c "import sys; sys.path.insert(0, r'outputs_h2/eu_case_studies/historical_2024/step23/base_cases_20261004/evidence/code_snapshot'); from run_h2_scenarios import main; raise SystemExit(main())" --input outputs_h2/eu_case_studies/historical_2024/step19/static_factors_20261003/released_inputs/hamburg_moorburg_D0_static_factors.csv --output-dir outputs_h2/eu_case_studies/historical_2024/step23/reproduction_hamburg_D0 --solver scipy-highs --emission-factor-metadata outputs_h2/eu_case_studies/historical_2024/step19/static_factors_20261003/released_inputs/hamburg_moorburg_D0_static_factors.metadata.json --require-separate-emission-factors --eu-site hamburg_moorburg --eu-design outputs_h2/eu_case_studies/historical_2024/step23/base_cases_20261004/evidence/h2_eu_case_studies_run_design.json
python -c "import sys; sys.path.insert(0, r'outputs_h2/eu_case_studies/historical_2024/step23/base_cases_20261004/evidence/code_snapshot'); from validate_h2_results import main; raise SystemExit(main())" --results-dir outputs_h2/eu_case_studies/historical_2024/step23/reproduction_hamburg_D0 --expected-hours 8784
python -c "import sys; sys.path.insert(0, r'outputs_h2/eu_case_studies/historical_2024/step23/base_cases_20261004/evidence/code_snapshot'); from run_h2_scenarios import main; raise SystemExit(main())" --input outputs_h2/eu_case_studies/historical_2024/step19/static_factors_20261003/released_inputs/huelva_la_rabida_D0_static_factors.csv --output-dir outputs_h2/eu_case_studies/historical_2024/step23/reproduction_huelva_D0 --solver scipy-highs --emission-factor-metadata outputs_h2/eu_case_studies/historical_2024/step19/static_factors_20261003/released_inputs/huelva_la_rabida_D0_static_factors.metadata.json --require-separate-emission-factors --eu-site huelva_la_rabida --eu-design outputs_h2/eu_case_studies/historical_2024/step23/base_cases_20261004/evidence/h2_eu_case_studies_run_design.json
python -c "import sys; sys.path.insert(0, r'outputs_h2/eu_case_studies/historical_2024/step23/base_cases_20261004/evidence/code_snapshot'); from validate_h2_results import main; raise SystemExit(main())" --results-dir outputs_h2/eu_case_studies/historical_2024/step23/reproduction_huelva_D0 --expected-hours 8784
```

Die Originalausgaben liegen unter `runs/<site>/D0` mit Summary, Stundenplan,
validiertem Input, Metadaten, Vergleich und unabhängigen Prüfberichten.
[Hamburg-Prüfung](../outputs_h2/eu_case_studies/historical_2024/step23/base_cases_20261004/runs/hamburg_moorburg/D0/validation/validation_report.json)
und [Huelva-Prüfung](../outputs_h2/eu_case_studies/historical_2024/step23/base_cases_20261004/runs/huelva_la_rabida/D0/validation/validation_report.json)
bestätigen zusammen 224/224 Prüfungen. Die [zusätzliche Ergebnisprüfung](../outputs_h2/eu_case_studies/historical_2024/step23/base_cases_20261004/scientific_review/annual_base_case_scientific_audit.json)
bestätigt separat 275/275 Prüfungen einschließlich Originalquellen und Nachrechnung.
Es wurden weder Kernparameter noch Solver-/Validierungstoleranzen geändert.
Die zuvor bestandenen 583 Softwaretests und 6 Unterprüfungen gehören zur
Schritte-19–22-Abnahme; sie werden von diesen neuen Ergebnisprüfungen unterschieden.

Zwei alte reine Beschreibungstexte bleiben im unveränderlichen Laufnachweis
kenntlich: Die gefrorene JSON nennt Ortsmonate noch als ausstehend, obwohl
ihre Rechenschlüssel und Exporte korrekt lokale Monate verwenden. Der
Speicherprüfer nennt im Detailtext „Stunde 8760“, rechnet aber tatsächlich mit
der letzten Zeile (`iloc[-1]`), hier Stunde 8784. Beide betreffen keine Zahlen.
Der Statusfreitext in der aktuellen Master-JSON wurde berichtigt; die gehashten
Laufdateien und die zugehörigen archivierten Modellversionen wurden nicht nachträglich verändert.

Ein eingefrorener Step24-Prüffreitext zu `sensitivity_parent_input_contract`
sagt verkürzt „Preisoffset erhält Verlauf und Vorzeichen“. Rechnerisch wird die
additive stündliche Verschiebung ohne Nullkappung geprüft; das Vorzeichen
einzelner Stunden darf wechseln. Die Klarstellung betrifft ausschließlich diesen
Freitext, keine Transformation, Prüfbedingung oder Zahlenänderung.

### Schritt-24-Reproduktion mit gebundenen Quellenversionen

Die Profile nutzten `evidence/initial_code`, die ökonomischen Fälle den separat
gehashten Vertrag `economic_code_contract.json` und `evidence/economic_code`.
Die ursprünglichen sechs D0-Exports bleiben im Schritt-23-Archiv. Jeder neue
Aufruf erhält einen neuen Ausgabeordner und den eingefrorenen Step24-Designpfad.
Die folgenden Befehle sind Reproduktion, keine Beschreibung zusätzlicher ausgeführter Läufe.

```powershell
python -c "import sys; sys.path.insert(0, r'outputs_h2/eu_case_studies/historical_2024/step24/sensitivities_20261004/evidence/initial_code'); from run_h2_scenarios import main; raise SystemExit(main())" --input outputs_h2/eu_case_studies/historical_2024/step19/static_factors_20261003/released_inputs/hamburg_moorburg_D1_static_factors.csv --output-dir outputs_h2/eu_case_studies/historical_2024/step24/reproduction_hamburg_moorburg_D1 --solver scipy-highs --emission-factor-metadata outputs_h2/eu_case_studies/historical_2024/step19/static_factors_20261003/released_inputs/hamburg_moorburg_D1_static_factors.metadata.json --require-separate-emission-factors --emissions-reporting complete --eu-site hamburg_moorburg --eu-design outputs_h2/eu_case_studies/historical_2024/step24/sensitivities_20261004/evidence/h2_eu_case_studies_run_design.json
python -c "import sys; sys.path.insert(0, r'outputs_h2/eu_case_studies/historical_2024/step24/sensitivities_20261004/evidence/initial_code'); from validate_h2_results import main; raise SystemExit(main())" --results-dir outputs_h2/eu_case_studies/historical_2024/step24/reproduction_hamburg_moorburg_D1 --expected-hours 8784
python -c "import sys; sys.path.insert(0, r'outputs_h2/eu_case_studies/historical_2024/step24/sensitivities_20261004/evidence/initial_code'); from run_h2_scenarios import main; raise SystemExit(main())" --input outputs_h2/eu_case_studies/historical_2024/step19/static_factors_20261003/released_inputs/hamburg_moorburg_D2_static_factors.csv --output-dir outputs_h2/eu_case_studies/historical_2024/step24/reproduction_hamburg_moorburg_D2 --solver scipy-highs --emission-factor-metadata outputs_h2/eu_case_studies/historical_2024/step19/static_factors_20261003/released_inputs/hamburg_moorburg_D2_static_factors.metadata.json --require-separate-emission-factors --emissions-reporting complete --eu-site hamburg_moorburg --eu-design outputs_h2/eu_case_studies/historical_2024/step24/sensitivities_20261004/evidence/h2_eu_case_studies_run_design.json
python -c "import sys; sys.path.insert(0, r'outputs_h2/eu_case_studies/historical_2024/step24/sensitivities_20261004/evidence/initial_code'); from validate_h2_results import main; raise SystemExit(main())" --results-dir outputs_h2/eu_case_studies/historical_2024/step24/reproduction_hamburg_moorburg_D2 --expected-hours 8784
python -c "import sys; sys.path.insert(0, r'outputs_h2/eu_case_studies/historical_2024/step24/sensitivities_20261004/evidence/initial_code'); from run_h2_scenarios import main; raise SystemExit(main())" --input outputs_h2/eu_case_studies/historical_2024/step19/static_factors_20261003/released_inputs/huelva_la_rabida_D1_static_factors.csv --output-dir outputs_h2/eu_case_studies/historical_2024/step24/reproduction_huelva_la_rabida_D1 --solver scipy-highs --emission-factor-metadata outputs_h2/eu_case_studies/historical_2024/step19/static_factors_20261003/released_inputs/huelva_la_rabida_D1_static_factors.metadata.json --require-separate-emission-factors --emissions-reporting complete --eu-site huelva_la_rabida --eu-design outputs_h2/eu_case_studies/historical_2024/step24/sensitivities_20261004/evidence/h2_eu_case_studies_run_design.json
python -c "import sys; sys.path.insert(0, r'outputs_h2/eu_case_studies/historical_2024/step24/sensitivities_20261004/evidence/initial_code'); from validate_h2_results import main; raise SystemExit(main())" --results-dir outputs_h2/eu_case_studies/historical_2024/step24/reproduction_huelva_la_rabida_D1 --expected-hours 8784
python -c "import sys; sys.path.insert(0, r'outputs_h2/eu_case_studies/historical_2024/step24/sensitivities_20261004/evidence/initial_code'); from run_h2_scenarios import main; raise SystemExit(main())" --input outputs_h2/eu_case_studies/historical_2024/step19/static_factors_20261003/released_inputs/huelva_la_rabida_D2_static_factors.csv --output-dir outputs_h2/eu_case_studies/historical_2024/step24/reproduction_huelva_la_rabida_D2 --solver scipy-highs --emission-factor-metadata outputs_h2/eu_case_studies/historical_2024/step19/static_factors_20261003/released_inputs/huelva_la_rabida_D2_static_factors.metadata.json --require-separate-emission-factors --emissions-reporting complete --eu-site huelva_la_rabida --eu-design outputs_h2/eu_case_studies/historical_2024/step24/sensitivities_20261004/evidence/h2_eu_case_studies_run_design.json
python -c "import sys; sys.path.insert(0, r'outputs_h2/eu_case_studies/historical_2024/step24/sensitivities_20261004/evidence/initial_code'); from validate_h2_results import main; raise SystemExit(main())" --results-dir outputs_h2/eu_case_studies/historical_2024/step24/reproduction_huelva_la_rabida_D2 --expected-hours 8784
python -c "import sys; sys.path.insert(0, r'outputs_h2/eu_case_studies/historical_2024/step24/sensitivities_20261004/evidence/economic_code'); from run_h2_sensitivity import main; raise SystemExit(main())" --input outputs_h2/eu_case_studies/historical_2024/step19/static_factors_20261003/released_inputs/hamburg_moorburg_D0_static_factors.csv --cases outputs_h2/eu_case_studies/historical_2024/step24/sensitivities_20261004/case_tables/hamburg_moorburg_economic_cases.csv --output-dir outputs_h2/eu_case_studies/historical_2024/step24/reproduction_hamburg_moorburg_economic --scenarios all --solver scipy-highs --emission-factor-metadata outputs_h2/eu_case_studies/historical_2024/step19/static_factors_20261003/released_inputs/hamburg_moorburg_D0_static_factors.metadata.json --require-separate-emission-factors --emissions-reporting complete --eu-site hamburg_moorburg --eu-design outputs_h2/eu_case_studies/historical_2024/step24/sensitivities_20261004/evidence/h2_eu_case_studies_run_design.json --reuse-baseline-dir outputs_h2/eu_case_studies/historical_2024/step23/base_cases_20261004/runs/hamburg_moorburg/D0
python -c "import sys; sys.path.insert(0, r'outputs_h2/eu_case_studies/historical_2024/step24/sensitivities_20261004/evidence/economic_code'); from run_h2_sensitivity import main; raise SystemExit(main())" --input outputs_h2/eu_case_studies/historical_2024/step19/static_factors_20261003/released_inputs/huelva_la_rabida_D0_static_factors.csv --cases outputs_h2/eu_case_studies/historical_2024/step24/sensitivities_20261004/case_tables/huelva_la_rabida_economic_cases.csv --output-dir outputs_h2/eu_case_studies/historical_2024/step24/reproduction_huelva_la_rabida_economic --scenarios all --solver scipy-highs --emission-factor-metadata outputs_h2/eu_case_studies/historical_2024/step19/static_factors_20261003/released_inputs/huelva_la_rabida_D0_static_factors.metadata.json --require-separate-emission-factors --emissions-reporting complete --eu-site huelva_la_rabida --eu-design outputs_h2/eu_case_studies/historical_2024/step24/sensitivities_20261004/evidence/h2_eu_case_studies_run_design.json --reuse-baseline-dir outputs_h2/eu_case_studies/historical_2024/step23/base_cases_20261004/runs/huelva_la_rabida/D0
```

Der ökonomische Runner erzeugt zunächst `sensitivity_comparison.csv` mit 27 Zeilen
je Standort. Für die unabhängige Drei-Szenario-Prüfung wird je Nichtbasisfall
eine `scenario_comparison.csv` aus genau seinen drei Zeilen erstellt;
`scenario_id` ist S0/S1/S2 und `result_directory` ist `reference`, `red_monthly`
oder `red_hourly`. Der Validator prüft anschließend jeden Fallordner unter
`runs/<case_id>` mit `--expected-hours 8784`. Die vorhandenen archivierten
Fallordner enthalten diesen Vergleich und die zugehörigen Prüfberichte.

Ein vollständiger Reproduktionsaufruf verwendet dafür die folgende Python-Schleife
nach den beiden Sensitivitätsaufrufen (aus dem Repository, in `h2-model`):

```python
from pathlib import Path
import sys
import pandas as pd
sys.path.insert(0, r'outputs_h2/eu_case_studies/historical_2024/step24/sensitivities_20261004/evidence/economic_code')
from validate_h2_results import validate_h2_results
for site in ('hamburg_moorburg', 'huelva_la_rabida'):
    root = Path('outputs_h2/eu_case_studies/historical_2024/step24') / f'reproduction_{site}_economic'
    comparison = pd.read_csv(root / 'sensitivity_comparison.csv')
    variants = comparison.loc[comparison.sensitivity_parameter != 'baseline']
    for case_id, group in variants.groupby('case_id', sort=False):
        assert len(group) == 3
        folder = root / 'runs' / case_id
        view = group.copy()
        view['scenario_id'] = view.scenario.map({'reference': 'S0', 'red_monthly': 'S1', 'red_hourly': 'S2'})
        view['result_directory'] = view.scenario
        view.to_csv(folder / 'scenario_comparison.csv', index=False)
        validation = validate_h2_results(folder, expected_hours=8784)
        assert validation.all_checks_passed
```

Schritt-24-Nachweise: [Versuchsvertrag](../outputs_h2/eu_case_studies/historical_2024/step24/sensitivities_20261004/experiment_contract.json), [ökonomischer Codevertrag](../outputs_h2/eu_case_studies/historical_2024/step24/sensitivities_20261004/economic_code_contract.json), [eingefrorenes Design](../outputs_h2/eu_case_studies/historical_2024/step24/sensitivities_20261004/evidence/h2_eu_case_studies_run_design.json).

**Schritt 25 bleibt fachlich abgeschlossen:** Ergebnisdiskussion,
Primärliteraturvergleich und Fazit sind historisch im
[Manuskriptentwurf](../manuskript/FORSCHUNGSARBEIT_ENTWURF.md) dokumentiert.
Die Manuskriptarbeit ist auf aktuellen Nutzerwunsch zurückgestellt.
Die ausdrücklich festgelegte Nachfragemengenanalyse ist mit eigenem
Laufvertrag und eigener Ergebnisabnahme abgeschlossen (Abschnitt 24).
Die anschließende fünfteilige GUI-Bedienrevision steht in Abschnitt 25.
Ein weiterer wissenschaftlicher Modellversuch ist noch nicht festgelegt.

### Erneute Ausführung der aktuellen D0-Basis

Auf Nutzerwunsch wurden am 04.10.2026 **sechs frische Jahresoptimierungen**
mit dem aktuellen Code ausgeführt: beide Standorte, D0 und S0/S1/S2. Eingaben
bleiben historisches 2024 mit 8.784 Stunden, Länderfaktoren 2024, Geldbasis
EUR 2023 und dokumentiertem WACC-2021-Proxy. Annualisierungsfaktor 1 und
3.650.000 kg gelieferter H2 gelten in allen sechs Fällen.

[Laufvertrag](../outputs_h2/eu_case_studies/historical_2024/verification_runs/basis_20261004_121938UTC/run_contract.json),
[neue Vergleichstabelle](../outputs_h2/eu_case_studies/historical_2024/verification_runs/basis_20261004_121938UTC/fresh_D0_results.csv),
[Abschlussstatus](../outputs_h2/eu_case_studies/historical_2024/verification_runs/basis_20261004_121938UTC/run_status.json) und
[zusätzliche Nachrechnung](../outputs_h2/eu_case_studies/historical_2024/verification_runs/basis_20261004_121938UTC/independent_review/fresh_run_review.json)
belegen die tatsächlichen Ausführungen. Alle sechs Fälle sind optimal; die
neuen Exporte bestehen 224/224 unabhängige Validatorprüfungen. Die
zusätzliche Prüfung bestätigt ihre Kosten gegenüber den ursprünglichen D0-Fällen.
Aktueller Code, Design und Inputs liegen als eigene gehashte Kopien in diesem
Laufarchiv; ursprüngliche Basis-/Sensitivitätsresultate werden nicht überschrieben.

Die sechs Ausführungen wiederholen vorhandene Szenariokombinationen. Sie
erweitern den wissenschaftlichen Versuchsraum von 66 unterschiedlichen Fällen
nicht auf 72. Optimale Zielfunktionswerte und die geprüften Bilanzen sind maßgeblich;
Kapazitätseindeutigkeit wird bei möglichen alternativen LP-Optima nicht behauptet.
Regulatorische Teilprüfung und statische Betriebsreferenz behalten ihre
dokumentierten Aussagegrenzen.

### Grafiken der erneut ausgeführten D0-Basis

Die [Grafikübersicht](../outputs_h2/eu_case_studies/historical_2024/verification_runs/basis_20261004_121938UTC/figures_20261004/GRAFIKEN_UEBERSICHT.md) enthält zwölf PNG-Abbildungen:
LCOH-, Kapazitäts-, Kostenanteils-, Betriebskennzahlen- und Stundenplots je
Standort sowie einen gemeinsamen Kosten- und Emissionsvergleich. Die
Betriebswoche ist für beide Standorte lokal 10.–17.02.2024 gewählt und
ist ein illustrativer Ausschnitt. Betriebliche Referenz und regulatorische
elektrische Teilbilanz bleiben getrennt. Bilder und Quellen sind gehasht;
alle zwölf Abbildungen wurden visuell geprüft. Modellresultate bleiben unverändert.

## 21. Quellenrollen

Die direkten Quellenlinks stehen bei den zugehörigen Annahmen in Abschnitten 3–10.
Ihre Rollen sind getrennt: HGHH/PRTR/Junta für Standortbezug; ECMWF/Open-Meteo für
Wetter; SMARD/REE/OMIE für Markt/Erzeugung; EEA/Eurostat für die aktive statische
Betriebsreferenz und Nennerumrechnung; JRC/Eurostat/FfE für die optionale eigene
dynamische Direktbilanz; EU-Recht für regulatorische Teilbedingungen;
IRENA/Brandt für Finanzierung und Technik.

Quelle, Abrufdatum, Gültigkeits-/Beobachtungsjahr, Einheit, Bilanzgrenze und
Raumebene werden vor der Jahresfreigabe im maschinenlesbaren Nachweis gesichert.
Die Reorganisation überprüft den vorhandenen Dokument-/Codezustand und erfindet
keine fehlenden Zahlen, Quellen oder EU-Ergebnisse.

## 23. Harmonisierte Sensitivitäten mit Namibia

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

Für eine Preisreihe mit arithmetischem Mittel μ gilt `p_t' = p_t ± 0,5 μ`.
Damit betragen die jährlichen Mittelwerte 50 / 150 % des Basiswerts. Preisabstände
bleiben unverändert; einzelne Vorzeichen dürfen wechseln, es wird nicht bei null
gekappt. Es handelt sich nicht um `p_t' = 0,5 p_t` bzw. `1,5 p_t` und nicht um eine
Variation des nach der Optimierung gezahlten, strommengengewichteten Einkaufspreises.
Namibias konstanter Wert 128 ergibt genau die bisherigen 64 / 192 EUR/MWh.

Der WACC-Faktor wird erst nach der Standortwahl auf PV, Wind, PEM, Kompressor und
Speicher angewandt. Er erhält die Verhältnisse der Komponentenraten; ihre absoluten
Prozentpunktabstände skalieren mit. Der H2-Aufschlag von 2 Prozentpunkten im
EU-Basisfall beträgt im niedrigen/hohen Sensitivitätsfall deshalb 1,2727 / 2,7273
Prozentpunkte. Dies ist eine Finanzierungssensitivität des gesamten Ratensatzes;
die ursprünglichen Länderbenchmarks und der Basisaufschlag werden nicht neu geschätzt.
Namibias einheitliche 11 % ergeben unverändert die bisherigen 7 / 15 %.

| Standort / WACC-Komponente | Basis | Niedrig | Hoch |
|---|---:|---:|---:|
| Hamburg / pv | 1.3000 % | 0.8273 % | 1.7727 % |
| Hamburg / wind_onshore | 1.3000 % | 0.8273 % | 1.7727 % |
| Hamburg / electrolyzer | 3.3000 % | 2.1000 % | 4.5000 % |
| Huelva / pv | 3.6000 % | 2.2909 % | 4.9091 % |
| Huelva / wind_onshore | 3.1000 % | 1.9727 % | 4.2273 % |
| Huelva / electrolyzer | 5.3500 % | 3.4045 % | 7.2955 % |

Kompressor und H2-Speicher verwenden jeweils dieselben Raten wie PEM.

| Standort | Mittlerer Basispreis | Preisoffset niedrig / hoch |
|---|---:|---:|
| Hamburg | 76.601218 | −38.300609 / +38.300609 |
| Huelva | 61.279935 | −30.639968 / +30.639968 |

Preise und Offsets in realen EUR 2023/MWh, Basisreihe: vollständiges lokales 2024.

### Ergebnisse des gemeinsamen Diagnoseprogramms

| Einfluss | Namibia | Hamburg | Huelva |
|---|---:|---:|---:|
| Preisniveau | -34.06 bis +2.23 % | -49.52 bis +26.53 % | -41.55 bis +19.88 % |
| WACC | -25.27 bis +27.37 % | -6.99 bis +7.40 % | -13.46 bis +14.67 % |
| PEM-CAPEX | -9.01 bis +8.76 % | -5.17 bis +4.55 % | -7.12 bis +7.00 % |
| PEM-Strombedarf | -9.40 bis +9.31 % | -8.87 bis +8.82 % | -8.87 bis +8.83 % |
| PV-CAPEX | -10.16 bis +10.03 % | -4.12 bis +3.45 % | -9.91 bis +9.88 % |
| Wind-CAPEX | -3.59 bis +0.00 % | -26.07 bis +15.15 % | -11.49 bis +0.38 % |
| Speicher-CAPEX | -1.74 bis +1.68 % | -7.08 bis +6.96 % | -2.60 bis +2.43 % |

Spannweiten über S0/S1/S2 und die jeweiligen Parameterstufen; keine normierten Elastizitäten.

Gleiche Diagnose- und Grafikmethoden machen die Eingabedaten nicht identisch:
Namibia verwendet TMY-Monate 2007–2016 mit technischem UTC-Index 2025 und 8.760
Stunden, die EU tatsächliches lokales 2024 mit 8.784 Stunden. Beide liefern
3.650.000 kg H2/a und verwenden die gleiche funktionelle Einheit. Namibia nutzt
11 % Regional-WACC, die EU dokumentierte komponentenspezifische 2021-Proxies.
Das Preisjahr des Namibia-Konstantpreises ist nicht vollständig belegt; EUR-2023-
Technologiekosten allein belegen keine Deflation dieses Strompreises.
Ein LCOH-Unterschied zwischen Ländern isoliert daher keinen kausalen Standorteffekt.
Namibias historische regulatorische 220er-Proxybewertung und die EU-Table-A-Faktoren
sind in den Emissionsbildern als unterschiedliche Quellenrollen bezeichnet.
Regulatorische Nullwerte betreffen die elektrische Teilbilanz, keine vollständige
RFNBO-Zertifizierung oder physische Emissionsfreiheit.

Alle drei Fälle erhalten denselben sechs Themen umfassenden Basissatz:
LCOH, Kapazitäten, Kostenbestandteile, Betriebskennzahlen, getrennte betriebliche /
regulatorische Emissionen und Stundenbetrieb. Hinzu kommen je drei S2-Sensitivitäts-
bilder sowie gemeinsame LCOH-Sensitivitätsvergleiche für S0/S1/S2 und ein Basiskostenbild.
Farben, Reihenfolge, Einheiten und Vergleichsachsen sind einheitlich; die PNGs haben
200 dpi. Negative Netzimportkosten werden unter null gestapelt. Windkapazität wird
in MW dargestellt, weil Namibia eine Nullbasis hat. Prozentänderungen anderer
Kapazitäten mit Nullbasis bleiben undefiniert und werden entsprechend gekennzeichnet.
Die Windgrafik zeigt nur getestete CAPEX-Stützpunkte, keine exakte Eintrittsschwelle.
Stundenbilder zeigen physische Direktnutzung und Netzimport, H2-Produktion vor Verlust,
Lieferung sowie Speicher am Stundenende. Der feste Ausschnitt 10.–17. Februar ist
illustrativ: Namibia Index 2025/UTC, EU 2024/lokale Zeit; keine Behauptung gleicher Wetterereignisse.
Bestehende Grafik- und Ergebnisarchive bleiben historische Nachweise.

[Grafikübersicht](../outputs_h2/cross_case_consistency/alignment_20261004/figures/GRAFIKEN_UEBERSICHT.md); [144-Fall-Tabelle](../outputs_h2/cross_case_consistency/alignment_20261004/results/common_sensitivity_comparison.csv); [Laufvertrag](../outputs_h2/cross_case_consistency/alignment_20261004/experiment_contract.json); [Abnahme](../outputs_h2/cross_case_consistency/alignment_20261004/completion_receipt.json).

## 24. Ergänzung: kleinere und größere H2-Jahresmengen

**Status: ABGENOMMEN am 6. Oktober 2026.** Der Nutzer hat fünf Anteile der Basis festgelegt
und anschließend den Umfang auf **Hamburg und Huelva, D0/D1/D2 sowie
S0/S1/S2** bestätigt. Der Versuch umfasst **90 Jahresfälle**; die
Manuskriptarbeit ist zurückgestellt.

### Menge variieren und das Lieferfenster beibehalten

Für ein Originalprofil `q_t` gilt `q_t(f) = f × q_t`, mit
`f ∈ {0,50; 0,75; 1,00; 1,25; 1,50}`. Die Pflichtlieferung in jeder
aktiven Stunde skaliert; alle bisherigen Nullstunden bleiben null.
D0 behält 8.784, D1 4.392 und D2 3.144 aktive Stunden. Die UTC-Zeitstempel,
lokalen Lieferfenster, Schalt-/Sommerzeitregeln und zwölf Ortsmonate bleiben
erhalten. Feiertage werden bei D2 weiterhin nicht gesondert ausgeschlossen.
Produktion und Speicherung sind auch außerhalb der Lieferfenster möglich.

| Anteil | Jahresmenge [kg H2/a] | Kalender-Tagesmittel 2024 [kg H2/d] |
|---|---:|---:|
| 50 % | 1.825.000 | 4.986,339 |
| 75 % | 2.737.500 | 7.479,508 |
| 100 % | 3.650.000 | 9.972,678 |
| 125 % | 4.562.500 | 12.465,847 |
| 150 % | 5.475.000 | 14.959,016 |

Das Kalender-Tagesmittel ist Jahresmenge / **366**. Bei D1/D2 ist es kein
Lieferwert für jede einzelne Stunde oder jeden Kalendertag. Die verlangte
Stundenmenge ergibt sich aus Jahresmenge / aktive Stunden des jeweiligen
Profils. Insbesondere erzeugt die 100-%-Basis weiterhin 3.650.000 kg/a,
keine stillen 3.660.000 kg/a.

Innerhalb jedes Standort-/Profilvergleichs werden ausschließlich
Nachfragespalte und gebundene effektive Nachfrageparameter geändert.
Unverändert bleiben PV-/Windprofile, reale historische Stundenpreise,
statischer betrieblicher Faktor, regulatorischer Faktor, Kalender, Technik,
Kosten und Komponenten-WACC. Wetter, Markt und Betriebsreferenz bleiben 2024,
Kostenbasis real EUR 2023, Finanzierungsproxy 2021 und normative Faktorrolle 2020.
Die Mengenstufen sind gesetzte Vergleichsannahmen, keine gemessene
Hafen-/Raffinerienachfrage, Marktprognose oder Wahrscheinlichkeitsverteilung.

### Neu dimensionierte Anlage und die erwartete Skalierung

Jede Stufe optimiert sämtliche Anlagenkapazitäten und den Jahresbetrieb neu.
Der Versuch untersucht deshalb Anlagen für unterschiedliche Pflichtmengen.
Die Simulation einer fest vorgegebenen Bestandsanlage oder des Ausfalls einer
Liefermenge wäre eine andere Forschungsfrage.

Der native Kern besitzt lineare, größenunabhängige Kosten und technische
Zusammenhänge. Absolute Standort-/Anschlusskapazitätsgrenzen,
Projektfixkosten, Mindestanlagenwerte und Größendegression fehlen.
Alle Nebenbedingungen sind homogen, abgesehen von der vorgeschriebenen
Nachfrage als einziger nicht null gesetzter rechter Seite. Für positive
Faktoren ist eine proportional skalierte Basislösung daher zulässig und
optimal. Theoretisch folgen

`J(f) = f × J(1)` und `LCOH(f) = J(f)/(f × Q(1)) = LCOH(1)`.

Eine größere Menge muss unter diesen Annahmen keine günstigeren Kosten je kg
erzeugen. Die berechneten Zielfunktionswerte und LCOH werden gegen diese
Eigenschaft geprüft. Alternative Kostenoptima können bei identischem
Kostenminimum unterschiedliche optimale Kapazitäts-/Dispatchwerte besitzen.
Exakte Proportionalität jedes Stundenexports oder jeder Emissionsintensität
ist deshalb eine Diagnose; sie wird nicht als universelle Eindeutigkeit
der optimalen Auslegung behauptet. Preisreaktionen der Strommärkte, feste
Anschlussgrenzen und real beobachtete Skaleneffekte werden nicht quantifiziert.

### Durchführung und Herkunft

Der Nativeingriff heißt `h2_demand_multiplier`, Einheit `factor`, und verlangt
einen positiven endlichen Wert. Seine Operation
`multiply_hourly_h2_demand_preserve_profile` wird in den abgeleiteten
Quellenmetadaten gespeichert. Parent-CSV, Parent-Sidecar, Basiskonfiguration
und Design bleiben per SHA-256 gebunden. Die effektive Jahresmenge ist
ausdrücklich eine Sensitivitätsannahme; der ursprüngliche freigegebene
Designwert wird nicht umgeschrieben.

Die Erweiterung betrifft `h2_sensitivity_overrides.py`,
`run_h2_sensitivity.py`, `run_single_site_h2.py` und `validate_h2_results.py`.
LP-Gleichungen, `config_h2.py`, Standortkonfiguration und aktive Design-JSON
werden durch diesen Versuch nicht verändert. Der unabhängige Validator
rekonstruiert Nachfrageoperation, Nachfragekonfiguration und Jahresziel
aus ihren gebundenen Quellen; abweichende Eingaben werden zurückgewiesen.

Die Prüfung der vorhandenen 18 Referenzexporte bestätigt passende
Input-/Metadatenhashes, skalare Parameter und Solver, aber einen anderen
Design-Dateihash. Deshalb werden in diesem Versuch auch die **18 Fälle bei
100 % frisch gelöst**. Zusammen mit den 72 Mengenvarianten sind das
**90 neue SciPy/HiGHS-Jahresoptimierungen**; ursprüngliche Resultate und
frühere Abnahmeberichte behalten ihre originalen Hashes und Pfade.

Alle Ergebnisgruppen werden als S0/S1/S2-Vergleich mit dem vorhandenen
Validator und `--expected-hours 8784` geprüft. Software- und Ergebnisprüfungen
sind getrennte Nachweise: **839 reguläre Softwaretests plus sechs Subtests, zusammen 845 JUnit-Prüfungen bestanden; die 141 Nachfrageprüfungen sind darin enthalten, nicht zusätzlich gezählt**;
**90 optimale vollständige 8.784-Stunden-Jahresfälle mit vollständiger Pflichtlieferung; 30 an ihre eigenen Drei-Szenario-CSV-Dateien gebundene unabhängige Berichte, 3.360/3.360 Einzelprüfungen bestanden**; **zusätzlicher erfolgreicher Quell-/Ergebnisaudit mit 30 Inputeingriffsprüfungen und 90 gebundenen nativen Exportgruppen; 50 gesonderte Postprocessingtests bestanden; diese Prüfungen ergänzen und ersetzen die unabhängigen Jahresberichte nicht**.

### Ergebnis und Auswertung

Die 90 tatsächlich neu gelösten Fälle bestätigen Kostenproportionalität und konstanten minimalen LCOH innerhalb der Prüftoleranz. Über alle Standorte, Profile und Szenarien reicht der LCOH von 3,888595 bis 7,422546 EUR 2023/kg H2; innerhalb jedes festen Standort-/Profil-/Szenariokontexts ändert er sich durch die Mengenstufe numerisch höchstens um 2.2524205e-12 EUR/kg. Die größte absolute Abweichung der Jahreskosten von `f × J(1)` beträgt 1.2330711e-05 EUR/a. Damit handelt es sich um ein geprüftes Ergebnis tatsächlicher Neuberechnungen, nicht um synthetisch skalierte Exporte. Kapazitäts-, Netzbezugs- und Emissionskurven verwenden die jeweils tatsächlich gelöste Variante; alternative gleich teure LP-Optima bleiben eine Diagnosegrenze.

Kosten und absolute Anlagengrößen werden zusätzlich zu LCOH dargestellt.
Gespeicherte Betrieb-/Emissionsgrößen gehören zur jeweils tatsächlich
gelösten optimalen Variante. Betriebliche Emissionen bleiben Netzimport mal
statische nationale Jahresreferenz; die regulatorische elektrische
Teilbilanz bleibt getrennt. Ein Nullwert ist kein vollständiger
RFNBO-Nachweis und keine physische Emissionsfreiheit.

In der GUI heißt die neue Sammlung **H₂-Jahresnachfrage: 50–150 % (2024)**.
Für jede Standortansicht wählen Sie unter **Sensitivitätsanalyse →
Gespeicherte Versuchsreihe** diese Sammlung und genau ein
**Lieferprofil der Sensitivitätskurven**. Kurve und Tabellen-Download
verwenden dasselbe Profil mit fünf Mengen und drei Szenarien.
Neue Mengenversuche verwenden den normalen Parameter **H2-Jahresnachfrage**;
bei D0/D1/D2 als ausdrücklich gewählten Basisprofilen und S0/S1/S2 ergeben
die fünf Mengen **45 Fälle je Standort**. Der Faktor 1 ist die einmalige
native Basis. Es gibt keinen besonderen Nachfrage-Übernahmebutton.
**H2-Lieferprofil** ist zusätzlich eine normale kategorische OAT-Dimension,
deren zusätzliche Profilstufen nur unveränderte numerische Basiswerte
verwenden. Die gemeinsame Namibia-/EU-Belegungshilfe bleibt bei 48 Fällen
je Standort und Basisprofil mit S0/S1/S2.

Archiv:
`outputs_h2/eu_case_studies/historical_2024/demand_quantity_20261005/`.
[Versuchsvertrag](../outputs_h2/eu_case_studies/historical_2024/demand_quantity_20261005/experiment_contract.json),
[90-Fall-Tabelle](../outputs_h2/eu_case_studies/historical_2024/demand_quantity_20261005/results/demand_quantity_comparison.csv),
[Ergebniserklärung](../outputs_h2/eu_case_studies/historical_2024/demand_quantity_20261005/results/NACHFRAGEMENGEN_ERGEBNISSE.md)
und [Abschlussnachweis](../outputs_h2/eu_case_studies/historical_2024/demand_quantity_20261005/completion_receipt.json).
Grafikindex und Herkunft: [zwölf PNG-/SVG-Abbildungen mit Quellenindex](../outputs_h2/eu_case_studies/historical_2024/demand_quantity_20261005/results/figures/ABBILDUNGSINDEX.md).
Ein erneuter SHA-256-Abgleich vom 6. Oktober 2026 bestätigt alle **1.170 zuvor geschützten Quellen-, Ergebnis- und GUI-Abnahmedateien unverändert**. Die aktuelle Oberflächenrevision wird separat abgelegt; alte Exporte, Quellenverträge und frühere Abnahmen werden nicht ersetzt.


## 25. Bedienrevision: fünf Bereiche mit erhaltenem Funktionsumfang

**Stand: 6. Oktober 2026.** Die aktuelle Oberfläche besitzt genau **Analyse**,
**Sensitivitätsanalyse**, **Vergleich**, **Quellen** und **Export**.
Analyse und Sensitivitätsanalyse verbinden Einstellungen → Berechnen →
Fortschritt → Resultate unmittelbar im selben Bereich. Alte Hauptseiten für
Planung, separaten Laufstart und Ergebnisse sind integriert; Fallstudienstatus,
Basiskonfiguration, Quellen und Validierung bleiben unter Quellen und beim
nativen Ergebnis zugänglich. Vergleich und Export erlauben gezielte Fall-,
Kennzahl-, Grafik- und Dateiauswahl.

Die vor und nach dem Umbau abgeglichene [Bestandsliste](../GUI_BESTANDSLISTE.md)
bestätigt **46/46 Kriterien**. An jedem der drei registrierten Standorte bleiben
alle zuvor angebotenen **elf numerischen Sensitivitätsparameter** erhalten.
Die EU-Standorte erhalten zusätzlich die gewöhnliche kategorische Dimension
`h2_delivery_profile`; Namibia besitzt weiterhin ausschließlich sein
registriertes D0-Profil. Szenarien S0/S1/S2/S3, HiGHS/Gurobi/auto,
Solververgleich, native Kennzahlen, Quellen- und Prüfnachweise bleiben erhalten.

H2-Jahresnachfrage ist ein normaler numerischer Parameter. Profile sind normale
kategorische Stufen; es gibt keinen besonderen Nachfrage-Button. Numerische
OAT-Varianten gelten nur für die ausdrücklich gewählten Basisprofile;
zusätzliche Profilstufen werden mit unveränderten numerischen Basiswerten
ergänzt. Dadurch entsteht kein stilles vollfaktorielles Experiment.
Ein gemeinsamer OAT-Auftrag bildet eine gespeicherte Familie über seine
Profil-CSV-Dateien. Jede Quelle behält ihren eigenen Hash und gebundenen
Prüfbericht. Vollständig identische Familien werden nur als Ganzes
zusammengefasst; teilweise überlappende Familien bleiben getrennt.

Die aktuelle installierte GUI-Prüfung besteht **123/123 Tests** ohne Fehler,
Fehlschläge oder übersprungene Fälle. Separat bestanden **40/40 Prüfungen**
der vorhandenen Adapter-, Job- und Ergebniswege. Diese 40 sind der gezielte
Kompatibilitätsnachweis des GUI-Umbaus; sie sind keine neue vollständige
845er-Gesamtsuite. Die zuvor aufgeführten 845 Softwareprüfungen gehören zur
gesonderten wissenschaftlichen Nachfrageerweiterung. Tatsächliche neue
Jahreslösungen sind die 90 EU-Nachfragemengenfälle; GUI-Interaktionstests mit
simulierter Workergrenze behaupten keine weitere Jahresoptimierung.

Mathematische Modelllogik geändert? **NEIN**. Wissenschaftliche Basisparameter
geändert? **NEIN**. Vorhandene Ergebnisse überschrieben? **NEIN**. Bestehende
CLI-Runner gebrochen? **NEIN**. Diese Aussagen beziehen sich auf den
Oberflächenumbau; der davor genehmigte neue Nachfrageparameter ist separat
in diesem Dokument beschrieben.

[Aktuelle Anleitung](../GUI_BEDIENUNGSANLEITUNG.md),
[aktueller GUI-Abnahmebericht](../GUI_ABNAHME.md),
[Installations- und Abschlussbeleg](../outputs_h2/gui_validation/simplified_20261006/interface_receipt.json).
Die vorhandene PDF dokumentiert ausdrücklich die vorherige Bedienrevision;
eine neue PDF und Manuskriptbearbeitung wurden nicht ausgeführt.


## 26. Tagesansicht der gespeicherten Ergebnisse (6. Oktober 2026)

Die GUI stellt nun auch einzelne Sensitivitätsfälle tageweise dar:
Solar-/Wind-Direktversorgung und Netzbezug oder gesamte Erzeugung und Netz
als Stundenverlauf bzw. kumulierte Tagesenergie. Ortszeit und vollständige
23/24/25-Stunden-Kalendertage werden berücksichtigt. Die Kurven sind reine
Auswertungen der vorhandenen Stundenexporte; Optimierungsmodell, Basis,
Jahreslösungen und unabhängige Validierung werden nicht geändert.
Bedienweg: Sensitivitätsanalyse → gespeicherte Versuchsreihe → Tagesstrom:
Solar, Wind und Netz → Ergebnisfall und Tag. Die aktualisierte GUI-Anleitung
und GUI_ABNAHME dokumentieren die geprüfte Ergänzung.


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
