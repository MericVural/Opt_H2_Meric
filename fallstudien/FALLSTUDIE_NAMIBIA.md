# Fallstudie Namibia – historischer Entwicklungs- und Validierungsfall

**Dokumentationsstand:** 3. Oktober 2026. **Ergebnisstand:** technische Abnahme vom 12. September 2026; Interpretation vom 14. September 2026.

Dieses Dokument sichert die abgeschlossenen Schritte 1–17. Es beschreibt vorhandene Eingaben, Modellstände und Ergebnisse; bei der Dokumentationsreorganisation wurden keine Modellläufe oder Tests erneut ausgeführt.

Allgemeine Gleichungen, Schnittstellen und Modellregeln stehen in [MODELL_UND_METHODIK.md](../MODELL_UND_METHODIK.md). Der aktuelle Forschungsumfang und die europäische Erweiterung stehen im [Forschungsarbeitsplan](../FORSCHUNGSARBEITSPLAN.md) und in der [Fallstudie Hamburg/Andalusien](FALLSTUDIE_HAMBURG_ANDALUSIEN.md).

## 1. Rolle und Ziel der Fallstudie

Namibia war der erste ausführliche Entwicklungs- und Validierungsfall des allgemeinen H2-Einzelstandortmodells. An der Nutzerkoordinate wurde der Ammoniakansatz zu einem eigenständigen Wasserstoffmodell entwickelt. Standortbezogene Ertragsprofile sowie Länder- und Regionalannahmen bilden einen reproduzierbaren technischen Referenzstand für spätere Fallstudien.

Seit dem Betreuergespräch vom 2. Oktober 2026 ist Hamburg–Moorburg/Huelva–La Rábida die aktive vergleichende Untersuchung. Namibia bleibt als historische Fallstudie erhalten; ihre Annahmen werden nicht automatisch auf die europäischen Standorte übertragen.

Die Referenz untersucht eine hypothetische standardisierte Anlage. Sie ist keine Standortplanung, Flächenprüfung, Anschlussstudie oder Finanzierung eines konkreten namibischen Projekts.

## 2. Forschungsfrage und Beitrag

Die damalige Forschungsfrage lautete:

> Wie beeinflussen der RED-III-Treibhausgasgrenzwert und die zeitliche Korrelation der Stromversorgung die kostenminimale Auslegung und die Levelised Cost of Hydrogen einer Elektrolyseanlage an einem frei wählbaren Standort?

S0, S1 und S2 verwenden denselben finalen Standortdatensatz und dieselben technischen und wirtschaftlichen Parameter. Die Szenarien unterscheiden sich durch die modellierte Zeitkorrelation und die zugehörige EE-Stromzuordnung. S0 setzt Erzeugung gleich Direktnutzung; S1/S2 erlauben zugeordnete Überschüsse. Der Vergleich isoliert die Wirkung dieses Regelpakets.

Die Fallstudie lieferte insbesondere:

- einen validierten H2-Kern mit PV, Onshore-Wind, Netz, PEM, Kompressor und Druckspeicher;
- zwei Solverpfade für dasselbe kontinuierliche lineare Problem;
- getrennte betriebliche und regulatorische Emissionsindikatoren;
- Szenarien-, Sensitivitäts-, Darstellungs- und unabhängige Validierungswerkzeuge;
- die Erkenntnis, dass geringe LCOH-Aufschläge große Veränderungen der Anlagenkonfiguration verdecken können.

## 3. Standort und räumliche Ebenen

| Größe | Finaler Fallstudienwert | Einordnung |
|---|---:|---|
| angefragte Breite | −21,0800° | Nutzervorgabe, WGS84 |
| angefragte Länge | 14,1610° | Nutzervorgabe, WGS84 |
| Rasterweite | 1° | entsprechend der Rasterlogik des ursprünglichen Ammoniakmodells |
| Modellbreite | −21,5° | Mittelpunkt des zugehörigen regelmäßigen Rasterpixels |
| Modelllänge | 14,5° | Mittelpunkt des zugehörigen regelmäßigen Rasterpixels |
| Distanz Anfrage → Modellpunkt | 58,435 km, gerundet 58,44 km | in Eingabemetadaten gespeichert |
| von PVGIS gemeldete Wetterkoordinate | −21,5° / 14,5° | für den finalen Wetterabruf |
| von PVGIS gemeldete Höhe | 539 m | finaler Pixelabruf |
| Land | Namibia, `NA` | ausdrücklich übergeben; Quelle „Explizite Benutzereingabe“ |

Die Option `--spatial-resolution 1` ordnet die angefragte Koordinate dem Pixelmittelpunkt zu. Der alte globale Pickledatensatz ist dafür nicht erforderlich. Rasterzuordnung und Wetterabruf werden getrennt reproduziert. PV/Wind beziehen sich auf den Modellpunkt, Preis und Netzfaktor auf das Land, WACC auf die Region. Ein einzelner Pixelwert belegt kein landesweites Potenzial.

Ohne ausdrücklichen Länderparameter kann der Datenadapter Natural Earth 1:110m nutzen. Bei Küsten-, Grenz-, Insel- oder Offshorepunkten ist die grobe Länderkarte begrenzt. Im Namibia-Fall wurde `NA` ausdrücklich festgelegt.

### Früherer Standortstand

Vor dem finalen Pixelabruf wurde die **exakte Nutzerkoordinate −21,0800° / 14,1610°** genutzt. Dort meldete PVGIS 439 m Höhe; Anfrage und gemeldeter Wetterpunkt lagen 0 km auseinander. Dieser technische Stand besitzt einen anderen Wetterdatensatz und Eingabe-Hash. Seine Ergebnisse stehen getrennt in Abschnitt 16 und dürfen nicht mit den finalen Pixelresultaten vermischt werden.

## 4. Zeitbasis und Bezugsjahre

| Bestandteil | Zeit-/Jahresbezug | Bedeutung |
|---|---|---|
| Stundenindex | 2025 | technisches Nicht-Schaltjahr, 8.760 Stunden |
| Zeitstandard | UTC | auch für die monatliche Namibia-Korrelation |
| erste Stunde | 2025-01-01 00:00 UTC | gespeicherter Indexbeginn |
| letzte Stunde | 2025-12-31 23:00 UTC | gespeicherter Indexschluss |
| Wetterauswahl | 2007–2016 | PVGIS-TMY aus repräsentativen Monaten |
| Netzfaktor | 2024 | Jahresmittel; Bericht erschien 2025 |
| Komponenten- und Wasserkosten | reale EUR 2023 | Brandt-Literaturbasis |
| H2-Nachfrage | Literaturannahme, Referenzjahr 2023 | kein gemessenes Standortprofil |
| regionaler WACC | kein Bezugsjahr in den Laufmetadaten | Modellfallback; keine Namibia-Beobachtung |

**2025 ist für Namibia ein Indexjahr. Die Wetterwerte sind kein tatsächlich beobachteter Verlauf von 2025.** Auch Strompreis, Netzfaktor und Finanzierung bilden keinen gemeinsamen historischen 2025-Datensatz.

Kürzere 24- und 168-Stunden-Perioden dienten der technischen Prüfung und wurden annualisiert. Finale Ergebnisse stammen aus Jahresläufen mit Annualisierungsfaktor 1. Die europäische Entscheidung für tatsächliche Wetter-/Marktintervalle von 2025 ändert den historischen Namibia-Datensatz nicht.

