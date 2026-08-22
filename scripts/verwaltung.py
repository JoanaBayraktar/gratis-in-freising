#!/usr/bin/env python3
"""Ihre Eingriffe von Hand, angewandt auf das, was die Quellen liefern.

    python3 scripts/verwaltung.py            zeigt, was hinterlegt ist

Warum es diese Datei gibt: `daten/events.json` gehoert dem Sammellauf. Er
schreibt sie jede Nacht neu, und alles, was jemand von Hand hineinschreibt,
ist beim naechsten Lauf Verhandlungssache — genau das ist frueher passiert,
als eine Nachpruefung 13 Termine geloescht hat. Ihre Eingriffe stehen deshalb
getrennt in `daten/verwaltung.json` und werden erst beim Bauen daruebergelegt.
Der Sammellauf kann sie damit gar nicht kaputtmachen; er kennt sie nicht.

Drei Arten von Eingriff, in dieser Reihenfolge angewandt:

  ausgeblendet  fliegt raus, egal was die Quelle sagt. Fuer Wochenmarkt,
                Mittagskarten, Dubletten, Unsinn.
  korrekturen   einzelne Felder werden ueberschrieben. Der Rest des Termins
                bleibt, wie die Quelle ihn meldet — meldet sie morgen eine
                neue Beschreibung, kommt die an, Ihr korrigierter Ort bleibt.
  eigene        vollstaendige Termine, die keine Quelle hat.

Dieselben drei Schritte macht die Webseite noch einmal in JavaScript, damit
eine Aenderung sofort sichtbar ist und nicht erst nach dem naechsten Lauf.
Wer hier etwas aendert, muss dort nachziehen — die Stelle ist in
`verwaltung.html` mit demselben Wort ueberschrieben.
"""
import json
import pathlib
import sys

BASIS = pathlib.Path(__file__).resolve().parent.parent
DATEI = BASIS / "daten" / "verwaltung.json"

# Was sich korrigieren laesst. Bewusst keine Liste aller Felder: `id` zu
# aendern wuerde die Zuordnung zerreissen, `zuletzt_gesehen` gehoert dem
# Sammellauf, und `eintritt_confidence` ergibt von Hand keinen Sinn — dafuer
# gibt es `manuell_bestaetigt`.
KORRIGIERBAR = {
    "titel", "beginn", "ende", "ganztaegig", "ort_name", "ort_adresse",
    "veranstalter", "beschreibung", "kategorie", "zielgruppe", "besonderheit",
    "eintritt", "dauertermin", "ausgebucht", "anmeldung_noetig",
    "quelle_url", "status",
}

LEER = {"stand": None, "eigene": [], "korrekturen": {}, "ausgeblendet": {}}


def laden() -> dict:
    """Die Verwaltungsdatei lesen. Fehlt sie, ist eben nichts hinterlegt.

    Ein fehlender oder kaputter Eingriff darf den naechtlichen Lauf nicht
    anhalten: Ohne Verwaltung ist die Ausgabe unvollstaendig, ohne Lauf
    gibt es gar keine.
    """
    if not DATEI.exists():
        return dict(LEER)
    try:
        daten = json.loads(DATEI.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as fehler:
        print(f"  verwaltung.json unlesbar ({fehler}) — wird uebergangen",
              file=sys.stderr)
        return dict(LEER)
    for feld, vorgabe in LEER.items():
        daten.setdefault(feld, vorgabe if not isinstance(vorgabe, (list, dict))
                         else type(vorgabe)())
    return daten


def anwenden(events: list, verwaltung: dict = None, laut: bool = True) -> list:
    """Ausblenden, korrigieren, eigene anhaengen — in dieser Reihenfolge."""
    v = verwaltung if verwaltung is not None else laden()
    versteckt = v.get("ausgeblendet") or {}
    korrekturen = v.get("korrekturen") or {}
    eigene = v.get("eigene") or []

    ergebnis, weg, geaendert = [], 0, 0
    for ev in events:
        kennung = ev.get("id")
        if kennung in versteckt:
            weg += 1
            continue
        felder = korrekturen.get(kennung)
        if felder:
            ev = dict(ev)
            angefasst = False
            for feld, wert in felder.items():
                if feld not in KORRIGIERBAR:
                    continue
                ev[feld] = wert
                angefasst = True
            if angefasst:
                geaendert += 1
            # `manuell_bestaetigt` hebt in regeln.anzeige() den Abschlag auf,
            # den unbelegte Preisangaben bekommen — aus "vermutlich kostenfrei"
            # wird "Eintritt frei". Das darf nur, wer den Preis tatsaechlich
            # angesehen hat. Eine berichtigte Adresse ist keine Preispruefung:
            # sonst genuegte ein Tippfehler im Ortsnamen, um eine Vermutung in
            # eine Zusage zu verwandeln, und jemand steht vor der Kasse.
            if "eintritt" in felder:
                ev["manuell_bestaetigt"] = True
        ergebnis.append(ev)

    # Eigene zuletzt, damit eine Korrektur sie nicht versehentlich trifft und
    # sie in jedem Fall drin sind, auch wenn ihre ID zufaellig kollidiert.
    vorhanden = {ev.get("id") for ev in ergebnis}
    dazu = 0
    for ev in eigene:
        if ev.get("id") in versteckt or ev.get("id") in vorhanden:
            continue
        ev = dict(ev)
        ev["manuell_bestaetigt"] = True
        ergebnis.append(ev)
        dazu += 1

    if laut and (weg or geaendert or dazu):
        print(f"  Verwaltung: {weg} ausgeblendet, {geaendert} korrigiert, "
              f"{dazu} eigene")
    ergebnis.sort(key=lambda ev: ev.get("beginn") or "")
    return ergebnis


def main() -> None:
    v = laden()
    print(f"Stand: {v.get('stand') or '—'}")
    print(f"  {len(v.get('eigene') or [])} eigene Termine")
    for ev in v.get("eigene") or []:
        print(f"    {(ev.get('beginn') or '')[:10]}  {ev.get('titel')}")
    print(f"  {len(v.get('korrekturen') or {})} Korrekturen")
    for kennung, felder in (v.get("korrekturen") or {}).items():
        print(f"    {kennung}  {', '.join(sorted(felder))}")
    print(f"  {len(v.get('ausgeblendet') or {})} ausgeblendet")
    for kennung, angabe in (v.get("ausgeblendet") or {}).items():
        grund = angabe.get("grund") if isinstance(angabe, dict) else angabe
        print(f"    {kennung}  {grund or '—'}")


if __name__ == "__main__":
    main()
