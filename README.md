# Gratis in Freising

Kostenlose Veranstaltungen in Freising automatisch sammeln, vereinheitlichen
und als übersichtliche Datenbasis bereitstellen. Website und Kalender zeigen
den aufbereiteten Bestand. Speicherung und Automatisierung laufen auf GitHub.

## Der normale Betrieb

Jede Nacht erledigt GitHub Actions diese Schritte:

1. Bestand und Archiv automatisch auf Datenfehler prüfen.
2. Aktive Quellen aus `quellen.yml` abfragen und Termine aktualisieren.
3. Feldnamen vereinheitlichen, Daten validieren und ältere Termine archivieren.
4. Kalender erzeugen und den Stand im Repository speichern.

Die Website liest die gespeicherten JSON-Dateien direkt. Es gibt keine
verpflichtende wöchentliche Prüfrunde. Unbelegte Eintrittsangaben erscheinen
als „vermutlich kostenfrei“; Termine mit belegtem Preis werden aus dem
Gratisangebot ausgeschlossen. Quelle und Preisbeleg bleiben nachvollziehbar.

Der Sammellauf startet um 03:20 UTC, also 05:20 im Sommer und 04:20 im Winter.
GitHub kann den Start verzögern. Ein manueller Lauf ist unter
**Actions → Events sammeln → Run workflow** möglich.

**Aktueller Fokus:** Sammlung und Datenaufbereitung. Social-Entwürfe sind
entfernt. Eingereichte Meldungen werden derzeit nicht übernommen; das
öffentliche Meldeformular und die Issue-Vorlage sind entfernt. Mailerzeugung
und Mailversand sowie die zusätzliche KI-Nachprüfung laufen nicht im Workflow.
Das vorhandene Mail- und Nachprüfungsskript bleibt für spätere Nutzung
verfügbar; vorhandene Maildateien sind alte Ausgaben und werden nicht aktualisiert.

## Was wo liegt

| Datei | Zweck |
| --- | --- |
| `index.html` | Öffentliche Übersicht auf GitHub Pages |
| `daten/events.json` | Aktuelle Termine und die letzten 30 Tage |
| `daten/verwaltung.json` | Geschützte manuelle Ergänzungen und Korrekturen |
| `daten/archiv/JJJJ.json` | Ältere Termine nach ihrem ursprünglichen Anfangsjahr |
| `daten/events.schema.json` | Verbindliches, automatisch geprüftes Datenformat |
| `quellen.yml` | Quellen aktivieren/deaktivieren und Ortsnamen vereinheitlichen |
| `daten/quellen-status.json` | Erfolg und Fehler je Quelle |
| `ausgabe/gratis-freising.ics` | Abonnierbarer Kalender |

**Importdaten nicht von Hand bearbeiten.** Manuelle Eingriffe gehören in
`daten/verwaltung.json`, damit der nächste Import sie nicht überschreibt.
Das Archiv bleibt erhalten, wird aber nicht von der Website geladen.
Archivierte Termine werden beim Import wiedererkannt; eine Verlängerung kann
sie mit derselben ID in den Arbeitsbestand zurückholen.

Einzeltermine und laufende Dauertermine werden getrennt dargestellt.
Abgesagte Termine tragen im Kalender einen Absagehinweis.
Unbekannte Endzeiten bleiben `null`; der Kalender verwendet dann zwei Stunden
als Darstellungsdauer, ohne diese als Quellinformation zu speichern.

## Bei Bedarf von Hand korrigieren

Korrekturen lassen sich im GitHub-Dateieditor in `daten/verwaltung.json`
speichern. Beispiel:

```json
{
  "stand": "2026-10-07T12:00:00",
  "eigene": [],
  "korrekturen": {
    "ID-AUS-EVENTS-JSON": { "ort_name": "Stadtbibliothek Freising" }
  },
  "ausgeblendet": {
    "ANDERE-ID": { "grund": "Keine Veranstaltung" }
  }
}
```

Nur die angegebenen Felder werden überschrieben. Eine Ortskorrektur bestätigt
keinen Preis. Erst eine ausdrückliche Korrektur von `eintritt` gilt als manuelle
Preiseinstufung. Bei der Archivierung bleiben alle manuellen Eingriffe erhalten.

`verwaltung.html` ist derzeit eine Leseansicht, solange
`const MELDESTELLE = "";` dort leer ist. Bearbeiten über diese Oberfläche
erfordert den optionalen Cloudflare Worker in `melden/worker.js`.
Für die Sammlung und Datenaufbereitung ist dieser externe Dienst nicht nötig.
Daten im öffentlichen Repository sind öffentlich, auch im Archiv.

## Einrichtung

1. GitHub Pages auf Branch `main`, Ordner `/` einstellen.
2. Unter **Settings → Secrets and variables → Actions** das Secret
   `MISTRAL_API_KEY` hinterlegen.
3. **Actions → Events sammeln → Run workflow** starten.

Der Workflow benötigt keine Mail-Secrets und keine Schreibrechte für Issues.
Nach der Veröffentlichung durch Pages zeigt die Website den neuen Stand.
Kalender werden beim nächsten Sammellauf neu erzeugt.

## Wenn etwas nicht funktioniert

- **Roter Sammellauf:** Fehler im Actions-Protokoll ansehen.
- **Quelle liefert nichts:** `daten/quellen-status.json` ansehen.
  Eine Quelle kann in `quellen.yml` mit `aktiv: false` pausiert werden.
  Ein fehlgeschlagener Abruf löscht keine Termine.
- **Falscher Termin:** In `daten/verwaltung.json` korrigieren oder ausblenden.
- **Datenprüfung schlägt fehl:** Feldname, Datentyp und Zeitraum anhand
  von [SCHEMA.md](SCHEMA.md) prüfen. Unbekannte Felder werden nicht still gelöscht.

## Lokal entwickeln und prüfen

```sh
python3 -m venv venv
venv/bin/pip install -r requirements.txt
venv/bin/python -m unittest discover -s tests
venv/bin/python scripts/datenpflege.py
venv/bin/python scripts/build_kalender.py
venv/bin/python -m http.server 8765
```

Die Website ist unter `http://localhost:8765` erreichbar.
`file://` kann die JSON-Dateien nicht zuverlässig laden.

`python scripts/datenpflege.py --schreiben` normalisiert und archiviert lokal.
Ohne diesen Schalter prüft das Skript nur. Alle Daten werden vor dem Schreiben
validiert. Pull Requests erhalten dieselben Prüfungen ohne Modellaufrufe.

`ausgabe/PRUEFLISTE.md` und `pruefen.ics` bleiben freiwillige Nachschlagewerke;
sie blockieren keine Veröffentlichung. Die Produktgrundsätze und der aktuelle
Fokus stehen in [PRODUCT.md](PRODUCT.md).