## 5. Wetter- und Erzeugungsdaten

`prepare_single_site_h2_input.py` ruft PVGIS-TMY ab und nutzt `calculate_renewable_yield.py`. Benötigt werden `temp_air`, `ghi`, `dni`, `dhi`, `wind_speed` und `pressure`. `pvlib` verarbeitet Strahlungs-/PV-Daten; `windpowerlib` bildet Windleistung ab.

### Ausgewählte TMY-Monate

Die beiden dokumentierten Standortstände verwenden unterschiedliche repräsentative Monate:

| Monat | finaler 1°-Pixel | vorläufige exakte Koordinate |
|---|---:|---:|
| Januar | 2007 | 2014 |
| Februar | 2016 | 2015 |
| März | 2009 | 2014 |
| April | 2008 | 2015 |
| Mai | 2014 | 2014 |
| Juni | 2014 | 2014 |
| Juli | 2011 | 2011 |
| August | 2007 | 2007 |
| September | 2015 | 2015 |
| Oktober | 2007 | 2015 |
| November | 2007 | 2016 |
| Dezember | 2008 | 2016 |

Der finale Abruf wurde am **12. September 2026, 16:54:22 UTC** dokumentiert; der Index blieb unverändert (`weather_index_alignment = unchanged`). Zwei Windwerte zwischen −1 und 0 wurden auf null gesetzt; für GHI, DNI und DHI beträgt die Bereinigungszählung jeweils null. Beim vorläufigen exakten Standort wurden zehn kleine negative Windwerte auf null gesetzt.

### Ertragsmodell und normierte Profile

| Größe | Verwendete Annahme |
|---|---|
| PV-Modul | Sandia-Modell `Sharp_NDQ235F4__2013_` |
| PV-Neigung | 35° |
| PV-Ausrichtung in Namibia | Norden, Azimut 0°, äquatorwärts |
| PV-Montage | `open_rack` |
| Wechselrichter | Sandia-Modell `ABB__MICRO_0_25_I_OUTD_US_208__208V_` |
| Onshore-Wind | Vestas V90, `V90/2000`, 2 MW |
| Nabenhöhe | 80 m |
| mittlerer PV-Kapazitätsfaktor | 0,250075858, gerundet 25,01 % |
| mittlerer Wind-Kapazitätsfaktor | 0,170179742, gerundet 17,02 % |

Die bereinigte Windfunktion übernimmt Länge und Zeitachse der übergebenen Wetterdaten; der Adapter unterstützt aktuelle und ältere `pvlib`-Rückgabeformate. Kapazitätsfaktoren geben verfügbare Leistung je installierter Leistung an; der Optimierer kann abregeln. TMY bildet weder interannuelle Streuung noch ein konkretes Extremjahr ab.

## 6. Strompreis und Kostenumfang

Der finale Namibia-Eingabedatensatz enthält in jeder Stunde **128 EUR/MWh**. Der Wert stammt aus dem landesweiten Gewerbestrompreis-Proxy in `input_data/gpp_2025_country_pages_numeric.json`.

Die Eingabemetadaten dokumentieren:

- Quelltyp `country_business_retail_price_proxy`;
- Quellwert 0,128 EUR/kWh und Modellwert 128 EUR/MWh;
- die Namibia-Seite von GlobalPetrolPrices;
- einen im Quellbestand verwendeten USD/EUR-Faktor von 0,86;
- konstante Wiederholung des Länderwerts über sämtliche Stunden;
- die ausdrückliche Eignungsgrenze `reference_cost_proxy_not_day_ahead_price`.

Der Proxy ist keine lokale PPA-Kondition und keine Day-Ahead-Reihe. Die RED-Niedrigpreis-Ausnahme bleibt deshalb deaktiviert. Netzengpässe, gesonderte Netzentgelte, PPA-Aufschläge, Übertragungsverluste und Erlöse für erneuerbare Überschüsse werden nicht zusätzlich modelliert.

**UNGEKLÄRT – Preisjahrkonsistenz:** Die Dokumentation behandelt die Kostenbasis als reale EUR 2023; der gespeicherte Strompreisbestand und seine Namibia-Metadaten enthalten keinen eindeutigen Beobachtungs-/Preisjahrnachweis und keine belegte Deflation auf EUR 2023. Der Dateiname mit `2025` belegt allein kein Datenjahr. Der historische Rechenwert 128 bleibt hier unverändert und als Proxy ausgewiesen.

## 7. Betriebliche Emissionsdaten

Der finale Fall verwendet **220 kg CO2e/MWh**, entsprechend 0,22 kg/kWh, aus dem **Electricity Control Board of Namibia, Integrated Annual Report 2025**, Datenjahr **2024**. `input_data/h2_country_factors.json` versioniert den Wert; die Metadaten kennzeichnen `country_annual_average`, `country_national_grid` und konstante Wiederholung über alle Stunden.

Die betriebliche Intensität bewertet den physischen Netzbezug je ausgeliefertem H2 und kann in S1 trotz bestandener Monatszuordnung positiv sein. Anlagenherstellung, Infrastruktur und weitere Vorketten fehlen; der Faktor ist kein lokaler oder marginaler Stundenfaktor. Die Kennzahl ist ein betrieblicher Strompfadindikator.

Der frühere technische Datensatz nutzte **350 kg CO2e/MWh** mit der Quellenbezeichnung „Technischer Testwert“. Dieser Wert wurde für den finalen wissenschaftlichen Fall durch den belegten 220er-Länderfaktor ersetzt.

## 8. Regulatorische Emissionsbewertung

Die Namibia-Läufe untersuchen Zeitzuordnung und regulatorischen THG-Teiltest gemäß [MODELL_UND_METHODIK.md](../MODELL_UND_METHODIK.md). Der historische Rechtsstand wurde im Modell am 10. September und für den Methodiktext am 13. September 2026 gegen EUR-Lex geprüft. Die Reorganisation ist keine erneute Rechtsprüfung.

Die hinterlegten Referenzwerte sind 94 g CO2e/MJ fossiler Vergleichswert, 70 % Mindestminderung und 120 MJ/kg H2 unterer Heizwert. Daraus folgen 28,2 g CO2e/MJ beziehungsweise **3,384 kg CO2e/kg H2**.

Im Referenzfall wird der physische Netzstrom regulatorisch als nicht erneuerbar bewertet. S1 und S2 erzwingen vollständige erneuerbare Mengendeckung im jeweiligen Zeitfenster; ihre regulatorische Stromlücke beträgt daher null. Der THG-Test ist dort eine Ex-post-Kontrolle und keine zusätzlich bindende Auslegungsrestriktion.

Die unabhängige Prüfung umfasst Elektrolyse **und Verdichtung** und nutzt tatsächlich modellierte PV-/Winderzeugung, getrennt vom direkten Eigenverbrauch. Zusätzlichkeit, geografische Korrelation und exklusive Allokation werden im Kontrollaufruf als positive Szenarioannahmen gesetzt; sie sind keine aus Namibia-Daten abgeleiteten Nachweise.

Für einen regulatorischen Projektbezug wäre ein gleichwertiges namibisches Gebotszonen-, Markt- oder Netzgebiet extern festzulegen und zu belegen. Inbetriebnahme, Förderstatus, PPA/eigene Anlage/direkte Leitung, Verträge und Zertifizierung bleiben ebenfalls extern.

