package main

required_tags := {"project", "environment", "owner", "cost_center", "managed_by"}

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
  resource.change.after.at_rest_encryption_enabled != true
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
  tags := object.get(resource.change.after, "tags", {})
  missing := required_tags - {key | tags[key]}
  count(missing) > 0
  msg := sprintf("%s is missing required tags: %v", [resource.address, missing])
}
