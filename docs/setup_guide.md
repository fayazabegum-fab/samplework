# Setup guide

## Requirements

- Python 3.12
- `uv`
- Terraform 1.10 or later
- Google Cloud CLI for local Application Default Credentials
- An approved GCP project and GCS bucket for Terraform state

## Prepare configuration

Replace the project ID placeholder in the selected `config/*.yaml` file. Confirm the region and resource names with the GCP project owner. Do not put credential values in YAML.

Install dependencies and validate the selected configuration:

```bash
uv sync
uv run python -c \
  'from src.utils.config_loader import load_config; load_config("config/dev.yaml")'
```

For local development, authenticate through Application Default Credentials:

```bash
gcloud auth application-default login
```

Use the attached workload identity when running in GCP.

## Run the application

```bash
uv run python -m src.main --config config/dev.yaml --pipeline sample
```

Omit `--pipeline` to start every pipeline in the selected environment file. Stop the process with Ctrl-C; the consumer cancels its streaming subscriptions and closes clients.

## Run tests

Run the unit suite:

```bash
uv run pytest
```

The integration test writes to GCP and queries the configured table. Use only a non-production project with the topic, subscription, dataset, and table already provisioned:

```bash
RUN_GCP_INTEGRATION_TESTS=1 \
PUBSUB_BQ_TEST_CONFIG=config/test.yaml \
PUBSUB_BQ_TEST_PIPELINE=sample \
uv run pytest tests/integration/test_pubsub_bigquery.py
```