Im eigenständigen Prüfer sind Rechtsgrenzen und Übergangsregeln hinterlegt; der Optimierer aktiviert hier weder die Niedrigpreis-Ausnahme noch die Sonderwege für hohen EE-Anteil, niedrige Netzintensität oder vermiedenen Redispatch.

**Ein Ergebnisfeld `red_iii_temporal_compliant = True` oder `red_iii_ghg_compliant = True` belegt ausschließlich den jeweiligen modellinternen Teiltest. Eine vollständige RFNBO-Zertifizierung ist für keinen Namibia-Lauf nachgewiesen.**

## 9. H2-Nachfrage und Bereitstellung

| Größe | Namibia-Basisfall |
|---|---:|
| Tagesabgabe | 10.000 kg H2/Tag |
| stündliche Abgabe | 416,666667 kg H2/h, konstant |
| Jahresabgabe | 3.650.000 kg = 3.650 t H2 |
| Jahresproduktion vor Verdichtungsverlust | 3.668.341,709 kg H2 |
| vereinfachter Verdichtungsverlust | 0,5 % |
| PEM-Ausgangsdruck | 30 bar |
| Kompressor-Ausgangsdruck | 350 bar |
| Speichernenndruck / funktionelle Einheit | 300 bar / 1 kg H2 am Speicherausgang |

Die Nachfrage folgt Brandt et al. (2024), Figure 4 und Supplementary Note 2; sie ist keine gemessene namibische Abnahme. Jede Stunde wird vollständig gedeckt; der zyklische Speicher verhindert kostenlosen Anfangsfüllungsverbrauch. Zeitvariable Profile oder veränderte Jahresmengen wurden allgemein erwogen, gehören aber nicht zu den 48 Namibia-Sensitivitätsläufen.

## 10. WACC und Finanzierung

Sämtliche Investitionskomponenten verwenden ausdrücklich **11 % realen WACC**. Mangels Namibia-Eintrag in der Steffen-et-al.-Datenbank gilt der Subsahara-Regionalfallback aus der ursprünglichen Modelllogik. Der frühere Datenprozessor wurde nach Sicherung dieser Annahme aus dem H2-Branch entfernt.

Der Wert wird nicht automatisch aus `input_data/SteffenEtAl2025_WACC_database.csv` gelesen. Der Runner erhält `--uniform-real-wacc 0.11` und eine Quellenbeschreibung; beides wird in den Laufmetadaten dokumentiert.

Der Konfigurationsstandard von 5 % für PV/Wind und 7 % für die H2-Anlage beschreibt den vorläufigen technischen Stand. Der finale 11-%-Fall darf damit nicht vermischt werden; seine Sensitivität nutzt 7/15 %. Der Regionalproxy ist keine projektspezifische Finanzierung, kein beobachteter Namibia-Zins und keine europäische Annahme.

## 11. Technisch-ökonomische Parameter

Brandt et al. (2024), Supplementary Tables 2–4, bildet den konsistenten Komponentenbasisfall. Die Geldwerte werden als reale EUR 2023 behandelt.

| Komponente | CAPEX | fixe OPEX pro Jahr | Lebensdauer | Literatur-WACC | finaler Namibia-WACC |
|---|---:|---:|---:|---:|---:|
| PV | 921 EUR/kW | 15,10 EUR/kW | 30 Jahre | 5 % | 11 % |
| Onshore-Wind | 1.779,50 EUR/kW | 22,64 EUR/kW | 25 Jahre | 5 % | 11 % |
| PEM | 1.297 EUR/kW | 20,20 EUR/kW | 30 Jahre | 7 % | 11 % |
| Kompressor | 4.577,50 EUR/kW | 4 % der CAPEX | 15 Jahre | 7 % | 11 % |
| H2-Druckspeicher | 733,50 EUR/kg H2 | 2 % der CAPEX | 25 Jahre | 7 % | 11 % |

| Weitere Größe | Wert |
|---|---:|
| PEM-Strombedarf einschließlich Peripherie | konstant 52,5 kWh/kg H2 |
| Wasserbedarf | 14 kg Wasser/kg produziertes H2 |
| Wasserpreis | 3,74 EUR_2023/m³ |
| Wasserdichte zur Umrechnung | 1.000 kg/m³ |
| isentroper Verdichtungsbedarf | 1,287 kWh/kg H2 |
| isentroper Wirkungsgrad | 80 % |
| mechanischer Wirkungsgrad | 90 % |
| effektiver Verdichtungsstrom | 1,7875 kWh/kg H2 |
| variable Wind-OPEX | 9 EUR_2023/MWh |
| variable PV-OPEX | 0 EUR_2023/MWh |

WACC und Lebensdauer bestimmen die Annualisierung. Gesonderter Stacktausch, zusätzliche Ersatzinvestitionsrechnung und Literatur-Teillastkennlinie sind nicht implementiert. `input_data/technology_costs.xlsx` und die WACC-Datenbank sind Quellen-/Vergleichsbestände; der normale Namibia-Lauf liest Komponentenwerte aus `config_h2.py`.

## 12. Szenarien

| ID / Ordner | Szenario im Code | Namibia-Regel | Rolle |
|---|---|---|---|
| S0 / `S0_reference` | `reference` | keine Zeitkorrelation | ökonomische Vergleichsbasis |
| S1 / `S1_red_monthly` | `red_monthly` | Deckung in jedem UTC-Kalendermonat | monatliche Stromzuordnung |
| S2 / `S2_red_hourly` | `red_hourly` | Deckung in jeder UTC-Stunde | stündliche Stromzuordnung |
| optional S3 / `S3_off_grid` | `off_grid` | kein Netzbezug | implementierte optionale Variante |

Der finale Vergleich und die 48 Sensitivitätsläufe enthalten **S0–S2**; S3 ist technisch verfügbar. Physischer Netzbezug bleibt für S1/S2 bei erfüllter erneuerbarer Zuordnung zulässig. Null Netzbezug im S2-Basisfall ist ein Optimierungsergebnis.

Die Differenz zwischen erneuerbarer Erzeugung und direktem Eigenverbrauch dient in S1 als vereinfachte zeitversetzte Überschuss-/PPA-Zuordnung. Für sie gibt es keinen Exporterlös und keine gesonderte Exportkapazitätsgrenze.

## 13. Sensitivitäten

Die Tabelle `input_data/h2_sensitivity_cases.csv` enthält einen Basisfall und 15 Varianten. Jeder Variantenfall ändert genau einen Parameter. Alle 16 Fälle wurden für S0, S1 und S2 gerechnet: **48 optimale Jahresläufe**.

| Parameter | Basis | Varianten |
|---|---:|---:|
| Strompreis | 128 EUR/MWh | 64 / 192 EUR/MWh, ±50 % |
| PEM-CAPEX | 1.297 EUR/kW | 972,75 / 1.621,25 EUR/kW, ±25 % |
| PEM-Strombedarf | 52,5 kWh/kg H2 | 47,25 / 57,75 kWh/kg H2, ±10 % |
| einheitlicher realer WACC | 11 % | 7 / 15 % |
| PV-CAPEX | 921 EUR/kW | 690,75 / 1.151,25 EUR/kW, ±25 % |
| Wind-CAPEX | 1.779,50 EUR/kW | 444,875 / 889,75 / 2.669,25 EUR/kW |
| H2-Speicher-CAPEX | 733,50 EUR/kg H2 | 550,125 / 916,875 EUR/kg H2, ±25 % |

