#!/usr/bin/env python3
"""Baut die taegliche Mail: heute plus Ausblick auf sieben Tage.

    python3 scripts/build_mail.py

Erzeugt in ausgabe/:
  mail.html      der Mailtext
  mail-betreff   die Betreffzeile (eine Zeile, fuer den Workflow)

Wie build_kalender.py bewusst ohne externe Bibliotheken. Das Skript entscheidet
nichts inhaltlich — es sortiert und formatiert nur, was in events.json steht.
"""
import html
import json
import pathlib
from datetime import datetime, timedelta

BASIS = pathlib.Path(__file__).resolve().parent.parent
DATEN = BASIS / "daten" / "events.json"
AUSGABE = BASIS / "ausgabe"

WOCHENTAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag",
              "Freitag", "Samstag", "Sonntag"]

# Nur diese beiden kommen in die Mail. "unklar" gehoert in die Pruefliste,
# nicht in eine Mail, die suggeriert, es sei alles kostenlos.
LABEL = {"frei": "Eintritt frei", "spende": "Spende erbeten"}


def e(text) -> str:
    return html.escape(str(text or ""))


def eintrag(ev: dict, tag) -> str:
    beginn = datetime.fromisoformat(ev["beginn"])
    ende = datetime.fromisoformat(ev["ende"]) if ev.get("ende") else beginn
    ort = ev.get("ort_name") or "Ort siehe Quelle"

    # Eine Ausstellung, die vor drei Tagen begonnen hat, faengt heute nicht um
    # 10:00 an. Die Anfangszeit gilt nur am ersten Tag; danach zaehlt, wie lange
    # sie noch laeuft.
    if beginn.date() < tag:
        zeit = "läuft noch"
    elif ev.get("ganztaegig"):
        zeit = "ganztägig"
    else:
        zeit = beginn.strftime("%H:%M Uhr")

    hinweis = ""
    if ende.date() > tag:
        hinweis = (f'<span style="color:#666;font-size:13px">bis '
                   f'{ende.strftime("%d.%m.")}</span> ')
    if ev.get("eintritt") == "spende":
        hinweis = ('<span style="background:#fff3cd;padding:1px 6px;border-radius:3px;'
                   'font-size:13px">Spende erbeten</span> ')
    if ev.get("anmeldung_noetig"):
        hinweis += '<span style="color:#8a6d3b;font-size:13px">Anmeldung nötig</span> '

    titel = e(ev["titel"])
    if ev.get("quelle_url"):
        titel = f'<a href="{e(ev["quelle_url"])}" style="color:#1a5490;'\
                f'text-decoration:none">{titel}</a>'

    return (
        '<tr>'
        f'<td style="padding:6px 12px 6px 0;color:#666;white-space:nowrap;'
        f'vertical-align:top;font-variant-numeric:tabular-nums">{e(zeit)}</td>'
        f'<td style="padding:6px 0">'
        f'<strong>{titel}</strong><br>'
        f'<span style="color:#666;font-size:14px">{e(ort)}</span> {hinweis}'
        f'</td></tr>'
    )


def tagesblock(ueberschrift: str, events: list, leertext: str, tag=None) -> str:
    if not events:
        return (f'<h2 style="font-size:17px;margin:24px 0 8px">{e(ueberschrift)}</h2>'
                f'<p style="color:#888;margin:0">{e(leertext)}</p>')
    zeilen = "".join(eintrag(ev, tag) for ev in events)
    return (f'<h2 style="font-size:17px;margin:24px 0 8px">{e(ueberschrift)}</h2>'
            f'<table style="border-collapse:collapse;width:100%">{zeilen}</table>')


def main() -> None:
    daten = json.loads(DATEN.read_text(encoding="utf-8"))
    AUSGABE.mkdir(exist_ok=True)

    heute = datetime.now().date()
    bis = heute + timedelta(days=7)

    def laeuft_an(ev, tag):
        """Auch mehrtaegige Veranstaltungen zaehlen an jedem ihrer Tage."""
        beginn = (ev.get("beginn") or "")[:10]
        ende = (ev.get("ende") or ev.get("beginn") or "")[:10]
        return beginn <= tag.isoformat() <= max(ende, beginn)

    passend = [ev for ev in daten["events"]
               if ev.get("status") == "aktiv"
               and ev.get("eintritt") in LABEL
               and not (ev.get("eintritt") == "frei"
                        and ev.get("eintritt_confidence") == "niedrig")]

    heute_events = sorted([ev for ev in passend if laeuft_an(ev, heute)],
                          key=lambda x: x["beginn"])

    bloecke = [tagesblock(
        f"Heute — {WOCHENTAGE[heute.weekday()]}, {heute.strftime('%d.%m.%Y')}",
        heute_events, "Heute nichts Kostenloses gefunden.", heute)]

    kommend = 0
    for versatz in range(1, 8):
        tag = heute + timedelta(days=versatz)
        tages = sorted([ev for ev in passend if laeuft_an(ev, tag)],
                       key=lambda x: x["beginn"])
        kommend += len(tages)
        if tages:
            bloecke.append(tagesblock(
                f"{WOCHENTAGE[tag.weekday()]}, {tag.strftime('%d.%m.')}", tages, "", tag))

    if kommend == 0:
        bloecke.append('<h2 style="font-size:17px;margin:24px 0 8px">Die nächsten '
                       '7 Tage</h2><p style="color:#888;margin:0">Nichts eingetragen.</p>')

    zu_pruefen = sum(1 for ev in daten["events"]
                     if ev.get("status") == "aktiv"
                     and ev.get("beginn", "")[:10] >= heute.isoformat()
                     and (ev.get("eintritt") == "unklar"
                          or (ev.get("eintritt") == "frei"
                              and ev.get("eintritt_confidence") != "hoch")))

    fuss = (f'<hr style="border:none;border-top:1px solid #ddd;margin:28px 0 12px">'
            f'<p style="color:#888;font-size:13px;margin:0">'
            f'{len(heute_events)} heute · {kommend} in den nächsten 7 Tagen · '
            f'{zu_pruefen} Fälle warten in der Prüfliste.<br>'
            f'Automatisch erzeugt aus daten/events.json. '
            f'Korrekturen gehören dorthin, nicht in diese Mail.</p>')

    seite = (
        '<div style="font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif;'
        'max-width:640px;margin:0 auto;padding:16px;color:#222;line-height:1.45">'
        '<h1 style="font-size:21px;margin:0 0 4px">Gratis in Freising</h1>'
        f'{"".join(bloecke)}{fuss}</div>'
    )

    if heute_events:
        betreff = (f"Gratis in Freising: {len(heute_events)} heute — "
                   f"{heute_events[0]['titel'][:48]}")
    else:
        betreff = f"Gratis in Freising: heute nichts, {kommend} diese Woche"

    (AUSGABE / "mail.html").write_text(seite, encoding="utf-8")
    (AUSGABE / "mail-betreff").write_text(betreff, encoding="utf-8")
    print(f"{betreff}\n  {len(heute_events)} heute, {kommend} in 7 Tagen, "
          f"{zu_pruefen} zu pruefen")


if __name__ == "__main__":
    main()
