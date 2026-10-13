# Wissenschaftliche Durchsicht von D1 und Kriterien für U1

**Stand: 11. Oktober 2026 · Fachlicher Review der lokalen Arbeitskopie; keine Produktabnahme.**

Der aktuelle Nutzerauftrag ist die Fortsetzung des nächsten Schritts mit wissenschaftlich sinnvollen Oberflächen und Analysen. Die Durchsicht bestätigt die fünf Hauptbereiche und acht Analyseziele von D1. Der Mehrwert entsteht durch beantwortbare Forschungsfragen, kontrollierte Vergleiche, nachvollziehbare Wirkungen und reproduzierbare Daten. Zusätzliche Diagramme allein begründen keinen Mehrwert.

Die Bewertung verwendet ausschließlich die lokale [Methodik](MODELL_UND_METHODIK.md), insbesondere Abschnitte 5–8, den [Oberflächenentwurf](GUI_OBERFLAECHENENTWURF.md) und den [Neuaufbauplan](GUI_NEUAUFBAU_PLAN.md), insbesondere Abschnitte 5, 7 und 13. Sie ist keine neue Rechtsprüfung und ändert weder Modellgleichungen noch Quellen- oder Jahresgrundlagen. Die genannten Kriterien sind Anforderungen für Umsetzung und Prüfung, keine bereits bestandenen Nachweise.

## 1. Forschungsfragen und wissenschaftlicher Nutzen

| Untersuchung | Kontrollierte Frage | Wirkung und Erklärung | Aussagegrenze |
|---|---|---|---|
| Szenarien S0/S1/S2, optional S3 | Wie wirken die implementierten Stromregeln bei gleichem Standort, Profil, Jahresmenge und sonstigen Annahmen? | LCOH/Jahreskosten; Auslegung, Netzbezug und Kostenbestandteile erklären Unterschiede. | Modellierter Regelsatz; keine vollständige Projektzertifizierung oder Prognose eines Inbetriebnahmejahrs. |
| Lieferprofile D0/D1/D2 | Wie wirkt die zeitliche Pflichtlieferung bei gleicher Jahresmenge? | LCOH und Speicher; Lieferstunden, geforderte Stundenabnahme sowie Produktion/Lieferung verdeutlichen den Mechanismus. | Synthetische Nachfrage; Lieferfenster sind keine Produktionsverbote. Eine separate Tankentnahmeleistungsgrenze fehlt im Modell. |
| Numerische OAT | Wie reagiert das Ergebnis auf genau eine dokumentierte Intervention? | Tatsächlicher Parameterwert, eigene Basis, absolute und gegebenenfalls relative Ergebnisänderung. | Kein Kreuzversuch, keine Interaktionsanalyse und keine statistische Unsicherheitsverteilung. |
| Nachfragemenge | Wie skaliert die kostenoptimale Neuauslegung im vorliegenden Modell? | Jahreskosten, Kapazitäten und Betrieb; Skalierung und Mengenbilanzen prüfen. | Keine industrielle Größendegression, empirische Nachfrageprognose oder Engpassprüfung einer festen Bestandsanlage. |
| Emissionen | Wie unterscheiden sich physischer Netzimport und regulatorische Stromzuordnung? | Getrennte betriebliche und regulatorische elektrische Teilintensitäten; spezifischer Netzbezug als erklärende Größe. | Statischer Länderfaktor, keine marginale Netzintensität, keine vollständige Produkt-LCA. |
| Tagesbetrieb | Wie erfüllt ein exakter Ergebnisfall die Strom- und H₂-Bilanzen im ausgewählten Zeitfenster? | Direktversorgung, Bedarf, Produktion, Lieferung und Speicher; stündlich oder kumulativ mit passenden Einheiten. | Ein Beispieltagesverlauf ist kein Nachweis eines repräsentativen Jahres oder vollständiger technischer Betriebsfähigkeit. |
| Standortvergleich | Welche Unterschiede entstehen auf den ausgewählten dokumentierten Grundlagen? | Gleiche und unterschiedliche Annahmen offenlegen; Kosten, Auslegung und Betrieb gezielt gegenüberstellen. | Namibia/TMY und EU 2024 liefern keinen isolierten Standorteffekt; ein historisches Jahr belegt keine mehrjährige Robustheit. |
| Solververgleich | Sind Kostenminimum und physische Lösung unter identischen Modelleingaben numerisch reproduzierbar? | Kosten, eigener Prüfstatus und Laufzeit; Kapazitäten zur Erklärung alternativer Optima. | Einzelne Laufzeiten sind kein allgemeiner Leistungsbenchmark; unterschiedliche Kapazitäten bei gleichem Optimum sind nicht automatisch ein Fehler. |

