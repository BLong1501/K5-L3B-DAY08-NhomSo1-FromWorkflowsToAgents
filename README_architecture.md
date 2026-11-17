# Kiến trúc repo — Lab 8 LogiX-VN (một task, bốn kiến trúc)

Tài liệu này giải thích toàn bộ repo: mỗi thư mục làm gì, một claim đi qua hệ thống thế nào, bốn shape khác nhau ra sao, host chặn ghi tiền thế nào, và các công cụ đo chấm cái gì. Mỗi phần có một đoạn giải thích ngắn và một sơ đồ Mermaid (GitHub tự vẽ).

> **Một câu:** khách gửi ticket xin hoàn phí; một trong bốn *shape* (A workflow, B single agent, C orchestrator, D swarm) đọc dữ liệu và đề xuất số tiền; **host** (code có sẵn) là cửa duy nhất được ghi tiền vào ledger SQLite, sau khi kiểm approval, trần theo đơn và idempotency.

---

## 1. Bản đồ thư mục

Repo chia ba lớp: **đề bài và báo cáo** ở gốc, **code** trong `src/`, **tài liệu tham khảo** trong `docs/`. Mọi lệnh chạy trong `src/`.

```mermaid
flowchart TB
  root["Repo gốc"]
  root --> docsRoot["README · RULES · CHECKPOINTS · RUBRIC · SUBMISSION · TEAM.md"]
  root --> docs["docs/<br/>business_rules · contracts · architecture · metrics · bonus · troubleshooting"]
  root --> report["report/team/<br/>group_report · decision_adr · research_card · MSSV_HoTen"]
  root --> ci[".github/workflows/ci.yml<br/>smoke + pytest + crash + benchmark swarm"]
  root --> src["src/"]

  src --> lab8["lab8/ — code chính"]
  src --> config["config/ — giá, policy tự chủ, manifest tool<br/>(thước đo, không sửa)"]
  src --> data["data/ — world + 14 claim public<br/>(thước đo, không sửa)"]
  src --> tests["tests/ — cổng host + ma trận student T01–T14"]
  src --> reports["reports/ — crash.json, benchmark.json<br/>(do lệnh sinh, không sửa tay)"]
  src --> audit["grader_audit/ — 3 grader ứng viên (bonus B7)"]

  lab8 --> shapes["shapes/ — workflow · single · orchestrator · swarm_reference · common"]
  lab8 --> host["Host: durability · policy · db"]
  lab8 --> libs["Thư viện: tools · runtime · handoff · mock_llm · trace · schemas · compensation"]
  lab8 --> clis["CLI: smoke · run · benchmark · crash_test · check_submission"]
```

| Thư mục / file | Vai trò | Ai sửa |
| --- | --- | --- |
| `src/lab8/shapes/workflow.py`, `single.py`, `orchestrator.py` | Ba shape nhóm viết | Nhóm |
| `src/lab8/shapes/swarm_reference.py` | Shape D có sẵn, để đối chứng | Không sửa |
| `src/lab8/durability.py`, `policy.py`, `metrics.py`, `config/`, `data/` | Host và thước đo | **Không sửa** |
| `src/lab8/tools.py`, `runtime.py`, `handoff.py`, `trace.py`, `mock_llm.py` | Thư viện dùng chung | Dùng, không cần sửa |
| `src/tests/` | Test host và test student; mỗi người thêm test của mình | Nhóm thêm |
| `report/team/`, `TEAM.md` | Báo cáo, ADR, bảng đóng góp | Nhóm |

---

## 2. Các module ghép với nhau thế nào

Shape chỉ được **đọc** qua `tools` và chỉ được **ghi** qua `durability.issue_refund`. MockLLM chỉ trả chữ và tính chi phí giả lập, không quyết định gì.

