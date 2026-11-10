# Team — Day 03 Lab: Research Agent Tool Eval

| Họ và tên | MSSV | GitHub | Mô tả công việc |
|---|---|---|---|
| Nguyễn Trường Thành | 2A202603512 | Thanhnt-da | Setup môi trường + chạy baseline `v0`; `v1` (R10: bỏ chỉ dẫn "đoán thay vì hỏi", thêm rule `clarify` có ví dụ); chạy lại `v3` trên `gpt-4o-mini` và sửa dòng log; `v4` (R01/R05: description `timeline` cho phép dùng tên người → handle); `v5` + tool mới `hn_search` (Hacker News) kèm 9 unit test; quản lý repo, `version_log.csv` và `REPORT.md`. |
| Lê Nhật Linh | 2A202603514 | Le Nhat Linh | `v2` (R11: hỏi lại URL bằng `clarify` thay vì tự đoán link); UI Streamlit `app.py`; fallback đọc tool call dạng text trong `chat.py` / `agent.py`. |
| Vũ Quốc Đạt | 2A202603515 | datvq | `v3` (R12: xin xác nhận `yes_no` trước khi `send`; viết lại description `clarify` / `lookup` / `send` với quy ước args và ví dụ). |

Provider / model dùng cho các version chính thức: OpenRouter, `openai/gpt-4o-mini`.
