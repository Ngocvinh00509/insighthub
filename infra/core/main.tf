locals {
  standard_tags = {
    project     = "insighthub"
    environment = var.environment
    owner       = var.owner
    cost_center = var.cost_center
    managed_by  = "terraform"
    lab_expiry  = var.lab_expiry
  }

  public_subnet_cidrs  = [for index in range(2) : cidrsubnet(var.vpc_cidr, 4, index)]
  private_subnet_cidrs = [for index in range(2) : cidrsubnet(var.vpc_cidr, 4, index + 2)]
}

data "aws_caller_identity" "current" {}

resource "aws_vpc" "this" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true
}

resource "aws_default_security_group" "this" {
  vpc_id = aws_vpc.this.id

  ingress = []
  egress  = []
}

resource "aws_cloudwatch_log_group" "vpc_flow_logs" {
  name              = "/aws/vpc/insighthub-${var.environment}-flow-logs"
  retention_in_days = 365
  kms_key_id        = aws_kms_key.platform.arn
}

resource "aws_iam_role" "vpc_flow_logs" {
  name = "insighthub-${var.environment}-vpc-flow-logs"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "vpc-flow-logs.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "vpc_flow_logs" {
  name = "insighthub-${var.environment}-vpc-flow-logs"
  role = aws_iam_role.vpc_flow_logs.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "${aws_cloudwatch_log_group.vpc_flow_logs.arn}:*"
      }
    ]
  })
}

resource "aws_flow_log" "this" {
  vpc_id               = aws_vpc.this.id
  traffic_type         = "ALL"
  log_destination_type = "cloud-watch-logs"
  log_destination      = aws_cloudwatch_log_group.vpc_flow_logs.arn
  iam_role_arn         = aws_iam_role.vpc_flow_logs.arn

  depends_on = [
    aws_iam_role_policy.vpc_flow_logs
  ]
}

resource "aws_kms_key" "platform" {
  description             = "InsightHub ${var.environment} encryption key"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "EnableAccountIAMPermissions"
        Effect = "Allow"

        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }

        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "AllowCloudWatchLogsEncryption"
        Effect = "Allow"

        Principal = {
          Service = "logs.${var.aws_region}.amazonaws.com"
        }

        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:Describe*"
        ]

        Resource = "*"

        Condition = {
          ArnLike = {
            "kms:EncryptionContext:aws:logs:arn" = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/vpc/insighthub-${var.environment}-flow-logs"
          }
        }
      }
    ]
  })
}

resource "aws_kms_alias" "platform" {
  name          = "alias/insighthub-${var.environment}"
  target_key_id = aws_kms_key.platform.key_id
}

resource "aws_security_group" "app" {
  name        = "insighthub-${var.environment}-app"
  description = "EKS workload traffic; data services allow ingress only from this group."
  vpc_id      = aws_vpc.this.id
}

resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id
}

resource "aws_subnet" "public" {
  for_each                = toset(var.availability_zones)
  vpc_id                  = aws_vpc.this.id
  availability_zone       = each.value
  cidr_block              = local.public_subnet_cidrs[index(var.availability_zones, each.value)]
  map_public_ip_on_launch = false
}

resource "aws_subnet" "private" {
  for_each          = toset(var.availability_zones)
  vpc_id            = aws_vpc.this.id
  availability_zone = each.value
  cidr_block        = local.private_subnet_cidrs[index(var.availability_zones, each.value)]
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.this.id
  }
}

resource "aws_route_table_association" "public" {
  for_each       = aws_subnet.public
  subnet_id      = each.value.id
  route_table_id = aws_route_table.public.id
}

# One NAT gateway is a deliberate lab cost trade-off, not a production HA topology.
resource "aws_eip" "nat" {
  domain = "vpc"
}

resource "aws_nat_gateway" "this" {
  allocation_id = aws_eip.nat.id
  subnet_id     = values(aws_subnet.public)[0].id
  depends_on    = [aws_internet_gateway.this]
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.this.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.this.id
  }
}

resource "aws_route_table_association" "private" {
  for_each       = aws_subnet.private
  subnet_id      = each.value.id
  route_table_id = aws_route_table.private.id
}

resource "aws_iam_role" "eks_cluster" {
  name = "${var.cluster_name}-cluster"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "eks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "eks_cluster" {
  role       = aws_iam_role.eks_cluster.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
}

