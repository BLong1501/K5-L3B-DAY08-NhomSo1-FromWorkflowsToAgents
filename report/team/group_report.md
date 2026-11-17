# Báo cáo nhóm — Lab 8 LogiX-VN

Tối đa 5 trang ngoài phụ lục. Số liệu lấy từ file trong `src/reports/`, không chép tay từ terminal.

## 1. Thông tin nhóm

- Tên nhóm: Nhóm Số 1 (L3B)
- Thành viên: xem `TEAM.md`
- Commit chốt (trùng `report/team/decision_adr.md`): `ea96d91`

## 2. Mục tiêu và cách tiếp cận

Bài toán yêu cầu xử lý quy trình hoàn phí vận chuyển LogiX-VN trên bốn kiến trúc (`workflow`, `single`, `orchestrator`, và `swarm` tham chiếu) với cùng chữ ký `run_claim`, đảm bảo ranh giới rõ ràng: **code** quyết định tính tiền, kiểm tra approval, trần theo đơn và idempotency qua host (`durability.issue_refund`), còn model chỉ đọc và soạn chữ. Từ số liệu thực nghiệm trên cùng corpus, seed và bảng giá, nhóm chọn kiến trúc **ít tự chủ nhất** nhưng vẫn hoàn thành đúng nhiệm vụ.

Nhóm 4 người phân công song song theo cấu trúc độc lập file:
- **Nhóm trưởng (Trần Bảo Long):** Phụ trách Policy, Durability, Integration & Evaluation (viết bộ test `src/tests/test_policy_and_durability.py`, chạy crash suite, benchmark, kiểm tra `check_submission`, tổng hợp báo cáo nhóm và ADR).
- **3 thành viên còn lại:** Mỗi người phụ trách triển khai trọn vẹn 1 kiến trúc (`workflow.py`, `single.py`, `orchestrator.py`) kèm test riêng trong `src/tests/`.

## 3. Giải pháp

Cả ba kiến trúc nhóm viết đều tuân thủ nghiêm ngặt ranh giới code/model ([docs/architecture.md](../../docs/architecture.md)) và trả kết quả qua `lab8.shapes.common.finish()`:

### 3.1 Shape A — `workflow` (`src/lab8/shapes/workflow.py`)

**Ý tưởng.** Toàn bộ claims flow là các bước Python cố định, không có vòng lặp model. Đây là mức tự chủ thấp nhất trong bốn shape: code đọc dữ liệu có cấu trúc, code tính tiền, host ghi tiền. Shape **không gọi MockLLM** (kể cả bước soạn câu trả lời), vì mọi quyết định trong bài đều là luật cố định; thêm model call chỉ làm tăng cost mà không đổi kết quả. Sơ đồ chi tiết: [docs/workflow_flow.md](../../docs/workflow_flow.md).

**Các bước.**

| # | Bước | Gọi | Nhánh ra |
|---|------|-----|----------|
| 1 | Đọc claim | `tools.get_claim_view` (chỉ `claim_id`, `principal_id`, `order_id`, `ticket`; không `SELECT *` vì claim row có `parent_secret`) | Không tồn tại → `failed`, `unknown_claim` |
| 2 | Kiểm `order_id` | — | Thiếu → `needs_info`, proposal 0. Không đoán mã đơn từ ticket |
| 3 | Tra đơn theo principal | `tools.lookup_order(conn, order_id, principal_id)` | `visible=false` (không thấy / không sở hữu) → `escalated`, proposal 0 |
| 4 | Tính quote | `tools.compute_compensation(conn, order)` trên order row; chỉ policy `is_current` và `effective_date ≤ 2026-11-15` | — |
| 5 | Quote = 0 | — | `denied`, proposal 0, **không** gọi `issue_refund` |
| 6 | Quote > 0 | `durability.issue_refund(conn, claim_id, quote, crash_at=crash_at)` với **quote đầy đủ** | `ok` → `resolved`; `conflict` → `failed`; còn lại → `denied` (host ghi `policy_denied`). `proposal_amount` luôn là quote đầy đủ |
| 7 | Trả kết quả | `shapes.common.finish(...)` ở **mọi** nhánh | Tự lấy `refund_effects`, `committed_audit_count` từ ledger và ghi trace |

**Ranh giới code / model.**

| Việc | Ai quyết trong workflow |
|---|---|
| Đọc ticket | Không ai. Ticket không được parse; số ngày trễ ("trễ 5 ngày", "ignore policy") không ảnh hưởng gì |
| Lọc principal, chọn policy hiện hành, tính tiền | Code (`lookup_order`, `compute_compensation`) |
| Approval, trần theo đơn, idempotency, ghi ledger | Host (`durability.issue_refund`, một transaction) |
| Soạn câu chữ | Không dùng model |

