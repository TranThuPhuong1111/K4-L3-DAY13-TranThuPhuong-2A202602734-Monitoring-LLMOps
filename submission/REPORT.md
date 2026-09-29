# Báo cáo cá nhân — K4-L3A Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên:** Trần Thu Phương
- **MSSV:** 2A202602734
- **Lớp:** K4-L3A
- **Repository URL:** https://github.com/TranThuPhuong1111/K4-L3-DAY13-TranThuPhuong-2A202602734-Monitoring-LLMOps.git
- **Commit SHA cuối:** Lấy SHA để nộp từ `git log -1` sau commit cuối; CP4 source/evidence nằm trong commit `b7d1a048c8c0618320be2b9650b01a607edd4549`.
- **Challenge ID:** `day13-k4-l3a-monitoring-llmops-v1` (cohort K4).
- **Tên project Langfuse cá nhân:** `day13-k4-l3a-2A202602734`

## 2. Evidence index

Điền đúng đường dẫn tới evidence thực tế. Có thể đổi tên hoặc dùng nhiều ảnh nếu cần.

| Evidence | Đường dẫn |
|---|---|
| Pytest cuối | `evidence/01-pytest.txt` |
| Log validator | `evidence/02-log-validator.txt` |
| Dashboard validator | `evidence/03-dashboard-validator.txt` |
| Structured log | `evidence/04-structured-log.txt` |
| PII redaction | `evidence/05-pii-redaction.txt` |
| Trace list | `evidence/06-trace-list.txt` |
| Trace waterfall | `evidence/07-trace-waterfall.txt` |
| Trace metadata | `evidence/08-trace-metadata.txt` |
| Prompt versions | `evidence/09-prompt-versions.txt` |
| Prompt rollback | `evidence/10-prompt-rollback.txt` |
| Dashboard runtime | `evidence/11-dashboard-overview.png` |
| Incident metric | `evidence/12-incident-metric.txt` |
| Incident log | `evidence/13-incident-log.txt` |
| Incident trace | `evidence/14-incident-trace.txt` |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | 30/100 (21 records; 20 missing required fields; 20 missing enrichment; 0 correlation IDs; 0 PII leaks) | Xem evidence cuối: 100/100 | Baseline preserved as `data/logs.baseline.jsonl`. |
| `validate_dashboard.py` | | 6/6 panels valid | Runtime snapshot: `evidence/11-dashboard-overview.png`; static HTML source is generated from JSONL. |
| `pytest` | | 33 passed | One Langfuse SDK deprecation warning for `asyncio.iscoroutinefunction`. |
| Số traces hợp lệ | | 43 roots in personal project | 4 prompt experiment traces verified with linked labels and metadata. |
| Số PII leak | | 0 | Log validator detects no raw PII. |
| Latency P95 / TTFT P95 | | 3,510 ms / 50 ms | 60-minute response-log snapshot including CP3 challenge. |
| Retrieval success rate | | 52.38% overall; 100% in CP3 workload | Overall window includes 10 intentional practice `tool_fail` failures; all 5 official CP3 requests succeeded. |

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:** Middleware giữ `x-request-id` không rỗng hoặc sinh `req-<8-hex>`, bind vào structlog contextvars và trả lại trong `x-request-id`; `x-response-time-ms` ghi thời gian xử lý.
- **Các metadata được ghi vào structured log:** `user_id_hash`, `session_id`, `feature`, `model`, `env` được bind trước `request_received`.
- **Cách bảo đảm PII được scrub trước khi ghi:** `scrub_event` duyệt đệ quy giá trị string trong event và chạy trước JSONL file processor/JSON renderer; nhận diện email, điện thoại Việt Nam, CCCD 12 số và thẻ 13–19 số.
- **Cách kiểm chứng kết quả:** Baseline 30/100 được lưu trước khi sửa; sau đó đổi tên log baseline, restart API, chạy load test và validator đạt 100/100 với 10 correlation ID và 0 PII leak.

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:** Langfuse observations API xác nhận project `day13-k4-l3a-2A202602734`, 43 root traces; 4 prompt traces cùng synthetic session `cp4-prompt-demo` được truy vấn theo correlation ID.
- **Cấu trúc root/retrieval/generation observations:** `lab-agent-run` (AGENT) có child `retrieve-context` (RETRIEVER) và `generate-response` (GENERATION); generation có model, prompt link, token usage và cost. CP3 waterfall tại [evidence/07-trace-waterfall.txt](evidence/07-trace-waterfall.txt).
- **Cách nối trace với log:** Mỗi generation và structured log dùng cùng `correlation_id`; đối chiếu các lần prompt tại [evidence/08-trace-metadata.txt](evidence/08-trace-metadata.txt).
- **Prompt name:** `day13-chat`.
- **Version/label baseline:** v1, labels `baseline` và cuối cùng `production`; trace `64011dfb2db88cfd0f14eda3350bd75d`.
- **Version/label candidate:** v2, label `candidate`; trace `4690411248ab5ef84e7ceee90d53443e`. Thay đổi: thêm chỉ dẫn trả lời ngắn gọn và dựa trên tài liệu liên quan.
- **Trace ID của mỗi version:** v1 baseline `64011dfb2db88cfd0f14eda3350bd75d`; v2 candidate `4690411248ab5ef84e7ceee90d53443e`; v2 khi được promote `669afbe3342d714a5f6394de0bf81dcd`; v1 sau rollback `714defa49423631d0f55d0de81793bd3`.
- **Cách promote và rollback `production`:** Chuyển `production` từ v1 sang v2, chạy cùng synthetic input và xác nhận `get(label=production)` trả v2; sau đó chuyển về v1 và xác nhận production trả v1. Chi tiết ở [evidence/09-prompt-versions.txt](evidence/09-prompt-versions.txt) và [evidence/10-prompt-rollback.txt](evidence/10-prompt-rollback.txt).

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:** `data/logs.jsonl` là nguồn chuẩn cho latency, traffic, errors/retrieval success, cost, tokens và quality. [evidence/11-dashboard-overview.png](evidence/11-dashboard-overview.png) là static 60-minute snapshot được tạo bằng `python scripts/render_dashboard.py`, không phải dashboard tự refresh.
- **SLO và lý do chọn:** `fast_successful_requests` đạt 99.5% trong rolling 28 ngày, mỗi request thành công phải có response trong 3 giây.
- **Cách tính error budget:** `100% - 99.5% = 0.5%`; tối đa 50 bad requests trên 10.000 requests.
- **Ba alert và runbook tương ứng:** latency P95 cao (`docs/alerts.md#latency-p95-high`), chat error rate cao (`docs/alerts.md#chat-error-rate-high`), retrieval success thấp (`docs/alerts.md#retrieval-success-low`); gửi Slack `#llmops-alerts`.

