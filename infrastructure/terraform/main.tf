locals {
  config = yamldecode(file(var.config_file))

  pipelines = {
    for pipeline in local.config.pipelines : pipeline.name => pipeline
  }

  datasets = {
    for dataset_id in distinct([for pipeline in local.config.pipelines : pipeline.dataset]) :
    dataset_id => dataset_id
  }

  labels = {
    environment = local.config.environment
    service     = "pubsub-bigquery-accelerator"
    managed_by  = "terraform"
  }
}

resource "google_service_account" "ingestion" {
  project      = local.config.project_id
  account_id   = "pubsub-bq-${local.config.environment}"
  display_name = "Pub/Sub BigQuery ingestion ${local.config.environment}"
}

module "pubsub" {
  for_each = local.pipelines
  source   = "../../modules/pubsub"

  project_id        = local.config.project_id
  topic_name        = each.value.topic
  subscription_name = each.value.subscription
  labels            = local.labels
}

module "bigquery" {
  for_each = local.datasets
  source   = "../../modules/bigquery"

  project_id  = local.config.project_id
  dataset_id  = each.value
  location    = local.config.region
  description = "Raw Pub/Sub landing data for ${local.config.environment}"
  labels      = local.labels
}

resource "google_pubsub_subscription_iam_member" "subscriber" {
  for_each = local.pipelines

  project      = local.config.project_id
  subscription = module.pubsub[each.key].subscription_name
  role         = "roles/pubsub.subscriber"
  member       = "serviceAccount:${google_service_account.ingestion.email}"
}

resource "google_project_iam_custom_role" "bigquery_raw_writer" {
  project     = local.config.project_id
  role_id     = "pubsubBigqueryRawWriter"
  title       = "Pub/Sub BigQuery Raw Writer"
  description = "Allows BigQuery streaming inserts into configured raw tables."
  permissions = [
    "bigquery.datasets.get",
    "bigquery.tables.get",
    "bigquery.tables.updateData",
  ]
  stage = "GA"
}

resource "google_bigquery_dataset_iam_member" "writer" {
  for_each = local.datasets

  project    = local.config.project_id
  dataset_id = module.bigquery[each.key].dataset_id
  role       = google_project_iam_custom_role.bigquery_raw_writer.name
  member     = "serviceAccount:${google_service_account.ingestion.email}"
}
