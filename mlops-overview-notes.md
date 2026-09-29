# MLOps Overview for InsightHub — Day 4

MLOps là cách vận hành vòng đời **model artifact** an toàn và có thể audit.
InsightHub hiện là ứng dụng RAG dùng provider/model bên ngoài, không có pipeline
train model riêng. Vì vậy đây là kiến thức để DevOps phối hợp với ML team khi
InsightHub sau này dùng embedding model, reranker hoặc model nội bộ; tài liệu này
không yêu cầu đổi kiến trúc Day 4.

Application artifact thường là `code + config + image/runtime`. Model artifact
rộng hơn: `code + data + feature schema + hyperparameters + evaluation + model
version`. App có thể healthy nhưng model vẫn cho kết quả kém vì data/khái niệm đã
thay đổi.

## Block 1 — Model Registry

**Concept.** Model Registry là nơi lưu model version bất biến cùng provenance:
training dataset/version, feature schema, evaluation result, owner và digest.
Nó tương tự container registry, nhưng một image digest không đủ để tái tạo chất
lượng model.

**InsightHub example.** Nếu thay embedding model hiện tại bằng embedding model
nội bộ, registry record phải nói rõ model version, dimension, normalization,
preprocessing và embedding identity. Điều này khớp với invariant InsightHub:
đổi identity không được âm thầm trộn vector space cũ/mới; cần reindex hoặc DB lab
riêng.

**Operational risk.** Deploy nhầm model chưa approved, model dimension khác
`VECTOR(1024)`, hoặc không biết data/model nào tạo embeddings. Hậu quả là retrieval
có thể vẫn trả HTTP 200 nhưng chất lượng/citation giảm hoặc index conflict.

**Metric/monitoring.** Theo dõi deployment revision, model/version/digest đã
approved, embedding identity mismatch, reindex progress/failure, query latency,
retrieval no-context rate và provider/model usage. Không đưa document ID, raw
prompt hay nội dung tài liệu vào metric label.

**DevOps responsibility.** Cung cấp registry immutable, RBAC, audit trail,
retention và chỉ cho deployment lấy version đã approved. DevOps không tự chọn
model tốt nhất hoặc sửa quality score.

## Block 2 — Approval Gate

**Concept.** Approval Gate là policy enforcement trước khi model được promote.
Nó kiểm chứng evidence chứ không chỉ là checkbox trong ticket: evaluation metric,
schema compatibility, security scan, latency/cost budget và người phê duyệt.

**InsightHub example.** Trước khi promote embedding/reranker nội bộ, gate có thể
yêu cầu: dimension 1024, identity/version rõ ràng, benchmark retrieval trên corpus
được phép dùng, không regression vượt ngưỡng, và kế hoạch reindex/rollback. Một
thay đổi `EMBEDDING_MODEL` đơn lẻ không đủ điều kiện deploy.

**Operational risk.** Bypass gate gây model chưa đánh giá đi production; canary
có thể lỗi compatibility hoặc tiêu tốn chi phí. Approval chỉ bằng lời nói không
tạo audit trail và khó rollback đúng version.

**Metric/monitoring.** Theo dõi gate pass/fail, version đang ở stage
`candidate/approved/production`, deployment result, latency p95, error rate, token
usage/cost nếu provider báo dữ liệu thật. Dashboard Day 4 đo reliability; nó không
tự chứng minh model quality.

**DevOps responsibility.** Tự động hóa gate trong CI/CD, lưu artifact/evidence,
enforce RBAC và chặn promotion trái policy. ML Engineer/Product owner đặt ngưỡng
quality và phê duyệt chất lượng.

## Block 3 — Drift Detection

**Concept.** Drift là production thay đổi so với baseline model.

- *Data drift:* phân phối input/feature thay đổi, ví dụ tài liệu mới có ngôn ngữ,
  độ dài hoặc format khác corpus trước đó.
- *Concept drift:* quan hệ input → target thay đổi; input vẫn hợp lệ nhưng output
  không còn đúng. Cần ground truth/feedback để xác minh.

**InsightHub example.** Nếu người dùng bắt đầu upload PDF scan nhiều, retrieval
quality có thể giảm dù API, Redis và PostgreSQL đều xanh. Nếu có model nội bộ,
theo dõi phân phối document type/length, extraction failure rate, embedding norm
validation, retrieval feedback và citation usefulness; không log raw document.

**Operational risk.** Nhầm latency anomaly với drift, hoặc tự retrain/promotion
khi chỉ có một alert. Baseline quá ngắn tạo false positive; thiếu feedback khiến
không thể kết luận concept drift.

**Metric/monitoring.** Dùng dashboard Day 4 cho RED/USE: API p95, error ratio,
queue depth, worker failures, pod resource. Với model riêng, thêm data freshness,
missing/schema violation, feature distribution, prediction distribution và quality
feedback. Alert drift phải ghi baseline/window; lab cần baseline >=1h, production
>=7 ngày theo spec.

**DevOps responsibility.** Vận hành collection, storage, dashboard, alert routing
và data-pipeline reliability. ML Engineer đánh giá statistical significance,
quality impact và quyết định retrain. DevOps **không tự retrain**.

## Block 4 — Model Rollback

