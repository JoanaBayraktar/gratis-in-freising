#!/usr/bin/env python3
"""Laesst das Modell zum Schluss ueber die fertige Liste sehen.

    MISTRAL_API_KEY=... python3 scripts/nachpruefen.py
    MISTRAL_API_KEY=... python3 scripts/nachpruefen.py --nur-melden

Warum ein zweiter Durchgang? Beim Sammeln sieht das Modell immer nur eine
Seite. Es kann deshalb nicht wissen, dass dieselbe Veranstaltung beim Merkur
schon steht, dass der Ort dort anders geschrieben wird oder dass eine Quelle
sie gratis nennt und die andere nicht. Diese Fragen lassen sich erst
beantworten, wenn alles beieinanderliegt — und genau dann kosten sie fast
nichts, weil nur noch Stichworte je Veranstaltung uebertragen werden und keine
Webseiten mehr.

Drei Fragen, drei verschiedene Konsequenzen:

  Ort          wird uebernommen. Ein Ortsname ist Anzeigetext; ihn zu
               vereinheitlichen kann nichts kaputtmachen.
  Widerspruch  wird NICHT uebernommen, sondern zur Pruefung vorgelegt. Ob eine
               Veranstaltung Geld kostet, entscheidet der Beleg auf der Seite,
               nicht die Vermutung eines Modells.
  Dublette     wird uebernommen, wenn beide Eintraege dieselbe Quelladresse
               oder denselben Ort haben — sonst vorgelegt. Falsch verschmolzen
               heisst: eine Veranstaltung ist weg, und niemand merkt es.

Jede Entscheidung steht hinterher in ausgabe/NACHPRUEFUNG.md, auch die
uebernommenen. Automatik, die man nicht nachlesen kann, ist keine Hilfe.
"""
import json
import os
import pathlib
import sys
from datetime import date, datetime

import yaml

from sammeln import (SICHERHEIT, modell_antwort, ort_vereinheitlichen,
                     ort_woerter, tage, verschmelzen)

BASIS = pathlib.Path(__file__).resolve().parent.parent
DATEN = BASIS / "daten" / "events.json"
QUELLEN = BASIS / "quellen.yml"
BERICHT = BASIS / "ausgabe" / "NACHPRUEFUNG.md"

# Mehr als das passt nicht sinnvoll in einen Aufruf, und weiter voraus lohnt
# die Pruefung ohnehin nicht — was in drei Monaten stattfindet, aendert sich
# bis dahin noch.
MAX_EVENTS = 120

PROMPT = """Du bekommst eine bereits gesammelte Liste von Veranstaltungen aus
Freising. Jede Zeile ist eine Veranstaltung mit einer Nummer. Deine Aufgabe ist
NICHT, neue Veranstaltungen zu finden, sondern drei Dinge in der vorhandenen
Liste zu erkennen.

1. DUBLETTEN. Steht dieselbe Veranstaltung mehrfach drin, weil zwei Portale sie
   verschieden benennen oder verschieden datieren? Gib die Nummern zusammen an.

   Vorsicht bei Reihen: "Karaoke mit Stefan" am 30.10. und am 20.11. sind ZWEI
   Abende, keine Dublette. Ebenso ist eine Fuehrung oder Vernissage INNERHALB
   einer laufenden Ausstellung eine eigene Veranstaltung, keine Dublette der
   Ausstellung. Im Zweifel: keine Dublette.

2. WIDERSPRUECHE beim Eintritt. Wird dieselbe Veranstaltung einmal als gratis
   und einmal als kostenpflichtig gefuehrt? Oder ist eine Veranstaltung als
   kostenpflichtig eingestuft, die ihrer Art nach ueblicherweise frei ist
   (offener Treff, Selbsthilfegruppe, Gottesdienst, oeffentliche Sitzung) —
   oder umgekehrt? Nenne die Nummer und was dagegen spricht.

3. ORTE. Zu jeder Veranstaltung steht der Ortsname, wie ihn die Quelle nennt.
   Du bekommst ausserdem eine Liste bereits bekannter Orte. Meint ein Ortsname
   einen der bekannten Orte, gib den bekannten Namen zurueck. Nur wenn es
   erkennbar ein anderes Haus ist, lass ihn weg.

   "Stadtbibliothek" und "Stadtbibliothek Freising" sind derselbe Ort.
   "Pfarrheim Neustift" und "Pfarrheim St. Georg" sind es nicht.

Erfinde nichts. Findest du zu einem Punkt nichts, gib eine leere Liste zurueck —
das ist ein gutes Ergebnis und kein Versaeumnis.
""" + SICHERHEIT