```mermaid
flowchart LR
  subgraph Shapes["Shape (nhóm viết)"]
    A["A workflow"]
    B["B single"]
    C["C orchestrator"]
    D["D swarm_reference"]
  end

  subgraph Lib["Thư viện"]
    tools["tools.py<br/>read tools + allowlist"]
    runtime["runtime.py<br/>run_react ≤ 8 bước<br/>run_readonly_investigators"]
    handoff["handoff.py<br/>make_handoff + sanitize"]
    llm["mock_llm.py<br/>complete() theo seed"]
    comp["compensation.py<br/>quote() tất định"]
    trace["trace.py<br/>Trace → JSON"]
    common["shapes/common.py<br/>finish() → RunResult"]
  end

  subgraph Host["Host (thước đo)"]
    dur["durability.py<br/>issue_refund"]
    pol["policy.py<br/>authorize"]
    db[("SQLite store")]
  end

  A & B & C & D --> tools
  B --> runtime
  C --> handoff --> runtime
  runtime --> tools
  tools --> comp
  A & B & C & D -.chữ, chi phí.-> llm
  A & B & C & D --> common --> trace
  A & B & C & D ==ghi tiền==> dur
  dur --> pol
  dur --> db
  tools --> db
  common --> db
```

**Giải thích ngắn từng module:**

- `tools.py`: tool đọc. `lookup_order` chỉ trả 7 field an toàn (không SĐT, địa chỉ, tên hàng, ghi chú nội bộ) và tự chặn principal không sở hữu đơn. `lookup_policy` chỉ trả policy `is_current` và đã có hiệu lực. `compute_compensation` gọi `compensation.quote`.
- `compensation.py`: luật tiền. Trễ ≥ 3 ngày thì hoàn phí ship; hỏng hàng đã verify thì `min(max_refund, paid)`; cả hai cùng đủ điều kiện thì lấy **số lớn hơn**, không cộng.
- `runtime.py`: vòng ReAct có trần bước, và bộ chạy investigator chỉ đọc. Worker gọi tool ghi thì bị `ToolRejected`.
- `handoff.py`: gói chuyển việc giữa các agent, lọc bằng allowlist trong code. Còn sót `CANARY_SECRET_`, `parent_secret`, header hay tool ghi thì báo lỗi.
- `mock_llm.py`: model giả, cùng seed và prompt thì ra cùng chữ. Chỉ để tính token và chi phí.
- `common.finish()`: dựng `RunResult`, tự đọc ledger để điền `refund_effects` và `committed_audit_count`, tự ghi trace.
- `durability.py` + `policy.py`: host. Xem mục 5.

---

## 3. Vòng đời một claim (luật nghiệp vụ chung cho mọi shape)

Dù shape nào, kết quả đúng phải theo cùng một cây quyết định. Nguồn sự thật là dòng order và policy hiện hành; chữ trong ticket chỉ là dữ liệu người dùng.

```mermaid
flowchart TD
  start(["run_claim(claim_id, seed, store_path, crash_at)"]) --> view["Đọc claim qua get_claim_view"]
  view -->|không tồn tại| F1["failed · proposal 0"]
  view --> hasOrder{"Có order_id?"}
  hasOrder -->|không| NI["needs_info · proposal 0<br/>không lấy mã đơn từ ticket"]
  hasOrder -->|có| lookup["lookup_order(order_id, principal)"]
  lookup -->|không thấy / không phải chủ| ES["escalated · proposal 0<br/>không lộ SĐT, địa chỉ"]
  lookup -->|thấy| quote["compute_compensation<br/>chỉ policy hiện hành"]
  quote -->|quote = 0| DN0["denied · proposal 0<br/>không gọi host"]
  quote -->|quote > 0| host["durability.issue_refund<br/>(quote đầy đủ, crash_at)"]
  host -->|từ chối: approval hỏng, sai claim,<br/>đơn đã hoàn đủ| DN["denied · proposal = quote<br/>audit policy_denied"]
  host -->|gọi lại, số tiền khác| FL["failed · giữ dòng cũ<br/>audit conflict"]
  host -->|chấp nhận| RS["resolved · proposal = quote<br/>1 dòng ledger + 1 audit refund_committed"]
```

Mọi nhánh đều phải ghi trace đúng contract v1 (file JSON của chính lần chạy, `run_id` khớp, có `events`). Grader fail-closed nếu thiếu hoặc sai trace.

---

## 4. Bốn shape: cùng việc, mức tự chủ khác nhau

Cả bốn có chung chữ ký `run_claim` và cùng gọi một cửa host. Khác nhau ở **ai chọn bước tiếp theo** và **bao nhiêu lời gọi model**.