## 2. Priorisierte fachliche Präzisierungen

### P1 · Vergleichsidentität und OAT-Basis

Ein kontrollierter Szenarienvergleich hält Standort, Profil, tatsächliche Jahreslieferung, Modellkalender, Technik, Preis- und Finanzierungsgrundlagen sowie Solver konstant. Ein Profilvergleich verändert das Lieferprofil bei gleicher Jahreslieferung. Eine numerische OAT verändert genau die deklarierte Parameterfamilie; mehrere Parameter ergeben getrennte Reihen. Beim Solververgleich ist ausschließlich der Solver die angekündigte Variation. Freie Mischvergleiche werden ausdrücklich als deskriptiv bezeichnet.

Ein abgeleiteter Inputhash kann wegen der zulässigen Intervention vom Basisfall abweichen. Die Transformation muss jedoch auf dieselbe unveränderte Herkunft zurückführen und die übrigen Annahmen belegen. Identität wird daher aus dokumentierter Herkunft, Operation und unveränderten Vergleichsannahmen geprüft, nicht aus gleichen Dateinamen, gerundeten Kosten oder pauschal identischen Hashes. Prüfdeckung bleibt je ausgewählter Ausführung sichtbar.

Jede numerische Reihe enthält genau einmal ihre eigene belegte Basis: Offset 0, Faktor 1 oder tatsächlicher direkter Basiswert. Bei Lieferprofilen sind die Kategorien getrennt; eine numerische Basisinterpolation ist dort unzulässig. Fremde Basisfälle werden nicht wegen ähnlicher Ergebniswerte eingesetzt.

### P1 · Tatsächliche OAT-Operation

Die Beschriftung folgt der tatsächlich gespeicherten Operation und dem Inputvertrag, nicht allein dem historischen Familiennamen. Der dokumentierte gemeinsame EU-Preisversuch verschiebt die Stundenreihe additiv um ±50 % ihres Basisjahresmittels. Er multipliziert nicht jede Preisstunde und ersetzt die Reihe nicht durch einen konstanten Tarif. Offset, Basismittel und Geldbasis gehören in Titel, Achse, Tabelle und Export. Ein tatsächlich konstanter Tarif bleibt entsprechend bezeichnet. WACC-Verschiebung verwendet Prozentpunkte; ein WACC-Faktor wirkt auf die dokumentierten einzelnen Komponentenraten.

### P1 · Nachfragehomogenität

Die dokumentierten kontinuierlichen LP-Gleichungen sind bei unveränderten Koeffizienten, positivem Nachfragefaktor und ohne zusätzliche absolute Grenzen homogen. Für ein wohldefiniertes Optimum gilt mit gleichem Annualisierungsbezug:

`C*(αD) = α · C*(D)` und `LCOH(αD) = LCOH(D)` für `α > 0`.

Eine proportional skalierte optimale Kapazitäts- und Betriebslösung existiert. Wegen alternativer Optima müssen separat gelöste Fälle nicht in jeder einzelnen Kapazität dieselbe Aufteilung zeigen. Kleine numerische Abweichungen werden im Zusammenhang mit Solver- und Prüftoleranzen beurteilt. Der Nachfragehinweis soll diese strukturelle Erwartung erklären. Nahezu konstante LCOH sind eine wissenschaftlich relevante Modelleigenschaft und werden nicht als unbrauchbare Kurve entfernt. Daraus folgen keine realen industriellen Skaleneffekte.

### P1 · Emissionsgrenzen und Rollen der Größen

Die betriebliche EU-Basis verwendet einen statischen Länderfaktor 2024: `GHG_op,a = EF_Land,2024 · E_Netz,a`. Die betriebliche Intensität wird daher durch spezifischen Netzimport erklärt. Allein die Verschiebung des Bezugs zwischen Stunden liefert in diesem Ansatz keinen zeitabhängigen Emissionsvorteil. Die betriebliche Bewertung beeinflusst die kostenminimale Auslegung nicht durch ein eigenes Emissionsziel oder eine Emissionsobergrenze.

