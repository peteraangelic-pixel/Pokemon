"""Regression tests for the Kaggle deployment notebook generator."""
from __future__ import annotations

import base64
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_notebook  # noqa: E402


class NotebookBuilderTests(unittest.TestCase):
    def test_cpu_notebook_is_offline_and_embeds_tracked_sources(self) -> None:
        notebook = build_notebook.build("cpu")
        self.assertEqual(notebook["nbformat"], 4)
        self.assertEqual(notebook["metadata"]["kaggle"]["accelerator"], "none")
        self.assertFalse(notebook["metadata"]["kaggle"]["isInternetEnabled"])
        self.assertEqual(len(notebook["cells"]), 4)

        source_writer = str(notebook["cells"][2]["source"])
        for filename in ("policy.py", "my_agent.py"):
            encoded = base64.b64encode((ROOT / "agent" / filename).read_bytes()).decode("ascii")
            self.assertIn(encoded, source_writer)

        runner = str(notebook["cells"][3]["source"])
        self.assertIn("KAGGLE_IS_COMPETITION_RERUN", runner)
        self.assertIn("http://gateway:8001/api/games", runner)
        self.assertIn("--agent", runner)
        self.assertNotIn("KAGGLE_API_TOKEN", runner)

    def test_gpu_metadata_is_opt_in(self) -> None:
        notebook = build_notebook.build("rtx6000")
        kaggle = notebook["metadata"]["kaggle"]
        self.assertEqual(kaggle["accelerator"], "nvidiaRtx6000")
        self.assertTrue(kaggle["isGpuEnabled"])
        self.assertFalse(kaggle["isInternetEnabled"])

    def test_unknown_accelerator_is_rejected(self) -> None:
        with self.assertRaises(SystemExit):
            build_notebook.build("not-a-gpu")


if __name__ == "__main__":
    unittest.main()
