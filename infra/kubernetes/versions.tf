terraform {
  required_version = ">= 1.10.0, < 1.16.0"

  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "= 2.38.0"
    }
  }

  backend "s3" {
    encrypt      = true
    use_lockfile = true
  }
}
