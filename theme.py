# theme.py — global UI theme + sidebar brand block + scroll to top button
import os, base64
import streamlit as st
import streamlit.components.v1 as components

APP_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGES_DIR = os.path.join(APP_DIR, "images")

PRIMARY_RED = "#e33b3b"
PRIMARY_RED_DARK = "#c62f2f"
PRIMARY_RED_LIGHT = "#ff4d4d"
ACCENT = "#f7f7f9"
TEXT = "#1f2937"
TEXT_LIGHT = "#6b7280"
SUCCESS = "#10b981"
WARNING = "#f59e0b"
ERROR = "#ef4444"
INFO = "#3b82f6"
RADIUS = "12px"
SHADOW_SM = "0 1px 3px rgba(0,0,0,0.12)"
SHADOW_MD = "0 4px 6px rgba(0,0,0,0.1)"
SHADOW_LG = "0 10px 15px rgba(0,0,0,0.1)"
FONT = "'Arial', system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, 'Apple Color Emoji', 'Segoe UI Emoji'"

def _b64(path: str) -> str | None:
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception:
        return None

def inject_theme() -> None:
    st.markdown(
        f"""
        <style>
        :root {{
            --primary-red: {PRIMARY_RED};
            --primary-red-dark: {PRIMARY_RED_DARK};
            --aid-divider: rgba(227,59,59,.35);
        }}
        
        html, body, [class^="block-container"] {{ font-family: {FONT} !important; color: {TEXT}; }}
        .main .block-container {{ padding-top: 0.9rem; overflow: visible; }}

        /* RED THEMED DIVIDERS - all hr elements */
        hr {{ 
            border: 0; 
            border-top: 2px solid var(--aid-divider) !important;
            margin: 1.5rem 0 !important;
        }}

        /* Sidebar styling */
        section[data-testid="stSidebar"] > div:first-child {{ 
            background: {PRIMARY_RED}; 
            color: #fff; 
            min-height: 100vh; 
        }}
        section[data-testid="stSidebar"] .sidebar-content {{ padding: 0.75rem 0.9rem 1.25rem 0.9rem; }}
        section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3, section[data-testid="stSidebar"] label,
        section[data-testid="stSidebar"] a, section[data-testid="stSidebar"] p,
        section[data-testid="stSidebar"] span:not(input):not(textarea) {{ color: #fff !important; }}
        section[data-testid="stSidebar"] input, section[data-testid="stSidebar"] textarea {{
          color: {TEXT} !important; background: #fff !important;
        }}

        /* Navigation buttons */
        .aid-nav .stButton > button {{
          display: block;
          justify-content: flex-start;
          text-align: left;
          background: rgba(255,255,255,.08);
          color:#fff;
          border: 1px solid rgba(255,255,255,.15);
          border-radius: 16px;
          padding: .65rem .9rem;
          font-weight: 600;
          width: 100%;
          transition: all 0.2s ease;
        }}
        .aid-nav .stButton > button:hover {{
          background: rgba(255,255,255,.18);
          transform: translateY(-1px);
        }}

        /* Primary buttons */
        .stButton > button {{
          background: {PRIMARY_RED}; 
          color: #fff; 
          border: 0; 
          border-radius: {RADIUS};
          padding: 0.55rem 0.9rem; 
          font-weight: 600; 
          font-size: 0.95rem; 
          transition: all .2s; 
          box-shadow: 0 1px 0 rgba(0,0,0,.04);
        }}
        .stButton > button:hover {{
            background: linear-gradient(135deg, {PRIMARY_RED_DARK} 0%, #a82525 100%);
            transform: translateY(-2px);
            box-shadow: {SHADOW_LG};
        }}
        .stButton > button:focus {{
            outline: none;
            box-shadow: 0 0 0 3px rgba(227, 59, 59, 0.3);
        }}

        /* Enhanced tabs with red accent */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 0.5rem;
            border-bottom: 2px solid var(--aid-divider);
            padding-bottom: 0;
        }}
        .stTabs [data-baseweb="tab"] {{
            padding: 0.75rem 1.25rem;
            border-radius: 8px 8px 0 0;
            background: transparent;
            color: {TEXT_LIGHT};
            font-weight: 600;
            transition: all 0.2s ease;
        }}
        .stTabs [data-baseweb="tab"]:hover {{
            background: rgba(227, 59, 59, 0.05);
            color: {PRIMARY_RED};
        }}
        .stTabs [aria-selected="true"] {{
            border-bottom: 3px solid {PRIMARY_RED};
            color: {PRIMARY_RED} !important;
            background: rgba(227, 59, 59, 0.08);
        }}

        /* ENHANCED TABLES - Red accent header */
        div[data-testid="stDataFrame"] {{ 
            border: 1px solid #ececf1; 
            border-radius: {RADIUS}; 
            overflow: hidden; 
        }}
        div[data-testid="stDataFrame"] thead tr th {{
            background: linear-gradient(135deg, rgba(227,59,59,.12) 0%, rgba(227,59,59,.08) 100%);
            color: {TEXT};
            font-weight: 700;
            padding: 0.75rem 0.5rem;
            border-bottom: 2px solid rgba(227,59,59,.25);
        }}
        div[data-testid="stDataFrame"] tbody tr:nth-child(even) {{
            background: rgba(247,247,249,0.5);
        }}
        div[data-testid="stDataFrame"] tbody tr:hover {{
            background: rgba(227,59,59,0.04);
        }}

        /* Input fields */
        .stTextInput input, .stNumberInput input, .stTextArea textarea {{ 
            border-radius: {RADIUS} !important; 
        }}

        /* Header styling */
        .aid-header-title {{ 
            font-weight: 800; 
            font-size: 1.25rem; 
            letter-spacing:.2px; 
            white-space:nowrap; 
        }}
        .aid-header {{
          display:flex; 
          align-items:center; 
          gap:.75rem;
          padding:.4rem 0 .9rem 0;
          min-height: 40px;
          overflow: visible;
        }}

        /* Alerts */
        .stAlert > div {{ border-radius: {RADIUS}; }}

        /* File uploader */
        section[data-testid="stFileUploaderDropzone"] {{
          border-radius: {RADIUS} !important; 
          border-color: var(--aid-divider) !important;
          background: rgba(227,59,59,.03) !important;
        }}

        /* Images as cards */
        .stImage img {{ 
            border-radius: 16px !important; 
            box-shadow: 0 6px 20px rgba(0,0,0,.06); 
        }}
        [data-testid="StyledFullScreenButton"] {{ display: none !important; }}

        /* Sidebar brand block */
        .aid-brand {{ 
            display:flex;
            align-items:center;
            gap:.6rem;
            margin:.35rem 0 1rem 0; 
        }}
        .aid-brand .aid-logo {{
          width:38px;
          height:38px;
          border-radius:8px;
          background:#fff;
          display:inline-block;
          box-shadow: 0 1px 0 rgba(0,0,0,.1);
        }}
        .aid-brand .aid-title {{ 
            font-weight:800;
            font-size:1rem;
            line-height:1; 
        }}
        .aid-brand .aid-sub {{ 
            opacity:.85;
            font-size:.8rem;
            line-height:1;
            margin-top:2px; 
        }}
        
        /* KPI boxes */
        .kpi {{
            background: linear-gradient(135deg, #fff 0%, #f9fafb 100%);
            border: 1px solid #e5e7eb;
            border-radius: 12px;
            padding: 1rem;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }}
        .kpi h3 {{
            font-size: 0.875rem;
            color: {TEXT_LIGHT};
            margin: 0 0 0.5rem 0;
            font-weight: 600;
        }}
        .kpi p {{
            font-size: 1.75rem;
            font-weight: 800;
            color: {PRIMARY_RED};
            margin: 0;
        }}

        /* SCROLL TO TOP BUTTON STYLES */
        #scrollTopBtn {{
            position: fixed;
            bottom: 30px;
            right: 30px;
            z-index: 9999;
            background: {PRIMARY_RED};
            color: white;
            border: none;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            font-size: 24px;
            cursor: pointer;
            box-shadow: {SHADOW_LG};
            opacity: 0;
            visibility: hidden;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
        }}
        
        #scrollTopBtn.show {{
            opacity: 1;
            visibility: visible;
        }}
        
        #scrollTopBtn:hover {{
            background: {PRIMARY_RED_DARK};
            transform: translateY(-3px);
            box-shadow: 0 12px 20px rgba(227, 59, 59, 0.3);
        }}
        
        #scrollTopBtn:active {{
            transform: translateY(-1px);
        }}
        </style>
        """, 
        unsafe_allow_html=True,
    )

