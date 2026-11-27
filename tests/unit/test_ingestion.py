from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import Mock

import pytest
from google.api_core.exceptions import GoogleAPICallError

from src.bigquery.bigquery_writer import (
    BigQueryWriteError,
    BigQueryWriter,
    build_raw_row,
)
from src.main import select_pipelines
from src.pubsub.pubsub_consumer import process_message
from src.utils.config_loader import AppConfig, PipelineConfig


def _message(data: bytes = b"\x00\xffraw") -> Mock:
    message = Mock()
    message.data = data
    message.message_id = "message-123"
    message.publish_time = datetime(2026, 11, 26, 10, 0, tzinfo=UTC)
    message.attributes = {"source": "unit-test"}
    return message


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
        ),
    )


def test_raw_row_preserves_payload_bytes_and_transport_metadata() -> None:
    ingested_at = datetime(2026, 11, 26, 10, 1, tzinfo=UTC)

    row = build_raw_row(_message(), ingested_at)

    assert row == {
        "payload": "AP9yYXc=",
        "message_id": "message-123",
        "publish_time": "2026-11-26T10:00:00+00:00",
        "attributes": {"source": "unit-test"},
        "ingested_at": "2026-11-26T10:01:00+00:00",
    }


def test_writer_omits_insert_ids_and_raises_on_row_errors() -> None:
    client = Mock()
    client.insert_rows_json.return_value = [{"index": 0, "errors": [{"reason": "invalid"}]}]
    writer = BigQueryWriter(
        client,
        "sample-project-123",
        "raw_test",
        "sample_messages",
        clock=lambda: datetime(2026, 11, 26, 10, 1, tzinfo=UTC),
    )

    with pytest.raises(BigQueryWriteError, match="rejected a raw message row"):
        writer.write(_message())

    client.insert_rows_json.assert_called_once()
    assert client.insert_rows_json.call_args.kwargs["row_ids"] == [None]


def test_writer_wraps_bigquery_request_failures() -> None:
    client = Mock()
    client.insert_rows_json.side_effect = GoogleAPICallError("request failed")
    writer = BigQueryWriter(
        client,
        "sample-project-123",
        "raw_test",
        "sample_messages",
    )

    with pytest.raises(BigQueryWriteError, match="request failed"):
        writer.write(_message())


def test_message_is_acknowledged_after_successful_write() -> None:
    message = _message()
    writer = Mock()

    process_message(message, writer, "sample")

    message.ack.assert_called_once_with()
    message.nack.assert_not_called()


def test_message_is_nacked_when_bigquery_write_fails() -> None:
    message = _message()
    writer = Mock()
    writer.write.side_effect = BigQueryWriteError("insert failed")

    process_message(message, writer, "sample")

    message.nack.assert_called_once_with()
    message.ack.assert_not_called()


def test_pipeline_selection_uses_configured_name() -> None:
    selected = select_pipelines(_config(), "sample")

    assert len(selected) == 1
    assert selected[0].subscription == "raw-sample-test-sub"


def test_pipeline_selection_reports_unknown_name() -> None:
    with pytest.raises(ValueError, match="is not configured"):
        select_pipelines(_config(), "unknown")
