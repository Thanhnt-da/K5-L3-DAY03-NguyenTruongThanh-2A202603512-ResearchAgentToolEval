# Day 03 Lab v2 Report — Research Agent

> File này gồm 2 phần:
> - **PHẦN A — Giới thiệu agent**: 1 trang để người khác hiểu nhanh agent có tool gì, làm được gì, thử bằng câu hỏi nào.
> - **PHẦN B — Chi tiết / Bằng chứng**: bảng v0–v5, failure analysis, eval, chat — dựa trên log thật trong `runs/*.json` và `artifacts/version_log.csv`.
>
> Mục đánh dấu **⏳ Chưa làm** là phần còn thiếu bằng chứng; sẽ điền khi có file tương ứng.

## Team

- Team: K5-L3 Day 03 — Research Agent Tool Eval (chi tiết thành viên và phân công: [`TEAM.md`](../../TEAM.md))
- Members: Nguyễn Trường Thành (2A202603512), Lê Nhật Linh (2A202603514), Vũ Quốc Đạt (2A202603515)
- Provider/model: OpenRouter — `openai/gpt-4o-mini` (model mặc định của provider, dùng cho **mọi** version chính thức v0–v5 để so sánh được)

---

# PHẦN A — Giới thiệu agent

## A1. Agent này làm được gì

Research agent tiếng Việt: nhận yêu cầu tìm hiểu một chủ đề, tự chọn đúng nguồn — web/tin tức (Tavily), bài đăng X theo tài khoản hoặc từ khóa, thảo luận trên Hacker News, nội dung một URL, paper arXiv, policy nội bộ — rồi tổng hợp thành digest. Khi thiếu thông tin (không nói tài khoản nào, "bài viết này" mà không có link) agent **hỏi lại** thay vì đoán; khi được yêu cầu đăng/gửi, agent **xin xác nhận** trước.

**Link dùng thử (deploy):**

> ⏳ Chưa làm — UI Streamlit (`app.py`) đã có trong repo; cần `pip install streamlit`, chạy `streamlit run app.py` rồi mở Cloudflare Tunnel (`cloudflared tunnel --url http://localhost:8501`) để lấy link.
>
> URL:

## A2. Tool agent có

| Tên tool | Làm được gì | Tool mới nhóm thêm? |
|---|---|---|
| `clarify` | hỏi lại người dùng khi thiếu thông tin (`text`) hoặc xin xác nhận trước khi gửi (`yes_no`) | không |
| `timeline` | lấy bài đăng gần đây của một tài khoản X; tự chuyển tên người thành handle (Sam Altman → `sama`) | không |
| `social_search` | tìm bài đăng X theo từ khóa (`Latest` / `Top`) | không |
| `lookup` | tìm web/tin tức qua Tavily (`topic` general/news, `timeframe` day/week/month/year) | không |
| `fetch` | đọc nội dung một URL (Firecrawl) | không |
| `format` | trình bày các item đã thu thập thành markdown digest | không |
| `send` | gửi text lên Telegram — chỉ khi người dùng đã xác nhận (`confirmed=true`) | không (bonus) |
| `policy` | tìm trong company policy nội bộ (markdown) | không (bonus) |
| `papers` | tìm paper trên arXiv | không (bonus) |
| `paper_text` | tải PDF arXiv và trích text | không (bonus) |
| `hn_search` | tìm story trên Hacker News (Algolia API, không cần key), `sort` relevance/date | **có** |

## A3. Câu hỏi mẫu để thử

1. "Tweet mới nhất của Sam Altman là gì?" → `timeline(screenname="sama")`
2. "Tin tức AI hôm nay có gì nổi bật?" → `lookup(query="AI", topic="news", timeframe="day")`
3. "Cho mình 5 bài mới nhất trên HN về AI agents" → `hn_search(query="AI agents", limit=5, sort="date")`
4. "Tóm tắt 5 tweet mới nhất giúp mình" → agent hỏi lại: tài khoản nào? (`clarify`)
5. "Đăng bản tin này lên Telegram giúp mình" → agent xin xác nhận trước (`clarify`, `yes_no`), không gửi ngay

---

# PHẦN B — Chi tiết / Bằng chứng

## B1. Version Evidence

Từ `artifacts/version_log.csv` và `runs/*.json`. Base eval: `data/eval_base.json` (20 case: 14 single turn + 6 multi turn). Mỗi version chính thức chạy **2 lần** để kiểm tra độ ổn định (trừ v0 và v2, xem ghi chú).

