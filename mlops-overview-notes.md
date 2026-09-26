# MLOps Architecture Overview cho DevOps Engineer

Tài liệu này mô tả kiến trúc MLOps ở mức vận hành. Mục tiêu là giúp DevOps
Engineer xây dựng đường đi an toàn, quan sát được và có thể đảo ngược cho model;
không thay thế vai trò đánh giá khoa học dữ liệu của ML Engineer.

## Block 1 — Mindset Shift: Application artifact và Model artifact

Một application artifact thường là **Code + Config + Runtime**. Khi cùng image,
cùng cấu hình và cùng runtime, hành vi thường có tính xác định cao: một lỗi có thể
được tái hiện bằng version code, dependency và cấu hình triển khai.

Model artifact rộng hơn: **Code + Data + Hyperparameters + Feature pipeline**.
Model có thể vẫn chạy thành công về mặt hạ tầng nhưng chất lượng dự đoán suy giảm
khi phân phối dữ liệu đầu vào đổi khác. Vì vậy, khả năng tái lập phải bao gồm
dataset/version, feature definition, seed (nếu áp dụng), môi trường train và
model version; chỉ lưu file trọng số là không đủ.

| Khía cạnh | Application artifact | Model artifact |
| --- | --- | --- |
| Thành phần chính | Code, config, image/runtime | Code, data, hyperparameters, feature pipeline, model |
| Tính xác định | Thường cao khi inputs/config cố định | Phụ thuộc data, feature và quá trình train/evaluation |
| Thay đổi cần theo dõi | Code, dependency, config, hạ tầng | Code **và** data/feature/schema/model version |
| Monitoring chính | Availability, latency, error, resource | Các tín hiệu app cộng thêm data quality, drift, prediction quality và bias (khi phù hợp) |

Do đó MLOps cần monitoring hai chiều thay đổi:

- **Code path:** image, dependency, serving config, prompt/feature code, rollout và lỗi runtime.
- **Data path:** freshness, missing values, schema, distribution feature, prediction distribution và nhãn phản hồi khi có.

Một dashboard chỉ xanh về CPU/latency không chứng minh model còn tốt. Ngược lại,
metric chất lượng tốt tại thời điểm validation cũng không thay thế health check,
SLO và quan sát production.

## Block 2 — ML Lifecycle Map và ownership

Luồng chuẩn dưới đây nhấn mạnh nơi model chuyển từ thử nghiệm sang vận hành:

```text
Data Collection
  -> Feature Engineering
  -> Training
  -> Validation
  -> Model Registry
  -> Approval Gate
  -> Shadow Deploy
  -> Canary Rollout
  -> Production + Monitoring
  -> Drift Detection
  -> Retrain Decision
      └────────────────────────────────────────────> Training
```

| Giai đoạn | Primary owner | Vai trò DevOps |
| --- | --- | --- |
| Data Collection | Data Engineer | Cung cấp storage, IAM, retention, encryption, lineage plumbing và observability cho pipeline. |
| Feature Engineering | ML Engineer / Data Engineer | Vận hành pipeline, kiểm soát version artifact và kiểm tra contract/schema. |
| Training | ML Engineer | Cấp hạ tầng compute có quota, image/runner tái lập, secret delivery và cost telemetry. |
| Validation | ML Engineer | Tự động hóa job, lưu evidence/metrics và bảo vệ quyền truy cập evaluation data. |
| Model Registry | ML Engineer / Platform owner | Cung cấp registry, RBAC, audit trail, immutable version/digest và retention. |
| Approval Gate | ML Engineer / Product owner | Triển khai policy-as-code, kiểm chứng evidence bắt buộc và bảo vệ promotion workflow. |
| Shadow Deploy | DevOps / ML Platform | Triển khai traffic shadow không ảnh hưởng người dùng, đo latency/cost/error và bảo vệ dữ liệu. |
| Canary Rollout | DevOps, với ML Engineer phê duyệt chất lượng | Thiết kế progressive delivery, SLO guardrail, rollback tự động/thủ công và quan sát theo version. |
| Production + Monitoring | DevOps | Chịu trách nhiệm chính về reliability, alerting, capacity, logs/metrics/traces an toàn và on-call runbook. |
| Drift Detection | ML Engineer (quality), DevOps (platform signal) | Vận hành telemetry/data checks, cảnh báo, dashboard và đảm bảo tín hiệu đến đúng owner. |
| Retrain Decision | ML Engineer / Product owner | Gửi retrain signal có bằng chứng; vận hành workflow, không tự ý train hoặc tự promotion model. |

