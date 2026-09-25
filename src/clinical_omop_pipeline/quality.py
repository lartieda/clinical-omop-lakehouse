"""Run transparent quality checks on the loaded OMOP subset."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VALID_CONDITION_CONCEPTS = {316866, 201826, 317009, 377821}


def check(name: str, actual: int, expected: int = 0) -> dict:
    return {"name": name, "status": "passed" if actual == expected else "failed", "observed": actual, "expected": expected}


def run_checks(database: Path) -> dict:
    connection = sqlite3.connect(database)
    try:
        checks = [
            check("person_count", connection.execute("SELECT COUNT(*) FROM person").fetchone()[0], 6),
            check("visit_count", connection.execute("SELECT COUNT(*) FROM visit_occurrence").fetchone()[0], 8),
            check("condition_count", connection.execute("SELECT COUNT(*) FROM condition_occurrence").fetchone()[0], 9),
            check("orphan_visits", connection.execute("SELECT COUNT(*) FROM visit_occurrence v LEFT JOIN person p ON p.person_id=v.person_id WHERE p.person_id IS NULL").fetchone()[0]),
            check("orphan_conditions", connection.execute("SELECT COUNT(*) FROM condition_occurrence c LEFT JOIN visit_occurrence v ON v.visit_occurrence_id=c.visit_occurrence_id WHERE v.visit_occurrence_id IS NULL").fetchone()[0]),
            check("visits_before_birth", connection.execute("SELECT COUNT(*) FROM visit_occurrence v JOIN person p ON p.person_id=v.person_id WHERE CAST(substr(v.visit_start_date,1,4) AS INTEGER) < p.year_of_birth").fetchone()[0]),
            check("conditions_outside_visit", connection.execute("SELECT COUNT(*) FROM condition_occurrence c JOIN visit_occurrence v ON v.visit_occurrence_id=c.visit_occurrence_id WHERE c.condition_start_date NOT BETWEEN v.visit_start_date AND v.visit_end_date").fetchone()[0]),
            check("unmapped_concepts", connection.execute("SELECT COUNT(*) FROM condition_occurrence WHERE condition_concept_id NOT IN ({})".format(",".join(str(item) for item in VALID_CONDITION_CONCEPTS))).fetchone()[0]),
        ]
    finally:
        connection.close()
    return {"database": str(database), "passed": sum(item["status"] == "passed" for item in checks), "failed": sum(item["status"] == "failed" for item in checks), "checks": checks}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=ROOT / "outputs" / "omop_cdm.sqlite")
    parser.add_argument("--report", type=Path, default=ROOT / "outputs" / "quality_report.json")
    args = parser.parse_args()
    report = run_checks(args.database)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Data-quality checks: {report['passed']} passed, {report['failed']} failed.")
    if report["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
