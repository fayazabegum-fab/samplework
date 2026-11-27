from __future__ import annotations

import os
import uuid

import pytest
from google.api_core.retry import Retry
from google.cloud import bigquery, pubsub_v1

from src.bigquery.bigquery_writer import BigQueryWriter
from src.main import select_pipelines
from src.pubsub.pubsub_consumer import start_subscription
from src.utils.config_loader import load_config


class _RowNotAvailable(Exception):
    pass


@pytest.mark.integration
def test_pubsub_message_reaches_configured_bigquery_table() -> None:
    if os.getenv("RUN_GCP_INTEGRATION_TESTS") != "1":
        pytest.skip("Set RUN_GCP_INTEGRATION_TESTS=1 to use the configured test project")

    config_path = os.getenv("PUBSUB_BQ_TEST_CONFIG")
    pipeline_name = os.getenv("PUBSUB_BQ_TEST_PIPELINE")
    if not config_path or not pipeline_name:
        pytest.fail("PUBSUB_BQ_TEST_CONFIG and PUBSUB_BQ_TEST_PIPELINE must be set")

    config = load_config(config_path)
    if config.environment != "test":
        pytest.fail("GCP integration tests require an environment: test configuration")
    pipeline = select_pipelines(config, pipeline_name)[0]

    subscriber = pubsub_v1.SubscriberClient()
    publisher = pubsub_v1.PublisherClient()
    bigquery_client = bigquery.Client(project=config.project_id, location=config.region)
    writer = BigQueryWriter(
        bigquery_client,
        config.project_id,
        pipeline.dataset,
        pipeline.table,
    )
    subscription_path = subscriber.subscription_path(config.project_id, pipeline.subscription)
    subscription_future = start_subscription(
        subscriber,
        subscription_path,
        writer,
        pipeline.name,
    )
    run_id = uuid.uuid4().hex
    payload = b"raw-pubsub-bigquery-integration"

    try:
        publisher.publish(
            publisher.topic_path(config.project_id, pipeline.topic),
            payload,
            integration_run_id=run_id,
        ).result(timeout=30)

        query = f"""
            SELECT payload, attributes
            FROM `{config.project_id}.{pipeline.dataset}.{pipeline.table}`
            WHERE JSON_VALUE(attributes, '$.integration_run_id') = @run_id
            ORDER BY ingested_at DESC
            LIMIT 1
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("run_id", "STRING", run_id)]
        )

        def find_row() -> bigquery.Row:
            rows = list(bigquery_client.query(query, job_config=job_config).result())
            if not rows:
                raise _RowNotAvailable
            return rows[0]

        row = Retry(
            predicate=lambda error: isinstance(error, _RowNotAvailable),
            initial=1.0,
            maximum=5.0,
            multiplier=1.5,
            deadline=120.0,
        )(find_row)()
        assert row["payload"] == payload
        assert row["attributes"]["integration_run_id"] == run_id
    finally:
        subscription_future.cancel()
        subscriber.close()
        publisher.close()
        bigquery_client.close()
