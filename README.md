# Pub/Sub-to-BigQuery Raw Ingestion Accelerator

## Objective

Read configured Google Cloud Pub/Sub subscriptions and write each original message payload and transport metadata to a configured BigQuery raw table.

## Scope

The application preserves Pub/Sub payload bytes and does not parse, enrich, transform, or deduplicate them. Terraform creates Pub/Sub topics, subscriptions, BigQuery datasets, and the ingestion service account. SQL DDL creates BigQuery tables. Terraform apply, deployment, and branch merge require separate approval.

Delivery is at least once. The application acknowledges a message only after BigQuery accepts the row. A failed write is nacked for Pub/Sub redelivery, so a failed acknowledgement can produce duplicate rows.

## Architecture

The Python worker uses Pub/Sub StreamingPull and BigQuery streaming inserts. It stores payload bytes in a `BYTES` column with the message ID, publish time, attributes, and ingestion time. See [the architecture guide](docs/architecture.md).

## Repository structure

```text
config/                 DEV, TEST, and PROD pipeline configuration
src/                    Python consumer, BigQuery writer, and config loader
infrastructure/         Terraform root and reusable modules
sql/                    BigQuery table DDL
tests/                  Unit and opt-in GCP integration tests
scripts/                Config, infrastructure, and DDL commands
docs/                   Architecture, setup, and deployment guides
```

## Prerequisites

- Python 3.12 and `uv`
- Terraform 1.10 or later
- Google Cloud CLI for local Application Default Credentials
- Approved GCP project IDs, region, GCS Terraform state bucket, and required API permissions

## Configuration

Edit `config/dev.yaml`, `config/test.yaml`, or `config/prod.yaml`. Replace each project ID placeholder before running the application or validating a profile. Add pipelines by adding an entry with a unique name, topic, subscription, dataset and table, plus a schema reference.

Install the locked dependencies with `uv sync`. Validate all environment files after replacing placeholders:

```bash
bash scripts/validate_config.sh
```

## Terraform

The Terraform root reads the selected YAML file. For a syntax and module preflight that does not use a remote backend:

```bash
bash scripts/deploy_infrastructure.sh dev
```

For an environment plan, provide its GCS state bucket and existing GCP credentials:

```bash
TF_STATE_BUCKET=<approved-state-bucket> RUN_TERRAFORM_PLAN=1 \
  bash scripts/deploy_infrastructure.sh dev
```

The [deployment guide](docs/deployment_guide.md) covers `terraform init`, `fmt`, `validate`, `plan`, and the separately approved `apply` command.

## BigQuery DDL

After the dataset exists, create a configured table with:

```bash
uv run python -m scripts.apply_ddl --config config/dev.yaml --pipeline sample
```

The script runs the checked-in DDL in `sql/tables/raw_message.sql`. DDL execution writes to GCP and requires the configured project and dataset permissions.

## Run and test

Start one configured pipeline:

```bash
uv run python -m src.main --config config/dev.yaml --pipeline sample
```

Run unit tests with `uv run pytest`. The GCP integration test publishes a test message and verifies its arrival in the configured test table. It requires an approved non-production project and Application Default Credentials:

```bash
RUN_GCP_INTEGRATION_TESTS=1 \
PUBSUB_BQ_TEST_CONFIG=config/test.yaml \
PUBSUB_BQ_TEST_PIPELINE=sample \
uv run pytest tests/integration/test_pubsub_bigquery.py
```

## Deployment prerequisites

Replace all placeholders, confirm the project, region, state bucket, and runtime identity, enable the Pub/Sub, BigQuery, and IAM APIs, and run a reviewed Terraform plan. Create tables from DDL after the datasets exist. Attach the output service account to the approved runtime. Review, approve, and execute any `terraform apply` or deployment separately.

See the [setup guide](docs/setup_guide.md) and [deployment guide](docs/deployment_guide.md) for the full procedures.

## Contributing

Run `uv run pytest` before requesting review. Keep environment-specific project and state values out of committed configuration. Do not run Terraform apply, deploy, or merge without explicit approval.