output "namespace" { value = kubernetes_namespace_v1.insighthub.metadata[0].name }
output "database_endpoint" { value = aws_db_instance.postgres.address }
output "database_secret_arn" {
  value     = aws_db_instance.postgres.master_user_secret[0].secret_arn
  sensitive = true
}
output "redis_primary_endpoint" { value = aws_elasticache_replication_group.redis.primary_endpoint_address }
output "application_secret_arn" { value = aws_secretsmanager_secret.application.arn }
output "api_irsa_role_arn" { value = aws_iam_role.api.arn }
output "worker_irsa_role_arn" { value = aws_iam_role.worker.arn }
