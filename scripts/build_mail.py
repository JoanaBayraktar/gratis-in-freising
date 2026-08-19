#!/usr/bin/env python3
"""Baut die taegliche Mail: heute plus Ausblick auf sieben Tage.

    python3 scripts/build_mail.py

Erzeugt in ausgabe/:
  mail.html      der Mailtext
  mail-betreff   die Betreffzeile (eine Zeile, fuer den Workflow)

Wie build_kalender.py bewusst ohne externe Bibliotheken. Das Skript entscheidet
nichts inhaltlich — es sortiert und formatiert nur, was in events.json steht.

Die Mail hat drei Ebenen, und die Trennung ist der eigentliche Inhalt dieser
Datei: Ein Einzeltermin kann man verpassen, eine laufende Ausstellung nicht.
Beide in einer Liste zu mischen, macht die Liste unbrauchbar — die Ausstellung
erschiene an jedem ihrer Tage und draengte die Termine nach unten, die heute
wirklich stattfinden.

  Heute            Einzeltermine des Tages, gross und mit Beschreibung
  Laeuft gerade    Mehrtaegiges, EINMAL genannt, nach Ende sortiert
  Naechste Tage    Einzeltermine als knappe Liste
"""
import html
import json
import pathlib
import re
from datetime import datetime, timedelta

from regeln import IN_DIE_MAIL, zu_pruefen

BASIS = pathlib.Path(__file__).resolve().parent.parent
DATEN = BASIS / "daten" / "events.json"
AUSGABE = BASIS / "ausgabe"

WOCHENTAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag",
              "Freitag", "Samstag", "Sonntag"]
MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
          "August", "September", "Oktober", "November", "Dezember"]

