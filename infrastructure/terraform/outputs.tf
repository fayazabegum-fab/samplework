output "service_account_email" {
  description = "Identity the runtime must use for ingestion."
  value       = google_service_account.ingestion.email
}

output "topic_ids" {
  description = "Pub/Sub topic IDs keyed by configured pipeline."
  value = {
    for name, resources in module.pubsub : name => resources.topic_id
  }
}

output "subscription_ids" {
  description = "Pub/Sub subscription IDs keyed by configured pipeline."
  value = {
    for name, resources in module.pubsub : name => resources.subscription_id
  }
}

output "dataset_ids" {
  description = "BigQuery dataset IDs provisioned for this environment."
  value       = { for dataset_id, resources in module.bigquery : dataset_id => resources.dataset_id }
}
