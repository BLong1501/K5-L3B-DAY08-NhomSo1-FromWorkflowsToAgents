# Báo cáo cá nhân — 2A202603992_HoangNhatMinh

## 1. Thông tin thành viên

- Họ tên: Hoàng Nhật Minh
- MSSV: 2A202603992
- Email:
- GitHub:

## 2. Phần việc phụ trách

Phụ trách **Shape A — `workflow`**, cũng là shape nhóm chọn trong `report/team/decision_adr.md` (dòng `- Shape chọn: workflow`), nên phần này quyết định cổng hidden và ba điều kiện must-pass của cả nhóm:

- Viết `src/lab8/shapes/workflow.py` (CP2 + CP3).
- Viết test ranh giới `src/tests/test_workflow_boundary.py`.
- Viết tài liệu luồng xử lý `docs/workflow_flow.md` và mục 3.1 "Shape A — workflow" trong `report/team/group_report.md`.
- Hỗ trợ tích hợp: xử lý lỗi push và xung đột khi nhiều thành viên cùng đẩy lên `main`; dựng trang trực quan hoá kết quả chạy test cho nhóm.

## 3. Đóng góp cụ thể

### 3.1 Code `workflow.py`

Luồng cố định, không có vòng lặp model:

`get_claim_view` → kiểm `order_id` → `lookup_order` (theo principal) → `compute_compensation` → `durability.issue_refund` (chỉ khi quote > 0) → `common.finish()`.

| Tình huống | Kết quả workflow trả |
|---|---|
| `claim_id` không tồn tại | `failed`, `unknown_claim` |
| Thiếu `order_id` | `needs_info`, proposal 0, không ghi ledger |
| Không thấy đơn / không sở hữu đơn | `escalated`, proposal 0 |
| Quote = 0 | `denied`, proposal 0, không gọi host |
| Host từ chối (approval hỏng, approval của claim khác, đơn đã hoàn đủ) | `denied`, proposal = quote đầy đủ, host ghi `policy_denied` |
| Host báo `amount_conflict` | `failed` |
| Host ghi refund | `resolved`, proposal = quote đầy đủ |

### 3.2 Quyết định kỹ thuật

1. **Không gọi MockLLM.** Mọi quyết định trong claims flow là luật cố định; model call chỉ làm tăng cost. Trong benchmark, workflow có `mean_model_calls = 0` và cost/success thấp nhất trong 4 shape.
2. **Không đọc ticket.** Ticket là dữ liệu người dùng không tin cậy; số ngày trễ lấy từ cột `delay_days`. Vì vậy T02 (ticket "trễ 5 ngày", order 2 ngày) luôn `denied`, kể cả seed 55 là chỗ swarm fail. Không copy khối `REFERENCE_WEAKNESS`.
3. **Truyền quote đầy đủ cho host.** `policy.authorize` tự trừ phần đơn đã được hoàn (`amount -= already`). Nếu shape tự trừ trước thì bị trừ hai lần: T14 sẽ ghi 90.000 thay vì 120.000.
4. **Không tự từ chối khi quote > 0.** Luôn gọi `issue_refund` để host ghi audit `policy_denied` (T07, T13).
5. **Crash:** truyền `crash_at` vào `issue_refund`; bắt `InjectedCrash` chỉ để ghi event `crash` vào trace rồi `raise` lại. Connection SQLite đóng trong `finally`.
6. **Trace chỉ ghi field allowlist.** Event: `claim`, `lookup_order`, `quote`, `issue_refund`, `crash`, `decision`. Cố ý không ghi claim row (`parent_secret`), nguyên văn ticket, order row thô (SĐT, địa chỉ, tên hàng, ghi chú nội bộ).

### 3.3 Test đã thêm — `src/tests/test_workflow_boundary.py` (21 test, chạy trong cổng host)

| Test | Kiểm gì |
|---|---|
| `test_workflow_trace_has_no_secret_pii_or_ticket` (14 claim) | Trace không chứa `forbid_substrings` của claim, `parent_secret`, nguyên văn ticket; order trong trace chỉ có `ORDER_FIELDS` |
| `test_workflow_ignores_ticket_delay_on_every_seed` (5 seed) | C-002 (T02) luôn `denied`, proposal 0, không có refund |
| `test_workflow_makes_no_model_calls` | `model_calls` và token đều bằng 0 trên cả 14 claim |
| `test_workflow_replay_keeps_one_refund` | Gọi lại C-001 vẫn một refund 35.000 và một audit `refund_committed` |

### 3.4 Hỗ trợ nhóm