Windwerte bei 25/50 % sind explorative Eintrittspunkte, keine Prognose oder Konfidenzintervalle. Der Runner validiert Fall-ID, Parameter, Wert, Einheit und Quelle vor der Optimierung. Konfigurationsvarianten verwenden Kopien; Strompreisvarianten erhalten separate validierte Stunden-CSV-Dateien. Der Basisdatensatz bleibt unverändert.

`sensitivity_comparison.csv` enthält Auslegung, LCOH, Betrieb, Emissionen sowie Abweichungen zum jeweiligen Szenario-Basisfall. `sensitivity_metadata.json` sichert Quell- und Tabellenhash, Ausgangswerte und Laufanzahl.

## 14. Datenpipeline und Ergebnisdateien

1. Koordinate, optionales Raster und Land festlegen.
2. PVGIS-TMY abrufen, Wetter prüfen und PV-/Windprofile berechnen.
3. Länderpreis, Netzfaktor und konstante H2-Nachfrage zuordnen.
4. die sechs Modellspalten als geprüfte UTC-Stunden-CSV speichern;
5. S0–S2 mit gemeinsamem Input und ausdrücklichem Namibia-WACC lösen;
6. gespeicherte CSV-/JSON-Ergebnisse unabhängig nachrechnen;
7. Hauptabbildungen und Einzelfaktor-Sensitivität auswerten.

Die sechs Spalten sind `timestamp`, `pv_capacity_factor`, `wind_capacity_factor`, `electricity_price`, `grid_emission_factor`, `h2_demand`; Einheiten: UTC, Anteil, Anteil, EUR/MWh, kg CO2e/MWh, kg H2/h. Der Validator verlangt eindeutige lückenlose Stunden und endliche Werte, Kapazitätsfaktoren 0–1 sowie nichtnegative Nachfrage/Faktoren. Negative Marktpreise wären zulässig, kommen hier aber nicht vor.

### Finale lokale Ablage, jeweils relativ zum Repository

```text
outputs_h2/namibia_case_study/
    namibia_input_1deg.csv
    namibia_input_1deg_metadata.json
    scenarios_wacc11/
        scenario_comparison.csv
        scenario_comparison_metadata.json
        S0_reference/, S1_red_monthly/, S2_red_hourly/
            validated_input.csv
            summary.csv
            hourly_operation.csv
            run_metadata.json
        validation/
            validation_report.json
            validation_checks.csv
            validation_samples.csv
        figures/
            01_lcoh_comparison.png ... 06_hourly_operation.png
            figure_manifest.json
    sensitivity_step14/
        sensitivity_comparison.csv
        sensitivity_metadata.json
        case_inputs/
        runs/<case_id>/<scenario>/
        figures/
            01_lcoh_sensitivity.png
            02_design_sensitivity.png
            03_wind_break_even.png
            sensitivity_figure_manifest.json
```

Standort-Metadaten sichern Koordinaten, TMY-Monate, Quellen, Einheiten, Bezugsjahre und Hashes; numerischer Runnerinput ist die Stunden-CSV. `outputs_h2/` ist von Git ausgeschlossen. Für eine historische Reproduktion müssen diese lokalen Ergebnisse separat erhalten beziehungsweise bereitgestellt werden.

## 15. Daten- und Ergebnisvalidierung

### Historische Abnahme

Der Modellstand wurde am **12. September 2026** mit **163 bestandenen automatisierten Tests** abgenommen. Die Tests umfassen Konfiguration, Einheiten, Datenprüfung, Komponentenbilanzen, Solverpfade, RED-Grenzfälle, Integration, Szenarien, Sensitivität, Darstellungen und den unabhängigen Validator.

Darunter waren 28 spezifische RED-Grenzfalltests. Frühere Zwischenstände berichteten 151 Tests; das ist ein Entwicklungsstand, kein Widerspruch zur späteren 163er-Abnahme. Aachen und Madrid lieferten im damaligen realen PVGIS-Übertragbarkeitstest jeweils 8.760 vollständige UTC-Stunden.

163 ist ein historisches Testergebnis. Die Reorganisation führte kein `pytest` aus; neue europäische Eingaben oder spätere Änderungen sind damit nicht geprüft.

### Gespeicherte unabhängige Prüfung

`validation_report.json` dokumentiert 61 Prüfungen für drei Szenarien, **61 bestanden**, null fehlgeschlagen, jeweils 8.760 erwartete Stunden. Der Bericht wurde am 12. September 2026 um 22:45:10 UTC erzeugt.

Nachgerechnet wurden Stundenachse, gemeinsamer Eingabehash, Strom- und zyklische H2-Bilanz, Elektrolyseumwandlung, Verdichtungsstrom/-verlust, Kapazitätsgrenzen, H2-Liefermenge, Jahreskosten, LCOH, betriebliche/regulatorische Emissionen und Zeitkorrelation.

| Größe | Größtes gespeichertes unabhängiges Residuum | Prüftoleranz |
|---|---:|---:|
| stündliche Strombilanz | 1,8207658 × 10⁻¹⁴ MWh | 10⁻⁶ MWh |
| zyklische H2-Speicherbilanz | 2,2293989 × 10⁻¹⁰ kg | 10⁻⁴ kg |
| jährliche Kosten | numerische Rundungsabweichung im Mikro-EUR-Bereich | 0,05 EUR |
| relative Vergleiche | gemäß Prüfreport | 10⁻⁸ |

Interne Solverresiduen sind teils null; die unabhängige CSV-Nachrechnung findet kleine Rundungsresiduen weit unter den Toleranzen. Die lesende Prüfung dieser Belege bei der Reorganisation ist keine erneute Modellabnahme oder Bestätigung externer RED-Nachweise.

## 16. Implementierungs- und Entwicklungshistorie

| Schritte | Historischer Beitrag | Abschluss-/Nachweisstand |
|---|---|---|
| 1 | Python-3.11-Umgebung, kleiner Gurobi-Lauf, Ausgangscodeprüfung | damalige Umgebung funktionsfähig; `main` blieb erhalten |
| 2–3 | Parameter, Systemgrenze und standardisierte Stunden-CSV | am 10. September 2026 abgeschlossen |
| 4–5 | linearer H2-Kern und ausführbarer Einzellauf | zuerst künstliche 24-Stunden-Fälle |
| 6 | PVGIS, Länderzuordnung, Preis-/Faktoradapter und optionales Raster | reale Koordinaten geprüft, Metadaten gesichert |
| 7 | 168-Stunden- und 8.760-Stunden-S0, SciPy/HiGHS-Pfad | Jahreslauf wiederholt; numerische Ergebnisse identisch |
| 8 | eigenständige RED-Daten und unabhängiger Prüfer | 28 Grenzfälle; Strombedarf einschließlich Verdichtung |
| 9 | monatliche Korrelation in beiden Solverpfaden | unabhängige Monatskontrolle |
| 10 | stündliche Korrelation | am 12. September abgeschlossen; Stundenkontrolle |
| 11 | betriebliche/regulatorische Emissionen und THG-Teiltest | Grenzwertfälle in beiden Solverpfaden geprüft |
| 12 | gemeinsamer S0/S1/S2-Runner | identische Eingaben, getrennte Ausgabeordner |
| 13 | sechs Hauptabbildungen mit Quellenmanifest | automatisiert und visuell geprüft |
| 14 | tabellengesteuerte Einzelfaktor-Sensitivität | 16 × 3 = 48 Jahresläufe |
| 15 | unabhängige Gesamtvalidierung und Übergabe | 163 Tests, 61/61 Ergebnisprüfungen |
| 16 | wissenschaftlicher Methodiktext | am 13. September abgeschlossen |
| 17 | zahlenbasierte Namibia-Interpretation | am 14. September abgeschlossen |

