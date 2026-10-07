#!/usr/bin/env python3
"""Validiert den Bestand und archiviert Termine, die seit 30 Tagen vorbei sind.

    python scripts/datenpflege.py             # nur pruefen, nichts schreiben
    python scripts/datenpflege.py --schreiben # normalisieren und archivieren

IDs, manuelle Korrekturen und Quellenbelege bleiben erhalten. Der effektive
Endtermin nach manueller Korrektur entscheidet, ob ein Termin ins Archiv darf.
"""
import argparse
import copy
import json
import pathlib
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from jsonschema import Draft202012Validator, FormatChecker

BASIS = pathlib.Path(__file__).resolve().parent.parent
SCHEMA = json.loads((BASIS / "daten/events.schema.json").read_text(encoding="utf-8"))
EVENT_SCHEMA = SCHEMA["$defs"]["event"]
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FormatChecker())
EVENT_VALIDATOR = Draft202012Validator(EVENT_SCHEMA, format_checker=FormatChecker())
ALIASE = {
    "drinnen_draußen": "drinnen_draussen",
    "drinnen_drauben": "drinnen_draussen",
    "drinnen_drauchen": "drinnen_draussen",
    "dauertermine": "dauertermin",
    "dauerterm": "dauertermin",
    "ausgebukt": "ausgebucht",
}
STANDARD = {
    "ende": None, "ganztaegig": False, "ort_name": None, "ort_adresse": None,
    "veranstalter": None, "beschreibung": None, "kategorie": "Sonstiges",
    "zielgruppe": "Alle", "drinnen_draussen": None, "anmeldung_noetig": False,
    "ausgebucht": False, "dauertermin": False, "besonderheit": None,
    "anmeldung_url": None, "bild_url": None, "social_text": None,
    "quellen_weitere": [], "manuell_bestaetigt": False,
}


def heute_berlin():
    return datetime.now(ZoneInfo("Europe/Berlin")).date()


def lesen(pfad):
    return json.loads(pfad.read_text(encoding="utf-8"))


def normalisieren(event):
    """Nur bekannte Schreibvarianten und fehlende optionale Felder reparieren.

    Bei widerspruechlichen Aliaswerten gewinnt das korrekt benannte Feld.
    Unbekannte Felder und ungueltige Werte werden nicht still entfernt.
    """
    ev = copy.deepcopy(event)
    for alias, richtig in ALIASE.items():
        if alias in ev:
            wert = ev.pop(alias)
            if richtig not in ev or ev[richtig] is None:
                ev[richtig] = wert
    if ev.get("drinnen_draussen") == "draußen":
        ev["drinnen_draussen"] = "draussen"
    for feld, standard in STANDARD.items():
        ev.setdefault(feld, copy.deepcopy(standard))
    return ev


def event_pruefen(event):
    EVENT_VALIDATOR.validate(event)
    start = datetime.fromisoformat(event["beginn"])
    if event.get("ende") and datetime.fromisoformat(event["ende"]) < start:
        raise ValueError(f"{event['id']}: Ende liegt vor Beginn")


def pruefen(bestand):
    VALIDATOR.validate(bestand)
    ids = set()
    for ev in bestand["events"]:
        event_pruefen(ev)
        if ev["id"] in ids:
            raise ValueError(f"Doppelte ID: {ev['id']}")
        ids.add(ev["id"])


def mit_archiv(bestand, archiv):
    """Beim Sammeln auch fruehere Termine wiedererkennen, statt sie neu anzulegen.

    Eine Quelle kann einen archivierten Termin erneut liefern oder verlaengern.
    Die Datenpflege verteilt danach wieder nach dem aktuellen Ende.
    """
    daten = copy.deepcopy(bestand)
    ids = {ev["id"] for ev in daten["events"]}
    for pfad in sorted(archiv.glob("[0-9][0-9][0-9][0-9].json")):
        for ev in lesen(pfad)["events"]:
            if ev["id"] not in ids:
                daten["events"].append(ev)
                ids.add(ev["id"])
    return daten


