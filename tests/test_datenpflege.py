import copy
import json
import pathlib
import sys
import tempfile
import unittest
from datetime import date

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from datenpflege import (normalisieren, vorbereiten, pruefen, mit_archiv,
                        verwaltung_pruefen)


def event(**werte):
    ev = normalisieren({
        "id": "test-id", "titel": "Testveranstaltung",
        "beginn": "2026-08-01T19:00:00", "ende": "2026-08-01T21:00:00",
        "quelle_name": "Testquelle", "quelle_url": "https://example.org/event",
        "eintritt": "frei", "eintritt_beleg": "Eintritt frei",
        "eintritt_confidence": "hoch", "status": "aktiv",
        "zuerst_gesehen": "2026-07-01", "zuletzt_gesehen": "2026-08-01",
    })
    ev.update(werte)
    return ev


def bestand(*events):
    return {"schema_version": 2, "events": list(events), "laeufe": []}


class DatenpflegeTests(unittest.TestCase):
    def test_archiv_erhaelt_alle_ids_belege_und_bestaetigungen(self):
        alt = event(manuell_bestaetigt=True)
        neu = event(id="neu", beginn="2026-09-20T19:00:00", ende=None)
        laufend = event(id="ausstellung", ende="2026-11-01T18:00:00", dauertermin=True)
        original = bestand(alt, neu, laufend)
        aktiv, archiv = vorbereiten(original, {}, date(2026, 10, 7))
        self.assertEqual({e["id"] for e in aktiv["events"]}, {"neu", "ausstellung"})
        self.assertEqual(archiv["2026"][0]["eintritt_beleg"], "Eintritt frei")
        self.assertTrue(archiv["2026"][0]["manuell_bestaetigt"])
        self.assertEqual(original["events"][0]["status"], "aktiv")
        self.assertEqual(archiv["2026"][0]["status"], "vergangen")

    def test_manuelle_verlaengerung_verhindert_archivierung(self):
        verwaltung = {"korrekturen": {"test-id": {"ende": "2026-11-01T18:00:00"}}}
        unveraendert = copy.deepcopy(verwaltung)
        aktiv, archiv = vorbereiten(bestand(event()), verwaltung, date(2026, 10, 7))
        self.assertEqual(len(aktiv["events"]), 1)
        self.assertEqual(archiv, {})
        self.assertEqual(aktiv["events"][0]["ende"], "2026-08-01T21:00:00")
        self.assertEqual(verwaltung, unveraendert)

    def test_grenze_30_tage_und_jahreszuordnung(self):
        genau = event(id="grenze", beginn="2026-09-07T19:00:00", ende=None)
        alt = event(id="vorjahr", beginn="2025-12-31T19:00:00", ende=None)
        aktiv, archiv = vorbereiten(bestand(genau, alt), {}, date(2026, 10, 7))
        self.assertEqual(aktiv["events"][0]["id"], "grenze")
        self.assertEqual(set(archiv), {"2025"})

    def test_aliaswerte_keine_fremden_felder_und_keine_id_aenderung(self):
        ev = event()
        ev.pop("drinnen_draussen")
        ev["drinnen_draußen"] = "draußen"
        ev["ausgebukt"] = True
        norm = normalisieren(ev)
        self.assertEqual(norm["drinnen_draussen"], "draussen")
        self.assertFalse(norm["ausgebucht"])
        self.assertNotIn("ausgebukt", norm)
        self.assertEqual(norm["id"], ev["id"])
        pruefen(bestand(norm))
        norm["unbekannt"] = "nicht still loeschen"
        with self.assertRaises(Exception):
            pruefen(bestand(norm))

    def test_ungueltiger_zeitraum_und_doppelte_id(self):
        for daten in (bestand(event(ende="2026-07-31T12:00:00")),
                      bestand(event(beginn="2026-02-30T12:00:00")),
                      bestand(event(), event())):
            with self.assertRaises(Exception):
                pruefen(daten)

    def test_archivierter_termin_wird_wiedererkannt_und_kann_zurueckkommen(self):
        with tempfile.TemporaryDirectory() as tmp:
            pfad = pathlib.Path(tmp)
            ev = event(status="vergangen")
            (pfad / "2026.json").write_text(json.dumps(bestand(ev)))
            alle = mit_archiv(bestand(), pfad)
            self.assertEqual(alle["events"][0]["id"], "test-id")
            alle["events"][0]["ende"] = "2026-11-01T12:00:00"
            aktiv, archiv = vorbereiten(alle, {}, date(2026, 10, 7))
            self.assertEqual(aktiv["events"][0]["status"], "aktiv")
            self.assertEqual(archiv, {})
            self.assertEqual(len(mit_archiv(aktiv, pfad)["events"]), 1)

    def test_fehlende_metadaten_eigener_termine_sind_erlaubt(self):
        ev = {"id": "manuell", "titel": "Eigener Termin", "beginn": "2026-11-01T12:00:00"}
        verwaltung_pruefen({"eigene": [ev]}, bestand())
        with self.assertRaises(Exception):
            verwaltung_pruefen({"korrekturen": {"test-id": {"ausgebucht": "ja"}}}, bestand(event()))

    def test_import_holt_nur_wiedergefundene_archivtermine(self):
        from sammeln import zusammenfuehren
        alt = event(status="vergangen", dauertermin=True)
        unberuehrt = event(id="historisch", titel="Anderer Termin")
        original = copy.deepcopy([alt, unberuehrt])
        daten = bestand()
        gefunden = event(ende="2026-11-01T21:00:00", dauertermin=True)
        quelle = {"name": "Testquelle", "url": "https://example.org"}
        neu, _ = zusammenfuehren(daten, [gefunden], quelle, "2026-10-07", [alt, unberuehrt])
        self.assertEqual(neu, 0)
        self.assertEqual([e["id"] for e in daten["events"]], ["test-id"])
        self.assertEqual(daten["events"][0]["ende"], "2026-11-01T21:00:00")
        self.assertEqual([alt, unberuehrt], original)

    def test_wiederholte_archivierung_ist_idempotent(self):
        a, jahre = vorbereiten(bestand(event()), {}, date(2026, 10, 7))
        vereint = {**a, "events": a["events"] + jahre["2026"]}
        b, nochmal = vorbereiten(vereint, {}, date(2026, 10, 7))
        self.assertEqual(a, b)
        self.assertEqual(jahre, nochmal)


if __name__ == "__main__":
    unittest.main()
