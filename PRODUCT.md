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

**Weitere Pflegende (bestätigt, noch nicht gebaut).** Mehrere Personen sollen
eintragen und korrigieren können. Der heutige Stand — ein geteiltes Passwort im
Cloudflare Worker — trägt das nicht: Er trennt keine Zugänge und hält nicht
fest, wer was geändert hat. Offene Produktentscheidung, siehe unten.

**Leserinnen und Leser: ein kleiner, bekannter Kreis.** Kein breites
Stadtpublikum. Sie bekommen die Tagesmail, abonnieren den Kalender oder sehen
auf die Übersichtsseite. Reichweite ist ausdrücklich kein Ziel.

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
- **Offen:** Wie mehrere Pflegende getrennte Zugänge bekommen. Bestätigt ist,
  dass es sie geben soll; die Bauart ist nicht entschieden.

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
