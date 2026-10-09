import streamlit as st
import streamlit_authenticator as stauth
from supabase_client import supabase

# Import only the leads component for now
from components.leads import render_leads
from components.checklist import render_checklist

# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="Roofing CRM",
    page_icon="📞",
    layout="wide",
    initial_sidebar_state="collapsed"
)


# =========================================================
# USER AUTHENTICATION SETUP (Compatible with v0.3+)
# =========================================================

credentials = {
    "usernames": {
        "govind": {
            "name": "govind",
            "password": "roofing123"
        },
        "sales": {
            "name": "Sales",
            "password": "sales123"
        }
    }
}

authenticator = stauth.Authenticate(
    credentials,
    cookie_name="roofing_crm_cookie",
    cookie_key="signature_key_98765",
    cookie_expiry_days=30
)

authenticator.login("main")

authentication_status = st.session_state.get("authentication_status")
name = st.session_state.get("name")
username = st.session_state.get("username")

if authentication_status == False:
    st.error("❌ Username or password is incorrect.")
    st.stop()
elif authentication_status == None:
    st.info("🔒 Please enter your credentials to access the Roofing CRM.")
    st.stop()


# =========================================================
# CUSTOM CSS & RESPONSIVE ADAPTIVE STYLING
# =========================================================

st.markdown(
    """
    <style>
    /* Clean System Font */
    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }

    /* Main Background */
    .stApp {
        background-color: #F8FAFC;
    }

    /* Hide sidebar */
    section[data-testid="stSidebar"] {
        display: none !important;
    }

    header[data-testid="stHeader"] {
        background-color: transparent !important;
    }

    /* Fluid container spacing for all devices */
    .block-container {
        padding-top: 1.2rem !important;
        padding-bottom: 3rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 1400px;
    }

    /* Responsive typography & cards */
    .main-title {
        font-size: clamp(20px, 2.5vw, 26px);
        font-weight: 700;
        color: #0F172A;
        margin-bottom: 2px;
    }

    .main-subtitle {
        color: #64748B;
        font-size: clamp(12px, 1.5vw, 13px);
        margin-bottom: 16px;
    }

    .stButton > button {
        background-color: #0F172A !important;
        color: #FFFFFF !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
        font-size: 13px !important;
        border: none !important;
        padding: 6px 14px !important;
    }

    .stButton > button:hover {
        background-color: #1E293B !important;
    }

    .stTextInput > div > div > input {
        border-radius: 6px !important;
        border: 1px solid #CBD5E1 !important;
        background-color: #FFFFFF !important;
        font-size: 13px !important;
        padding: 8px 12px !important;
    }

    div[data-testid="stDataFrame"] {
        border: 1px solid #E2E8F0 !important;
        border-radius: 6px !important;
    }

    hr {
        border-color: #E2E8F0 !important;
        margin: 12px 0 !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)


# =========================================================
# TOP BAR USER INFO & LOGOUT
# =========================================================

top_col1, top_col2 = st.columns([6, 4])
with top_col1:
    st.markdown("<div style='font-size: clamp(18px, 2vw, 22px); font-weight: 800; color: #0F172A;'>📞 Roofing CRM</div>", unsafe_allow_html=True)
with top_col2:
    u_col1, u_col2 = st.columns([3, 1])
    with u_col1:
        st.markdown(f"<div style='text-align: right; font-size: 13px; font-weight: 600; padding-top: 6px; color: #0F172A;'>👤 {name}</div>", unsafe_allow_html=True)
    with u_col2:
        authenticator.logout("Logout", "main")

st.divider()

# =========================================================
# HORIZONTAL NAVIGATION TABS
# =========================================================

tab_dashboard, tab_leads, tab_checklist, tab_calling, tab_followups, tab_hot, tab_reports, tab_settings = st.tabs([
    "🏠 Dashboard",
    "📋 Leads",
    "☑️ Daily Checklist",  # <--- New Tab added here
    "📞 Cold Calling",
    "🔄 Follow-ups",
    "🔥 Hot Leads",
    "📊 Reports",
    "⚙️ Settings"
])

with tab_dashboard:
    st.info("Dashboard component coming soon.")

with tab_leads:
    with st.spinner("Loading leads directory..."):
        response = supabase.table("leads").select("*").execute()
        leads = response.data or []
    render_leads(leads)

with tab_checklist:  # <--- New Tab Content
    render_checklist()

with tab_calling:
    st.info("Cold Calling component coming soon.")

with tab_followups:
    st.info("Follow-ups component coming soon.")

with tab_hot:
    st.info("Hot Leads component coming soon.")

with tab_reports:
    st.info("Reports component coming soon.")

with tab_settings:
    st.info("Settings component coming soon.")