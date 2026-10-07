# Gratis in Freising

Veranstaltungen in Freising sammeln und als Website, Kalender und Tagesmail
anzeigen. Speicherung und Automatisierung laufen auf GitHub.

## Der normale Betrieb

Jede Nacht erledigt GitHub Actions diese Schritte:

1. Vorhandene Daten automatisch auf Formatfehler pruefen.
2. Aktive Quellen aus `quellen.yml` abfragen und Termine aktualisieren.
3. Freigegebene GitHub-Meldungen uebernehmen.
4. Bekannte Feldschreibfehler vereinheitlichen und alte Termine archivieren.
5. Kalender und Mail erzeugen und den Stand im Repository speichern.
6. Uebernommene Meldungen schliessen und, sofern eingerichtet, die Tagesmail senden.

Es gibt **keine verpflichtende woechentliche Pruefrunde**. Nicht belegte
Eintrittsangaben erscheinen weiterhin als „vermutlich kostenfrei“. Eine
Preisangabe schliesst einen Termin aus dem Gratisangebot aus. Die Automatik
kann sich irren; jeder Termin verlinkt deshalb seine Quelle und den Preisbeleg.

Der Sammellauf startet um 03:20 UTC, also 05:20 im Sommer und 04:20 im Winter.
GitHub kann den Start verzoegern. Ein manueller Lauf ist unter
**Actions → Events sammeln → Run workflow** moeglich. Die optionalen Schalter
fuer KI-Nachpruefung und Social-Entwuerfe bleiben normalerweise ausgeschaltet.

## Was wo liegt

| Datei | Zweck |
| --- | --- |
| `index.html` | Oeffentliche Uebersicht auf GitHub Pages |
| `daten/events.json` | Importbestand: aktuelle Termine und die letzten 30 Tage |
| `daten/verwaltung.json` | Eigene Termine, Korrekturen und Ausblendungen |
| `daten/archiv/JJJJ.json` | Aeltere Termine nach ihrem urspruenglichen Anfangsjahr |
| `daten/events.schema.json` | Verbindliches, automatisch geprueftes Datenformat |
| `quellen.yml` | Quellen aktivieren/deaktivieren und Ortsnamen vereinheitlichen |
| `daten/quellen-status.json` | Erfolg und Fehler je Quelle |
| `ausgabe/gratis-freising.ics` | Abonnierbarer Kalender |
| `ausgabe/mail.html` | Vorschau der Tagesmail |

**Importdaten nicht von Hand bearbeiten.** Korrekturen gehoeren in
`daten/verwaltung.json`, damit der naechste Import sie nicht ueberschreibt.
Das Archiv bleibt erhalten, wird aber nicht von der Website geladen.
Ein Archivtermin, dessen Ende spaeter verlaengert wird, kann in den
Arbeitsbestand zurueckkehren. Die stabile ID bleibt dabei erhalten.

Kalender, Mail und Website unterscheiden Einzeltermine und laufende
Dauertermine. Abgesagte Termine tragen im Kalender einen Absagehinweis.
Unbekannte Endzeiten bleiben `null`; der Kalender verwendet dann eine
Darstellungsdauer von zwei Stunden, ohne diese als Quellinformation zu speichern.

## Termine von Hand eintragen

