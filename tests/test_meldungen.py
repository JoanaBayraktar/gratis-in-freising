import json
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
import meldungen
from test_datenpflege import event, bestand


class MeldungenTests(unittest.TestCase):
    def test_issue_wird_erst_nach_explizitem_abschluss_geschlossen(self):
        with tempfile.TemporaryDirectory() as tmp:
            basis = pathlib.Path(tmp)
            daten = basis / "daten/events.json"
            daten.parent.mkdir()
            daten.write_text(json.dumps(bestand()))
            abschluss = basis / "work/abschluss.json"
            with patch.object(meldungen, "BASIS", basis), \
                 patch.object(meldungen, "DATEN", daten), \
                 patch.object(meldungen, "ABSCHLUSS", abschluss), \
                 patch.dict("os.environ", {"GITHUB_REPOSITORY": "test/repo"}), \
                 patch.object(meldungen, "bauen", return_value=event()), \
                 patch.object(meldungen, "github", return_value=[{"number": 1}]) as api, \
                 patch.object(sys, "argv", ["meldungen.py", "--spaeter-schliessen"]):
                meldungen.main()
                self.assertEqual(api.call_count, 1)  # Nur die Meldungen lesen.
                self.assertEqual(len(json.loads(daten.read_text())["events"]), 1)
                self.assertTrue(abschluss.exists())
                with patch.object(sys, "argv", ["meldungen.py", "--abschliessen"]):
                    meldungen.main()
                self.assertEqual(api.call_args.args[1:], ("PATCH", {"state": "closed"}))

    def test_fehlgeschlagene_validierung_schliesst_keine_meldung(self):
        with tempfile.TemporaryDirectory() as tmp:
            basis = pathlib.Path(tmp)
            daten = basis / "events.json"
            # Ein kaputter vorhandener Bestand darf nicht nach einer Import-
            # Bestaetigung erst auffallen.
            daten.write_text(json.dumps(bestand(event(id="alt", unbekannt=True))))
            with patch.object(meldungen, "BASIS", basis), \
                 patch.object(meldungen, "DATEN", daten), \
                 patch.dict("os.environ", {"GITHUB_REPOSITORY": "test/repo"}), \
                 patch.object(meldungen, "bauen", return_value=event(id="neu")), \
                 patch.object(meldungen, "github", return_value=[{"number": 1}]) as api, \
                 patch.object(sys, "argv", ["meldungen.py"]):
                with self.assertRaises(Exception):
                    meldungen.main()
                self.assertEqual(api.call_count, 1)