Die regulatorische elektrische Teilbewertung bleibt getrennt. Null bei S1/S2 folgt im hinterlegten Modellpfad aus erzwungener EE-Mengendeckung und belegt keine physische Emissionsfreiheit. Die native Produktreferenz gehört ausschließlich als beschriftete Linie in die passende regulatorische Intensitätsansicht mit derselben Einheit und Heizwertbasis. Sie gehört nicht auf absolute Jahresemissionen oder in eine eigene Sensitivitätskurve. Prüfgrößen bleiben in der Modellprüfung. Fehlende Werte und nicht ausgewertete Größen sind keine Nullen.

### P2 · Effekte verständlich darstellen

Ein Szenarienvergleich kann neben Kostenwerten die Änderung zur eigenen S0-Basis zeigen. OAT kann absolute und relative Ergebnisänderungen zur eigenen Basis anbieten; bei Basiswert null ist die relative Änderung nicht definiert. Verbundene Punkte bezeichnen berechnete Stufen, keine belegte Antwort an allen Zwischenwerten. Variationsstufen sind Szenarioannahmen, keine Konfidenzintervalle. Diese Darstellungen sind Auswertungen vorhandener Resultate und benötigen keine neuen Modellgleichungen.

## 3. Konkrete Kriterien für U1

| Kriterium | Erwarteter gezielter Nachweis | Bezug |
|---|---|---|
| Operation korrekt | Historische EU-Preisfamilie anhand `add_to_hourly_price_profile` / `electricity_price_offset_eur_per_mwh` als additive Verschiebung beschriften; einen tatsächlichen Konstantpreis unterscheiden. | M01 |
| Eigene Referenz | Jede gezeichnete numerische Reihe besitzt genau eine belegte Basis am richtigen x-Wert; fehlende oder mehrdeutige Basis wird erklärt, nicht erfunden. | M02 |
| Kontrollierter Vergleich | Szenarien bei einem Standort/Profil/Mengen-/Solverkontext vorauswählen; unzulässige gemeinsame Grundlagen erkennen und deskriptive Mischvergleiche ausdrücklich kennzeichnen. | M04 |
| Rollen fachlich passend | Ergebnisgrößen als Auswertung, native Referenz als passende Linie, Prüfgrößen als Diagnostik; statische betriebliche und regulatorische Teilbewertung getrennt erklären. | M03, M05 |
| Grafik und CSV identisch | Identische dargestellte Fälle, Stufen inklusive Basis, Größen, Einheiten und Zeitfenster aus einem vorbereiteten Datensatz verwenden. Stundenkurven exportieren Stundenwerte; OAT exportiert genau die gewählte Reihe. | M06 |
| Kontextwechsel eindeutig | Standort-/Profil-/Fall-/Kennzahlwechsel oder leere Auswahl darf keinen alten Export als aktuellen anbieten. Ausgewählter Detailfall und Vergleichsmenge sind unterscheidbar. | M07 |
| Kategorien sicher | Doppelte Diagrammkategorien vor Darstellung erkennen; belegte identische Ausführungen erläutern oder getrennt darstellen; keine fachliche Aussage aus technischen Dopplungen erzeugen. | M11 |
| Interpretationsgrenzen erhalten | Nachfrage als Neuauslegung/Skalierung, historische Jahres- und Geldbasis, Lieferpunkt, statische Faktoren und elektrische Teilbilanzhinweis an relevanter Ergebnisansicht sichtbar halten. | M19 sowie D1 Abschnitte 4, 5 und 8 |

Die Reihenfolge ist: **belegte Fallidentität → kontrollierte Vergleichsmenge → tatsächliche Operation und eigene Referenz → passende Größenrolle → identischer Grafik-/Exportdatensatz**. Gezielte Prüfungen vorhandener gespeicherter Fälle und kleine Testdaten reichen für diesen Ergebnisbezug; neue Jahresoptimierungen sind kein erforderlicher fachlicher Nachweis einer GUI-Korrektur.

U1 ersetzt weder U2–U4 noch eine Produkt-, Geräte- oder Nutzerabnahme. Der Implementierungs- und Prüfstand wird separat mit eigenen Nachweisen dokumentiert. Alle ursprünglichen Quellen, Modellfälle und Prüfberichte bleiben erhalten.

## 4. Gezielte unabhängige Prüfung der Umsetzung

