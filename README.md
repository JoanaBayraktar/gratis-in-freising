# Gratis in Freising — automatische Eventsammlung

Jede Nacht liest ein GitHub-Action-Lauf die Quellen aus `quellen.yml`, erkennt
Veranstaltungen mit freiem Eintritt und pflegt daraus zwei Kalender. Das läuft
auf GitHubs Servern — Ihr Rechner muss dafür nicht an sein.

## Was wo liegt

```
index.html               die Übersichtsseite (GitHub Pages)
melden/worker.js         Meldestelle für das Formular (Cloudflare Worker)
quellen.yml              Quellenliste  ← hier Quellen an- und abschalten
SCHEMA.md                welche Felder ein Event hat und was sie bedeuten
daten/
  events.json            die Datenablage — das ist die Wahrheit
  quellen-status.json    Gesundheit je Quelle: Fehlversuche, Trefferverlauf
ausgabe/
  gratis-freising.ics    gesicherte Gratis-Events → abonnieren
  pruefen.ics            unklare Fälle → wöchentlich sichten
  PRUEFLISTE.md          dieselben Fälle als lesbare Liste
  SOCIAL-KWxx.md         Post-Entwürfe, entstehen freitags
  mail.html              die Tagesmail, wird täglich neu erzeugt
  NACHPRUEFUNG.md        was der zweite Modellblick gefunden und getan hat
scripts/
  sammeln.py             holt die Quellen, fragt das Modell, schreibt events.json
  build_kalender.py      baut die .ics-Dateien und die Prüfliste
  meldungen.py           übernimmt freigegebene Meldungen aus GitHub-Issues
  nachpruefen.py         zweiter Modellblick auf die fertige Liste
  build_mail.py          baut die Tagesmail
  build_social.py        baut die Social-Entwürfe
  event_id.py            stabile ID für die Dublettenerkennung
.github/workflows/       der nächtliche Ablauf
```

Wichtig zu verstehen: **`daten/events.json` ist die Quelle, alles unter `ausgabe/`
wird daraus neu erzeugt.** Änderungen direkt in einer `.ics`-Datei sind beim
nächsten Lauf weg. Korrekturen gehören in die JSON-Datei.

## Einrichtung

1. Repository auf GitHub anlegen (öffentlich) und diesen Ordner hochladen.
2. Unter **Settings → Secrets and variables → Actions → New repository secret**
   ein Secret namens `MISTRAL_API_KEY` mit Ihrem Mistral-Schlüssel anlegen.
   Der Schlüssel gehört ausschließlich dorthin — nie in eine Datei im Repo.
3. Für die Tagesmail vier weitere Secrets anlegen:

   | Name | Wert |
   |---|---|
   | `MAIL_SERVER` | SMTP-Server, bei Gmail `smtp.gmail.com` |
   | `MAIL_BENUTZER` | Ihre Absenderadresse |
   | `MAIL_PASSWORT` | **App-Passwort**, nicht das Kontopasswort |
   | `MAIL_AN` | Empfänger, mehrere mit Komma getrennt |

   Gmail und die meisten Anbieter verlangen für SMTP ein eigenes App-Passwort,
   das Sie in Ihren Kontoeinstellungen erzeugen. Das normale Passwort
   funktioniert nicht und gehört auch nicht in ein Repository-Secret.

