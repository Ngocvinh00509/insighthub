provider "aws" {
  region = var.aws_region

  default_tags {
    tags = local.standard_tags
  }
}

data "aws_eks_cluster" "core" {
  name = data.terraform_remote_state.core.outputs.cluster_name
}

data "aws_eks_cluster_auth" "core" {
  name = data.terraform_remote_state.core.outputs.cluster_name
}

provider "kubernetes" {
  host                   = data.aws_eks_cluster.core.endpoint
  cluster_ca_certificate = base64decode(data.aws_eks_cluster.core.certificate_authority[0].data)
  token                  = data.aws_eks_cluster_auth.core.token
}