def vorbereiten(bestand, verwaltung, heute, behalten_tage=30):
    daten = copy.deepcopy(bestand)
    daten["schema_version"] = 2
    daten.setdefault("laeufe", [])
    daten["events"] = [normalisieren(ev) for ev in daten["events"]]
    pruefen(daten)
    aktiv, archiv = [], {}
    grenze = heute - timedelta(days=behalten_tage)
    for ev in daten["events"]:
        effektiv = dict(ev)
        # Ausblenden ist keine Loeschung. Nur die korrigierten Daten bestimmen
        # den Zeitraum; ausgeblendete Termine werden ebenfalls aufbewahrt.
        korrektur = (verwaltung.get("korrekturen") or {}).get(ev["id"], {})
        for feld in ("beginn", "ende"):
            if feld in korrektur:
                effektiv[feld] = korrektur[feld]
        event_pruefen(effektiv)
        ende = max(effektiv["beginn"][:10], (effektiv.get("ende") or "")[:10])
        endtag = date.fromisoformat(ende)
        if endtag < heute and ev["status"] == "aktiv":
            ev["status"] = "vergangen"
        elif endtag >= heute and ev["status"] == "vergangen":
            ev["status"] = "aktiv"
        if endtag < grenze:
            jahr = ev["beginn"][:4]
            archiv.setdefault(jahr, []).append(ev)
        else:
            aktiv.append(ev)
    daten["events"] = sorted(aktiv, key=lambda e: (e["beginn"], e["id"]))
    for events in archiv.values():
        events.sort(key=lambda e: (e["beginn"], e["id"]))
    return daten, archiv


def verwaltung_pruefen(verwaltung, bestand):
    from verwaltung import KORRIGIERBAR, anwenden

    for kennung, korrektur in (verwaltung.get("korrekturen") or {}).items():
        for feld, wert in korrektur.items():
            if feld not in KORRIGIERBAR:
                raise ValueError(f"{kennung}: Feld {feld!r} darf nicht korrigiert werden")
            Draft202012Validator(EVENT_SCHEMA["properties"][feld]).validate(wert)
    # Eigene Termine haben weniger Metadaten, aber dieselben Inhaltsregeln.
    for ev in verwaltung.get("eigene") or []:
        fertig = normalisieren(ev)
        fertig.setdefault("quelle_name", "Manuell")
        fertig.setdefault("quelle_url", None)
        fertig.setdefault("status", "aktiv")
        fertig.setdefault("zuerst_gesehen", ev.get("beginn", "")[:10])
        fertig.setdefault("zuletzt_gesehen", ev.get("beginn", "")[:10])
        fertig.setdefault("eintritt", "unklar")
        fertig.setdefault("eintritt_beleg", None)
        fertig.setdefault("eintritt_confidence", "niedrig")
        event_pruefen(fertig)
    for ev in anwenden(bestand["events"], verwaltung, laut=False):
        # Auch falsche Zeitraeume durch Kombination zweier gueltiger Felder
        # erkennen. Eigene werden oben vollstaendig geprueft.
        if ev.get("ende") and ev["ende"] < ev["beginn"]:
            raise ValueError(f"{ev['id']}: korrigiertes Ende liegt vor Beginn")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schreiben", action="store_true")
    parser.add_argument("--heute", type=date.fromisoformat, default=heute_berlin())
    args = parser.parse_args()
    pfad = BASIS / "daten/events.json"
    archivpfad = BASIS / "daten/archiv"
    bestand = lesen(pfad)
    verwaltung = lesen(BASIS / "daten/verwaltung.json")
    if not args.schreiben:
        pruefen(bestand)
        alle = copy.deepcopy(bestand)
        for archivdatei in sorted(archivpfad.glob("*.json")):
            archivbestand = lesen(archivdatei)
            pruefen(archivbestand)
            alle["events"].extend(archivbestand["events"])
        pruefen(alle)
        verwaltung_pruefen(verwaltung, alle)
        print(f"Gueltig: {len(bestand['events'])} im Arbeitsbestand, "
              f"{len(alle['events']) - len(bestand['events'])} im Archiv.")
        return

    alle = mit_archiv(bestand, archivpfad)
    daten, jahre = vorbereiten(alle, verwaltung, args.heute)
    verwaltung_pruefen(verwaltung, {**daten, "events": [normalisieren(e) for e in alle["events"]]})
    # Erst alles pruefen, dann schreiben. Alte Archivjahre bleiben lesbar.
    archivpfad.mkdir(exist_ok=True)
    for jahr in set(jahre) | {p.stem for p in archivpfad.glob("*.json")}:
        inhalt = {"schema_version": 2, "events": jahre.get(jahr, []), "laeufe": []}
        (archivpfad / f"{jahr}.json").write_text(
            json.dumps(inhalt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    pfad.write_text(json.dumps(daten, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Datenpflege: {len(daten['events'])} im Arbeitsbestand, "
          f"{sum(map(len, jahre.values()))} archiviert.")


if __name__ == "__main__":
    main()
