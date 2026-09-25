# Clinical OMOP Lakehouse

A reproducible PySpark and Delta Lake project that transforms synthetic clinical source data into a focused subset of the [OMOP Common Data Model](https://www.ohdsi.org/data-standardization/the-common-data-model/). It is designed as a portfolio project for biomedical data engineering, clinical informatics and healthcare data-platform roles.

> **Data note:** all records in this repository are synthetic. They do not describe real patients, events or healthcare providers.

## Why this project

Clinical data work is not only model building. Reliable downstream analysis depends on transparent source-to-target mappings, data-quality controls and traceable transformations. This project demonstrates those principles end to end:

- bronze, silver and gold data layers in Delta Lake;
- source data ingestion and schema checks with PySpark;
- explicit source-code to standard-concept mapping;
- loading a relational OMOP CDM subset as Delta tables;
- referential-integrity and plausibility checks;
- reusable Gold tables for quality monitoring and cohort analysis;
- a Power BI dashboard fed from Gold-layer CSV exports;
- automated tests and GitHub Actions CI.

## Lakehouse architecture

```text
synthetic clinical CSV source data
        |
        v
Bronze: immutable source-aligned Delta tables
        |
        v
Silver: validated OMOP CDM subset + explicit concept mappings
  person | visit_occurrence | condition_occurrence | observation_period
        |
        +------------------> Gold: quality metrics + condition summary + patient utilization + cohort demographics
```

## Run in Databricks

1. Create a schema called `clinical_portfolio` in your active catalog.
2. Create a volume called `source` inside that schema and upload the four CSVs from `data/source/`.
3. Import the notebooks in order from `notebooks/`.
4. In notebook 01, update the `SOURCE_VOLUME` path with your active catalog name.
5. Run notebooks 01 to 05 in sequence.

The Databricks notebooks use the platform's built-in PySpark and Delta Lake runtime. The final tables are:

| Layer | Tables |
| --- | --- |
| Bronze | `bronze_patients`, `bronze_encounters`, `bronze_conditions`, `bronze_condition_mapping` |
| Silver | `person`, `visit_occurrence`, `condition_occurrence`, `observation_period` |
| Gold | `gold_quality_metrics`, `gold_condition_summary`, `gold_patient_utilization`, `gold_cohort_demographics` |

Notebook 05 exports the Gold tables as CSV files for the accompanying Power BI report. The report uses synthetic data only and is intended as a portfolio artifact, not as a clinical decision-support tool.

## Dashboard

The companion Power BI report presents a compact data-quality and cohort overview:

- headline metrics for patients, visits, mapped condition events and visit linkage;
- condition-event and unique-patient counts by diagnosis;
- patient distribution by sex.

Save the report as `clinical_omop_lakehouse_dashboard.pbix` and place a screenshot at `assets/dashboard_overview.png` before publishing the repository. Do not commit credentials, tokens, patient-level extracts or any non-synthetic data.

## Local prototype

The original lightweight local prototype uses only the Python standard library and remains useful for fast unit tests.

```bash
python -m src.clinical_omop_pipeline.etl --output-dir outputs
python -m src.clinical_omop_pipeline.quality --database outputs/omop_cdm.sqlite --report outputs/quality_report.json
```

Expected results:

```text
Loaded 6 persons, 8 visits and 9 condition records.
Data-quality checks: 8 passed, 0 failed.
```

Run the test suite:

```bash
python -m unittest discover -s tests -v
```

## Source data and mapping decisions

The source extract contains four small CSV files:

| Source file | Purpose | OMOP target |
| --- | --- | --- |
| `patients.csv` | demographic extract | `person` |
| `encounters.csv` | encounter extract | `visit_occurrence` |
| `conditions.csv` | coded diagnoses | `condition_occurrence` |
| `condition_mapping.csv` | source-to-standard mapping | standard concept fields |

The mapping table is deliberately versioned and human-readable. In a production implementation it would be maintained with vocabulary release metadata, mapping governance and change control.

## Quality checks

The quality module validates:

- target table row counts;
- duplicate primary keys;
- person/visit referential integrity;
- visit dates occurring after birth year;
- condition start dates within their visit interval;
- use of only mapped standard condition concepts;
- observation-period coverage for each person.

## Project structure

```text
clinical-omop-data-pipeline/
├── data/source/                 # synthetic source extracts
├── docs/                        # data contract and mapping rationale
├── notebooks/                   # Databricks PySpark notebooks
├── src/clinical_lakehouse/      # reusable PySpark transformations
├── src/clinical_omop_pipeline/  # lightweight local prototype
├── tests/                       # automated tests
└── .github/workflows/ci.yml     # continuous integration
```

## Skills demonstrated

PySpark, Databricks, Delta Lake, SQL, clinical data standardization, OMOP CDM, ETL, data quality, testing, Git, and GitHub Actions.

## Next improvements

- Add an incremental-load pattern and audit table.
- Add vocabulary versioning and mapping coverage metrics.
- Port the SQL layer to DuckDB or PostgreSQL.
- Add an incremental-load pattern and audit table.
- Connect the dashboard directly to a governed Databricks SQL warehouse.
