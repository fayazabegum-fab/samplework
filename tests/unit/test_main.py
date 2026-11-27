from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import Future
from datetime import UTC, datetime
from unittest.mock import Mock

import pytest

import src.main as main_module
from src.utils.config_loader import AppConfig, PipelineConfig


class _Subscriber:
    def __init__(self) -> None:
        self.subscription_paths: list[str] = []
        self.messages: list[Mock] = []

    def subscription_path(self, project_id: str, subscription: str) -> str:
        return f"projects/{project_id}/subscriptions/{subscription}"

    def subscribe(self, subscription_path: str, callback: Callable[[Mock], None]) -> Future[None]:
        self.subscription_paths.append(subscription_path)
        message = Mock()
        message.data = b"\x00raw-payload"
        message.message_id = "message-123"
        message.publish_time = datetime(2026, 11, 26, 10, 0, tzinfo=UTC)
        message.attributes = {"source": "unit-test"}
        self.messages.append(message)
        callback(message)

        future: Future[None] = Future()
        future.set_result(None)
        return future

    def close(self) -> None:
        pass


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


@pytest.mark.parametrize(
    ("pipeline_name", "expected_names"),
    [
        ("events", ["events"]),
        (None, ["sample", "events"]),
    ],
)
def test_run_uses_configured_subscriptions_and_tables(
    monkeypatch: pytest.MonkeyPatch,
    pipeline_name: str | None,
    expected_names: list[str],
) -> None:
    subscriber = _Subscriber()
    subscriber_factory = Mock(return_value=subscriber)
    bigquery_client = Mock()
    bigquery_client.insert_rows_json.return_value = []
    bigquery_factory = Mock(return_value=bigquery_client)
    monkeypatch.setattr(main_module.pubsub_v1, "SubscriberClient", subscriber_factory)
    monkeypatch.setattr(main_module.bigquery, "Client", bigquery_factory)

    with pytest.raises(RuntimeError, match="All Pub/Sub subscriptions stopped"):
        main_module.run(_config(), pipeline_name)

    assert subscriber.subscription_paths == [
        f"projects/sample-project-123/subscriptions/raw-{name}-test-sub" for name in expected_names
    ]
    expected_tables = {"sample": "sample_messages", "events": "event_messages"}
    assert [call.args[0] for call in bigquery_client.insert_rows_json.call_args_list] == [
        f"sample-project-123.raw_test.{expected_tables[name]}" for name in expected_names
    ]
    assert all(message.ack.call_count == 1 for message in subscriber.messages)
    assert subscriber_factory.call_count == 1
    bigquery_factory.assert_called_once_with(project="sample-project-123", location="us-central1")


def test_run_propagates_subscription_future_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    subscriber = _Subscriber()
    subscriber_factory = Mock(return_value=subscriber)
    subscriber_close = Mock()
    bigquery_client = Mock()
    failed_future: Future[None] = Future()
    failed_future.set_exception(RuntimeError("subscription failed"))
    monkeypatch.setattr(subscriber, "close", subscriber_close)
    monkeypatch.setattr(main_module.pubsub_v1, "SubscriberClient", subscriber_factory)
    monkeypatch.setattr(main_module.bigquery, "Client", Mock(return_value=bigquery_client))
    monkeypatch.setattr(main_module, "start_subscription", Mock(return_value=failed_future))

    with pytest.raises(RuntimeError, match="subscription failed"):
        main_module.run(_config(), "sample")

    subscriber_close.assert_called_once_with()
    bigquery_client.close.assert_called_once_with()


def test_run_cancels_other_subscriptions_after_future_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    subscriber = _Subscriber()
    subscriber_close = Mock()
    bigquery_client = Mock()
    failed_future: Future[None] = Future()
    failed_future.set_exception(RuntimeError("subscription failed"))
    pending_future: Future[None] = Future()
    monkeypatch.setattr(subscriber, "close", subscriber_close)
    monkeypatch.setattr(main_module.pubsub_v1, "SubscriberClient", Mock(return_value=subscriber))
    monkeypatch.setattr(main_module.bigquery, "Client", Mock(return_value=bigquery_client))
    monkeypatch.setattr(
        main_module,
        "start_subscription",
        Mock(side_effect=[failed_future, pending_future]),
    )

    with pytest.raises(RuntimeError, match="subscription failed"):
        main_module.run(_config())

    assert pending_future.cancelled()
    subscriber_close.assert_called_once_with()
    bigquery_client.close.assert_called_once_with()