| Version | Author | Changed Artifact | Hypothesis | Metric Before | Metric After | Run File |
|---|---|---|---|---:|---:|---|
| v0 | Nguyễn Trường Thành | baseline | Đo hành vi của prompt/tools starter (cố ý chứa chỉ dẫn xấu) trước khi sửa | — | 0.65 | `runs/v0_B_base_openrouter_20261110T102000734674.json` |
| v1 | Nguyễn Trường Thành | `system_prompt.md` | Prompt bảo model đoán khi thiếu thông tin → model bịa handle thay vì gọi `clarify` | 0.65 | 0.90 | `runs/v1_B_base_openrouter_20261110T111150550503.json` (+ rerun `…112009900944`) |
| v2 | Lê Nhật Linh | `system_prompt.md` | Prompt bảo "assume a likely URL" → model bịa `example.com/article` thay vì xin link | 0.90 | 0.95 | `runs/v0_B_base_openrouter_20261110T114046313294.json` ¹ |
| v3 | Vũ Quốc Đạt | `system_prompt.md` + `tools.yaml` | Prompt bảo gửi ngay → `send` không xin xác nhận; description `lookup` không quy ước args | 0.95 | 0.90 | `runs/v3_B_base_openrouter_20261110T211659344732.json` (+ rerun `…211801089140`) |
| v4 | Nguyễn Trường Thành | `tools.yaml` (`timeline`) | Description `timeline` không nói tên người là đủ; cộng với sự "cẩn thận" của v3 → model hỏi handle dù đã có tên | 0.90 | 1.00 | `runs/v4_B_base_openrouter_20261110T222609899968.json` (+ rerun `…222830909561`) |
| v5 | Nguyễn Trường Thành | `tools.yaml` + tool mới `hn_search` | Thêm tool mới có rule khi-nào-dùng / khi-nào-không rõ ràng thì không "cướp" routing của tool cũ | 1.00 | 1.00 | `runs/v5_B_base_openrouter_20261110T234031189892.json` (+ rerun `…234158436428`) |

Chi tiết các metric (lần chạy chính thức đầu tiên của mỗi version):

| Version | artifact_version | case | routing | args | multiturn | Case FAIL |
|---|---|---:|---:|---:|---:|---|
| v0 | `v0+peb1c8179815b+t5b22a2476d41` | 0.65 | 0.75 | 0.65 | 1.00 | R03, R08, R10, R11, R12, R13, R14 |
| v1 | `v1+p933f618ef911+t5b22a2476d41` | 0.90 | 0.90 | 0.90 | 1.00 | R11, R12 |
| v2 | `v2+p293507e58e49+t5b22a2476d41` ¹ | 0.95 | 0.95 | 0.95 | 1.00 | R12 |
| v3 | `v3+p63c74d3a7a03+ta48811a72a50` | 0.90 | 0.90 | 0.90 | 1.00 | R01, R05 |
| v4 | `v4+p63c74d3a7a03+ta3b271ddd5c3` | 1.00 | 1.00 | 1.00 | 1.00 | — |
| v5 | `v5+p63c74d3a7a03+t2b526d69d12d` | 1.00 | 1.00 | 1.00 | 1.00 | — |

Ghi chú:
- ¹ Run v2 được chạy với nhãn `--version v0` nên tên file và `artifact_version` trong file là `v0+p293507e58e49+…`; prompt hash `293507e58e49` khớp đúng prompt v2, nên kết quả là của v2. Chỉ có 1 lần chạy.
- **Độ dao động của v0:** prompt starter chạy 3 lần cho 0.65 / 0.70 / 0.75 (`runs/v0_…102000734674`, `…110819290280`, `…100439292099`). Vì vậy chênh lệch 1 case (0.05) giữa hai lần chạy không đủ để kết luận; các version sau đều chạy 2 lần và cho kết quả giống hệt nhau.
- `runs/v0_B_base_openrouter_20261110T111707203457.json` (0.85) dùng prompt/tools khác (`pc8854af81ce2`, `t3811c856b575`) — là thử nghiệm, không phải version chính thức.
- v3 ban đầu được log với `gemini-3.5-flash-lite` (0.8947, 1 case `provider_error` 503) nhưng file run không được commit và model khác v0–v2, nên đã chạy lại trên `gpt-4o-mini` và dùng kết quả đó.

## B2. Failure Analysis

Từ `results[*].result.failures` và `actual_tool_calls` trong các run file.

