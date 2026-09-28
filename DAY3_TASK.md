Bạn là Senior DevOps Engineer. Hãy tiếp tục hoàn thiện Day 3 của repository InsightHub hiện tại.

MỤC TIÊU:
Hoàn thiện Day 3 theo file:
Running-Project-Specification-Student.md

Hãy tự đọc specification và audit toàn bộ implementation hiện tại trước khi sửa.

Repository hiện đang ở branch:
day3-terraform

AWS:
- Account: 154931139523
- Region: ap-southeast-1
- Environment: dev
- Terraform: 1.15.9
- AWS Provider: 5.100.0
- Checkov: 3.3.18
- Conftest: 0.70.1

Kiến trúc Terraform hiện tại:
infra/bootstrap
infra/core
infra/platform
infra/policy

Các phần Day 3 cần kiểm tra:
1. Terraform Core infrastructure
2. EKS
3. VPC/private networking
4. RDS PostgreSQL 16 + pgvector
5. ElastiCache Redis 7
6. KMS encryption
7. Secrets Manager
8. IRSA
9. EKS namespace insighthub-dev
10. GitHub Actions OIDC
11. GitHub Actions pipeline
12. TFLint
13. Checkov
14. Conftest
15. Infracost
16. Helm deployment
17. web/api/ingestion-worker
18. HTTPS
19. smoke test upload -> ingest -> chat

TRẠNG THÁI HIỆN TẠI:
- terraform fmt Core: PASS
- terraform validate Core: PASS
- TFLint Core: PASS
- CKV_AWS_355: PASS
- Core GitHub plan/apply IAM đã được bổ sung quyền cho
  VPC Flow Logs và CloudWatch Logs.
- Chưa được phép terraform apply.

NHIỆM VỤ:

BƯỚC 1 - AUDIT
Đọc:
- Running-Project-Specification-Student.md
- .github/workflows/iac.yml
- infra/**
- deploy/helm/**
- scripts/**
- application config liên quan PostgreSQL/Redis/worker

So sánh implementation với từng Must-Have và Acceptance Criteria
của Day 3.

Không được giả định một requirement đã hoàn thành nếu source code
không chứng minh được.

BƯỚC 2 - CORE FINAL GATE
Tự chạy:
terraform -chdir=infra/core fmt -check
terraform -chdir=infra/core validate
tflint --chdir=infra/core --recursive
python "$CHECKOV_SCRIPT" -d infra/core --framework terraform --compact

Nếu có lỗi:
- phân tích nguyên nhân
- sửa tối thiểu
- giữ least privilege
- chạy lại gate
- không disable Checkov chỉ để làm pipeline xanh

Sau đó tạo Terraform plan Core.

Kiểm tra kỹ:
- không có unexpected destroy
- không có unexpected replacement
- IAM không mở quyền không cần thiết
- EKS private endpoint
- VPC Flow Logs
- KMS
- GitHub OIDC
- tags bắt buộc

Convert plan thành JSON và chạy Conftest với:
infra/policy/terraform

Nếu fail thì sửa và chạy lại.

BƯỚC 3 - PLATFORM
Audit và hoàn thiện infra/platform.

Phải đáp ứng:
- PostgreSQL 16
- encrypted
- non-public
- pgvector
- Redis 7
- private
- encrypted
- Secrets Manager
- IRSA
- mandatory tags

Chạy:
fmt
validate
tflint
checkov
terraform plan
conftest

Không tự động sửa tất cả Checkov findings.
Phân biệt:
- requirement bắt buộc
- security issue thực tế
- finding cần exception/justification

BƯỚC 4 - KUBERNETES / HELM
Kiểm tra requirement Terraform phải tạo namespace:
insighthub-dev

Không dùng Helm --create-namespace để giả vờ đáp ứng requirement
nếu specification yêu cầu Terraform namespace resource.

Kiểm tra:
- EKS authentication/access
- private EKS network access
- IRSA
- ServiceAccount
- web
- api
- ingestion-worker
- RDS endpoint
- Redis endpoint
- Secrets Manager
- ECR images
- HTTPS/Ingress
- health checks

Không được làm public EKS endpoint chỉ để CI chạy.

BƯỚC 5 - CI/CD
Audit .github/workflows/iac.yml.

Pipeline phải thể hiện đầy đủ:
fmt -> lint -> security scan -> policy check -> plan ->
cost estimate -> manual approval -> apply

Kiểm tra:
- GitHub OIDC
- không AWS access key lâu dài
- plan role read-only
- apply role least privilege
- artifact/checksum của saved plan
- Infracost
- environment approval
- action version/pinning
- permissions
- private EKS deployment path

Không để apply job chỉ là placeholder.

BƯỚC 6 - VALIDATION
Sau mỗi thay đổi tự chạy lại các validation liên quan.

Không dừng lại chỉ vì gặp lỗi có thể tự sửa.
Tự phân tích -> sửa -> validate lại.

QUY TẮC AN TOÀN RẤT QUAN TRỌNG:

KHÔNG chạy:
terraform apply
terraform destroy

KHÔNG tạo/xóa resource AWS.

KHÔNG push Git.
KHÔNG commit Git.
KHÔNG đổi branch.

KHÔNG đọc/in secret value.
KHÔNG commit:
terraform.tfvars
backend.hcl
*.tfstate
secret
credential

KHÔNG sửa application business logic ngoài phạm vi cần thiết cho Day 3.

Nếu terraform plan có:
- destroy
- replacement bất ngờ
- thay đổi IAM lớn
- thay đổi networking nguy hiểm

thì DỪNG và báo cáo.

Được phép tự sửa source code/configuration cần thiết để Day 3 đạt
specification.

Ưu tiên sửa nhỏ nhất có thể và giữ kiến trúc hiện tại.

KHI HOÀN THÀNH:
Không apply.

Hãy trả cho tôi báo cáo cuối:

1. Những file đã sửa
2. Những lỗi đã tìm thấy
3. Những lỗi đã sửa
4. Kết quả:
   - fmt
   - validate
   - tflint
   - checkov
   - terraform plan
   - conftest
5. Day 3 Must-Have nào PASS
6. Must-Have nào còn BLOCKED
7. Acceptance Criteria nào PASS/BLOCKED
8. AWS resources dự kiến được tạo
9. Chi phí Infracost nếu có
10. Các blocker còn lại trước terraform apply
11. Lệnh tiếp theo tôi cần chạy

Chỉ được kết luận Day 3 hoàn thành khi có bằng chứng từ source code