## Block 3 — Bốn khái niệm MLOps cốt lõi qua lăng kính DevOps

### 1. Model Registry

Model Registry tương tự **Container Registry**: mỗi model có version, metadata,
provenance và quyền promotion. MLflow là một ví dụ phổ biến về registry/experiment
tracking. Khác với image registry, một entry model cần liên kết thêm training data,
feature schema, evaluation metrics và compatibility contract. DevOps cần đảm bảo
artifact immutable, RBAC/audit và deployment chỉ lấy artifact đã được phê duyệt.

### 2. Approval Gate

Approval Gate giống **metric-based PR review gate** trong CI/CD. Một model chỉ được
promote khi evidence đạt các ngưỡng đã thống nhất: ví dụ quality metric, fairness
check phù hợp, data/schema validation, security scan và inference latency/cost
budget. Gate là policy có thể audit, không phải lời hứa trong ticket. DevOps triển
khai enforcement và trail; ML Engineer chịu trách nhiệm chứng minh chất lượng.

### 3. Drift Detection

Drift Detection có quan hệ với AIOps anomaly detection, nhưng đối tượng là chất
lượng dự đoán:

- **Data drift:** phân phối input/feature thực tế khác distribution đã train, như
  tỷ lệ missing hoặc histogram của một feature thay đổi.
- **Concept drift:** quan hệ giữa input và target thay đổi; model có thể nhận input
  hợp lệ nhưng prediction không còn chính xác khi có nhãn phản hồi.

DevOps vận hành collection, dashboard và alert delivery. ML Engineer đặt ngưỡng,
đánh giá ý nghĩa thống kê và quyết định có cần retrain. Không nên coi một alert
drift là lệnh tự động thay model trong production.

### 4. Rollback Model

Rollback model giống rollback image/version, nhưng phải kiểm tra thêm compatibility
schema **input/output**. Trước khi quay về version cũ, xác nhận serving API vẫn
chấp nhận feature schema hiện tại, output contract không làm hỏng downstream,
feature pipeline tương thích và registry artifact còn truy cập được. Canary,
version labels, SLO/error guardrail và runbook làm cho rollback trở thành thao tác
nhanh nhưng có kiểm soát.

## Block 4 — Ownership Boundary

DevOps **không trực tiếp train model**, không tự chọn training data, không thay ML
metric threshold và không tự phê duyệt chất lượng dự đoán. Các quyết định này cần
ML Engineer và, khi cần, Product/Data owner chịu trách nhiệm.

DevOps chịu trách nhiệm chính từ **Deploy -> Monitor -> Retrain Signal**:

- Deploy model đã được phê duyệt bằng artifact version/digest xác định; thực hiện
  shadow/canary, rollback và kiểm soát quyền triển khai.
- Monitor reliability và vận hành: availability, latency, errors, saturation,
  resource/cost, audit logs, data-pipeline health và delivery của alert.
- Retrain Signal: chuyển evidence về drift, chất lượng, SLO hay dữ liệu tới owner
  phù hợp; vận hành workflow retrain có guardrail nhưng không tự promotion model.

Ranh giới này giúp tránh hai lỗi phổ biến: hạ tầng tự động thay đổi model mà không
có quyết định khoa học dữ liệu, hoặc model được đánh giá tốt trong lab nhưng thiếu
reliability, security và khả năng rollback khi vào production.