Der [unabhängige wissenschaftliche Audit](outputs_h2/gui_validation/u1_20261011/verification/scientific_audit/SCIENTIFIC_AUDIT.md) dokumentiert **14/14 bestandene gezielte Prüfungen** mit vorhandenen echten Ergebnissen. Das Installationsziel des verlinkten Nachweises liegt unter `outputs_h2/gui_validation/u1_20261011`; die Prüfung selbst schrieb ausschließlich in die separate lokale Arbeitskopie. Ausgewertet wurden die gemeinsame Hamburger D0-Preis-/WACC-/PV-Familie, ursprüngliche EU-Preis-/WACC-Reihen, der ursprüngliche Namibia-Konstanttarif, Hamburger D0-Nachfrage 50–150 % und frische S0/S1/S2-Jahresfälle 2024.

Nachgewiesen sind korrekte tatsächliche Operationen, eigene eindeutige Basen, Ablehnung fremder Preis- und eingebetteter Nachfragebasen, erhaltene native Ergebniswerte, kontrollierte Szenarienvorauswahl und deskriptive Mischprofilkennzeichnung, passende native Emissionsreferenz sowie identische Grafik-/CSV-Punkte und native Stundenwerte. Die Nachfrage besitzt genau drei eigene 100-%-Referenzen und zeigt innerhalb einer relativen numerischen Toleranz von `1e-6` die strukturell erwartete Kosten-/Mengenproportionalität und konstante LCOH. Der tatsächlich gespeicherte Namibia-Basistarif beträgt in dieser geprüften historischen Familie 128 EUR/MWh; er wurde aus den nativen Inputs übernommen, nicht als neuer Modellwert festgelegt.

Der Audit deckte eine reale Zuordnungslücke bei der Nachfragebasis auf: Die unveränderte native Basisausführung trägt die Operation `unchanged`, während ihre akzeptierte Tabellenzeile zur Nachfragefamilie gehört. Die Korrektur unterscheidet diese belegte Basis von der Eingriffsoperation und prüft weiterhin Konfiguration, Kalender, Software und tatsächliche Inputänderung. Danach bestehen auch die Nachfrage- und Fremdbasisprüfungen.

Preis-, Nachfrage-, Emissions- und Stundenabbildung wurden zusätzlich visuell geprüft. **189 gelesene Originaldateien** besitzen nach dem Audit unveränderte Hashes; neue Optimierungen wurden nicht ausgeführt. Bericht, Quell- und Codestandhashes sowie die exakten Tabellen und PNGs liegen im Auditnachweis. Dieser gezielte Nachweis ersetzt keine Browser-/Nutzerabnahme, keine vollständige Prüfung aller registrierten Familien und keine Auftrags-/Geräteprüfung aus U2–U4.

Eine anschließende ausschließlich lesende Prüfung von `remember_figure` bestätigt die ergänzte Exportbedeutung: Eine Kopie des unveränderten Grafikdatensatzes erhält `__plot_label`, `__plot_x_label`, `__plot_y_labels` als JSON je Achse, `__plot_operation`, `__plot_note` und `__plot_parameter`. Die native Tabelle und ihre Zeilen bleiben erhalten. Damit ist auch die Prozentachse der Nachfrage gegenüber dem nativen Faktor im CSV ausdrücklich interpretierbar. Diese Lesedurchsicht ist ein ergänzender Nachweis für die spätere App-Fassung; die ursprünglichen Codestandhashes des ausgeführten 14-Punkte-Audits bleiben unverändert dokumentiert.
## 5. Abschluss am installierten Codestand

Nach der letzten zusätzlichen Eingriffs-/Achsenprüfung wurde derselbe reale Audit erneut direkt aus dem installierten Modellordner ausgeführt. [14/14 Checks bestehen auch mit exakt den installierten Modulen](outputs_h2/gui_validation/u1_20261011/verification/scientific_audit_final/SCIENTIFIC_AUDIT.md); deren vier GUI-Modulhashes stimmen mit den installierten Dateien überein. 189 gelesene Originaldateien blieben erhalten. Der erste unabhängige Audit und seine Hashes wurden nicht überschrieben. Die [Browserkontrolle](outputs_h2/gui_validation/u1_20261011/verification/browser/BROWSER_PRUEFUNG.md) bestätigt zusätzlich neun tatsächliche Preisgrafikpunkte einschließlich drei eigener Basen, exportierte Achsenbedeutung und byteidentische Grafikdownloads in Sensitivitätsanalyse und Export. U2–U4 und die vollständige Produktabnahme bleiben offen.
