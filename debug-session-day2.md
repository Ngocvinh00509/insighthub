# Day 2 — MCP Debug Session

**Dự án:** InsightHub RAG Notebook  
**Phạm vi:** MCP Protocol Integration trên môi trường local Windows  
**Trạng thái:** Đã ghi nhận sự cố khởi động MCP và kiểm thử chặn thao tác ghi bằng RBAC.

## Mục tiêu

1. Điều tra lỗi các MCP client `filesystem`, `kubernetes`, `docker` và `prometheus` không hoàn tất khởi động khi Codex CLI kết nối qua stdio.
2. Xác minh rằng Kubernetes MCP chỉ có quyền đọc khi sử dụng ServiceAccount `mcp-readonly`: liệt kê Pod được phép, còn xóa Pod phải bị API server từ chối.
3. Ghi lại cách khắc phục có thể tái lập, không đưa kubeconfig, token, đường dẫn allowlist cụ thể hoặc dữ liệu nhạy cảm vào nhật ký.

## Các tool/lệnh đã gọi

### Case Study 1 — MCP client timeout khi khởi động

Các client MCP được Codex CLI khởi động qua `npx`/Node trên Windows:

| MCP client | Kết quả khởi động ban đầu |
| --- | --- |
| Filesystem | Timeout |
| Kubernetes | Timeout |
| Docker | Timeout |
| Prometheus | Timeout |

Lệnh/điểm kiểm tra sử dụng trong phiên debug:

```powershell
codex mcp list
codex mcp get filesystem
codex mcp get kubernetes
codex mcp get docker
codex mcp get prometheus
```

Sau khi sửa cấu hình, khởi động lại Codex CLI và chạy lại danh sách MCP để kiểm tra trạng thái kết nối. Không dùng `npx` với phiên bản thả nổi trong cấu hình nộp bài; phiên bản server phải được pin theo cấu hình Day 2 đã được phê duyệt.

### Case Study 2 — Điều tra nghi vấn ingestion-worker restart/crash

Trong quá trình quan sát container `insighthub-do2603-ingestion-worker-1`, Docker MCP trả về nhiều thông báo:

```text
Starting worker for 1 functions: process_document
```

Điều này tạo ra giả thuyết rằng ingestion-worker có thể đã restart hoặc crash.

Tuy nhiên, các dòng startup không đủ để kết luận container bị crash. Vì vậy quá trình điều tra tiếp tục bằng các Docker MCP tool read-only.

#### Bước 1 — Kiểm tra logs

Tool:

```text
container_logs
```

được gọi thông qua MCP Inspector với giới hạn số dòng log.

Log quan sát được gồm:

```text
Starting worker for 1 functions: process_document
redis_version=7.4.11
```

Trong phần log được kiểm tra không quan sát thấy traceback, exception, OOM message hoặc application error.

#### Bước 2 — Kiểm tra container state

Tool read-only:

```text
container_inspect
```

được sử dụng để kiểm tra trạng thái container.

Các field không nhạy cảm được trích xuất:

```text
Status: running
Running: True
Restarting: False
ExitCode: 0
OOMKilled: False
Error:
Health: healthy
```

Kết quả cho thấy container hiện đang chạy và healthy, không có bằng chứng về active crash loop hoặc OOM termination.

#### Bước 3 — Kiểm tra restart policy

Từ cùng kết quả `container_inspect`:

```text
RestartPolicy.Name: no
RestartPolicy.MaximumRetryCount: 0
```

Container không được cấu hình Docker automatic restart policy.

#### Kết luận

Giả thuyết ingestion-worker hiện đang crash-looping **không được evidence hỗ trợ**.

Evidence cho thấy:

- container đang `running`;
- health status là `healthy`;
- `Restarting=False`;
- `ExitCode=0`;
- `OOMKilled=False`;
- error field trống;
- log được kiểm tra không có exception hoặc traceback;
- Docker automatic restart policy không được bật.

Các startup message cho thấy worker đã được start nhiều lần, nhưng evidence hiện tại không xác định nguyên nhân của các lần start đó.

Vì vậy không kết luận rằng worker đã crash, bị Docker tự restart, bị Compose recreate hay được restart thủ công nếu chưa có thêm evidence.

