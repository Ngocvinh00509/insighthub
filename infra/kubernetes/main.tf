locals {
  standard_tags = {
    project     = "insighthub"
    environment = var.environment
    owner       = var.owner
    cost_center = var.cost_center
    managed_by  = "terraform"
    lab_expiry  = var.lab_expiry
  }
}

data "terraform_remote_state" "core" {
  backend = "s3"
  config = {
    bucket       = var.core_state_bucket
    key          = var.core_state_key
    region       = var.core_state_region
    use_lockfile = true
    encrypt      = true
  }
}

# The EKS API is private. This root is deliberately independent from the AWS
# Platform root and must run only on the existing self-hosted VPC runner.
resource "kubernetes_namespace_v1" "insighthub" {
  metadata {
    name = var.namespace
    annotations = {
      lab_expiry = var.lab_expiry
    }
    labels = {
      project     = "insighthub"
      environment = var.environment
      owner       = var.owner
      cost_center = var.cost_center
      managed_by  = "terraform"
    }
  }
}
