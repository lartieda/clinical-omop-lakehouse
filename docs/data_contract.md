# Data contract and mapping rationale

## Source contract

The source files model a minimal clinical extract. Identifiers are stable only within this synthetic dataset. Dates use ISO 8601 (`YYYY-MM-DD`). A production ingestion layer should reject malformed files before a load is attempted.

## OMOP conventions used here

This educational implementation loads a focused OMOP subset rather than the complete specification:

- `person` captures patient-level demographics.
- `visit_occurrence` captures outpatient and inpatient encounters.
- `condition_occurrence` stores a mapped standard concept and retains the source code.
- `observation_period` spans each person's first and last loaded visit.

Gender and visit concepts use fixed standard concept IDs for demonstration. Condition mappings are externalized to `condition_mapping.csv`, which keeps the mapping decision auditable.

## Deliberate limitations

This project is not a clinical production system or an official OHDSI vocabulary distribution. It uses synthetic records and a compact mapping table to demonstrate the design patterns: explicit mapping, relational loading, validation and reproducibility.
