# app.py — AidBot dashboard (routing, analytics, admin tools, cases)

import os, io, re, json, datetime as dt
from math import ceil
import pandas as pd
import numpy as np
import altair as alt
import streamlit as st
import pydeck as pdk
from sklearn.metrics import accuracy_score, confusion_matrix
import streamlit as st
from simulate_alerts import simulate_future_prediction
from get_weather import get_weather_data
from blood_forecaster import BloodDemandForecaster

try:
    import joblib  # optional (only needed if you place a trained model)
except Exception:
    joblib = None

from theme import inject_theme, sidebar_brand, add_scroll_to_top_button
from login import login_page, admin_user_panel, SKILL_OPTIONS

from db import (
    init_db,
    # users
    list_users, list_volunteers, get_user, update_user_profile, update_user, delete_user,
    # notifications
    add_notification, list_notifications, mark_all_read,
    # cases
    create_case, list_cases, assign_case, update_case_status, get_case,
    # shelters
    list_shelters, create_shelter, update_shelter, delete_shelter, _next_numeric_id,
    # blood & resources
    read_blood_df, write_blood_df, read_resources_df, write_resources_df,
    # blood via DB helpers
    list_blood, create_blood, update_blood, delete_blood,
    # Ops Planner + Audit
    write_preposition_plan, list_preposition_plans, list_audit,
    # Contact messages
    create_contact_message, list_contact_messages
)

# ---------------- Bootstraps & constants ----------------
init_db()

APP_DIR    = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(APP_DIR, "uploads")
IMAGES_DIR = os.path.join(APP_DIR, "images")
MODELS_DIR = os.path.join(APP_DIR, "models")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)

LOGO_PATH = os.path.join(IMAGES_DIR, "AidBot.png")
DEFAULT_AVATAR = os.path.join(IMAGES_DIR, "default_avatar.png")
SAMPLE_CSV = os.path.join(APP_DIR, "sample_predictions.csv")
MAPBOX_TOKEN = os.getenv("MAPBOX_TOKEN", "")

st.set_page_config(page_title="AidBot — Disaster Response Dashboard", page_icon="images/AidBot.svg", layout="wide")

inject_theme()
add_scroll_to_top_button()

# === UI helpers (styling + compact tables & pagination) ======================
st.markdown("""
<style>
:root{
  --primary-red:#e33b3b;
  --primary-red-dark:#c52d2d;
  --primary-red-light:#f87171;
}

/* Header layout */
.aid-header { 
  margin-bottom: 1.5rem; 
  padding-bottom: 1rem;
}

.aid-header-title {
  font-size: 1.5rem;
  font-weight: 600;
  color: #111827;
}

/* Actions container */
.aid-actions{ 
  display: flex; 
  align-items: center; 
  justify-content: flex-end; 
  gap: 8px;
  margin-top: 8px;
}

/* Style all buttons in the actions area */
.aid-actions .stButton > button {
  border-radius: 6px !important;
  padding: 6px 14px !important;
  height: 36px !important;
  font-size: 0.875rem !important;
  line-height: 1.25rem !important;
  white-space: nowrap !important;
  font-weight: 500 !important;
  transition: all 0.2s ease !important;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05) !important;
}

/* Primary red buttons (Notifications and Profile) */
.aid-actions [data-testid="column"]:nth-child(1) button,
.aid-actions [data-testid="column"]:nth-child(2) button {
  background-color: var(--primary-red) !important;
  color: white !important;
  border: none !important;
}

.aid-actions [data-testid="column"]:nth-child(1) button:hover,
.aid-actions [data-testid="column"]:nth-child(2) button:hover {
  background-color: var(--primary-red-dark) !important;
  transform: translateY(-1px) !important;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1) !important;
}

/* Logout button - outline style */
.aid-actions [data-testid="column"]:nth-child(3) button {
  background-color: white !important;
  color: var(--primary-red) !important;
  border: 1.5px solid var(--primary-red) !important;
}

.aid-actions [data-testid="column"]:nth-child(3) button:hover {
  background-color: #fef2f2 !important;
  border-color: var(--primary-red-dark) !important;
  color: var(--primary-red-dark) !important;
  transform: translateY(-1px) !important;
}

/* KPI cards */
.kpi-grid{ 
  display: grid; 
  grid-template-columns: repeat(4, minmax(0,1fr)); 
  gap: 12px;
  margin: 1rem 0;
}

.kpi{ 
  background: #fff; 
  border: 1px solid #e5e7eb; 
  border-radius: 8px; 
  padding: 16px 18px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.kpi h3{ 
  margin: 0 0 6px 0; 
  font-size: 0.875rem; 
  color: #6b7280;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.025em;
}

.kpi p{ 
  margin: 0; 
  font-size: 2rem; 
  font-weight: 700; 
  color: #111827; 
}

.aid-signed { 
  color: #6b7280; 
  margin-top: 8px;
  font-size: 0.875rem;
}
.aid-signed { 
  color: #6b7280; 
  margin-top: 8px;
  font-size: 0.875rem;
}

/* ADD THIS NEW SECTION HERE ↓↓↓ */
/* Table header styling - RED THEME */
div[data-testid="stDataFrame"] thead tr th,
div[data-testid="stDataFrame"] thead th,
div[data-testid="stDataFrame"] table thead tr th,
div[data-testid="stDataFrame"] table thead th {
  background-color: var(--primary-red) !important;
  color: white !important;
  font-weight: 600 !important;
  border-bottom: 2px solid var(--primary-red-dark) !important;
  padding: 12px 8px !important;
}

div[data-testid="stDataFrame"] tbody tr:nth-child(even) {
  background-color: #fafafa !important;
}

div[data-testid="stDataFrame"] tbody tr:hover {
  background-color: var(--primary-red-light) !important;
  transition: background-color 0.2s ease !important;
}
/* ADD ABOVE THIS LINE ↑↑↑ */

/* Responsive adjustments */
@media (max-width: 1200px){
  .aid-actions { gap: 6px; }
  
/* Responsive adjustments */
@media (max-width: 1200px){
  .aid-actions { gap: 6px; }
  .aid-actions .stButton > button { 
    padding: 5px 10px !important; 
    font-size: 0.8125rem !important;
    height: 32px !important;
  }
}
</style>
""", unsafe_allow_html=True)

# --- Clickable-HTML navigation support (logo/title -> Home) ---
def _read_query_params():
    try:
        # Streamlit ≥ 1.30
        qp = dict(st.query_params)
    except Exception:
        # Older Streamlit
        qp = st.experimental_get_query_params()
    return {k: (v[0] if isinstance(v, list) else v) for k, v in qp.items()}

def _clear_query_params():
    try:
        st.query_params.clear()             # Streamlit ≥ 1.30
    except Exception:
        st.experimental_set_query_params()  # Older Streamlit

_q = _read_query_params()
if _q.get("go") == "home":
    st.session_state["route"] = "home"
    _clear_query_params()

def _auto_height(n_rows: int, row_h: int = 36, head: int = 42,
                 min_h: int = 140, max_h: int = 420) -> int:
    """Compute a tidy dataframe height so you don't see lots of empty rows."""
    n = max(1, int(n_rows))
    return max(min_h, min(head + row_h * n, max_h))

