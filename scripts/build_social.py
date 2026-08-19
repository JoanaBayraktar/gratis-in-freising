#!/usr/bin/env python3
"""Stellt die Social-Media-Entwuerfe fuer die kommende Woche zusammen.

    python3 scripts/build_social.py            # naechste 7 Tage
    python3 scripts/build_social.py 14         # naechste 14 Tage

Der Text pro Event kommt aus dem Feld `social_text` in daten/events.json und
wird vom Agenten geschrieben. Dieses Skript sortiert, gruppiert und formatiert
nur — damit die Ausgabe jede Woche gleich aussieht.
"""
import json
import pathlib
import sys
from datetime import datetime, timedelta

BASIS = pathlib.Path(__file__).resolve().parent.parent
DATEN = BASIS / "daten" / "events.json"
AUSGABE = BASIS / "ausgabe"

WOCHENTAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]

HASHTAGS = {
    "Musik": "#LiveMusik #Konzert",
    "Kunst": "#Ausstellung #Kunst",
    "Familie": "#FamilienZeit #MitKindern",
    "Vortrag": "#Vortrag #Wissen",
    "Markt": "#Markt",
    "Sport": "#Sport #Bewegung",
    "Fest": "#Fest #Feiern",
    "Sonstiges": "",
}


def main() -> None:
    tage = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    daten = json.loads(DATEN.read_text(encoding="utf-8"))
    AUSGABE.mkdir(exist_ok=True)

    heute = datetime.now().date()
    bis = heute + timedelta(days=tage)

    passend = [
        ev
        for ev in daten["events"]
        if ev.get("eintritt") in ("frei", "spende")
        and ev.get("status") == "aktiv"
        and heute.isoformat() <= ev.get("beginn", "")[:10] <= bis.isoformat()
    ]
    passend.sort(key=lambda e: e["beginn"])

    kw = heute.isocalendar()[1]
    zeilen = [
        f"# Social-Entwuerfe — ab KW {kw}",
        "",
        f"Zeitraum: {heute.strftime('%d.%m.')} bis {bis.strftime('%d.%m.%Y')} · "
        f"{len(passend)} Veranstaltungen mit freiem Eintritt",
        "",
        "Entwuerfe. Vor dem Posten gegenlesen — besonders bei `Spende`,",
        "das ist nicht dasselbe wie kostenlos.",
        "",
        "---",
        "",
    ]

    if not passend:
        zeilen.append("_Keine passenden Veranstaltungen im Zeitraum._")

    for ev in passend:
        start = datetime.fromisoformat(ev["beginn"])
        wtag = WOCHENTAGE[start.weekday()]
        uhrzeit = "ganztaegig" if ev.get("ganztaegig") else start.strftime("%H:%M Uhr")
        hinweis = " · Spende erbeten" if ev.get("eintritt") == "spende" else " · Eintritt frei"

        zeilen += [
            f"## {ev['titel']}",
            "",
            f"**{wtag}, {start.strftime('%d.%m.')} · {uhrzeit} · "
            f"{ev.get('ort_name') or 'Ort siehe Quelle'}{hinweis}**",
            "",
        ]

        if ev.get("social_text"):
            zeilen += ["```", ev["social_text"], "```", ""]
        else:
            zeilen += [
                "> _Kein Text hinterlegt._ Grundlage aus der Beschreibung:",
                "",
                f"> {ev.get('beschreibung') or '—'}",
                "",
            ]

        tags = HASHTAGS.get(ev.get("kategorie"), "")
        zeilen.append(f"Hashtags: #GratisInFreising #Freising {tags}".rstrip())
        if ev.get("bild_url"):
            zeilen.append(f"Bild: {ev['bild_url']}")
        else:
            zeilen.append("Bild: **fehlt** — eigenes Foto oder Grafik noetig")
        if ev.get("anmeldung_noetig"):
            zeilen.append(f"Hinweis: Anmeldung noetig — {ev.get('anmeldung_url') or 'siehe Quelle'}")
        zeilen += [f"Quelle: {ev.get('quelle_url') or '—'}", "", "---", ""]

    ziel = AUSGABE / f"SOCIAL-KW{kw:02d}.md"
    ziel.write_text("\n".join(zeilen), encoding="utf-8")
    print(f"{ziel.name}: {len(passend)} Veranstaltungen")


if __name__ == "__main__":
    main()