SCHEMA = {
    "type": "object",
    "properties": {
        "dubletten": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "nummern": {"type": "array", "items": {"type": "integer"}},
                    "begruendung": {"type": "string"},
                },
                "required": ["nummern", "begruendung"],
            },
        },
        "widersprueche": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "nummer": {"type": "integer"},
                    "vermutet": {"type": "string",
                                 "enum": ["frei", "spende", "kostenpflichtig", "unklar"]},
                    "begruendung": {"type": "string"},
                },
                "required": ["nummer", "vermutet", "begruendung"],
            },
        },
        "orte": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "nummer": {"type": "integer"},
                    "bekannter_ort": {"type": "string"},
                },
                "required": ["nummer", "bekannter_ort"],
            },
        },
    },
    "required": ["dubletten", "widersprueche", "orte"],
}


def zeile(nummer: int, ev: dict) -> str:
    beginn, ende = tage(ev)
    wann = beginn if ende == beginn else f"{beginn} bis {ende}"
    beleg = ev.get("eintritt_beleg") or "kein Beleg"
    if beleg.startswith("Keine Preisangabe"):
        beleg = "kein Beleg, Hausregel der Quelle"
    return (f"{nummer}. {ev['titel']}\n"
            f"   wann: {wann} | ort: {ev.get('ort_name') or '—'}"
            f" | quelle: {ev.get('quelle_name')}\n"
            f"   eintritt: {ev.get('eintritt')} ({ev.get('eintritt_confidence')})"
            f" | beleg: {beleg[:90]}")


def bekannte_orte(events: list, tabelle: dict) -> list:
    """Die gepflegten Orte plus alles, was mehrfach gleich geschrieben wurde."""
    zaehler = {}
    for ev in events:
        name = ev.get("ort_name")
        if name:
            zaehler[name] = zaehler.get(name, 0) + 1
    namen = list(tabelle)
    for name, n in sorted(zaehler.items(), key=lambda x: -x[1]):
        # Einmalige Schreibweisen sind gerade die Kandidaten fuer einen Fehler
        # und taugen deshalb nicht als Referenz.
        if n >= 2 and name not in namen and ort_woerter(name):
            namen.append(name)
    return namen


def zusammenlegen(events: list, gruppe: list, bericht: list, streng: bool) -> set:
    """Eine vom Modell gemeldete Dublettengruppe verschmelzen."""
    teile = [events[n] for n in gruppe if 0 <= n < len(events)]
    if len(teile) < 2:
        return set()

    if any(ev.get("manuell_bestaetigt") for ev in teile):
        bericht.append("  übergangen: enthält einen von Hand bestätigten Eintrag")
        return set()

    if streng:
        # Ein gemeinsames Merkmal ausser dem Urteil des Modells: dieselbe
        # Adresse oder derselbe Ort. Ohne das bleibt es ein Vorschlag.
        adressen = [ev.get("quelle_url") for ev in teile]
        orte = [ort_woerter(ev.get("ort_name")) for ev in teile]
        gleich = (len(set(adressen)) == 1 and adressen[0]
                  or all(o and o & orte[0] for o in orte))
        if not gleich:
            bericht.append("  nur gemeldet, nicht verschmolzen: "
                           "weder gleiche Adresse noch gleicher Ort")
            return set()

    behalten = max(teile, key=lambda ev: (len(ev.get("beschreibung") or ""),
                                          len(ev.get("quellen_weitere") or [])))
    for ev in teile:
        if ev is not behalten:
            verschmelzen(behalten, ev)
    return {id(ev) for ev in teile if ev is not behalten}