resource "aws_iam_role" "eks_node" {
  name = "${var.cluster_name}-node"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "eks_node" {
  for_each = toset([
    "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy",
    "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy",
    "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPullOnly",
  ])
  role       = aws_iam_role.eks_node.name
  policy_arn = each.value
}

resource "aws_eks_cluster" "this" {
  name     = var.cluster_name
  role_arn = aws_iam_role.eks_cluster.arn
  version  = var.kubernetes_version

  access_config {
    authentication_mode                         = "API_AND_CONFIG_MAP"
    bootstrap_cluster_creator_admin_permissions = false
  }

  vpc_config {
    subnet_ids              = values(aws_subnet.private)[*].id
    security_group_ids      = [aws_security_group.app.id]
    endpoint_private_access = true
    endpoint_public_access  = false
  }

  enabled_cluster_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]

  encryption_config {
    provider {
      key_arn = aws_kms_key.platform.arn
    }
    resources = ["secrets"]
  }

  depends_on = [aws_iam_role_policy_attachment.eks_cluster]
}

resource "aws_eks_node_group" "lab" {
  cluster_name    = aws_eks_cluster.this.name
  node_group_name = "lab"
  node_role_arn   = aws_iam_role.eks_node.arn
  subnet_ids      = values(aws_subnet.private)[*].id
  instance_types  = var.node_instance_types

  scaling_config {
    desired_size = 2
    max_size     = 2
    min_size     = 2
  }

  depends_on = [aws_iam_role_policy_attachment.eks_node]
}

# The protected GitHub apply role is the only non-node principal granted
# Kubernetes administration. Platform Terraform and Helm run only on the
# private VPC runner, so the API endpoint remains private.
resource "aws_eks_access_entry" "github_apply" {
  cluster_name  = aws_eks_cluster.this.name
  principal_arn = aws_iam_role.github_apply.arn
  type          = "STANDARD"
}

resource "aws_eks_access_policy_association" "github_apply_cluster_admin" {
  cluster_name  = aws_eks_cluster.this.name
  principal_arn = aws_iam_role.github_apply.arn
  policy_arn    = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy"

  access_scope {
    type = "cluster"
  }

  depends_on = [aws_eks_access_entry.github_apply]
}

# The protected plan job needs only Kubernetes discovery access so the
# Terraform Kubernetes provider can read the namespace during a Platform plan.
resource "aws_eks_access_entry" "github_plan" {
  cluster_name  = aws_eks_cluster.this.name
  principal_arn = aws_iam_role.github_plan.arn
  type          = "STANDARD"
}

resource "aws_eks_access_policy_association" "github_plan_namespace_view" {
  cluster_name  = aws_eks_cluster.this.name
  principal_arn = aws_iam_role.github_plan.arn
  policy_arn    = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSViewPolicy"

  access_scope {
    type       = "namespace"
    namespaces = ["insighthub-${var.environment}"]
  }

  depends_on = [aws_eks_access_entry.github_plan]
}

data "tls_certificate" "eks_oidc" {
  url = aws_eks_cluster.this.identity[0].oidc[0].issuer
}

resource "aws_iam_openid_connect_provider" "eks" {
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.eks_oidc.certificates[0].sha1_fingerprint]
  url             = aws_eks_cluster.this.identity[0].oidc[0].issuer
}

# GitHub Actions exchanges an ephemeral OIDC token. These roles deliberately
# start with no permissions: attach reviewed, least-privilege policies only in
# the CI implementation change that consumes them.
resource "aws_iam_openid_connect_provider" "github_actions" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["ab9d0263244dd0326eb67015705a667e79cfe998"]
}

resource "aws_iam_role" "github_plan" {
  name = "insighthub-${var.environment}-github-plan"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRoleWithWebIdentity"
      Principal = { Federated = aws_iam_openid_connect_provider.github_actions.arn }
      Condition = { StringEquals = {
        "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
        "token.actions.githubusercontent.com:sub" = var.github_plan_subject
      } }
    }]
  })
}

resource "aws_iam_role" "github_apply" {
  name = "insighthub-${var.environment}-github-apply"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRoleWithWebIdentity"
      Principal = { Federated = aws_iam_openid_connect_provider.github_actions.arn }
      Condition = { StringEquals = {
        "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
        "token.actions.githubusercontent.com:sub" = var.github_apply_subject
      } }
    }]
  })
}

resource "aws_ecr_repository" "app" {
  name                 = "insighthub-${var.environment}"
  image_tag_mutability = "IMMUTABLE"
  encryption_configuration {
    encryption_type = "KMS"
    kms_key         = aws_kms_key.platform.arn
  }

  image_scanning_configuration {
    scan_on_push = true
  }
}