`calculate_renewable_yield.py` blieb als benötigter Ertragsbaustein erhalten. H2-Bilanzen, Konfiguration, RED-Logik und Runner wurden als eigenständige Module umgesetzt. ASU, Haber-Bosch, NH3-Nachfrage/-Transport und alte LCA-/Stickstoffbestände gehören nicht zum H2-Kern.

Der frühere Datenprozessor erforderte beim Import die nicht versionierte Datei `input_data/ghg_factors.json`. Diese versteckte Abhängigkeit wurde nicht übernommen. Die benötigte Länder-/Rasterlogik wurde fachlich getrennt implementiert; fehlende Ammoniak-LCA-Daten wurden nicht rekonstruiert.

### Solverwahl und Vergleich

Der 168-Stunden-Referenzfall wurde mit Gurobi optimal gelöst. Die lokal größenbeschränkte Gurobi-Lizenz lehnte den vollständigen 8.760-Stunden-Fall ab. Daraufhin wurde für dasselbe kontinuierliche LP der SciPy/HiGHS-Pfad implementiert.

Ein automatisierter 24-Stunden-Vergleich ergab gleiche Zielfunktion, LCOH und Kapazitäten für beide Solver. Der frühere vollständige S0-Lauf mit SciPy/HiGHS wurde numerisch identisch wiederholt; nur die Rechenzeit änderte sich. Die finalen `scipy_highs`-Jahresläufe sind optimal, mit exportierter Lücke null; damalige Laufzeiten: S0 11,24 s, S1 8,36 s, S2 9,72 s.

Gespeicherte Softwareversionen des finalen S2-Laufs: Python 3.11.15, pandas 3.0.5, SciPy 1.17.1 und Gurobi 13.0.3. `environment_h2.yml` beschreibt die Python-3.11-Umgebung; Paketmindestversionen allein frieren nicht jede historische Installation exakt ein.

Die frühere README dokumentiert außerdem folgende **damals in Schritt 1 geprüfte Umgebung**:

| Paket | Historisch dokumentierte Version |
|---|---:|
| Python | 3.11.15 |
| NumPy | 2.4.6 |
| pandas | 3.0.5 |
| xarray | 2026.7.0 |
| openpyxl | 3.1.5 |
| Matplotlib | 3.9.4 |
| SciPy | 1.17.1 |
| pvlib | 0.15.2 |
| windpowerlib | 0.2.2 |
| pycountry | 26.2.16 |
| pytest | 9.1.1 |
| gurobipy | 13.0.3 |
| spyder-kernels | 3.0.5 |

Dies ist kein heutiger Installationstest oder exakter Lockfile-Nachweis.
Insbesondere PV-/Windbibliotheken sind für die Profilreproduktion relevant.
Die frühere Umgebungskontrolle meldete eine Nichtproduktionslizenz mit Ablauf
29. November 2027 und Größenbeschränkung; ihr heutiger Status wurde nicht neu geprüft.

### Git-Ausgangsstand

Die frühere README nannte `c3286cb` als damaligen gemeinsamen Ausgangscommit von
`main` und `h2-single-site`. Dies ist historische Herkunft, keine Behauptung des
heutigen Branch-HEAD. Laut Entscheidungsprotokoll wurde der H2-Branch am
15. September 2026 synchronisiert; die frühere Absicht „zunächst kein Push“ wurde
damit durch eine spätere Uploadentscheidung ergänzt. Die Reorganisation führt
keinen Commit, Push oder Branchwechsel aus.

### Vorläufige technische Referenzergebnisse aus Schritt 7

| Kennzahl | 168 Stunden | 8.760 Stunden |
|---|---:|---:|
| LCOH [EUR/kg H2] | 4,819381 | 4,989748 |
| PV [MW] | 100,917 | 100,179 |
| Wind [MW] | 0 | 0 |
| PEM [MW] | 63,315 | 63,267 |
| Kompressor [MW] | 2,156 | 2,154 |
| H2-Speicher [kg] | 5.847,001 | 6.239,817 |

Diese Werte nutzen exakte Koordinate, 350er-Testfaktor und Literatur-WACC 5/7 %; der 168-Stunden-Lauf annualisiert mit 52,142857. Die LCOH 4,99 ist kein finales 11-%-Pixelresultat. Dateien: `outputs_h2/namibia_input.csv`, `outputs_h2/namibia_input_metadata.json`, `outputs_h2/step7_namibia_reference/` mit `run_168h/`, `run_8760h/` und `run_8760h_repeat/`.

Weitere Zwischenstände liegen unter `outputs_h2/step9_namibia_red_monthly*`, `outputs_h2/step10_namibia_red_hourly/`, `outputs_h2/step11_namibia_*` und `outputs_h2/step12_namibia_comparison/`. Sie dokumentieren Entwicklungsstufen; die finalen Kennzahlen dieses Dokuments stammen ausschließlich aus `namibia_case_study/`.

Beim damaligen technischen RED-Schnittstellentest verletzte das unbeschränkte S0-Ergebnis 11 Monats- beziehungsweise 380 Stundenkorrelationen. Das war ein technischer Prüfernachweis unter testweise gesetzten externen Annahmen, keine regulatorische Standortbewertung.

Die frühere Schlussaussage, nach Schritt 17 folge Literaturdiskussion als Schritt 18, ist historisch. Seit der Umfangsänderung heißen Schritt 18 Methodikentscheidung und Schritt 19 Datenumsetzung; Diskussion/Ausblick liegen nun in Schritt 25.

## 17. Finale Ergebnisse

Alle folgenden Zahlen beziehen sich auf das 1°-Pixel −21,5° / 14,5°, den 128er-Preisproxy, 220 kg CO2e/MWh und 11 % realen WACC. Abgabe und Komponentenbasis sind in allen drei Szenarien gleich.

### Auslegung, Betrieb und Emissionen

