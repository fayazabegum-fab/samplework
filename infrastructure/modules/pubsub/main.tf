resource "google_pubsub_topic" "this" {
  project = var.project_id
  name    = var.topic_name
  labels  = var.labels
}

resource "google_pubsub_subscription" "this" {
  project                    = var.project_id
  name                       = var.subscription_name
  topic                      = google_pubsub_topic.this.id
  ack_deadline_seconds       = 60
  message_retention_duration = "604800s"
  labels                     = var.labels
}
