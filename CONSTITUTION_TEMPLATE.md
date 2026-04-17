# Project Constitution

> Fill in sections relevant to your project. Delete sections that don't apply.
> Examples below are for a cybersecurity analytics project - adjust to fit your specific work.

## Project Overview

**Name**: Threat Detection Pipeline
**Purpose**: Detect anomalous authentication patterns across enterprise endpoints
**Status**: Active development

## Tech Stack

- **Language**: Python 3.10+
- **Data**: pandas, polars
- **ML**: scikit-learn, xgboost
- **Storage**: Parquet files, PostgreSQL
- **Key Dependencies**: pydantic, pyyaml, python-dotenv

## Architecture

Batch processing pipeline that runs daily:
1. Ingest logs from data lake (Parquet)
2. Feature engineering on auth events
3. Score with trained model
4. Output alerts to analyst queue

## Code Conventions

### Style
- NumPy-style docstrings on public functions
- Type hints on function signatures
- Keep functions under 50 lines

### Naming
- `snake_case` for files, functions, variables
- `PascalCase` for classes
- `UPPER_SNAKE_CASE` for constants

### File Organization
- `src/` - Core logic (feature engineering, scoring, data loading)
- `scripts/` - Entry points and orchestration
- `config/` - YAML configuration files
- `notebooks/` - Exploration only, not production code

## Patterns in Use

- Configuration loaded from `config/config.yaml`, secrets from `.env`
- DataFrames passed through pipeline, not mutated in place
- Logging via standard library `logging`, not print statements
- Pydantic models for validating config and external inputs

## Patterns to Avoid

- No class hierarchies for simple data transformations - use functions
- No abstract base classes unless there are 3+ implementations
- No ORMs - use raw SQL or pandas `read_sql`
- No async - batch jobs don't need it
- Don't optimize prematurely - profile first

## Testing Approach

- Integration tests on full pipeline with sample data
- No unit tests for internal functions unless complex logic
- Tests live in `tests/` with `test_` prefix
- Use pytest fixtures for sample DataFrames

## Known Quirks / Technical Debt

- Legacy feature names in `src/features.py` don't match current schema
- Model expects `user_id` but some sources call it `account_id`
- Retry logic in `src/ingest.py` is copy-pasted, needs refactor

## Additional Context

Users are data scientists and SOC analysts. Prioritize readable code over clever abstractions. When in doubt, write explicit code that's easy to debug.
