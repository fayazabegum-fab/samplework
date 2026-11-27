"""Consume configured Pub/Sub subscriptions and manage message acknowledgements."""

from __future__ import annotations

import logging
from typing import Any

from src.bigquery.bigquery_writer import BigQueryWriteError

logger = logging.getLogger(__name__)


def process_message(message: Any, writer: Any, pipeline_name: str) -> None:
    """Acknowledge only messages that the configured BigQuery writer accepts."""
    try:
        writer.write(message)
    except BigQueryWriteError:
        logger.exception("BigQuery write failed for pipeline %s", pipeline_name)
        message.nack()
        return

    message.ack()


def start_subscription(
    subscriber: Any,
    subscription_path: str,
    writer: Any,
    pipeline_name: str,
) -> Any:
    """Start asynchronous streaming pull for one configured subscription."""
    return subscriber.subscribe(
        subscription_path,
        callback=lambda message: process_message(message, writer, pipeline_name),
    )
