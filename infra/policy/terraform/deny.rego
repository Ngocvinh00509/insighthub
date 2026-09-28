package main

required_tags := {"project", "environment", "owner", "cost_center", "managed_by"}

redis_at_rest_encryption_enabled(value) if {
  value == true
}

redis_at_rest_encryption_enabled(value) if {
  value == "true"
}

deny contains msg if {
  resource := input.resource_changes[_]
  resource.type == "aws_db_instance"
  resource.change.after.publicly_accessible == true
  msg := sprintf("%s must not be publicly accessible", [resource.address])
}

deny contains msg if {
  resource := input.resource_changes[_]
  resource.type == "aws_db_instance"
  resource.change.after.storage_encrypted != true
  msg := sprintf("%s must enable storage encryption", [resource.address])
}

deny contains msg if {
  resource := input.resource_changes[_]
  resource.type == "aws_elasticache_replication_group"
  resource.change.after.transit_encryption_enabled != true
  msg := sprintf("%s must enable transit encryption", [resource.address])
}

deny contains msg if {
  resource := input.resource_changes[_]
  resource.type == "aws_elasticache_replication_group"
  not redis_at_rest_encryption_enabled(resource.change.after.at_rest_encryption_enabled)
  msg := sprintf("%s must enable at-rest encryption", [resource.address])
}

deny contains msg if {
  resource := input.resource_changes[_]
  resource.type == "aws_iam_role"
  contains(json.marshal(resource.change.after.assume_role_policy), "\"Principal\":\"*\"")
  msg := sprintf("%s must not trust a wildcard principal", [resource.address])
}

deny contains msg if {
  resource := input.resource_changes[_]
  after := resource.change.after
  after != null

  tags_all := object.get(after, "tags_all", null)
  tags_all != null

  missing := required_tags - {key | tags_all[key]}
  count(missing) > 0

  msg := sprintf("%s is missing required tags: %v", [resource.address, missing])
}

# These two write actions support resource-level permissions. Keep their
# resource scopes concrete even though other create operations can require "*".
deny contains msg if {
  resource := input.resource_changes[_]
  resource.type == "aws_iam_role_policy"
  resource.address == "aws_iam_role_policy.github_apply"
  policy := json.unmarshal(resource.change.after.policy)
  statement := policy.Statement[_]
  statement.Sid == "CreateInsightHubECRRepository"
  statement.Resource == "*"
  msg := sprintf("%s must scope ecr:CreateRepository to the InsightHub repository ARN", [resource.address])
}

deny contains msg if {
  resource := input.resource_changes[_]
  resource.type == "aws_iam_role_policy"
  resource.address == "aws_iam_role_policy.github_apply"
  policy := json.unmarshal(resource.change.after.policy)
  statement := policy.Statement[_]
  statement.Sid == "ManageInsightHubKMSAlias"
  statement.Resource == "*"
  msg := sprintf("%s must scope KMS alias management to the InsightHub alias and key", [resource.address])
}
