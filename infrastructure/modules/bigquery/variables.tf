variable "project_id" {
  description = "GCP project that owns the dataset."
  type        = string
}

variable "dataset_id" {
  description = "BigQuery dataset identifier."
  type        = string

  validation {
    condition     = can(regex("^[A-Za-z0-9_]{1,1024}$", var.dataset_id))
    error_message = "dataset_id must contain only letters, numbers, and underscores."
  }
}

variable "location" {
  description = "BigQuery dataset location."
  type        = string
}

variable "description" {
  description = "Purpose of the raw landing dataset."
  type        = string
}

variable "labels" {
  description = "Labels applied to the dataset."
  type        = map(string)
  default     = {}
}
