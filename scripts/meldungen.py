#!/usr/bin/env python3
"""Uebernimmt freigegebene Meldungen aus GitHub-Issues in die Eventliste.

    GITHUB_TOKEN=... GITHUB_REPOSITORY=besitzer/repo python3 scripts/meldungen.py
    python3 scripts/meldungen.py --nur-melden     nichts schreiben, nur zeigen

Der Weg einer Meldung:

  1. Jemand traegt sie auf der Uebersichtsseite ein oder legt direkt ein Issue
     an. Beides erzeugt ein Issue mit dem Etikett `meldung`.
  2. Sie sehen es an, und wenn es stimmt, haengen Sie `freigegeben` dran.
  3. Der naechste Lauf holt es hier ab, schreibt es in events.json und
     schliesst das Issue mit einem Kommentar.

Der zweite Schritt ist der Sinn der Sache. Ohne ihn koennte jede beliebige
Person schreiben, was in Ihrem Kalender steht — und der Kalender wird
veroeffentlicht. Ein Issue ohne `freigegeben` wird deshalb nie angefasst,
egal was drinsteht.

Uebernommene Meldungen bekommen `manuell_bestaetigt: true`: Sie haben sie
geprueft, also darf der naechtliche Lauf sie nicht wieder umstufen.
"""
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime

from event_id import event_id

BASIS = pathlib.Path(__file__).resolve().parent.parent
DATEN = BASIS / "daten" / "events.json"

ETIKETT = "freigegeben"
API = "https://api.github.com"

EINTRITT = {
    "eintritt frei": "frei",
    "spende erbeten": "spende",
    "weiß ich nicht": "unklar",
    "weiss ich nicht": "unklar",
}


def github(pfad: str, methode: str = "GET", inhalt: dict = None):
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        sys.exit("GITHUB_TOKEN ist nicht gesetzt.")
    daten = json.dumps(inhalt).encode("utf-8") if inhalt is not None else None
    anfrage = urllib.request.Request(f"{API}{pfad}", data=daten, method=methode, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
    })
    with urllib.request.urlopen(anfrage, timeout=30) as antwort:
        roh = antwort.read()
    return json.loads(roh) if roh else None


def abschnitte(text: str) -> dict:
    """Die `### Ueberschrift`-Bloecke eines Issue-Formulars einlesen.

    Sowohl das Formular auf der Uebersichtsseite als auch GitHubs eigenes
    Issue-Formular erzeugen dieses Format. Eine Ueberschrift, unter der nichts
    oder nur ein Platzhalter steht, gilt als leer.
    """
    gefunden = {}
    teile = re.split(r"^###\s+(.+?)\s*$", text or "", flags=re.M)
    for name, inhalt in zip(teile[1::2], teile[2::2]):
        # Alles ab einer Trennlinie ist Fussnote des Formulars, nicht Inhalt.
        wert = re.split(r"^---\s*$", inhalt, flags=re.M)[0].strip()
        if wert.lower() in ("", "_no response_", "_none_", "_keine_", "_keiner_",
                            "_nicht angegeben_", "n/a"):
            continue
        gefunden[name.strip().lower()] = wert
    return gefunden


