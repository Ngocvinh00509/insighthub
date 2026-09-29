locals {
  terraform_state_bucket_arn = "arn:aws:s3:::insighthub-terraform-state-154931139523"

  terraform_core_state_arn = "${local.terraform_state_bucket_arn}/insighthub/core/dev.tfstate"
  terraform_core_lock_arn  = "${local.terraform_core_state_arn}.tflock"

  terraform_platform_state_arn = "${local.terraform_state_bucket_arn}/insighthub/platform/dev.tfstate"
  terraform_platform_lock_arn  = "${local.terraform_platform_state_arn}.tflock"

  account_id = "154931139523"

  ec2_vpc_arn              = "arn:aws:ec2:${var.aws_region}:${local.account_id}:vpc/*"
  ec2_subnet_arn           = "arn:aws:ec2:${var.aws_region}:${local.account_id}:subnet/*"
  ec2_security_group_arn   = "arn:aws:ec2:${var.aws_region}:${local.account_id}:security-group/*"
  ec2_internet_gateway_arn = "arn:aws:ec2:${var.aws_region}:${local.account_id}:internet-gateway/*"
  ec2_route_table_arn      = "arn:aws:ec2:${var.aws_region}:${local.account_id}:route-table/*"
  ec2_nat_gateway_arn      = "arn:aws:ec2:${var.aws_region}:${local.account_id}:natgateway/*"
  ec2_elastic_ip_arn       = "arn:aws:ec2:${var.aws_region}:${local.account_id}:elastic-ip/*"

  rds_db_arn = "arn:aws:rds:${var.aws_region}:${local.account_id}:db:insighthub-${var.environment}"

  rds_subnet_group_arn = "arn:aws:rds:${var.aws_region}:${local.account_id}:subgrp:insighthub-${var.environment}-db"

  elasticache_replication_group_arn = "arn:aws:elasticache:${var.aws_region}:${local.account_id}:replicationgroup:insighthub-${var.environment}"

  elasticache_subnet_group_arn = "arn:aws:elasticache:${var.aws_region}:${local.account_id}:subnetgroup:insighthub-${var.environment}-cache"

  elasticache_cluster_arn = "arn:aws:elasticache:${var.aws_region}:${local.account_id}:cluster:insighthub-${var.environment}-*"

  # The ElastiCache API authorizes CreateReplicationGroup against the selected
  # parameter group as well as the new replication group.
  elasticache_parameter_group_arn = "arn:aws:elasticache:${var.aws_region}:${local.account_id}:parametergroup:*"

  kms_key_arn    = "arn:aws:kms:${var.aws_region}:${local.account_id}:key/*"
  kms_alias_name = "alias/insighthub-${var.environment}"
  kms_alias_arn  = "arn:aws:kms:${var.aws_region}:${local.account_id}:${local.kms_alias_name}"

  application_secret_arn = "arn:aws:secretsmanager:${var.aws_region}:${local.account_id}:secret:insighthub/${var.environment}/application-*"
  secrets_arn            = "arn:aws:secretsmanager:${var.aws_region}:${local.account_id}:secret:insighthub/${var.environment}/*"
  rds_master_secret_arn  = "arn:aws:secretsmanager:${var.aws_region}:${local.account_id}:secret:rds!db-*"

  flow_log_arn       = "arn:aws:ec2:${var.aws_region}:${local.account_id}:vpc-flow-log/*"
  flow_log_group_arn = "arn:aws:logs:${var.aws_region}:${local.account_id}:log-group:/aws/vpc/insighthub-${var.environment}-flow-logs"

  eks_cluster_arn      = "arn:aws:eks:${var.aws_region}:${local.account_id}:cluster/${var.cluster_name}"
  eks_nodegroup_arn    = "arn:aws:eks:${var.aws_region}:${local.account_id}:nodegroup/${var.cluster_name}/*/*"
  eks_access_entry_arn = "arn:aws:eks:${var.aws_region}:${local.account_id}:access-entry/${var.cluster_name}/*"
  eks_access_policy_arns = [
    "arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy",
    "arn:aws:eks::aws:cluster-access-policy/AmazonEKSViewPolicy"
  ]

  ecr_repository_arn = "arn:aws:ecr:${var.aws_region}:${local.account_id}:repository/insighthub-${var.environment}"

  iam_role_arns = [
    "arn:aws:iam::${local.account_id}:role/${var.cluster_name}-cluster",
    "arn:aws:iam::${local.account_id}:role/${var.cluster_name}-node",
    "arn:aws:iam::${local.account_id}:role/insighthub-${var.environment}-github-plan",
    "arn:aws:iam::${local.account_id}:role/insighthub-${var.environment}-github-apply",
    "arn:aws:iam::${local.account_id}:role/insighthub-${var.environment}-vpc-flow-logs"
  ]

  github_oidc_provider_arn = "arn:aws:iam::${local.account_id}:oidc-provider/token.actions.githubusercontent.com"
}

