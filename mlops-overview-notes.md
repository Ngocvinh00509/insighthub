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
