"""Create a configured raw BigQuery table from its checked-in DDL template."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from google.cloud import bigquery

from src.utils.config_loader import AppConfig, PipelineConfig, load_config

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def select_pipeline(config: AppConfig, pipeline_name: str) -> PipelineConfig:
    """Return a configured pipeline or raise when its name is unknown."""
    for pipeline in config.pipelines:
        if pipeline.name == pipeline_name:
            return pipeline
    raise ValueError(f"Pipeline {pipeline_name!r} is not configured")


def render_ddl(config: AppConfig, pipeline: PipelineConfig) -> str:
    """Fill validated resource identifiers in a repository-owned DDL template."""
    template_path = REPOSITORY_ROOT / pipeline.schema_ref
    statement = template_path.read_text(encoding="utf-8")
    replacements = {
        "{{PROJECT_ID}}": config.project_id,
        "{{DATASET_ID}}": pipeline.dataset,
        "{{TABLE_ID}}": pipeline.table,
    }
    for placeholder, value in replacements.items():
        statement = statement.replace(placeholder, value)
    if "{{" in statement or "}}" in statement:
        raise ValueError(f"DDL template contains an unsupported placeholder: {pipeline.schema_ref}")
    return statement


def main(argv: Sequence[str] | None = None) -> None:
    """Run the selected pipeline's DDL against its configured BigQuery project."""
    parser = argparse.ArgumentParser(description="Create a configured BigQuery raw table")
    parser.add_argument("--config", type=Path, default=Path("config/dev.yaml"))
    parser.add_argument("--pipeline", required=True)
    args = parser.parse_args(argv)

    config = load_config(args.config)
    pipeline = select_pipeline(config, args.pipeline)
    client = bigquery.Client(project=config.project_id, location=config.region)
    try:
        client.query(render_ddl(config, pipeline)).result()
    finally:
        client.close()


if __name__ == "__main__":
    main()
