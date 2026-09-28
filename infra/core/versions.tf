terraform {
  required_version = ">= 1.10.0, < 1.16.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "= 5.100.0"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "= 4.4.1"
    }
  }

  backend "s3" {
    encrypt      = true
    use_lockfile = true
  }
}