def add_scroll_to_top_button() -> None:
    """Add scroll to top button - only for admin/coordinator"""
    # Check if user is logged in and is admin or coordinator
    user = st.session_state.get("user")
    if not user:
        return
    
    role = user.get("role", "")
    if role not in ("admin", "coordinator"):
        return
    
    # Add anchor at the very top
    st.markdown('<span id="top"></span>', unsafe_allow_html=True)
    
    # Add smaller button with white arrow
    st.markdown("""
    <style>
    .scroll-top-btn {
        position: fixed;
        bottom: 30px;
        right: 30px;
        z-index: 99999;
        background: linear-gradient(135deg, #e33b3b 0%, #c62f2f 100%);
        color: white !important;
        width: 48px;
        height: 48px;
        border-radius: 14px;
        text-align: center;
        line-height: 48px;
        font-size: 22px;
        font-weight: 600;
        cursor: pointer;
        box-shadow: 0 6px 20px rgba(227, 59, 59, 0.3);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        text-decoration: none !important;
        display: flex;
        align-items: center;
        justify-content: center;
        border: 1px solid rgba(255, 255, 255, 0.15);
    }
    .scroll-top-btn:hover {
        background: linear-gradient(135deg, #c62f2f 0%, #a82525 100%);
        transform: translateY(-4px) scale(1.05);
        box-shadow: 0 10px 28px rgba(227, 59, 59, 0.45);
        color: white !important;
    }
    .scroll-top-btn:active {
        transform: translateY(-2px) scale(1.02);
    }
    .scroll-top-btn:visited {
        color: white !important;
    }
    </style>
    
    <a href="#top" class="scroll-top-btn">↑</a>
    """, unsafe_allow_html=True)

