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
variable "db_name" {
  type    = string
  default = "insighthub"
}
variable "db_username" {
  type    = string
  default = "insighthub"
}
variable "db_instance_class" {
  type    = string
  default = "db.t4g.micro"
}
variable "db_engine_version" {
  type        = string
  description = "Exact PostgreSQL 16 version confirmed to support pgvector in the approved region."
}
variable "redis_node_type" {
  type    = string
  default = "cache.t4g.micro"
}
variable "redis_engine_version" {
  type        = string
  description = "Exact Redis OSS 7 version approved for the target region."
}
variable "lab_recreatable_data" {
  type        = bool
  default     = true
  description = "True only for approved short labs with reproducible data; controls RDS final snapshot behavior."
}