| Kennzahl | S0 Referenz | S1 monatlich | S2 stündlich |
|---|---:|---:|---:|
| LCOH [EUR/kg H2] | 6,965735 | 7,032868 | 7,426891 |
| Änderung gegenüber S0 | 0 % | +0,963752 % | +6,620350 % |
| annualisierte Kosten [Mio. EUR/a] | 25,424934 | 25,669967 | 27,108154 |
| PV [MW] | 36,496640 | 97,265074 | 102,727119 |
| Wind [MW] | 0 | 0 | 0 |
| PEM [MW] | 24,678018 | 61,404174 | 63,870707 |
| Kompressor [MW] | 0,840228 | 2,090666 | 2,174646 |
| H2-Speicher [t] | 0,274894 | 5,729176 | 18,482348 |
| Speicher in Stunden mittlerer Nachfrage | 0,66 | 13,75 | 44,36 |
| PV-Erzeugung [GWh/a] | 74,781 | 213,075 | 225,041 |
| direkter PV-Verbrauch [GWh/a] | 74,781 | 191,275 | 199,145 |
| PV-Überschuss-/Zuordnungsmenge [GWh/a] | 0 | 21,800 | 25,896 |
| physischer Netzbezug [GWh/a] | 124,364 | 7,870 | 0 |
| Netzanteil am Prozessstrom | 62,45 % | 3,95 % | 0 % |
| PEM-Vollbenutzungsstunden [h/a] | 7.804 | 3.136 | 3.015 |
| Stunden mit PEM-Betrieb | 8.760 | 4.519 | 4.251 |
| betriebliche Emissionen [t CO2e/a] | 27.360,048 | 1.731,469 | 0 |
| betriebliche Intensität [kg CO2e/kg H2] | 7,495904 | 0,474375 | 0 |
| regulatorische Intensität [kg CO2e/kg H2] | 7,495904 | 0 | 0 |
| regulatorische Minderung zum Vergleichswert | 33,55 % | 100 % | 100 % |
| THG-Teiltest | nicht bestanden | bestanden | bestanden |
| geprüfte Korrelationsperioden | nicht angewandt | 12 | 8.760 |
| maximale zeitliche Fehlmenge [MWh] | nicht angewandt | 0 | 0 |

Die winzige negative betriebliche Intensität in der gespeicherten S2-Zeile, etwa −9 × 10⁻¹⁸ kg/kg, ist numerisches Rauschen und wird hier als null dargestellt.

### Kostenbeiträge

| Beitrag [EUR/kg H2] | S0 | S1 | S2 |
|---|---:|---:|---:|
| PV | 1,210 | 3,225 | 3,407 |
| Wind | 0 | 0 | 0 |
| PEM | 1,145 | 2,850 | 2,964 |
| Kompressor | 0,189 | 0,469 | 0,488 |
| H2-Speicher | 0,008 | 0,160 | 0,515 |
| Netzstrom | 4,361 | 0,276 | 0 |
| Wasser | 0,053 | 0,053 | 0,053 |

Gerundete Einzelbeiträge können von der Summe in den letzten Nachkommastellen abweichen. Annualisierte CAPEX und fixe/variable OPEX sind separat in den jeweiligen `summary.csv` gespeichert.

### Vollständiger LCOH-Vergleich der Sensitivitätsfälle

| Fall-ID | S0 [EUR/kg] | S1 [EUR/kg] | S2 [EUR/kg] | S2-Änderung zum Basisfall |
|---|---:|---:|---:|---:|
| `baseline` | 6,965735 | 7,032868 | 7,426891 | 0 % |
| `electricity_price_low` | 4,593095 | 6,518265 | 7,426891 | 0 % |
| `electricity_price_high` | 7,121195 | 7,133605 | 7,426891 | 0 % |
| `electrolyzer_capex_low` | 6,354624 | 6,399373 | 6,772443 | −8,812 % |
| `electrolyzer_capex_high` | 7,191071 | 7,648615 | 8,077321 | +8,758 % |
| `electrolyzer_energy_low` | 6,310705 | 6,409267 | 6,800950 | −8,428 % |
| `electrolyzer_energy_high` | 7,614015 | 7,656305 | 8,052524 | +8,424 % |
| `wacc_low` | 5,295876 | 5,308106 | 5,550433 | −25,266 % |
| `wacc_high` | 7,583736 | 8,855516 | 9,459743 | +27,371 % |
| `pv_capex_low` | 6,318298 | 6,320049 | 6,672425 | −10,159 % |
| `pv_capex_high` | 7,196525 | 7,738567 | 8,168075 | +9,980 % |
| `wind_capex_quarter` | 6,715808 | 6,956672 | 7,404772 | −0,298 % |
| `wind_capex_half` | 6,965563 | 7,032694 | 7,426891 | 0 % |
| `wind_capex_high` | 6,965735 | 7,032868 | 7,426891 | 0 % |
| `storage_capex_low` | 6,958229 | 6,992626 | 7,297470 | −1,743 % |
| `storage_capex_high` | 6,966423 | 7,072733 | 7,551744 | +1,681 % |

### Wind-Eintritt

| Wind-CAPEX [EUR/kW] | S0 Wind [MW] | S1 Wind [MW] | S2 Wind [MW] |
|---|---:|---:|---:|
| 444,875, 25 % | 28,0225 | 19,0208 | 19,9767 |
| 889,750, 50 % | 0,8973 | 0,6547 | 0 |
| 1.779,500, 100 % | 0 | 0 | 0 |
| 2.669,250, 150 % | 0 | 0 | 0 |

In S2 liegt der Eintrittspunkt zwischen den getesteten 444,875 und 889,75 EUR/kW. Ein exakter Schwellenwert wurde nicht bestimmt. S0/S1 bauen bei 50 % bereits kleine Windleistungen; die Aussage „bei halben Kosten kein Wind“ gilt nur für S2.

### Vorhandene Abbildungen

Die sechs Hauptplots zeigen LCOH, Kapazitäten, Kosten, Betriebsindikatoren, Emissionen/THG-Teiltest und Stundenbetrieb (Dateien: Abschnitt 14). `figure_manifest.json` sichert Quellhashes, 180 dpi und **10. Februar 2025, 00:00 UTC bis 16. Februar 2025, 23:00 UTC**, 168 Stunden. Sensitivitätsplots zeigen LCOH, Auslegungsänderungen und Wind-Eintritt. Die historische visuelle Prüfung wurde bei der Reorganisation nicht wiederholt.

## 18. Interpretation und übertragbare Erkenntnisse

**S0:** Der Elektrolyseur läuft in allen Stunden, mit rund 7.804 Vollbenutzungsstunden. 62,45 % des Prozessstroms kommen aus dem Netz. Das reduziert die erforderlichen Anlagen- und Speicherkapazitäten, verursacht aber 7,496 kg CO2e/kg H2 und überschreitet den modellierten THG-Grenzwert.

**S1:** Gegenüber S0 steigen PV um rund 167 % und PEM um rund 149 %. Der Speicher wächst auf 5,729 t. Netzbezug fällt um 93,7 %, während die LCOH nur um 0,067 EUR/kg beziehungsweise 0,96 % steigen. Mehr annualisierte Anlagenkosten werden durch niedrigere Netzstromkosten weitgehend ausgeglichen.

Die 21,800 GWh Überschuss-/Zuordnungsmenge ermöglicht im Monatsfenster den regulatorischen Ausgleich einzelner physischer Netzstunden. Deshalb ist die betriebliche Intensität 0,474 kg/kg, während die regulatorische Stromkomponente null beträgt.

**S2:** Gegenüber S1 wachsen PV um rund 5,6 %, PEM um 4,0 % und Speicher um 222,6 %. Der Speicher deckt rund 44,4 Stunden mittlere Nachfrage. Produktion konzentriert sich auf 4.251 Betriebsstunden; der Netzbezug fällt auf null. LCOH steigen gegenüber S1 um rund 5,6 % und gegenüber S0 um 6,62 %.

Der strengere Stundenabgleich entkoppelt PV-Produktion und konstante H2-Abgabe über größeren H2-Speicher. Die operative und regulatorische Stromkomponente ist null; die fehlenden Anlagen-/Vorkettenemissionen werden dadurch nicht nachgewiesen.

In S0 trägt Netzstrom rund 62,6 % der Gesamtkosten. In S1/S2 tragen PV rund 45,9 % und PEM rund 40 %. Der S2-Speicher trägt 0,515 EUR/kg beziehungsweise 6,9 %. Das Kostenrisiko verschiebt sich damit von Netzstromausgaben zu kapital- und finanzierungsabhängigen Kosten.