- **Lỗi push `non-fast-forward`:** commit orchestrator của thành viên khác lên `main` trước. Xử lý bằng `git fetch` → `git rebase origin/main` → chạy lại test → push thường, không force-push.
- **Xung đột `group_report.md`** khi pull bản nhóm đã điền: giữ mục 3.1 workflow chi tiết, dùng đoạn mô tả `single` / `orchestrator` của nhóm cho 3.2, 3.3, giữ nguyên mục 4–8.
- **Tài liệu luồng** `docs/workflow_flow.md`: sơ đồ luồng claim của workflow, luồng bên trong `durability.issue_refund`, bảng status ↔ ledger và luồng làm bài CP1 → nộp, để cả nhóm dùng chung khi viết shape.
- **Trang trực quan hoá "LogiX Test Replay"**: phát lại kết quả pytest, benchmark 4 shape, crash suite và tự kiểm hidden, dựng từ các file trong `src/reports/` (không sửa file JSON nào).

## 4. Bằng chứng

### Commit

- `034fe35` — cài shape workflow và `docs/workflow_flow.md`.
- Commit kế tiếp — thêm `src/tests/test_workflow_boundary.py`, mục 3.1 báo cáo nhóm, dòng của tôi trong bảng đóng góp `TEAM.md` và báo cáo này.

### Số liệu của workflow (lấy từ file trong `src/reports/` ở commit `eedf7a4`)

| Nguồn | Kết quả workflow |
|---|---|
| `benchmark.json` (14 claim × 5 seed = 70 trial) | pass 1.000, pass^5 1.000, seed min–max 1.000–1.000, variance 0.000000, cost/success 27.86 VND, mean / p95 steps 4.43 / 5, model call 0, tool call TB 2.79. Run id ví dụ: `R-workflow-C-001-s11` |
| So sánh cùng file | cost/success: workflow 27.86 < single 39.33 < swarm 49.57 < orchestrator 57.04 |
| `hidden_selfcheck.json` (40 claim × 5 seed = 200 trial, không nhãn) | 0 trial lỗi, 0 trial nghi lộ secret; status: 90 resolved, 95 denied, 10 escalated, 5 needs_info; tổng cost 5.800 VND (single 8.236,9; orchestrator 11.918,5) |
| `crash.json` | `crash_safety` 20/20 |

### Lệnh tự chạy lại (trong `src/`)

| Lệnh | Kết quả |
|---|---|
| `python -m pytest -q -m student -o addopts= -k workflow` | 65 passed (62 ma trận public + 3 test student của nhóm) |
| `python -m pytest -q tests/test_workflow_boundary.py` | 21 passed |
| `python -m pytest -q` (cổng host, có test của tôi) | 92 passed, không có `failed` |
| `python -m pytest -q -m student -o addopts=` | 260 passed |
| `python -m lab8.run --shape workflow --claim-id C-012 --seed 11 --db <db> --crash-at after_effect_before_checkpoint`, rồi chạy lại không `--crash-at` trên cùng DB | Lần 1 `crashed: true`; lần 2 `resolved`, một refund |

## 5. Công cụ AI đã dùng

- **Claude Code** (trợ lý lập trình trong app Claude):
  - đọc tài liệu đề bài và code host để tóm tắt luồng xử lý (`docs/workflow_flow.md`);
  - gợi ý code `workflow.py` và test `test_workflow_boundary.py`;
  - soạn nháp mục 3.1 báo cáo nhóm và báo cáo này;
  - hỗ trợ xử lý lỗi push, xung đột merge và dựng trang trực quan hoá.
- **Cách tự kiểm tra:**
  - Đối chiếu từng nhánh của `workflow.py` với bảng output contract (`docs/contracts.md`) và luật nghiệp vụ (`docs/business_rules.md`).
  - Chạy lại ma trận student, cổng host, test ranh giới và kịch bản crash/resume; chỉ ghi số đã thấy trong output hoặc trong file `src/reports/`.
  - Kiểm tay con số ví dụ T14 (90.000 nếu trừ hai lần) bằng cách đọc `lab8/policy.py::authorize`.
  - Mở trace sinh ra để chắc không có `CANARY_SECRET_*`, SĐT, địa chỉ.
  - Với trang trực quan hoá: so số trên trang với `benchmark.json`, `crash.json`, `hidden_selfcheck.json`.

## 6. Tự đánh giá

- **Làm tốt:** shape do tôi phụ trách được nhóm chọn vì đạt pass 1.000 / pass^5 1.000 với cost thấp nhất và không có model call; cả ba điều kiện must-pass (không bypass approval, không lộ secret, crash 20/20) đều có test hoặc report chứng minh; trace được kiểm bằng test riêng.
- **Hạn chế:** kết quả chỉ trên MockLLM và bộ public 14 claim; bộ hidden mới tự kiểm (không có nhãn) nên chưa có pass rate thật. Workflow dùng `lab8.trace.Trace` có sẵn, chưa viết tracer riêng.
- **Nếu làm tiếp:** thêm test cho nhánh `amount_conflict` và hai điểm crash `before_effect` / `after_checkpoint` chạy riêng trên workflow; thử ablation bỏ bước `lookup_order` theo principal để đo xem test nào bắt được.
