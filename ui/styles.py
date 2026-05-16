"""Custom CSS for the ChatBI Streamlit UI."""
CUSTOM_CSS = """
<style>
    /* Chat container */
    .stApp {
        max-width: 100%;
    }
    .main-header {
        background: #1e4969;
        color: white;
        padding: 1.5rem 2rem;
        margin: -3rem -3rem 2rem -3rem;
        border-radius: 0;
    }
    .main-header h1 {
        color: white !important;
        font-size: 1.8rem;
        margin: 0;
    }
    .main-header p {
        color: #b8d4e8;
        margin: 0.3rem 0 0 0;
        font-size: 0.9rem;
    }

    /* Chat bubbles */
    .chat-bubble {
        padding: 1rem 1.2rem;
        border-radius: 0.8rem;
        margin-bottom: 0.8rem;
        max-width: 85%;
        line-height: 1.6;
    }
    .chat-bubble.user {
        background: #e8f0f7;
        margin-left: auto;
        border-bottom-right-radius: 0.2rem;
    }
    .chat-bubble.assistant {
        background: #f6f2eb;
        margin-right: auto;
        border-bottom-left-radius: 0.2rem;
    }
    .chat-bubble .msg-label {
        font-size: 0.7rem;
        font-weight: 600;
        color: #8b7355;
        margin-bottom: 0.3rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .chat-bubble.user .msg-label {
        color: #1e4969;
    }

    /* SQL expander */
    .sql-expander {
        border: 1px solid #d0dde8;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .sql-expander .streamlit-expanderHeader {
        font-size: 0.8rem;
        color: #507a9c;
    }
    .sql-expander code {
        background: #f0f6fa;
        padding: 0.8rem;
        border-radius: 0.3rem;
        display: block;
        font-size: 0.8rem;
        white-space: pre-wrap;
    }

    /* Status badge */
    .status-badge {
        display: inline-block;
        padding: 0.15rem 0.5rem;
        border-radius: 0.3rem;
        font-size: 0.7rem;
        font-weight: 600;
    }
    .status-badge.online { background: #d4edda; color: #155724; }
    .status-badge.offline { background: #f8d7da; color: #721c24; }
    .status-badge.active { background: #d4edda; color: #155724; }
    .status-badge.pending { background: #fff3cd; color: #856404; }

    /* Metrics row */
    .metric-card {
        background: #f0f6fa;
        border-radius: 0.5rem;
        padding: 1rem;
        text-align: center;
    }
    .metric-card .num {
        font-size: 1.6rem;
        font-weight: 700;
        color: #1e4969;
    }
    .metric-card .label {
        font-size: 0.75rem;
        color: #8b8070;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: #f6f2eb;
    }
    section[data-testid="stSidebar"] .stButton button {
        width: 100%;
        background: #1e4969;
        color: white;
        border: none;
    }
    section[data-testid="stSidebar"] .stButton button:hover {
        background: #153a54;
    }

    /* Data table */
    .dataframe-container {
        overflow-x: auto;
        margin: 0.5rem 0;
    }
    .dataframe-container table {
        font-size: 0.8rem;
    }
</style>
"""

# Page config
PAGE_CONFIG = {
    "page_title": "ChatBI - 智慧家庭AI运营系统",
    "page_icon": "🤖",
    "layout": "wide",
    "initial_sidebar_state": "expanded",
}
