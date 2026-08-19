#!/usr/bin/env python3
"""Erzeugt die stabile Event-ID fuer die Dublettenerkennung.

    python3 scripts/event_id.py "Titel" "2026-08-28" "Ort"

Dieselbe Veranstaltung muss auf mehreren Quellseiten dieselbe ID ergeben,
darum wird vorher hart normalisiert.
"""
import hashlib
import sys
import unicodedata

UMLAUTE = {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}


def normalisieren(text: str) -> str:
    text = (text or "").lower()
    for umlaut, ersatz in UMLAUTE.items():
        text = text.replace(umlaut, ersatz)
    # Restliche Akzente abstreifen (café -> cafe)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return "".join(c for c in text if c.isalnum())


def event_id(titel: str, datum: str, ort: str) -> str:
    # Nur das Datum zaehlt, nicht die Uhrzeit: Quellen weichen bei
    # Einlass- vs. Beginnzeit gern um 30 Minuten voneinander ab.
    datum = (datum or "")[:10]
    roh = f"{normalisieren(titel)}|{datum}|{normalisieren(ort)}"
    return hashlib.sha1(roh.encode("utf-8")).hexdigest()[:16]


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(__doc__, file=sys.stderr)
        sys.exit(1)
    print(event_id(sys.argv[1], sys.argv[2], sys.argv[3]))