resource "aws_iam_role_policy" "github_plan" {
  name = "insighthub-${var.environment}-terraform-plan"
  role = aws_iam_role.github_plan.id

  policy = jsonencode({
    Version = "2012-10-17"

    Statement = [
      {
        Sid    = "ListTerraformStateBucket"
        Effect = "Allow"
        Action = [
          "s3:GetBucketLocation",
          "s3:ListBucket"
        ]
        Resource = local.terraform_state_bucket_arn

        Condition = {
          StringLike = {
            "s3:prefix" = [
              "insighthub/core/dev.tfstate",
              "insighthub/core/dev.tfstate.tflock",
              "insighthub/platform/dev.tfstate",
              "insighthub/platform/dev.tfstate.tflock"
            ]
          }
        }
      },
      {
        Sid    = "ReadWriteTerraformState"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject"
        ]
        Resource = [
          local.terraform_core_state_arn,
          local.terraform_platform_state_arn
        ]
      },
      {
        Sid    = "ManageTerraformStateLocks"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = [
          local.terraform_core_lock_arn,
          local.terraform_platform_lock_arn
        ]
      },
      {
        Sid    = "ReadEC2"
        Effect = "Allow"
        Action = [
          "ec2:DescribeAddresses",
          "ec2:DescribeAvailabilityZones",
          "ec2:DescribeFlowLogs",
          "ec2:DescribeInternetGateways",
          "ec2:DescribeNatGateways",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DescribeRouteTables",
          "ec2:DescribeSecurityGroupRules",
          "ec2:DescribeSecurityGroups",
          "ec2:DescribeSubnets",
          "ec2:DescribeTags",
          "ec2:DescribeVpcs"
        ]
        Resource = "*"
      },
      {
        Sid      = "DescribeVPCFlowLogGroups"
        Effect   = "Allow"
        Action   = "logs:DescribeLogGroups"
        Resource = "*"
      },
      {
        Sid    = "ReadVPCFlowLogGroupTags"
        Effect = "Allow"
        Action = [
          "logs:ListTagsForResource"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:${local.account_id}:log-group:/aws/vpc/insighthub-${var.environment}-flow-logs"
      },
      {
        Sid    = "ReadEKSList"
        Effect = "Allow"
        Action = [
          "eks:ListClusters"
        ]
        Resource = "*"
      },
      {
        Sid    = "ReadEKSResources"
        Effect = "Allow"
        Action = [
          "eks:DescribeCluster",
          "eks:DescribeNodegroup",
          "eks:ListNodegroups",
          "eks:ListTagsForResource"
        ]
        Resource = [
          local.eks_cluster_arn,
          local.eks_nodegroup_arn
        ]
      },
      {
        Sid    = "ReadECR"
        Effect = "Allow"
        Action = [
          "ecr:DescribeRepositories",
          "ecr:ListTagsForResource"
        ]
        Resource = local.ecr_repository_arn
      },
      {
        Sid    = "ReadIAMRoles"
        Effect = "Allow"
        Action = [
          "iam:GetRole",
          "iam:GetRolePolicy",
          "iam:ListAttachedRolePolicies",
          "iam:ListRolePolicies"
        ]
        Resource = local.iam_role_arns
      },
      {
        Sid    = "ReadGitHubOIDC"
        Effect = "Allow"
        Action = [
          "iam:GetOpenIDConnectProvider",
          "iam:ListOpenIDConnectProviderTags"
        ]
        Resource = local.github_oidc_provider_arn
      },
      {
        Sid    = "ReadKMSList"
        Effect = "Allow"
        Action = [
          "kms:ListAliases"
        ]
        Resource = "*"
      },
      {
        Sid    = "ReadKMSKey"
        Effect = "Allow"
        Action = [
          "kms:DescribeKey",
          "kms:GetKeyPolicy",
          "kms:GetKeyRotationStatus",
          "kms:ListResourceTags"
        ]
        Resource = local.kms_key_arn
      },
      {
        Sid    = "ReadRDSInstances"
        Effect = "Allow"
        Action = [
          "rds:DescribeDBInstances",
          "rds:ListTagsForResource"
        ]
        Resource = local.rds_db_arn
      },
      {
        Sid    = "ReadRDSSubnetGroups"
        Effect = "Allow"
        Action = [
          "rds:DescribeDBSubnetGroups",
          "rds:ListTagsForResource"
        ]
        Resource = local.rds_subnet_group_arn
      },
      {
        Sid    = "ReadElastiCacheReplicationGroup"
        Effect = "Allow"
        Action = [
          "elasticache:DescribeReplicationGroups",
          "elasticache:ListTagsForResource"
        ]
        Resource = local.elasticache_replication_group_arn
      },
      {
        Sid    = "ReadElastiCacheSubnetGroup"
        Effect = "Allow"
        Action = [
          "elasticache:DescribeCacheSubnetGroups",
          "elasticache:ListTagsForResource"
        ]
        Resource = local.elasticache_subnet_group_arn
      },
      {
        Sid    = "ReadSecretsManagerList"
        Effect = "Allow"
        Action = [
          "secretsmanager:ListSecrets"
        ]
        Resource = "*"
      },
      {
        Sid    = "ReadSecretsManagerResources"
        Effect = "Allow"
        Action = [
          "secretsmanager:DescribeSecret",
          "secretsmanager:ListSecretVersionIds"
        ]
        Resource = local.secrets_arn
      }
    ]
  })
}