Der WACC ist in S2 der stärkste untersuchte Treiber: 7–15 % ergeben LCOH von 5,550 bis 9,460 EUR/kg. PV-CAPEX, PEM-CAPEX und PEM-Strombedarf folgen. Strompreisvariationen beeinflussen diesen S2-Basisfall nicht, weil er keinen Netzstrom nutzt.

S0 reagiert asymmetrisch auf den Preis: Halbierung senkt LCOH um 34,06 %, Erhöhung auf 192 EUR/MWh steigert sie nur um 2,23 %. Der Optimierer wechselt seine Versorgungsstrategie. Das ist keine lineare Preiselastizität. In S1 betragen die entsprechenden Änderungen −7,32 % und +1,43 %.

Wind ist technisch aktiv, wird bei Basiskosten aber wirtschaftlich nicht gewählt. Die explorativen Fälle zeigen seinen Eintritt. Null Windleistung belegt weder einen Programmfehler noch eine generelle Überlegenheit von PV an anderen Standorten.

Übertragbar sind die Modellstruktur, validierte Bilanzlogik und der Bedarf, Kostenaufschläge gemeinsam mit Auslegung und Betrieb zu interpretieren. Pixel, TMY-Auswahl, konstanten Preis, 220er-Faktor, 11-%-WACC, Nachfrageannahme und Namibia-Sensitivitätsbänder müssen andere Fallstudien separat begründen.

## 19. Limitationen und ungeklärte Nachweise

Die allgemeinen Modellgrenzen stehen in [MODELL_UND_METHODIK.md](../MODELL_UND_METHODIK.md). Für Namibia sind folgende Punkte besonders relevant:

- 1°-Pixel und 58,44-km-Abstand begrenzen die lokale Repräsentativität.
- TMY und 2025-Index sind kein zusammenhängendes beobachtetes Markt-/Wetterjahr.
- Landespreis und Jahresnetzfaktor verdecken stündliche und lokale Unterschiede.
- Preisjahrkonsistenz des 128er-Proxys bleibt **UNGEKLÄRT**.
- 11 % WACC ist regional; Finanzierungsjahr und projektspezifische Konditionen sind nicht belegt.
- Der PPA-/Überschusspfad hat keine Exportvergütung, separate Exportgrenze oder Transaktions-/Netzkosten.
- RED-Gebiet, Zusätzlichkeit, Vertragsweg, Förderung, Allokation und Zertifizierung sind **UNGEKLÄRT beziehungsweise extern offen**.
- Anlagenemissionen und weitere Vorketten fehlen; null Stromemissionen bedeuten keinen vollständigen Product Carbon Footprint.
- Technik nutzt konstante Effizienz, kontinuierliche Kapazitäten und vereinfachte Verluste; Mindestlast, Anfahren, Druckdynamik und Degradation fehlen.
- Nachfrage ist konstant und keine Standortmessung; Wechselwirkungen unsicherer Parameter wurden nicht untersucht.
- Wetterstreuung, Last-/Preisprognosefehler, Netzanschluss, Fläche, Genehmigung und Wasseraufbereitung sind nicht untersucht.

**UNGEKLÄRT – vollständige Softwarebindung:** Die Ergebnisdateien enthalten Input-, Quellen- und Tabellenhashes sowie Softwareversionen, aber keinen ausgewiesenen Git-Commit des gesamten ausführbaren Modellstands. Git-Historie und damalige Umgebung sind für eine exakte Software-Rekonstruktion zusätzlich erforderlich.

## 20. Reproduzierbarkeit

Alle folgenden Befehle beziehen sich auf **`C:\Forschungsarbeit\Opt_H2_Meric-h2`** und dokumentieren eine spätere Reproduktion. Sie wurden für diese Reorganisation nicht ausgeführt.

### Umgebung

In der Anaconda Prompt (`cmd`):

```bat
cd /d C:\Forschungsarbeit\Opt_H2_Meric-h2
conda env create -f environment_h2.yml
conda activate h2-model
python --version
```

Bei vorhandener Umgebung genügt die Aktivierung. Für Spyder war `C:\Users\meric\anaconda3\envs\h2-model\python.exe` als Interpreter vorgesehen; danach Kernel neu starten. In PowerShell lautet der Verzeichniswechsel `Set-Location -LiteralPath 'C:\Forschungsarbeit\Opt_H2_Meric-h2'`.

### Gespeicherte Eingabe verwenden und Kernszenarien reproduzieren

```bat
python run_h2_scenarios.py --input outputs_h2\namibia_case_study\namibia_input_1deg.csv --output-dir outputs_h2\namibia_case_study\reproduction\scenarios_wacc11 --solver scipy-highs --uniform-real-wacc 0.11 --wacc-source "Regionalfallback Subsahara-Afrika nach ursprünglicher Modelllogik"
python validate_h2_results.py --results-dir outputs_h2\namibia_case_study\reproduction\scenarios_wacc11 --expected-hours 8760
python plot_h2_results.py --results-dir outputs_h2\namibia_case_study\reproduction\scenarios_wacc11 --start 2025-02-10 --hours 168
```

Die gespeicherte Eingabe vermeidet einen neuen Wetterabruf. Der getrennte Reproduktionsordner erhält den historischen Bestand. Existieren Zielausgaben bereits, verweigern die Werkzeuge die Überschreibung; die ausdrücklich gewählte Option `--overwrite` würde sie ersetzen.

### Datenaufbereitung für denselben Namibia-Fall

```bat
python prepare_single_site_h2_input.py --latitude -21.0800 --longitude 14.1610 --country-code NA --spatial-resolution 1 --output outputs_h2\namibia_case_study\reproduction\namibia_input_1deg.csv
```

Dieser Abruf benötigt Internet und nutzt die hinterlegten Preis-/Faktorbestände. Ein neuer PVGIS-Abruf muss mit den historischen Metadaten und Hashes verglichen werden; identische Koordinaten allein garantieren keinen byteidentischen Datensatz.

Für einen ausdrücklich gesetzten Netzfaktor unterstützt die aktuelle CLI `--grid-emission-factor 220 --grid-emission-source "Electricity Control Board of Namibia, Integrated Annual Report 2025; Berichtsjahr 2024"`. Strompreis-, Wetter- und Netzfaktor-CSV können ebenfalls ausdrücklich übergeben werden.

### Sensitivitätsbestand reproduzieren

```bat
python run_h2_sensitivity.py --input outputs_h2\namibia_case_study\namibia_input_1deg.csv --cases input_data\h2_sensitivity_cases.csv --output-dir outputs_h2\namibia_case_study\reproduction\sensitivity_step14 --scenarios all --solver scipy-highs --base-uniform-real-wacc 0.11 --base-wacc-source "Regionalfallback Subsahara-Afrika nach ursprünglicher Modelllogik"
python plot_h2_sensitivity.py --comparison outputs_h2\namibia_case_study\reproduction\sensitivity_step14\sensitivity_comparison.csv --scenario red_hourly
```

Eine spätere erneute Softwareprüfung verwendet `python -m pytest -q`. Das historische 163er-Ergebnis darf erst nach einem solchen Lauf als aktuelles Testergebnis bezeichnet werden.

### SHA-256-Belege

