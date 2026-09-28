output "cluster_name" { value = aws_eks_cluster.this.name }
output "cluster_endpoint" { value = aws_eks_cluster.this.endpoint }
output "cluster_ca_data" {
  value     = aws_eks_cluster.this.certificate_authority[0].data
  sensitive = true
}
output "oidc_provider_arn" { value = aws_iam_openid_connect_provider.eks.arn }
output "oidc_issuer" { value = aws_iam_openid_connect_provider.eks.url }
output "private_subnet_ids" { value = values(aws_subnet.private)[*].id }
output "vpc_id" { value = aws_vpc.this.id }
output "app_security_group_id" { value = aws_security_group.app.id }
output "platform_kms_key_arn" { value = aws_kms_key.platform.arn }
output "github_plan_role_arn" { value = aws_iam_role.github_plan.arn }
output "github_apply_role_arn" { value = aws_iam_role.github_apply.arn }
output "ecr_repository_url" { value = aws_ecr_repository.app.repository_url }
