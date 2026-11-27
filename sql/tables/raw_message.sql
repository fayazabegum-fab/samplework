CREATE TABLE IF NOT EXISTS `{{PROJECT_ID}}.{{DATASET_ID}}.{{TABLE_ID}}` (
  payload BYTES NOT NULL,
  message_id STRING NOT NULL,
  publish_time TIMESTAMP NOT NULL,
  attributes JSON NOT NULL,
  ingested_at TIMESTAMP NOT NULL
)
PARTITION BY DATE(ingested_at)
OPTIONS (
  description = "Unmodified Pub/Sub payload bytes and transport metadata"
);
