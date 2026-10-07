"""Quellenkonfiguration und Abrufverlauf für die statische Übersicht."""
import json
import pathlib
from datetime import datetime
from zoneinfo import ZoneInfo

import yaml


def konfigurieren(status, quellen):
    """Auch pausierte/ungetestete Quellen zeigen; keine Abrufe erfinden."""
    for eintrag in status.values():
        eintrag["aktiv"] = False
    for quelle in quellen:
        eintrag = status.setdefault(quelle["name"], {"verlauf": [], "fehlversuche": 0})
        eintrag.update(aktiv=bool(quelle.get("aktiv")), url=quelle["url"],
                       methode=quelle.get("methode", "text"))
        if eintrag.get("verlauf"):
            eintrag.setdefault("zuletzt_gefunden", eintrag["verlauf"][-1])


def gesundheit_pruefen(status, name, anzahl, fehler, heute, zeitpunkt=None):
    eintrag = status.setdefault(name, {"verlauf": [], "fehlversuche": 0})
    eintrag["letzter_versuch"] = zeitpunkt or datetime.now(ZoneInfo("Europe/Berlin")).isoformat(timespec="seconds")
    if fehler:
        eintrag["fehlversuche"] = eintrag.get("fehlversuche", 0) + 1
        eintrag["letzter_fehler"] = f"{heute}: {fehler}"
        print(f"    FEHLER ({eintrag['fehlversuche']}. Mal in Folge): {fehler}")
        return

    eintrag["fehlversuche"] = 0
    eintrag["letzter_erfolg"] = heute
    eintrag["letzter_erfolg_um"] = eintrag["letzter_versuch"]
    eintrag["zuletzt_gefunden"] = anzahl
    verlauf = eintrag.setdefault("verlauf", [])
    eintrag["warnung"] = ("Keine Termine gefunden, obwohl frühere Abrufe mindestens drei lieferten."
                          if verlauf and anzahl == 0 and max(verlauf) >= 3 else None)
    if eintrag["warnung"]:
        print(f"    WARNUNG: {eintrag['warnung']}")
    verlauf.append(anzahl)
    eintrag["verlauf"] = verlauf[-10:]


if __name__ == "__main__":
    # Bestehende Messwerte um Konfiguration ergänzen, ohne Seiten/KI aufzurufen.
    basis = pathlib.Path(__file__).resolve().parent.parent
    pfad = basis / "daten/quellen-status.json"
    status = json.loads(pfad.read_text(encoding="utf-8")) if pfad.exists() else {}
    quellen = yaml.safe_load((basis / "quellen.yml").read_text(encoding="utf-8"))["quellen"]
    konfigurieren(status, quellen)
    pfad.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