```mermaid
flowchart LR
  subgraph A["A · workflow — ít tự chủ nhất"]
    a1["get_claim_view"] --> a2["lookup_order"] --> a3["compute_compensation"] --> a4["issue_refund"]
  end

  subgraph B["B · single — một agent ReAct"]
    b0["decide()"] -->|chọn tool đọc| b1["dispatch tool"] --> b0
    b0 -->|final hoặc 8 bước| b2["code gọi issue_refund"]
  end

  subgraph C["C · orchestrator — điều phối + investigator"]
    c0["orchestrator plan"] --> c1["make_handoff<br/>allowlist, 4 tool đọc"] --> c2["investigators<br/>chỉ đọc"] --> c3["orchestrator gọi issue_refund"]
  end

  subgraph D["D · swarm — các peer trao đổi"]
    d0["peer + parse ticket"] --> d1["investigators"] --> d2["seed % 5 == 0:<br/>tin số ngày trong ticket ⚠"] --> d3["issue_refund"]
  end
```

| Shape | Ai chọn bước | Model làm gì | Ai quyết tiền | Rủi ro chính |
| --- | --- | --- | --- | --- |
| A workflow | Code, bước cố định | Không gọi model | Code + host | Cứng; ticket lạ cần người xử lý |
| B single | Model, vòng ReAct ≤ 8 bước | Chọn tool đọc | Code + host | Vượt trần bước, thêm chi phí |
| C orchestrator | Code giao việc cho investigator | Lập kế hoạch + soạn chữ | Code + host | Handoff lộ dữ liệu nếu không dùng allowlist |
| D swarm | Các peer bàn nhau | Nhiều lời gọi, có lúc tin ticket | Host chặn ở cửa cuối | Dao động theo seed (`REFERENCE_WEAKNESS`) |

### Shape C chi tiết (sequence)

```mermaid
sequenceDiagram
  autonumber
  participant O as Orchestrator
  participant L as MockLLM
  participant H as make_handoff
  participant I as Investigators (chỉ đọc)
  participant DB as SQLite
  participant HO as Host issue_refund
  participant T as Trace

  O->>DB: get_claim_view(claim_id)
  O->>T: claim {has_order_id}
  alt thiếu order_id
    O->>T: decision needs_info
  else có order_id
    O->>L: complete(purpose="plan")
    O->>H: claim_id, task, facts={}, 4 tool đọc
    H-->>O: handoff đã sanitize
    O->>T: handoff (đã sanitize)
    O->>I: run_readonly_investigators(handoff)
    I->>DB: lookup_order · lookup_policy · lookup_refund_history · compute_compensation
    I-->>O: order view (allowlist) + quote
    O->>T: investigator (field allowlist) + quote
    alt không thấy đơn
      O->>T: decision escalated
    else quote = 0
      O->>T: decision denied
    else quote > 0
      O->>HO: issue_refund(claim_id, quote đầy đủ, crash_at)
      HO-->>O: ok / denied / conflict
      O->>T: host + decision
    end
  end
  O->>L: complete(purpose="draft")
  O->>DB: finish(): đọc ledger → RunResult
```

---

## 5. Host: cửa ghi tiền duy nhất

`durability.issue_refund` là nơi duy nhất ghi ledger. Nó gọi `policy.authorize` để kiểm approval và tính số được ghi, rồi ghi **dòng ledger và audit `refund_committed` trong cùng một transaction**. Khóa idempotency là `refund:{claim_id}` (claim_id cũng là khóa chính của ledger), nên gọi lại hay crash rồi chạy lại vẫn chỉ có một refund.

