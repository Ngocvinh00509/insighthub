provider "kubernetes" {
  host                   = data.terraform_remote_state.core.outputs.cluster_endpoint
  cluster_ca_certificate = base64decode(data.terraform_remote_state.core.outputs.cluster_ca_data)

  exec {
    api_version = "client.authentication.k8s.io/v1beta1"
    command     = "aws"
    args        = ["eks", "get-token", "--cluster-name", data.terraform_remote_state.core.outputs.cluster_name, "--region", var.aws_region]
  }
}
