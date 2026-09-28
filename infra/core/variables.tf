variable "aws_region" { type = string }
variable "environment" { type = string }
variable "owner" { type = string }
variable "cost_center" { type = string }
variable "vpc_cidr" { type = string }
variable "availability_zones" {
  type        = list(string)
  description = "Exactly two approved AZs for this short-lived lab."
  validation {
    condition     = length(var.availability_zones) == 2
    error_message = "Provide exactly two availability zones."
  }
}
variable "cluster_name" { type = string }
variable "kubernetes_version" {
  type        = string
  description = "EKS version explicitly approved for the target region."
}
variable "node_instance_types" {
  type    = list(string)
  default = ["t3.medium"]
}
variable "lab_expiry" {
  type        = string
  description = "RFC3339 stop time recorded for human teardown; tags do not automatically delete resources."
}

variable "github_plan_subject" {
  type        = string
  description = "Exact GitHub OIDC sub claim for the reviewed plan workflow; wildcard subjects are forbidden."
  validation {
    condition     = startswith(var.github_plan_subject, "repo:") && !strcontains(var.github_plan_subject, "*")
    error_message = "github_plan_subject must be an exact GitHub repo subject and must not contain a wildcard."
  }
}

variable "github_apply_subject" {
  type        = string
  description = "Exact GitHub OIDC sub claim for the protected apply environment; wildcard subjects are forbidden."
  validation {
    condition     = startswith(var.github_apply_subject, "repo:") && !strcontains(var.github_apply_subject, "*")
    error_message = "github_apply_subject must be an exact GitHub repo/environment subject and must not contain a wildcard."
  }
}