4. Unter **Actions** den Workflow „Events sammeln" einmal von Hand starten
   („Run workflow"), um zu sehen, ob alles greift.

Danach läuft er täglich um 03:20 UTC, also 05:20 deutscher Sommerzeit.

## Die Tagesmail

Nach jedem Sammellauf geht eine Mail raus, in drei Abschnitten:

**Heute** — die Einzeltermine des Tages, mit Uhrzeit, Ort und kurzer
Beschreibung. Das ist, was man verpassen kann.

**Läuft gerade** — mehrtägiges wie Ausstellungen, jedes **einmal** genannt
statt an jedem seiner Tage. Statt der Anfangszeit steht dort die Restlaufzeit,
sortiert nach Ende: was bald ausläuft, steht oben und wird in den letzten zwei
Tagen farbig. Eine Ausstellung, die noch drei Monate zu sehen ist, eilt nicht
und steht unten.

**Die nächsten Tage** — Einzeltermine als knappe Liste, ohne Beschreibung.

Enthalten ist alles, was nicht nachweislich Geld kostet. Was nur vermutlich
kostenlos ist — weil die Seite zum Preis schweigt —, steht mit dabei und trägt
die Marke „vermutlich kostenfrei". Spendenbasis ebenso. Nur der belegte freie
Eintritt bleibt unbeschriftet: Das ist der Normalfall, beschriftet wird die
Abweichung.

Der Mailtext lässt sich jederzeit ohne Versand ansehen:

```bash
./venv/bin/python scripts/build_mail.py
```

Danach `ausgabe/mail.html` im Browser öffnen.

## Die Nachprüfung

Beim Sammeln sieht das Modell immer nur eine Seite. Dass dieselbe Veranstaltung
beim Merkur schon steht, dass der Ort dort anders geschrieben wird oder dass
eine Quelle sie gratis nennt und die andere nicht — das lässt sich erst
beantworten, wenn alles beieinanderliegt.

`nachpruefen.py` schickt deshalb nach dem Sammeln die fertige Liste noch einmal
zum Modell, als Stichworte, ohne Webseiten. Das kostet rund 6.000 Tokens, also
etwa 0,1 Cent. Drei Fragen mit drei verschiedenen Folgen:

| Findet | Was passiert |
|---|---|
| Ortsname meint einen bekannten Ort | wird übernommen |
| Dublettenverdacht | wird **nur gemeldet** |
| Widerspruch beim Eintritt | wird **nur gemeldet** |

Nur der Ortsname wird automatisch geändert, weil das reiner Anzeigetext ist.
Alles andere ist ein Hinweis zum Nachsehen, keine Entscheidung.

Der erste Lauf hat gezeigt, warum das so sein muss: Das Modell hielt jede
wiederkehrende Reihe für eine Dublette — „Führung im Furtner" an vier Terminen,
„Karaoke mit Stefan" an zwei Abenden. Es schrieb sogar dazu, dass die Tage
verschieden seien, und meldete sie trotzdem. Verschmolzen wird deshalb
ausschließlich nach den festen Regeln in `sammeln.py`.

Alles Gefundene steht hinterher in `ausgabe/NACHPRUEFUNG.md`, auch das
Übernommene. Ohne Änderungen, nur zum Ansehen:

```bash
MISTRAL_API_KEY=... ./venv/bin/python scripts/nachpruefen.py --nur-melden
```

## Die Übersichtsseite

`index.html` zeigt alle gesammelten Veranstaltungen im Browser — mit Datum,
Ort, Quelle samt Link, Eintrittseinstufung und dem Belegzitat unter „Details".
Suchen, nach Quelle filtern, nach Datum oder Titel sortieren.

Die Seite liest `daten/events.json` direkt und hat keinen Bauschritt: Was der
nächtliche Lauf schreibt, steht dort ohne weiteres Zutun. Sie lädt nichts aus
dem Netz nach — keine Schriften, keine Bibliotheken.

Zum Suchen gibt es drei Wege nebeneinander: das Suchfeld, die Auswahllisten
für Quelle und Art der Veranstaltung, und einen kleinen Monatskalender hinter
„Tag wählen". Tage ohne Veranstaltung sind dort ausgegraut; ein gewählter Tag
sticht die Zeitfilter aus, weil man ihn ja bewusst angeklickt hat.

### Veranstaltungen melden

Unten auf der Seite steht ein Formular. Der Weg einer Meldung:

1. Jemand füllt das Formular aus → Issue mit dem Etikett `meldung`
2. Sie sehen es an. Stimmt es, hängen Sie das Etikett **`freigegeben`** dran
3. Der nächste nächtliche Lauf übernimmt es, schließt das Issue und
   kommentiert es

Ohne `freigegeben` passiert nichts, egal was im Issue steht. Übernommene
Meldungen bekommen `manuell_bestaetigt: true` — Sie haben sie geprüft, also
fasst der Sammellauf sie nicht mehr an.

### Die Meldestelle einrichten

Solange in `index.html` die Zeile `const MELDESTELLE = "";` leer ist, führt das
Formular über einen vorausgefüllten GitHub-Eintrag — das setzt bei der
meldenden Person ein GitHub-Konto voraus.

Damit Meldungen direkt eingehen, braucht es eine kleine Zwischenstelle, die
den GitHub-Token hält. Auf einer statischen Seite kann der Token nicht liegen:
Er stünde im Quelltext und wäre für jeden lesbar. `melden/worker.js` ist diese
Zwischenstelle, gedacht für Cloudflare Workers — kostenlos, kein Server.

1. **Token erzeugen:** github.com → Settings → Developer settings →
   Personal access tokens → **Fine-grained tokens** → Generate new token.
   Repository access: **nur** `gratis-in-freising`. Permissions:
   **Issues → Read and write**, sonst nichts. Laufzeit ruhig knapp wählen und
   im Kalender notieren, wann er abläuft.
2. **Worker anlegen:** dash.cloudflare.com → Workers & Pages → Create →
   Start with Hello World. Den Inhalt von `melden/worker.js` einfügen, Deploy.
3. **Variablen setzen** (Settings → Variables and Secrets), alle als *Secret*:

   | Name | Wert |
   |---|---|
   | `GITHUB_TOKEN` | der Token aus Schritt 1 |
   | `GITHUB_REPO` | `JoanaBayraktar/gratis-in-freising` |
   | `ERLAUBTE_HERKUNFT` | `https://joanabayraktar.github.io` |

4. **Adresse eintragen:** Die Worker-Adresse (`https://….workers.dev`) in
   `index.html` bei `const MELDESTELLE` einsetzen und committen.

Warum der Token so eng geschnitten wird: Die Adresse ist öffentlich, jeder
kann darauf POSTen. Selbst wenn das jemand ausnutzt, entstehen daraus nur
Issues — nichts, was ins Repository geschrieben wird, und nichts, was ohne Ihr
`freigegeben` in Kalender oder Mail landet. Gegen einfache Bots hilft ein
unsichtbares Feld im Formular; wird es ausgefüllt, verschwindet die Meldung
lautlos.

Wenn doch Spam ankommt, lässt sich **Cloudflare Turnstile** dazuschalten: Im
Cloudflare-Dashboard eine Website hinzufügen, den Secret Key als
`TURNSTILE_SECRET` hinterlegen — der Worker prüft ihn dann. Das Widget im
Formular kommt in dem Fall noch dazu; sagen Sie Bescheid, dann baue ich es ein.

Was gerade zur Freigabe wartet:
<https://github.com/JoanaBayraktar/gratis-in-freising/issues?q=is%3Aopen+label%3Ameldung>

Lokal ansehen (ein Server ist nötig, `file://` darf die JSON nicht laden):

```bash
./venv/bin/python -m http.server 8765
```

Dann http://localhost:8765 öffnen.

## Kalender abonnieren

Nach dem ersten erfolgreichen Lauf liegt `ausgabe/gratis-freising.ics` im Repo.
Den Raw-Link kopieren (Datei öffnen → Button „Raw" → Adresse aus der Zeile) und
im Kalenderprogramm unter „Kalenderabonnement hinzufügen" eintragen. Der
Kalender aktualisiert sich dann von selbst.

## Die wöchentliche Handarbeit

Rechnen Sie mit rund 15 Minuten:

1. `ausgabe/PRUEFLISTE.md` öffnen
2. Bei jedem Fall entscheiden — das Belegzitat steht dabei, meist reicht es
3. In `daten/events.json` das Feld `eintritt` korrigieren **und
   `manuell_bestaetigt` auf `true` setzen**

Schritt 3 ist der entscheidende: `manuell_bestaetigt: true` schützt Ihre
Entscheidung davor, im nächsten Lauf wieder überschrieben zu werden. Der
Sammellauf fasst solche Einträge nur noch an, um `zuletzt_gesehen` nachzuziehen.

## Quellen pflegen

`quellen.yml` lässt sich direkt auf github.com bearbeiten: Datei öffnen,
Stift-Symbol, ändern, „Commit changes". Kein Git nötig.

`aktiv: false` schaltet eine Quelle ab, ohne sie zu löschen — samt Notiz, warum.

Eine einzelne Quelle vorher ausprobieren:

```bash
MISTRAL_API_KEY=... python3 scripts/sammeln.py "Schafhof Kunstforum"
```

## Wenn eine Quelle Ärger macht

`daten/quellen-status.json` führt je Quelle Buch: letzter Erfolg, Fehlversuche
in Folge, wie viele Events die letzten zehn Läufe gebracht haben. Der Lauf meldet
am Ende, welche Quellen dreimal hintereinander versagt haben, und warnt, wenn
eine Quelle plötzlich null Events liefert, die sonst zuverlässig welche hatte.
Das ist der stille Ausfall, der sonst monatelang unbemerkt bliebe.

GitHub schickt Ihnen außerdem automatisch eine E-Mail, wenn ein Lauf abbricht.

## Stand der Quellen (geprüft am 19.08.2026)

Von den 23 gesammelten Adressen liefern beim einfachen Abruf nur sechs
verwertbare Daten — die übrigen laden ihre Termine per JavaScript nach oder
nennen Datumsangaben ohne Jahreszahl. Die Gründe stehen einzeln in `quellen.yml`.

Aktiv: Stadtkalender Freising, Merkur, Schafhof, Furtner (API), Einfach selber
machen (API), vhs „kostenfrei".

Bevor weitere Quellen dazukommen, lohnt der Blick in die Daten: Wenn die beiden
Aggregatoren die Veranstaltungen der Einzelveranstalter ohnehin mit abdecken,
bringt jede zusätzliche Quelle vor allem zusätzliche Wartung.

## Kosten

Rund 25.000 Tokens pro Lauf — die Detailseiten hinter den Übersichten kosten
mehr als die Listen selbst, liefern aber erst die Preisangabe. Mit
`mistral-small-latest` sind das etwa 0,4 Cent pro Lauf, also weniger als
einen Euro im Monat. GitHub Actions ist bei öffentlichen Repositories kostenlos.

Ein anderes Modell lässt sich ohne Codeänderung setzen: Umgebungsvariable
`MISTRAL_MODELL`, lokal vorangestellt oder im Workflow als `env:`.
