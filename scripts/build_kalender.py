#!/usr/bin/env python3
"""Baut aus daten/events.json die Ausgabedateien.

    python3 scripts/build_kalender.py

Erzeugt in ausgabe/:
  gratis-freising.ics  — nur gesicherte Gratis-Events (oeffentlich abonnierbar)
  pruefen.ics          — unklare Faelle und Spendenbasis, zur Sichtung
  PRUEFLISTE.md        — dieselben Faelle als lesbare Liste mit Belegzitat

Bewusst ohne externe Bibliotheken: nur Python-Standardbibliothek, damit hier
nichts durch ein Paket-Update kaputtgehen kann.
"""
import json
import pathlib
from datetime import datetime, timedelta, timezone

from regeln import BESCHRIFTUNG, FREI, KOSTEN, SPENDE, VERMUTLICH, anzeige

BASIS = pathlib.Path(__file__).resolve().parent.parent
DATEN = BASIS / "daten" / "events.json"
AUSGABE = BASIS / "ausgabe"

# Statische Zeitzonendefinition. Aendert sich nur, wenn die EU die
# Zeitumstellung abschafft.
VTIMEZONE = """BEGIN:VTIMEZONE
TZID:Europe/Berlin
BEGIN:DAYLIGHT
TZOFFSETFROM:+0100
TZOFFSETTO:+0200
TZNAME:CEST
DTSTART:19700329T020000
RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU
END:DAYLIGHT
BEGIN:STANDARD
TZOFFSETFROM:+0200
TZOFFSETTO:+0100
TZNAME:CET
DTSTART:19701025T030000
RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU
END:STANDARD
END:VTIMEZONE"""


def escape(text) -> str:
    """Sonderzeichen nach RFC 5545 maskieren."""
    if text is None:
        return ""
    return (
        str(text)
        .replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
    )


def falten(zeile: str) -> str:
    """Zeilen auf 75 Oktett begrenzen, Fortsetzung mit fuehrendem Leerzeichen."""
    roh = zeile.encode("utf-8")
    if len(roh) <= 75:
        return zeile
    teile, rest = [], roh
    teile.append(rest[:75])
    rest = rest[75:]
    while rest:
        teile.append(rest[:74])
        rest = rest[74:]
    # An UTF-8-Grenzen sauber dekodieren
    ausgabe = teile[0].decode("utf-8", errors="ignore")
    for teil in teile[1:]:
        ausgabe += "\r\n " + teil.decode("utf-8", errors="ignore")
    return ausgabe


def ics_zeit(wert: str, ganztaegig: bool) -> str:
    dt = datetime.fromisoformat(wert)
    if ganztaegig:
        return dt.strftime("%Y%m%d")
    return dt.strftime("%Y%m%dT%H%M%S")


def beschreibung_bauen(ev: dict) -> str:
    """Alles, was beim Posten gebraucht wird, direkt im Kalendereintrag."""
    zeilen = []
    if ev.get("beschreibung"):
        zeilen += [ev["beschreibung"], ""]

    zeilen.append(f"Eintritt: {BESCHRIFTUNG[anzeige(ev)]}"
                  f" (Quelle nennt: {ev.get('eintritt')})")

    if ev.get("eintritt_beleg"):
        zeilen.append(f'Beleg: "{ev["eintritt_beleg"]}"')
    if ev.get("eintritt_confidence"):
        zeilen.append(f"Sicherheit: {ev['eintritt_confidence']}")

    zeilen.append("")
    for feld, beschriftung in [
        ("veranstalter", "Veranstalter"),
        ("kategorie", "Kategorie"),
        ("zielgruppe", "Zielgruppe"),
        ("drinnen_draussen", "Drinnen/Draussen"),
    ]:
        if ev.get(feld):
            zeilen.append(f"{beschriftung}: {ev[feld]}")

    if ev.get("anmeldung_noetig"):
        zeilen.append(f"Anmeldung noetig: ja — {ev.get('anmeldung_url') or 'siehe Quelle'}")

    zeilen.append("")
    zeilen.append(f"Quelle: {ev.get('quelle_url') or '—'}")
    for weitere in ev.get("quellen_weitere") or []:
        zeilen.append(f"Auch bei: {weitere}")
    if ev.get("bild_url"):
        zeilen.append(f"Bild: {ev['bild_url']}")

    return "\n".join(zeilen).strip()