def zeitpunkt(wann: str) -> tuple:
    """"2026-09-12, 19:30 Uhr" -> ISO-Zeitstempel und ob ganztaegig."""
    text = wann or ""
    datum = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", text)
    if datum:
        jahr, monat, tag = datum.groups()
    else:
        # Auch die deutsche Schreibweise annehmen — sie wird getippt werden.
        datum = re.search(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", text)
        if not datum:
            return None, False
        tag, monat, jahr = datum.groups()

    # Das Datum aus dem Text nehmen, bevor nach der Uhrzeit gesucht wird:
    # "12.09.2026 20:00" enthaelt sonst mit "12.09" schon etwas Uhrzeitfoermiges.
    rest = text[:datum.start()] + " " + text[datum.end():]
    uhr = re.search(r"(\d{1,2})[:.](\d{2})", rest)
    if uhr:
        stunde, minute = uhr.groups()
        return (f"{jahr}-{int(monat):02d}-{int(tag):02d}"
                f"T{int(stunde):02d}:{minute}:00"), False
    return f"{jahr}-{int(monat):02d}-{int(tag):02d}T00:00:00", True


def bauen(issue: dict) -> dict:
    felder = abschnitte(issue.get("body") or "")
    titel = felder.get("titel") or ""
    beginn, ganztaegig = zeitpunkt(felder.get("wann", ""))
    if not titel or not beginn:
        return None

    eintritt = EINTRITT.get((felder.get("eintritt") or "").lower(), "unklar")
    return {
        "titel": titel,
        "beginn": beginn,
        "ende": beginn,
        "ganztaegig": ganztaegig,
        "ort_name": felder.get("wo"),
        "ort_adresse": None,
        "veranstalter": None,
        "beschreibung": felder.get("beschreibung"),
        "kategorie": "Sonstiges",
        "zielgruppe": "Alle",
        "drinnen_draussen": None,
        "anmeldung_noetig": False,
        "ausgebucht": False,
        "dauertermin": False,
        "besonderheit": None,
        "anmeldung_url": None,
        "bild_url": None,
        "quelle_url": felder.get("link") or issue["html_url"],
        "quellen_weitere": [],
        "quelle_name": f"Meldung #{issue['number']}",
        "eintritt": eintritt,
        "eintritt_beleg": (f"Von Hand freigegeben nach Meldung #{issue['number']} "
                           f"von @{issue['user']['login']}."),
        "eintritt_confidence": "hoch" if eintritt != "unklar" else "niedrig",
        "id": event_id(titel, beginn, felder.get("wo") or ""),
        "social_text": None,
        "status": "aktiv",
        "zuerst_gesehen": datetime.now().date().isoformat(),
        "zuletzt_gesehen": datetime.now().date().isoformat(),
        # Sie haben freigegeben — der Sammellauf fasst das nicht mehr an.
        "manuell_bestaetigt": True,
    }


def main() -> None:
    nur_melden = "--nur-melden" in sys.argv
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not repo:
        sys.exit("GITHUB_REPOSITORY ist nicht gesetzt (Form: besitzer/repo).")

    offen = github(f"/repos/{repo}/issues?state=open&labels={ETIKETT}&per_page=50") or []
    # Die API liefert unter /issues auch Pull Requests. Die gehoeren nicht hierher.
    offen = [i for i in offen if "pull_request" not in i]
    if not offen:
        print("Keine freigegebenen Meldungen.")
        return

    daten = json.loads(DATEN.read_text(encoding="utf-8"))
    vorhanden = {ev.get("id") for ev in daten["events"]}
    neu = 0

    for issue in offen:
        ereignis = bauen(issue)
        if ereignis is None:
            print(f"  #{issue['number']}: Titel oder Datum fehlt — übersprungen")
            continue
        if ereignis["id"] in vorhanden:
            print(f"  #{issue['number']}: steht schon in der Liste")
            hinweis = "Steht bereits in der Liste — Meldung geschlossen."
        else:
            daten["events"].append(ereignis)
            vorhanden.add(ereignis["id"])
            neu += 1
            print(f"  #{issue['number']}: übernommen — {ereignis['titel']} "
                  f"am {ereignis['beginn'][:10]}")
            hinweis = (f"Übernommen: **{ereignis['titel']}** am "
                       f"{ereignis['beginn'][:10]}. Erscheint mit dem nächsten "
                       f"Kalender- und Mailbau. Danke fürs Melden!")

        if nur_melden:
            continue
        github(f"/repos/{repo}/issues/{issue['number']}/comments",
               "POST", {"body": hinweis})
        github(f"/repos/{repo}/issues/{issue['number']}",
               "PATCH", {"state": "closed"})

    if neu and not nur_melden:
        daten["events"].sort(key=lambda ev: ev.get("beginn") or "")
        with DATEN.open("w", encoding="utf-8") as datei:
            json.dump(daten, datei, ensure_ascii=False, indent=2)
            datei.write("\n")
    print(f"{neu} Meldungen übernommen.")


if __name__ == "__main__":
    main()