**Concept.** Rollback đưa serving về model version đã approved trước đó. Khác image
rollback, phải kiểm tra input/output schema, feature pipeline và artifact còn
truy cập được.

**InsightHub example.** Nếu embedding rollout làm retrieval regression, rollback
không chỉ đổi env model name: phải đảm bảo query embeddings và stored chunk vectors
cùng identity. Có thể cần giữ serving ở version cũ cho đến khi reindex hoàn tất,
hoặc route canary sang index/version tương thích.

**Operational risk.** Rollback model cũ với index mới gây vector-space mismatch;
rollback API mà không rollback feature/preprocessing contract có thể làm downstream
lỗi. Rollback không test trước làm sự cố dài hơn.

**Metric/monitoring.** Theo dõi rollout revision, available replicas, API errors,
LLM/embedding latency, retrieval no-context rate, index identity conflict và queue
backlog trước/sau rollback. So sánh cùng workload; không gọi một screenshot xanh là
quality recovery.

**DevOps responsibility.** Chuẩn bị version pinning, canary/shadow rollout,
rollback runbook, SLO guardrail và audit log; thực hiện rollback sau approval theo
quy trình incident. ML Engineer xác nhận model target còn phù hợp về quality và
schema.

## Ownership boundary — nhớ nhanh

| Việc | Primary owner | DevOps làm gì? |
| --- | --- | --- |
| Data/feature definition, train, quality threshold | Data/ML Engineer | Cung cấp platform, quyền truy cập, reproducible runner |
| Registry, promotion policy, deployment | ML Platform/DevOps + approver | Immutable artifact, RBAC, CI/CD, canary, rollback |
| Reliability, alerting, capacity, cost telemetry | DevOps | Own vận hành và on-call runbook |
| Drift interpretation, retrain decision | ML Engineer/Product owner | Gửi evidence/retrain signal, không tự train/promote |

## Quiz / self-check Day 4

Ghi câu trả lời của bạn trước khi xem đáp án. Mục tiêu spec là **>=4/5**; mục tiêu
nộp Day 4 là **5/5** cùng evidence quiz.

1. Application artifact và model artifact của InsightHub khác nhau tối thiểu bốn
   thành phần nào?
2. Vì sao đổi embedding model/normalization trong InsightHub không thể chỉ đổi
   environment variable rồi deploy?
3. Data drift và concept drift khác nhau thế nào? Signal nào cần để khẳng định
   concept drift?
4. Khi drift alert fire cho model nội bộ, DevOps cần làm gì và không được làm gì?
5. Trước khi rollback embedding model, ba compatibility/evidence nào phải được
   xác minh?

### Đáp án / rubric

<<<<<<< Updated upstream
1. App: code/config/runtime; model: thêm data version, feature schema/pipeline,
   hyperparameters, evaluation/provenance và model version. Nêu được bốn ý hợp lệ.
2. Vì embedding identity/vector space có thể khác; query và stored chunks phải
   tương thích, nên cần reindex hoặc index/version tách biệt, gate và rollback plan.
3. Data drift là phân phối input/feature đổi; concept drift là quan hệ input-target
   đổi. Concept drift cần ground truth/feedback/quality evidence, không chỉ latency.
4. DevOps kiểm tra pipeline/telemetry, gửi evidence tới ML owner, vận hành alert và
   workflow; không tự retrain, thay threshold quality hoặc tự promote model.
5. Xác minh approved model version/digest, input-output/feature schema compatibility,
   embedding/index identity và evidence SLO/quality/canary trước-sau rollback.
=======
Luồng chuẩn dưới đây nhấn mạnh nơi model chuyển từ thử nghiệm sang vận hành:

```text
Data
  -> Train
  -> Validate
  -> Registry
  -> Deploy (sau Approval Gate; có thể shadow/canary)
  -> Monitor
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

## Block 4 — Tình huống quyết định release và self-check

Ví dụ: một candidate model tăng điểm tổng trên evaluation set nhưng làm giảm chất
lượng tiếng Việt, hoặc vượt inference-latency gate. Candidate đó **chưa được
promote**. ML Engineer/Data owner đánh giá chất lượng, coverage data và nguyên
nhân; Product owner xác nhận trade-off với người dùng; DevOps giữ version/digest,
validation evidence, compatibility result và trạng thái gate trong audit trail.
DevOps không tự nới ngưỡng, không tự chọn candidate và không tự chạy retrain hay
promotion.

Self-check:

- **Data drift có chứng minh concept drift hay chất lượng đã giảm không?** Không.
  Nó là tín hiệu phân phối input/feature thay đổi; cần evaluation với nhãn/feedback
  hoặc phân tích ML để kết luận tác động chất lượng.
- **Khi nào báo ML Engineer?** Khi data/schema/freshness check hoặc drift signal
  vượt ngưỡng đã duyệt, prediction-quality feedback giảm, hay model version có
  reliability/latency signal cần đánh giá trade-off. Báo kèm version, khoảng thời
  gian, metric/evidence và compatibility context.
- **Giới hạn ownership DevOps là gì?** DevOps vận hành deployment đã duyệt,
  observability, rollback có kiểm soát và workflow signal. DevOps không tự quyết
  training data, ML quality threshold, retrain, registry promotion hoặc release
  model mới.
>>>>>>> Stashed changes
