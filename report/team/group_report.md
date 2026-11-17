# Báo cáo nhóm — Lab 8 LogiX-VN

Tối đa 5 trang ngoài phụ lục. Số liệu lấy từ file trong `src/reports/`, không chép tay từ terminal.

## 1. Thông tin nhóm

- Tên nhóm: Nhóm Số 1 (L3B)
- Thành viên: xem `TEAM.md`
- Commit chốt (trùng `report/team/decision_adr.md`): `096e265`

## 2. Mục tiêu và cách tiếp cận

Bài toán yêu cầu xử lý quy trình hoàn phí vận chuyển LogiX-VN trên bốn kiến trúc (`workflow`, `single`, `orchestrator`, và `swarm` tham chiếu) với cùng chữ ký `run_claim`, đảm bảo ranh giới rõ ràng: **code** quyết định tính tiền, kiểm tra approval, trần theo đơn và idempotency qua host (`durability.issue_refund`), còn model chỉ đọc và soạn chữ. Từ số liệu thực nghiệm trên cùng corpus, seed và bảng giá, nhóm chọn kiến trúc **ít tự chủ nhất** nhưng vẫn hoàn thành đúng nhiệm vụ.

Nhóm 4 người phân công song song theo cấu trúc độc lập file:
- **Nhóm trưởng (Trần Bảo Long):** Phụ trách Policy, Durability, Integration & Evaluation (viết bộ test `src/tests/test_policy_and_durability.py`, chạy crash suite, benchmark, kiểm tra `check_submission`, tổng hợp báo cáo nhóm và ADR).
- **3 thành viên còn lại:** Mỗi người phụ trách triển khai trọn vẹn 1 kiến trúc (`workflow.py`, `single.py`, `orchestrator.py`) kèm test riêng trong `src/tests/`.

## 3. Giải pháp

Cả ba kiến trúc nhóm viết đều tuân thủ nghiêm ngặt ranh giới code/model ([docs/architecture.md](../../docs/architecture.md)) và trả kết quả qua `lab8.shapes.common.finish()`:

- **Shape A — `workflow` (`src/lab8/shapes/workflow.py`):** Thực thi theo pipeline Python cố định: đọc claim view → kiểm tra `order_id` (thiếu trả `needs_info`) → gọi `lookup_order` (không thấy/sai principal trả `escalated`) → lọc policy hiện hành (`is_current`) và tính tiền bằng `compute_compensation` → nếu `quote == 0` trả `denied`, nếu `quote > 0` gọi `durability.issue_refund(..., crash_at=crash_at)` với quote đầy đủ và không nuốt `InjectedCrash`.
- **Shape B — `single` (`src/lab8/shapes/single.py`):** Vòng lặp ReAct tối đa 8 bước với `MockLLM` chỉ được gọi tool đọc (`lookup_order`, `lookup_policy`, `lookup_refund_history`, `compute_compensation`). Sau vòng lặp, code của shape tự kiểm chứng kết quả và gọi `durability.issue_refund` với quote đầy đủ.
- **Shape C — `orchestrator` (`src/lab8/shapes/orchestrator.py`):** Orchestrator tạo gói `handoff.v1` qua `lab8.handoff.make_handoff` chỉ gồm các field allowlist và cấp quyền tool chỉ đọc cho investigator; toàn bộ `parent_secret`, `raw_headers_json`, PII (`phone`, địa chỉ, `item_name`, `internal_note`) bị loại bỏ trước khi chuyển giao và không ghi vào trace.

## 4. Kết quả

Bảng so sánh 4 shape trên bộ public (`src/reports/benchmark.json`, 14 claim × 5 seed `11,22,33,44,55` = 70 trial/shape):

| Shape | Pass rate | Pass^5 | Seed min–max | Variance | Cost/success (VND) | Mean / p95 steps |
| --- | ---: | ---: | --- | ---: | ---: | ---: |
| `workflow` | 1.000 | 1.000 | 1.000–1.000 | 0.000000 | 27.86 | 4.43 / 5.0 |
| `single` | 1.000 | 1.000 | 1.000–1.000 | 0.000000 | 39.33 | 8.79 / 10.0 |
| `orchestrator` | 1.000 | 1.000 | 1.000–1.000 | 0.000000 | 57.04 | 5.36 / 6.0 |
| `swarm` | 0.986 | 0.929 | 0.929–1.000 | 0.000816 | 49.57 | 2.80 / 3.0 |

- **Crash safety (`src/reports/crash.json`):** `20/20` kịch bản crash (`before_effect`, `after_effect_before_checkpoint`, `after_checkpoint`) đều an toàn sau resume.
- **Test tự động:** Cổng host đạt `71 passed` (gồm cả test policy/durability nhóm thêm); ma trận student đạt `260 passed`.
- Quyết định kiến trúc và lý do: xem `report/team/decision_adr.md`. Phiếu nghiên cứu và ablation: xem `report/team/research_card.md`.

## 5. Khó khăn và cách xử lý

- **Lỗi kích hoạt môi trường ảo trên Windows PowerShell:** Lệnh `source .venv/bin/activate` không chạy trên PowerShell; nhóm chuyển sang dùng `.\.venv\Scripts\Activate.ps1` và chạy `python -m pip install -r requirements.txt` theo hướng dẫn Windows trong `src/README.md`.
- **Lỗi `trial_pass` khi viết test grader audit:** Ban đầu tự tạo dict `expected` thiếu field `refund_vnd` gây `KeyError` trong `lab8.metrics.trial_pass`, và nhầm `check_trace` với kiểm tra secret. Nhóm đã sửa bằng cách lấy `expected` chuẩn từ `BY_ID["C-007"]["expected"]` và kiểm tra secret leakage thông qua `trial_pass` (`forbidden_substring`).

## 6. Tổng hợp đóng góp

Chi tiết đóng góp của từng thành viên nằm trong `TEAM.md` (bảng đóng góp) và báo cáo cá nhân `report/team/MSSV_HoTen.md`.

## 7. Hạn chế và hướng cải thiện

MockLLM không phải model sản xuất; latency là `unavailable`, và chi phí token chỉ là mô phỏng theo `config/pricing.yaml`. Kết luận chọn `workflow` đúng với tập dữ liệu có quy trình nghiệp vụ xác định; nếu mở rộng sang ticket đa ngôn ngữ hoặc yêu cầu tra cứu ngữ nghĩa phức tạp hơn, cần đánh giá lại trên LLM thật với bộ kiểm thử chống prompt injection.

## 8. Tài liệu tham khảo

- Tài liệu hướng dẫn nội bộ repo: `README.md`, `docs/business_rules.md`, `docs/contracts.md`, `docs/architecture.md`, `docs/metrics.md`.
- AgentArch (AACL 2026) — tài liệu tham khảo lý thuyết về lựa chọn kiến trúc agent (slide 68–69).
