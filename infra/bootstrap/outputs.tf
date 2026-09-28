output "state_bucket_name" {
  value       = aws_s3_bucket.terraform_state.bucket
  description = "Supply this value through partial backend configuration; do not hardcode it in committed backend files."
}