## 7. Điều tra challenge

- **Challenge ID:** `day13-k4-l3a-monitoring-llmops-v1`, cohort K4. Chạy bằng `python scripts/inject_incident.py` và `python scripts/load_test.py --challenge --concurrency 5`; seed/query được nạp cục bộ từ file riêng và không sao chép vào report.
- **Khoảng thời gian điều tra:** 2026-09-29 09:27:08.163703–09:27:23.468080 UTC (5 request).
- **Triệu chứng từ metrics:** Latency P95/P99 là 3.510 giây, vượt threshold 3.000 ms; TTFT P95 là 50 ms. Năm request đều HTTP 200. P95 vượt ngưỡng nhưng cửa sổ khoảng 15 giây ngắn hơn duration 5 phút nên không kết luận alert đã fire.
- **Log line và correlation ID liên quan:** `response_sent` lúc `2026-09-29T09:27:11.676048Z`, `latency_ms=3510`, `ttft_ms=50`, `tool_name=retrieval`, `tool_success=true`; correlation ID `req-45963f0a`.
- **Trace ID và span gây ảnh hưởng:** `31f162d1bc2328f7414b61fa09a44306`; root `lab-agent-run` (`69929cf7f11d6660`) mất 3.511 giây, child `retrieve-context` (`ee9752fa26749a73`) mất 2.501 giây, child `generate-response` (`bfdf2d2401aa993d`) mất 0.152 giây. Cả ba mang cùng correlation metadata.
- **Root cause:** Challenge bật incident `rag_slow` trong mock retrieval, thêm khoảng 2.5 giây vào bước retrieve; trace xác nhận retrieval chiếm phần lớn latency và làm request vượt threshold.
- **Fix action:** Tắt incident bằng `python scripts/inject_incident.py --disable`; `/health` xác nhận `rag_slow=false`, request recovery `req-48b983d6` thành công trong 1.381 giây.
- **Preventive measure:** Đặt latency budget/timeout cho retrieval, theo dõi latency theo observation type, và giảm thời gian truy xuất bằng cache/optimization. Duy trì alert P95 đủ 5 phút trước khi coi là incident được page; challenge config được giữ nguyên và vẫn ignored.

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:** Dùng observation riêng `RETRIEVER` và `GENERATION` dưới root `AGENT`; như vậy trace cho thấy retrieval chiếm 2.501 giây trong request chậm thay vì chỉ cho biết tổng request chậm.
- **Một lỗi/blocker đã gặp:** Python 3.14 ban đầu buộc build `pydantic-core` từ source nhưng Windows Application Control chặn build; cập nhật pin Pydantic để dùng wheel. Khi thêm prompt v1, CLI flag làm mất phần multiline, nên xác minh bằng GET và tạo lại bằng JSON body-file trước khi chạy trace.
- **Cách tìm nguyên nhân và xử lý:** Lấy P95 3.510 ms làm triệu chứng, tìm `req-45963f0a` trong log, rồi truy vấn trace ID `31f162d1bc2328f7414b61fa09a44306`; so sánh retriever 2.501 s với generation 0.152 s. Tắt `rag_slow` và xác nhận request recovery 1.381 s.
- **Cách hiểu luồng Metrics → Logs → Traces:** Metrics khoanh vùng tail latency; correlation ID chọn request cụ thể trong log; trace chia request thành retrieval/generation để xác định bước gây chậm.
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:** Labels cho phép triển khai prompt không đổi code; trace gắn version/usage/cost để so sánh; `production` đã được chuyển v1→v2→v1 và xác nhận bằng trace sau mỗi trạng thái.
- **Điều quan trọng nhất đã học:** Một ngưỡng bị vượt chưa chứng minh alert đã fire; cần kiểm chứng cả duration. Cũng cần đảm bảo metrics tính được request lỗi, không chỉ request thành công.
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:** Dashboard evidence là static snapshot, chưa có dashboard server tự refresh; challenge window ngắn hơn alert duration nên firing chưa được kiểm tra. CP4 changes chưa commit, vì vậy chưa có commit SHA cuối để nộp.

## 9. Checklist trước khi nộp

- [ ] Kết quả và evidence thuộc commit SHA cuối (CP4 changes chưa commit).
- [x] Tất cả ảnh/output hiện có mở được bằng đường dẫn tương đối.
- [x] Incident evidence nối đúng metric → log → trace.
- [x] Trace/prompt evidence thuộc project Langfuse cá nhân, không chứa raw prompt/PII/secret.
- [x] Repository tests và validators chạy được; dashboard snapshot được render từ JSONL.
- [x] Secret-pattern scan sạch; `.env`, challenge config và logs bị ignore; không có PII thô trong validator.
- [ ] URL repo và commit SHA cuối đã được đưa lên LMS/Codelabs (URL khớp `origin`; cần commit các thay đổi CP4 trước khi nộp SHA cuối).
