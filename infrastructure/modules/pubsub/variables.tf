variable "project_id" {
  description = "GCP project that owns the topic and subscription."
  type        = string
}

variable "topic_name" {
  description = "Pub/Sub topic name."
  type        = string

  validation {
    condition     = can(regex("^[A-Za-z][A-Za-z0-9._~+%-]{2,254}$", var.topic_name))
    error_message = "topic_name must be a valid Pub/Sub identifier."
  }
}

variable "subscription_name" {
  description = "Pull subscription name."
  type        = string

  validation {
    condition     = can(regex("^[A-Za-z][A-Za-z0-9._~+%-]{2,254}$", var.subscription_name))
    error_message = "subscription_name must be a valid Pub/Sub identifier."
  }
}

variable "labels" {
  description = "Labels applied to Pub/Sub resources."
  type        = map(string)
  default     = {}
}