```mermaid
flowchart TD
  in(["issue_refund(claim_id, quote, crash_at)"]) --> c1{"Claim có order_id,<br/>principal sở hữu đơn?"}
  c1 -->|không| pd1["policy_denied"]
  c1 -->|có| already["already = tổng đã hoàn của đơn<br/>(claim khác)"]
  already --> auth["policy.authorize"]
  auth --> a1{"approval_id của claim tồn tại?"}
  a1 -->|không| pd2["policy_denied: missing_approval"]
  a1 --> a2{"approval cấp cho đúng claim?"}
  a2 -->|không| pd3["policy_denied: approval_claim_mismatch"]
  a2 --> a3{"status valid, chưa hết hạn, > 0?"}
  a3 -->|không| pd4["policy_denied: revoked / expired / non_positive"]
  a3 --> cap["amount = quote − already<br/>= min(amount, approved, paid − already)"]
  cap -->|≤ 0| pd5["policy_denied: order_already_refunded"]
  cap -->|> 0| crash1{{"crash_at = before_effect?"}}
  crash1 --> exist{"Claim đã có dòng ledger?"}
  exist -->|có, cùng số| replay["idempotent_replay → ok"]
  exist -->|có, khác số| conflict["amount_conflict → giữ số cũ"]
  exist -->|chưa| tx["BEGIN IMMEDIATE<br/>đọc lại tổng của đơn<br/>INSERT refund_ledger + audit refund_committed<br/>COMMIT"]
  tx --> crash2{{"crash_at = after_effect_before_checkpoint?"}}
  crash2 --> ckpt["checkpoint"]
  ckpt --> crash3{{"crash_at = after_checkpoint?"}}
  crash3 --> ok(["ok: committed"])
```

**Vì sao shape phải truyền quote đầy đủ:** host tự trừ phần đã hoàn của đơn (`already`). Nếu shape trừ trước thì bị trừ hai lần. Ví dụ T14: đơn `O-515` đã hoàn ship 30.000, nay hỏng hàng (entitlement 150.000) → shape truyền 150.000, host ghi 120.000, `proposal_amount` vẫn là 150.000.

**Vì sao checkpoint không đủ:** crash sau khi ghi ledger nhưng trước checkpoint thì checkpoint không biết đã ghi. Ledger với khóa duy nhất mới bảo đảm lần chạy lại không ghi thêm (demo: `python -m lab8.demo.buggy_workflow`).

---

## 6. Dữ liệu (SQLite)

Mỗi trial có một file SQLite riêng (trừ test gọi lại). Các bảng in đậm chứa dữ liệu nhạy cảm mà shape **không được** ghi ra trace.

```mermaid
erDiagram
  CLAIMS ||--o| ORDERS : "order_id"
  CLAIMS ||--o| APPROVALS : "approval_id"
  APPROVALS }o--|| CLAIMS : "claim_id (phải khớp)"
  CLAIMS ||--o| REFUND_LEDGER : "tối đa 1 dòng"
  ORDERS ||--o{ REFUND_LEDGER : "trần theo đơn"
  CLAIMS ||--o{ AUDIT_EVENTS : "refund_committed / policy_denied"
  CLAIMS ||--o{ CHECKPOINTS : "step"

  CLAIMS {
    text claim_id PK
    text principal_id
    text order_id
    text ticket "dữ liệu người dùng"
    text parent_secret "CANARY - cấm ghi"
    text raw_headers_json "cấm ghi"
    text approval_id
  }
  ORDERS {
    text order_id PK
    text principal_id
    text status
    int delay_days
    int shipping_fee_vnd
    int paid_vnd
    int damage_verified
    text carrier
    text phone "PII - cấm ghi"
    text address "PII - cấm ghi"
    text internal_note "cấm ghi"
    text item_name "cấm ghi"
  }
  APPROVALS {
    text approval_id PK
    text claim_id
    int approved_vnd
    text status
    text expires_at
  }
  REFUND_LEDGER {
    text claim_id PK
    text order_id
    text idempotency_key UK "refund:claim_id"
    int amount_vnd
    text status "committed"
  }
  AUDIT_EVENTS {
    text audit_key PK
    text claim_id
    text event_type
    text details_json
  }
  POLICIES {
    text policy_id PK
    text version
    int is_current
    text effective_date
    text clauses_json
  }
  CHECKPOINTS {
    text claim_id
    text step
    text result_json
  }
```

---

## 7. Ranh giới bảo mật

Ba lớp chặn dữ liệu nhạy cảm, đều nằm trong **code**, không dựa vào việc model "tự biết giữ bí mật".