def _paginate(items: list, key_prefix: str, page_size: int = 10):
    """Return (page_items, cur, pages, key_name, total)."""
    total = len(items)
    pages = max(1, (total + page_size - 1)//page_size)
    key_page = f"{key_prefix}_page"
    cur = st.session_state.get(key_page, 1)
    if cur > pages: cur = pages
    start = (cur-1) * page_size
    end   = min(start + page_size, total)
    return items[start:end], cur, pages, key_page, total

def _pager(cur: int, pages: int, key_page: str, center_note: str = ""):
    """Render Previous / Page X of Y / Next."""
    if pages <= 1:
        if center_note:
            st.markdown(f"<div style='text-align:center'>{center_note}</div>", unsafe_allow_html=True)
        return
    col1, col2, col3 = st.columns([0.3, 0.4, 0.3])
    with col1:
        if cur > 1 and st.button("← Previous", key=f"{key_page}_prev"):
            st.session_state[key_page] = cur - 1; st.rerun()
    with col2:
        st.markdown(
            f"<div style='text-align:center'>Page {cur} of {pages}{(' — ' + center_note) if center_note else ''}</div>",
            unsafe_allow_html=True
        )
    with col3:
        if cur < pages and st.button("Next →", key=f"{key_page}_next"):
            st.session_state[key_page] = cur + 1; st.rerun()
# ============================================================================

def _keep_open(cid: str):
    st.session_state["active_case_id"] = cid

def _safe_filename(name: str, maxlen: int = 80) -> str:
    base = re.sub(r"[^A-Za-z0-9._-]", "_", name or "")
    root, ext = os.path.splitext(base)
    return (root[: maxlen - len(ext)] + ext.lower()).lstrip("._")

# ---------- SIMPLE NAV HISTORY (for universal ← Back to Home) ----------
def go(new_route: str, **page_state):
    cur = st.session_state.get("route", "home")
    if new_route != cur:
        st.session_state.setdefault("back_stack", []).append(cur)
    for k, v in page_state.items():
        st.session_state[k] = v
    st.session_state["route"] = new_route
    if new_route == "home":
        st.session_state["_route_hist"] = []
        st.session_state["_last_route"] = "home"
    st.rerun()

def back_button():
    """Back to Home button - always goes to home"""
    if st.session_state.get("route", "home") != "home":
        if st.button("← Back to Home", key=f"back_home_{st.session_state.get('route')}"):
            st.session_state["route"] = "home"
            st.rerun()

# ---------- Assets helpers ----------
def _image_path(name: str) -> str | None:
    path = os.path.join(IMAGES_DIR, name)
    return path if os.path.exists(path) else None

def _first_existing_image(names: list[str]) -> str | None:
    for n in names:
        p = _image_path(n)
        if p:
            return p
    return None

# ---------- Translations ----------
_LANGS = {"English": "en", "Burmese": "my"}

def _translate(en_text: str, lang: str) -> str:
    table = {
        "my": {
            # Home & Navigation
            "Welcome to AidBot": "AidBot မှကြိုဆိုပါသည်",
            "Get help fast. First-aid, disaster tips, shelters, and contact helpers.": "အကူအညီကို လွယ်ကူမြန်ဆန် ရယူပါ — First-aid, ဘေးအန္တရာယ်အကြောင်း အကြံဉာဏ်များ၊ ခိုလှုံရေးတည်နေရာများ၊ ဆက်သွယ်ရန်။",
            "First-Aid Guide": "ရှေးဦးသူနာပြု",
            "Red Cross Info": "ကယ်ဆယ်ရေး",
            "Chat with Us": "စာအကူညီရယူပါ",
            "Emergency Form": "အရေးပေါ် ဖောင်",
            "Case Status": "အမှုကိစ္စ အခြေအနေ",
            "Volunteer with Us": "ကျွန်ုပ်တို့နှင့်အတူ စေတနာ့ဝန်ထမ်းလုပ်ပါ။",
            "Volunteer / Coordinator Login": "Volunteer / Coordinator Login",
            "Contact Us": "ဆက်သွယ်ရန်",
            "About AidBot": "AidBot အကြောင်း",
            "Choose language": "ဘာသာစကား ရွေးချယ်ပါ",
            "Back to Home": "ပင်မစာမျက်နှာသို့ ပြန်သွားရန်",

            #SideBar
            "Home": "ပင်မစာမျက်နှာ",
            "First Aid": "ရှေးဦးသူနာပြု",
            "Chat with Us": "ကျွန်ုပ်တို့နှင့် စကားပြောပါ",
            "Red Cross Information": "ကြက်ခြေနီအချက်အလက်", 
            "About Us": "ကျွန်ုပ်တို့ အကြောင်း",
            "Contact Us": "ကျွန်ုပ်တို့ကို ဆက်သွယ်ပါ",
            "Emergency Form": "အရေးပေါ် ဖောင်",
            
            # Buttons & Actions
            "Send": "Chat ပို့ပါ",
            "Clear Chat": "Chat ရှင်းပါ",
            "Save": "သိမ်းဆည်းပါ",
            "Delete": "ဖျက်ပါ",
            "Apply": "လျှောက်ထားပါ",
            "Create": "ဖန်တီးပါ",
            "Update": "အပ်ဒိတ်လုပ်ပါ",
            "Search": "ရှာဖွေပါ",
            "Filter": "စစ်ထုတ်ပါ",
            "Download": "ဒေါင်းလုပ်လုပ်ပါ",
            "Back to Home": "ပင်မစာမျက်နှာသို့ သွားပါ",
            
            # Dashboard
            "Dashboard": "ဒက်ရှ်ဘုတ်",
            "Notifications": "အသိပေးချက်",
            "My Profile": "ကျွန်ုပ်၏ပရိုဖိုင်",
            "Logout": "အကောင့်ထွက်ရန်",
            "Cases": "အမှုကိစ္စများ",
            "Shelters": "ခိုလှုံနေရာများ",
            "Blood Inventory": "သွေးဘဏ် စာရင်း",
            "Resource Allocation": "အရင်းအမြစ် ခွဲဝေမှု",
            
            # Messages
            "Thanks! Our coordinators will review and respond.": "ကျေးဇူးတင်ပါတယ်။ ညှိနှိုင်းသူများက ပြန်လည်တုံ့ပြန်ပါမည်။",
            "No notifications.": "အသိပေးချက်များ မရှိပါ။",
            "No cases.": "အမှုကိစ္စများ မရှိပါ။",
            "No shelters yet.": "ခိုလှုံနေရာများ မရှိသေးပါ။",
            
            # Safety tips (subset)
            "This may be an emergency. Call local emergency services immediately. If trained, begin CPR and keep the person safe until help arrives.": "ပြင်းထန်သော အရေးအခင် ဖြစ်နိုင်ပါသည်။ ဒေသီယ် အရေးပေါ်အကူအညီကို ချက်ချင်း ခေါ်ဆိုပါ။ သင်တန်းရောက်ပြီးသားဖြစ်ပါက CPR စတင်လုပ်ဆောင်ပါ။",
            "Apply firm pressure with a clean cloth for at least 10 minutes. Elevate the area if possible. If bleeding is severe or won't stop, seek medical help.": "သန့်ရှင်းသော အဝတ်ဖြင့် အနည်းဆုံး ၁၀ မိနစ် ခိုင်မာစွာ ဖိထားပါ။ ဖြစ်နိုင်လျှင် မြှင့်ထားပါ။ မရပ်တန်မှု/ပြင်းထန်လျှင် ဆေးဘက်ဝင်အကူအညီ ရှာပါ။",
            "Cool the burn under clean running water for at least 10 minutes. Do not apply ice, butter, or ointments. Cover loosely with a clean, dry dressing.": "ဒဏ်ရာကို ရေစီးလှုပ်သော ရေအောက်တွင် ၁၀ မိနစ် ချပါ။ ရေခဲ/ဆီ/ဆေးလိမ်း မသုံးပါနှင့်။ သန့်ရှင်းခြောက်သွေ့ အဝတ်ဖြင့် ဖုံးအုပ်ပါ။",
            "Immobilize the area, avoid moving it, and apply a cold compress (wrapped). Seek medical evaluation—X-ray may be needed.": "ဒဏ်ရာတည်နေရာကို မရွှေ့ရန် ကြိုးစားပြီး အေးမြသောဖိအောင် ချုပ်တင်ပါ။ ဆေးခန်းတွင် စစ်ဆေးသည်။",
            "Encourage coughing. If the person can't breathe or speak, perform abdominal thrusts if trained, and call emergency services.": "ချောင်းဆိုးခိုင်းပါ။ အသက်ရှု/ပြောမရပါက သင်တန်းရောက်ပြီးသားဖြစ်လျှင် ဝမ်းဗိုက်ဖိအား တင်ပါ။ အရေးပေါ်အကူအညီခေါ်ဆိုပါ။",
            "Drop, cover, and hold on. Stay away from windows. After shaking stops, check for injuries and hazards.": "အောက်ထိုင်၊ ဖုံးကွယ်၊ ထိန်းထားပါ။ ပြတင်းပေါက်များမှ ဝေးကွာပါ။ ရပ်ပြီးနောက် ထိခိုက်ဒဏ်ရာ/အန္တရာယ်များ စစ်ဆေးပါ။",
            "Move to higher ground. Avoid walking or driving through flood water. Just 15 cm of moving water can knock you down.": "မြင့်နေရာသို့ ရွှေ့ပါ။ ရေကြီးထဲ လမ်းလျှောက်ခြင်း/မောင်းနှင်ခြင်း မလုပ်ပါနှင့်။",
            "Shelter in a small interior room away from windows. Keep your phone charged and avoid downed power lines.": "ပြတင်းပေါက်မှ ဝေးကွာသည့် အတွင်းခန်းငယ်တွင် ခိုလှုံပါ။ ဖုန်းအားထားပါ။ လျှပ်စစ်ကြိုးကျိုးကျော်မှ ဝေးပါ။",
            "Move away from the slide path to higher, stable ground. Watch for flooding after the slide.": "လျှောစီးလမ်းကြောင်းမှ ဝေးကွာကာ မြင့်ပြီး တည်ငြိမ်ရာသို့ ရွှေ့ပါ။",
            "Rest, hydrate with safe fluids, and monitor symptoms. Seek medical care if symptoms are severe, persistent, or in infants/elderly.": "အနားယူပြီး သန့်ရှင်းသောရည်ယောက်ပါ။ ပြင်းထန်/မသက်သာလျှင် ဆေးခန်းသို့ သွား​ပါ။",
            "I'm here. Please share your location (city/area) and needs. A volunteer/coordinator will follow up.": "နှောက်နှေးမနေပါနှင့်—တည်နေရာနှင့် လိုအပ်ချက်များကို ထပ်မံဖော်ပြပါ။ စေတနာရှင်/ညှိနှိုင်းသူမှ ဆက်သွယ်ပါမည်။",
            "Thanks for reaching out. Please describe your location and needs. A coordinator or volunteer will review and respond.": "ဆက်သွယ်လာသည့်အတွက် ကျေးဇူးတင်ပါတယ်။ တည်နေရာနှင့် လိုအပ်ချက်ကို ဖော်ပြပါ။ ပြန်လည်တုံ့ပြန်ပါမည်။",
        }
    }
    return table.get(lang, {}).get(en_text, en_text)
# ---------- Country-Region mapping (Asia only) ----------
COUNTRY_REGION_MAP = {
    # East Asia
    "Japan": "East Asia",
    "South Korea": "East Asia",
    "North Korea": "East Asia",
    "China": "East Asia",
    "Taiwan": "East Asia",
    "Mongolia": "East Asia",
    
    # Southeast Asia
    "Singapore": "Southeast Asia",
    "Malaysia": "Southeast Asia",
    "Indonesia": "Southeast Asia",
    "Thailand": "Southeast Asia",
    "Vietnam": "Southeast Asia",
    "Philippines": "Southeast Asia",
    "Myanmar": "Southeast Asia",
    "Cambodia": "Southeast Asia",
    "Laos": "Southeast Asia",
    "Brunei": "Southeast Asia",
    "Timor-Leste": "Southeast Asia",
    
    # South Asia
    "India": "South Asia",
    "Pakistan": "South Asia",
    "Bangladesh": "South Asia",
    "Sri Lanka": "South Asia",
    "Nepal": "South Asia",
    "Bhutan": "South Asia",
    "Maldives": "South Asia",
    "Afghanistan": "South Asia",
    
    # Central Asia
    "Kazakhstan": "Central Asia",
    "Uzbekistan": "Central Asia",
    "Turkmenistan": "Central Asia",
    "Kyrgyzstan": "Central Asia",
    "Tajikistan": "Central Asia",
    
    # West Asia (Middle East)
    "Turkey": "West Asia",
    "Iran": "West Asia",
    "Iraq": "West Asia",
    "Syria": "West Asia",
    "Lebanon": "West Asia",
    "Jordan": "West Asia",
    "Israel": "West Asia",
    "Palestine": "West Asia",
    "Saudi Arabia": "West Asia",
    "Yemen": "West Asia",
    "Oman": "West Asia",
    "UAE": "West Asia",
    "Qatar": "West Asia",
    "Kuwait": "West Asia",
    "Bahrain": "West Asia",
}

def get_region_for_country(country: str) -> str:
    """Auto-detect region based on country name (case-insensitive)"""
    if not country or not country.strip():
        return ""
    
    country_clean = country.strip()
    
    # Case-insensitive exact match
    for mapped_country, region in COUNTRY_REGION_MAP.items():
        if country_clean.lower() == mapped_country.lower():
            return region
    
    return ""  # No match found

def _aidbot_reply(t: str, lang: str = "en") -> str:
    s = (t or "").lower()
    def any_in(keys): return any(k in s for k in keys)
    if any_in(["unconscious","အသက်မရှူ","not breathing","no pulse","chest pain","ရင်ဘတ်အောင့်ခြင်း","severe bleeding"]):
        en = "This may be an emergency. Call local emergency services immediately. If trained, begin CPR and keep the person safe until help arrives."
        return _translate(en, lang)
    if any_in(["bleed","သွေးထွက်","bleeding","cut","wound","အနာ","laceration"]):
        en = "Apply firm pressure with a clean cloth for at least 10 minutes. Elevate the area if possible. If bleeding is severe or won't stop, seek medical help."
        return _translate(en, lang)
    if any_in(["burn","ပူလောင်","scald","ရေနွေးပူ"]):
        en = "Cool the burn under clean running water for at least 10 minutes. Do not apply ice, butter, or ointments. Cover loosely with a clean, dry dressing."
        return _translate(en, lang)
    if any_in(["fracture","broken bone","အရိုးကျိုး","sprain"]):
        en = "Immobilize the area, avoid moving it, and apply a cold compress (wrapped). Seek medical evaluation—X-ray may be needed."
        return _translate(en, lang)
    if any_in(["choking","နှာစေးခြင်း"]):
        en = "Encourage coughing. If the person can't breathe or speak, perform abdominal thrusts if trained, and call emergency services."
        return _translate(en, lang)
    if any_in(["earthquake","ငလျင်","tremor","aftershock"]):
        en = "Drop, cover, and hold on. Stay away from windows. After shaking stops, check for injuries and hazards."
        return _translate(en, lang)
    if any_in(["flood","ရေလွှမ်းမိုး","flash flood"]):
        en = "Move to higher ground. Avoid walking or driving through flood water. Just 15 cm of moving water can knock you down."
        return _translate(en, lang)
    if any_in(["storm","မုန်တိုင်း","cyclone","typhoon","hurricane","tornado"]):
        en = "Shelter in a small interior room away from windows. Keep your phone charged and avoid downed power lines."
        return _translate(en, lang)
    if any_in(["landslide","ပြိုကျခြင်း"]):
        en = "Move away from the slide path to higher, stable ground. Watch for flooding after the slide."
        return _translate(en, lang)
    if any_in(["fever","ဖျားခြင်း","cough","flu","diarrhea","vomit","အော့အန်ခြင်း","vomiting"]):
        en = "Rest, hydrate with safe fluids, and monitor symptoms. Seek medical care if symptoms are severe, persistent, or in infants/elderly."
        return _translate(en, lang)
    if any_in(["help","ကူညီကြပါ","contact","assist","support"]):
        en = "I'm here. Please share your location (city/area) and needs. A volunteer/coordinator will follow up."
        return _translate(en, lang)
    en = "Thanks for reaching out. Please describe your location and needs. A coordinator or volunteer will review and respond."
    return _translate(en, lang)

# ---------- History for global Back ----------
def _update_route_history():
    route = st.session_state.get("route", "home")
    last  = st.session_state.get("_last_route")
    hist = st.session_state.setdefault("_route_hist", [])
    if last is not None and last != route:
        if not hist or hist[-1] != last:
            hist.append(last)
        if len(hist) > 25:
            del hist[:-25]
    st.session_state["_last_route"] = route

def _global_back_button():
    """Unified Back to Home button"""
    route = st.session_state.get("route", "home")
    if route == "home":
        return
    
    st.markdown(
        """
        <style>
        .aid-back-wrap { margin: 8px 0 6px 0; }
        .aid-back-wrap .stButton>button{ 
            white-space: nowrap; 
            border-radius: 16px; 
            padding: 6px 14px;
            background-color: var(--primary-red);
            color: white;
            border: none;
        }
        .aid-back-wrap .stButton>button:hover{ 
            background-color: var(--primary-red-dark);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="aid-back-wrap">', unsafe_allow_html=True)
    lang = st.session_state.get("lang", "en")
    if st.button(f"← {_translate('Back to Home', lang)}", key="__back_global"):
        st.session_state["route"] = "home"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ---------- Header ----------
def render_header(show_auth: bool = False):
    _update_route_history()
    _global_back_button()
    sidebar_brand(_translate)

    st.markdown('<div class="aid-header">', unsafe_allow_html=True)

    # columns across the very top row
    col1, col2, col3 = st.columns([0.06, 0.64, 0.30])

    with col1:
        header_logo = os.path.join(IMAGES_DIR, "aidbot_header.svg")
        if os.path.exists(header_logo): 
            st.image(header_logo, width=50)
        elif os.path.exists(LOGO_PATH): 
            st.image(LOGO_PATH, width=50)
        elif os.path.exists(DEFAULT_AVATAR): 
            st.image(DEFAULT_AVATAR, width=50)

    with col2:
        lang = st.session_state.get("lang", "en")
        st.markdown(
            f'<div class="aid-header-title">AidBot — {_translate("Dashboard", lang)}</div>',
            unsafe_allow_html=True,
        )

    with col3:
        # language selector
        lang_names = list(_LANGS.keys())
        current_lang = st.session_state.get("lang_name", lang_names[0])
        selected_lang = st.selectbox(
            f"🌐 {_translate('Choose language', st.session_state.get('lang','en'))}",
            lang_names,
            index=lang_names.index(current_lang) if current_lang in lang_names else 0,
            key="header_lang_select",
        )
        if selected_lang != current_lang:
            st.session_state["lang_name"] = selected_lang
            st.session_state["lang"] = _LANGS[selected_lang]
            st.rerun()

    # ===== New Row Below Header: Buttons Row =====
    if show_auth and "user" in st.session_state:
        u = st.session_state["user"]
        lang = st.session_state.get("lang", "en")
        unread = len(list_notifications(u["user_id"], unread_only=True))

        # Create 1 spacer + 3 button columns (pushed to right)
        spacer, c1, c2, c3 = st.columns([2, 1, 1, 1])

        with c1:
            # Keep notifications in one line with nbsp (non-breaking space)
            label = f"🔔 {_translate('Notifications', lang)}"
            if unread > 0:
                label += f" ({unread})"
            if st.button(label.replace(" ", "\u00A0"), key=f"btn_notif_{u['user_id']}", use_container_width=True):
                st.session_state["route"] = "notifications"
                st.rerun()

        with c2:
            if st.button(f"👤 {_translate('My Profile', lang)}", 
                        key=f"btn_profile_{u['user_id']}", 
                        use_container_width=True):
                st.session_state["route"] = "profile"
                st.rerun()

        with c3:
            if st.button(_translate("Logout", lang), 
                        key=f"btn_logout_{u['user_id']}", 
                        use_container_width=True):
                st.session_state.clear()
                st.rerun()

        # Signed-in info aligned to the right
        st.markdown(
            f'<div style="text-align: right;"><p class="aid-signed">Signed in as <strong>{u["username"]}</strong></p></div>',
            unsafe_allow_html=True,
        )

    st.divider()

# ---------- Informational pages ----------
def first_aid_page():
    render_header("user" in st.session_state)
    lang = st.session_state.get("lang", "en")
    st.subheader("🆘 " + _translate("First-Aid Guide", lang))
    img = _first_existing_image(["firstaid.JPG"])
    c1, c2 = st.columns([0.45, 0.55])
    with c1:
        if img: st.image(img, use_column_width=True)
    with c2:
        with st.expander("CPR — Adults (Hands-only CPR)", expanded=False):
            st.write("Call emergency services. Push hard and fast in the center of the chest (100–120/min). Switch helper if tired.")
        with st.expander("Bleeding", expanded=False):
            st.write("Apply direct pressure with clean cloth for 10 minutes. Elevate if possible. Seek care if heavy or not stopping.")
        with st.expander("Burns / Scalds", expanded=False):
            st.write("Cool the burn under running water for 10 minutes. Do not use ice or butter. Cover with clean dry dressing.")
        with st.expander("Flood Safety", expanded=False):
            st.write("Move to higher ground. Do not walk or drive through flood water. Avoid electrical hazards.")
        with st.expander("Earthquake Safety", expanded=False):
            st.write("Drop, cover, and hold on. Stay away from windows. After shaking, check for hazards.")
        with st.expander("Choking", expanded=False):
            st.write("Encourage coughing. If unable to breathe/speak, perform abdominal thrusts if trained and call emergency services.")
        with st.expander("Heat Exhaustion", expanded=False):
            st.write("Move to a cool place, loosen clothing, sip water. Seek help if confusion or vomiting occurs.")
        with st.expander("Wound Dressing", expanded=False):
            st.write("Clean with safe water, apply antiseptic if available, cover with sterile dressing.")
        st.markdown("---")
        st.caption("⚠️ Tips are informational only—not a substitute for professional care or local emergency services.")

def red_cross_info_page():
    render_header("user" in st.session_state)
    lang = st.session_state.get("lang", "en")
    st.subheader("🏥 " + _translate("Red Cross Info", lang))
    img = _first_existing_image(["3747350.JPG"])
    c1, c2 = st.columns([0.45, 0.55])
    with c1:
        if img: st.image(img, use_column_width=True)
    with c2:
        st.markdown("### International Red Cross / Red Crescent Movement")
        st.write("""
        **Mission:** To protect life and health, ensure respect for human beings, prevent and alleviate human suffering, without discrimination.
        
        **Seven Fundamental Principles:**
        - **Humanity** — Prevent and alleviate suffering wherever it may be found
        - **Impartiality** — No discrimination based on nationality, race, religion, class, or political opinions
        - **Neutrality** — Does not take sides in hostilities or engage in controversies
        - **Independence** — Autonomous and independent organizations
        - **Voluntary Service** — Voluntary relief movement not prompted by desire for gain
        - **Unity** — Only one Red Cross/Red Crescent Society in any one country
        - **Universality** — A worldwide institution with equal status for all societies
        
        **Scope of Work:**
        - Emergency disaster response and relief
        - Health and care services in communities
        - Support for national blood services
        - First aid training and public health education
        - Tracing and reunification services for separated families
        - Advocacy for international humanitarian law
        
        For more information, visit your local Red Cross or Red Crescent Society.
        """)

def about_page():
    render_header("user" in st.session_state)
    lang = st.session_state.get("lang", "en")
    st.subheader(_translate("About AidBot", lang))
    img = _first_existing_image(["aboutus.JPG"])
    c1, c2 = st.columns([0.45, 0.55])
    with c1:
        if img: st.image(img, use_column_width=True)
    with c2:
        st.markdown("### About AidBot")
        st.write("""
        **AidBot** is a community-driven disaster response platform designed to save lives and coordinate relief efforts during emergencies.
        
        **What We Do:**
        - **Emergency Response:** Connect victims with volunteers and coordinators in real-time
        - **Resource Management:** Track shelters, blood inventory, medical supplies, and transport
        - **First Aid Guidance:** Provide immediate, life-saving information accessible in multiple languages
        - **Data-Driven Planning:** Use predictive analytics to pre-position resources where they're most needed
        - **Volunteer Coordination:** Match skilled volunteers with cases based on location and expertise
        
        **Our Approach:**
        Built on principles of transparency, efficiency, and community resilience, AidBot bridges the gap between those who need help and those who can provide it. We leverage modern technology while respecting privacy and ensuring data security.
        
        **Get Involved:**
        Whether you're a victim seeking help, a volunteer ready to serve, or an organization looking to partner, AidBot is here to support you.
        
        Together, we build resilient communities prepared for any disaster.
        """)

def contact_page():
    render_header("user" in st.session_state)
    lang = st.session_state.get("lang", "en")
    st.subheader(_translate("Contact Us", lang))
    img = _first_existing_image(["contactRedCross.JPG","help.JPG"])
    c1, c2 = st.columns([0.45, 0.55])
    with c1:
        if img: st.image(img, use_column_width=True)
    with c2:
        with st.form("contact_form"):
            name = st.text_input("Your name")
            email = st.text_input("Email")
            message = st.text_area("Message")
            submitted = st.form_submit_button(_translate("Send", lang), type="primary")
        if submitted:
            mid = create_contact_message(name, email, message)
            for coord in list_users("coordinator"):
                add_notification(coord["user_id"], f"📩 Contact message {mid} from {name or 'Anonymous'}: {message[:120]}...")
            for adm in list_users("admin"):
                add_notification(adm["user_id"], f"📩 Contact message {mid} from {name or 'Anonymous'}: {message[:120]}...")
            st.success(_translate("Thanks! Our coordinators will review and respond.", lang))
# ---------- Chat ----------
def chat_page():
    render_header("user" in st.session_state)
    lang = st.session_state.get("lang", "en")
    st.subheader("💬 " + _translate("Chat with Us", lang))
    st.caption("Quick tips only; not a substitute for professional or emergency care.")
    
    history = st.session_state.setdefault("chat_history", [])
    max_history = 12
    for msg in history[-max_history:]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    with st.form("chat_compose", clear_on_submit=True):
        user_text = st.text_input("Describe your situation…", key="compose_text", placeholder="Type here…")
        spacer, c_send, c_clear = st.columns([1.0, 0.16, 0.20], gap="small")
        with c_send:
            send = st.form_submit_button(_translate("Send", lang), type="primary")
        with c_clear:
            clear = st.form_submit_button(_translate("Clear Chat", lang))
    if clear:
        st.session_state["chat_history"] = []
        st.rerun()
    if send and user_text.strip():
        history.append({"role":"user","content":user_text})
        bot = _aidbot_reply(user_text, lang=lang)
        history.append({"role":"assistant","content":bot})
        st.session_state["chat_history"] = history[-max_history:]
        st.rerun()

# ---------- Notifications → open case ----------
def _goto_case_from_notification(cid: str):
    u = st.session_state.get("user") or {}
    role = u.get("role","")
    st.session_state["focus_case_id"] = cid
    if role in ("admin","coordinator","volunteer"):
        go("home")
    else:
        go("victim", prefill_case_id=cid)

def notifications_page():
    render_header(True)
    u = st.session_state.get("user")
    if not u:
        st.warning("You must log in.")
        return
    
    lang = st.session_state.get("lang", "en")
    st.subheader("🔔 " + _translate("Notifications", lang))
    st.caption("You'll be notified on new cases, assignments, status changes, and contact messages.")
    
    # Search box
    search_query = st.text_input(_translate("Search", lang) + " notifications", placeholder="Search by case ID or message text...", key="notif_search")
    
    unread = list_notifications(u["user_id"], unread_only=True)
    all_n  = list_notifications(u["user_id"], unread_only=False)
    
    # Apply search filter
    if search_query.strip():
        q = search_query.lower()
        unread = [n for n in unread if q in n["message"].lower()]
        all_n = [n for n in all_n if q in n["message"].lower()]
    
    # Pagination helper
    def paginate_list(items: list, page_size: int = 10):
        total = len(items)
        total_pages = max(1, ceil(total / page_size))
        page_key = f"notif_page_{st.session_state.get('_notif_tab', 'unread')}"
        current_page = st.session_state.get(page_key, 1)
        if current_page > total_pages:
            current_page = total_pages
            st.session_state[page_key] = current_page
        
        start_idx = (current_page - 1) * page_size
        end_idx = min(start_idx + page_size, total)
        page_items = items[start_idx:end_idx]
        
        return page_items, current_page, total_pages, page_key
    
    def _render_list(items: list, show_read_mark: bool, tab_name: str):
        if not items:
            st.info(_translate("No notifications.", lang))
            return
        
        page_items, current_page, total_pages, page_key = paginate_list(items)
        
        for i, n in enumerate(page_items, start=1):
            ts = dt.datetime.fromtimestamp(n["created_at"]).strftime("%Y-%m-%d %H:%M")
            msg = n["message"]
            cid_match = re.search(r"(C-[0-9a-f]+)", msg)
            cols = st.columns([0.8, 0.2])
            with cols[0]:
                mark = "• " if not show_read_mark and not n.get("read_at") else ""
                st.write(f"{mark}**{ts}** — {msg}")
            mid_match = re.search(r"(M-\d+)", msg)
            with cols[1]:
                if cid_match:
                    if st.button("Open case", key=f"open_case_{n['id']}_{tab_name}_{i}_{current_page}"):
                        _goto_case_from_notification(cid_match.group(1))
                        st.rerun()
                elif mid_match:
                    if st.button("Open message", key=f"open_msg_{n['id']}_{tab_name}_{i}_{current_page}"):
                        st.session_state["focus_message_id"] = mid_match.group(1)
                        st.session_state["route"] = "messages_admin"
                        st.rerun()
        
        # Pagination controls
        if total_pages > 1:
            st.markdown("---")
            col1, col2, col3 = st.columns([0.3, 0.4, 0.3])
            with col1:
                if current_page > 1:
                    if st.button("← Previous", key=f"notif_prev_{tab_name}"):
                        st.session_state[page_key] = current_page - 1
                        st.rerun()
            with col2:
                st.markdown(f"<div style='text-align:center'>Page {current_page} of {total_pages}</div>", unsafe_allow_html=True)
            with col3:
                if current_page < total_pages:
                    if st.button("Next →", key=f"notif_next_{tab_name}"):
                        st.session_state[page_key] = current_page + 1
                        st.rerun()
    
    tabs = st.tabs(["Unread", "All"])
    with tabs[0]:
        st.session_state["_notif_tab"] = "unread"
        _render_list(unread, show_read_mark=False, tab_name="unread")
        if unread and st.button("Mark all as read", key="mark_all_read"):
            mark_all_read(u["user_id"])
            st.success("Marked all as read.")
            st.rerun()
    with tabs[1]:
        st.session_state["_notif_tab"] = "all"
        _render_list(all_n, show_read_mark=True, tab_name="all")

# ---------- Public home ----------
def public_home():
    render_header(False)
    lang = st.session_state.get("lang", "en")
    st.markdown("### " + _translate("Welcome to AidBot", lang))
    #hero = _first_existing_image(["woman-doctor.JPG"])
    #if hero:
       # st.image(hero, use_column_width=True)
    st.write("**" + _translate("Get help fast. First-aid, disaster tips, shelters, and contact helpers.", lang) + "**")
    c1, c2, c3 = st.columns(3, gap="large")
    with c1:
        st.subheader("First Aid")
        img = _first_existing_image(["crp.JPG","firstaid.JPG"])
        if img: st.image(img, use_column_width=True)
        st.write("CPR basics, Wound care, Flood safety...")
        b1, b2 = st.columns(2)
        with b1:
            if st.button(_translate("First-Aid Guide", lang)):
                go("first_aid")
        with b2:
            if st.button(_translate("Red Cross Info", lang), key="rc_info"):
                go("red_cross")
    with c2:
        st.subheader("Contact AidBot")
        img = _first_existing_image(["contactRedCross.JPG"])
        if img: st.image(img, use_column_width=True)
        st.write("Need help now? Contact our team!")
        b1, b2 = st.columns([0.45, 0.55])
        with b1:
            if st.button(_translate("Chat With Us", lang), type="primary"):
                go("chat")
        with b2:
            if st.button(_translate("Emergency Form", lang), key="victim_form_btn"):
                go("victim")
    with c3:
        st.subheader("Volunteer with Us")
        img = _first_existing_image(["volunteers.JPG"])
        if img: st.image(img, use_column_width=True)
        st.write("Join AidBot team to help save lives!")
        if st.button(_translate("Volunteer / Coordinator Login", lang), key="home_login", type="primary"):
            go("login")

# ---------- Map helper (shelters) ----------
def _shelters_map_pydeck(shelters_df: pd.DataFrame):
    if shelters_df.empty:
        st.caption("No shelters to display.")
        return
    df = shelters_df.rename(columns={"latitude":"lat","longitude":"lon"})
    df = df.dropna(subset=["lat","lon"])
    if df.empty:
        st.info("Shelters map: no coordinates found. Edit a shelter and add Latitude/Longitude to show pins.")
        return
    if MAPBOX_TOKEN:
        layer = pdk.Layer(
            "ScatterplotLayer",
            data=df,
            get_position=["lon","lat"],
            get_radius=1200,
            get_fill_color=[227,59,59,160],
            pickable=True,
        )
        deck = pdk.Deck(
            layers=[layer],
            initial_view_state=pdk.ViewState(latitude=float(df["lat"].mean()),
                                             longitude=float(df["lon"].mean()), zoom=5),
            map_provider="mapbox",
            map_style="mapbox://styles/mapbox/light-v11",
            api_keys={"mapbox": MAPBOX_TOKEN},
            tooltip={"text": "{name}\nCapacity: {capacity}\nAvailable: {available}"},
        )
        st.pydeck_chart(deck, use_container_width=True)
    else:
        st.map(df.rename(columns={"lat":"latitude","lon":"longitude"})[["latitude","longitude"]])

# ---------- Victim portal ----------
def victim_portal():
    render_header(True)
    lang = st.session_state.get("lang", "en")
    default_country = (st.session_state.get("user") or {}).get("country","")
    default_country = st.session_state.get("last_country", default_country)

    st.subheader("🚨 " + _translate("Emergency Form", lang))
    
    # Show detected region info box
    if "form_country" in st.session_state and st.session_state["form_country"]:
        detected = get_region_for_country(st.session_state["form_country"])
        if detected:
            st.info(f"✅ Auto-detected Region: **{detected}** (based on {st.session_state['form_country']})")
    
    with st.form("victim_form"):
        name = st.text_input("Your name")
        email = st.text_input("Email")
        phone = st.text_input("Phone")
        
        # Country input FIRST
        country = st.text_input("Country", value=default_country, key="form_country_input")
        
        # Auto-fill region based on country
        auto_region = get_region_for_country(country) if country else ""
        region = st.text_input(
            "Region", 
            value=auto_region, 
            help="Auto-filled based on country. You can edit if needed.",
            key="form_region_input"
        )
        
        lat = st.text_input("Latitude (optional)")
        lon = st.text_input("Longitude (optional)")
        desc = st.text_area("What happened?")
        file = st.file_uploader("Attach photo/file")
        consent = st.checkbox(
            "I consent to store my contact, description, and (optional) location for the purpose of responding to this request.",
            value=False
        )
        submit = st.form_submit_button(_translate("Send", lang) + " Request", type="primary")

    if submit:
        if not consent:
            st.error("Please check consent before submitting.")
            return
        
        # Store country for next time
        st.session_state["form_country"] = country

        def _flt(x):
            try:
                return float(x) if str(x).strip() else None
            except Exception:
                return None

        lat_val, lon_val = _flt(lat), _flt(lon)

        # save upload
        attach_path = ""
        if file is not None:
            fname = _safe_filename(file.name)
            attach_path = os.path.join(UPLOAD_DIR, fname)
            with open(attach_path, "wb") as f:
                f.write(file.getbuffer())

        # 1) persist the form
        from db import create_emergency_form, link_form_to_case
        form_id = create_emergency_form(
            user_id=(st.session_state.get("user") or {}).get("user_id"),
            victim_name=name, contact_email=email, phone=phone,
            region=region, country=country, latitude=lat_val, longitude=lon_val,
            description=desc, attachment_path=attach_path
        )

        # 2) create the case
        cid = create_case(
            victim_name=name, email=email, phone=phone,
            region=region, country=country, lat=lat_val, lon=lon_val,
            description=desc, attachment_path=attach_path
        )

        # 3) link form → case
        link_form_to_case(form_id, cid)

        # notify + UI
        st.success(f"Emergency request submitted! Your Case ID: **{cid}**")
        st.session_state["last_country"] = country
        for coord in list_users("coordinator"):
            add_notification(coord["user_id"], f"New emergency case submitted: {cid}")
        for adm in list_users("admin"):
            add_notification(adm["user_id"], f"New emergency case submitted: {cid}")

    # Nearby shelters (unchanged)
    st.markdown("### Nearby shelters")
    shelters = list_shelters()
    _shelters_map_pydeck(pd.DataFrame(shelters) if shelters else pd.DataFrame())

    # Inline case lookup (unchanged)
    st.markdown("---")
    st.subheader("🔎 " + _translate("Case Status", lang))
    default_id = st.session_state.pop("prefill_case_id", "")
    case_id = st.text_input("Enter your Case ID", value=default_id, key="case_lookup_inline")
    if st.button("Lookup", key="lookup_inline_btn"):
        c = get_case((case_id or "").strip())
        if not c:
            st.error("Case not found. Check the ID and try again.")
        else:
            st.success(f"Status: {c.get('status','new')} (Loaded successfully!)")
            st.write(f"Region/Country: {c.get('region','')} / {c.get('country','')}")
            ts = c.get('created_at', 0)
            if ts:
                st.write(f"Submitted: {dt.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')}")
            tl = c.get("timeline")
            if tl:
                try:
                    items = json.loads(tl) or []
                except Exception:
                    items = []
                if items:
                    st.markdown("**Timeline**")
                    for item in items[::-1]:
                        when = dt.datetime.fromtimestamp(item.get("ts",0)).strftime("%Y-%m-%d %H:%M")
                        st.write(f"- {when}: {item.get('action','')}")

# ---------- Cases ----------
def volunteer_cases():
    u = st.session_state["user"]
    lang = st.session_state.get("lang", "en")
    st.subheader(_translate("Cases", lang) + " (My assignments)")
    my = list_cases(assigned_to=u["user_id"])
    _cases_table(my, volunteer=True, admin_mode=False, focus_case_id=st.session_state.pop("focus_case_id", None))

def _cases_grid(cases: list, page_key: str = "cases_grid"):
    page_items, cur, pages, key_page, total = _paginate(cases, page_key, page_size=10)
    if not page_items:
        st.info("No cases."); return
    df = pd.DataFrame(page_items)
    cols = ["case_id","victim_name","status","region","country","assigned_to","shelter_id","created_at"]
    show = [c for c in cols if c in df.columns]
    if "created_at" in show:
        df["created_at"] = pd.to_datetime(df["created_at"], unit="s", errors="coerce")
    h = _auto_height(len(df))
    st.dataframe(df[show], use_container_width=True, height=h, hide_index=True)
    _pager(cur, pages, key_page, center_note=f"{total} total")

def coordinator_cases(admin_mode: bool):
    lang = st.session_state.get("lang", "en")
    st.subheader(_translate("Cases", lang) + " (All)")

    # ---- Filters -----------------------------------------------------------
    c1, c2, c3 = st.columns(3)
    with c1:
        status = st.selectbox(
            _translate("Filter", lang) + " by status",
            ["(all)", "new", "acknowledged", "en_route", "arrived", "closed", "cancelled"],
            index=0
        )
        status = None if status == "(all)" else status

    with c2:
        today = dt.date.today()

        # derive a sensible min date from your DB (fallback: last 90 days)
        all_dates = [dt.date.fromtimestamp(c["created_at"])
                    for c in list_cases() if c.get("created_at")]
        min_date = min(all_dates) if all_dates else (today - dt.timedelta(days=90))

        # Set default date range (last 30 days to today)
        default_start = max(min_date, today - dt.timedelta(days=30))
        default_end = today
        
        # Ensure min_date is before max_date
        if min_date > today:
            min_date = today - dt.timedelta(days=90)

        date_val = st.date_input(
            "Created between",
            value=(default_start, default_end),
            min_value=min_date,
            max_value=today,
            key="cases_date_range"
        )
        
        # Handle the returned value properly
        if isinstance(date_val, (list, tuple)):
            if len(date_val) == 2:
                start, end = date_val
            elif len(date_val) == 1:
                start = end = date_val[0]
            else:
                start = end = today
        else:
            start = end = date_val

    with c3:
        search_text = st.text_input(_translate("Search", lang), placeholder="Victim name, case ID, region...")

    # request cases (by status only first)
    cs = list_cases(status=status)

    # apply date filter
    def in_range(ts):
        d = dt.date.fromtimestamp(ts) if ts else None
        return (d is None) or (start <= d <= end)
    cs = [c for c in cs if in_range(c.get("created_at", 0))]

    # text filter
    if (search_text or "").strip():
        q = search_text.lower()
        cs = [c for c in cs if (
            q in (c.get("case_id") or "").lower() or
            q in (c.get("victim_name") or "").lower() or
            q in (c.get("region") or "").lower() or
            q in (c.get("country") or "").lower()
        )]

    # ---- Overview KPIs (for filtered set) ---------------------------------
    by_status = {}
    for c in cs:
        by_status[c.get("status","new")] = by_status.get(c.get("status","new"), 0) + 1
    open_count = sum(by_status.get(s, 0) for s in ["new","acknowledged","en_route","arrived"])

    k1, k2, k3, k4 = st.columns(4)
    with k1: st.markdown(f'<div class="kpi" style="background: linear-gradient(135deg, rgba(227,59,59,0.1) 0%, rgba(227,59,59,0.05) 100%); border-left: 4px solid #e33b3b;"><h3 style="color: #e33b3b;">Cases (filtered)</h3><p style="color: #e33b3b;">{len(cs)}</p></div>', unsafe_allow_html=True)
    with k2: st.markdown(f'<div class="kpi" style="background: linear-gradient(135deg, rgba(227,59,59,0.1) 0%, rgba(227,59,59,0.05) 100%); border-left: 4px solid #e33b3b;"><h3 style="color: #e33b3b;">Open</h3><p style="color: #e33b3b;">{open_count}</p></div>', unsafe_allow_html=True)
    with k3: st.markdown(f'<div class="kpi" style="background: linear-gradient(135deg, rgba(227,59,59,0.1) 0%, rgba(227,59,59,0.05) 100%); border-left: 4px solid #e33b3b;"><h3 style="color: #e33b3b;">Closed</h3><p style="color: #e33b3b;">{by_status.get("closed",0)}</p></div>', unsafe_allow_html=True)
    with k4: st.markdown(f'<div class="kpi" style="background: linear-gradient(135deg, rgba(227,59,59,0.1) 0%, rgba(227,59,59,0.05) 100%); border-left: 4px solid #e33b3b;"><h3 style="color: #e33b3b;">Cancelled</h3><p style="color: #e33b3b;">{by_status.get("cancelled",0)}</p></div>', unsafe_allow_html=True)
    st.divider()

    # Cards view ONLY
    _cases_table(cs, volunteer=False, admin_mode=admin_mode, focus_case_id=st.session_state.pop("focus_case_id", None))

def _notify_admins_and_coords(msg: str):
    for coord in list_users("coordinator"):
        add_notification(coord["user_id"], msg)
    for adm in list_users("admin"):
        add_notification(adm["user_id"], msg)

def _cases_table(cases: list, volunteer: bool, admin_mode: bool=False, focus_case_id: str | None = None):
    lang = st.session_state.get("lang", "en")
    if not cases:
        st.info(_translate("No cases.", lang))
        return
    
    # Pagination
    page_size = 10
    total = len(cases)
    total_pages = max(1, ceil(total / page_size))
    page_key = "cases_page"
    current_page = st.session_state.get(page_key, 1)
    if current_page > total_pages:
        current_page = total_pages
        st.session_state[page_key] = current_page
    
    start_idx = (current_page - 1) * page_size
    end_idx = min(start_idx + page_size, total)
    page_cases = cases[start_idx:end_idx]
    
    vol_list = list_volunteers()
    vol_map = {v["user_id"]: v["username"] for v in vol_list}
    
    active_id = st.session_state.get("active_case_id")
    for c in page_cases:
        cid = c["case_id"]
        expanded = (cid == focus_case_id) or (cid == active_id)
        with st.expander(f"{cid} — {c.get('victim_name','(no name)')} · {c.get('status','new')}", expanded=expanded):
            cols = st.columns(3)
            with cols[0]:
                st.write(f"*Region/Country:* {c.get('region','')} / {c.get('country','')}")
                st.write(f"*Contact:* {c.get('phone','')} · {c.get('contact_email','')}")
            with cols[1]:
                assignee_id = c.get('assigned_to')
                st.write(f"Assigned to: {vol_map.get(assignee_id, '—')}")
                st.write(f"Shelter: {c.get('shelter_id') or '—'}")
            with cols[2]:
                st.write(f"*Coords:* {c.get('latitude','')} , {c.get('longitude','')}")
                try:
                    ts = dt.datetime.fromtimestamp(c.get('created_at', 0)).strftime('%Y-%m-%d %H:%M')
                except Exception:
                    ts = "—"
                st.write(f"*Created:* {ts}")

            desc = (c.get('description') or '').strip()
            if desc:
                st.markdown("*Description:*")
                st.write(desc)

            att = (c.get("attachment_path") or "").strip()
            if att:
                if admin_mode:
                    st.write(f"*Attachment path:* {att}")
                else:
                    st.write("Attachment: Available to coordinators/admins only.")

            st.markdown("---")

            if not volunteer:
                ac1, ac2, ac3 = st.columns([0.45, 0.35, 0.20])
                with ac1:
                    assign_opts = ["(none)"] + [f"{v['username']} | {v['user_id']}" for v in vol_list]
                    current_val = "(none)" if not c.get("assigned_to") else f"{vol_map.get(c['assigned_to'],'?')} | {c['assigned_to']}"
                    sel_assign = st.selectbox("Assign to", assign_opts,
                        index=assign_opts.index(current_val) if current_val in assign_opts else 0,
                        key=f"assignee_{cid}_{current_page}",
                        on_change=_keep_open, args=(cid,))
                with ac2:
                    shel_input = st.text_input("Shelter ID (optional)", value=c.get("shelter_id") or "", 
                        key=f"shelter_{cid}_{current_page}",
                        on_change=_keep_open, args=(cid,))
                with ac3:
                    if st.button(_translate("Apply", lang), key=f"apply_assign_{cid}_{current_page}"):
                        uid = None
                        if sel_assign != "(none)":
                            uid = sel_assign.split("|", 1)[1].strip()
                            add_notification(uid, f"You have been assigned to case {cid}.")
                        assign_case(cid, uid, shelter_id=shel_input or None)
                        _notify_admins_and_coords(f"Case {cid} assignment updated.")
                        st.success("Assignment updated successfully!")
                        st.session_state["active_case_id"] = cid
                        st.rerun()

            st.markdown("*Update status*")
            status_choices = ["acknowledged", "en_route", "arrived", "closed", "cancelled"]
            sel_status = st.selectbox("New status", status_choices, index=0, 
                key=f"status_{cid}_{current_page}",
                on_change=_keep_open, args=(cid,))
            if st.button(_translate("Save", lang) + " status", key=f"save_status_{cid}_{current_page}"):
                update_case_status(cid, sel_status)
                if c.get("assigned_to"):
                    add_notification(c["assigned_to"], f"Status for case {cid} set to {sel_status}.")
                _notify_admins_and_coords(f"Case {cid} status changed to {sel_status}.")
                st.success("Status updated successfully!")
                st.session_state["active_case_id"] = cid
                st.rerun()

            if admin_mode:
                st.markdown("---")
                st.caption("Admin actions")
                ec1, ec2, ec3 = st.columns([0.34, 0.33, 0.33])
                with ec1:
                    new_region = st.text_input("Region", value=c.get("region",""), key=f"edit_r_{cid}_{current_page}")
                    new_country= st.text_input("Country", value=c.get("country",""), key=f"edit_c_{cid}_{current_page}")
                with ec2:
                    new_desc   = st.text_area("Description", value=c.get("description",""), key=f"edit_d_{cid}_{current_page}", height=80)
                with ec3:
                    if st.button(_translate("Save", lang) + " edits", key=f"edit_save_{cid}_{current_page}"):
                        from db import _connect
                        with _connect() as conn:
                            conn.execute("UPDATE cases SET region=?, country=?, description=? WHERE case_id=?",
                                         (new_region, new_country, new_desc, cid))
                            conn.commit()
                        st.success("Case updated successfully!")
                    if st.button(_translate("Delete", lang) + " case", key=f"del_case_{cid}_{current_page}"):
                        from db import _connect
                        with _connect() as conn:
                            conn.execute("DELETE FROM cases WHERE case_id=?", (cid,))
                            conn.commit()
                        st.success("Case deleted successfully!")
                        st.rerun()
    
    # Pagination controls
    if total_pages > 1:
        st.markdown("---")
        col1, col2, col3 = st.columns([0.3, 0.4, 0.3])
        with col1:
            if current_page > 1:
                if st.button("← Previous", key="cases_prev"):
                    st.session_state[page_key] = current_page - 1
                    st.rerun()
        with col2:
            st.markdown(f"<div style='text-align:center'>Page {current_page} of {total_pages} ({total} total)</div>", unsafe_allow_html=True)
        with col3:
            if current_page < total_pages:
                if st.button("Next →", key="cases_next"):
                    st.session_state[page_key] = current_page + 1
                    st.rerun()

# ---------- Profile ----------
def profile_page():
    render_header(True)
    lang = st.session_state.get("lang", "en")
    u_sess = st.session_state.get("user")
    if not u_sess:
        st.warning("You need to log in.")
        return
    u = get_user(u_sess["user_id"]) or u_sess
    st.subheader("👤 " + _translate("My Profile", lang))
    col1, col2 = st.columns([0.32, 0.68])
    with col1:
        img_path = (u.get("photo_path") or "").strip()
        if not img_path or not os.path.exists(img_path):
            img_file = (u.get("avatar") or "").strip()
            img_path = os.path.join(IMAGES_DIR, img_file) if img_file else DEFAULT_AVATAR
        if not img_path or not os.path.exists(img_path):
            img_path = DEFAULT_AVATAR if os.path.exists(DEFAULT_AVATAR) else ""
        if img_path and os.path.exists(img_path):
            st.image(img_path, width=160)
        else:
            st.info("No avatar image found. Add images/default_avatar.png for a placeholder.")
        upl = st.file_uploader("Upload profile photo", type=["jpg","jpeg","png"], key="profile_photo")
        st.caption("Tip: JPG/PNG. Stored under /uploads.")
        new_avatar = st.text_input("Avatar filename (in /images)", value=(u.get("avatar") or "default_avatar.png"),
                                   key=f"avatar_{u['user_id']}")
    with col2:
        current_skills = [s for s in (u.get("skills","") or "").split(",") if s.strip()]
        with st.form("edit_profile"):
            first = st.text_input("First name", value=u.get("first_name",""))
            last  = st.text_input("Last name",  value=u.get("last_name",""))
            email = st.text_input("Email",      value=u.get("email",""))
            phone = st.text_input("Phone",      value=u.get("phone",""))
            country= st.text_input("Country",   value=u.get("country",""))
            region= st.text_input("Region",     value=u.get("region",""))
            skills_multi = st.multiselect("Skills", options=SKILL_OPTIONS, default=current_skills)
            bio   = st.text_area("Bio",         value=u.get("bio",""), height=100)
            saved = st.form_submit_button(_translate("Save", lang) + " changes", type="primary")
        if saved:
            photo_path = (u.get("photo_path") or "").strip()
            if upl is not None:
                fname = _safe_filename(upl.name)
                photo_path = os.path.join(UPLOAD_DIR, fname)
                with open(photo_path, "wb") as f:
                    f.write(upl.getbuffer())
            skills_joined = ",".join(skills_multi)
            update_user_profile(
                u["user_id"], phone=phone, region=region, avatar=new_avatar, bio=bio,
                photo_path=photo_path, country=country, skills=skills_joined
            )
            update_user(u["user_id"], {
                "first_name": first, "last_name": last, "email": email,
                "phone": phone, "country": country, "region": region, "skills": skills_joined
            })
            st.session_state["user"].update(dict(
                first_name=first, last_name=last, email=email, phone=phone,
                country=country, region=region, skills=skills_joined,
                avatar=new_avatar, bio=bio, photo_path=photo_path
            ))
            st.success("Profile updated successfully!")
            st.rerun()
        
        # ✅✅✅ NEW: CHANGE PASSWORD SECTION ✅✅✅
        st.markdown("---")
        st.subheader("🔐 Change Password")
        st.caption("Update your account password. You'll need to login again after changing it.")
        
        with st.form("change_password_form"):
            col_pw1, col_pw2 = st.columns(2)
            with col_pw1:
                current_pw = st.text_input("Current Password", type="password", key="current_pw")
                new_pw = st.text_input("New Password", type="password", key="new_pw")
            with col_pw2:
                confirm_pw = st.text_input("Confirm New Password", type="password", key="confirm_pw")
                st.caption("⚠️ Password must be at least 6 characters")
            
            change_pw_submit = st.form_submit_button("🔐 Change Password", type="primary")
        
        if change_pw_submit:
            # Validation
            if not current_pw or not new_pw or not confirm_pw:
                st.error("⚠️ All fields are required.")
            elif new_pw != confirm_pw:
                st.error("❌ New passwords don't match!")
            elif len(new_pw) < 6:
                st.error("⚠️ New password must be at least 6 characters long.")
            else:
                # Verify current password
                from db import get_user_by_credentials, hash_password
                user_check = get_user_by_credentials(u["username"], current_pw)
                
                if not user_check:
                    st.error("❌ Current password is incorrect!")
                else:
                    # Update password
                    update_user(u["user_id"], {"password_hash": hash_password(new_pw)})
                    st.success("✅ Password changed successfully! Please login again.")
                    st.info("🔄 Logging you out in 3 seconds...")
                    
                    # Logout user
                    import time
                    time.sleep(3)
                    st.session_state.clear()
                    st.session_state["route"] = "login"
                    st.rerun()
        # ✅✅✅ END OF CHANGE PASSWORD SECTION ✅✅✅
        
        st.divider()
        st.caption("Confirm delete?")
        if st.button(_translate("Delete", lang) + " my account", type="secondary"):
            delete_user(u["user_id"])
            st.success("Account deleted successfully! You are now signed out.")
            st.session_state.clear()
            st.rerun()

def messages_admin_page():
    render_header(True)
    lang = st.session_state.get("lang", "en")
    st.subheader("📥 Contact messages")

    rows = list_contact_messages()
    if not rows:
        st.info("No contact messages yet.")
        return

    focused = st.session_state.pop("focus_message_id", None)

    for r in rows:
        # accept various timestamp fields / formats
        ts = r.get("created_at") or r.get("created") or r.get("created_ts")
        when = "—"
        if isinstance(ts, (int, float)):
            when = dt.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
        elif isinstance(ts, str) and ts.strip():
            try:
                when = dt.datetime.fromisoformat(ts.replace("Z", "")).strftime("%Y-%m-%d %H:%M")
            except Exception:
                when = ts  # already formatted or unknown

        msg_id = r.get("msg_id", "(no id)")
        name   = r.get("name")  or "Anonymous"
        email  = r.get("email") or "—"
        body   = r.get("message","")

        with st.expander(f"{msg_id} — {name} • {when}", expanded=(msg_id == focused)):
            st.write(f"**From:** {name}  \n**Email:** {email}")
            st.markdown("---")
            st.write(body)

# ---------- Shelters ----------
def shelters_admin():
    lang = st.session_state.get("lang", "en")
    st.subheader(_translate("Shelters", lang))
    
    # Search and filters
    search_query = st.text_input(_translate("Search", lang) + " shelters", placeholder="Name, region, country...")
    
    suggested = _next_numeric_id("S", "shelters", "shelter_id", width=4)
    with st.expander(_translate("Create", lang) + " new shelter"):
        sid  = st.text_input("Shelter ID", value=suggested, help="Editable. Example: S0001")
        name = st.text_input("Name")
        reg = st.text_input("Region")
        ctry = st.text_input("Country")
        lat  = st.text_input("Latitude (optional)")
        lon = st.text_input("Longitude (optional)")
        capacity = st.number_input("Capacity", value=100, step=1)
        available= st.number_input("Available", value=100, step=1)
        contact = st.text_input("Contact")
        notes = st.text_area("Notes")
        if st.button(_translate("Create", lang) + " shelter"):
            def _flt(x):
                try: return float(x) if str(x).strip() else None
                except Exception: return None
            sid_out = create_shelter(name, reg, ctry, _flt(lat), _flt(lon),
                                     int(capacity), int(available), contact, notes,
                                     shelter_id=(sid or None))
            st.success(f"Shelter created successfully! ID: {sid_out}")
            st.rerun()
    
    shel = list_shelters()
    
    # Apply search filter
    if search_query.strip():
        q = search_query.lower()
        shel = [s for s in shel if (
            q in (s.get("name") or "").lower() or
            q in (s.get("region") or "").lower() or
            q in (s.get("country") or "").lower() or
            q in (s.get("shelter_id") or "").lower()
        )]
    
    if not shel:
        st.info("No shelters yet.")
    else:
        df = pd.DataFrame(shel).reset_index(drop=True)
        df.insert(0, "No.", range(1, len(df)+1))
        h = _auto_height(len(df))
        st.dataframe(df[["No.","shelter_id","name","region","country","capacity","available"]],
             use_container_width=True, height=h, hide_index=True)

        st.markdown("#### Manage shelters")
        
        # Pagination
        page_size = 10
        total = len(shel)
        total_pages = max(1, ceil(total / page_size))
        page_key = "shelters_page"
        current_page = st.session_state.get(page_key, 1)
        if current_page > total_pages:
            current_page = total_pages
            st.session_state[page_key] = current_page
        
        start_idx = (current_page - 1) * page_size
        end_idx = min(start_idx + page_size, total)
        page_shelters = shel[start_idx:end_idx]
        
        for r in page_shelters:
            with st.expander(f"{r['shelter_id']} — {r['name']}"):
                e1, e2, e3 = st.columns(3)
                with e1:
                    n  = st.text_input("Name",   value=r.get("name",""),    key=f"sh_n_{r['shelter_id']}_{current_page}")
                    rg = st.text_input("Region", value=r.get("region",""),  key=f"sh_r_{r['shelter_id']}_{current_page}")
                    ct = st.text_input("Country",value=r.get("country",""), key=f"sh_c_{r['shelter_id']}_{current_page}")
                with e2:
                    cap = st.number_input("Capacity", value=int(r.get("capacity") or 0), step=1, key=f"sh_cap_{r['shelter_id']}_{current_page}")
                    ava = st.number_input("Available", value=int(r.get("available") or 0), step=1, key=f"sh_ava_{r['shelter_id']}_{current_page}")
                    contact = st.text_input("Contact", value=r.get("contact",""), key=f"sh_cont_{r['shelter_id']}_{current_page}")
                with e3:
                    notes = st.text_area("Notes", value=r.get("notes",""), key=f"sh_notes_{r['shelter_id']}_{current_page}", height=80)
                    lat = st.text_input("Latitude",  value=str(r.get("latitude") or ""),  key=f"sh_lat_{r['shelter_id']}_{current_page}")
                    lon = st.text_input("Longitude", value=str(r.get("longitude") or ""), key=f"sh_lon_{r['shelter_id']}_{current_page}")
                b1, b2 = st.columns(2)
                if b1.button("💾 " + _translate("Save", lang), key=f"sh_save_{r['shelter_id']}_{current_page}"):
                    def _flt(x):
                        try: return float(x) if str(x).strip() else None
                        except Exception: return None
                    update_shelter(r["shelter_id"], {
                        "name": n, "region": rg, "country": ct,
                        "capacity": int(cap), "available": int(ava),
                        "contact": contact, "notes": notes,
                        "latitude": _flt(lat), "longitude": _flt(lon)
                    })
                    st.success("Shelter updated successfully!")
                if b2.button("🗑️ " + _translate("Delete", lang), key=f"sh_del_{r['shelter_id']}_{current_page}"):
                    delete_shelter(r["shelter_id"])
                    st.success("Shelter deleted successfully!")
                    st.rerun()
        
        # Pagination controls
        if total_pages > 1:
            st.markdown("---")
            col1, col2, col3 = st.columns([0.3, 0.4, 0.3])
            with col1:
                if current_page > 1:
                    if st.button("← Previous", key="shelters_prev"):
                        st.session_state[page_key] = current_page - 1
                        st.rerun()
            with col2:
                st.markdown(f"<div style='text-align:center'>Page {current_page} of {total_pages}</div>", unsafe_allow_html=True)
            with col3:
                if current_page < total_pages:
                    if st.button("Next →", key="shelters_next"):
                        st.session_state[page_key] = current_page + 1
                        st.rerun()

        st.markdown("#### Shelters map")
        _shelters_map_pydeck(pd.DataFrame(shel))

# ---------- Blood (ENHANCED WITH FORECASTING - FILTER FIX) ----------
def _expiry_status(expires_str: str) -> tuple[str, str]:
    """Helper function for blood expiry status"""
    if not (expires_str or "").strip():
        return ("—", "#6b7280")
    try:
        d = dt.datetime.strptime(expires_str, "%Y-%m-%d").date()
        days = (d - dt.date.today()).days
        if days < 0:  return ("Expired", "#b91c1c")
        if days <= 7: return ("Expires soon", "#b45309")
        return (f"In {days} days", "#065f46")
    except Exception:
        return ("Invalid date", "#6b7280")


def blood_tab_enhanced(role: str):
    """Enhanced blood inventory with demand forecasting"""
    lang = st.session_state.get("lang", "en")
    
    # ========================================================================
    # ✅ FIX: Read filters DIRECTLY instead of from session state
    # This ensures real-time synchronization with sidebar
    # ========================================================================
    
    # Get disaster predictions from session state
    df_pred = st.session_state.get('disaster_predictions_df')
    
    # If disaster predictions exist, get current filter values
    if df_pred is not None and not df_pred.empty:
        # Read filters from session state (these should be set by sidebar)
        selected_types = st.session_state.get('sidebar_disaster_types', [])
        selected_region = st.session_state.get('sidebar_region', '(All)')
        selected_country = st.session_state.get('sidebar_country', '(All)')
        year_range = st.session_state.get('sidebar_year_range', None)
        
        # ✅ DEBUG: Show current filter values at top of blood section
        #with st.expander("🔍 Current Active Filters (Debug Info)", expanded=False):
           # st.write(f"**Region Filter:** {selected_region}")
            #st.write(f"**Country Filter:** {selected_country}")
            #st.write(f"**Disaster Types:** {selected_types}")
            #st.write(f"**Year Range:** {year_range}")
    
    # Create tabs for different blood management views
    tabs = st.tabs([
        "📦 Current Inventory",
        "🔮 Demand Forecast",
        "⚠️ Expiry Alerts",
        "🔄 Supply-Demand Matching"
    ])
    
    # ========================================================================
    # TAB 0: Current Inventory (UNCHANGED)
    # ========================================================================
    with tabs[0]:
        st.subheader("🩸 " + _translate("Blood Inventory", lang))
        editable = role in ("admin", "coordinator")
        actor_id = (st.session_state.get("user") or {}).get("user_id")
        
        # Search and filter
        search_query = st.text_input(
            _translate("Search", lang) + " blood", 
            placeholder="Region, country, blood type...", 
            key="blood_search"
        )
        sort_by = st.radio(
            "Sort by", 
            ["Soonest expiry first", "Oldest first (creation order)"], 
            index=0, 
            horizontal=True
        )
        
        # Add blood record
        with st.expander(_translate("Create", lang) + " blood record"):
            suggested_id = _next_numeric_id("B","blood_inventory","id", width=4)
            
            bid = st.text_input("Blood ID", value=suggested_id, key="blood_id_display")
            
            cols = st.columns(5)
            with cols[0]:
                region = st.text_input("Region", key="blood_add_region")
            with cols[1]:
                country = st.text_input("Country", key="blood_add_country")
            with cols[2]:
                blood_type = st.selectbox(
                    "Blood type", 
                    ["O+","O-","A+","A-","B+","B-","AB+","AB-"], 
                    key="blood_add_bt"
                )
            with cols[3]:
                units = st.number_input("Units", value=0, step=1, min_value=0, key="blood_add_units")
            with cols[4]:
                expires = st.text_input("ExpiresOn (YYYY-MM-DD)", value="", key="blood_add_exp")
            
            if st.button(_translate("Create", lang) + " blood", disabled=not editable, key="blood_add_btn"):
                create_blood(region, country, blood_type, int(units), expires, id=(bid or None), actor_id=actor_id)
                st.success("Blood record saved successfully!")
                st.rerun()
        
        # Display inventory
        rows = list_blood()
        
        # Apply search filter
        if search_query.strip():
            q = search_query.lower()
            rows = [r for r in rows if (
                q in (r.get("Region") or "").lower() or
                q in (r.get("Country") or "").lower() or
                q in (r.get("BloodType") or "").lower() or
                q in (r.get("id") or "").lower()
            )]
        
        # Apply sorting
        if sort_by.startswith("Soonest"):
            def sort_key(r):
                exp = r.get("ExpiresOn", "")
                if not exp.strip():
                    return (2, 9999, 9999)
                try:
                    d = dt.datetime.strptime(exp, "%Y-%m-%d").date()
                    days = (d - dt.date.today()).days
                    if days < 0:
                        return (0, days, r.get("Units", 9999))
                    return (1, days, r.get("Units", 9999))
                except:
                    return (2, 9999, 9999)
            rows = sorted(rows, key=sort_key)
        
        if not rows:
            st.info("No blood records.")
        else:
            # Add expiry status
            for r in rows:
                label, color = _expiry_status(r.get("ExpiresOn",""))
                r["_Expiry"] = label
            
            df = pd.DataFrame(rows).reset_index(drop=True)
            df.insert(0, "No.", range(1, len(df)+1))
            h = _auto_height(len(df))
            st.dataframe(
                df[["No.","id","Region","Country","BloodType","Units","ExpiresOn","_Expiry"]],
                use_container_width=True, 
                height=h, 
                hide_index=True
            )
            
            st.download_button(
                "⬇️ " + _translate("Download", lang) + " all blood (CSV)",
                data=pd.DataFrame(rows).to_csv(index=False).encode("utf-8"),
                file_name="aidbot_blood_inventory.csv", 
                mime="text/csv",
                key="dl_all_blood"
            )
            
            # Manage blood records
            st.markdown("#### Manage blood records")
            
            # Pagination
            page_size = 10
            total = len(rows)
            total_pages = max(1, ceil(total / page_size))
            page_key = "blood_page"
            current_page = st.session_state.get(page_key, 1)
            if current_page > total_pages:
                current_page = total_pages
                st.session_state[page_key] = current_page
            
            start_idx = (current_page - 1) * page_size
            end_idx = min(start_idx + page_size, total)
            page_rows = rows[start_idx:end_idx]
            
            bt_order = ["O+","O-","A+","A-","B+","B-","AB+","AB-"]
            for idx, r in enumerate(page_rows):
                with st.expander(f"{r['id']} — {r['Country']} / {r['Region']} · {r['BloodType']}"):
                    c1, c2, c3, c4 = st.columns([0.25, 0.25, 0.25, 0.25])
                    with c1:
                        region = st.text_input("Region", value=r["Region"], key=f"bl_reg_{r['id']}_{current_page}_{idx}")
                    with c2:
                        country = st.text_input("Country", value=r["Country"], key=f"bl_cty_{r['id']}_{current_page}_{idx}")
                    with c3:
                        btype = st.selectbox("Blood type", bt_order,
                                             index=bt_order.index(r["BloodType"]) if r["BloodType"] in bt_order else 0,
                                             key=f"bl_bt_{r['id']}_{current_page}_{idx}")
                    with c4:
                        units = st.number_input("Units", value=int(r["Units"]), step=1, min_value=0, 
                                               key=f"bl_units_{r['id']}_{current_page}_{idx}")
                    ex = st.text_input("ExpiresOn (YYYY-MM-DD)", value=r.get("ExpiresOn",""), 
                                      key=f"bl_exp_{r['id']}_{current_page}_{idx}")
                    b1, b2 = st.columns(2)
                    if b1.button("💾 " + _translate("Save", lang), 
                                 key=f"bl_save_{r['id']}_{current_page}_{idx}", 
                                 disabled=not editable):
                        update_blood(r["id"], {"region": region, "country": country, "blood_type": btype, 
                                              "units": int(units), "expires_on": ex}, actor_id=actor_id)
                        st.success("Blood record updated successfully!")
                    if b2.button("🗑️ " + _translate("Delete", lang), 
                                 key=f"bl_del_{r['id']}_{current_page}_{idx}", 
                                 disabled=not editable):
                        delete_blood(r["id"])
                        st.success("Blood record deleted successfully!")
                        st.rerun()
            
            # Pagination controls
            if total_pages > 1:
                st.markdown("---")
                col1, col2, col3 = st.columns([0.3, 0.4, 0.3])
                with col1:
                    if current_page > 1:
                        if st.button("← Previous", key="blood_prev"):
                            st.session_state[page_key] = current_page - 1
                            st.rerun()
                with col2:
                    st.markdown(f"<div style='text-align:center'>Page {current_page} of {total_pages}</div>", 
                               unsafe_allow_html=True)
                with col3:
                    if current_page < total_pages:
                        if st.button("Next →", key="blood_next"):
                            st.session_state[page_key] = current_page + 1
                            st.rerun()
    
    # ========================================================================
    # TAB 1: Demand Forecast (FIXED)
    # ========================================================================
    with tabs[1]:
        st.subheader("🔮 Blood Demand Forecasting")
        st.caption("Predict blood needs based on disaster predictions")
        
        # Initialize forecaster
        forecaster = BloodDemandForecaster()
        
        # Try to load saved model, or train new one
        if not forecaster.load_model():
            with st.spinner("Training forecasting model..."):
                forecaster.train()
                forecaster.save_model()
        
        # Get disaster predictions from session state
        df_pred = st.session_state.get('disaster_predictions_df')
        
        if df_pred is None or df_pred.empty:
            st.warning("⚠️ No disaster predictions available. Please upload predictions CSV first.")
            st.info("💡 Go to 'Disaster Predictions' section and upload your disaster forecast CSV")
        else:
            # ✅ Get CURRENT filter values from session state
            selected_types = st.session_state.get('sidebar_disaster_types', [])
            selected_region = st.session_state.get('sidebar_region', '(All)')
            selected_country = st.session_state.get('sidebar_country', '(All)')
            year_range = st.session_state.get('sidebar_year_range', None)
            
            # Apply filters
            filtered_pred = df_pred.copy()
            
            # Apply disaster type filter
            if selected_types:
                disaster_col = None
                for col in ['Disaster Type', 'DisasterType', 'Disaster', 'Target']:
                    if col in filtered_pred.columns:
                        disaster_col = col
                        break
                if disaster_col:
                    filtered_pred = filtered_pred[filtered_pred[disaster_col].isin(selected_types)]
            
            # Apply region filter with case-insensitive matching
            if selected_region and selected_region != "(All)":
                region_col = 'Region' if 'Region' in filtered_pred.columns else None
                if region_col:
                    filtered_pred = filtered_pred[
                        filtered_pred[region_col].str.strip().str.lower() == selected_region.strip().lower()
                    ]
            
            # Apply country filter with case-insensitive matching
            if selected_country and selected_country != "(All)":
                country_col = 'Country' if 'Country' in filtered_pred.columns else None
                if country_col:
                    filtered_pred = filtered_pred[
                        filtered_pred[country_col].str.strip().str.lower() == selected_country.strip().lower()
                    ]
            
            # Apply year filter
            if year_range:
                year_col = None
                for col in ['Year', 'Start Year', 'StartYear']:
                    if col in filtered_pred.columns:
                        year_col = col
                        break
                if year_col:
                    filtered_pred[year_col] = pd.to_numeric(filtered_pred[year_col], errors='coerce')
                    y1, y2 = year_range
                    filtered_pred = filtered_pred[filtered_pred[year_col].between(y1, y2, inclusive='both')]
            
            # Show filter summary
            if filtered_pred.empty:
                st.error(f"⚠️ No disasters found for: **{selected_region} / {selected_country}** with disaster type **{selected_types}**")
                st.info("💡 Try adjusting your sidebar filters or selecting (All)")
            else:
                year_display = f"{year_range[0]}-{year_range[1]}" if year_range else "N/A"
                filter_summary = f"**{selected_region}**" if selected_region != "(All)" else "All regions"
                if selected_country != "(All)":
                    filter_summary += f" / **{selected_country}**"
                
                st.info(f"📊 Using **{len(filtered_pred)} filtered disasters** for forecasting "
                       f"(filtered from {len(df_pred)} total) • Region: {filter_summary} • Years: **{year_display}**")
                
                # Convert predictions to format needed by forecaster
                disaster_preds = []
                for _, row in filtered_pred.iterrows():
                    disaster_preds.append({
                        'region': row.get('Region', 'Unknown'),
                        'predicted_disaster': row.get('Disaster Type', 'Unknown'),
                        'confidence': 75,
                        'year': row.get('Year', dt.datetime.now().year)
                    })
                
                # Generate forecast button
                if st.button("Generate Blood Demand Forecast", type="primary", key="generate_forecast_btn"):
                    with st.spinner("Forecasting blood demand..."):
                        demand_forecast = forecaster.predict_demand(disaster_preds[:20])
                        
                        if not demand_forecast.empty:
                            st.success(f"✅ Forecast generated for {len(demand_forecast)} disaster scenarios in **{filter_summary}**")
                            
                            # Display forecast
                            st.dataframe(
                                demand_forecast[[
                                    'region', 'predicted_disaster', 'year',
                                    'predicted_blood_units', 'confidence', 
                                    'alert_level', 'range_min', 'range_max'
                                ]],
                                use_container_width=True,
                                hide_index=True
                            )
                            
                            # Summary statistics
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                total_demand = demand_forecast['predicted_blood_units'].sum()
                                st.metric("Total Predicted Demand", f"{total_demand:,} units")
                            with col2:
                                high_alerts = (demand_forecast['alert_level'] == 'HIGH').sum()
                                st.metric("High Alert Scenarios", high_alerts)
                            with col3:
                                avg_demand = demand_forecast['predicted_blood_units'].mean()
                                st.metric("Average per Disaster", f"{avg_demand:.0f} units")
                            
                            # Download button
                            st.download_button(
                                "⬇️ Download Forecast (CSV)",
                                data=demand_forecast.to_csv(index=False).encode("utf-8"),
                                file_name=f"blood_demand_forecast_{dt.datetime.now().strftime('%Y%m%d')}.csv",
                                mime="text/csv",
                                key="download_forecast_csv"
                            )
                        else:
                            st.warning("No forecast generated. Check disaster predictions data.")
    
    # ========================================================================
    # TAB 2: Expiry Alerts (UNCHANGED)
    # ========================================================================
    with tabs[2]:
        st.subheader("⚠️ Blood Expiry Alerts")
        st.caption("Identify blood units at risk of expiring")
        
        inventory = read_blood_df()
        
        if inventory.empty:
            st.info("No blood inventory to check.")
        else:
            forecaster = BloodDemandForecaster()
            days_threshold = st.slider("Alert threshold (days)", 1, 14, 7, key="expiry_threshold_slider")
            at_risk = forecaster.check_expiry_waste(inventory, days_threshold)
            
            if at_risk.empty:
                st.success(f"✅ No blood expiring within {days_threshold} days!")
            else:
                st.error(f"🚨 {len(at_risk)} blood units expiring soon!")
                
                # Display at-risk inventory
                st.dataframe(at_risk, use_container_width=True, hide_index=True)
                
                # Summary by status
                col1, col2 = st.columns(2)
                with col1:
                    urgent = (at_risk['Status'] == 'URGENT').sum()
                    st.metric("🔴 Urgent (≤3 days)", urgent)
                with col2:
                    warning = (at_risk['Status'] == 'WARNING').sum()
                    st.metric("🟡 Warning (4-7 days)", warning)
                
                # Recommendations
                st.markdown("### 💡 Recommendations")
                for _, row in at_risk.iterrows():
                    if row['DaysLeft'] <= 3:
                        st.error(
                            f"🔴 URGENT: {row['Units']} units of {row['BloodType']} "
                            f"in {row['Region']} expires in {row['DaysLeft']} days! "
                            f"Consider immediate redistribution."
                        )
                    else:
                        st.warning(
                            f"🟡 {row['Units']} units of {row['BloodType']} "
                            f"in {row['Region']} expires in {row['DaysLeft']} days."
                        )
    
    # ========================================================================
    # TAB 3: Supply-Demand Matching (FIXED WITH FILTER SYNC)
    # ========================================================================
    with tabs[3]:
        st.subheader("🔄 Supply-Demand Matching")
        st.caption("Match regional blood supply with predicted demand")
        
        inventory = read_blood_df()
        df_pred = st.session_state.get('disaster_predictions_df')
        
        if inventory.empty:
            st.warning("⚠️ No blood inventory data available.")
        elif df_pred is None or df_pred.empty:
            st.warning("⚠️ No disaster predictions available. Upload predictions CSV first.")
        else:
            forecaster = BloodDemandForecaster()
            if not forecaster.load_model():
                forecaster.train()
            
            # ✅ Get CURRENT filter values from session state
            selected_types = st.session_state.get('sidebar_disaster_types', [])
            selected_region = st.session_state.get('sidebar_region', '(All)')
            selected_country = st.session_state.get('sidebar_country', '(All)')
            year_range = st.session_state.get('sidebar_year_range', None)
            
            # Apply filters
            filtered_pred = df_pred.copy()
            
            # Apply disaster type filter
            if selected_types:
                disaster_col = None
                for col in ['Disaster Type', 'DisasterType', 'Disaster', 'Target']:
                    if col in filtered_pred.columns:
                        disaster_col = col
                        break
                if disaster_col:
                    filtered_pred = filtered_pred[filtered_pred[disaster_col].isin(selected_types)]
            
            # Apply region filter with case-insensitive matching
            if selected_region and selected_region != "(All)":
                region_col = 'Region' if 'Region' in filtered_pred.columns else None
                if region_col:
                    filtered_pred = filtered_pred[
                        filtered_pred[region_col].str.strip().str.lower() == selected_region.strip().lower()
                    ]
            
            # Apply country filter with case-insensitive matching
            if selected_country and selected_country != "(All)":
                country_col = 'Country' if 'Country' in filtered_pred.columns else None
                if country_col:
                    filtered_pred = filtered_pred[
                        filtered_pred[country_col].str.strip().str.lower() == selected_country.strip().lower()
                    ]
            
            # Apply year filter
            if year_range:
                year_col = None
                for col in ['Year', 'Start Year', 'StartYear']:
                    if col in filtered_pred.columns:
                        year_col = col
                        break
                if year_col:
                    filtered_pred[year_col] = pd.to_numeric(filtered_pred[year_col], errors='coerce')
                    y1, y2 = year_range
                    filtered_pred = filtered_pred[filtered_pred[year_col].between(y1, y2, inclusive='both')]
            
            # Show filter summary
            if filtered_pred.empty:
                st.error(f"⚠️ No disasters found for: **{selected_region} / {selected_country}** with disaster type **{selected_types}**")
                st.info("💡 Try adjusting your sidebar filters")
            else:
                year_display = f"{year_range[0]}-{year_range[1]}" if year_range else "N/A"
                filter_summary = f"**{selected_region}**" if selected_region != "(All)" else "All regions"
                if selected_country != "(All)":
                    filter_summary += f" / **{selected_country}**"
                
                st.info(f"📊 Analyzing **{len(filtered_pred)} filtered disasters** "
                       f"(from {len(df_pred)} total) • Region: {filter_summary} • Years: **{year_display}**")
                
                # ✅ Filter blood inventory by same region/country (with case-insensitive matching)
                filtered_inventory = inventory.copy()
                
                if selected_region and selected_region != "(All)":
                    filtered_inventory = filtered_inventory[
                        filtered_inventory['Region'].str.strip().str.lower() == selected_region.strip().lower()
                    ]
                
                if selected_country and selected_country != "(All)":
                    filtered_inventory = filtered_inventory[
                        filtered_inventory['Country'].str.strip().str.lower() == selected_country.strip().lower()
                    ]
                
                # Show current inventory summary
                if filtered_inventory.empty:
                    if selected_region == "(All)" and selected_country == "(All)":
                        st.warning(f"⚠️ No blood inventory data available in system")
                    else:
                        st.warning(f"⚠️ No blood inventory found for {selected_region}/{selected_country}")
                    total_supply = 0
                else:
                    total_supply = int(filtered_inventory['Units'].sum())
                    
                    if selected_region == "(All)" and selected_country == "(All)":
                        unique_regions = filtered_inventory['Region'].nunique()
                        st.success(f"✅ Total supply across **{unique_regions} regions**: **{total_supply} units**")
                    else:
                        st.success(f"✅ Supply in {filter_summary}: **{total_supply} units**")
                
                # Convert filtered predictions
                disaster_preds = []
                for _, row in filtered_pred.iterrows():
                    disaster_preds.append({
                        'region': row.get('Region', 'Unknown'),
                        'predicted_disaster': row.get('Disaster Type', 'Unknown'),
                        'confidence': 75,
                        'year': row.get('Year', dt.datetime.now().year)
                    })
                
                if st.button("🔍 Analyze Supply vs Demand", type="primary", key="analyze_supply_demand_btn"):
                    with st.spinner("Analyzing..."):
                        # Generate demand forecast (using filtered disasters)
                        demand_forecast = forecaster.predict_demand(disaster_preds[:50])
                        
                        # Match with filtered inventory
                        recommendations = forecaster.match_supply_demand(filtered_inventory, demand_forecast)
                        
                        if recommendations:
                            # Filter out recommendations with 0 supply AND 0 demand
                            recommendations = [r for r in recommendations 
                                             if r['current_supply'] > 0 or r['predicted_demand'] > 0]
                            
                            if not recommendations:
                                st.info("No actionable recommendations. All regions have 0 supply and 0 demand.")
                            else:
                                st.success(f"✅ Analysis complete for {len(recommendations)} disaster scenarios in **{filter_summary}**")
                                
                                # Display recommendations
                                rec_df = pd.DataFrame(recommendations)
                                st.dataframe(
                                    rec_df[[
                                        'region', 'predicted_disaster', 'current_supply',
                                        'predicted_demand', 'balance', 'coverage_percent',
                                        'status', 'action', 'priority'
                                    ]],
                                    use_container_width=True,
                                    hide_index=True
                                )
                                
                                # Summary metrics
                                col1, col2, col3, col4 = st.columns(4)
                                with col1:
                                    total_demand = int(rec_df['predicted_demand'].sum())
                                    st.metric("📊 Total Demand", f"{total_demand} units")
                                with col2:
                                    total_supply_matched = int(rec_df['current_supply'].sum())
                                    st.metric("📦 Matched Supply", f"{total_supply_matched} units")
                                with col3:
                                    gap = total_supply_matched - total_demand
                                    st.metric("⚖️ Gap", f"{gap:+d} units", 
                                            delta_color="inverse" if gap < 0 else "normal")
                                with col4:
                                    shortages = sum(1 for r in recommendations if '🔴' in r['status'])
                                    st.metric("🔴 Shortages", shortages)
                                
                                # Critical alerts
                                st.markdown("### 🚨 Critical Actions Needed")
                                shortage_found = False
                                for rec in recommendations:
                                    if '🔴' in rec['status']:
                                        shortage_found = True
                                        st.error(
                                            f"**{rec['region']}** ({rec['predicted_disaster']}): {rec['action']} "
                                            f"(Coverage: {rec['coverage_percent']:.1f}%)"
                                        )
                                
                                if not shortage_found:
                                    st.success("✅ No critical shortages detected!")
                                
                                # Redistribution opportunities
                                surplus_recs = [r for r in recommendations if '🟢' in r['status']]
                                if surplus_recs:
                                    st.markdown("### ✅ Redistribution Opportunities")
                                    for rec in surplus_recs:
                                        st.success(
                                            f"**{rec['region']}**: {rec['action']} "
                                            f"(Surplus: {rec['balance']} units)"
                                        )
                        else:
                            st.info("No recommendations generated. Check that both inventory and predictions exist.")
# ---------- Resources (ENHANCED) ----------
def resources_tab(role: str):
    lang = st.session_state.get("lang", "en")
    st.subheader("🚚 " + _translate("Resource Allocation", lang))
    st.caption("**How it works:** Upload a CSV or edit the table directly. Click 'Save resources' to persist changes. The table shows current resource allocation by region/country.")
    editable = role in ("admin", "coordinator")
    actor_id = (st.session_state.get("user") or {}).get("user_id")

    current = read_resources_df()
    upl = st.file_uploader("Upload resources CSV (optional)", type=["csv"], key="resources_csv")
    if upl is not None and editable:
        try:
            uploaded = pd.read_csv(io.BytesIO(upl.read()))
            expected = ["Region","Country","Volunteers","Trucks","Boats","MedKits","FoodKits","WaterKits"]
            missing = [c for c in expected if c not in uploaded.columns]
            if missing:
                st.error(f"CSV missing required columns: {', '.join(missing)}")
            else:
                current = uploaded
                st.success("CSV loaded into table. Click 'Save resources' to persist.")
        except Exception as e:
            st.error(f"Could not read CSV: {e}")

    expected = ["Region","Country","Volunteers","Trucks","Boats","MedKits","FoodKits","WaterKits"]
    if current.empty:
        current = pd.DataFrame(columns=expected)
    else:
        for c in expected:
            if c not in current.columns:
                current[c] = 0 if c not in ("Region","Country") else ""

    rows_now = len(current)
    h = _auto_height(rows_now)
    edited = st.data_editor(
        current[expected],
        num_rows="dynamic",
        use_container_width=True,
        disabled=not editable,
        key="resources_editor",
        height=h
    )
    # Auto-remove invalid/empty rows
    edited = edited[
        (edited['Region'].notna()) & 
        (edited['Region'].astype(str).str.strip() != '') &
        (edited['Region'].astype(str).str.strip() != '0') &
        (edited['Country'].notna()) & 
        (edited['Country'].astype(str).str.strip() != '') &
        (edited['Country'].astype(str).str.strip() != '0')
    ].copy()

    col_actions = st.columns([0.69, 0.31])
    with col_actions[0]:
        if editable and st.button(_translate("Save", lang) + " resources", type="primary"):
            write_resources_df(edited.fillna(0), actor_id=actor_id)
            st.success("Resources saved successfully!")
            st.rerun()
    with col_actions[1]:
        st.download_button(
            "⬇️ " + _translate("Download", lang) + " all resources (CSV)",
            data=edited.to_csv(index=False).encode("utf-8"),
            file_name="aidbot_resources.csv",
            mime="text/csv",
            key="dl_resources"
        )
    # ========== Original: Create Resource Row ==========
    st.markdown("---")
    with st.expander(_translate("Create", lang) + " resource row"):
        r1, r2, r3, r4, r5, r6, r7 = st.columns(7)
        with r1: reg = st.text_input("Region", key="res_add_reg")
        with r2: cty = st.text_input("Country", key="res_add_cty")
        with r3: vol = st.number_input("Volunteers", value=0, step=1, min_value=0, key="res_add_vol")
        with r4: tru = st.number_input("Trucks", value=0, step=1, min_value=0, key="res_add_tru")
        with r5: boa = st.number_input("Boats", value=0, step=1, min_value=0, key="res_add_boa")
        with r6: med = st.number_input("MedKits", value=0, step=1, min_value=0, key="res_add_med")
        with r7: fod = st.number_input("FoodKits", value=0, step=1, min_value=0, key="res_add_food")
        wat = st.number_input("WaterKits", value=0, step=1, min_value=0, key="res_add_water")
        if st.button(_translate("Create", lang) + " resource", disabled=not editable, key="res_add_btn"):
            df = read_resources_df()
            if df.empty:
                df = pd.DataFrame(columns=["Region","Country","Volunteers","Trucks","Boats","MedKits","FoodKits","WaterKits"])
            new = pd.DataFrame([{
                "Region": reg, "Country": cty, "Volunteers": int(vol), "Trucks": int(tru),
                "Boats": int(boa), "MedKits": int(med), "FoodKits": int(fod), "WaterKits": int(wat)
            }])
            df = pd.concat([df, new], ignore_index=True)
            write_resources_df(df.fillna(0), actor_id=actor_id)
            st.success("Resource row added successfully!")
            for k in ["res_add_reg","res_add_cty","res_add_vol","res_add_tru","res_add_boa","res_add_med","res_add_food","res_add_water"]:
                if k in st.session_state: del st.session_state[k]
            st.rerun()
    # ========== ENHANCEMENT 1: Resource Status Alerts ==========
    st.markdown("---")
    st.markdown("### ⚠️ Resource Status Alerts")
    st.caption("Automated alerts for low resource levels across regions")
    
    if not edited.empty:
        # Define thresholds
        THRESHOLDS = {
            "Volunteers": {"critical": 10, "warning": 70},
            "Trucks": {"critical": 1, "warning": 7},
            "Boats": {"critical": 0, "warning": 7},
            "MedKits": {"critical": 50, "warning": 100},
            "FoodKits": {"critical": 100, "warning": 100},
            "WaterKits": {"critical": 100, "warning": 100}
        }
        
        alerts = []
        
        for _, row in edited.iterrows():
            # Skip invalid/empty rows
            country = str(row.get('Country', '')).strip()
            region = str(row.get('Region', '')).strip()
            
            # Skip if country/region is empty, "0", "None", or invalid
            if not country or not region or country in ['0', 'None', 'nan'] or region in ['0', 'None', 'nan']:
                continue
            
            location = f"{country} - {region}"
            
            for resource, thresholds in THRESHOLDS.items():
                # Safe conversion: handle NaN, None, empty strings
                raw_value = row.get(resource, 0)
                try:
                    value = int(float(raw_value)) if pd.notna(raw_value) else 0
                except (ValueError, TypeError):
                    value = 0
                
                if value <= thresholds["critical"]:
                    alerts.append({
                        "Level": "🔴 Critical",
                        "Location": location,
                        "Resource": resource,
                        "Current": value,
                        "Threshold": thresholds["critical"],
                        "Priority": 3
                    })
                elif value <= thresholds["warning"]:
                    alerts.append({
                        "Level": "🟡 Warning",
                        "Location": location,
                        "Resource": resource,
                        "Current": value,
                        "Threshold": thresholds["warning"],
                        "Priority": 2
                    })
        
        if alerts:
            # Sort by priority (critical first)
            alerts_df = pd.DataFrame(alerts).sort_values("Priority", ascending=False)
            
            # Show summary metrics
            col1, col2, col3 = st.columns(3)
            critical_count = len([a for a in alerts if "Critical" in a["Level"]])
            warning_count = len([a for a in alerts if "Warning" in a["Level"]])
            
            with col1:
                st.metric("🔴 Critical Alerts", critical_count)
            with col2:
                st.metric("🟡 Warning Alerts", warning_count)
            with col3:
                st.metric("✅ Regions Checked", len(edited))
            
            # Display alerts table
            st.dataframe(
                alerts_df[["Level", "Location", "Resource", "Current", "Threshold"]],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.success("✅ All regions have adequate resource levels!")
    else:
        st.info("Upload or create resources to see alerts.")
    
    # ========== ENHANCEMENT 2: Deployment Recommendations ==========
    st.markdown("---")
    st.markdown("### 🎯 Deployment Recommendations")
    st.caption("Smart matching of resources to open emergency cases")
    
    if not edited.empty:
        open_cases = [c for c in list_cases() 
                      if c.get("status") in ["new", "acknowledged", "en_route"]]
        
        if open_cases:
            recommendations = []
            
            for case in open_cases[:15]:  # Limit to 15 cases for performance
                case_country = case.get("country", "").strip()
                case_region = case.get("region", "").strip()
                
                # Match by country OR region
                matches = edited[
                    (edited["Country"].str.strip().str.lower() == case_country.lower()) |
                    (edited["Region"].str.strip().str.lower() == case_region.lower())
                ]
                
                if not matches.empty:
                    match = matches.iloc[0]
                    
                    volunteers = int(match.get("Volunteers", 0))
                    trucks = int(match.get("Trucks", 0))
                    medkits = int(match.get("MedKits", 0))
                    
                    # Deployment readiness logic
                    can_deploy_volunteers = volunteers >= 5
                    can_deploy_transport = trucks >= 1
                    can_deploy_supplies = medkits >= 10
                    
                    if can_deploy_volunteers and can_deploy_transport and can_deploy_supplies:
                        status = "✅ Ready"
                        status_color = "🟢"
                    elif can_deploy_volunteers or can_deploy_supplies:
                        status = "⚠️ Limited"
                        status_color = "🟡"
                    else:
                        status = "❌ Insufficient"
                        status_color = "🔴"
                    
                    recommendations.append({
                        "Case ID": case["case_id"],
                        "Location": f"{case_country}, {case_region}",
                        "Status": case.get("status", "new"),
                        "Volunteers": volunteers,
                        "Trucks": trucks,
                        "MedKits": medkits,
                        "Deployment": status,
                        "Priority": status_color
                    })
                else:
                    recommendations.append({
                        "Case ID": case["case_id"],
                        "Location": f"{case_country}, {case_region}",
                        "Status": case.get("status", "new"),
                        "Volunteers": 0,
                        "Trucks": 0,
                        "MedKits": 0,
                        "Deployment": "❌ No Match",
                        "Priority": "🔴"
                    })
            
            if recommendations:
                rec_df = pd.DataFrame(recommendations)
                
                # Summary metrics
                col1, col2, col3 = st.columns(3)
                ready = len(rec_df[rec_df["Deployment"] == "✅ Ready"])
                limited = len(rec_df[rec_df["Deployment"] == "⚠️ Limited"])
                insufficient = len(rec_df[rec_df["Deployment"].str.contains("Insufficient|No Match")])
                
                with col1:
                    st.metric("✅ Ready for Deployment", ready)
                with col2:
                    st.metric("⚠️ Limited Resources", limited)
                with col3:
                    st.metric("❌ Cannot Deploy", insufficient)
                
                # Display recommendations
                st.dataframe(
                    rec_df[["Case ID", "Location", "Status", "Volunteers", "Trucks", "MedKits", "Deployment"]],
                    use_container_width=True,
                    hide_index=True
                )
                
                # Action items
                st.markdown("#### 💡 Action Items")
                if insufficient > 0:
                    st.error(f"🚨 **{insufficient} cases** cannot be deployed due to lack of resources. Consider resource redistribution.")
                if limited > 0:
                    st.warning(f"⚠️ **{limited} cases** have limited resources. Monitor closely.")
                if ready > 0:
                    st.success(f"✅ **{ready} cases** are ready for immediate deployment!")
                
                st.info("💡 **Tip:** Assign volunteers to cases from the 'Cases' tab to activate deployment.")
            else:
                st.success("No deployment recommendations needed at this time.")
        else:
            st.info("No open cases requiring deployment.")
    else:
        st.info("Add resources to see deployment recommendations.")
    
    # ========== ENHANCEMENT 3: Regional Coverage Analysis ==========
    st.markdown("---")
    st.markdown("### 📊 Regional Coverage Analysis")
    st.caption("Visual overview of resource distribution across regions")
    
    if not edited.empty and len(edited) > 0:
        # Group by region
        if "Region" in edited.columns:
            regional_summary = edited.groupby("Region").agg({
                "Volunteers": "sum",
                "Trucks": "sum",
                "MedKits": "sum",
                "FoodKits": "sum",
                "WaterKits": "sum"
            }).reset_index()
            
            # Create visualization
            st.markdown("#### Resource Distribution by Region")
            
            # Bar chart for volunteers
            chart_volunteers = alt.Chart(regional_summary).mark_bar(color='#e33b3b').encode(
                x=alt.X('Region:N', sort='-y', title='Region'),
                y=alt.Y('Volunteers:Q', title='Total Volunteers'),
                tooltip=['Region', 'Volunteers']
            ).properties(height=300, title="Volunteers by Region")
            
            st.altair_chart(chart_volunteers, use_container_width=True)
            
            # Summary table
            st.dataframe(regional_summary, use_container_width=True, hide_index=True)

# ---------- Predictions ----------
def pick(df, *names):
    for n in names:
        if n in df.columns: return n
    return None

def predictions_tabs(df):
    # ✅ CSV Validation Layer (Prevents crashes from missing columns)
    required_cols = ["Year", "Region", "Country", "Disaster Type"]
    missing = [col for col in required_cols if col not in df.columns]

    if missing:
        st.warning(f"⚠️ Missing columns detected: {', '.join(missing)}")
        st.info("Please upload a file that includes these columns for full functionality.")
        st.stop()

    # Auto-repair (for usability)
    import datetime
    if "Year" not in df.columns:
        df["Year"] = datetime.datetime.now().year
        st.info("✅ Added missing 'Year' column automatically with current year.")

    TRUE_COL    = pick(df, "Disaster Type","True","Target","Disaster_Type")
    TREE_COL    = pick(df, "Tree")
    NN_COL      = pick(df, "Neural Network","NeuralNetwork","NN")
    YEAR_COL    = pick(df, "Year","Start Year","StartYear")
    REGION_COL  = pick(df, "Region")
    COUNTRY_COL = pick(df, "Country")
    LAT_COL     = pick(df, "Latitude","lat","Lat")
    LON_COL     = pick(df, "Longitude","lon","Lng","Long")

    year_all_nan = True
    if YEAR_COL:
        df[YEAR_COL] = pd.to_numeric(df[YEAR_COL], errors="coerce")
        year_all_nan = df[YEAR_COL].isna().all()

    # Normalize labels/preds & drop junk rows
    if TRUE_COL:
        BAD_TRUE = {"class",
                    "Drought Earthquake Epidemic Extreme\\ temperature Flood Other Landslide Storm Wildfire",
                    ""}
        def _clean(s): return None if pd.isna(s) else str(s).strip()
        for c in [TRUE_COL, TREE_COL, NN_COL]:
            if c and c in df.columns:
                df[c] = df[c].map(_clean)
        df = df[~df[TRUE_COL].isin(BAD_TRUE)].copy()

    # ============================================================
    # 🎯 Sidebar Filters – Fully Corrected (for Disaster, Region, Country)
    # ============================================================
    st.sidebar.header("Filters")

    import re

    def clean_label(text):
        """Remove slashes, extra spaces, and invalid entries."""
        if not isinstance(text, str):
            return None
        t = text.strip().replace("\\", "").replace("  ", " ")
        if not t or t.lower() in ["nan", "none", "(dry)"]:
            return None
        return t

    def clean_disaster_types(series):
        """Clean and extract valid disaster type names."""
        items = []
        for val in series.dropna().astype(str):
            val = val.strip().replace("\\", "")
            # skip known combined long string
            if "Drought Earthquake Epidemic" in val:
                continue
            # split only on punctuation, NOT spaces
            parts = [p.strip() for p in re.split(r'[;,|]', val) if p.strip()]
            items.extend(parts)
        # remove duplicates and bad entries
        return sorted(set(clean_label(x) for x in items if clean_label(x)))

    def clean_region_country(series):
        """Clean Region/Country columns and remove combined multi-items."""
        items = []
        for val in series.dropna().astype(str):
            val = val.strip().replace("\\", "")
            # skip long joined entries like 'Central Asia Eastern Asia ...'
            if "Eastern Asia" in val and "Western Asia" in val:
                continue
            if "Afghanistan" in val and "Yemen" in val:
                continue
            # split only if comma/semicolon/pipe — not spaces
            parts = [p.strip() for p in re.split(r'[;,|]', val) if p.strip()]
            items.extend(parts)
        unique = sorted(set(clean_label(x) for x in items if clean_label(x)))
        return ["(All)"] + unique

    # Apply cleaning
    if TRUE_COL:
        dtype_opts = clean_disaster_types(df[TRUE_COL])
    else:
        pool = []
        if TREE_COL:
            pool += df[TREE_COL].dropna().astype(str).tolist()
        if NN_COL:
            pool += df[NN_COL].dropna().astype(str).tolist()
        dtype_opts = clean_disaster_types(pd.Series(pool))

    region_opts = clean_region_country(df[REGION_COL]) if REGION_COL else ["(All)"]
    country_opts = clean_region_country(df[COUNTRY_COL]) if COUNTRY_COL else ["(All)"]

    # UI widgets
    selected_types = st.sidebar.multiselect(
        "Disaster type",
        options=dtype_opts,
        default=[],
        placeholder="Choose disaster type…"
    )
    st.session_state['sidebar_disaster_types'] = selected_types
    selected_region = st.sidebar.selectbox(
        "Region",
        options=region_opts,
        index=0,
        placeholder="Choose region…"
    )
    st.session_state['sidebar_region'] = selected_region

    selected_country = st.sidebar.selectbox(
        "Country",
        options=country_opts,
        index=0,
        placeholder="Choose country…"
    )
    st.session_state['sidebar_country'] = selected_country

    # Year filter
    if not year_all_nan:
        y_min = int(np.nanmin(df[YEAR_COL].values))
        y_max = int(np.nanmax(df[YEAR_COL].values))
        if y_min == y_max:
            y_min = y_max - 1
        year_range = st.sidebar.slider("Year", min_value=y_min, max_value=y_max, value=(y_min, y_max))
    else:
        year_range = None
        st.session_state['sidebar_disaster_types'] = selected_types
        st.session_state['sidebar_region'] = selected_region
        st.session_state['sidebar_country'] = selected_country
        st.session_state['sidebar_year_range'] = year_range if not year_all_nan else None
        st.sidebar.caption("No usable Year column detected; year filter disabled.")

    def apply_filters(df_src: pd.DataFrame) -> pd.DataFrame:
        mask = pd.Series(True, index=df_src.index)
        if selected_types:
            if TRUE_COL: mask &= df_src[TRUE_COL].astype(str).isin(selected_types)
            else:
                m = pd.Series(False, index=df_src.index)
                if TREE_COL:
                    m |= df_src[TREE_COL].astype(str).isin(selected_types)
                if NN_COL:
                    m |= df_src[NN_COL].astype(str).isin(selected_types)
                mask &= m
        if REGION_COL and selected_region != "(All)": mask &= (df_src[REGION_COL].astype(str) == selected_region)
        if COUNTRY_COL and selected_country != "(All)": mask &= (df_src[COUNTRY_COL].astype(str) == selected_country)
        if year_range and not year_all_nan:
            y1, y2 = year_range
            mask &= df_src[YEAR_COL].between(y1, y2, inclusive="both")
        return df_src[mask].copy()

    def class_dist_chart(data: pd.DataFrame, title="Class distribution"):
        st.subheader(title)
        TRUE = TRUE_COL
        if TRUE and not data.empty:
            cd = data[TRUE].value_counts().reset_index()
            cd.columns = ["Disaster Type","Count"]
            chart = (alt.Chart(cd).mark_bar()
                     .encode(x=alt.X("Disaster Type:N", sort="-y"),
                             y=alt.Y("Count:Q"),
                             tooltip=["Disaster Type","Count"])
                     .properties(height=240))
            st.altair_chart(chart, use_container_width=True)
        else:
            st.caption("No 'Disaster Type' column found (or no rows).")

    def confusion_table(data: pd.DataFrame, title="Confusion matrix (Tree)"):
        st.subheader(title)
        if TRUE_COL and TREE_COL and not data.empty:
            y_true=data[TRUE_COL].astype(str)
            y_pred=data[TREE_COL].astype(str)
            labels=sorted(list(set(y_true.unique()) | set(y_pred.unique())))
            if len(labels) > 1:
                cm=confusion_matrix(y_true,y_pred,labels=labels)
                cm_df=pd.DataFrame(cm,index=labels,columns=labels)
                st.dataframe(cm_df,use_container_width=True, hide_index=True)
            else:
                st.caption("Not enough classes to build a confusion matrix.")
        else:
            st.caption("Need both true labels and Tree predictions.")

    def accuracy_block(data: pd.DataFrame):
        if TRUE_COL and not data.empty:
            blocks = []
            if TREE_COL in data.columns:
                a = accuracy_score(data[TRUE_COL].astype(str), data[TREE_COL].astype(str))
                blocks.append(("Tree accuracy", f"{a*100:.1f}%"))
            if NN_COL and NN_COL in data.columns:
                a = accuracy_score(data[TRUE_COL].astype(str), data[NN_COL].astype(str))
                blocks.append(("Neural Net accuracy", f"{a*100:.1f}%"))
            if blocks:
                c = st.columns(len(blocks))
                for i, (h, v) in enumerate(blocks):
                    with c[i]:
                        st.markdown(f'<div class="kpi" style="background: linear-gradient(135deg, rgba(227,59,59,0.1) 0%, rgba(227,59,59,0.05) 100%); border-left: 4px solid #e33b3b;"><h3 style="color: #e33b3b;">{h}</h3><p style="color: #e33b3b;">{v}</p></div>', unsafe_allow_html=True)

    def map_block(data: pd.DataFrame, title="Map (records with coordinates)"):
        st.subheader(title)
        if data is None or data.empty:
            st.caption("No rows to map.")
            return
        lat_col, lon_col = LAT_COL, LON_COL
        if (lat_col not in data.columns) or (lon_col not in data.columns):
            st.info("This CSV has no Latitude/Longitude columns to map.")
            return
        lat = pd.to_numeric(data[lat_col], errors="coerce")
        lon = pd.to_numeric(data[lon_col], errors="coerce")
        mask = lat.between(-90, 90) & lon.between(-180, 180)
        mdf = pd.DataFrame({"lat": lat[mask], "lon": lon[mask]}).dropna()
        if mdf.empty:
            st.info("No valid numeric coordinates found in filtered data.")
            return
        
        # Check for Mapbox token
        if MAPBOX_TOKEN:
            # Option to toggle between heatmap and binned
            map_type = st.radio("Map visualization", ["Heatmap (Mapbox)", "Binned heat (Altair)"], index=0, horizontal=True)
            
            if map_type.startswith("Heatmap"):
                st.caption(f"Showing {len(mdf):,} disaster locations as a density heatmap. Areas with more incidents appear brighter.")
                layer = pdk.Layer(
                    "HeatmapLayer",
                    data=mdf,
                    get_position=["lon", "lat"],
                    aggregation='"MEAN"',
                    get_weight=1,
                    radiusPixels=60,
                )
                deck = pdk.Deck(
                    layers=[layer],
                    initial_view_state=pdk.ViewState(
                        latitude=float(mdf["lat"].mean()),
                        longitude=float(mdf["lon"].mean()),
                        zoom=3,
                        pitch=0,
                    ),
                    map_provider="mapbox",
                    map_style="mapbox://styles/mapbox/dark-v11",
                    api_keys={"mapbox": MAPBOX_TOKEN},
                )
                st.pydeck_chart(deck, use_container_width=True)
            else:
                # Altair binned heat
                st.caption(f"Showing {len(mdf):,} disaster locations binned by latitude/longitude. Darker cells indicate more incidents.")
                heat = (
                    alt.Chart(mdf)
                    .mark_rect()
                    .encode(
                        x=alt.X("lon:Q", bin=alt.Bin(maxbins=30), scale=alt.Scale(domain=[-180, 180]), title="Longitude"),
                        y=alt.Y("lat:Q", bin=alt.Bin(maxbins=30), scale=alt.Scale(domain=[-90, 90]), title="Latitude"),
                        color=alt.Color("count():Q", title="Count", scale=alt.Scale(scheme="reds")),
                        tooltip=[alt.Tooltip("count():Q", title="Count")]
                    )
                    .properties(height=320)
                )
                st.altair_chart(heat, use_container_width=True)
        else:
            # No token: Altair only
            st.caption(f"Showing {len(mdf):,} disaster locations binned by latitude/longitude. Darker cells indicate more incidents. (Set MAPBOX_TOKEN for interactive heatmap.)")
            heat = (
                alt.Chart(mdf)
                .mark_rect()
                .encode(
                    x=alt.X("lon:Q", bin=alt.Bin(maxbins=30), scale=alt.Scale(domain=[-180, 180]), title="Longitude"),
                    y=alt.Y("lat:Q", bin=alt.Bin(maxbins=30), scale=alt.Scale(domain=[-90, 90]), title="Latitude"),
                    color=alt.Color("count():Q", title="Count", scale=alt.Scale(scheme="reds")),
                    tooltip=[alt.Tooltip("count():Q", title="Count")]
                )
                .properties(height=320)
            )
            st.altair_chart(heat, use_container_width=True)

    def table_and_download(data: pd.DataFrame, title="Predictions table", suffix=""):
        st.subheader(f"{title}{suffix}")
        cols_pref=[TRUE_COL,TREE_COL,NN_COL,YEAR_COL,COUNTRY_COL,REGION_COL,LAT_COL,LON_COL]
        show_cols=[c for c in cols_pref if c and c in data.columns] or data.columns.tolist()
        st.dataframe(data[show_cols].head(1000),use_container_width=True, hide_index=True)
        st.download_button(f"Download {('filtered ' if suffix else '')}data (CSV)",
                           data=data.to_csv(index=False).encode("utf-8"),
                           file_name=f"aidbot_{'filtered_' if suffix else ''}predictions.csv",
                           mime="text/csv")

    # Tabs: Overview / Filtered / Map / Trained model
    tabs = st.tabs(["Overview","Filtered analysis","Map","Trained Model & Model Card", "Future Simulation"])
    with tabs[0]:
        st.markdown("#### Overview (all data)")
        
        # Collect all KPIs
        kpis = [("TOTAL ROWS", len(df))]
        if TRUE_COL and not df.empty:
            if TREE_COL in df.columns:
                tree_acc = accuracy_score(df[TRUE_COL].astype(str), df[TREE_COL].astype(str))
                kpis.append(("TREE ACCURACY", f"{tree_acc*100:.1f}%"))
            if NN_COL and NN_COL in df.columns:
                nn_acc = accuracy_score(df[TRUE_COL].astype(str), df[NN_COL].astype(str))
                kpis.append(("NEURAL NET ACCURACY", f"{nn_acc*100:.1f}%"))
        
        # Display KPIs in one row
        cols = st.columns(len(kpis))
        for i, (label, value) in enumerate(kpis):
            with cols[i]:
                st.markdown(f"""
                <div style="
                    background: linear-gradient(135deg, rgba(227,59,59,0.1) 0%, rgba(227,59,59,0.05) 100%);
                    border-left: 4px solid #e33b3b;
                    border-radius: 12px;
                    padding: 1.5rem 1rem;
                    text-align: center;
                    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
                ">
                    <h3 style="
                        font-size: 0.875rem;
                        color: #e33b3b;
                        margin: 0 0 0.5rem 0;
                        font-weight: 500;
                        text-transform: uppercase;
                        letter-spacing: 0.025em;
                    ">{label}</h3>
                    <p style="
                        font-size: 2rem;
                        font-weight: 700;
                        color: #e33b3b;
                        margin: 0;
                    ">{value}</p>
                </div>
                """, unsafe_allow_html=True)
        
        st.divider()
        table_and_download(df,"Predictions table")

    with tabs[1]:
        base = apply_filters(df)
        if base.empty:
            st.info("No filters selected or no matching rows.")
        else:
            st.markdown("#### KPIs (filtered)")
            st.write(f"Rows: *{len(base)}*")
            accuracy_block(base)
            st.divider()
            confusion_table(base,"Confusion matrix (Tree)")
            st.divider()
            table_and_download(base,"Predictions table"," (filtered)")
            # Ops Planner bridge
            st.markdown("### Ops Planner")
            reg = pick(base, "Region")
            cty = pick(base, "Country")
            if reg and cty:
                prev = (base.groupby([reg, cty], dropna=False).size().reset_index(name="Incidents"))
                prev["Trucks"]    = np.ceil(prev["Incidents"] / 20).astype(int)
                prev["MedKits"]   = (prev["Incidents"] * 10).astype(int)
                prev["WaterKits"] = (prev["Incidents"] * 10).astype(int)
                st.dataframe(prev.rename(columns={reg:"Region", cty:"Country"}),
                             use_container_width=True, hide_index=True, height=220)
                if st.button("Create Ops Plan", key="create_ops_plan"):
                    batch_id = write_preposition_plan(prev.rename(columns={reg:"Region", cty:"Country"}))
                    st.success(f"Ops Plan created. Batch: {batch_id}")
            else:
                st.caption("Need Region and Country columns to build an Ops Plan.")

    with tabs[2]:
        base = apply_filters(df)
        if base.empty:
            st.info("No filters selected or no matching rows.")
        else:
            map_block(base, "Map (filtered records with coordinates)")

    with tabs[3]:
        st.caption("Drop your trained artifacts under /models: tree_baseline.joblib and metrics.json.")
        metrics_path = os.path.join(MODELS_DIR, "metrics.json")
        model_path   = os.path.join(MODELS_DIR, "tree_baseline.joblib")
        if os.path.exists(metrics_path):
            try:
                with open(metrics_path, "r") as f:
                    m = json.load(f)
                c1, c2, c3, c4 = st.columns(4)
                with c1: st.metric("Precision", f"{m.get('precision', 0):.2f}")
                with c2: st.metric("Recall",    f"{m.get('recall', 0):.2f}")
                with c3: st.metric("F1",        f"{m.get('f1', 0):.2f}")
                with c4: st.metric("ROC-AUC",   f"{m.get('roc_auc', 0):.2f}")
            except Exception as e:
                st.warning(f"Could not read metrics.json: {e}")
        else:
            st.info("metrics.json not found.")

        if joblib and os.path.exists(model_path):
            try:
                model = joblib.load(model_path)
                st.success("Trained model loaded.")
                st.write("**Run inference on a CSV of features** (columns should match training).")
                f = st.file_uploader("Upload features CSV", type=["csv"], key="predict_csv")
                if f is not None:
                    X = pd.read_csv(io.BytesIO(f.read()))
                    try:
                        yhat = model.predict(X)
                        out = X.copy()
                        out["Prediction"] = yhat
                        st.dataframe(out.head(1000), use_container_width=True, hide_index=True)
                        st.download_button("⬇️ Download predictions (CSV)",
                                        data=out.to_csv(index=False).encode("utf-8"),
                                        file_name="aidbot_model_predictions.csv",
                                        mime="text/csv")
                    except Exception as e:
                        st.error(f"Model could not predict on this CSV: {e}")
            except Exception as e:
                st.warning(f"Could not load trained model: {e}")
        else:
            st.info("tree_baseline.joblib not found (or joblib not installed).")

    # ✅ New cleanly aligned Future Simulation tab
    with tabs[4]:
        st.markdown("<h3 style='font-weight:600; color:#1f2937;'>Future Disaster Simulation</h3>", unsafe_allow_html=True)
        st.info("""
        💡 **How predictions work:**
        - Uses **2 models** (Decision Tree and Neural Network)
        - Predicts **most likely disaster type** for selected locations and future year
        - Based on **historical patterns** from your Asia dataset (1900–2021)
        - Ignores filters for disaster type — it predicts independently
        """)
        st.subheader("🌤 Current Weather Data")

        # Get weather data for selected country or default
        try:
            weather_country = selected_country if selected_country != "(All)" else "Yangon"
            df_weather = get_weather_data(weather_country)
            st.dataframe(df_weather, use_container_width=True)
            st.caption(f"Using real-time weather data for {weather_country} 🌦️")
        except Exception as e:
            st.warning(f"⚠️ Could not fetch weather data: {e}")
            df_weather = pd.DataFrame([{
                "city": "N/A",
                "temperature": None,
                "humidity": None,
                "pressure": None,
                "wind_speed": None,
                "weather": "No data"
            }])
            st.dataframe(df_weather, use_container_width=True)


        if df is None or df.empty:
            st.warning("⚠️ Please upload a valid CSV file first.")
        else:
            # ✅ Use your existing pick() (no redefinition!)
            DISASTER_COL = pick(df, "Disaster Type", "DisasterType", "Disaster", "Target")
            REGION_COL   = pick(df, "Region")
            COUNTRY_COL  = pick(df, "Country")
            YEAR_COL     = pick(df, "Year", "Start Year", "StartYear")

            from simulate_alerts import simulate_future_prediction, load_model
            models, encoders, scaler, meta = load_model()

            region_filter = selected_region if selected_region != "(All)" else None
            country_filter = selected_country if selected_country != "(All)" else None

            filtered_df = df.copy()
            if 'selected_types' in locals() and selected_types:
                selected_disaster = selected_types[0]  # pick the first one
            else:
                selected_disaster = "(All)"

            # Apply filters
            if DISASTER_COL and selected_disaster and selected_disaster != "(All)":
                filtered_df = filtered_df[filtered_df[DISASTER_COL] == selected_disaster]
                st.caption(f"🌪 Filtered by Disaster Type: **{selected_disaster}**")

            if REGION_COL and selected_region != "(All)":
                filtered_df = filtered_df[filtered_df[REGION_COL] == selected_region]
                st.caption(f"🌍 Filtered by Region: **{selected_region}**")

            if COUNTRY_COL and selected_country != "(All)":
                filtered_df = filtered_df[filtered_df[COUNTRY_COL] == selected_country]
                st.caption(f"🗺 Filtered by Country: **{selected_country}**")

            if year_range:
                y1, y2 = year_range
                filtered_df = filtered_df[filtered_df[YEAR_COL].between(y1, y2)]
                st.caption(f"📅 Using historical data from: **{y1}–{y2}**")

            if filtered_df.empty:
                st.warning("⚠️ No data found for your selected filters.")
            else:
                st.success(f"✅ {len(filtered_df)} records found for simulation")
                st.dataframe(filtered_df[["Region", "Country", "Year"]],height=min(400, 40 + len(filtered_df) * 25))


                year = st.slider("Select Future Year", 2025, 2050, 2030)
                if st.button("Predict Future Disasters", type="primary"):
                    results = []
                    progress = st.progress(0)
                    for i, (_, row) in enumerate(filtered_df.iterrows()):
                        result = simulate_future_prediction(row.to_dict(), models, encoders, scaler, meta, year=year, selected_disaster=selected_types)
                        results.append(result)
                        progress.progress((i + 1) / len(filtered_df))
                    progress.empty()

                    df_results = pd.DataFrame(results)
                    st.dataframe(df_results, use_container_width=True)

                    high = (df_results["alert_level"] == "HIGH").sum()
                    med = (df_results["alert_level"] == "MEDIUM").sum()
                    low = (df_results["alert_level"] == "LOW").sum()

                    col1, col2, col3 = st.columns(3)
                    col1.metric("High Alerts", high)
                    col2.metric("Medium Alerts", med)
                    col3.metric("Low Alerts", low)
                    st.caption("Note: Model predictions may differ from the selected filter. AidBot forecasts the most probable disaster type based on regional and environmental patterns.")

# ---------- Allocation Optimizer (beta) ----------
def _parse_skills(sk: str) -> set:
    return {s.strip().lower() for s in (sk or "").split(",") if s.strip()}

def optimizer_panel(role: str):
    lang = st.session_state.get("lang", "en")
    st.subheader("🍀 Allocation Optimizer (beta)")
    st.caption("Suggests volunteer assignments for unassigned, open cases using region/country and skill match heuristics.")
    if role not in ("admin","coordinator"):
        st.info("Only coordinators/admins can run the optimizer.")
        return
    open_status = {"new","acknowledged","en_route","arrived"}
    cases = [c for c in list_cases() if (c.get("status") in open_status and not c.get("assigned_to"))]
    vols  = list_volunteers()
    if not cases:
        st.success("No unassigned open cases. Nothing to optimize.")
        return
    if not vols:
        st.warning("No volunteers available.")
        return
    assigned_open = {}
    for c in list_cases():
        if c.get("assigned_to") and c.get("status") in open_status:
            assigned_open[c["assigned_to"]] = assigned_open.get(c["assigned_to"], 0) + 1
    suggestions = []
    used_vols = set()
    for c in cases:
        ranked = []
        for v in vols:
            vid = v["user_id"]
            if vid in used_vols:
                continue
            score = 0
            why = []
            if (v.get("region","") or "").strip() and (c.get("region","") or "").strip():
                if v["region"].strip().lower() == (c.get("region","") or "").strip().lower():
                    score += 2
                    why.append("same region")
            if (v.get("country","") or "").strip() and (c.get("country","") or "").strip():
                if v["country"].strip().lower() == (c.get("country","") or "").strip().lower():
                    score += 1
                    why.append("same country")
            vs = _parse_skills(v.get("skills",""))
            want = {"first aid","cpr","nursing","medical doctor","paramedic","boat operator","driving","search & rescue"}
            overlap = len(vs & want)
            if overlap:
                score += overlap*3
                why.append(f"{overlap} skill match")
            w = assigned_open.get(vid, 0)
            if w:
                score -= w
                why.append(f"-{w} workload penalty")
            ranked.append({"v": v, "score": score, "why": ", ".join(why) if why else "generic"})
        ranked.sort(key=lambda r: r["score"], reverse=True)
        if ranked and ranked[0]["score"] > float("-inf"):
            top = ranked[0]
            v = top["v"]
            suggestions.append({
                "case_id": c["case_id"],
                "victim": c.get("victim_name") or "(no name)",
                "region": c.get("region",""),
                "country": c.get("country",""),
                "vol_id": v["user_id"],
                "volunteer": v["username"],
                "score": int(top["score"]),
                "why": top["why"],
            })
            used_vols.add(v["user_id"])
    if not suggestions:
        st.info("No suitable suggestions were found with current data.")
        return
    sug_df = pd.DataFrame(suggestions)
    st.dataframe(sug_df[["case_id","victim","region","country","volunteer","score","why"]],
                 use_container_width=True, hide_index=True, height=220)
    if st.button(_translate("Apply", lang) + " suggested plan", type="primary", key="apply_plan"):
        for row in suggestions:
            assign_case(row["case_id"], row["vol_id"])
            add_notification(row["vol_id"], f"You have been assigned to case {row['case_id']}. (optimizer)")
        _notify_admins_and_coords(f"Optimizer applied: {len(suggestions)} assignments.")
        st.success("Plan applied.")
        st.rerun()

# ---------- Routing ----------
route = st.session_state.get("route", "home")
user  = st.session_state.get("user")

# Public routes
if not user:
    if route == "login": login_page(); st.stop()
    elif route == "first_aid": first_aid_page(); st.stop()
    elif route == "red_cross": red_cross_info_page(); st.stop()
    elif route == "victim": victim_portal(); st.stop()
    elif route == "case_status": case_status_page(); st.stop()
    elif route == "notifications": notifications_page(); st.stop()
    elif route == "about": about_page(); st.stop()
    elif route == "contact": contact_page(); st.stop()
    elif route == "chat": chat_page(); st.stop()
    elif route == "messages_admin": messages_admin_page(); st.stop()
    else: public_home(); st.stop()

# Logged-in routes (also allow info pages)
if route == "profile": profile_page(); st.stop()
elif route == "notifications": notifications_page(); st.stop()
elif route == "about": about_page(); st.stop()
elif route == "contact": contact_page(); st.stop()
elif route == "chat": chat_page(); st.stop()
elif route == "first_aid": first_aid_page(); st.stop()
elif route == "red_cross": red_cross_info_page(); st.stop()
elif route == "victim": victim_portal(); st.stop()
elif route == "case_status": case_status_page(); st.stop()
elif route == "messages_admin": messages_admin_page(); st.stop()

# Signed-in dashboards
render_header(show_auth=True)
role = user.get("role", "victim")
lang = st.session_state.get("lang", "en")

if role == "victim":
    victim_portal()
    st.stop()

if role == "volunteer":
    volunteer_cases()
    st.markdown("---")
    blood_tab_enhanced(role=role)
    st.stop()

# Coordinator/Admin dashboard
st.markdown("## " + _translate("Dashboard", lang) + " (Coordinator / Admin)")
st.subheader(_translate("Dashboard", lang) + " Overview")
cs = list_cases()
total = len(cs)
by_status = {}
for c in cs: by_status[c["status"]] = by_status.get(c["status"],0)+1
col = st.columns(4)
with col[0]: st.metric("Cases (total)", total)
with col[1]: st.metric("Open", sum(by_status.get(s,0) for s in ["new","acknowledged","en_route","arrived"]))
with col[2]: st.metric("Closed", by_status.get("closed",0))
with col[3]: st.metric("Cancelled", by_status.get("cancelled",0))
st.markdown("---")
#st.subheader(_translate("Cases", lang))
coordinator_cases(admin_mode=(role=="admin"))

# Admin Users panel
if role == "admin":
    st.markdown("---")
    st.subheader("Admin — Users")
    
    # Search and filters
    search_user = st.text_input(_translate("Search", lang) + " users", placeholder="Username or email...")
    col1, col2 = st.columns(2)
    with col1:
        role_filter = st.selectbox(_translate("Filter", lang) + " by role", ["(all)","admin","coordinator","volunteer","victim"], index=0)
    with col2:
        sort_by = st.radio("Sort by", ["Newest → Oldest", "Oldest → Newest"], index=0, horizontal=True)
    
    users = list_users(None if role_filter=="(all)" else role_filter)
    
    # Apply search filter
    if search_user.strip():
        q = search_user.lower()
        users = [u for u in users if (
            q in (u.get("username") or "").lower() or
            q in (u.get("email") or "").lower()
        )]
    
    # Apply ordering
    if sort_by.startswith("Oldest"):
        users = sorted(users, key=lambda u: u.get("created_at", 0))
    else:
        users = sorted(users, key=lambda u: u.get("created_at", 0), reverse=True)

    if users:
        # Pagination
        page_size = 10
        total = len(users)
        total_pages = max(1, ceil(total / page_size))
        page_key = "users_page"
        current_page = st.session_state.get(page_key, 1)
        if current_page > total_pages:
            current_page = total_pages
            st.session_state[page_key] = current_page
        
        start_idx = (current_page - 1) * page_size
        end_idx = min(start_idx + page_size, total)
        page_users = users[start_idx:end_idx]
        
        df = pd.DataFrame(page_users).reset_index(drop=True)
        df.insert(0, "No.", range(start_idx + 1, end_idx + 1))
        show = df.rename(columns={"user_id":"User ID"})[["No.","User ID","username","role","first_name","last_name","email","phone","region","skills","deleted"]]
        h = _auto_height(len(page_users))
        st.dataframe(show, use_container_width=True, height=h, hide_index=True)
        
        # Pagination controls
        if total_pages > 1:
            st.markdown("---")
            col1, col2, col3 = st.columns([0.3, 0.4, 0.3])
            with col1:
                if current_page > 1:
                    if st.button("← Previous", key="users_prev"):
                        st.session_state[page_key] = current_page - 1
                        st.rerun()
            with col2:
                st.markdown(f"<div style='text-align:center'>Page {current_page} of {total_pages} ({total} total)</div>", unsafe_allow_html=True)
            with col3:
                if current_page < total_pages:
                    if st.button("Next →", key="users_next"):
                        st.session_state[page_key] = current_page + 1
                        st.rerun()
        
        # Download button (all users, not just current page)
        full_df = pd.DataFrame(users).reset_index(drop=True)
        full_df.insert(0, "No.", range(1, len(full_df)+1))
        full_show = full_df.rename(columns={"user_id":"User ID"})[["No.","User ID","username","role","first_name","last_name","email","phone","region","skills","deleted"]]
        st.download_button(
            "⬇️ " + _translate("Download", lang) + " users (CSV)",
            data=full_show.to_csv(index=False).encode("utf-8"),
            file_name="aidbot_users.csv",
            mime="text/csv",
            key="dl_users"
        )
    
    admin_user_panel()

st.markdown("---")
#st.subheader(_translate("Shelters", lang))
shelters_admin()
st.markdown("---")

# Ops Plans list
st.subheader("Ops Plans")
plans = list_preposition_plans(limit=10)
if not plans:
    st.info("No Ops Plans yet. Build one from Predictions → Filtered analysis → Ops Planner.")
else:
    for p in plans:
        with st.expander(f"{p['batch_id']} — {dt.datetime.fromtimestamp(p['created_at']).strftime('%Y-%m-%d %H:%M')}"):
            try:
                dfp = pd.read_csv(io.StringIO(p["payload_csv"]))
                st.dataframe(dfp.head(50), use_container_width=True, hide_index=True)
                st.download_button(
                    f"⬇️ {_translate('Download', lang)} plan {p['batch_id']} (CSV)",
                    data=p["payload_csv"].encode("utf-8"),
                    file_name=f"ops_plan_{p['batch_id']}.csv",
                    mime="text/csv",
                    key=f"dl_plan_{p['batch_id']}"
                )
            except Exception as e:
                st.warning(f"Could not preview plan: {e}")

st.markdown("---")
st.subheader("Disaster Predictions Dashboard")

@st.cache_data(show_spinner=False)
def load_csv(file_bytes: bytes | None) -> pd.DataFrame:
    if file_bytes is not None:
        return pd.read_csv(io.BytesIO(file_bytes), low_memory=False)
    if os.path.exists(SAMPLE_CSV):
        try: return pd.read_csv(SAMPLE_CSV, low_memory=False)
        except Exception: return pd.DataFrame()
    return pd.DataFrame()

up = st.file_uploader("Upload predictions CSV (from Orange)", type=["csv"])
df_pred = load_csv(up.read() if up is not None else None)
if df_pred.empty:
    st.info("Upload a predictions CSV to open the analytics tabs.")
else:
    predictions_tabs(df_pred)

st.markdown("---")
resources_tab(role=role)

st.markdown("---")
if 'disaster_predictions_df' not in st.session_state:
    st.session_state['disaster_predictions_df'] = None

# If predictions were uploaded, save to session state
if 'df_pred' in locals() and df_pred is not None and not df_pred.empty:
    st.session_state['disaster_predictions_df'] = df_pred

blood_tab_enhanced(role=role)  # ← NEW ENHANCED VERSION

# Audit feed (last 10 changes)
st.markdown("---")
st.subheader("Audit (last 10 changes)")
aud = list_audit(limit=10)
if not aud:
    st.info("No audit entries yet.")
else:
    for a in aud:
        when = dt.datetime.fromtimestamp(a["created_at"]).strftime("%Y-%m-%d %H:%M")
        st.write(f"• {when} — {a['table_name']} — actor={a.get('actor_id') or 'unknown'}")
        with st.expander("Payload"):
            st.code(a["payload_json"], language="json")

st.markdown("---")
optimizer_panel(role=role)