## Phân tích từ AI Agent

### Case Study 1 — Phân tích MCP startup

Trong giai đoạn cấu hình ban đầu, các MCP backend gặp vấn đề hoàn tất startup/stdio initialization.

Các cấu hình được kiểm tra bằng:

```text
codex mcp list
codex mcp get filesystem
codex mcp get docker
codex mcp get kubernetes
codex mcp get prometheus
```

Sau quá trình kiểm tra command, arguments, đường dẫn, dependency và timeout configuration, cả bốn MCP backend đều thực hiện thành công real read-only tool call.

Kết quả cuối cùng:

```text
Filesystem   PASS
Docker       PASS
Kubernetes   PASS
Prometheus   PASS
```

MCP Inspector cũng thực hiện thành công `tools/list` và `tools/call` trên cả bốn backend.

Evidence hiện có không đủ để khẳng định một nguyên nhân duy nhất cho startup issue ban đầu.

Vì vậy không kết luận rằng `npx`, Node.js hoặc một giá trị timeout cụ thể là root cause nếu chưa có timing/log evidence chứng minh điều đó.

Cấu hình cuối cùng sử dụng explicit `startup_timeout_sec` và `tool_timeout_sec` phù hợp cho từng MCP server thay vì tăng toàn bộ server lên `60` giây.

### Case Study 2 — Phân tích ingestion-worker

Các startup message ban đầu tạo ra giả thuyết rằng ingestion-worker có thể restart hoặc crash.

Docker MCP được sử dụng để thu thập thêm evidence bằng:

```text
container_logs
container_inspect
```

State quan sát được:

```text
Status: running
Running: True
Restarting: False
ExitCode: 0
OOMKilled: False
Health: healthy
```

Restart policy:

```text
RestartPolicy.Name: no
RestartPolicy.MaximumRetryCount: 0
```

Do đó không có evidence cho thấy container hiện đang crash-looping.

Các lần startup trước đó không được gán nguyên nhân khi chưa có thêm evidence.

### Kubernetes RBAC

Kubernetes MCP sử dụng ServiceAccount `mcp-readonly` trong namespace `insighthub`.

RBAC cho phép các thao tác đọc như:

```text
get
list
watch
```

và không cấp các mutation verb như:

```text
create
update
patch
delete
```

Read operation được xác nhận thành công trong khi destructive Pod operation bị Kubernetes authorization từ chối.

Điều này tạo defense in depth giữa MCP read-only configuration và Kubernetes RBAC.

## Kết luận & Sửa đổi

1. **MCP startup:** cả bốn MCP backend `filesystem`, `docker`, `kubernetes` và `prometheus` đã hoàn thành real read-only tool call. Không gán một root cause cụ thể cho startup issue ban đầu khi chưa có đủ timing/log evidence.

2. **Filesystem security:** Filesystem MCP chỉ được phép truy cập project allowlist. Thử truy cập đường dẫn bên ngoài allowlist bị từ chối.

3. **Docker validation:** Docker MCP đã quan sát container thành công bằng các read-only tool. Việc điều tra ingestion-worker bằng `container_logs` và `container_inspect` không tìm thấy evidence của active crash loop.

4. **Kubernetes security:** Kubernetes MCP sử dụng ServiceAccount `mcp-readonly` và namespace-scoped RBAC. Các thao tác đọc được cho phép, trong khi destructive operation không được RBAC cấp quyền.

5. **Prometheus validation:** Prometheus MCP gọi thành công `prometheus_summary` với predefined aggregate query `requests_5m`.

6. **MCP Inspector:** `tools/list` và real `tools/call` đã được kiểm tra thành công trên cả bốn MCP backend.

7. **Security:** không đưa token, kubeconfig content, private key, database credential hoặc secret khác vào debug report.

### Final validation

```text
Filesystem MCP    PASS
Docker MCP        PASS
Kubernetes MCP    PASS
Prometheus MCP    PASS

Inspector Filesystem    PASS
Inspector Docker        PASS
Inspector Kubernetes    PASS
Inspector Prometheus    PASS
```

Day 2 MCP integration và debugging workflow đã được xác minh bằng real read-only tool calls và evidence thu thập từ môi trường local.
