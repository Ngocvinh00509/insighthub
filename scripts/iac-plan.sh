#!/usr/bin/env bash
set -euo pipefail
mkdir -p evidence/iac
test -n "${AWS_REGION:?}"; test -n "${TF_STATE_BUCKET:?}"
terraform -chdir=infra/core init -input=false -backend-config="bucket=$TF_STATE_BUCKET" -backend-config="key=$TF_CORE_STATE_KEY" -backend-config="region=$AWS_REGION" -backend-config="use_lockfile=true"
terraform -chdir=infra/core plan -out=../../evidence/iac/core.tfplan -input=false
sha256sum evidence/iac/core.tfplan > evidence/iac/plan.sha256
terraform -chdir=infra/core show -json evidence/iac/core.tfplan | jq '{resource_changes:[.resource_changes[]|{address,type,change:{actions:.change.actions}}]}' > evidence/iac/summary.json
