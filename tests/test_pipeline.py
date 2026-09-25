import tempfile
import unittest
from pathlib import Path

from src.clinical_omop_pipeline.etl import load
from src.clinical_omop_pipeline.quality import run_checks


class ClinicalOmopPipelineTests(unittest.TestCase):
    def test_load_and_quality_checks_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            database = load(Path(tmp))
            self.assertTrue(database.exists())
            report = run_checks(database)
        self.assertEqual(report["failed"], 0)
        self.assertEqual(report["passed"], 8)


if __name__ == "__main__":
    unittest.main()