locals {
  # Keep every existing statement intact, but distribute them across managed
  # policies. IAM inline-role policies are limited to 10,240 bytes and an
  # individual managed policy is limited to 6,144 characters.
  github_apply_policy_statements = [
    {
      Sid    = "ListTerraformStateBucket"
      Effect = "Allow"
      Action = [
        "s3:GetBucketLocation",
        "s3:ListBucket"
      ]
      Resource = local.terraform_state_bucket_arn

      Condition = {
        StringLike = {
          "s3:prefix" = [
            "insighthub/core/dev.tfstate",
            "insighthub/core/dev.tfstate.tflock",
            "insighthub/platform/dev.tfstate",
            "insighthub/platform/dev.tfstate.tflock"
          ]
        }
      }
    },
    {
      Sid    = "ReadWriteTerraformState"
      Effect = "Allow"
      Action = [
        "s3:GetObject",
        "s3:PutObject"
      ]
      Resource = [
        local.terraform_core_state_arn,
        local.terraform_platform_state_arn
      ]
    },
    {
      Sid    = "ManageTerraformStateLocks"
      Effect = "Allow"
      Action = [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject"
      ]
      Resource = [
        local.terraform_core_lock_arn,
        local.terraform_platform_lock_arn
      ]
    },
    {
      Sid    = "ReadEC2"
      Effect = "Allow"
      Action = [
        "ec2:DescribeAddresses",
        "ec2:DescribeAvailabilityZones",
        "ec2:DescribeInternetGateways",
        "ec2:DescribeNatGateways",
        "ec2:DescribeNetworkInterfaces",
        "ec2:DescribeRouteTables",
        "ec2:DescribeSecurityGroupRules",
        "ec2:DescribeSecurityGroups",
        "ec2:DescribeSubnets",
        "ec2:DescribeTags",
        "ec2:DescribeVpcs"
      ]
      Resource = "*"
    },
    {
      Sid    = "CreateInsightHubVpc"
      Effect = "Allow"
      Action = [
        "ec2:CreateVpc"
      ]
      Resource = local.ec2_vpc_arn

      Condition = {
        StringEquals = {
          "aws:RequestTag/project"     = "insighthub"
          "aws:RequestTag/environment" = var.environment
        }
      }
    },
    {
      Sid    = "ManageInsightHubVpc"
      Effect = "Allow"
      Action = [
        "ec2:DeleteVpc",
        "ec2:ModifyVpcAttribute"
      ]
      Resource = local.ec2_vpc_arn

      Condition = {
        StringEquals = {
          "aws:ResourceTag/project"     = "insighthub"
          "aws:ResourceTag/environment" = var.environment
        }
      }
    },
    {
      Sid    = "CreateInsightHubSubnet"
      Effect = "Allow"
      Action = [
        "ec2:CreateSubnet"
      ]
      Resource = [
        local.ec2_subnet_arn,
        local.ec2_vpc_arn
      ]

      Condition = {
        StringEquals = {
          "aws:RequestTag/project"     = "insighthub"
          "aws:RequestTag/environment" = var.environment
        }
      }
    },
    {
      Sid    = "ManageInsightHubSubnet"
      Effect = "Allow"
      Action = [
        "ec2:DeleteSubnet",
        "ec2:ModifySubnetAttribute"
      ]
      Resource = local.ec2_subnet_arn

      Condition = {
        StringEquals = {
          "aws:ResourceTag/project"     = "insighthub"
          "aws:ResourceTag/environment" = var.environment
        }
      }
    },
    {
      Sid    = "CreateInsightHubInternetGateway"
      Effect = "Allow"
      Action = [
        "ec2:CreateInternetGateway"
      ]
      Resource = local.ec2_internet_gateway_arn

      Condition = {
        StringEquals = {
          "aws:RequestTag/project"     = "insighthub"
          "aws:RequestTag/environment" = var.environment
        }
      }
    },
    {
      Sid    = "ManageInsightHubInternetGateway"
      Effect = "Allow"
      Action = [
        "ec2:DeleteInternetGateway"
      ]
      Resource = local.ec2_internet_gateway_arn

      Condition = {
        StringEquals = {
          "aws:ResourceTag/project"     = "insighthub"
          "aws:ResourceTag/environment" = var.environment
        }
      }
    },
    {
      Sid    = "AttachDetachInsightHubInternetGateway"
      Effect = "Allow"
      Action = [
        "ec2:AttachInternetGateway",
        "ec2:DetachInternetGateway"
      ]
      Resource = [
        local.ec2_internet_gateway_arn,
        local.ec2_vpc_arn
      ]

      Condition = {
        StringEquals = {
          "aws:ResourceTag/project"     = "insighthub"
          "aws:ResourceTag/environment" = var.environment
        }
      }
    },
    {
      Sid    = "CreateInsightHubRouteTable"
      Effect = "Allow"
      Action = [
        "ec2:CreateRouteTable"
      ]
      Resource = [
        local.ec2_route_table_arn,
        local.ec2_vpc_arn
      ]

      Condition = {
        StringEquals = {
          "aws:RequestTag/project"     = "insighthub"
          "aws:RequestTag/environment" = var.environment
        }
      }
    },
    {
      Sid    = "ManageInsightHubRouteTable"
      Effect = "Allow"
      Action = [
        "ec2:DeleteRouteTable",
        "ec2:CreateRoute",
        "ec2:ReplaceRoute",
        "ec2:DeleteRoute"
      ]
      Resource = local.ec2_route_table_arn

      Condition = {
        StringEquals = {
          "aws:ResourceTag/project"     = "insighthub"
          "aws:ResourceTag/environment" = var.environment
        }
      }
    },
    {
      Sid    = "AssociateInsightHubRouteTable"
      Effect = "Allow"
      Action = [
        "ec2:AssociateRouteTable"
      ]
      Resource = [
        local.ec2_route_table_arn,
        local.ec2_subnet_arn
      ]

      Condition = {
        StringEquals = {
          "aws:ResourceTag/project"     = "insighthub"
          "aws:ResourceTag/environment" = var.environment
        }
      }
    },
    {
      Sid    = "DisassociateInsightHubRouteTable"
      Effect = "Allow"
      Action = [
        "ec2:DisassociateRouteTable"
      ]
      Resource = local.ec2_route_table_arn

      Condition = {
        StringEquals = {
          "aws:ResourceTag/project"     = "insighthub"
          "aws:ResourceTag/environment" = var.environment
        }
      }
    },
    {
      Sid    = "AllocateInsightHubElasticIp"
      Effect = "Allow"
      Action = [
        "ec2:AllocateAddress"
      ]
      Resource = local.ec2_elastic_ip_arn

      Condition = {
        StringEquals = {
          "aws:RequestTag/project"     = "insighthub"
          "aws:RequestTag/environment" = var.environment
        }
      }
    },
    {
      Sid    = "ReleaseInsightHubElasticIp"
      Effect = "Allow"
      Action = [
        "ec2:ReleaseAddress"
      ]
      Resource = local.ec2_elastic_ip_arn

      Condition = {
        StringEquals = {
          "aws:ResourceTag/project"     = "insighthub"
          "aws:ResourceTag/environment" = var.environment
        }
      }
    },
    {
      Sid    = "CreateInsightHubNatGateway"
      Effect = "Allow"
      Action = [
        "ec2:CreateNatGateway"
      ]
      Resource = [
        local.ec2_nat_gateway_arn,
        local.ec2_subnet_arn,
        local.ec2_elastic_ip_arn,
        local.ec2_vpc_arn
      ]

      Condition = {
        StringEquals = {
          "aws:RequestTag/project"     = "insighthub"
          "aws:RequestTag/environment" = var.environment
        }
      }
    },
    {
      Sid    = "DeleteInsightHubNatGateway"
      Effect = "Allow"
      Action = [
        "ec2:DeleteNatGateway"
      ]
      Resource = local.ec2_nat_gateway_arn

      Condition = {
        StringEquals = {
          "aws:ResourceTag/project"     = "insighthub"
          "aws:ResourceTag/environment" = var.environment
        }
      }
    },
    {
      Sid    = "CreateInsightHubSecurityGroup"
      Effect = "Allow"
      Action = [
        "ec2:CreateSecurityGroup"
      ]
      Resource = [
        local.ec2_security_group_arn,
        local.ec2_vpc_arn
      ]

      Condition = {
        StringEquals = {
          "aws:RequestTag/project"     = "insighthub"
          "aws:RequestTag/environment" = var.environment
        }
      }
    },
    {
      Sid    = "ManageInsightHubSecurityGroup"
      Effect = "Allow"
      Action = [
        "ec2:DeleteSecurityGroup",
        "ec2:AuthorizeSecurityGroupIngress",
        "ec2:RevokeSecurityGroupIngress",
        "ec2:AuthorizeSecurityGroupEgress",
        "ec2:RevokeSecurityGroupEgress"
      ]
      Resource = local.ec2_security_group_arn

      Condition = {
        StringEquals = {
          "aws:ResourceTag/project"     = "insighthub"
          "aws:ResourceTag/environment" = var.environment
        }
      }
    },
    {
      Sid    = "TagInsightHubEC2ResourcesOnCreate"
      Effect = "Allow"
      Action = [
        "ec2:CreateTags"
      ]
      Resource = [
        local.ec2_vpc_arn,
        local.ec2_subnet_arn,
        local.ec2_security_group_arn,
        local.ec2_internet_gateway_arn,
        local.ec2_route_table_arn,
        local.ec2_nat_gateway_arn,
        local.ec2_elastic_ip_arn
      ]

      Condition = {
        StringEquals = {
          "aws:RequestTag/project"     = "insighthub"
          "aws:RequestTag/environment" = var.environment
        }

        StringLike = {
          "ec2:CreateAction" = [
            "CreateVpc",
            "CreateSubnet",
            "CreateSecurityGroup",
            "CreateInternetGateway",
            "CreateRouteTable",
            "CreateNatGateway",
            "AllocateAddress"
          ]
        }
      }
    },
    {
      Sid    = "DeleteInsightHubEC2Tags"
      Effect = "Allow"
      Action = [
        "ec2:DeleteTags"
      ]
      Resource = [
        local.ec2_vpc_arn,
        local.ec2_subnet_arn,
        local.ec2_security_group_arn,
        local.ec2_internet_gateway_arn,
        local.ec2_route_table_arn,
        local.ec2_nat_gateway_arn,
        local.ec2_elastic_ip_arn
      ]

      Condition = {
        StringEquals = {
          "aws:ResourceTag/project"     = "insighthub"
          "aws:ResourceTag/environment" = var.environment
        }
      }
    },
    # CreateCluster has no service resource ARN because the cluster does not
    # exist yet. AWS supports request tags and endpoint-mode conditions.
    {
      Sid      = "CreateInsightHubEKSCluster"
      Effect   = "Allow"
      Action   = "eks:CreateCluster"
      Resource = "*"

      Condition = {
        StringEquals = {
          "aws:RequestTag/project"     = "insighthub"
          "aws:RequestTag/environment" = var.environment
          "eks:endpointPrivateAccess"  = "true"
          "eks:endpointPublicAccess"   = "false"
        }
      }
    },
    {
      Sid    = "ManageInsightHubEKSCluster"
      Effect = "Allow"
      Action = [
        "eks:DeleteCluster",
        "eks:DescribeCluster",
        "eks:UpdateClusterConfig",
        "eks:UpdateClusterVersion",
        "eks:ListNodegroups",
        "eks:ListTagsForResource"
      ]
      Resource = local.eks_cluster_arn

      Condition = {
        StringEquals = {
          "aws:ResourceTag/project"     = "insighthub"
          "aws:ResourceTag/environment" = var.environment
        }
      }
    },
    {
      Sid      = "CreateInsightHubEKSNodegroup"
      Effect   = "Allow"
      Action   = "eks:CreateNodegroup"
      Resource = local.eks_cluster_arn

      Condition = {
        StringEquals = {
          "aws:RequestTag/project"      = "insighthub"
          "aws:RequestTag/environment"  = var.environment
          "aws:ResourceTag/project"     = "insighthub"
          "aws:ResourceTag/environment" = var.environment
        }
      }
    },
    {
      Sid    = "ManageInsightHubEKSNodegroup"
      Effect = "Allow"
      Action = [
        "eks:DeleteNodegroup",
        "eks:DescribeNodegroup",
        "eks:UpdateNodegroupConfig",
        "eks:UpdateNodegroupVersion"
      ]
      Resource = local.eks_nodegroup_arn

      Condition = {
        StringEquals = {
          "aws:ResourceTag/project"     = "insighthub"
          "aws:ResourceTag/environment" = var.environment
        }
      }
    },
    {
      Sid      = "CreateInsightHubEKSAccessEntries"
      Effect   = "Allow"
      Action   = "eks:CreateAccessEntry"
      Resource = local.eks_cluster_arn

      Condition = {
        ArnEquals = {
          "eks:principalArn" = [local.iam_role_arns[2], local.iam_role_arns[3]]
        }
        StringEquals = {
          "aws:RequestTag/project"      = "insighthub"
          "aws:RequestTag/environment"  = var.environment
          "aws:ResourceTag/project"     = "insighthub"
          "aws:ResourceTag/environment" = var.environment
          "eks:accessEntryType"         = "STANDARD"
        }
      }
    },
    {
      Sid    = "ManageInsightHubEKSAccessEntries"
      Effect = "Allow"
      Action = [
        "eks:DeleteAccessEntry",
        "eks:DescribeAccessEntry",
        "eks:ListAssociatedAccessPolicies"
      ]
      Resource = local.eks_access_entry_arn

      Condition = {
        StringEquals = {
          "aws:ResourceTag/project"     = "insighthub"
          "aws:ResourceTag/environment" = var.environment
        }
      }
    },
    {
      Sid      = "AssociateInsightHubEKSAccessPolicies"
      Effect   = "Allow"
      Action   = ["eks:AssociateAccessPolicy", "eks:DisassociateAccessPolicy"]
      Resource = local.eks_access_entry_arn

      Condition = {
        ArnEquals = {
          "eks:policyArn" = local.eks_access_policy_arns
        }
        StringEquals = {
          "aws:ResourceTag/project"     = "insighthub"
          "aws:ResourceTag/environment" = var.environment
        }
      }
    },
    {
      Sid      = "TagInsightHubEKSResources"
      Effect   = "Allow"
      Action   = ["eks:TagResource", "eks:UntagResource"]
      Resource = [local.eks_cluster_arn, local.eks_nodegroup_arn, local.eks_access_entry_arn]

      Condition = {
        StringEquals = {
          "aws:ResourceTag/project"     = "insighthub"
          "aws:ResourceTag/environment" = var.environment
        }
      }
    },
    {
      Sid      = "ListEKSClusters"
      Effect   = "Allow"
      Action   = "eks:ListClusters"
      Resource = "*"
    },
    # ECR supports authorization against the ARN of the repository being
    # created, so keep this permission limited to the sole InsightHub repo.
    {
      Sid      = "CreateInsightHubECRRepository"
      Effect   = "Allow"
      Action   = "ecr:CreateRepository"
      Resource = local.ecr_repository_arn

      Condition = {
        StringEquals = {
          "aws:RequestTag/project"     = "insighthub"
          "aws:RequestTag/environment" = var.environment
        }
      }
    },
    {
      Sid    = "ManageInsightHubECRRepository"
      Effect = "Allow"
      Action = [
        "ecr:DeleteRepository",
        "ecr:DescribeRepositories",
        "ecr:PutImageScanningConfiguration",
        "ecr:PutImageTagMutability",
        "ecr:TagResource",
        "ecr:UntagResource",
        "ecr:ListTagsForResource"
      ]
      Resource = local.ecr_repository_arn

      Condition = {
        StringEquals = {
          "aws:ResourceTag/project"     = "insighthub"
          "aws:ResourceTag/environment" = var.environment
        }
      }
    },
    # KMS CreateKey does not support resource-level permissions. Required
    # creation tags are the narrowest supported authorization control.
    {
      Sid      = "CreateInsightHubKMSKey"
      Effect   = "Allow"
      Action   = "kms:CreateKey"
      Resource = "*"

      Condition = {
        StringEquals = {
          "aws:RequestTag/project"     = "insighthub"
          "aws:RequestTag/environment" = var.environment
        }
      }
    },
    {
      Sid    = "ManageInsightHubKMSKey"
      Effect = "Allow"
      Action = [
        "kms:DescribeKey",
        "kms:EnableKeyRotation",
        "kms:DisableKeyRotation",
        "kms:GetKeyRotationStatus",
        "kms:GetKeyPolicy",
        "kms:PutKeyPolicy",
        "kms:TagResource",
        "kms:UntagResource",
        "kms:ListResourceTags",
        "kms:ScheduleKeyDeletion",
        "kms:CancelKeyDeletion"
      ]
      Resource = local.kms_key_arn

      Condition = {
        StringEquals = {
          "aws:ResourceTag/project"     = "insighthub"
          "aws:ResourceTag/environment" = var.environment
        }
      }
    },
    # Alias operations apply to both the alias and its target key. The key
    # is created earlier in this Terraform graph, so both resources can be
    # concrete rather than granting alias management account-wide.
    {
      Sid      = "ManageInsightHubKMSAlias"
      Effect   = "Allow"
      Action   = ["kms:CreateAlias", "kms:DeleteAlias", "kms:UpdateAlias"]
      Resource = [local.kms_alias_arn, aws_kms_key.platform.arn]
    },
    {
      Sid      = "ListKMSAliases"
      Effect   = "Allow"
      Action   = "kms:ListAliases"
      Resource = "*"
    },
    {
      Sid    = "CreateInsightHubIAMRoles"
      Effect = "Allow"
      Action = [
        "iam:CreateRole"
      ]
      Resource = local.iam_role_arns

      Condition = {
        StringEquals = {
          "aws:RequestTag/project"     = "insighthub"
          "aws:RequestTag/environment" = var.environment
        }
      }
    },
    {
      Sid    = "ManageInsightHubIAMRoles"
      Effect = "Allow"
      Action = [
        "iam:DeleteRole",
        "iam:GetRole",
        "iam:UpdateAssumeRolePolicy",
        "iam:TagRole",
        "iam:UntagRole",
        "iam:AttachRolePolicy",
        "iam:DetachRolePolicy",
        "iam:ListAttachedRolePolicies",
        "iam:PutRolePolicy",
        "iam:DeleteRolePolicy",
        "iam:GetRolePolicy",
        "iam:ListRolePolicies"
      ]
      Resource = local.iam_role_arns

      Condition = {
        StringEquals = {
          "aws:ResourceTag/project"     = "insighthub"
          "aws:ResourceTag/environment" = var.environment
        }
      }
    },
    {
      Sid    = "ManageGitHubOIDCProvider"
      Effect = "Allow"
      Action = [
        "iam:CreateOpenIDConnectProvider",
        "iam:DeleteOpenIDConnectProvider",
        "iam:GetOpenIDConnectProvider",
        "iam:TagOpenIDConnectProvider",
        "iam:UntagOpenIDConnectProvider",
        "iam:ListOpenIDConnectProviderTags"
      ]
      Resource = local.github_oidc_provider_arn
    },
    {
      Sid      = "PassInsightHubEKSRoles"
      Effect   = "Allow"
      Action   = "iam:PassRole"
      Resource = [local.iam_role_arns[0], local.iam_role_arns[1]]

      Condition = {
        StringEquals = { "iam:PassedToService" = "eks.amazonaws.com" }
      }
    },
    {
      Sid      = "PassInsightHubFlowLogRole"
      Effect   = "Allow"
      Action   = "iam:PassRole"
      Resource = local.iam_role_arns[4]

      Condition = {
        StringEquals = { "iam:PassedToService" = "vpc-flow-logs.amazonaws.com" }
      }
    },
    {
      Sid      = "CreateInsightHubVPCFlowLogs"
      Effect   = "Allow"
      Action   = "ec2:CreateFlowLogs"
      Resource = local.ec2_vpc_arn

      Condition = {
        StringEquals = {
          "aws:RequestTag/project"      = "insighthub"
          "aws:RequestTag/environment"  = var.environment
          "aws:ResourceTag/project"     = "insighthub"
          "aws:ResourceTag/environment" = var.environment
        }
      }
    },
    {
      Sid      = "DeleteInsightHubVPCFlowLogs"
      Effect   = "Allow"
      Action   = "ec2:DeleteFlowLogs"
      Resource = local.flow_log_arn

      Condition = {
        StringEquals = {
          "aws:ResourceTag/project"     = "insighthub"
          "aws:ResourceTag/environment" = var.environment
        }
      }
    },
    {
      Sid      = "DescribeVPCFlowLogs"
      Effect   = "Allow"
      Action   = "ec2:DescribeFlowLogs"
      Resource = "*"
    },
    {
      Sid      = "CreateInsightHubVPCFlowLogGroup"
      Effect   = "Allow"
      Action   = "logs:CreateLogGroup"
      Resource = local.flow_log_group_arn

      Condition = {
        StringEquals = {
          "aws:RequestTag/project"     = "insighthub"
          "aws:RequestTag/environment" = var.environment
        }
      }
    },
    {
      Sid    = "ManageInsightHubVPCFlowLogGroup"
      Effect = "Allow"
      Action = [
        "logs:DeleteLogGroup",
        "logs:PutRetentionPolicy",
        "logs:AssociateKmsKey",
        "logs:DisassociateKmsKey",
        "logs:TagResource",
        "logs:ListTagsForResource"
      ]
      Resource = local.flow_log_group_arn

      Condition = {
        StringEquals = {
          "aws:ResourceTag/project"     = "insighthub"
          "aws:ResourceTag/environment" = var.environment
        }
      }
    },
    {
      Sid      = "DescribeVPCFlowLogGroups"
      Effect   = "Allow"
      Action   = "logs:DescribeLogGroups"
      Resource = "*"
    },
    # Terraform's RDS resources below are limited to one DB instance and
    # one DB subnet group. The AWS authorization reference supports their
    # concrete resource ARNs, including request/resource tag conditions.
    {
      Sid    = "ReadInsightHubRDS"
      Effect = "Allow"
      Action = [
        "rds:DescribeDBInstances",
        "rds:DescribeDBSubnetGroups",
        "rds:DescribePendingMaintenanceActions",
        "rds:ListTagsForResource"
      ]
      Resource = [local.rds_db_arn, local.rds_subnet_group_arn]
    },
    {
      Sid    = "ReadRDSCatalog"
      Effect = "Allow"
      Action = [
        "rds:DescribeDBEngineVersions",
        "rds:DescribeOrderableDBInstanceOptions"
      ]
      Resource = "*"
    },
    {
      Sid    = "CreateInsightHubRDS"
      Effect = "Allow"
      Action = [
        "rds:CreateDBInstance",
        "rds:CreateDBSubnetGroup"
      ]
      Resource = [local.rds_db_arn, local.rds_subnet_group_arn]

      Condition = {
        StringEquals = {
          "aws:RequestTag/project"     = "insighthub"
          "aws:RequestTag/environment" = var.environment
        }
      }
    },
    {
      Sid    = "ModifyDeleteInsightHubRDS"
      Effect = "Allow"
      Action = [
        "rds:ModifyDBInstance",
        "rds:DeleteDBInstance",
        "rds:ModifyDBSubnetGroup",
        "rds:DeleteDBSubnetGroup"
      ]
      Resource = [local.rds_db_arn, local.rds_subnet_group_arn]

      Condition = {
        StringEquals = {
          "aws:ResourceTag/project"     = "insighthub"
          "aws:ResourceTag/environment" = var.environment
        }
      }
    },
    {
      Sid    = "TagInsightHubRDS"
      Effect = "Allow"
      Action = [
        "rds:AddTagsToResource",
        "rds:RemoveTagsFromResource"
      ]
      Resource = [local.rds_db_arn, local.rds_subnet_group_arn]
    },
    # ElastiCache exposes resource ARNs for the replication and subnet
    # groups used here; no cache clusters, users, snapshots, or global
    # replication groups are granted to the workflow role.
    {
      Sid    = "ReadInsightHubElastiCache"
      Effect = "Allow"
      Action = [
        "elasticache:DescribeCacheSubnetGroups",
        "elasticache:DescribeReplicationGroups",
        "elasticache:ListTagsForResource"
      ]
      Resource = [local.elasticache_replication_group_arn, local.elasticache_subnet_group_arn]
    },
    {
      Sid    = "CreateInsightHubElastiCache"
      Effect = "Allow"
      Action = [
        "elasticache:CreateCacheSubnetGroup",
        "elasticache:CreateReplicationGroup"
      ]
      Resource = [local.elasticache_replication_group_arn, local.elasticache_subnet_group_arn]

      Condition = {
        StringEquals = {
          "aws:RequestTag/project"     = "insighthub"
          "aws:RequestTag/environment" = var.environment
        }
      }
    },
    {
      Sid    = "ModifyDeleteInsightHubElastiCache"
      Effect = "Allow"
      Action = [
        "elasticache:ModifyCacheSubnetGroup",
        "elasticache:DeleteCacheSubnetGroup",
        "elasticache:ModifyReplicationGroup",
        "elasticache:DeleteReplicationGroup"
      ]
      Resource = [local.elasticache_replication_group_arn, local.elasticache_subnet_group_arn]

      Condition = {
        StringEquals = {
          "aws:ResourceTag/project"     = "insighthub"
          "aws:ResourceTag/environment" = var.environment
        }
      }
    },
    {
      Sid    = "TagInsightHubElastiCache"
      Effect = "Allow"
      Action = [
        "elasticache:AddTagsToResource",
        "elasticache:RemoveTagsFromResource"
      ]
      Resource = [local.elasticache_replication_group_arn, local.elasticache_subnet_group_arn]
    },
    {
      Sid      = "CreateInsightHubApplicationSecret"
      Effect   = "Allow"
      Action   = "secretsmanager:CreateSecret"
      Resource = local.application_secret_arn

      Condition = {
        StringEquals = {
          "aws:RequestTag/project"     = "insighthub"
          "aws:RequestTag/environment" = var.environment
        }
      }
    },
    {
      Sid    = "ManageInsightHubApplicationSecret"
      Effect = "Allow"
      Action = [
        "secretsmanager:DeleteSecret",
        "secretsmanager:DescribeSecret",
        "secretsmanager:TagResource",
        "secretsmanager:UntagResource",
        "secretsmanager:UpdateSecret",
        "secretsmanager:ListSecretVersionIds",
        "secretsmanager:PutSecretValue"
      ]
      Resource = local.application_secret_arn

      Condition = {
        StringEquals = {
          "aws:ResourceTag/project"     = "insighthub"
          "aws:ResourceTag/environment" = var.environment
        }
      }
    },
    {
      Sid      = "ReadRdsManagedMasterSecretForSecretDelivery"
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = local.rds_master_secret_arn
    }
  ]

  github_apply_policy_statement_groups = {
    state      = slice(local.github_apply_policy_statements, 0, 3)
    networking = slice(local.github_apply_policy_statements, 3, 11)
    ec2_routes = slice(local.github_apply_policy_statements, 11, 23)
    eks        = slice(local.github_apply_policy_statements, 23, 32)
    ecr_kms    = slice(local.github_apply_policy_statements, 32, 38)
    iam        = slice(local.github_apply_policy_statements, 38, 43)
    flow_logs  = slice(local.github_apply_policy_statements, 43, 49)
    data       = slice(local.github_apply_policy_statements, 49, 61)
  }
}

