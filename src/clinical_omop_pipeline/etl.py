"""Load synthetic clinical extracts into a focused OMOP CDM subset."""

from __future__ import annotations

import argparse
import csv
import sqlite3
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data" / "source"

GENDER_CONCEPTS = {"M": 8507, "F": 8532}
VISIT_CONCEPTS = {"outpatient": 9202, "inpatient": 9201}


def read_csv(filename: str) -> list[dict[str, str]]:
    with (SOURCE / filename).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def validate_source(patients, encounters, conditions, mappings) -> None:
    if len({row["patient_id"] for row in patients}) != len(patients):
        raise ValueError("patient_id values must be unique")
    if len({row["encounter_id"] for row in encounters}) != len(encounters):
        raise ValueError("encounter_id values must be unique")
    patient_ids = {row["patient_id"] for row in patients}
    encounter_ids = {row["encounter_id"] for row in encounters}
    mapping_codes = {row["source_condition_code"] for row in mappings if row["mapping_status"] == "standard"}
    if unknown := {row["patient_id"] for row in encounters} - patient_ids:
        raise ValueError(f"encounters reference unknown patients: {sorted(unknown)}")
    if unknown := {row["encounter_id"] for row in conditions} - encounter_ids:
        raise ValueError(f"conditions reference unknown encounters: {sorted(unknown)}")
    if unknown := {row["source_condition_code"] for row in conditions} - mapping_codes:
        raise ValueError(f"conditions have no standard mapping: {sorted(unknown)}")


def initialise_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        PRAGMA foreign_keys = ON;
        CREATE TABLE person (
          person_id INTEGER PRIMARY KEY,
          person_source_value TEXT UNIQUE NOT NULL,
          year_of_birth INTEGER NOT NULL,
          gender_concept_id INTEGER NOT NULL,
          gender_source_value TEXT NOT NULL
        );
        CREATE TABLE visit_occurrence (
          visit_occurrence_id INTEGER PRIMARY KEY,
          person_id INTEGER NOT NULL REFERENCES person(person_id),
          visit_concept_id INTEGER NOT NULL,
          visit_start_date TEXT NOT NULL,
          visit_end_date TEXT NOT NULL,
          visit_source_value TEXT UNIQUE NOT NULL
        );
        CREATE TABLE condition_occurrence (
          condition_occurrence_id INTEGER PRIMARY KEY,
          person_id INTEGER NOT NULL REFERENCES person(person_id),
          visit_occurrence_id INTEGER NOT NULL REFERENCES visit_occurrence(visit_occurrence_id),
          condition_concept_id INTEGER NOT NULL,
          condition_start_date TEXT NOT NULL,
          condition_source_value TEXT NOT NULL
        );
        CREATE TABLE observation_period (
          observation_period_id INTEGER PRIMARY KEY,
          person_id INTEGER NOT NULL REFERENCES person(person_id),
          observation_period_start_date TEXT NOT NULL,
          observation_period_end_date TEXT NOT NULL
        );
        """
    )


def load(output_dir: Path) -> Path:
    patients = read_csv("patients.csv")
    encounters = read_csv("encounters.csv")
    conditions = read_csv("conditions.csv")
    mappings = read_csv("condition_mapping.csv")
    validate_source(patients, encounters, conditions, mappings)
    output_dir.mkdir(parents=True, exist_ok=True)
    database = output_dir / "omop_cdm.sqlite"
    if database.exists():
        database.unlink()
    mapping_by_code = {row["source_condition_code"]: row for row in mappings}
    person_keys = {row["patient_id"]: index for index, row in enumerate(patients, start=1)}
    visit_keys = {row["encounter_id"]: index for index, row in enumerate(encounters, start=1)}

    connection = sqlite3.connect(database)
    try:
        initialise_schema(connection)
        connection.executemany(
            "INSERT INTO person VALUES (?, ?, ?, ?, ?)",
            [(person_keys[row["patient_id"]], row["patient_id"], int(row["birth_year"]), GENDER_CONCEPTS[row["gender_source_value"]], row["gender_source_value"]) for row in patients],
        )
        connection.executemany(
            "INSERT INTO visit_occurrence VALUES (?, ?, ?, ?, ?, ?)",
            [(visit_keys[row["encounter_id"]], person_keys[row["patient_id"]], VISIT_CONCEPTS[row["encounter_type"]], row["encounter_start_date"], row["encounter_end_date"], row["encounter_id"]) for row in encounters],
        )
        connection.executemany(
            "INSERT INTO condition_occurrence VALUES (?, ?, ?, ?, ?, ?)",
            [(index, person_keys[next(item["patient_id"] for item in encounters if item["encounter_id"] == row["encounter_id"])], visit_keys[row["encounter_id"]], int(mapping_by_code[row["source_condition_code"]]["standard_concept_id"]), row["condition_start_date"], row["source_condition_code"]) for index, row in enumerate(conditions, start=1)],
        )
        spans = defaultdict(list)
        for row in encounters:
            spans[row["patient_id"]].append((row["encounter_start_date"], row["encounter_end_date"]))
        connection.executemany(
            "INSERT INTO observation_period VALUES (?, ?, ?, ?)",
            [(index, person_keys[patient_id], min(start for start, _ in dates), max(end for _, end in dates)) for index, (patient_id, dates) in enumerate(sorted(spans.items()), start=1)],
        )
        connection.commit()
    finally:
        connection.close()
    return database


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs")
    args = parser.parse_args()
    database = load(args.output_dir)
    connection = sqlite3.connect(database)
    try:
        counts = [connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in ("person", "visit_occurrence", "condition_occurrence")]
    finally:
        connection.close()
    print(f"Loaded {counts[0]} persons, {counts[1]} visits and {counts[2]} condition records into {database}.")


if __name__ == "__main__":
    main()