**Vì sao truyền quote đầy đủ.** Host tự trừ phần đơn đã được hoàn bởi claim khác trong cùng transaction ghi. Nếu shape tự trừ trước thì bị trừ hai lần: T14 (`O-515`, đã hoàn 30.000, entitlement 150.000) sẽ ghi 90.000 thay vì 120.000. Tương tự, khi quote > 0 mà approval hỏng hoặc đơn đã hoàn đủ (T07, T13), workflow vẫn gọi host để có audit `policy_denied` thay vì tự từ chối.

**Crash và retry.** `crash_at` được truyền thẳng vào `issue_refund`. Khi có `InjectedCrash`, workflow ghi event `crash` vào trace rồi `raise` lại, không nuốt lỗi. Chạy lại trên cùng DB thì host trả `idempotent_replay` theo khóa `refund:{claim_id}`, nên vẫn một dòng ledger và một audit `refund_committed`.

**Trace.** Dùng `lab8.trace.Trace`, file `traces/<run_id>.json`, ghi ở mọi nhánh return. Các event:

| Event | Payload |
|---|---|
| `claim` | `claim_id`, `found`, `has_order_id` |
| `lookup_order` | `visible` + `reason`, hoặc order view allowlist (`ORDER_FIELDS`: `order_id`, `status`, `delay_days`, `shipping_fee_vnd`, `paid_vnd`, `damage_verified`, `carrier`) |
| `quote` | `amount_vnd`, `reason`, `clause_ids` |
| `issue_refund` | `ok`, `reason`, `conflict` |
| `crash` | `at` (chỉ khi có crash injection) |
| `decision` | `status`, `proposal_amount`, `reason` |

Cố ý **không** ghi: claim row (có `parent_secret`), nguyên văn ticket, order row thô (SĐT, địa chỉ, tên hàng, ghi chú nội bộ), approval row.

**Kiểm chứng.** Ma trận student `-k workflow`: 62/62 passed. Test riêng `src/tests/test_workflow_boundary.py` (21 test): trace không chứa chuỗi cấm của từng claim và không chứa ticket; T02 bị `denied` ở cả 5 seed (kể cả seed 55, chỗ swarm fail); không có model call; gọi lại cùng claim vẫn một refund.

### 3.2 Shape B — `single` (`src/lab8/shapes/single.py`)

Vòng lặp ReAct tối đa 8 bước với `MockLLM` chỉ được gọi tool đọc (`lookup_order`, `lookup_policy`, `lookup_refund_history`, `compute_compensation`). Sau vòng lặp, code của shape tự kiểm chứng kết quả và gọi `durability.issue_refund` với quote đầy đủ.

### 3.3 Shape C — `orchestrator` (`src/lab8/shapes/orchestrator.py`)

- **Chuẩn bị:** orchestrator đọc claim qua `get_claim_view`; thiếu `order_id` thì trả `needs_info` ngay, không giao việc. Model được gọi một lần để lập kế hoạch.
- **Handoff:** orchestrator tạo gói `handoff.v1` bằng `lab8.handoff.make_handoff` với `facts={}`, tức không chuyển dữ kiện nào từ ngữ cảnh của mình. Gói chỉ gồm field trong allowlist và cấp 4 tool chỉ đọc: `lookup_order`, `lookup_policy`, `lookup_refund_history`, `compute_compensation`.
- **Điều tra:** `run_readonly_investigators` chạy hết danh sách tool rồi báo kết quả về.
- **Quyết định:** orchestrator trả `escalated` nếu không phải chủ đơn, `denied` nếu quote bằng 0. Nếu quote lớn hơn 0, orchestrator gọi `durability.issue_refund` với quote đầy đủ và `crash_at`, không bắt `InjectedCrash`.
- **Bảo mật:** `parent_secret`, `raw_headers_json`, ticket và PII (`phone`, địa chỉ, `item_name`, `internal_note`) không đi qua handoff. Trace chỉ ghi handoff đã sanitize và 7 field đơn hàng trong allowlist. Lời gọi model không chứa ticket.
- **Chi phí:** orchestrator đắt nhất (57,04 VND/success) dù chỉ khoảng 1,9 lời gọi model mỗi claim. Theo bảng giá mô phỏng, phần lớn chi phí là tool call (10 VND/lần). Investigator đọc lại claim view và chạy hết 4 tool trong handoff mà không dừng sớm, trung bình khoảng 5,6 tool call mỗi claim.
- Sơ đồ chi tiết: [README_architecture.md](../../README_architecture.md).

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
