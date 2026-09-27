package main

test_allows_private_encrypted_tagged_database if {
  count(deny with input as {
    "resource_changes": [{
      "address": "aws_db_instance.postgres",
      "type": "aws_db_instance",
      "change": {"after": {
        "publicly_accessible": false,
        "storage_encrypted": true,
        "tags": {"project": "insighthub", "environment": "dev", "owner": "student", "cost_center": "lab", "managed_by": "terraform"}
      }}
    }]
  }) == 0
}

test_denies_public_unencrypted_database if {
  violations := deny with input as {
    "resource_changes": [{
      "address": "aws_db_instance.unsafe",
      "type": "aws_db_instance",
      "change": {"after": {
        "publicly_accessible": true,
        "storage_encrypted": false,
        "tags": {"project": "insighthub"}
      }}
    }]
  }
  count(violations) >= 3
}
