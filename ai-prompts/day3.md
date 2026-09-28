# Day 3 prompt log

Host: ChatGPT-Codex (GPT-5) · Date: 2026-09-28

## Prompt 1 — audit

> Audit Day 3 Terraform, Helm, CI and application configuration against the
> specification. Do not apply, destroy, push, commit or change branch. Report
> only source-backed findings and run relevant local validation after each edit.

Decision: accepted. It found that the required EKS namespace was not managed by
Terraform, Helm dev/staging used direct endpoint placeholders, TLS was not
rendered, and CI apply was a placeholder.

## Prompt 2 — private EKS namespace and secrets

> Make the smallest source changes to manage `insighthub-dev` with Terraform
> while retaining a private EKS endpoint. Helm must source runtime credentials
> from AWS Secrets Manager through the CSI driver, not values files.

Decision: accepted. Added the pinned Kubernetes provider with AWS exec token,
`kubernetes_namespace_v1`, and CSI-backed Secret sync with `envFrom`; rejected
public EKS access and putting endpoint or credential values into Helm.

## Prompt 3 — reviewed apply

> Replace a GitHub Actions apply placeholder with an implementation that uses a
> protected environment, OIDC apply role and exactly the checksum-verified plan
> artifact. Do not invoke it.

Decision: accepted. The `lab-aws` environment name matches the exact configured
OIDC subject; apply reconfigures the backend, verifies checksum and applies only
the saved Core plan. The task did not authorize executing this workflow.

## Actual validation

- `terraform -chdir=infra/core fmt -check`, `validate`, and recursive TFLint: pass.
- Core Checkov 3.3.18: 88 passed, 0 failed.
- `terraform -chdir=infra/platform fmt -check`, `validate`, and recursive TFLint: pass after downloading the pinned Kubernetes provider.
- Helm lint and local/dev render: pass.
- Conftest 0.70.1 policy unit tests: 2/2 pass; positive fixture: 6/6 pass; negative fixture denied expected three violations.
- New AWS plan, live deployment, Infracost, and GitHub workflow are not recorded as pass: see final Day 3 audit report for blockers.
