locals {
  standard_tags = {
    project     = "insighthub"
    environment = var.environment
    owner       = var.owner
    cost_center = var.cost_center
    managed_by  = "terraform"
    lab_expiry  = var.lab_expiry
  }
  oidc_hostpath = trimprefix(data.terraform_remote_state.core.outputs.oidc_issuer, "https://")
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

resource "aws_security_group" "data" {
  name        = "insighthub-${var.environment}-data"
  description = "Private RDS and Redis access from approved application security groups only."
  vpc_id      = data.terraform_remote_state.core.outputs.vpc_id
}

resource "aws_db_subnet_group" "this" {
  name       = "insighthub-${var.environment}-db"
  subnet_ids = data.terraform_remote_state.core.outputs.private_subnet_ids
}

resource "aws_vpc_security_group_ingress_rule" "postgres_from_app" {
  security_group_id            = aws_security_group.data.id
  referenced_security_group_id = data.terraform_remote_state.core.outputs.app_security_group_id
  from_port                    = 5432
  to_port                      = 5432
  ip_protocol                  = "tcp"
  description                  = "PostgreSQL from InsightHub application workloads"
}

resource "aws_vpc_security_group_ingress_rule" "redis_from_app" {
  security_group_id            = aws_security_group.data.id
  referenced_security_group_id = data.terraform_remote_state.core.outputs.app_security_group_id
  from_port                    = 6379
  to_port                      = 6379
  ip_protocol                  = "tcp"
  description                  = "Redis from InsightHub API and ingestion worker"
}

resource "aws_db_instance" "postgres" {
  identifier                  = "insighthub-${var.environment}"
  engine                      = "postgres"
  engine_version              = var.db_engine_version
  instance_class              = var.db_instance_class
  allocated_storage           = 20
  max_allocated_storage       = 40
  storage_encrypted           = true
  kms_key_id                  = data.terraform_remote_state.core.outputs.platform_kms_key_arn
  publicly_accessible         = false
  db_name                     = var.db_name
  username                    = var.db_username
  manage_master_user_password = true
  db_subnet_group_name        = aws_db_subnet_group.this.name
  vpc_security_group_ids      = [aws_security_group.data.id]
  backup_retention_period     = 0
  deletion_protection         = false
  skip_final_snapshot         = var.lab_recreatable_data
  copy_tags_to_snapshot       = true
}

resource "aws_elasticache_subnet_group" "this" {
  name       = "insighthub-${var.environment}-cache"
  subnet_ids = data.terraform_remote_state.core.outputs.private_subnet_ids
}

resource "aws_elasticache_replication_group" "redis" {
  replication_group_id       = "insighthub-${var.environment}"
  description                = "InsightHub ARQ queue for an approved short-lived lab"
  engine                     = "redis"
  engine_version             = var.redis_engine_version
  node_type                  = var.redis_node_type
  num_cache_clusters         = 1
  port                       = 6379
  subnet_group_name          = aws_elasticache_subnet_group.this.name
  security_group_ids         = [aws_security_group.data.id]
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  kms_key_id                 = data.terraform_remote_state.core.outputs.platform_kms_key_arn
  automatic_failover_enabled = false
}

# Secret metadata only. Values are supplied through an approved secret-delivery process,
# never Terraform variables, Helm values, source, or GitHub logs.
resource "aws_secretsmanager_secret" "application" {
  name                    = "insighthub/${var.environment}/application"
  recovery_window_in_days = 0
  kms_key_id              = data.terraform_remote_state.core.outputs.platform_kms_key_arn
}

resource "kubernetes_namespace_v1" "insighthub" {
  metadata {
    name   = var.namespace
    labels = local.standard_tags
  }
}

resource "aws_iam_role" "api" {
  name = "insighthub-${var.environment}-api"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRoleWithWebIdentity"
      Principal = { Federated = data.terraform_remote_state.core.outputs.oidc_provider_arn }
      Condition = { StringEquals = {
        "${local.oidc_hostpath}:aud" = "sts.amazonaws.com"
        "${local.oidc_hostpath}:sub" = "system:serviceaccount:${var.namespace}:insighthub-api"
      } }
    }]
  })
}

resource "aws_iam_role_policy" "api_secrets" {
  name = "read-application-secret"
  role = aws_iam_role.api.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = [aws_secretsmanager_secret.application.arn, aws_db_instance.postgres.master_user_secret[0].secret_arn]
    }]
  })
}

resource "aws_iam_role" "worker" {
  name = "insighthub-${var.environment}-worker"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRoleWithWebIdentity"
      Principal = { Federated = data.terraform_remote_state.core.outputs.oidc_provider_arn }
      Condition = { StringEquals = {
        "${local.oidc_hostpath}:aud" = "sts.amazonaws.com"
        "${local.oidc_hostpath}:sub" = "system:serviceaccount:${var.namespace}:insighthub-worker"
      } }
    }]
  })
}

resource "aws_iam_role_policy" "worker_secrets" {
  name = "read-application-secret"
  role = aws_iam_role.worker.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = [aws_secretsmanager_secret.application.arn, aws_db_instance.postgres.master_user_secret[0].secret_arn]
    }]
  })
}