```mermaid
flowchart LR
  raw[("Claim row + order row thô<br/>parent_secret, header, SĐT, địa chỉ")]
  raw -->|get_claim_view / lookup_order<br/>allowlist field| safe["View an toàn"]
  safe -->|make_handoff + sanitize<br/>allowlist field + chỉ tool đọc| ho["Handoff handoff.v1"]
  ho --> inv["Investigator"]
  safe --> tr["Trace JSON"]
  ho --> tr
  tr -->|grader quét CANARY_SECRET_,<br/>forbid_substrings| grade{"Sạch?"}
  grade -->|không| fail["trial fail"]
  grade -->|có| pass["tiếp tục chấm"]
```

- Tóm tắt bằng LLM **không** tính là redaction; chỉ allowlist trong code mới tính.
- Trace là ranh giới bảo mật: grader đọc `trace_path` và mọi file `<run_id>*` cùng thư mục.
- Chữ trong ticket ("ignore policy", "trễ 9 ngày") là dữ liệu, không phải lệnh.

---

## 8. Đo và chấm

Có bốn công cụ, mỗi cái trả lời một câu hỏi khác.

```mermaid
flowchart LR
  data["data/public_claims.jsonl<br/>14 claim + nhãn"] --> bench["lab8.benchmark<br/>4 shape × 14 claim × 5 seed<br/>mỗi trial một SQLite riêng"]
  bench --> metrics["metrics.trial_pass<br/>status · proposal · ledger · audit · trace · secret"]
  metrics --> summ["metrics.summarize<br/>pass rate · pass^5 · seed variance · cost/success"]
  summ --> bj["reports/benchmark.json"]

  crash["lab8.crash_test<br/>20 điểm crash"] --> cj["reports/crash.json<br/>crash_safety 20/20"]
  tests["pytest -q<br/>cổng host"] --> green["phải luôn xanh"]
  stud["pytest -m student<br/>T01–T14 × 4 shape"] --> perShape["62 test / shape"]

  bj & cj & green --> check["lab8.check_submission<br/>0 FAIL"]
  check --> hidden["Grader giảng viên<br/>40 claim hidden × 5 seed<br/>shape chọn ≥ 0.75"]
```

| Metric | Nghĩa |
| --- | --- |
| pass rate | Tỉ lệ trial pass |
| pass^5 | Tỉ lệ claim pass cả 5 seed |
| seed variance | Độ dao động pass rate giữa các seed |
| cost/success | Chi phí giả lập (VND) chia số trial pass |

**Số đo hiện tại** (`src/reports/benchmark.json`, 14 claim × 5 seed, MockLLM, giá giả lập):

| Shape | Pass rate | pass^5 | Seed variance | Cost/success (VND) |
| --- | --- | --- | --- | --- |
| workflow | 1.000 | 1.000 | 0 | 27.9 |
| single | 1.000 | 1.000 | 0 | 39.3 |
| orchestrator | 1.000 | 1.000 | 0 | 57.0 |
| swarm | 0.986 | 0.929 | 0.0008 | 49.6 |

Swarm trượt đúng một trial (seed 55, `resolved` thay vì `denied`) vì tin số ngày trễ trong ticket. Ba shape nhóm viết cùng đạt 100%; workflow rẻ nhất vì không gọi model. Đây là dữ kiện cho ADR: chọn kiến trúc **ít tự chủ nhất mà vẫn làm được việc**.

---

## 9. Lệnh thường dùng (chạy trong `src/`)

```bash
python -m lab8.smoke                                   # kiểm môi trường
python -m pytest -q                                    # cổng host, phải xanh
python -m pytest -q -m student -o addopts= -k orchestrator   # 62 test của một shape
python -m lab8.run --shape orchestrator --claim-id C-001 --seed 11 --db data/run.sqlite
python -m lab8.crash_test --count 20 --out reports/crash.json
python -m lab8.benchmark --shapes workflow,single,orchestrator,swarm --cases data/public_claims.jsonl --seeds 11,22,33,44,55 --out reports/benchmark.json
python -m lab8.check_submission                        # phải ra 0 FAIL
```

Xem thêm: [docs/business_rules.md](docs/business_rules.md), [docs/contracts.md](docs/contracts.md), [docs/metrics.md](docs/metrics.md), [docs/architecture.md](docs/architecture.md).