def event_block(ev: dict, jetzt: str) -> list:
    ganztaegig = bool(ev.get("ganztaegig"))
    beginn = ics_zeit(ev["beginn"], ganztaegig)

    if ev.get("ende"):
        ende = ics_zeit(ev["ende"], ganztaegig)
    elif ganztaegig:
        # Ohne Endangabe: eintaegig. Der Aufschlag auf DTEND passiert unten.
        ende = beginn
    else:
        dt = datetime.fromisoformat(ev["beginn"]) + timedelta(hours=2)
        ende = ics_zeit(dt.isoformat(), False)

    if ganztaegig:
        # DTEND ist bei ganztaegigen Terminen exklusiv, im Schema steht aber der
        # letzte Tag, an dem das Event stattfindet ("Ausstellung bis 30.09.").
        # Darum immer einen Tag aufschlagen.
        letzter_tag = datetime.strptime(ende, "%Y%m%d")
        ende = (letzter_tag + timedelta(days=1)).strftime("%Y%m%d")
        zeit = [f"DTSTART;VALUE=DATE:{beginn}", f"DTEND;VALUE=DATE:{ende}"]
    else:
        zeit = [
            f"DTSTART;TZID=Europe/Berlin:{beginn}",
            f"DTEND;TZID=Europe/Berlin:{ende}",
        ]

    ort = " — ".join(x for x in [ev.get("ort_name"), ev.get("ort_adresse")] if x)
    titel = ev["titel"]
    art = anzeige(ev)
    if art == SPENDE:
        titel = f"{titel} (Spende)"
    elif art == VERMUTLICH:
        # Im Kalendereintrag muss stehen, worauf man sich verlassen kann —
        # dort sieht niemand mehr die Belegzeile aus der Pruefliste.
        titel = f"{titel} (vermutlich frei)"
    # Im Kalender bleibt Ausgebuchtes sichtbar — er ist zum Nachschlagen da,
    # nicht zum Empfehlen. In der Mail faellt es weg.
    if ev.get("ausgebucht"):
        titel = f"[AUSGEBUCHT] {titel}"
    if ev.get("status") == "abgesagt":
        titel = f"ABGESAGT: {titel}"

    block = ["BEGIN:VEVENT", f"UID:{ev['id']}@gratis-freising", f"DTSTAMP:{jetzt}"]
    block += zeit
    block += [
        f"SUMMARY:{escape(titel)}",
        f"LOCATION:{escape(ort)}",
        f"DESCRIPTION:{escape(beschreibung_bauen(ev))}",
    ]
    if ev.get("quelle_url"):
        block.append(f"URL:{escape(ev['quelle_url'])}")
    if ev.get("kategorie"):
        block.append(f"CATEGORIES:{escape(ev['kategorie'])}")
    if ev.get("status") == "abgesagt":
        block.append("STATUS:CANCELLED")
    block.append("END:VEVENT")
    return block


def kalender_schreiben(pfad: pathlib.Path, name: str, events: list) -> None:
    jetzt = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    zeilen = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Gratis in Freising//Eventsammler//DE",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{escape(name)}",
        "X-WR-TIMEZONE:Europe/Berlin",
    ]
    zeilen += VTIMEZONE.split("\n")
    for ev in events:
        zeilen += event_block(ev, jetzt)
    zeilen.append("END:VCALENDAR")

    inhalt = "\r\n".join(falten(z) for z in zeilen) + "\r\n"
    pfad.write_text(inhalt, encoding="utf-8")


def pruefliste_schreiben(pfad: pathlib.Path, events: list) -> None:
    zeilen = [
        "# Pruefliste",
        "",
        "Faelle, bei denen der freie Eintritt nicht gesichert ist.",
        "Nach dem Pruefen in `daten/events.json` das Feld `eintritt` korrigieren",
        "und `manuell_bestaetigt` auf `true` setzen — dann fasst der Agent den",
        "Eintrag nicht mehr an.",
        "",
    ]
    if not events:
        zeilen.append("_Nichts zu pruefen._")
    for ev in sorted(events, key=lambda e: e["beginn"]):
        datum = datetime.fromisoformat(ev["beginn"]).strftime("%d.%m.%Y %H:%M")
        zeilen += [
            f"## {ev['titel']}",
            f"- **Wann:** {datum}",
            f"- **Wo:** {ev.get('ort_name') or '—'}",
            f"- **Angezeigt als:** {BESCHRIFTUNG[anzeige(ev)]} — Quelle nennt "
            f"`{ev.get('eintritt')}` (Sicherheit: {ev.get('eintritt_confidence') or '—'})",
            f"- **Beleg:** {ev.get('eintritt_beleg') or '_kein Hinweis im Text gefunden_'}",
            f"- **Quelle:** {ev.get('quelle_url') or '—'}",
            "",
        ]
    pfad.write_text("\n".join(zeilen), encoding="utf-8")


def main() -> None:
    daten = json.loads(DATEN.read_text(encoding="utf-8"))
    AUSGABE.mkdir(exist_ok=True)

    heute = datetime.now().date().isoformat()
    kommend = [
        ev
        for ev in daten["events"]
        # Mehrtaegiges zaehlt, solange es laeuft — nicht nur bis zu seinem
        # Anfang. Sonst faellt jede laufende Ausstellung aus dem Kalender.
        if max((ev.get("ende") or "")[:10], (ev.get("beginn") or "")[:10]) >= heute
        and ev.get("status") != "verschwunden"
    ]

    # Der oeffentliche Kalender zeigt alles, was nicht nachweislich Geld
    # kostet — Vermutungen sind im Titel als solche gekennzeichnet.
    gratis = [ev for ev in kommend if anzeige(ev) != KOSTEN]
    pruefen = [ev for ev in kommend if anzeige(ev) == VERMUTLICH]

    kalender_schreiben(AUSGABE / "gratis-freising.ics", "Gratis in Freising", gratis)
    kalender_schreiben(AUSGABE / "pruefen.ics", "Gratis in Freising — zu pruefen", pruefen)
    pruefliste_schreiben(AUSGABE / "PRUEFLISTE.md", pruefen)

    print(f"{len(daten['events'])} Events gespeichert, davon {len(kommend)} kommend.")
    print(f"  gratis-freising.ics : {len(gratis)}")
    print(f"  pruefen.ics         : {len(pruefen)}")


if __name__ == "__main__":
    main()
