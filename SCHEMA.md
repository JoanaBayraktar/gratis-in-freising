# Datenschema — ein Event in `daten/events.json`

Alle Felder immer angeben. Was unbekannt ist, bekommt `null` — **nicht** raten,
**nicht** weglassen.

```json
{
  "id": "sha1-hash",
  "titel": "Serenade im Saunagarten",
  "beginn": "2026-08-28T19:30:00",
  "ende": "2026-08-28T21:00:00",
  "ganztaegig": false,
  "ort_name": "Fresch Freibad",
  "ort_adresse": "Am Fischersteig 3, 85354 Freising",
  "eintritt": "frei",
  "eintritt_beleg": "Zitat aus der Quelle, das die Einstufung stützt",
  "eintritt_confidence": "hoch",
  "veranstalter": "Stadtwerke Freising",
  "beschreibung": "Ein bis zwei Sätze in eigenen Worten.",
  "kategorie": "Musik",
  "zielgruppe": "Alle",
  "drinnen_draussen": "draussen",
  "anmeldung_noetig": false,
  "ausgebucht": false,
  "anmeldung_url": null,
  "bild_url": "https://…/foto.jpg",
  "quelle_url": "https://…/das-konkrete-event",
  "quellen_weitere": ["https://…/dasselbe-event-woanders"],
  "social_text": null,
  "zuerst_gesehen": "2026-08-19",
  "zuletzt_gesehen": "2026-08-19",
  "status": "aktiv",
  "manuell_bestaetigt": false
}
```

## Feldregeln

**`id`** — SHA1 aus `titel_normalisiert|beginn_datum|ort_name_normalisiert`.
Normalisiert heißt: kleingeschrieben, Umlaute aufgelöst, alles außer Buchstaben
und Ziffern entfernt. Erzeugen mit:
`python3 scripts/event_id.py "Titel" "2026-08-28" "Ort"`

**`beginn` / `ende`** — ISO 8601, lokale Zeit Europe/Berlin, **ohne** Zeitzonen-Suffix.
Ist keine Uhrzeit angegeben, `ganztaegig: true` setzen und die Zeit auf `T00:00:00`.
Ist kein Ende bekannt: bei Terminen mit Uhrzeit zwei Stunden annehmen, bei
ganztägigen denselben Tag.

**`eintritt`** — genau einer von vier Werten:

| Wert | Wann |
|---|---|
| `frei` | Text sagt ausdrücklich freier/kostenloser Eintritt, oder Quelle ist die vhs-Seite „kostenfrei" |
| `spende` | „Spende erbeten", „Hutkasse", „auf Spendenbasis", „Eintritt frei, um Spende wird gebeten" |
| `kostenpflichtig` | ein Preis, „ab 12 €", „Tickets", „VVK/AK" |
| `unklar` | steht nichts dazu da — **der Normalfall, keine Verlegenheitslösung** |

Wichtig: „Anmeldung erforderlich" heißt **nicht** kostenpflichtig. Ein leeres
`cost`-Feld in einer API heißt **nicht** gratis.

Beleg und Einstufung müssen zusammenpassen. `einstufung_pruefen()` in
`sammeln.py` setzt das durch: Steht im Beleg ein Betrag, gilt `kostenpflichtig`;
steht dort „Eintritt frei" oder „kostenlos", gilt `frei` mit Sicherheit `hoch`.
Das greift nur bei `unklar` — eine Einstufung, die das Modell selbst getroffen
hat, wird nie überstimmt.

**`ausgebucht`** — `true` nur, wenn die Quelle es sagt („ausgebucht",
„ausverkauft", „nur noch Warteliste"). Anmeldepflicht allein genügt nicht.
Neben dem Modellurteil greift eine Textprüfung auf Titel und Beschreibung,
weil Veranstalter den Hinweis gern in den Titel schreiben.

Folgen: Die Tagesmail lässt solche Termine weg und zählt sie nur im Fuß —
sie ist eine Empfehlung, und was man nicht mehr besuchen kann, gehört nicht
empfohlen. Im ICS-Kalender bleiben sie stehen, mit `[AUSGEBUCHT]` vor dem
Titel; ein Kalender ist zum Nachschlagen da. Gelöscht wird nichts: Wird ein
Platz wieder frei, ist die Veranstaltung noch da.

**`eintritt_beleg`** — wörtliches Zitat aus der Quelle, das die Einstufung trägt.
Bei `unklar` darf das `null` sein. Dieses Feld macht die Einstufung nachprüfbar,
ohne dass jemand die Quellseite erneut öffnen muss.

Steht dort „Annahme laut quellen.yml", war **kein** Beleg auf der Seite: Dann
greift die Hausregel `eintritt_wenn_unklar` einer Quelle (etwa „im Furtner ist
der Eintritt frei, wenn nichts anderes dabeisteht"). Der Text sagt das
ausdrücklich, damit im Kalender unterscheidbar bleibt, was belegt und was
unterstellt ist. Eine ausgewiesene Preisangabe schlägt die Hausregel immer.

**`eintritt_confidence`** — `hoch` (steht wörtlich da) · `mittel` (erschlossen,
z. B. Vernissage ist üblicherweise frei) · `niedrig` (geraten).
Nur `frei` + `hoch` landet automatisch im öffentlichen Kalender.

**`kategorie`** — einer von: `Musik`, `Kunst`, `Familie`, `Vortrag`, `Markt`,
`Sport`, `Fest`, `Sonstiges`

**`zielgruppe`** — `Alle`, `Familien`, `Kinder`, `Jugendliche`, `Erwachsene`, `Senioren`

**`drinnen_draussen`** — `drinnen`, `draussen`, `beides`, `null`

**`quelle_name`** — Name der Quelle aus `quellen.yml`, die das Event zuerst
gefunden hat. Wird beim Zusammenführen nicht überschrieben, denn davon hängt
`verschwunden` ab.

**`ort_name` / `ort_adresse`** — nennt die Quelle keinen Ort, springt
`ort_standard` aus `quellen.yml` ein. Das gilt nur für Veranstalter, die
ausschließlich im eigenen Haus veranstalten (Furtner, Schafhof, Offene
Werkstatt) — niemals für Aggregatoren wie Stadtkalender oder Merkur.

**`status`** — `aktiv` · `abgesagt` · `verschwunden` · `vergangen`

`verschwunden` heißt: Die Quelle wurde gelesen und das Event stand seit vier
Wochen nicht mehr drin. Wurde die Quelle gar nicht gelesen — abgeschaltet oder
kaputt —, bleibt das Event `aktiv`. Nicht nachgesehen zu haben ist kein Beleg
für ein abgesagtes Event.

**`manuell_bestaetigt`** — setzen Sie das von Hand auf `true`, wenn Sie einen
Eintrag geprüft haben. Der Agent überschreibt solche Einträge dann nicht mehr.

**`social_text`** — bleibt beim Sammeln `null`, wird freitags gefüllt.
