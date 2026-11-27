output "dataset_id" {
  description = "BigQuery dataset identifier."
  value       = google_bigquery_dataset.this.dataset_id
}

output "dataset_name" {
  description = "Fully qualified BigQuery dataset name."
  value       = google_bigquery_dataset.this.id
}
