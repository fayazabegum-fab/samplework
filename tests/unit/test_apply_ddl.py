from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest
import yaml

import scripts.apply_ddl as apply_ddl
from src.utils.config_loader import AppConfig, PipelineConfig


def _config() -> AppConfig:
    return AppConfig(
        environment="test",
        project_id="sample-project-123",
        region="us-central1",
        pipelines=(
            PipelineConfig(
                name="sample",
                topic="raw-sample-test",
                subscription="raw-sample-test-sub",
                dataset="raw_test",
                table="sample_messages",
                schema_ref="sql/tables/raw_message.sql",
            ),
            PipelineConfig(
                name="events",
                topic="raw-events-test",
                subscription="raw-events-test-sub",
                dataset="raw_test",
                table="event_messages",
                schema_ref="sql/tables/raw_message.sql",
            ),
        ),
    )


def _write_config(path: Path) -> Path:
    config = _config()
    path.write_text(
        yaml.safe_dump(
            {
                "environment": config.environment,
                "project_id": config.project_id,
                "region": config.region,
                "pipelines": [
                    {
                        "name": pipeline.name,
                        "topic": pipeline.topic,
                        "subscription": pipeline.subscription,
                        "dataset": pipeline.dataset,
                        "table": pipeline.table,
                        "schema_ref": pipeline.schema_ref,
                    }
                    for pipeline in config.pipelines
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def test_render_ddl_uses_the_configured_table() -> None:
    config = _config()

    statement = apply_ddl.render_ddl(config, config.pipelines[1])

    assert "`sample-project-123.raw_test.event_messages`" in statement
    assert "{{" not in statement


def test_render_ddl_keeps_the_raw_bytes_schema_and_ingestion_partition() -> None:
    config = _config()

    statement = apply_ddl.render_ddl(config, config.pipelines[0])

    assert "payload BYTES NOT NULL" in statement
    assert "PARTITION BY DATE(ingested_at)" in statement


def test_main_executes_ddl_for_the_selected_pipeline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = _write_config(tmp_path / "test.yaml")
    bigquery_client = Mock()
    bigquery_factory = Mock(return_value=bigquery_client)
    monkeypatch.setattr(apply_ddl.bigquery, "Client", bigquery_factory)

    apply_ddl.main(["--config", str(config_path), "--pipeline", "events"])

    statement = bigquery_client.query.call_args.args[0]
    assert "`sample-project-123.raw_test.event_messages`" in statement
    bigquery_client.query.return_value.result.assert_called_once_with()
    bigquery_client.close.assert_called_once_with()
    bigquery_factory.assert_called_once_with(project="sample-project-123", location="us-central1")


def test_main_rejects_an_unknown_pipeline_before_creating_a_client(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = _write_config(tmp_path / "test.yaml")
    bigquery_factory = Mock()
    monkeypatch.setattr(apply_ddl.bigquery, "Client", bigquery_factory)

    with pytest.raises(ValueError, match="is not configured"):
        apply_ddl.main(["--config", str(config_path), "--pipeline", "unknown"])

    bigquery_factory.assert_not_called()


def test_main_closes_client_when_ddl_query_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = _write_config(tmp_path / "test.yaml")
    bigquery_client = Mock()
    bigquery_client.query.side_effect = RuntimeError("DDL query failed")
    monkeypatch.setattr(apply_ddl.bigquery, "Client", Mock(return_value=bigquery_client))

    with pytest.raises(RuntimeError, match="DDL query failed"):
        apply_ddl.main(["--config", str(config_path), "--pipeline", "events"])

    bigquery_client.close.assert_called_once_with()
