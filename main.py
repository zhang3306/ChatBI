"""ChatBI — 智慧家庭AI运营系统 · Streamlit 入口

启动方式：
    streamlit run main.py
"""
import sys
from pathlib import Path

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
from ui.styles import CUSTOM_CSS, PAGE_CONFIG
from ui.components import render_chat_message, render_metric_row

st.set_page_config(**PAGE_CONFIG)
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ── Header ─────────────────────────────────────────────────────
st.markdown(
    '<div class="main-header">'
    '<h1>ChatBI - 智慧家庭AI运营系统</h1>'
    '<p>用自然语言查询千万级运营数据 — Text2SQL + RAG + Agent</p>'
    '</div>',
    unsafe_allow_html=True,
)

# ── Session state init ──────────────────────────────────────────
if "agent" not in st.session_state:
    st.session_state.agent = None
if "messages" not in st.session_state:
    st.session_state.messages = []


def _init_system(api_key: str):
    """Initialize the full ChatBI system."""
    import os
    os.environ["DEEPSEEK_API_KEY"] = api_key

    from sql.generator import SQLGenerator
    from sql.executor import SQLExecutor
    from rag.vector_store import VectorStore
    from rag.retriever import Retriever
    from agent.conversation import ConversationAgent

    vs = VectorStore()
    retriever = Retriever(vs)
    generator = SQLGenerator(retriever)
    executor = SQLExecutor()

    agent = ConversationAgent(generator, executor)
    st.session_state.agent = agent


def _process_query(query: str):
    """Process user query through the agent."""
    if not st.session_state.agent:
        st.session_state.messages.append({
            "role": "assistant",
            "content": "请先在左侧栏输入 API Key 并点击「初始化系统」。",
        })
        st.rerun()
        return

    agent = st.session_state.agent
    with st.spinner("Analyzing..."):
        result = agent.chat(query)

    st.session_state.messages.append({
        "role": "assistant",
        "content": result["response"],
        "data": result["data"],
        "sql": result["sql"],
    })


# ── Sidebar ─────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ 配置")

    api_key = st.text_input(
        "DeepSeek API Key",
        type="password",
        help="从 platform.deepseek.com 获取",
        value=st.session_state.get("api_key", ""),
    )
    st.session_state.api_key = api_key

    if st.button("[Init] 初始化系统", use_container_width=True):
        if not api_key:
            st.warning("请先输入 API Key")
        else:
            _init_system(api_key)
            st.success("系统初始化完成！")

    if st.button("[Clear] 清空对话", use_container_width=True):
        st.session_state.messages = []
        if st.session_state.agent:
            st.session_state.agent.clear_memory()
            from agent.tools import _last_query_data
            _last_query_data["data"] = None
            _last_query_data["sql"] = ""
        st.rerun()

    st.divider()
    st.markdown("### 💡 示例问题")
    examples = [
        "设备总量、在线量、报错量概览",
        "各城市的设备数量排名",
        "安防类设备有多少",
        "待处理工单数量",
        "最近7天每日事件趋势",
        "各类型工单数量分布",
        "北京有多少在线设备",
        "报警最多的设备TOP20",
    ]
    for q in examples:
        if st.button(f"  {q}", use_container_width=True, key=f"ex_{q}"):
            st.session_state.pending_query = q

    st.divider()
    st.caption("v1.0 · DeepSeek + LangChain + Chroma + Streamlit")


# ── Show DB metrics ─────────────────────────────────────────────
try:
    render_metric_row()
except Exception:
    pass  # DB not seeded yet

# ── Chat history ────────────────────────────────────────────────
for msg in st.session_state.messages:
    render_chat_message(
        role=msg["role"],
        content=msg["content"],
        data=msg.get("data"),
        sql=msg.get("sql"),
    )

# ── Check pending query from sidebar ────────────────────────────
if "pending_query" in st.session_state and st.session_state.pending_query:
    query = st.session_state.pending_query
    st.session_state.pending_query = ""
    st.session_state.messages.append({"role": "user", "content": query})
    _process_query(query)
    st.rerun()

# ── Chat input ──────────────────────────────────────────────────
if prompt := st.chat_input("输入你的问题，例如「北京有多少在线设备？」"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    _process_query(prompt)
    st.rerun()
