# Observability và MLOps - bắt buộc Day 4

ServiceMonitor/exporters cho đủ 5 thành phần, Grafana 9+ panels, 3 anomaly và 3
incident/RCA, Slack alert, MLOps overview notes 4 blocks/quiz. Queue/worker Day 1
và deployment Day 3 phải có thật. [Spec mục 8](../Running-Project-Specification-Student.md).

<<<<<<< Updated upstream
Dùng telemetry local cho baseline; không giữ AWS chạy liên tục. Alloy/OTel có thể cải tiến collector, không bỏ các nhiệm vụ gốc.

## Prometheus topology

Helm template `deploy/helm/insighthub/templates/observability.yaml` là nguồn
triển khai ServiceMonitor. Bật `observability.enabled=true` chỉ sau khi
`kube-prometheus-stack` đã cài CRD Prometheus Operator.

- Web và API scrape endpoint `/metrics` thực tế.
- Worker mở endpoint Prometheus riêng trên `WORKER_METRICS_PORT` (mặc định
  `9108`) và không dùng log để tạo series.
- Redis và PostgreSQL dùng exporter riêng; queue exporter đọc read-only đúng
  Redis sorted set do ARQ dùng, xuất queue depth/oldest-job-age thật.
- Exporter nhận connection values qua các Secret đã tồn tại. Helm không tạo
  secret, không chứa DSN, password hoặc webhook.

Secret Redis exporter cần key `REDIS_ADDR`; PostgreSQL exporter cần
`DATA_SOURCE_NAME`; queue exporter cần `REDIS_URL` và tùy chọn
`INGESTION_QUEUE`. Các key có thể cùng nằm trong một Secret hoặc dùng Secret
riêng theo từng exporter qua values.

Ví dụ render an toàn (không apply):

```powershell
helm template insighthub deploy/helm/insighthub -f deploy/helm/insighthub/values-local.yaml `
  --set observability.enabled=true `
  --set observability.exporters.redis.existingSecret=insighthub-observability `
  --set observability.exporters.postgres.existingSecret=insighthub-observability `
  --set observability.exporters.queue.existingSecret=insighthub-observability
```
=======
## Nguồn metric theo thành phần

| Thành phần | Nguồn thực | Cách Prometheus discover |
| --- | --- | --- |
| Web | kubelet/cAdvisor container CPU/RAM qua kube-prometheus-stack; Next.js hiện không có `/metrics` | kube-prometheus-stack kubelet scrape, không tạo ServiceMonitor giả |
| API | FastAPI `GET /metrics` | Helm Service `insighthub-api`, port `http-metrics` |
| Ingestion worker | `prometheus_client` HTTP endpoint; processing metrics và ARQ Redis `ZCARD` queue depth | Helm Service `insighthub-worker`, port `http-metrics` |
| PostgreSQL | `prometheuscommunity/postgres-exporter` | Exporter Service, port `http-metrics` |
| Redis / ARQ queue | `oliver006/redis_exporter`; queue-depth là metric worker đọc trực tiếp ZSET của ARQ | Redis exporter Service và worker Service |

`deploy/helm/insighthub/templates/observability.yaml` là source of truth cho
ServiceMonitor/exporter. Exporters chỉ enable ở môi trường có Secret application
tham chiếu; chart chỉ render `secretKeyRef` cho `DATABASE_URL`/`REDIS_URL`, không
render giá trị credential. `observability/kube-prometheus-stack-values.yaml` là
override để platform owner áp dụng cho kube-prometheus-stack ngoài chart này; nó
đặt retention 15 ngày và resource requests/limits Prometheus.

Dùng telemetry local cho baseline; không giữ AWS chạy liên tục. Alloy/OTel có thể
cải tiến collector, không bỏ các nhiệm vụ gốc.

## Generation cost estimate

`insighthub_llm_generation_estimated_cost_dollars_total` chỉ tăng khi API nhận
đủ `input_tokens` và `output_tokens` do provider trả về, provider là `openai`, và
model cấu hình chính xác là `gpt-5.6-sol`. Giá lab đã được phê duyệt ngày
2026-09-29 từ yêu cầu Day 4: USD 5 / một triệu input tokens và USD 30 / một triệu
output tokens. Đây chỉ là ước lượng generation; không gồm embedding hoặc hạ tầng,
không phải hóa đơn và không suy diễn giá cho model/provider khác. Usage thiếu hay
model khác sẽ không tạo series cost (dashboard phải hiển thị unavailable, không
diễn dịch là USD 0).
>>>>>>> Stashed changes
