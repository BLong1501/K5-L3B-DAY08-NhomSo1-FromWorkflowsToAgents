# Decision record

Điền sau dấu `:` trên cùng dòng, không xóa nhãn. Giảng viên và `python -m lab8.check_submission` (chạy trong `src/`) đọc các dòng này bằng máy. Không đổi tên hay dời file này khỏi `report/team/`.
`Shape chọn` phải là đúng một trong: `workflow`, `single`, `orchestrator`, `swarm`. Đây là shape được chấm cổng hidden.

- Shape chọn: workflow
- Commit hash: 9ad2cc7
- Run id dẫn chứng: R-workflow-C-001-s11 (tập 70 trial trong src/reports/benchmark.json)
- Pass rate / pass^5 / seed min-max / variance: 1.000 / 1.000 / 1.000-1.000 / 0.000000
- Cost per success (mô phỏng, VND): 27.86
- Crash safety: 20/20 (src/reports/crash.json)
- Secret leak / approval bypass: 0 / 0

Ví dụ một dòng đã điền: `- Shape chọn: workflow`, `- Crash safety: 20/20 (src/reports/crash.json)`.

## Vì sao shape này

So sánh trên cùng tập 14 claim public × 5 seed (`11, 22, 33, 44, 55`, tổng 70 trial mỗi shape, bảng giá `config/pricing.yaml`, `as_of = 2026-11-15`), ba kiến trúc `workflow`, `single`, và `orchestrator` đều đạt `pass_rate = 1.000`, `pass^5 = 1.000`, `seed_variance = 0.000000` (trong khi `swarm` đạt `0.986` / `0.929`, `var = 0.000816` do fail `C-002` ở seed `55`). Chọn `workflow` vì đây là kiến trúc **ít tự chủ nhất** nhưng vẫn giải quyết trọn vẹn bài toán: các bước đọc claim, kiểm tra `order_id`, tra cứu order/policy hiện hành (`is_current`), tính tiền bằng `compute_compensation` và gọi `durability.issue_refund` đều tất định bằng code, cho chi phí mô phỏng thấp nhất (`27.86` VND/success so với `39.33` ở `single`, `57.04` ở `orchestrator`, `49.57` ở `swarm`) và số bước ít nhất (`4.43` mean steps).

## Có đáng đổi lấy multi-agent không

Không đáng đổi trong bài toán xử lý claim có luật nghiệp vụ cố định này. `single` và `orchestrator` chỉ ngang bằng về độ chính xác (`1.000`) nhưng tốn chi phí cao hơn 1.4x–2.0x vì phát sinh các lượt gọi model (`5.50` model calls ở `single`, `1.93` ở `orchestrator` so với `0.00` ở `workflow`), còn `swarm` làm tăng variance (`0.000816`) và có nguy cơ bị prompt injection từ ticket làm lệch số liệu. Quyết định chỉ đảo lại sang `single` hoặc `orchestrator` nếu bài toán mở rộng sang các claim phi cấu trúc cần suy luận nhiều nguồn tài liệu ngoài schema cố định, nơi `workflow` không thể đạt ngưỡng `pass_rate >= 0.75` trên tập đánh giá.

## Trace và bằng chứng

Trace của `workflow` chỉ ghi các sự kiện tối thiểu đã qua allowlist (đọc claim view, kết quả `lookup_order`, `compute_compensation`, quyết định gọi `issue_refund` / `crash`), hoàn toàn **không** ghi dòng `claims` thô (có `parent_secret`, `raw_headers_json`) hay dòng `orders` thô (có `phone`, địa chỉ, `item_name`, `internal_note`). Nếu trace nằm ngoài thư mục scanner mặc định, nhóm chứng minh không lộ secret/PII bằng cách chỉ cho phép ghi trace qua `lab8.shapes.common.finish()` với payload đã lọc allowlist và kiểm tra tự động bằng bộ test `test_trace_contract.py`, `test_handoff_secret.py` và `test_policy_and_durability.py`.

## Giới hạn

MockLLM không phải model sản xuất; kết quả phản ánh hành vi tất định theo seed của MockLLM chứ không đo khả năng hiểu ngôn ngữ tự nhiên của LLM thật. Latency để `unavailable`. Giá token trong `config/pricing.yaml` là giá mô phỏng (VND), không phải hóa đơn API thực tế. Không sửa JSON cho đủ 0.75.