resource "aws_iam_policy" "github_apply" {
  for_each = local.github_apply_policy_statement_groups

  name        = "insighthub-${var.environment}-terraform-apply-${each.key}"
  description = "Least-privilege ${each.key} permissions for InsightHub ${var.environment} Terraform"
  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = each.value
  })
}

resource "aws_iam_role_policy_attachment" "github_apply" {
  for_each = aws_iam_policy.github_apply

  role       = aws_iam_role.github_apply.name
  policy_arn = each.value.arn
}

# This customer-managed recovery policy avoids the named operator's constrained
# inline-policy quota while remaining attached only to that operator.
resource "aws_iam_policy" "local_platform_recovery" {
  name        = "insighthub-${var.environment}-platform-recovery"
  description = "Least-privilege permissions for local Platform recovery"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "ReadPlatformState"
        Effect   = "Allow"
        Action   = ["s3:GetBucketLocation", "s3:ListBucket"]
        Resource = local.terraform_state_bucket_arn
        Condition = {
          StringLike = {
            "s3:prefix" = [
              "insighthub/core/dev.tfstate",
              "insighthub/core/dev.tfstate.tflock",
              "insighthub/platform/dev.tfstate",
              "insighthub/platform/dev.tfstate.tflock"
            ]
          }
        }
      },
      {
        Sid    = "ReadWritePlatformStateAndLock"
        Effect = "Allow"
        Action = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
        Resource = [
          local.terraform_core_state_arn,
          local.terraform_core_lock_arn,
          local.terraform_platform_state_arn,
          local.terraform_platform_lock_arn
        ]
      },
      {
        Sid    = "ReadPlatformDependencies"
        Effect = "Allow"
        Action = [
          "ec2:DescribeNetworkInterfaces",
          "ec2:DescribeSecurityGroups",
          "ec2:DescribeSubnets",
          "ec2:DescribeVpcs",
          "rds:DescribeDBEngineVersions",
          "rds:DescribeDBInstances",
          "rds:DescribeDBSubnetGroups",
          "rds:DescribeOrderableDBInstanceOptions"
        ]
        Resource = "*"
      },
      {
        Sid    = "CreateInsightHubRDS"
        Effect = "Allow"
        Action = [
          "rds:AddTagsToResource",
          "rds:CreateDBInstance"
        ]
        Resource = local.rds_db_arn
        Condition = {
          StringEquals = {
            "aws:RequestTag/project"     = "insighthub"
            "aws:RequestTag/environment" = var.environment
          }
        }
      },
      {
        Sid    = "CreateInsightHubElastiCache"
        Effect = "Allow"
        Action = [
          "elasticache:AddTagsToResource",
          "elasticache:CreateCacheSubnetGroup",
          "elasticache:CreateReplicationGroup"
        ]
        Resource = [
          local.elasticache_cluster_arn,
          local.elasticache_replication_group_arn,
          local.elasticache_subnet_group_arn
        ]
        Condition = {
          StringEquals = {
            "aws:RequestTag/project"     = "insighthub"
            "aws:RequestTag/environment" = var.environment
          }
        }
      },
      {
        Sid    = "ReadInsightHubElastiCache"
        Effect = "Allow"
        Action = [
          "elasticache:DescribeCacheSubnetGroups",
          "elasticache:DescribeReplicationGroups",
          "elasticache:ListTagsForResource"
        ]
        Resource = "*"
      },
      {
        # This is separate from the creation/tagging grant above so it cannot
        # be used to tag, modify, or delete any existing parameter group.
        Sid      = "UseElastiCacheParameterGroupForRedisCreate"
        Effect   = "Allow"
        Action   = ["elasticache:CreateReplicationGroup"]
        Resource = local.elasticache_parameter_group_arn
      },
      {
        # Existing subnet groups do not carry request tags for the
        # CreateReplicationGroup authorization check.
        Sid      = "UseElastiCacheSubnetGroupForRedisCreate"
        Effect   = "Allow"
        Action   = ["elasticache:CreateReplicationGroup"]
        Resource = local.elasticache_subnet_group_arn
      },
      {
        Sid    = "CreateInsightHubApplicationSecrets"
        Effect = "Allow"
        # Terraform sends default tags at creation time, which requires
        # TagResource in addition to CreateSecret. Request tags restrict
        # creation to the intended InsightHub environment.
        Action   = ["secretsmanager:CreateSecret", "secretsmanager:TagResource"]
        Resource = local.secrets_arn
        Condition = {
          StringEquals = {
            "aws:RequestTag/project"     = "insighthub"
            "aws:RequestTag/environment" = var.environment
          }
        }
      },
      {
        Sid      = "CreateRDSManagedMasterSecret"
        Effect   = "Allow"
        Action   = ["secretsmanager:CreateSecret", "secretsmanager:TagResource"]
        Resource = local.rds_master_secret_arn
      },
      {
        Sid    = "DescribePlatformKMSForRDSManagedSecret"
        Effect = "Allow"
        Action = [
          "kms:DescribeKey"
        ]
        Resource = aws_kms_key.platform.arn
      },
      {
        Sid      = "CreatePlatformKMSGrantForRDSManagedSecret"
        Effect   = "Allow"
        Action   = "kms:CreateGrant"
        Resource = aws_kms_key.platform.arn
        Condition = {
          Bool = { "kms:GrantIsForAWSResource" = "true" }
          "ForAnyValue:StringEquals" = {
            "kms:ViaService" = [
              "rds.${var.aws_region}.amazonaws.com",
              "secretsmanager.${var.aws_region}.amazonaws.com"
            ]
          }
        }
      },
      {
        Sid      = "UsePlatformKMSForRDSManagedSecret"
        Effect   = "Allow"
        Action   = ["kms:Decrypt", "kms:GenerateDataKey"]
        Resource = aws_kms_key.platform.arn
        Condition = {
          "ForAnyValue:StringEquals" = {
            "kms:ViaService" = [
              "rds.${var.aws_region}.amazonaws.com",
              "secretsmanager.${var.aws_region}.amazonaws.com"
            ]
          }
        }
      }
    ]
  })
}

resource "aws_iam_user_policy_attachment" "local_platform_recovery" {
  user       = "DE000216"
  policy_arn = aws_iam_policy.local_platform_recovery.arn
}
