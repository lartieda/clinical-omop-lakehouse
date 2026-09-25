"""Data-quality metrics for the synthetic OMOP lakehouse."""

from pyspark.sql import DataFrame, SparkSession, functions as F


def quality_metrics(spark: SparkSession, schema: str) -> DataFrame:
    """Return transparent quality metrics as a queryable DataFrame."""
    checks = [
        ("person_count", f"SELECT COUNT(*) AS observed FROM {schema}.person", 6),
        ("visit_count", f"SELECT COUNT(*) AS observed FROM {schema}.visit_occurrence", 8),
        ("condition_count", f"SELECT COUNT(*) AS observed FROM {schema}.condition_occurrence", 9),
        ("orphan_visits", f"SELECT COUNT(*) AS observed FROM {schema}.visit_occurrence v LEFT ANTI JOIN {schema}.person p ON p.person_id = v.person_id", 0),
        ("orphan_conditions", f"SELECT COUNT(*) AS observed FROM {schema}.condition_occurrence c LEFT ANTI JOIN {schema}.visit_occurrence v ON v.visit_occurrence_id = c.visit_occurrence_id", 0),
        ("conditions_outside_visit", f"SELECT COUNT(*) AS observed FROM {schema}.condition_occurrence c JOIN {schema}.visit_occurrence v ON v.visit_occurrence_id = c.visit_occurrence_id WHERE c.condition_start_date NOT BETWEEN v.visit_start_date AND v.visit_end_date", 0),
    ]
    rows = []
    for name, query, expected in checks:
        observed = spark.sql(query).first()["observed"]
        rows.append((name, int(observed), expected, "passed" if observed == expected else "failed"))
    return spark.createDataFrame(rows, ["check_name", "observed", "expected", "status"]).withColumn("checked_at", F.current_timestamp())
