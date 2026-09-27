variable "aws_region" {
  type        = string
  description = "AWS region approved for the short-lived lab."
}

variable "state_bucket_name" {
  type        = string
  description = "Globally unique S3 bucket name for Terraform remote state."

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$", var.state_bucket_name))
    error_message = "state_bucket_name must be a valid 3-63 character lowercase S3 bucket name."
  }
}

variable "environment" {
  type        = string
  description = "Lab environment name, for example dev."
}

variable "owner" {
  type        = string
  description = "Named lab owner responsible for teardown."
}

variable "cost_center" {
  type        = string
  description = "Approved cost-center label."
}
