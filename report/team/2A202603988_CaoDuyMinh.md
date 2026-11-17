# Báo cáo cá nhân — 2A202603988_CaoDuyMinh

## 1. Thông tin thành viên

- Họ tên: Cao Duy Minh
- MSSV: 2A202603988
- Email:
- GitHub: workcaominh-gif (commit ký tên `cduyminh`)

## 2. Phần việc phụ trách

Shape C `orchestrator` (`src/lab8/shapes/orchestrator.py`): orchestrator cộng investigator chỉ đọc, handoff qua allowlist, ghi tiền qua cửa host `durability.issue_refund`. Phần này gồm cả CP2 (thay stub) và CP3 (truyền `crash_at`, handoff đã sanitize trong trace).

## 3. Đóng góp cụ thể

**Commit chính:** [`0498ae4`](https://github.com/BLong1501/K5-L3B-DAY08-NhomSo1-FromWorkflowsToAgents/commit/0498ae4d19cf48a6f0fba99dc6f56b238004d760): `feat(orchestrator): shape C with read-only investigators and sanitized handoff`.

**Luồng của shape C:**

1. Orchestrator đọc claim qua `get_claim_view`. View này không có cột `parent_secret`.
   - Claim không tồn tại: `failed`.
   - Thiếu `order_id`: `needs_info`. Không tìm mã đơn trong câu chữ của ticket.
2. Dựng handoff bằng `make_handoff` với `facts={}` và 4 tool chỉ đọc: `lookup_order`, `lookup_policy`, `lookup_refund_history`, `compute_compensation`. Không có tool ghi nào được giao.
3. `run_readonly_investigators` chạy các tool đó với `worker=True`.
   - Không thấy đơn, hoặc principal không sở hữu đơn: `escalated`.
4. Số tiền lấy từ `compute_compensation`, chỉ dựa trên policy hiện hành. MockLLM chỉ được gọi hai lần: một lần `plan` để mô phỏng việc giao việc, một lần `draft` để soạn câu trả lời. Câu chữ model trả về không quyết định số tiền hay status.
5. Gọi host:
   - Quote = 0: `denied`, không gọi `issue_refund`.
   - Quote > 0: gọi `issue_refund(claim_id, quote đầy đủ, crash_at=crash_at)`. Host từ chối thì `denied`, xung đột số tiền thì `failed`, chấp nhận thì `resolved`. `proposal_amount` luôn là quote đầy đủ.
6. Mọi nhánh return đi qua một hàm `done()` → `common.finish()`, nên nhánh nào cũng có trace đúng contract v1.

**Quyết định kỹ thuật:**

| Quyết định | Lý do |
| --- | --- |
| Truyền quote đầy đủ, không tự trừ phần đã hoàn | Host đã trừ theo trần của đơn. Shape trừ trước thì bị trừ hai lần và T14 fail (O-515: truyền 150.000, ledger ghi 120.000). |
| Không bao giờ tin số ngày trễ hay mã đơn trong ticket | Ticket là dữ liệu người dùng. Đây cũng là điểm yếu `REFERENCE_WEAKNESS` của swarm ở seed 55. |
| `except InjectedCrash`: chỉ ghi trace rồi `raise` lại | T12 cần thấy crash thật xảy ra. Ledger cùng khóa `refund:{claim_id}` bảo đảm resume không tạo refund thứ hai. |
| Trace chỉ ghi handoff đã sanitize và các field đơn trong allowlist (`TRACE_ORDER_KEYS`) | Trace là ranh giới bảo mật. Không ghi ticket, claim row, SĐT, địa chỉ, tên hàng, ghi chú nội bộ. |
| Thêm `lookup_refund_history` vào tool của investigator | Orchestrator biết đơn đã được hoàn bao nhiêu (ghi `refunded_vnd` vào trace) mà vẫn để host quyết định trần. |

**Test đã thêm:** `src/tests/test_orchestrator_boundary.py`

- `test_orchestrator_traces_sanitized_handoff_without_ticket`: chạy mọi claim public. Kiểm trace không chứa `CANARY_SECRET_`, `parent_secret` hay nội dung ticket; event handoff chỉ có field trong `ALLOWED_FIELDS` và tool trong `READONLY_TOOLS`.
- `test_orchestrator_missing_order_id_is_needs_info_without_ledger`: claim thiếu mã đơn trả `needs_info`, `proposal_amount = 0`, không có refund.

**Tài liệu kiến trúc:** [`abc0639`](https://github.com/BLong1501/K5-L3B-DAY08-NhomSo1-FromWorkflowsToAgents/commit/abc0639): `README_architecture.md` ở gốc repo. Gồm bản đồ thư mục, cách các module ghép nhau, vòng đời một claim, so sánh bốn shape, sequence của shape C, cổng ghi tiền của host, sơ đồ ER của SQLite, ranh giới bảo mật và pipeline đo, đều vẽ bằng Mermaid, kèm bảng số đo từ `src/reports/benchmark.json`.

**Tài liệu demo:**

- Bộ slide có animation chạy lặp cho từng shape A/B/C. Năm claim public chạy qua sơ đồ; bong bóng giải thích lý do mỗi khi một case rời đường chính. Thêm slide CP3 (T11, T12, handoff).
- Một trang tương tác: bấm một case để chạy riêng case đó qua cả ba shape, kèm bảng so sánh từng bước. Ví dụ C-005: single dừng ngay sau tra đơn vì model quan sát rồi mới chọn, còn orchestrator vẫn tra policy và lịch sử hoàn vì đã giao trọn danh sách việc trong handoff.
- Số bước, lời gọi model và tool call trên slide lấy từ lần chạy thật ba shape trên 5 claim public, seed 11.

## 4. Bằng chứng

Chạy trong `src/` ở commit `0498ae4`:

| Lệnh | Kết quả |
| --- | --- |
| `python -m pytest -q -m student -o addopts= -k orchestrator` | 62 passed |
| `python -m pytest -q` (cổng host, có 2 test mới) | 56 passed |
| `python -m lab8.crash_test --count 20 --out <file tạm>` | `crash_safety 20/20` |
| `python -m pytest -q -m student -o addopts=` (cả 4 shape) | 124 failed, 124 passed. Phần đỏ là workflow và single, chưa viết lúc đó |

Ví dụ trace `orchestrator` claim `C-001` seed 11: `resolved`, `proposal_amount` 35.000. Các event lần lượt là `claim` (`has_order_id: true`), `handoff` (đã sanitize, 4 tool đọc), `investigator` (O-107, `delivered_late`, trễ 4 ngày, phí ship 35.000), `quote`, `host`, `decision`.

File `src/reports/crash.json` và `src/reports/benchmark.json` chính thức do người phụ trách CP4 và CP5 sinh ra. Các con số ở trên là lần tự kiểm của tôi.

Chạy lại trên bản hoàn chỉnh của nhóm (commit `eedf7a4`, đủ ba shape):

| Lệnh | Kết quả |
| --- | --- |
| `python -m pytest -q` | 71 passed |
| `python -m pytest -q -m student -o addopts=` (cả 4 shape) | 260 passed, 0 failed |
| `python -m lab8.crash_test --count 20` | `crash_safety 20/20` |
| `python -m lab8.check_submission`, phần shape | orchestrator: format đúng, 12/12 claim public pass ở seed 11 |

Số liệu của orchestrator trong `src/reports/benchmark.json` (14 claim × 5 seed): pass rate 1.000, pass^5 1.000, cost/success 57,04 VND, trung bình 5,36 bước và 1,93 lời gọi model.

Trên bộ hidden (`src/reports/hidden_selfcheck.json`, 40 claim × 5 seed, nhóm trưởng chạy), orchestrator có 0 trial lỗi và 0 trial nghi lộ secret. Ở mọi claim và mọi seed, orchestrator ra cùng `status` với workflow và single. Bộ hidden không có nhãn nên đây chưa phải pass rate.

## 5. Công cụ AI đã dùng

- **Claude Code (Claude Opus 5.5):**
  - đọc đề, `docs/business_rules.md`, `docs/contracts.md` và `swarm_reference.py`;
  - viết `orchestrator.py` và 2 test trong `test_orchestrator_boundary.py`;
  - giải thích từng nhánh của code cho tôi;
  - viết `README_architecture.md` và các sơ đồ Mermaid;
  - dựng bộ slide demo và trang tương tác. Số liệu trên đó lấy từ lần chạy thật ba shape, không do AI tự đặt.
- **Cách tôi tự kiểm tra:**
  - chạy 62 test student của orchestrator, cổng host và crash suite 20 điểm (kết quả ở mục 4);
  - đọc file trace của một claim để chắc chỉ có handoff đã sanitize và field trong allowlist;
  - đối chiếu từng nhánh `status` với bảng output contract trong `docs/contracts.md`.
- Không dùng AI để tạo số liệu benchmark, run id hay commit. Mọi số liệu ở mục 4 lấy từ output lệnh thật.

## 6. Tự đánh giá

<!-- Phần này tôi tự viết (RULES.md: không dùng AI để viết phần tự đánh giá). Gợi ý: điều đã hiểu về ranh giới code / model, điều còn chưa chắc, nếu làm lại sẽ đổi gì. -->

...
