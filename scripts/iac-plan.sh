#!/usr/bin/env bash
set -euo pipefail

EVIDENCE_DIR="evidence/iac"
PLAN_FILE="../../${EVIDENCE_DIR}/core.tfplan"
PLAN_JSON="../../${EVIDENCE_DIR}/core.tfplan.json"

mkdir -p "${EVIDENCE_DIR}"

: "${AWS_REGION:?AWS_REGION is required}"
: "${TF_STATE_BUCKET:?TF_STATE_BUCKET is required}"
: "${TF_CORE_STATE_KEY:?TF_CORE_STATE_KEY is required}"

echo "===== TERRAFORM INIT ====="

terraform -chdir=infra/core init \
  -input=false \
  -reconfigure \
  -backend-config="bucket=${TF_STATE_BUCKET}" \
  -backend-config="key=${TF_CORE_STATE_KEY}" \
  -backend-config="region=${AWS_REGION}" \
  -backend-config="encrypt=true" \
  -backend-config="use_lockfile=true"

echo
echo "===== TERRAFORM VALIDATE ====="

terraform -chdir=infra/core validate

echo
echo "===== TERRAFORM PLAN ====="

terraform -chdir=infra/core plan \
  -input=false \
  -out="${PLAN_FILE}"

echo
echo "===== PLAN JSON ====="

terraform -chdir=infra/core show \
  -json "${PLAN_FILE}" \
  > "${EVIDENCE_DIR}/core.tfplan.json"

echo
echo "===== PLAN CHECKSUM ====="

sha256sum "${EVIDENCE_DIR}/core.tfplan" \
  > "${EVIDENCE_DIR}/plan.sha256"

echo
echo "===== PLAN SUMMARY ====="

jq \
  '{resource_changes: [.resource_changes[] | {
      address,
      type,
      actions: .change.actions
  }]}' \
  "${EVIDENCE_DIR}/core.tfplan.json" \
  > "${EVIDENCE_DIR}/summary.json"

echo
echo "Terraform plan evidence generated successfully."
