import contextlib
import io
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import verify_release


class ReleaseVerificationTests(unittest.TestCase):
    def test_public_reproduction_preserves_accepted_files_and_pointers(self):
        root = verify_release.ROOT
        pointers = list((root / "data").glob("*/current.json"))
        before = {p: p.read_bytes() for p in pointers}
        with contextlib.redirect_stdout(io.StringIO()):
            receipt = verify_release.verify(root)
        self.assertEqual(before, {p: p.read_bytes() for p in pointers})
        self.assertEqual(receipt["status"], "passed_public_reproduction")
        self.assertEqual(len(receipt["builds"]), 8)
        self.assertFalse(receipt["private_archive_used"])
        self.assertFalse(receipt["fresh_acquisition_performed"])

    def test_tampered_frozen_evidence_stops_release_verification(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            shutil.copytree(
                verify_release.ROOT / "docs/verification", root / "docs/verification"
            )
            target = (
                root
                / "data/analytical/releases/3b2e883513623cfa/bridge_title_reference.csv"
            )
            target.parent.mkdir(parents=True)
            target.write_bytes(b"altered source\n")
            with self.assertRaisesRegex(ValueError, "Accepted evidence differs"):
                verify_release.verify(root)
            self.assertEqual(target.read_bytes(), b"altered source\n")
            self.assertFalse((root / "rebuilt").exists())