# Ueber Stichwoerter statt ueber die Kategorieliste: die Quellen liefern eigene
# Bezeichnungen ("EDV & Digitales", "Umwelt, Nachhaltigkeit und Verbraucher-
# fragen"), die im Schema nicht vorgesehen sind. Wer zuerst passt, gewinnt —
# die Reihenfolge ist deshalb Absicht.
ICONS = [
    ("kunst|ausstell|galerie|vernissage|kultur|brauchtum", "🎨"),
    ("musik|konzert|chor|jazz|band|karaoke", "🎵"),
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

# Nur unter "Heute". Die Vorschau bleibt eine Liste — sonst scrollt man an den
# heutigen Terminen vorbei, um die der naechsten Woche zu lesen.
LAENGE_HEUTE = 300

SCHRIFT = 'font-family:-apple-system,"Segoe UI",Helvetica,Arial,sans-serif'
BLAU = "#1a5490"


def e(text) -> str:
    return html.escape(str(text or ""))


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


def spanne(ev: dict) -> tuple:
    """Erster und letzter Tag. Ein fehlendes Ende heisst: derselbe Tag."""
    beginn = datetime.fromisoformat(ev["beginn"]).date()
    ende = datetime.fromisoformat(ev["ende"]).date() if ev.get("ende") else beginn
    return beginn, max(ende, beginn)


def mehrtaegig(ev: dict) -> bool:
    beginn, ende = spanne(ev)
    return ende > beginn


def zeitangabe(ev: dict, kurz: bool = False) -> str:
    """Anfang und, wo bekannt, Ende.

    Bei gut der Haelfte der Events steht in `ende` dasselbe wie in `beginn` —
    die Quelle nennt kein Ende. Dann bleibt es bei der Anfangszeit, statt eine
    Dauer zu erfinden.
    """
    if ev.get("ganztaegig"):
        return "ganzt." if kurz else "ganztägig"
    beginn = datetime.fromisoformat(ev["beginn"])
    ende = datetime.fromisoformat(ev["ende"]) if ev.get("ende") else None
    if not ende or ende <= beginn:
        return beginn.strftime("%H:%M")
    if ende.date() > beginn.date():
        return f'{beginn.strftime("%H:%M")} – {ende.strftime("%d.%m.")}'
    return f'{beginn.strftime("%H:%M")}–{ende.strftime("%H:%M")}'


def verlinkt(ev: dict) -> str:
    titel = e(ev["titel"])
    if not ev.get("quelle_url"):
        return titel
    return (f'<a href="{e(ev["quelle_url"])}" style="color:#123c63;'
            f'text-decoration:none">{titel}</a>')


def ueberschrift(text: str, unter: str = "") -> str:
    zusatz = (f'<span style="font-size:12px;color:#8a8a8a;margin-left:8px">'
              f'{e(unter)}</span>' if unter else "")
    return (f'<div style="margin:30px 0 10px;border-bottom:2px solid {BLAU};'
            f'padding-bottom:4px"><span style="font-size:12px;font-weight:700;'
            f'letter-spacing:.09em;text-transform:uppercase;color:{BLAU}">'
            f'{e(text)}</span>{zusatz}</div>')


def karte(ev: dict) -> str:
    """Einzeltermin heute — das Wichtigste der Mail, entsprechend gross."""
    marke = ('<span style="display:inline-block;background:#fff3cd;color:#7a5b00;'
             'padding:1px 7px;border-radius:10px;font-size:12px;font-weight:600;'
             'margin-left:6px">Spende erbeten</span>'
             if ev.get("eintritt") == "spende" else "")
    anmeldung = ('<span style="color:#8a6d3b;font-size:12px;margin-left:6px">'
                 'Anmeldung nötig</span>' if ev.get("anmeldung_noetig") else "")
    text = ""
    if ev.get("beschreibung"):
        text = (f'<div style="color:#4a4a4a;font-size:14px;line-height:1.5;'
                f'margin-top:5px">{e(kuerzen(ev["beschreibung"], LAENGE_HEUTE))}</div>')
    return (
        f'<div style="border-left:3px solid {BLAU};padding:2px 0 2px 14px;'
        f'margin:0 0 18px">'
        f'<div style="font-size:13px;color:{BLAU};font-weight:700">'
        f'{e(zeitangabe(ev))}</div>'
        f'<div style="font-size:17px;font-weight:700;margin-top:1px;'
        f'line-height:1.3">{icon(ev)} {verlinkt(ev)}{marke}</div>'
        f'<div style="color:#6b6b6b;font-size:13px;margin-top:2px">'
        f'{e(ev.get("ort_name") or "Ort siehe Quelle")}'
        f' &middot; {e(ev.get("quelle_name"))}{anmeldung}</div>'
        f'{text}</div>')


def dauerzeile(ev: dict, heute) -> str:
    """Was laeuft, braucht keine Anfangszeit — sondern die Restlaufzeit."""
    _, ende = spanne(ev)
    rest = (ende - heute).days
    wann = ("läuft noch heute" if rest <= 0 else
            "nur noch bis morgen" if rest == 1 else
            f"noch {rest} Tage, bis {ende.strftime('%d.%m.')}")
    knapp = rest <= 2
    return (
        f'<tr><td style="padding:7px 0;border-bottom:1px solid #ececec">'
        f'<div style="font-size:15px">{icon(ev)} {verlinkt(ev)}</div>'
        f'<div style="font-size:13px;color:#6b6b6b;margin-top:1px">'
        f'{e(ev.get("ort_name") or "")} &middot; '
        f'<span style="color:{"#a8471a" if knapp else "#6b6b6b"};'
        f'{"font-weight:600" if knapp else ""}">{e(wann)}</span></div>'
        f'</td></tr>')


def listenzeile(ev: dict) -> str:
    marke = (' <span style="color:#7a5b00;font-size:12px">(Spende)</span>'
             if ev.get("eintritt") == "spende" else "")
    return (
        f'<tr>'
        f'<td style="padding:5px 10px 5px 0;color:#6b6b6b;font-size:13px;'
        f'white-space:nowrap;vertical-align:top;'
        f'font-variant-numeric:tabular-nums">{e(zeitangabe(ev, kurz=True))}</td>'
        f'<td style="padding:5px 0;font-size:14px;vertical-align:top;'
        f'line-height:1.45">{icon(ev)} {verlinkt(ev)}{marke}'
        f'<span style="color:#8a8a8a"> &middot; {e(ev.get("ort_name") or "")}'
        f'</span></td></tr>')


def pruefblock(offen: list) -> str:
    zeilen = []
    for ev in offen:
        wann = datetime.fromisoformat(ev["beginn"]).strftime("%d.%m.")
        grund = (f'Beleg: „{kuerzen(ev["eintritt_beleg"], 80)}"'
                 if ev.get("eintritt_beleg")
                 else "kein Hinweis zum Eintritt auf der Seite")
        zeilen.append(f'<li style="margin-bottom:6px">{e(wann)} &middot; '
                      f'{verlinkt(ev)}<br><span style="color:#777;font-size:13px">'
                      f'{e(grund)}</span></li>')
    return (ueberschrift("Noch zu prüfen")
            + '<p style="color:#777;font-size:13px;margin:0 0 8px">Hier ist nicht '
              'gesichert, dass der Eintritt frei ist — deshalb stehen diese Termine '
              'oben nicht mit. Der Link führt zur Quelle.</p>'
            + f'<ul style="margin:0;padding-left:20px">{"".join(zeilen)}</ul>')


def main() -> None:
    daten = json.loads(DATEN.read_text(encoding="utf-8"))
    AUSGABE.mkdir(exist_ok=True)

    heute = datetime.now().date()
    bis = heute + timedelta(days=7)

    # Was hier oben steht, taucht unter "Noch zu pruefen" nicht auf und
    # umgekehrt. Derselbe Termin einmal als gratis und einmal als ungeklaert
    # wuerde beides entwerten.
    zeigbar = [ev for ev in daten["events"]
               if ev.get("status") == "aktiv"
               and ev.get("eintritt") in IN_DIE_MAIL
               and not ev.get("ausgebucht")
               and not zu_pruefen(ev)]

    # Dauertermine nach Ende sortiert: was bald ausläuft, ist die eigentliche
    # Nachricht. Eine Ausstellung, die noch drei Monate zu sehen ist, steht
    # deshalb unten — sie eilt nicht.
    dauer = sorted([ev for ev in zeigbar if mehrtaegig(ev)
                    and spanne(ev)[0] <= bis and spanne(ev)[1] >= heute],
                   key=lambda x: (spanne(x)[1], x["beginn"]))
    einzeln = [ev for ev in zeigbar if not mehrtaegig(ev)]
    heute_ev = sorted([ev for ev in einzeln if spanne(ev)[0] == heute],
                      key=lambda x: x["beginn"])
    spaeter = sorted([ev for ev in einzeln if heute < spanne(ev)[0] <= bis],
                     key=lambda x: x["beginn"])

    teile = [
        f'<div style="{SCHRIFT};max-width:600px;margin:0 auto;padding:20px 18px;'
        f'color:#1c1c1c">',
        '<div style="font-size:23px;font-weight:800">Gratis in Freising</div>',
        f'<div style="color:#6b6b6b;font-size:14px;margin-top:2px">'
        f'{WOCHENTAGE[heute.weekday()]}, {heute.day}. {MONATE[heute.month - 1]} '
        f'{heute.year}</div>',
        ueberschrift("Heute", f"{len(heute_ev)} Termine" if heute_ev else ""),
        ("".join(karte(ev) for ev in heute_ev) if heute_ev
         else '<p style="color:#8a8a8a;margin:0">Heute nichts Kostenloses gefunden.</p>'),
    ]

    if dauer:
        teile.append(ueberschrift("Läuft gerade", "mehrtägig"))
        teile.append(f'<table style="border-collapse:collapse;width:100%">'
                     f'{"".join(dauerzeile(ev, heute) for ev in dauer)}</table>')

    if spaeter:
        teile.append(ueberschrift("Die nächsten Tage"))
        # Eine Tabelle fuer alle Tage. Je Tag eine eigene rechnet sich ihre
        # Spaltenbreite selbst aus, und die Titel stehen dann von Tag zu Tag
        # verschieden weit rechts.
        zeilen = []
        for versatz in range(1, 8):
            tag = heute + timedelta(days=versatz)
            am_tag = [ev for ev in spaeter if spanne(ev)[0] == tag]
            if not am_tag:
                continue
            zeilen.append(f'<tr><td colspan="2" style="padding:14px 0 3px;'
                          f'font-size:13px;font-weight:700;color:#3a3a3a">'
                          f'{WOCHENTAGE[tag.weekday()]}, {tag.strftime("%d.%m.")}'
                          f'</td></tr>')
            zeilen += [listenzeile(ev) for ev in am_tag]
        teile.append(f'<table style="border-collapse:collapse;width:100%">'
                     f'{"".join(zeilen)}</table>')

    offen = sorted([ev for ev in daten["events"]
                    if ev.get("status") == "aktiv" and zu_pruefen(ev)
                    and heute <= spanne(ev)[0] <= bis],
                   key=lambda x: x["beginn"])
    if offen:
        teile.append(pruefblock(offen))

    verborgen = sum(1 for ev in daten["events"]
                    if ev.get("status") == "aktiv" and ev.get("ausgebucht")
                    and ev.get("eintritt") in IN_DIE_MAIL
                    and heute <= spanne(ev)[0] <= bis)
    zaehler = [f"{len(heute_ev)} heute", f"{len(dauer)} laufend",
               f"{len(spaeter)} in den nächsten 7 Tagen"]
    if verborgen:
        zaehler.append(f"{verborgen} ausgebucht")
    if offen:
        zaehler.append(f"{len(offen)} zu prüfen")

    teile.append(
        '<div style="border-top:1px solid #e2e2e2;margin-top:28px;padding-top:10px;'
        'color:#8a8a8a;font-size:12px;line-height:1.5">'
        + " &middot; ".join(e(z) for z in zaehler) +
        '<br>Automatisch erzeugt aus daten/events.json. '
        'Korrekturen gehören dorthin, nicht in diese Mail.</div></div>')

    if heute_ev:
        betreff = (f"Gratis in Freising: {len(heute_ev)} heute — "
                   f"{heute_ev[0]['titel'][:48]}")
    elif dauer:
        betreff = f"Gratis in Freising: heute nichts Neues, {len(dauer)} laufend"
    else:
        betreff = f"Gratis in Freising: heute nichts, {len(spaeter)} diese Woche"

    (AUSGABE / "mail.html").write_text("".join(teile), encoding="utf-8")
    (AUSGABE / "mail-betreff").write_text(betreff, encoding="utf-8")
    print(f"{betreff}\n  " + ", ".join(zaehler))


if __name__ == "__main__":
    main()
