# Day 4 — AI Prompt Log

Ngày ghi nhận: 2026-09-24. Host: Codex API. Model/version không được cung cấp
cho nhật ký này. Nhật ký không chứa khóa API, URL webhook, token, hay giá trị
Secret.

## Prompt 1 — ServiceMonitor và exporters

### Mục tiêu

Tạo manifest ServiceMonitor để Prometheus thu thập `/metrics` cho năm thành phần
InsightHub: web, api, ingestion-worker, Redis exporter và PostgreSQL exporter.

### Ràng buộc

- Dùng `monitoring.coreos.com/v1`, `kind: ServiceMonitor`, namespace
  `insighthub-dev` và label release của kube-prometheus-stack.
- Selector phải khớp label chung của đúng năm metric Service; endpoint dùng port
  name `http-metrics`, path `/metrics` và interval 30 giây.
- Không thay đổi schema dữ liệu, không nhúng credential hoặc địa chỉ private vào
  manifest.
- Sau khi triển khai, kiểm tra ServiceMonitor và Prometheus Targets; báo rõ target
  nào chưa `UP` cùng nguyên nhân có bằng chứng.

### Tiêu chí thành công

Manifest áp dụng được; ServiceMonitor active; năm target web, api,
ingestion-worker, Redis và PostgreSQL hiển thị `UP` trong Prometheus Targets.

### Ngữ cảnh tham chiếu

Đọc `observability/servicemonitor.yaml`, metric endpoint của API, các Service
Kubernetes InsightHub và tiêu chí MH1/MH2 trong tài liệu Day 4.

### Why it worked

Prompt giới hạn rõ resource, namespace, selector, tên port và điều kiện xác minh
end-to-end. Yêu cầu phân biệt trạng thái `UP` với việc chỉ tạo CRD giúp tránh kết
luận nhầm rằng apply thành công đồng nghĩa Prometheus đã scrape được metrics.

### What I changed

- Giữ selector `app.kubernetes.io/part-of: insighthub` và port `http-metrics`
  khớp manifest đã review.
- Ghi nhận trung thực kết quả: kubeconfig không phân giải được DNS endpoint EKS
  và Prometheus localhost không có listener, nên không tuyên bố 5/5 target `UP`.
- Không thêm exporter, label hoặc fallback giả lập chỉ để làm kết quả xanh.

## Prompt 2 — Prometheus recording rules và alerts

### Mục tiêu

Tạo `PrometheusRule` cho dải anomaly LLM latency và ba cảnh báo: latency spike,
ingestion queue backlog và HTTP 5xx error burst.

### Ràng buộc

- Dùng `monitoring.coreos.com/v1`, label release kube-prometheus-stack và đặt
  rule tại namespace monitoring.
- Record p95 LLM từ histogram; upper band là rolling average một giờ cộng ba lần
  standard deviation.
- Alert latency dùng ngưỡng anomaly trong 2 phút, queue depth lớn hơn 50 trong 3
  phút, và error ratio 5xx lớn hơn 5% trong 1 phút.
- Mỗi alert có severity, service/team labels, summary và description; không chứa
  dữ liệu nhạy cảm hoặc raw request/document content.
- Xác minh với `promtool check rules` khi promtool có sẵn; không báo pass nếu tool
  chưa tồn tại.

### Tiêu chí thành công

`observability/prometheus-rules.yaml` hợp lệ, biểu thức PromQL có nhãn namespace
phù hợp và `promtool check rules` trả về thành công trong môi trường có promtool.

### Ngữ cảnh tham chiếu

Đọc `api/app/core/metrics.py`, `observability/grafana-dashboard.json`,
`observability/servicemonitor.yaml` và yêu cầu MH4/MH5 Day 4.

### Why it worked

Prompt ràng buộc metric, duration và severity theo từng failure mode, nên rule có
thể đối chiếu trực tiếp với dashboard và incident runbook. Điều kiện không giả
định `promtool` có sẵn cũng bảo toàn tính trung thực của evidence verification.

### What I changed

- Aggregation p95 theo `namespace` để không trộn môi trường trong cùng Prometheus.
- Dùng `clamp_min` ở mẫu số error ratio để tránh phép chia bởi zero.
- Kiểm tra đã chạy cho thấy `promtool` không có trong PATH; do đó chỉ báo manifest
  đã tạo, không ghi nhận gate promtool là pass.

## Prompt 3 — AI RCA analysis theo Evidence-First

### Mục tiêu

Sinh ba báo cáo RCA JSON cho LLM latency spike, queue backlog accumulation và HTTP
5xx error burst, dựa trên metric Prometheus của InsightHub.

### Ràng buộc

- Mỗi báo cáo phải có incident ID/type/timestamp/summary, evidence không rỗng,
  hypotheses với confidence 0.0–1.0 và evidence reference, ruled-out causes, cùng
  recommended actions.
- Evidence gồm metric name, observed value, baseline và timestamp ISO 8601.
- Không suy diễn raw document content, credential, provider body hay thông tin
  nhạy cảm từ log.
- Nếu Prometheus live không truy cập được, đánh dấu evidence là simulated thay vì
  gọi là số liệu production thực tế.

### Tiêu chí thành công

Ba file JSON parse được, đủ field bắt buộc, evidence/timestamp không rỗng và các
metric phù hợp với anomaly/alert InsightHub.

### Ngữ cảnh tham chiếu

Đọc `observability/prometheus-rules.yaml`,
`observability/grafana-dashboard.json`, `api/app/core/metrics.py` và tiêu chí
MH7–MH10 Day 4.

### Why it worked

Prompt buộc hypothesis phải tham chiếu evidence và yêu cầu ruled-out causes, giúp
RCA là chuỗi lập luận có thể review thay vì danh sách phỏng đoán. Điều kiện về
provenance ngăn dữ liệu mô phỏng bị trình bày sai như bằng chứng live.

### What I changed

- Dùng metric names đã có hoặc đã được định nghĩa trong observability contract:
  LLM latency, queue depth, ingestion errors, HTTP request/error ratio và pod CPU.
- Thêm `evidence_source` để phân biệt dữ liệu mô phỏng với telemetry production.
- Kiểm tra cả ba file bằng JSON parser; giữ timestamps ISO 8601 và confidence trong
  khoảng cho phép.
