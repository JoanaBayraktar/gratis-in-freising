# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

**Betreiberin (primär).** Pflegt die Sammlung: sichtet wöchentlich die unklaren
Fälle, korrigiert Ort- und Preisangaben, trägt Termine ein, die keine Quelle
liefert, und blendet aus, was keine Veranstaltung ist. Arbeitet **ernsthaft an
beiden Geräten** — am Mac für längere Durchgänge, am Handy für Einzelfälle
unterwegs. Die dichte Tabelle muss deshalb am Telefon eine eigene Darstellung
haben, nicht seitlich weggescrollt werden.

**Zwei bis drei Pflegende (entschieden).** Die Betreiberin und ein bis zwei
weitere Personen pflegen gemeinsam. Jede bekommt einen **eigenen Zugang**; ein
geteiltes Passwort genügt nicht, weil nachvollziehbar bleiben muss, wer was
geändert hat.

**Veranstalter (später).** Sollen eigene Termine einreichen und deren Status
sehen. Heute läuft das über ein Formular, das ein GitHub-Issue erzeugt.

**Leserinnen und Leser: heute ein kleiner, bekannter Kreis.** Kein breites
Stadtpublikum. Sie bekommen die Tagesmail, abonnieren den Kalender oder sehen
auf die Übersichtsseite.

## Product Purpose

Veranstaltungen in Freising, die nichts kosten, automatisch zusammentragen und
in drei Formen ausliefern: eine Tagesmail, einen abonnierbaren Kalender und
eine Übersichtsseite. Der Zweck ist, dass niemand zehn Veranstalterseiten
durchsehen muss, um zu erfahren, was heute umsonst stattfindet.

Erfolg heißt: Die Mail kommt jeden Morgen, sie stimmt, und sie kostet fast
keine laufende Arbeit.

## Positioning

Andere Veranstaltungskalender listen Termine. Dieser legt sich fest, ob etwas
**nichts kostet**, und zeigt, woher er das weiß: Jede Einstufung trägt ein
wörtliches Zitat von der Quellseite mit sich, und wo keines zu finden war,
heißt es „vermutlich kostenfrei" statt „Eintritt frei". Diese Trennung zwischen
Belegtem und Vermutetem ist der Kern — sie ist der Grund, warum man der Angabe
trauen kann.

## Operating Context

- Der Sammellauf startet nachts gegen 03:20 UTC als GitHub Action. Kein Server,
  keine Datenbank: GitHub ist Ablage, Zeitplan, Versionsverlauf und Sicherung
  in einem.
- Die laufenden Kosten liegen bei etwa 25 Cent im Monat (Modellabfragen).
- Das Repository ist **öffentlich**. Alle Daten liegen für jeden lesbar da;
  Geheimhaltung ist bauartbedingt unmöglich.
- Ein Cloudflare Worker ist das einzige serverseitige Stück. Er hält den
  GitHub-Token, den eine statische Seite nicht haben darf.
- Rund 15 Minuten Handarbeit pro Woche sind eingeplant: Prüfliste durchsehen,
  Meldungen freigeben, Quellenstatus prüfen.
- Meldungen von außen laufen über ein Formular in ein GitHub-Issue und werden
  erst mit dem Etikett `freigegeben` übernommen.

## Capabilities and Constraints

**Wartungsarmut ist das oberste Kriterium.** Es steht über Funktionsumfang,
Vollständigkeit und Eleganz. Jede Erweiterung wird daran gemessen, was sie im
Störungsfall an Arbeit erzeugt.

- **Zuständigkeiten sind getrennt:** `daten/events.json` gehört dem
  Sammellauf und wird jede Nacht neu geschrieben. Eingriffe von Hand stehen in
  `daten/verwaltung.json` und werden erst beim Bauen darübergelegt. Automatik
  darf Handarbeit nie überschreiben — das ist einmal schiefgegangen und hat 13
  Termine gelöscht.
- **Vier Einstufungen:** `frei`, `spende`, `vermutlich`, `kosten`. Alles ohne
  ausdrücklichen Preis gilt zunächst als „vermutlich kostenfrei". Nur eine
  ausdrückliche Preisprüfung hebt eine Vermutung zur Zusage.
- **Zwei Terminarten:** *Dauertermine* laufen über Wochen (Ausstellungen,
  Sportprogramme). *Einzeltermine* sind einzelne Anlässe — auch wenn sie
  regelmäßig wiederkehren. Eine monatliche Führung ist ein Einzeltermin, kein
  Dauertermin.
- **Keine Veranstaltungen:** Wochenmarkt, Mittagskarten und Hinweise auf Essen
  oder Essensaktionen. Eine Veranstaltung, die nebenbei Essen erwähnt, bleibt
  eine Veranstaltung.
