"""Streamlit UI components for ChatBI."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
import pandas as pd


def render_metric_row():
    """Show quick overview metrics in a row of cards."""
    import sqlite3
    from config import SQLITE_DB_PATH

    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cur = conn.cursor()
        total_devices = cur.execute("SELECT COUNT(*) FROM devices").fetchone()[0]
        online_devices = cur.execute("SELECT COUNT(*) FROM devices WHERE status='online'").fetchone()[0]
        pending_orders = cur.execute("SELECT COUNT(*) FROM service_orders WHERE status='pending'").fetchone()[0]
        total_users = cur.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        conn.close()
    except Exception:
        total_devices = online_devices = pending_orders = total_users = 0

    cols = st.columns(4)
    with cols[0]:
        st.markdown(f'<div class="metric-card"><div class="num">{total_devices:,}</div><div class="label">设备总数</div></div>', unsafe_allow_html=True)
    with cols[1]:
        st.markdown(f'<div class="metric-card"><div class="num">{online_devices:,}</div><div class="label">在线设备</div></div>', unsafe_allow_html=True)
    with cols[2]:
        st.markdown(f'<div class="metric-card"><div class="num">{pending_orders:,}</div><div class="label">待处理工单</div></div>', unsafe_allow_html=True)
    with cols[3]:
        st.markdown(f'<div class="metric-card"><div class="num">{total_users:,}</div><div class="label">用户总数</div></div>', unsafe_allow_html=True)


def render_chat_message(role: str, content: str, data: pd.DataFrame | None = None,
                        sql: str | None = None):
    """Render a single chat message with optional data and SQL expander."""
    css_class = "user" if role == "user" else "assistant"
    label = "你" if role == "user" else "ChatBI"

    with st.chat_message(role):
        st.markdown(f'<div class="chat-bubble {css_class}">'
                    f'<div class="msg-label">{label}</div>'
                    f'{content}</div>',
                    unsafe_allow_html=True)

        if sql:
            with st.expander("🔍 查看SQL", expanded=False):
                st.code(sql, language="sql")

        if data is not None and not data.empty:
            _render_data_result(data)


def _render_data_result(df: pd.DataFrame):
    """Render query result as table + auto-chart."""
    tab_table, tab_chart = st.tabs(["📊 数据表格", "📈 图表"])

    with tab_table:
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.caption(f"共 {len(df)} 行")

    with tab_chart:
        _auto_chart(df)


def _auto_chart(df: pd.DataFrame):
    """Auto-detect and render bar/line chart based on data shape."""
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    str_cols = df.select_dtypes(include=["object", "string"]).columns.tolist()

    if len(numeric_cols) < 1 or len(df) < 2:
        st.info("数据量不足以生成图表")
        return

    x_col = None
    y_col = numeric_cols[0]

    # Pick x-axis: use first string column if available
    if len(str_cols) > 0:
        x_col = str_cols[0]
    else:
        x_col = df.columns[0]

    try:
        chart_df = df.set_index(x_col) if x_col in df.columns else df
        if y_col in chart_df.columns:
            st.bar_chart(chart_df[y_col])
            st.caption(f"X: {x_col} / Y: {y_col}")
    except Exception:
        st.info("无法生成图表，数据类型不匹配")
