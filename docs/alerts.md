# Alert Runbooks

Ba alert dùng ngưỡng triệu chứng người dùng từ dashboard/SLO. Cấu hình Slack channel trong `config/alert_rules.yaml`; mỗi lần điều tra, nối log với trace qua `correlation_id`.

## Latency P95 High

- **Severity / duration:** warning, P95 trên 3.000 ms liên tục 5 phút.
- **Ảnh hưởng:** câu trả lời đến chậm hoặc timeout ở phía người dùng.
- **Kiểm tra:**
	1. Xem panel latency và xác nhận P95/P99 cùng tăng trong cùng time range.
	2. Lọc `response_sent` có `latency_ms > 3000`, lấy correlation ID và so thời gian retrieval với generation trong trace.
	3. Kiểm tra deploy, tải request và trạng thái dependency trong khoảng thời gian đó.
- **Mitigation:** rollback deploy/prompt mới nếu trùng thời điểm; giảm concurrency hoặc tạm tắt bước truy xuất chậm để khôi phục phản hồi.
- **Owner:** `platform-oncall`.

## Chat Error Rate High

- **Severity / duration:** critical, error rate trên 2% liên tục 5 phút.
- **Ảnh hưởng:** nhiều request không nhận được câu trả lời.
- **Kiểm tra:**
	1. Xem panel errors và breakdown `error_type`.
	2. So `request_failed` với `request_received`, sau đó mở trace bằng correlation ID của request lỗi.
	3. Kiểm tra `/health`, thay đổi gần nhất và tình trạng Langfuse/model/retrieval dependency.
- **Mitigation:** rollback thay đổi gần nhất; nếu lỗi chỉ do lấy managed prompt, giữ local prompt fallback; nếu retrieval lỗi diện rộng, chuyển tạm sang câu trả lời fallback và khôi phục dependency.
- **Owner:** `platform-oncall`.

## Retrieval Success Low

- **Severity / duration:** warning, retrieval success dưới 90% liên tục 10 phút.
- **Ảnh hưởng:** câu trả lời thiếu ngữ cảnh hoặc phải dùng fallback thường xuyên.
- **Kiểm tra:**
	1. So tỷ lệ `response_sent` retrieval thành công với `request_failed` có `tool_name=retrieval`.
	2. Mở một trace lỗi theo correlation ID và kiểm tra observation `retrieve-context`.
	3. Kiểm tra vector store, index/data freshness, timeout và thay đổi retrieval gần nhất.
- **Mitigation:** khôi phục index/dependency gần nhất còn tốt; giảm tải hoặc timeout phù hợp; nếu chưa thể khôi phục, tắt retrieval có kiểm soát và dùng fallback, đồng thời thông báo giới hạn chất lượng.
- **Owner:** `ai-platform`.
