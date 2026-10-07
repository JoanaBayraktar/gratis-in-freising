import copy
import json
import pathlib
import sys
import tempfile
import unittest
from datetime import date
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from quellenstatus import konfigurieren, gesundheit_pruefen


class QuellenstatusTests(unittest.TestCase):
    def test_altdaten_und_pausierte_quellen(self):
        status = {"Alt": {"verlauf": [4, 7], "fehlversuche": 3,
                          "letzter_erfolg": "2026-09-01"}}
        konfigurieren(status, [{"name": "Alt", "url": "https://example.org", "aktiv": True},
                               {"name": "Pause", "url": "https://example.org/p", "aktiv": False}])
        self.assertEqual(status["Alt"]["zuletzt_gefunden"], 7)
        self.assertNotIn("letzter_versuch", status["Alt"])
        self.assertFalse(status["Pause"]["aktiv"])
        self.assertNotIn("letzter_erfolg", status["Pause"])

    def test_fehler_erhaelt_letzten_erfolg_und_zahl(self):
        status = {}
        gesundheit_pruefen(status, "Q", 8, "", "2026-10-07", "2026-10-07T05:20:00+02:00")
        erfolg = copy.deepcopy(status["Q"])
        gesundheit_pruefen(status, "Q", 0, "HTTP 429", "2026-10-08", "2026-10-08T05:20:00+02:00")
        self.assertEqual(status["Q"]["zuletzt_gefunden"], 8)
        self.assertEqual(status["Q"]["letzter_erfolg_um"], erfolg["letzter_erfolg_um"])
        self.assertEqual(status["Q"]["fehlversuche"], 1)
        self.assertEqual(status["Q"]["verlauf"], [8])

    def test_erholung_und_stiller_ausfall(self):
        status = {"Q": {"verlauf": [5], "fehlversuche": 4}}
        gesundheit_pruefen(status, "Q", 0, "", "2026-10-07")
        self.assertEqual(status["Q"]["fehlversuche"], 0)
        self.assertEqual(status["Q"]["zuletzt_gefunden"], 0)
        self.assertTrue(status["Q"]["warnung"])
        gesundheit_pruefen(status, "Q", 3, "", "2026-10-08")
        self.assertIsNone(status["Q"]["warnung"])

    def test_verlauf_bleibt_begrenzt_und_entfernte_quelle_pausiert(self):
        status = {"Q": {"verlauf": list(range(10)), "fehlversuche": 0, "aktiv": True}}
        gesundheit_pruefen(status, "Q", 20, "", "2026-10-07")
        self.assertEqual(len(status["Q"]["verlauf"]), 10)
        konfigurieren(status, [])
        self.assertFalse(status["Q"]["aktiv"])

    def test_sammellauf_speichert_fehler_ohne_einen_erfolg_zu_erfinden(self):
        import sammeln
        with tempfile.TemporaryDirectory() as ordner:
            basis = pathlib.Path(ordner)
            daten = basis / "events.json"
            status = basis / "status.json"
            quellen = basis / "quellen.yml"
            daten.write_text(json.dumps({"schema_version": 2, "events": [], "laeufe": []}))
            quellen.write_text('quellen:\n  - name: Test\n    url: https://example.org\n    aktiv: true\n')
            with patch.multiple(sammeln, BASIS=basis, DATEN=daten, STATUS=status, QUELLEN=quellen), \
                    patch.object(sys, "argv", ["sammeln.py"]), \
                    patch.object(sammeln, "heute_berlin", return_value=date(2026, 10, 7)), \
                    patch.object(sammeln, "text_lesen", side_effect=RuntimeError("HTTP 429")), \
                    patch("builtins.print") as ausgabe:
                sammeln.main()
            gespeichert = json.loads(status.read_text())["Test"]
            self.assertTrue(gespeichert["aktiv"])
            self.assertEqual(gespeichert["fehlversuche"], 1)
            self.assertNotIn("letzter_erfolg", gespeichert)
            self.assertIn("letzter_versuch", gespeichert)
            self.assertTrue(any("::warning::" in str(aufruf) for aufruf in ausgabe.call_args_list))
            self.assertEqual(json.loads(daten.read_text())["events"], [])
