# Báo cáo cá nhân — 2A202604012_TranBaoLong

## 1. Thông tin thành viên

- Họ tên: Trần Bảo Long
- MSSV: 2A202604012
- Email: tranbaolong5b@gmail.com
- GitHub: BLong1501

## 2. Phần việc phụ trách

Nhóm trưởng — phụ trách mảng **Policy, Durability, Integration & Evaluation**:
- Điều phối chia việc, kiểm tra chuẩn môi trường CP1 cho cả nhóm.
- Thiết kế và viết bộ test kiểm tra Policy, Durability, Crash và Trace Security cho cả 3 shape nhóm viết (`workflow`, `single`, `orchestrator`) và host gate.
- Tổng hợp code từ 3 thành viên, chạy crash suite (`lab8.crash_test`), benchmark (`lab8.benchmark`), kiểm tra format nộp bài (`lab8.check_submission`), và hoàn thiện `decision_adr.md`, `research_card.md`, `group_report.md`, `TEAM.md`.

## 3. Đóng góp cụ thể

- Thêm mới file test `src/tests/test_policy_and_durability.py` gồm:
  - 5 test cổng host kiểm tra approval hết hạn/thu hồi/`<= 0`, bỏ qua policy cũ & tương lai, trần theo đơn (`cap_per_order` + `paid_vnd`), các điểm crash (`before_effect`, `after_checkpoint`), và fail-closed của `trial_pass` / `check_trace`.
  - 3 test `@pytest.mark.student` kiểm tra cả 4 shape với các ca: mượn approval của claim khác (`approval_claim_mismatch`), prompt injection trong ticket kèm `order_id = NULL`, và truyền quote đầy đủ trên đơn đã hoàn một phần (`C-014`).
- Chạy và xác nhận kết quả toàn bộ cổng host (`71 passed`), ma trận student (`260 passed`), crash suite (`20/20`) và benchmark 4 shape × 5 seed.

## 4. Bằng chứng

- File test đã thêm: `src/tests/test_policy_and_durability.py`
- File báo cáo công cụ sinh ra: `src/reports/crash.json` (`crash_safety: 20/20`), `src/reports/benchmark.json` (4 shape × 14 claim × 5 seed, ví dụ `R-workflow-C-001-s11`).
- Báo cáo nhóm & ADR: `report/team/decision_adr.md`, `report/team/research_card.md`, `report/team/group_report.md`.
- Commit benchmark hiện tại: `096e265` (sẽ cập nhật commit chốt cuối cùng vào `decision_adr.md` và `TEAM.md`).

## 5. Công cụ AI đã dùng

- Sử dụng trợ lý AI trong IDE (Antigravity / Gemini) để phân tích yêu cầu đề bài (`README.md`, `docs/business_rules.md`, `docs/contracts.md`), gợi ý cấu trúc các test case edge-case cho policy/durability và rà soát cấu trúc báo cáo.
- Cách tự kiểm tra kết quả: tự chạy trực tiếp toàn bộ lệnh `python -m pytest -q` (`71 passed`), `python -m pytest -q -m student -o addopts=` (`260 passed`), `python -m lab8.crash_test --count 20 --out reports/crash.json` (`20/20`), `python -m lab8.benchmark ...` và đối chiếu số liệu trong `src/reports/benchmark.json` trước khi đưa vào báo cáo.

## 6. Tự đánh giá

Hoàn thành đúng tiến độ các mốc CP1–CP5, đảm bảo cả 3 shape của nhóm không vi phạm 3 điều kiện must-pass (`approval_bypass = 0`, `secret_leak = 0`, `crash_safety = 20/20`) và đạt `pass_rate = 1.000` trên tập public.
