# Datenformat

Die verbindliche Definition ist [daten/events.schema.json](daten/events.schema.json)
(JSON Schema Draft 2020-12). Der Bestand und jedes Jahresarchiv verwenden:

```json
{
  "schema_version": 2,
  "events": [],
  "laeufe": []
}
```

`laeufe` bleibt aus Kompatibilitaetsgruenden erhalten; die Laufhistorie liegt
in GitHub Actions, der Quellenverlauf in `daten/quellen-status.json`.

## Termin

Alle Felder aus `$defs.event` sind erforderlich. Unbekannte Textangaben sind
`null`; Listen sind `[]`. Boolesche Felder verwenden `true`/`false`,
keine Zeichenketten. Zusaetzliche, unbekannte Felder sind ungueltig.

| Felder | Bedeutung |
| --- | --- |
| `id` | Stabile Kennung; bei Migration und Archivierung nie neu erzeugen |
| `titel`, `beschreibung` | Titel und kurze Beschreibung |
| `beginn`, `ende`, `ganztaegig` | Zeitraum; unbekanntes Ende bleibt `null` |
| `dauertermin`, `besonderheit` | Laufende Veranstaltung bzw. besonderer Anlass darin |
| `ort_name`, `ort_adresse`, `veranstalter` | Ort und Veranstalter |
| `kategorie`, `zielgruppe` | Nichtleere Texte; Quellkategorien bleiben erhalten |
| `drinnen_draussen` | `drinnen`, `draussen`, `beides` oder `null` |
| `anmeldung_noetig`, `anmeldung_url`, `ausgebucht` | Anmeldung und Verfuegbarkeit |
| `bild_url` | Optionales Veranstaltungsbild |
| `eintritt` | `frei`, `spende`, `kostenpflichtig`, `unklar` |
| `eintritt_beleg` | Quellenzitat oder ausdruecklich als Annahme bezeichnete Hausregel |
| `eintritt_confidence` | `hoch`, `mittel`, `niedrig` |
| `quelle_name`, `quelle_url`, `quellen_weitere` | Erstquelle, Hauptadresse und weitere Quellen |
| `status` | `aktiv`, `abgesagt`, `verschwunden`, `vergangen` |
| `zuerst_gesehen`, `zuletzt_gesehen` | Datum als `YYYY-MM-DD` |
| `manuell_bestaetigt` | Inhalt ist gegen automatische Ueberschreibung geschuetzt |

Zeitpunkte sind lokale Zeit in **Europe/Berlin**, Format
`YYYY-MM-DDTHH:MM:SS` ohne Suffix. Ganztagsereignisse beginnen um Mitternacht.
Ein Ende darf nicht vor dem Anfang liegen. Die Python-Pruefung kontrolliert
neben dem Schema echte Kalenderdaten und eindeutige IDs.

Neue Import-IDs werden durch `scripts/event_id.py` aus normalisiertem Titel,
Anfangsdatum und Ort gebildet (16 Zeichen des SHA1-Hashs). Der Import besitzt
zusaetzliche Regeln zum Wiedererkennen derselben Veranstaltung. Einzeltermine
einer Reihe bleiben getrennte Termine.

## Import und Normalisierung

Das Modellformat wird aus dem Ablageschema abgeleitet. Modellantworten werden
vor der Uebernahme geprueft. Vor dem Speichern wird der vollstaendige Bestand
geprueft. Bekannte historische Feldvarianten wie `drinnen_draußen`,
`dauertermine`, `dauerterm` und `ausgebukt` werden auf die kanonischen Namen
abgebildet. Bei widerspruechlichen Werten gewinnt das korrekt benannte Feld.
Unbekannte Felder oder falsche Werte erzeugen einen Fehler.

Das frühere Feld `social_text` wird bei der Migration entfernt; Social-Ausgaben
sind nicht mehr Teil des Produkts. Alle Termininhalte und Quellenbelege bleiben erhalten.

Kategorien und Zielgruppen sind bewusst freie Texte: Vorhandene Quellen
liefern etwa „Fuehrung/Besichtigung“ oder „Frauen“. Sie auf „Sonstiges“ bzw.
„Alle“ zu reduzieren, wuerde Information verlieren. Eine spaetere gemeinsame
Kategorisierung sollte ein eigenes redaktionelles Feld erhalten.

## Eintritt und Anzeige

Die Regeln stehen in `scripts/regeln.py`:
belegtes oder manuell bestaetigtes `frei` erscheint als „Eintritt frei“,
belegte Spendenbasis als „Spende erbeten“, unbelegte Angaben und `unklar`
als „vermutlich kostenfrei“. `kostenpflichtig` wird aus dem Gratisangebot
ausgeschlossen. Das gilt ohne verpflichtende manuelle Sichtung.

Eine Anmeldepflicht bedeutet nicht, dass ein Termin Geld kostet.
Ein leeres Preisfeld belegt keinen freien Eintritt. Eine Hausregel einer
Quelle muss im Beleg als Annahme bezeichnet sein. Nur eine ausdrueckliche
manuelle Eintrittskorrektur gilt als Preiseinstufung.

## Archiv und Handarbeit

Termine mit Ende **vor heute minus 30 Tage** gehen in
`daten/archiv/JJJJ.json`. Ohne Ende zaehlt der Anfangstag.
Mehrtaegige Veranstaltungen bleiben bis nach ihrem Ende im Arbeitsbestand.
Das Jahr richtet sich nach dem urspruenglichen Anfang, nicht nach dem Import.

Manuelle Datumskorrekturen werden vor der Archiventscheidung beruecksichtigt.
Der Import liest das Archiv zum Wiedererkennen ein; eine Verlaengerung oder
Terminverschiebung kann einen Eintrag mit derselben ID zurueckholen.
Die Website laedt nur den Arbeitsbestand. Eine automatische Verschiebung des
Anfangsdatums kann weiterhin eine neue Kennung erzeugen; diese bestehende
Importregel wird durch die Archivierung nicht geaendert.

`daten/verwaltung.json` bleibt getrennt und unveraendert:
`ausgeblendet` entfernt Eintraege aus der Ausgabe,
`korrekturen` ueberschreibt erlaubte Felder je ID,
`eigene` fuegt manuelle Termine hinzu. Eigene Termine verbleiben in der
Verwaltungsdatei; ihre automatische Archivierung ist fuer spaeter vorgesehen.
Korrekturen bleiben auch fuer archivierte IDs erhalten.

Ein fehlgeschlagener Quellenabruf ist kein Beleg fuer eine Absage.
`verschwunden` setzt einen erfolgreichen Abruf und mindestens vier Wochen
ohne erneute Sichtung voraus.
