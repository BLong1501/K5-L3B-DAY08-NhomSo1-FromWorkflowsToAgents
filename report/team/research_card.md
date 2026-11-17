# Research card

File này nằm cố định ở `report/team/research_card.md`; `python -m lab8.check_submission` đọc cột "Nhóm điền" bằng máy.

Phần này nối tiếp phần mini research ở buổi lý thuyết (slide 62–63). Chọn **một** câu R1–R4, điền 6 dòng, rồi biến nó thành **một ablation** chạy được trong lab: giữ nguyên model (MockLLM), tool, seed, corpus và giá, chỉ thay đổi một biến.

| Câu | Nguồn (thư viện tham khảo, slide 68–69) | Câu hỏi gợi ý cho lab |
| --- | --- | --- |
| R1 · Scaling | Google Research 2026, *Towards a Science of Scaling Agent Systems* | Task claims chủ yếu tuần tự hay song song được? Dự đoán thêm investigator sẽ làm pass rate và cost/success thay đổi thế nào. |
| R2 · Failure taxonomy | MAST, NeurIPS 2025, *Why Do Multi-Agent LLM Systems Fail?* | Các trial fail của swarm (seed 55) thuộc nhóm nào: lỗi giao việc, lệch mục tiêu, hay lỗi kiểm chứng? |
| R3 · Architecture choices | AgentArch, AACL 2026 | Nếu đổi topology mà giữ nguyên mọi thứ khác, biến nào phải cố định để kết luận còn đúng? |
| R4 · Evaluation confounders | EMNLP 2026, *Rethinking Evaluation of MAS Efficiency* | Làm sao chứng minh chênh lệch giữa A/B/C/D là do topology, không phải do prompt, tool hay seed? |

## Phiếu của nhóm

Điền vào cột cuối. Không xóa hai cột đầu.

| Field | Hướng dẫn | Nhóm điền |
| --- | --- | --- |
| CÂU | R1 / R2 / R3 / R4 | R3 |
| SOURCE | Paper/blog, năm, URL, loại bằng chứng (benchmark, production report, blog kinh nghiệm) | AgentArch (AACL 2026), tài liệu tham khảo lý thuyết slide 68–69; bằng chứng thực nghiệm trên benchmark có kiểm soát biến |
| CLAIM | Một kết luận gốc của nguồn. Không viết rộng hơn phạm vi paper | Hiệu quả và chi phí của hệ thống agent phụ thuộc trực tiếp vào topology điều phối (workflow, single ReAct, orchestrator, swarm) khi giữ nguyên các thành phần nền |
| BOUNDARY | Model / dataset / setup giới hạn kết luận đó | Áp dụng trong phạm vi task xử lý claim có quy trình xác định trên MockLLM, 14 claim public × 5 seed (`11,22,33,44,55`), bảng giá mô phỏng `config/pricing.yaml` |
| HYPOTHESIS | Nếu đổi shape A→B (hoặc bật/tắt một thành phần), metric X sẽ đổi theo hướng nào, khoảng bao nhiêu | Khi giữ nguyên tool, bảng giá, seed và corpus, chuyển từ `workflow` sang `single` hoặc `orchestrator` sẽ giữ nguyên `pass_rate = 1.000` nhưng làm tăng `cost_per_success_vnd` (khoảng 1.4x–2.0x) và `mean_steps` do phát sinh vòng lặp/handoff |
| METHOD | Biến giữ cố định: model, tools, seed, corpus, giá, evaluator. Biến duy nhất được thay đổi: … | Biến giữ cố định: `MockLLM`, bộ tool đọc/ghi host, 5 seed `[11,22,33,44,55]`, corpus `data/public_claims.jsonl` (14 claim), `config/pricing.yaml`, evaluator `lab8.metrics.trial_pass`. Biến duy nhất thay đổi: topology (`workflow`, `single`, `orchestrator`, `swarm`) |
| FAILURE / METRIC | Một lỗi dự kiến và cách đo nó: pass rate, pass^5, variance, cost/success, leak, bypass | Lỗi dự kiến: `swarm` bị lệch kết quả ở seed 55 (`status resolved != denied` trên `C-002`); đo bằng `pass_rate`, `pass_5`, `seed_variance`, `cost_per_success_vnd`, `mean_steps` trong `src/reports/benchmark.json` |

## Kết quả ablation

- Lệnh đã chạy (copy nguyên văn): `python -m lab8.benchmark --shapes workflow,single,orchestrator,swarm --cases data/public_claims.jsonl --seeds 11,22,33,44,55 --out reports/benchmark.json`
- Run id / file report: `src/reports/benchmark.json` (ví dụ `R-workflow-C-001-s11`, `R-single-C-001-s11`, `R-orchestrator-C-001-s11`, `R-swarm-C-001-s11`)
- Kết quả so với hypothesis (đúng / sai / không kết luận được), kèm số liệu: **Đúng với giả thuyết.** Trên cùng 70 trial/shape: `workflow`, `single`, `orchestrator` đều đạt `pass_rate = 1.000`, `pass_5 = 1.000`, `seed_variance = 0.000000`, nhưng `cost_per_success_vnd` tăng từ `27.86` (`workflow`, `4.43` steps) lên `39.33` (`single`, `8.79` steps) và `57.04` (`orchestrator`, `5.36` steps). Trong khi đó `swarm` giảm xuống `pass_rate = 0.986`, `pass_5 = 0.929`, `seed_variance = 0.000816`, `cost_per_success_vnd = 49.57`.
- Giới hạn: MockLLM không phải model sản xuất, latency là `unavailable`.

Muốn đi xa hơn một ablation để lấy điểm cộng thì xem [docs/bonus_topics.md](../../docs/bonus_topics.md).
