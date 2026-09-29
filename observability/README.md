# Observability và MLOps - bắt buộc Day 4

ServiceMonitor/exporters cho đủ5 thành phần, Grafana9+ panels,3 anomaly và3 incident/RCA, Slack alert, MLOps overview notes4 blocks/quiz. Queue/worker Day 1 và deployment Day 3 phải có thật. [Spec mục 8](../Running-Project-Specification-Student.md).

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
