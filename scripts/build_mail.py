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
import re

from regeln import IN_DIE_MAIL, zu_pruefen
from datetime import datetime, timedelta

BASIS = pathlib.Path(__file__).resolve().parent.parent
DATEN = BASIS / "daten" / "events.json"
AUSGABE = BASIS / "ausgabe"

WOCHENTAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag",
              "Freitag", "Samstag", "Sonntag"]

LABEL = {"frei": "Eintritt frei", "spende": "Spende erbeten"}

# Ueber Stichwoerter statt ueber die Kategorieliste: die Quellen liefern eigene
# Bezeichnungen ("EDV & Digitales", "Umwelt, Nachhaltigkeit und Verbraucher-
# fragen"), die im Schema nicht vorgesehen sind. Wer zuerst passt, gewinnt —
# die Reihenfolge ist deshalb Absicht.
ICONS = [
    ("kunst|ausstell|galerie|vernissage|kultur|brauchtum", "🎨"),
    ("musik|konzert|chor|jazz|band", "🎵"),
    ("kind|famili|jugend", "👪"),
    ("sport|bewegung|gesundheit|wellness|yoga", "🏃"),
    ("f[uü]hrung|besichtig|rundgang", "🧭"),
    ("umwelt|natur|nachhaltig|garten", "🌱"),
    ("edv|digital|computer|internet", "💻"),
    ("sprach|deutsch|englisch", "🗣"),
    ("markt|fest|flohmarkt", "🎪"),
    ("handarbeit|n[aä]hen|n[aä]hcaf|stricken|repair|reparat|basteln"
     "|werkstatt|handwerk", "🧵"),
    ("selbsthilfe|beratung|anonyme|treff\\b|stammtisch", "🤝"),
    ("vortrag|lesung|diskussion|seminar|workshop", "🎤"),
]

# Was in der Mail an Beschreibung hoechstens steht. "Heute" darf ausfuehrlich
# sein, die Vorschau bleibt eine Liste — sonst scrollt man an den heutigen
# Terminen vorbei, um die der naechsten Woche zu lesen.
LAENGE_HEUTE = 320


def icon(ev: dict) -> str:
    text = f"{ev.get('kategorie') or ''} {ev.get('titel') or ''}".lower()
    for muster, zeichen in ICONS:
        if re.search(muster, text):
            return zeichen
    return "📌"


def kuerzen(text: str, grenze: int) -> str:
    """Am Satzende kuerzen, sonst am Wortende — nie mitten im Wort."""
    text = " ".join((text or "").split())
    if len(text) <= grenze:
        return text
    schnitt = text[:grenze]
    satz = max(schnitt.rfind(". "), schnitt.rfind("! "), schnitt.rfind("? "))
    if satz > grenze * 0.6:
        return schnitt[:satz + 1]
    return schnitt[:schnitt.rfind(" ")].rstrip(",;:") + " …"


def e(text) -> str:
    return html.escape(str(text or ""))


def eintrag(ev: dict, tag, ausfuehrlich: bool = False) -> str:
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

    # Die Quelle steht als Text hinter dem Ort, nicht als Symbol: fuer
    # "Merkur Veranstaltungen" gibt es kein Bildzeichen, das jemand errät.
    herkunft = ev.get("quelle_name")
    zweitzeile = e(ort) + (f' · {e(herkunft)}' if herkunft else "")

    text = ""
    if ausfuehrlich and ev.get("beschreibung"):
        text = (f'<div style="color:#444;font-size:14px;margin-top:3px">'
                f'{e(kuerzen(ev["beschreibung"], LAENGE_HEUTE))}</div>')

    return (
        '<tr>'
        f'<td style="padding:8px 12px 8px 0;color:#666;white-space:nowrap;'
        f'vertical-align:top;font-variant-numeric:tabular-nums">{e(zeit)}</td>'
        f'<td style="padding:8px 0;vertical-align:top">'
        f'<strong>{icon(ev)} {titel}</strong><br>'
        f'<span style="color:#666;font-size:14px">{zweitzeile}</span> {hinweis}'
        f'{text}'
        f'</td></tr>'
    )


