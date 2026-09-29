locals {
  terraform_state_bucket_arn = "arn:aws:s3:::${var.terraform_state_bucket}"
  terraform_state_object_arns = [
    "${local.terraform_state_bucket_arn}/${var.core_state_key}",
    "${local.terraform_state_bucket_arn}/${var.platform_state_key}",
  ]
  terraform_lock_object_arns = [
    "${local.terraform_state_bucket_arn}/${var.core_state_key}.tflock",
    "${local.terraform_state_bucket_arn}/${var.platform_state_key}.tflock",
  ]
}

# GitHub OIDC trust is defined in main.tf using exact, validated sub claims.
# This policy is intentionally limited to remote-state access. AWS discovery
# permissions and mutation permissions require a separate least-privilege
# review before they are attached.
data "aws_iam_policy_document" "github_plan" {
  statement {
    sid       = "ListInsightHubStateBucket"
    effect    = "Allow"
    actions   = ["s3:GetBucketLocation", "s3:ListBucket"]
    resources = [local.terraform_state_bucket_arn]

    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values = [
        var.core_state_key,
        "${var.core_state_key}.tflock",
        var.platform_state_key,
        "${var.platform_state_key}.tflock",
      ]
    }
  }

  statement {
    sid       = "ReadTerraformState"
    effect    = "Allow"
    actions   = ["s3:GetObject"]
    resources = concat(local.terraform_state_object_arns, local.terraform_lock_object_arns)
  }

}

resource "aws_iam_role_policy" "github_plan" {
  name   = "insighthub-${var.environment}-terraform-plan"
  role   = aws_iam_role.github_plan.id
  policy = data.aws_iam_policy_document.github_plan.json
}

# The protected apply role has exact OIDC trust but intentionally receives no
# mutation policy until a saved-plan action/resource matrix is reviewed.