Die vollstaendig auf GitHub laufende Variante verwendet das
[Veranstaltungsformular](https://github.com/JoanaBayraktar/gratis-in-freising/issues/new?template=veranstaltung.yml).
Ein GitHub-Konto ist dafuer erforderlich.

- Titel, Datum, Ort und Eintritt eintragen.
- Als Betreiberin das Label `freigegeben` setzen.
- Der naechste Sammellauf uebernimmt die Meldung und schliesst sie nach dem
  erfolgreichen Speichern.

Diese Freigabe betrifft neue Einreichungen, nicht die automatische
Terminsammlung. Meldungen bleiben ohne Freigabe ausserhalb der Anzeige.

Korrekturen lassen sich direkt im GitHub-Dateieditor in
`daten/verwaltung.json` speichern. Beispiel:

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

Es werden nur die angegebenen Felder ueberschrieben. Eine Ortskorrektur
bestaetigt keinen Preis. Erst eine ausdrueckliche Korrektur von `eintritt`
gilt als manuelle Preiseinstufung. IDs und Eintraege in der Verwaltungsdatei
werden bei der Archivierung nicht entfernt.

`verwaltung.html` ist derzeit nur eine Leseansicht, solange
`const MELDESTELLE = "";` dort leer ist. Bearbeiten ueber diese Oberflaeche
erfordert den optionalen Cloudflare Worker in `melden/worker.js`.
Der Worker ist ein externer Dienst; fuer den GitHub-only-Betrieb genuegen
Issue-Formular und GitHub-Dateieditor. Daten im oeffentlichen Repository
sind oeffentlich, auch in der Verwaltungsdatei und im Archiv.

## Einrichtung

1. GitHub Pages auf Branch `main`, Ordner `/` einstellen.
2. Unter **Settings → Secrets and variables → Actions** das Secret
   `MISTRAL_API_KEY` hinterlegen.
3. **Actions → Events sammeln → Run workflow** starten.
4. Optional die Mail-Secrets `MAIL_SERVER`, `MAIL_BENUTZER`,
   `MAIL_PASSWORT` und `MAIL_AN` setzen. Ohne vollstaendige Konfiguration
   laeuft das Projekt mit Website und Kalender weiter.

SMTP verwendet Port 465 und TLS. Bei Gmail ist ein App-Passwort erforderlich.
Ein Versandfehler wird gemeldet, bereits gespeicherte Daten bleiben erhalten.

Die Website liest die JSON-Dateien direkt. Korrekturen erscheinen nach der
Veroeffentlichung durch Pages; Mail und Kalender werden beim naechsten
Sammellauf neu erzeugt.

## Wenn etwas nicht funktioniert

- **Roter Sammellauf:** Fehler im Actions-Protokoll ansehen. Mailfehler werden
  gesondert bezeichnet; Daten sind dann bereits gespeichert.
- **Quelle liefert nichts:** `daten/quellen-status.json` ansehen.
  Eine Quelle kann in `quellen.yml` mit `aktiv: false` pausiert werden.
  Ein fehlgeschlagener Abruf loescht keine Termine.
- **Falscher Termin:** In `daten/verwaltung.json` korrigieren oder ausblenden.
- **Datenpruefung schlaegt fehl:** Feldname, Datentyp, Datum und Ende anhand
  von [SCHEMA.md](SCHEMA.md) pruefen. Unbekannte Felder werden nicht still geloescht.

## Lokal entwickeln und pruefen

```sh
python3 -m venv venv
venv/bin/pip install -r requirements.txt
venv/bin/python -m unittest discover -s tests
venv/bin/python scripts/datenpflege.py
venv/bin/python scripts/build_kalender.py
venv/bin/python scripts/build_mail.py
venv/bin/python -m http.server 8765
```

Die Website ist unter `http://localhost:8765` erreichbar.
`file://` kann die JSON-Dateien nicht zuverlaessig laden.

`python scripts/datenpflege.py --schreiben` normalisiert und archiviert
lokal. Ohne diesen Schalter prueft das Skript nur. Alle Daten werden vor dem
Schreiben validiert. Pull Requests erhalten dieselben Pruefungen ohne
Modellaufrufe oder Mailversand.

## Optionale Erweiterungen

`ausgabe/PRUEFLISTE.md` und `pruefen.ics` bleiben als freiwillige
Nachschlagewerke erhalten. Sie blockieren keine Veroeffentlichung.
KI-Nachpruefung und Social-Entwuerfe sind manuell zuschaltbar; die
vorhandenen Skripte bleiben verfuegbar.

Die geplanten Ausbaustufen und Produktgrundsaetze stehen in [PRODUCT.md](PRODUCT.md).