def tagesblock(ueberschrift: str, events: list, leertext: str, tag=None,
               ausfuehrlich: bool = False) -> str:
    if not events:
        return (f'<h2 style="font-size:17px;margin:24px 0 8px">{e(ueberschrift)}</h2>'
                f'<p style="color:#888;margin:0">{e(leertext)}</p>')
    zeilen = "".join(eintrag(ev, tag, ausfuehrlich) for ev in events)
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

    # Ausgebuchtes bleibt in den Daten und im Kalender, nur die Mail laesst es
    # weg: sie ist eine Empfehlung, und was man nicht mehr besuchen kann,
    # gehoert nicht empfohlen.
    # Genau das Gegenstueck zum Block "Noch zu pruefen": was hier oben steht,
    # taucht dort nicht auf und umgekehrt. Derselbe Termin einmal als gratis
    # und einmal als ungeklaert wuerde beides entwerten.
    passend = [ev for ev in daten["events"]
               if ev.get("status") == "aktiv"
               and ev.get("eintritt") in IN_DIE_MAIL
               and not ev.get("ausgebucht")
               and not zu_pruefen(ev)]

    verborgen = sum(1 for ev in daten["events"]
                    if ev.get("status") == "aktiv" and ev.get("ausgebucht")
                    and ev.get("eintritt") in IN_DIE_MAIL
                    and heute.isoformat() <= (ev.get("beginn") or "")[:10]
                    <= bis.isoformat())

    heute_events = sorted([ev for ev in passend if laeuft_an(ev, heute)],
                          key=lambda x: x["beginn"])

    bloecke = [tagesblock(
        f"Heute — {WOCHENTAGE[heute.weekday()]}, {heute.strftime('%d.%m.%Y')}",
        heute_events, "Heute nichts Kostenloses gefunden.", heute, True)]

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

    # Prueffaelle der naechsten sieben Tage — die weiter entfernten haben Zeit
    # und wuerden die Mail nur laenger machen.
    offen = sorted(
        [ev for ev in daten["events"]
         if ev.get("status") == "aktiv" and zu_pruefen(ev)
         and heute.isoformat() <= (ev.get("beginn") or "")[:10] <= bis.isoformat()],
        key=lambda x: x["beginn"])

    if offen:
        zeilen = []
        for ev in offen:
            wann = datetime.fromisoformat(ev["beginn"]).strftime("%d.%m.")
            grund = (f'Beleg: „{kuerzen(ev["eintritt_beleg"], 80)}"'
                     if ev.get("eintritt_beleg")
                     else "kein Hinweis zum Eintritt auf der Seite")
            titel = e(ev["titel"])
            if ev.get("quelle_url"):
                titel = (f'<a href="{e(ev["quelle_url"])}" style="color:#1a5490">'
                         f'{titel}</a>')
            zeilen.append(
                f'<li style="margin-bottom:6px">{e(wann)} · {titel}<br>'
                f'<span style="color:#777;font-size:13px">{e(grund)}</span></li>')
        bloecke.append(
            '<h2 style="font-size:17px;margin:28px 0 8px">Noch zu prüfen</h2>'
            '<p style="color:#777;font-size:13px;margin:0 0 8px">Hier ist nicht '
            'gesichert, dass der Eintritt frei ist — deshalb stehen diese Termine '
            'oben nicht mit. Der Link führt zur Quelle.</p>'
            f'<ul style="margin:0;padding-left:20px">{"".join(zeilen)}</ul>')

    ausgeblendet = (f'{verborgen} ausgebucht und deshalb nicht gelistet · '
                    if verborgen else "")

    fuss = (f'<hr style="border:none;border-top:1px solid #ddd;margin:28px 0 12px">'
            f'<p style="color:#888;font-size:13px;margin:0">'
            f'{len(heute_events)} heute · {kommend} in den nächsten 7 Tagen · '
            f'{ausgeblendet}'
            f'{len(offen)} zu prüfen.<br>'
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
          f"{len(offen)} zu pruefen, {verborgen} ausgebucht")


if __name__ == "__main__":
    main()