Die vorhandenen Dateien wurden bei der Reorganisation lesend gehasht; die folgenden drei Hashes stimmen mit den gespeicherten Belegen überein:

| Datei / Bedeutung | SHA-256 |
|---|---|
| finale `namibia_input_1deg.csv` | `cfadb75437dff6a3eac0f163db604226c37f2fb327c1b23370c163b71446bb41` |
| finale `scenario_comparison.csv` | `56b1fa7d06d4000deb646804ad7ef3ded3db2b8b2b6a56d63a4c0716a9de2a77` |
| `h2_sensitivity_cases.csv` | `f51f84ed8279aed90ebeaf85c2aa14520a9d69760c5dc0f892b6e9d73af9cb7e` |

Zusätzliche historische Belege in den Metadaten:

| Quelle | gespeicherter SHA-256 |
|---|---|
| vorläufige exakte-Koordinaten-Eingabe | `ce2a92c304304817639bcd8b264d417c89b60ff0d42f0eedba9603b7fc8aead7` |
| Gewerbestrompreis-Quelldatei | `1c02bc82860027561a1e8d39080e21fbb4e48010a81732835216ca4a4a00baaa` |
| Länder-Netzfaktor-Quelldatei | `667c4c4c05500aa391e2b257c549d5453ae7dd4abbb7de29644995f7fb38f559` |
| S0-Stundenquelle im Hauptplotmanifest | `c45d10c56b7c9a69d0666e321bcefb2d4169f7cae06a708cec5aa89a49aa9fdc` |
| S1-Stundenquelle im Hauptplotmanifest | `9125e6bb19366fb53392d52326094a968052d745713e972ea631756c6e6ba9a7` |
| S2-Stundenquelle im Hauptplotmanifest | `2bb9e7e2140feff82e355546060e2ed643cbc3eea165eef156b464268af223a8` |

### Manuell lesbare Stundenbeispiele

Aus `validation_samples.csv`, S0, 1. Januar 2025, 00:00 UTC:

```text
Strom: PV 0 + Wind 0 + Netz 25,518246
       = PEM 24,678018 + Kompressor 0,840228 MWh
H2:    alter Speicher 0 + H2 nach Verdichtung 467,707197
       − Nachfrage 416,666667 = neuer Speicher 51,040530 kg
```

S2, 1. Januar 2025, 09:00 UTC, ebenfalls aus `validation_samples.csv`:

```text
Strom: PV 66,045353 = PEM 63,870707 + Kompressor 2,174646 MWh
H2:    alter Speicher 4.333,363867 + H2 nach Verdichtung 1.210,501978
       − Nachfrage 416,666667 = neuer Speicher 5.127,199179 kg
```

Die Produktionsmengen dieser Speicherbeispiele sind **nach** dem 0,5-%-Verdichtungsverlust. Sie dürfen nicht als rohe PEM-Produktion bezeichnet werden. Rundungsdifferenzen entstehen durch die dargestellten Nachkommastellen.

## 21. Quellen und Herkunft der Konsolidierung

### Fachliche und historische Quellen

- Brandt et al. (2024): *Cost and competitiveness of green hydrogen and the effects of the European Union regulatory framework*, Nature Energy 9, 703–713, [DOI 10.1038/s41560-024-01511-z](https://doi.org/10.1038/s41560-024-01511-z). Komponenten: Supplementary Tables 2–4; Nachfrage: Figure 4 und Supplementary Note 2.
- [PVGIS / Joint Research Centre](https://re.jrc.ec.europa.eu/pvg_tools/en/): TMY-Auswahl 2007–2016; konkreter Abruf und Monatsauswahl in `namibia_input_1deg_metadata.json`.
- [GlobalPetrolPrices, Namibia electricity prices](https://www.globalpetrolprices.com/Namibia/electricity_prices/): Herkunft des gespeicherten Gewerbestrompreis-Proxys; für die historischen Werte ist der gehashte lokale Bestand maßgeblich.
- [Electricity Control Board, Integrated Annual Report 2025](https://www.ecb.org.na/wp-content/uploads/2025/12/ECB_IAR_2025_web.pdf): Namibia-Netzfaktor für 2024; Umrechnung in `h2_country_factors.json` dokumentiert.
- Steffen-et-al.-WACC-Datenbestand und ursprüngliche Ammoniak-Modelllogik: Prüfung fehlenden Namibia-Eintrags und regionaler Subsahara-Fallback. Das Ergebnis ist ein Modellproxy; kein neuer Länderwert wird daraus behauptet.
- [Richtlinie (EU) 2023/2413](https://eur-lex.europa.eu/eli/dir/2023/2413/oj), [Delegierte Verordnung (EU) 2023/1184](https://eur-lex.europa.eu/legal-content/DE/TXT/?uri=CELEX:32023R1184), [Delegierte Verordnung (EU) 2023/1185](https://eur-lex.europa.eu/legal-content/DE/TXT/?uri=CELEX:32023R1185): historisch dokumentierte Rechtsbasis des Modellstands.

Diese Quellenlinks wurden aus den vorhandenen Dokumenten und Metadaten übernommen. Bei der Reorganisation wurden keine neuen Webquellen oder geänderten Parameter eingeführt.

### Übernommene interne Dokumentation

| bisheriges Dokument | hier gesicherte Namibia-Information |
|---|---|
| `Forschungsarbeitplan.md` | Schritte 1–17, ursprünglicher technischer Stand, Solververgleich, Abnahme und Entscheidungen |
| `METHODIK_UND_MODELLFORMULIERUNG.md` | konkrete Namibia-Daten, TMY/Indexjahr, Komponentenbasis und Fallgrenzen |
| `MODELLUEBERGABE.md` | Umgebung, CLI, Ergebnisorte, 61er-Prüfung und manuelle Bilanzen |
| `MODELLABLAUF_EINFACH_ERKLAERT.md` | vollständige Ein-/Ausgabeübergaben, Quellenrollen und Ausführungsfolge |
| `ERGEBNISINTERPRETATION.md` | Kernergebnisse, Kostenstruktur, Sensitivitätsinterpretation und Wind-Eintritt |
| `MODELLGRENZEN.md` | technische, räumliche, wirtschaftliche und regulatorische Aussagegrenzen |
| bisherige `README.md` | Überblick, Herkunft aus dem Ammoniakmodell, Module und Entwicklungsstand |

Die bisherigen Dateinamen in dieser Tabelle sind Herkunftsangaben, keine aktiven Navigationsziele. Allgemeine Inhalte wurden in [MODELL_UND_METHODIK.md](../MODELL_UND_METHODIK.md) konzentriert.

Die konkrete Ergebnisherkunft bilden `namibia_input_1deg_metadata.json`, `scenario_comparison.csv`, drei `summary.csv`/`hourly_operation.csv`/`run_metadata.json`, der 61er-Prüfbericht, `sensitivity_comparison.csv` und die beiden Abbildungsmanifeste unter den in Abschnitt 14 genannten Repositorypfaden.

## 20. Gemeinsame Diagnose- und Grafikdarstellung mit den EU-Fällen

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

Die Namibia-Eingaben und alle 48 historischen Sensitivitätsresultate bleiben unverändert. Die neue Preis-/WACC-Schreibweise ist dort algebraisch identisch mit 64/192 EUR/MWh und 7/15 % aus dem bisherigen Programm. Es waren keine neuen Namibia-Optimierungen erforderlich.

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
