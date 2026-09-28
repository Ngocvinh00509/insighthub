variable "aws_region" { type = string }
variable "environment" { type = string }
variable "owner" { type = string }
variable "cost_center" { type = string }
variable "lab_expiry" { type = string }
variable "core_state_bucket" { type = string }
variable "core_state_key" { type = string }
variable "core_state_region" { type = string }
variable "namespace" {
  type    = string
  default = "insighthub-dev"
}
