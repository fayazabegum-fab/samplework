variable "config_file" {
  description = "Path to the selected environment YAML file."
  type        = string
  default     = "../../config/dev.yaml"

  validation {
    condition     = can(yamldecode(file(var.config_file)))
    error_message = "config_file must point to a readable YAML configuration."
  }
}