def sidebar_brand(_translate) -> None:
    logo_path = os.path.join(IMAGES_DIR, "AidBot.png")
    b64 = _b64(logo_path) if os.path.exists(logo_path) else None
    if b64:
        st.sidebar.markdown(
            f"""
            <div class="aid-brand">
              <img class="aid-logo" src="data:image/png;base64,{b64}" />
              <div>
                <div class="aid-title">AidBot</div>
                <div class="aid-sub">Disaster Response</div>
              </div>
            </div>
            <hr style="border-color: rgba(255,255,255,.25)">
            """, 
            unsafe_allow_html=True,
        )
    else:
        st.sidebar.markdown(
            """
            <div style="display:flex;align-items:center;gap:.6rem;margin:.35rem 0 1rem 0;">
              <div style="width:38px;height:38px;display:flex;align-items:center;justify-content:center;
                          background:#fff;color:#e33b3b;border-radius:8px;font-weight:900;">+</div>
              <div style="line-height:1">
                <div style="font-weight:800;font-size:1rem;">AidBot</div>
                <div style="opacity:.85;font-size:.8rem;">Disaster Response</div>
              </div>
            </div>
            <hr style="border-color: rgba(255,255,255,.25)">
            """, 
            unsafe_allow_html=True,
        )

    with st.sidebar.container(border=False):
        st.markdown('<div class="aid-nav">', unsafe_allow_html=True)
        def _nav_btn(label: str, route: str, key: str):
            if st.button(label, key=key):
                st.session_state["route"] = route
                st.rerun()
        lang = st.session_state.get("lang", "en")
        _nav_btn(f"🏥  {_translate('Home', lang)}", "home", "nav_home")
        _nav_btn(f"💬  {_translate('Chat with Us', lang)}", "chat", "nav_chat")
        _nav_btn(f"🆘  {_translate('First Aid', lang)}", "first_aid", "nav_firstaid")
        _nav_btn(f"⛑️  {_translate('Red Cross Information', lang)}", "red_cross", "nav_rcinfo")
        _nav_btn(f"ℹ️  {_translate('About Us', lang)}", "about", "nav_about")
        _nav_btn(f"📩  {_translate('Contact Us', lang)}", "contact", "nav_contact")
        _nav_btn(f"🚨  {_translate('Emergency Form', lang)}", "victim", "nav_victim")
        if "user" in st.session_state and st.session_state["user"]:
            _nav_btn(f"👤  {_translate('My Profile', lang)}", "profile", "nav_profile")
            _nav_btn(f"🔔  {_translate('Notifications', lang)}", "notifications", "nav_notifications")


    st.sidebar.markdown(
        '<div style="margin-top:1.25rem;opacity:.8;font-size:.8rem;">©️ AidBot</div>',
        unsafe_allow_html=True,
    )