package main

test_allows_private_encrypted_tagged_database if {
  test_input := {
    "resource_changes": [{
      "address": "aws_db_instance.postgres",
      "type": "aws_db_instance",
      "change": {"after": {
        "publicly_accessible": false,
        "storage_encrypted": true,
        "tags_all": {
          "project": "insighthub",
          "environment": "dev",
          "owner": "student",
          "cost_center": "lab",
          "managed_by": "terraform"
        }
      }}
    }]
  }

  violations := deny with input as test_input
  count(violations) == 0
}

test_denies_public_unencrypted_database if {
  test_input := {
    "resource_changes": [{
      "address": "aws_db_instance.unsafe",
      "type": "aws_db_instance",
      "change": {"after": {
        "publicly_accessible": true,
        "storage_encrypted": false,
        "tags_all": {
          "project": "insighthub"
        }
      }}
    }]
  }

  violations := deny with input as test_input
  count(violations) >= 3
}

test_denies_wildcard_ecr_repository_creation if {
  test_input := {
    "resource_changes": [{
      "address": "aws_iam_role_policy.github_apply",
      "type": "aws_iam_role_policy",
      "change": {"after": {
        "policy": json.marshal({"Statement": [{
          "Sid": "CreateInsightHubECRRepository",
          "Resource": "*"
        }]})
      }}
    }]
  }

  violations := deny with input as test_input
  count(violations) == 1
}

test_denies_wildcard_kms_alias_management if {
  test_input := {
    "resource_changes": [{
      "address": "aws_iam_role_policy.github_apply",
      "type": "aws_iam_role_policy",
      "change": {"after": {
        "policy": json.marshal({"Statement": [{
          "Sid": "ManageInsightHubKMSAlias",
          "Resource": "*"
        }]})
      }}
    }]
  }

  violations := deny with input as test_input
  count(violations) == 1
}

test_allows_redis_at_rest_encryption_boolean_true if {
  test_input := {
    "resource_changes": [{
      "address": "aws_elasticache_replication_group.redis",
      "type": "aws_elasticache_replication_group",
      "change": {"after": {
        "at_rest_encryption_enabled": true,
        "transit_encryption_enabled": true
      }}
    }]
  }

  violations := deny with input as test_input
  count(violations) == 0
}

test_allows_redis_at_rest_encryption_serialized_string_true if {
  test_input := {
    "resource_changes": [{
      "address": "aws_elasticache_replication_group.redis",
      "type": "aws_elasticache_replication_group",
      "change": {"after": {
        "at_rest_encryption_enabled": "true",
        "transit_encryption_enabled": true
      }}
    }]
  }

  violations := deny with input as test_input
  count(violations) == 0
}

test_denies_redis_at_rest_encryption_false_boolean if {
  test_input := {
    "resource_changes": [{
      "address": "aws_elasticache_replication_group.redis",
      "type": "aws_elasticache_replication_group",
      "change": {"after": {
        "at_rest_encryption_enabled": false,
        "transit_encryption_enabled": true
      }}
    }]
  }

  violations := deny with input as test_input
  count(violations) == 1
}

test_denies_redis_at_rest_encryption_serialized_string_false if {
  test_input := {
    "resource_changes": [{
      "address": "aws_elasticache_replication_group.redis",
      "type": "aws_elasticache_replication_group",
      "change": {"after": {
        "at_rest_encryption_enabled": "false",
        "transit_encryption_enabled": true
      }}
    }]
  }

  violations := deny with input as test_input
  count(violations) == 1
}
