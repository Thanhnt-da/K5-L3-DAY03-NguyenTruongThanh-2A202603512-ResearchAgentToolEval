import json
from pathlib import Path
import streamlit as st

from env_loader import load_lab_env
from providers import make_provider
from tools import load_tool_declarations, to_openai_tools
from chat import run_model_tool_loop

ROOT = Path(__file__).parent
load_lab_env(ROOT)

st.set_page_config(
    page_title="AI Research Agent Demo",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS supporting both Light and Dark mode
st.markdown("""
<style>
    .main-title {
        font-size: 1.8rem;
        font-weight: 700;
        margin-bottom: 0.1rem;
    }
    .badge-status {
        background-color: rgba(46, 125, 50, 0.2);
        color: #4caf50;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 600;
        display: inline-block;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- Khởi tạo Provider & Tools -----------------
@st.cache_resource
def get_agent_resources():
    provider = make_provider("openrouter")
    tools_decl = load_tool_declarations(ROOT / "artifacts" / "tools.yaml")
    tools = to_openai_tools(tools_decl)
    return provider, tools, tools_decl

try:
    provider, tools, tools_decl = get_agent_resources()
except Exception as e:
    st.error(f"Lỗi khởi tạo provider/tools: {e}")
    st.stop()

TOOL_ICONS = {
    "clarify": "💬",
    "timeline": "🐦",
    "social_search": "🔍",
    "lookup": "🌐",
    "fetch": "📄",
    "format": "📑",
    "send": "📢",
    "policy": "📚",
    "papers": "🎓",
    "paper_text": "📜",
}

def get_system_prompt() -> str:
    prompt_file = ROOT / "artifacts" / "system_prompt.md"
    if prompt_file.exists():
        return prompt_file.read_text(encoding="utf-8")
    return "You are a helpful research assistant."

def reset_chat():
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Xin chào! Tôi là **AI Research Agent**. Tôi có thể giúp bạn tra cứu tin tức web, đọc bài đăng Twitter/X, tải nội dung bài viết và tổng hợp dữ liệu. Hãy nhập yêu cầu của bạn nhé!",
            "tool_events": []
        }
    ]

# Khởi tạo tin nhắn nếu chưa có
if "messages" not in st.session_state:
    reset_chat()

# ----------------- Sidebar -----------------
with st.sidebar:
    # Nút Cuộc trò chuyện mới nổi bật trên cùng
    if st.button("➕ Cuộc trò chuyện mới", use_container_width=True, type="primary"):
        reset_chat()
        st.rerun()

    st.divider()
    st.subheader("⚙️ Thông tin hệ thống")
    st.markdown("**Provider:** `OpenRouter`")
    st.markdown("**Model:** `openai/gpt-4o-mini`")
    st.markdown("**Trạng thái:** 🟢 `Online`")

    st.divider()
    st.caption("AI Research Agent • Day 03 Lab v2")

# ----------------- Header chính -----------------
col1, col2 = st.columns([0.8, 0.2])
with col1:
    st.markdown('<div class="main-title">🔍 AI Research Agent Demo</div>', unsafe_allow_html=True)
    st.markdown('<span class="badge-status">● Live Demo • Multi-turn Tool Calling</span>', unsafe_allow_html=True)
with col2:
    if st.button("🔄 Làm mới chat", use_container_width=True):
        reset_chat()
        st.rerun()

# ----------------- Render lịch sử hội thoại -----------------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg.get("tool_events"):
            with st.expander(f"🔧 Đã thực thi {len(msg['tool_events'])} lượt gọi công cụ", expanded=False):
                for event in msg["tool_events"]:
                    tool_name = event.get("tool")
                    args = event.get("args")
                    result = event.get("result")
                    icon = TOOL_ICONS.get(tool_name, "📌")
                    st.markdown(f"{icon} **Công cụ:** `{tool_name}`")
                    st.caption("Tham số đầu vào:")
                    st.code(json.dumps(args, ensure_ascii=False, indent=2), language="json")
                    st.caption("Kết quả:")
                    st.code(str(result)[:500] + ("..." if len(str(result)) > 500 else ""), language="text")
                    st.divider()
        st.markdown(msg["content"])

# ----------------- Nhận tin nhắn từ User -----------------
user_input = st.chat_input("Nhập yêu cầu nghiên cứu của bạn...")

if user_input:
    # 1. Thêm và render tin nhắn của User
    st.session_state.messages.append({"role": "user", "content": user_input, "tool_events": []})
    with st.chat_message("user"):
        st.markdown(user_input)

    # 2. Xây dựng prompt & danh sách messages
    system_prompt = get_system_prompt()
    working_messages = [{"role": "system", "content": system_prompt}]
    for m in st.session_state.messages:
        working_messages.append({"role": m["role"], "content": m["content"]})

    # 3. Chạy vòng lặp Agent
    with st.chat_message("assistant"):
        with st.status("Agent đang phân tích câu hỏi và điều phối Tools...", expanded=True) as status:
            result = run_model_tool_loop(
                provider=provider,
                messages=working_messages,
                tools=tools,
                model=None,
                max_tool_rounds=4,
            )

            tool_events = result.get("tool_events", [])
            if tool_events:
                st.write(f"Đã gọi **{len(tool_events)}** công cụ:")
                for event in tool_events:
                    icon = TOOL_ICONS.get(event.get('tool'), '📌')
                    st.code(f"{icon} {event.get('tool')}({json.dumps(event.get('args', {}), ensure_ascii=False)})", language="python")

            if result.get("status") == "waiting_for_user":
                status_label = "💬 Agent cần hỏi thêm thông tin (Clarify)..."
            else:
                status_label = "✅ Đã tổng hợp xong kết quả!"
            status.update(label=status_label, state="complete", expanded=False)

        reply_text = result.get("assistant_text", "")
        st.markdown(reply_text)

        # Lưu tin nhắn Assistant vào lịch sử
        st.session_state.messages.append({
            "role": "assistant",
            "content": reply_text,
            "tool_events": tool_events,
        })
