from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from src.utils.config_loader import ConfigError, load_config


def _write_config(path: Path, **overrides: object) -> Path:
    config: dict[str, object] = {
        "environment": "test",
        "project_id": "sample-project-123",
        "region": "us-central1",
        "pipelines": [
            {
                "name": "sample",
                "topic": "raw-sample-test",
                "subscription": "raw-sample-test-sub",
                "dataset": "raw_test",
                "table": "sample_messages",
                "schema_ref": "sql/tables/raw_message.sql",
            }
        ],
    }
    config.update(overrides)
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return path


def test_loads_multiple_configured_pipelines(tmp_path: Path) -> None:
    config_file = _write_config(
        tmp_path / "test.yaml",
        pipelines=[
            {
                "name": "sample",
                "topic": "raw-sample-test",
                "subscription": "raw-sample-test-sub",
                "dataset": "raw_test",
                "table": "sample_messages",
                "schema_ref": "sql/tables/raw_message.sql",
            },
            {
                "name": "events",
                "topic": "raw-events-test",
                "subscription": "raw-events-test-sub",
                "dataset": "raw_test",
                "table": "event_messages",
                "schema_ref": "sql/tables/raw_message.sql",
            },
        ],
    )

    config = load_config(config_file)

    assert [pipeline.name for pipeline in config.pipelines] == ["sample", "events"]
    assert config.pipelines[1].table == "event_messages"


def test_rejects_placeholder_project_id(tmp_path: Path) -> None:
    config_file = _write_config(tmp_path / "dev.yaml", project_id="replace-with-gcp-project-id")

    with pytest.raises(ConfigError, match="must be replaced"):
        load_config(config_file)


@pytest.mark.parametrize("region", ["northamerica-northeast1", "europe-west10", "US"])
def test_accepts_supported_bigquery_locations(tmp_path: Path, region: str) -> None:
    config_file = _write_config(tmp_path / "test.yaml", region=region)

    config = load_config(config_file)

    assert config.region == region


def test_rejects_unsupported_bigquery_location(tmp_path: Path) -> None:
    config_file = _write_config(tmp_path / "test.yaml", region="northamerica-northeast99")

    with pytest.raises(ConfigError, match="supported BigQuery location"):
        load_config(config_file)


def test_rejects_schema_reference_outside_sql_directory(tmp_path: Path) -> None:
    config_file = _write_config(
        tmp_path / "test.yaml",
        pipelines=[
            {
                "name": "sample",
                "topic": "raw-sample-test",
                "subscription": "raw-sample-test-sub",
                "dataset": "raw_test",
                "table": "sample_messages",
                "schema_ref": "../secret.sql",
            }
        ],
    )

    with pytest.raises(ConfigError, match="relative path under sql"):
        load_config(config_file)


def test_rejects_duplicate_subscription_names(tmp_path: Path) -> None:
    pipeline = {
        "name": "sample",
        "topic": "raw-sample-test",
        "subscription": "raw-sample-test-sub",
        "dataset": "raw_test",
        "table": "sample_messages",
        "schema_ref": "sql/tables/raw_message.sql",
    }
    duplicate = {**pipeline, "name": "events", "topic": "raw-events-test"}
    config_file = _write_config(tmp_path / "test.yaml", pipelines=[pipeline, duplicate])

    with pytest.raises(ConfigError, match="subscription names must be unique"):
        load_config(config_file)