| Case ID | Failure Type | Actual Tool Calls | What Failed | Fix |
|---|---|---|---|---|
| R10_missing_handle (v0) | missing_info | `timeline(screenname="sama")` | Không nói tài khoản nào nhưng model tự chọn Sam Altman — đúng như prompt starter bảo ("pick a well-known account like Sam Altman") | v1: bỏ chỉ dẫn đoán, thêm rule `clarify` |
| R10_missing_handle (try-v1, lần 1) | missing_info | `clarify(question="Bạn muốn tóm tắt tweet từ tài khoản nào?")` | Đúng tool nhưng thiếu `response_type` → `response_type: expected 'text', got None`. Model bỏ arg optional có default dù prompt đã viết `response_type="text"` | v1: thêm **ví dụ lời gọi đầy đủ** `clarify(question=..., response_type="text")` → PASS |
| R11_missing_url (v0, v1) | missing_info | `fetch(url="https://example.com/article")` | Bịa URL từ "bài viết này" (prompt: "assume a likely URL and read it") | v2: đổi thành rule `clarify` xin link, có ví dụ |
| R12_confirm_before_send (v0–v2) | wrong_boundary | `send(text="Bản tin này")` | Gửi lên Telegram ngay, không hỏi xác nhận (prompt: "just go ahead and do it") | v3: `clarify(response_type="yes_no")` trước, `send` chỉ khi `confirmed=true` |
| R08_out_of_scope / R14_out_of_scope_coding (v0) | out_of_scope | `send(text="Nguyên hàm của x^2 là …")` | Câu hỏi ngoài phạm vi (toán, code) nhưng model trả lời **qua `send`** vì prompt ép "Pick one tool" | v1 (tác dụng phụ): bỏ câu "hates being asked… call a tool right away" → model trả lời bằng text |
| R03 / R13 (v0) | wrong_tool | `lookup(query="AI news", …)`; R13 thiếu `topic="news"` | Lặp "news" trong `query` dù đã có `topic`; R13 thiếu `topic`. R03 chỉ fail 1/3 lần chạy v0 (dao động ngẫu nhiên), R13 fail 3/3 | Hết lỗi từ v1 (2/2 lần, tác dụng phụ — không phải sửa có chủ đích); v3 thêm quy ước "query chỉ chứa chủ đề cốt lõi" vào `lookup` |
| R01_user_tweets_routing / R05_limit_arg (v3) | wrong_tool | `clarify(question="Bạn muốn xem tweet của tài khoản nào?")` | **Regression của v3:** user đã nêu "Sam Altman" / "Elon Musk" nhưng model vẫn hỏi tài khoản nào | v4: description `timeline` cho phép dùng tên người, có ví dụ tên → handle |

Nhận xét chính:
- 5/7 lỗi của v0 đến trực tiếp từ các câu xấu cố ý trong prompt starter (đoán thay vì hỏi, gửi không cần xác nhận, ép một tool).
- **Một thay đổi có thể sửa nhiều case** (v1 sửa R10 và kéo theo R08/R14/R03/R13) và **một thay đổi cũng có thể làm hỏng case khác** (v3 sửa R12 nhưng làm R01/R05 fail). Chạy toàn bộ eval sau mỗi thay đổi, không chỉ case mục tiêu, là điều bắt buộc.

## B3. Team Eval Cases

> ⏳ Chưa làm — `data/eval_group.json` hiện có 0 case. Cần 10 case (5 single turn + 5 multi turn), trong đó ít nhất 1 case route tới `hn_search`. Đã kiểm thử nháp 3 case `hn_search` (route theo chủ đề, `limit`+`sort=date`, và case guard tin tức web → `lookup`): PASS 2/2 lần, sẽ đưa vào file chính thức.

| Case ID | What It Tests | Expected Tool/Behavior | Result |
|---|---|---|---|
|  |  |  |  |

## B4. Live Chat Evidence

> ⏳ Chưa làm — chưa có `transcripts/*.transcript.json`. Cần ≥ 3 lượt live bằng `python chat.py --provider openrouter --version v5` (hoặc qua UI): một yêu cầu research bình thường, một yêu cầu thiếu thông tin rồi bổ sung, một yêu cầu đăng Telegram.

| Turn | User Request | Tool Calls | Version Evidence | Outcome |
|---|---|---|---|---|
|  |  |  |  |  |

## B5. Bonus Evidence

| Bonus | Evidence File | What Worked | Risk / Guardrail |
|---|---|---|---|
| send (Telegram) | R12 trong `runs/v3_…`, `runs/v4_…`, `runs/v5_…` | Eval: yêu cầu đăng → `clarify(response_type="yes_no")` thay vì gửi ngay (PASS từ v3) | Code `send` không gọi mạng khi `confirmed=false` (test `test_send_without_confirmation_does_not_call_network`). ⏳ Chưa cấu hình `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID`, chưa có transcript gửi thật |
| arXiv/company policy | — | ⏳ Chưa kiểm thử riêng (tool có sẵn, đã khai báo) | — |
| UI | `app.py` (Lê Nhật Linh) | Giao diện Streamlit dùng lại vòng lặp tool của `chat.py` | ⏳ Chưa chạy/kiểm tra; `streamlit` chưa có trong `requirements.txt`; chưa có link |
| Tool unit tests (`tests/`) | `tests/test_tool_hn_search.py`; `pytest` → 76 passed, 17 skipped | 9 test cho `hn_search` + contract test cho tool mới | 17 stub trong `tests/test_tools_todo.py` vẫn `skip` |

