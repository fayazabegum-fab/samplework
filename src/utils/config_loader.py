"""Load and validate Pub/Sub-to-BigQuery pipeline configuration."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

_PROJECT_ID = re.compile(r"[a-z][a-z0-9-]{4,28}[a-z0-9]\Z")
_PIPELINE_NAME = re.compile(r"[a-z][a-z0-9-]{0,62}\Z")
_PUBSUB_NAME = re.compile(r"[A-Za-z][A-Za-z0-9._~+%-]{2,254}\Z")
_BIGQUERY_ID = re.compile(r"[A-Za-z0-9_]{1,1024}\Z")
_ENVIRONMENTS = {"dev", "test", "prod"}
_BIGQUERY_LOCATIONS = frozenset(
    {
        "africa-south1",
        "asia-east1",
        "asia-east2",
        "asia-northeast1",
        "asia-northeast2",
        "asia-northeast3",
        "asia-south1",
        "asia-south2",
        "asia-southeast1",
        "asia-southeast2",
        "asia-southeast3",
        "australia-southeast1",
        "australia-southeast2",
        "EU",
        "europe-central2",
        "europe-north1",
        "europe-north2",
        "europe-southwest1",
        "europe-west1",
        "europe-west2",
        "europe-west3",
        "europe-west4",
        "europe-west6",
        "europe-west8",
        "europe-west9",
        "europe-west10",
        "europe-west12",
        "me-central1",
        "me-central2",
        "me-west1",
        "northamerica-northeast1",
        "northamerica-northeast2",
        "northamerica-south1",
        "southamerica-east1",
        "southamerica-west1",
        "US",
        "us-central1",
        "us-central2",
        "us-east1",
        "us-east4",
        "us-east5",
        "us-south1",
        "us-west1",
        "us-west2",
        "us-west3",
        "us-west4",
    }
)


class ConfigError(ValueError):
    """Raised when an ingestion configuration is missing or invalid."""


@dataclass(frozen=True)
class PipelineConfig:
    """Configuration for one Pub/Sub subscription and BigQuery table."""

    name: str
    topic: str
    subscription: str
    dataset: str
    table: str
    schema_ref: str


@dataclass(frozen=True)
class AppConfig:
    """Validated configuration shared by the process and Terraform."""

    environment: str
    project_id: str
    region: str
    pipelines: tuple[PipelineConfig, ...]


def _mapping(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ConfigError(f"{context} must be a mapping")
    return value


def _required_string(mapping: dict[str, Any], key: str, context: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{context}.{key} must be a non-empty string")
    return value.strip()


def _validate_keys(mapping: dict[str, Any], expected: set[str], context: str) -> None:
    unknown = set(mapping) - expected
    if unknown:
        raise ConfigError(f"{context} contains unsupported fields: {', '.join(sorted(unknown))}")


def _schema_reference(value: str, context: str) -> str:
    path = PurePosixPath(value)
    if not path.parts or path.is_absolute() or ".." in path.parts or path.parts[0] != "sql":
        raise ConfigError(f"{context}.schema_ref must be a relative path under sql/")
    return value


def load_config(path: str | Path) -> AppConfig:
    """Load a YAML profile and reject invalid or deployment-placeholder values."""
    config_path = Path(path)
    try:
        raw_config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise ConfigError(f"Could not parse configuration file {config_path}") from error

    config = _mapping(raw_config, "configuration")
    _validate_keys(config, {"environment", "project_id", "region", "pipelines"}, "configuration")

    environment = _required_string(config, "environment", "configuration")
    if environment not in _ENVIRONMENTS:
        raise ConfigError("configuration.environment must be dev, test, or prod")

    project_id = _required_string(config, "project_id", "configuration")
    if "replace" in project_id.lower() or "placeholder" in project_id.lower():
        raise ConfigError("configuration.project_id must be replaced with a GCP project ID")
    if not _PROJECT_ID.fullmatch(project_id):
        raise ConfigError("configuration.project_id must be a valid GCP project ID")

    region = _required_string(config, "region", "configuration")
    if region not in _BIGQUERY_LOCATIONS:
        raise ConfigError("configuration.region must be a supported BigQuery location")

    raw_pipelines = config.get("pipelines")
    if not isinstance(raw_pipelines, list) or not raw_pipelines:
        raise ConfigError("configuration.pipelines must be a non-empty list")

    pipelines: list[PipelineConfig] = []
    for index, raw_pipeline in enumerate(raw_pipelines):
        context = f"configuration.pipelines[{index}]"
        pipeline = _mapping(raw_pipeline, context)
        expected = {"name", "topic", "subscription", "dataset", "table", "schema_ref"}
        _validate_keys(pipeline, expected, context)

        name = _required_string(pipeline, "name", context)
        if not _PIPELINE_NAME.fullmatch(name):
            raise ConfigError(f"{context}.name must be a lowercase identifier")

        topic = _required_string(pipeline, "topic", context)
        subscription = _required_string(pipeline, "subscription", context)
        if not _PUBSUB_NAME.fullmatch(topic) or not _PUBSUB_NAME.fullmatch(subscription):
            raise ConfigError(f"{context} topic and subscription must be valid Pub/Sub identifiers")

        dataset = _required_string(pipeline, "dataset", context)
        table = _required_string(pipeline, "table", context)
        if not _BIGQUERY_ID.fullmatch(dataset) or not _BIGQUERY_ID.fullmatch(table):
            raise ConfigError(f"{context} dataset and table must be valid BigQuery identifiers")

        schema_ref = _schema_reference(_required_string(pipeline, "schema_ref", context), context)
        pipelines.append(
            PipelineConfig(
                name=name,
                topic=topic,
                subscription=subscription,
                dataset=dataset,
                table=table,
                schema_ref=schema_ref,
            )
        )

    names = [pipeline.name for pipeline in pipelines]
    topics = [pipeline.topic for pipeline in pipelines]
    subscriptions = [pipeline.subscription for pipeline in pipelines]
    tables = [(pipeline.dataset, pipeline.table) for pipeline in pipelines]
    if len(set(names)) != len(names):
        raise ConfigError("configuration pipeline names must be unique")
    if len(set(topics)) != len(topics):
        raise ConfigError("configuration topic names must be unique")
    if len(set(subscriptions)) != len(subscriptions):
        raise ConfigError("configuration subscription names must be unique")
    if len(set(tables)) != len(tables):
        raise ConfigError("configuration dataset and table pairs must be unique")

    return AppConfig(
        environment=environment,
        project_id=project_id,
        region=region,
        pipelines=tuple(pipelines),
    )
