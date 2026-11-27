"""Run configured Pub/Sub-to-BigQuery raw ingestion pipelines."""

from __future__ import annotations

import argparse
import logging
from collections.abc import Sequence
from concurrent.futures import FIRST_EXCEPTION, Future, wait
from pathlib import Path

from google.cloud import bigquery, pubsub_v1

from src.bigquery.bigquery_writer import BigQueryWriter
from src.pubsub.pubsub_consumer import start_subscription
from src.utils.config_loader import AppConfig, PipelineConfig, load_config

logger = logging.getLogger(__name__)


def select_pipelines(config: AppConfig, pipeline_name: str | None) -> tuple[PipelineConfig, ...]:
    """Select all configured pipelines or one named pipeline."""
    if pipeline_name is None:
        return config.pipelines

    selected = tuple(pipeline for pipeline in config.pipelines if pipeline.name == pipeline_name)
    if not selected:
        raise ValueError(f"Pipeline {pipeline_name!r} is not configured")
    return selected


def run(config: AppConfig, pipeline_name: str | None = None) -> None:
    """Start the selected pipelines and close clients when the process exits."""
    pipelines = select_pipelines(config, pipeline_name)
    subscriber = pubsub_v1.SubscriberClient()
    bigquery_client = bigquery.Client(project=config.project_id, location=config.region)
    futures: list[Future[None]] = []

    try:
        for pipeline in pipelines:
            subscription_path = subscriber.subscription_path(
                config.project_id,
                pipeline.subscription,
            )
            writer = BigQueryWriter(
                bigquery_client,
                config.project_id,
                pipeline.dataset,
                pipeline.table,
            )
            futures.append(start_subscription(subscriber, subscription_path, writer, pipeline.name))

        done, _ = wait(futures, return_when=FIRST_EXCEPTION)
        for future in done:
            future.result()
        raise RuntimeError("All Pub/Sub subscriptions stopped without an error")
    except KeyboardInterrupt:
        logger.info("Stopping Pub/Sub subscriptions")
    finally:
        for future in futures:
            future.cancel()
        subscriber.close()
        bigquery_client.close()


def main(argv: Sequence[str] | None = None) -> None:
    """Load configuration and start ingestion."""
    parser = argparse.ArgumentParser(description="Ingest raw Pub/Sub messages into BigQuery")
    parser.add_argument("--config", type=Path, default=Path("config/dev.yaml"))
    parser.add_argument("--pipeline")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    run(load_config(args.config), args.pipeline)


if __name__ == "__main__":
    main()