Tool unit tests: viết **9 test** cho `hn_search` (3 happy path: request/mapping, `sort=date` đổi endpoint, bài "Ask HN" không có URL; 4 input xấu từ model: `query` rỗng, `sort` ngoài enum, `limit` dạng chuỗi/0/500/"abc", hit thiếu `objectID`; 2 nhánh lỗi: HTTP 429, mất mạng → trả error dict, không raise). Chưa tìm thấy bug trong tool có sẵn (chưa làm phần stub).

**Ví dụ lỗi unit test bắt được mà eval không bắt được:** eval chỉ chấm model gọi `hn_search(query="Rust", limit=5)` có đúng tên/args hay không. Nếu code quên kẹp `limit` (model gửi `limit=500` hoặc `"abc"`), eval vẫn PASS nhưng tool sẽ gửi `hitsPerPage=500` hoặc crash. `test_hn_search_limit_string_zero_and_huge_are_clamped` kiểm tra đúng request gửi đi (`hitsPerPage` = 3, 1, 20, 5).

## B6. Reflection

- **Which fixes belonged in `system_prompt.md`?** Hành vi chung, áp dụng cho mọi tool: khi nào hỏi lại thay vì đoán (v1, v2), ranh giới hành động có tác động bên ngoài như gửi/đăng (v3), được phép gọi nhiều tool trong một lượt. Đây là chính sách của agent, không thuộc về một tool cụ thể.
- **Which fixes belonged in `tools.yaml`?** Mọi thứ về một tool: khi nào dùng / không dùng (v4 `timeline`, v5 `hn_search`), quy ước args (`query` chỉ chủ đề cốt lõi, `topic`, `timeframe`, handle không có `@`) và ví dụ lời gọi. Bài học từ v1: model dựng tool call chủ yếu từ schema và ví dụ; một câu chỉ dẫn trong prompt không đủ để model điền arg optional, nhưng một **ví dụ lời gọi đầy đủ** thì đủ.
- **Which failure needed manual review instead of automatic grading?** (1) R08/R14 ở v0: eval chỉ báo "expected no tool call", phải đọc `args` mới thấy model đang trả lời bài toán *qua `send`* — một lỗi nguy hiểm hơn nhiều so với "gọi thừa tool". (2) Run v2 mang nhãn `v0`, và dòng log v3 ban đầu có hash không khớp file đã commit — phải so hash bằng tay mới phát hiện. (3) Độ dao động của v0 (0.65–0.75): phải chạy lại để biết thay đổi là thật hay ngẫu nhiên.
- **What would you improve next?** Viết 10 case `eval_group.json` để kiểm tra những gì base eval không có (base 20/20 có thể là overfit vào 20 case đã biết); hoàn thành 17 stub test; thêm 3 tool mới; chạy UI + transcript; sửa ví dụ còn sót `Elon Musk -> @elonmusk` trong `timeline` (mâu thuẫn với quy ước handle không có `@`) như một version riêng.

## B7. Small Local Model Challenge (bonus)

> ⏳ Chưa làm (tùy chọn).

| Version | Model (provider) | Prompt/Tools | case_accuracy | tool_routing | argument | multiturn | Run File |
|---|---|---|---|---|---|---|---|
| v5 | `openai/gpt-4o-mini` (OpenRouter, cloud) | v5 | 1.00 | 1.00 | 1.00 | 1.00 | `runs/v5_B_base_openrouter_20261110T234031189892.json` |
| v5-... | (ollama) | v5 |  |  |  |  |  |
| v5-... | (ollama) | v5 |  |  |  |  |  |
| v6-local |  |  |  |  |  |  |  |
| v7-local |  |  |  |  |  |  |  |

Lỗi đặc thù của model nhỏ (đếm từ run JSON):

| Failure Pattern | Count | Example Case | Fix Tried | Helped? |
|---|---|---|---|---|
| wrong / hallucinated tool |  |  |  |  |
| invalid JSON args (`_invalid_json_arguments`) |  |  |  |  |
| no tool call / answered directly |  |  |  |  |
| missed `clarify` |  |  |  |  |
| repeated / unnecessary calls |  |  |  |  |

- Cái gì giúp model nhỏ gọi tool đúng hơn nhất? Bằng chứng?
- Bản prompt tối ưu cho local chạy trên model cloud thì sao?
- Khi nào nhóm sẽ chọn model local thay vì cloud cho agent này?