def main() -> None:
    nur_melden = "--nur-melden" in sys.argv
    if not os.environ.get("MISTRAL_API_KEY"):
        sys.exit("MISTRAL_API_KEY ist nicht gesetzt.")

    konfig = yaml.safe_load(QUELLEN.read_text(encoding="utf-8"))
    tabelle = konfig.get("orte") or {}
    daten = json.loads(DATEN.read_text(encoding="utf-8"))

    heute = date.today().isoformat()
    kommend = [ev for ev in daten["events"]
               if tage(ev)[1] >= heute and ev.get("status") != "verschwunden"]
    kommend.sort(key=lambda ev: ev["beginn"])
    kommend = kommend[:MAX_EVENTS]
    if not kommend:
        print("Nichts zu pruefen.")
        return

    orte = bekannte_orte(kommend, tabelle)
    text = ("Bekannte Orte:\n" + "\n".join(f"- {o}" for o in orte)
            + "\n\nVeranstaltungen:\n"
            + "\n".join(zeile(i, ev) for i, ev in enumerate(kommend)))

    print(f"{len(kommend)} Veranstaltungen, {len(orte)} bekannte Orte "
          f"({len(text)} Zeichen)")
    antwort = modell_antwort(PROMPT, text, SCHEMA, "nachpruefung")

    bericht = [f"# Nachprüfung {datetime.now():%d.%m.%Y %H:%M}", "",
               f"{len(kommend)} kommende Veranstaltungen geprüft.", ""]
    entfernen = set()

    gruppen = antwort.get("dubletten") or []
    bericht += ["## Dubletten", ""] if gruppen else ["## Dubletten", "", "_Keine._", ""]
    for g in gruppen:
        nummern = g.get("nummern") or []
        titel = [kommend[n]["titel"] for n in nummern if 0 <= n < len(kommend)]
        bericht.append(f"- {' + '.join(repr(t) for t in titel)}")
        bericht.append(f"  {g.get('begruendung')}")
        if not nur_melden:
            entfernen |= zusammenlegen(kommend, nummern, bericht, streng=True)
    bericht.append("")

    wid = antwort.get("widersprueche") or []
    bericht += ["## Widersprüche beim Eintritt", ""]
    bericht.append("Diese Fälle werden **nicht** automatisch geändert — der Beleg "
                   "auf der Seite entscheidet, nicht die Vermutung des Modells.")
    bericht.append("")
    for w in wid:
        n = w.get("nummer")
        if not (isinstance(n, int) and 0 <= n < len(kommend)):
            continue
        ev = kommend[n]
        bericht.append(f"- **{ev['titel']}** ({tage(ev)[0]})")
        bericht.append(f"  eingestuft als `{ev.get('eintritt')}`, "
                       f"vermutet `{w.get('vermutet')}` — {w.get('begruendung')}")
        bericht.append(f"  {ev.get('quelle_url') or ''}")
    if not wid:
        bericht.append("_Keine._")
    bericht.append("")

    geaendert = 0
    bericht += ["## Orte vereinheitlicht", ""]
    for o in antwort.get("orte") or []:
        n = o.get("nummer")
        if not (isinstance(n, int) and 0 <= n < len(kommend)):
            continue
        ev = kommend[n]
        neu = ort_vereinheitlichen(o.get("bekannter_ort"), tabelle)
        alt = ev.get("ort_name")
        if not neu or neu == alt or ev.get("manuell_bestaetigt"):
            continue
        # Nur zuordnen, was erkennbar dasselbe Haus meint.
        if ort_woerter(alt) and not (ort_woerter(alt) & ort_woerter(neu)):
            bericht.append(f"- übergangen: {alt!r} → {neu!r} (kein gemeinsames Wort)")
            continue
        bericht.append(f"- {alt!r} → {neu!r} ({ev['titel'][:44]})")
        if not nur_melden:
            ev["ort_name"] = neu
            geaendert += 1
    if geaendert == 0 and len(bericht) and bericht[-1] == "":
        bericht.append("_Nichts zu ändern._")
    bericht.append("")

    if entfernen:
        daten["events"] = [ev for ev in daten["events"] if id(ev) not in entfernen]

    if not nur_melden:
        with DATEN.open("w", encoding="utf-8") as datei:
            json.dump(daten, datei, ensure_ascii=False, indent=2)
            datei.write("\n")

    BERICHT.parent.mkdir(exist_ok=True)
    BERICHT.write_text("\n".join(bericht) + "\n", encoding="utf-8")
    print(f"  {len(gruppen)} Dublettenmeldungen, davon {len(entfernen)} verschmolzen")
    print(f"  {len(wid)} Widersprüche zur Prüfung vorgelegt")
    print(f"  {geaendert} Ortsnamen vereinheitlicht")
    print(f"  Bericht: {BERICHT.relative_to(BASIS)}")


if __name__ == "__main__":
    main()
