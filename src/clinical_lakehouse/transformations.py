"""Portable PySpark transformations used by the Databricks notebooks."""

from pyspark.sql import DataFrame, functions as F

GENDER_CONCEPTS = {"M": 8507, "F": 8532}
VISIT_CONCEPTS = {"outpatient": 9202, "inpatient": 9201}


def add_ingestion_metadata(frame: DataFrame, source_file: str) -> DataFrame:
    """Keep raw records source-aligned while adding auditable ingestion metadata."""
    return (
        frame.withColumn("_ingested_at", F.current_timestamp())
        .withColumn("_source_file", F.lit(source_file))
        .withColumn("_batch_id", F.date_format(F.current_timestamp(), "yyyyMMddHHmmss"))
    )


def person(patients: DataFrame) -> DataFrame:
    mapping = F.create_map([F.lit(item) for pair in GENDER_CONCEPTS.items() for item in pair])
    return patients.select(
        F.abs(F.xxhash64("patient_id")).alias("person_id"),
        F.col("patient_id").alias("person_source_value"),
        F.col("birth_year").cast("int").alias("year_of_birth"),
        mapping[F.col("gender_source_value")].cast("int").alias("gender_concept_id"),
        "gender_source_value",
    )


def visit_occurrence(encounters: DataFrame, people: DataFrame) -> DataFrame:
    mapping = F.create_map([F.lit(item) for pair in VISIT_CONCEPTS.items() for item in pair])
    return (
        encounters.join(people.select("person_id", "person_source_value"), encounters.patient_id == people.person_source_value, "inner")
        .select(
            F.abs(F.xxhash64("encounter_id")).alias("visit_occurrence_id"),
            "person_id",
            mapping[F.col("encounter_type")].cast("int").alias("visit_concept_id"),
            F.to_date("encounter_start_date").alias("visit_start_date"),
            F.to_date("encounter_end_date").alias("visit_end_date"),
            F.col("encounter_id").alias("visit_source_value"),
        )
    )


def condition_occurrence(conditions: DataFrame, encounters: DataFrame, visits: DataFrame, people: DataFrame, mappings: DataFrame) -> DataFrame:
    encounter_people = encounters.select("encounter_id", "patient_id")
    return (
        conditions.join(mappings.filter(F.col("mapping_status") == "standard"), "source_condition_code", "inner")
        .join(encounter_people, "encounter_id", "inner")
        .join(people.select("person_id", "person_source_value"), F.col("patient_id") == F.col("person_source_value"), "inner")
        .join(visits.select("visit_occurrence_id", "visit_source_value"), F.col("encounter_id") == F.col("visit_source_value"), "inner")
        .select(
            F.abs(F.xxhash64("condition_event_id")).alias("condition_occurrence_id"),
            "person_id",
            "visit_occurrence_id",
            F.col("standard_concept_id").cast("int").alias("condition_concept_id"),
            F.to_date("condition_start_date").alias("condition_start_date"),
            F.col("source_condition_code").alias("condition_source_value"),
        )
    )


def observation_period(visits: DataFrame) -> DataFrame:
    return visits.groupBy("person_id").agg(
        F.min("visit_start_date").alias("observation_period_start_date"),
        F.max("visit_end_date").alias("observation_period_end_date"),
    ).withColumn("observation_period_id", F.abs(F.xxhash64("person_id"))).select(
        "observation_period_id", "person_id", "observation_period_start_date", "observation_period_end_date"
    )