- Alles auf Deutsch, in der Sie-Form.
- **Mehrere Zugänge:** Jede pflegende Person meldet sich mit eigenem Namen und
  eigenem Passwort an. Der Cloudflare Worker prüft gegen eine Zugangsliste und
  schreibt den Namen in die Commit-Nachricht — der Git-Verlauf ist damit der
  belastbare Nachweis, wer wann was geändert hat. Die Namen, die zusätzlich in
  `verwaltung.json` stehen, sind Anzeigekomfort und keine Sicherheitsgrenze:
  Alle Pflegenden sind vertraute Personen mit vollem Zugriff.

## Brand Commitments

- Name: **Gratis in Freising**
- Hauptfarbe **#3b91db** zu Schwarz (von der Betreiberin festgelegt)
- **Monospace**-Schrift als tragendes Schriftbild (von der Betreiberin
  festgelegt)
- Keine externen Schriften, Bibliotheken oder CDN-Abhängigkeiten: Die Seiten
  sollen ohne Nachladen funktionieren.

## Evidence on Hand

- `daten/events.json` — 139 Termine aus 10 aktiven Quellen
- `quellen.yml` — 23 geprüfte Quellen, davon 10 nutzbar, mit Messwerten
- `ausgabe/` — Kalenderdateien, Tagesmail, Prüfliste, Social-Entwürfe
- `daten/quellen-status.json` — Gesundheitsverlauf je Quelle

**Nicht vorhanden und nicht zu erfinden:** Nutzerzahlen, Abonnentenzahlen,
Presseerwähnungen, Empfehlungen, Partnerschaften mit der Stadt oder mit
Veranstaltern.

## Ausbaustufen (entschieden am 22.08.2026)

Das Ziel ist eine Plattform mit Konten, Rollen, Veranstaltereinreichung,
Werbekunden, Kampagnen und Rechnungen. Der Weg dorthin ist **stufenweise und
an Belege geknüpft**, nicht an Absicht.

1. **Bestehend:** Sammellauf, Kalender, Tagesmail, öffentliche Übersicht,
   interner Bereich.
2. **Als Nächstes, in der heutigen Bauart:** eigene Zugänge je Pflegender,
   Event-Detailseite mit Teilen-Knöpfen, Einreichung mit sichtbarem Status für
   Veranstalter, Kategorienpflege.
3. **Neubau, erst wenn Stufe 2 im Betrieb ist und Veranstalter tatsächlich von
   sich aus einreichen:** Konten, Rollen, Werbekunden, Kampagnen, Rechnungen,
   Metriken. Das braucht Datenbank und Server; die heutige Bauart ohne Server
   kann es nicht tragen.

Was Stufe 3 auslöst, ist eine Beobachtung, keine Frist: nennenswert viele
Einreichungen von Fremden. Bleiben sie aus, ist eine Nutzerverwaltung Ballast.

Stufe 2 wird so gebaut, dass die Daten später umziehen können: stabile IDs,
festgehaltenes Wer und Wann, kein Format, das sich nicht in Tabellen überführen
lässt.

**Zwei Dinge, die Stufe 3 voraussetzt und die heute nicht gelten:** Werbekunden
zahlen für Reichweite, die es beim heutigen kleinen Leserkreis nicht gibt — ob
Reichweite dann ein Ziel wird, ist offen. Und sobald Geld fließt, kommen
Impressum, AGB, Rechnungspflichtangaben und DSGVO-Pflichten dazu, die kein Code
abnimmt.

## Product Principles

1. **Wartungsarmut schlägt Funktionsumfang.** Was im Störungsfall Handarbeit
   erzeugt, ist teurer als es aussieht.
2. **Ein fälschlich als gratis ausgewiesener Termin ist schlimmer als ein
   verpasster.** Im einen Fall entgeht jemandem eine Gelegenheit, im anderen
   steht er vor der Kasse.
3. **Jede Einstufung zeigt auf ihren Beleg.** Vermutung und Zusage sind sichtbar
   verschiedene Dinge.
4. **Automatik überschreibt Handarbeit nie.** Wer hingesehen hat, behält recht.
5. **Was öffentlich liegt, ist öffentlich.** Nichts bauen, das Geheimhaltung
   voraussetzt.

## Accessibility & Inclusion

Kein förmlicher Standard vereinbart. Als Arbeitsgrundlage gilt WCAG AA für
Kontraste, weil die Oberflächen viel kleine Schrift verwenden — die Hauptfarbe
erreicht auf Weiß nur 3,36:1 und wird deshalb für Text durch eine dunklere
Abstufung ersetzt.
