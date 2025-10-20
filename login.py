# login.py — Sign in / Sign up + minimal admin panel (with i18n polish)
import os
import secrets
import streamlit as st
from db import (
    get_user_by_credentials, create_user, list_users, update_user, delete_user
)

APP_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(APP_DIR, "uploads")
IMAGES_DIR = os.path.join(APP_DIR, "images")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(IMAGES_DIR, exist_ok=True)

DEFAULT_AVATAR = "default_avatar.png"

SKILL_OPTIONS = [
    "First Aid", "CPR", "Search & Rescue", "Driving", "Boat Operator",
    "Logistics", "Nursing", "Medical Doctor", "Paramedic", "Interpreter",
    "Mapping/GIS", "IT Support", "Radio Comms", "Psychological First Aid"
]

# --- minimal local i18n (uses st.session_state['lang'] set from app header) ---
_LANGS = {"English": "en", "Burmese": "my"}
_T = {
    "en": {
        "Login": "Login",
        "Use your AidBot account credentials to sign in.": "Use your AidBot account credentials to sign in.",
        "Sign in": "Sign in",
        "Sign up": "Sign up",
        "Username": "Username",
        "Password": "Password",
        "Invalid username or password.": "Invalid username or password.",
        "Create a volunteer or coordinator account.": "Create a volunteer or coordinator account.",
        "New username": "New username",
        "New password": "New password",
        "Role": "Role",
        "First name": "First name",
        "Last name": "Last name",
        "Email": "Email",
        "Phone": "Phone",
        "Country": "Country",
        "Region": "Region",
        "Skills": "Skills",
        "Profile photo (optional)": "Profile photo (optional)",
        "Create account": "Create account",
        "Account created. You can sign in now.": "Account created. You can sign in now.",
        "Username already exists or invalid input.": "Username already exists or invalid input.",
        "Admin — Users": "Admin — Users",
        "Total users:": "Total users:",
        "Update user": "Update user",
        "User updated. Reload the page to see changes.": "User updated. Reload the page to see changes.",
        "Yes, delete this user": "Yes, delete this user",
        "Delete user": "Delete user",
        "User deleted (soft delete).": "User deleted (soft delete).",
    },
    "my": {
        "Login": "ဝင်ရောက်မယ်",
        "Use your AidBot account credentials to sign in.": "AidBot အကောင့်ဖြင့် ဝင်ရောက်ပါ။",
        "Sign in": "ဝင်ရောက်ရန်",
        "Sign up": "အကောင့်ဖန်တီးရန်",
        "Username": "အသုံးပြုသူအမည်",
        "Password": "စကားဝှက်",
        "Invalid username or password.": "အသုံးပြုသူအမည်/စကားဝှက် မမှန်ပါ။",
        "Create a volunteer or coordinator account.": "စေတနာ့ဝန်ထမ်း သို့မဟုတ် စီမံခန့်ခွဲသူ အကောင့်ဖန်တီးရန်။",
        "New username": "အသုံးပြုသူအမည်အသစ်",
        "New password": "စကားဝှက်အသစ်",
        "Role": "တာဝန်",
        "First name": "အမည်",
        "Last name": "မျိုးနွယ်အမည်",
        "Email": "အီးမေးလ်",
        "Phone": "ဖုန်း",
        "Country": "နိုင်ငံ",
        "Region": "တိုင်းဒေသကြီး/တိုင်း",
        "Skills": "ကျွမ်းကျင်မှုများ",
        "Profile photo (optional)": "ပရိုဖိုင်ဓာတ်ပုံ (Optional)",
        "Create account": "အကောင့်ဖန်တီးပါ",
        "Account created. You can sign in now.": "အကောင့်ဖန်တီးပြီးပါပြီ။ အခုဝင်ရောက်နိုင်ပါပြီ။",
        "Username already exists or invalid input.": "အသုံးပြုသူအမည်ရှိပြီးသား သို့မဟုတ် မှားယွင်းသောအချက်အလက်။",
        "Admin — Users": "အက်ဒ်မင် — အသုံးပြုသူများ",
        "Total users:": "စုစုပေါင်းအသုံးပြုသူအရေအတွက်:",
        "Update user": "အသုံးပြုသူအချက်အလက်ပြင်ဆင်ရန်",
        "User updated. Reload the page to see changes.": "ပြင်ဆင်ပြီးပါပြီ။ စာမျက်နှာကိုပြန်လည်ဖွင့်ကြည့်ပါ။",
        "Yes, delete this user": "ဤအသုံးပြုသူကို ဖျက်မည်",
        "Delete user": "ဖျက်မည်",
        "User deleted (soft delete).": "အသုံးပြုသူကို ဖျက်ထားပါသည် (Soft delete)။",
    }
}
def _t(s: str) -> str:
    lang = st.session_state.get("lang", "en")
    return _T.get(lang, _T["en"]).get(s, s)

def login_page():
    st.header(_t("Login"))
    st.caption(_t("Use your AidBot account credentials to sign in."))

    tab_signin, tab_signup = st.tabs([_t("Sign in"), _t("Sign up")])

    # SIGN IN TAB (WITH PASSWORD RESET)
    # SIGN IN TAB (WITH PASSWORD RESET)
    # ============================================
    with tab_signin:
        with st.form("signin_form"):
            uname = st.text_input(_t("Username"), key="signin_username")
            pw = st.text_input(_t("Password"), type="password", key="signin_password")
            
            # Add columns inside the form for sign in button and forgot password
            col1, col2 = st.columns([0.25, 0.75])
            with col1:
                submit = st.form_submit_button(_t("Sign in"), type="primary")
            with col2:
                # Empty space to push forgot password to the very right
                subcol1, subcol2 = st.columns([0.75, 0.25])
                with subcol2:
                    forgot_clicked = st.form_submit_button("🔑 Forgot password?", use_container_width=True)

        if submit:
            user = get_user_by_credentials((uname or "").strip(), (pw or "").strip())
            if user:
                st.session_state["user"] = user
                st.session_state["route"] = "home"
                st.success("Signed in")
                st.rerun()
            else:
                st.error(_t("Invalid username or password."))

        # -------------------------------------------------
        # ✅ Forgot password link (click toggles reset form)
        # -------------------------------------------------
        if "show_reset" not in st.session_state:
            st.session_state["show_reset"] = False

        # Toggle the reset form when clicked
        if forgot_clicked:
            st.session_state["show_reset"] = not st.session_state["show_reset"]

        # Show reset form only when clicked
        if st.session_state["show_reset"]:
            st.markdown("### 🔐 Reset your password")
            st.caption("Enter your username to reset your password. A new temporary password will be generated.")

            with st.form("forgot_password_form"):
                forgot_username = st.text_input("Username", key="forgot_username")
                reset_submit = st.form_submit_button("Reset Password", type="secondary")

            if reset_submit:
                if forgot_username.strip():
                    from db import get_user_by_username, update_user, hash_password
                    import secrets

                    user = get_user_by_username(forgot_username.strip())

                    if user:
                        # Generate new random password
                        new_password = secrets.token_urlsafe(12)
                        update_user(user["user_id"], {"password_hash": hash_password(new_password)})

                        st.success("✅ Password reset successful!")
                        st.info(f"**Your new password is:** `{new_password}`")
                        st.warning("⚠️ Please copy this password and login immediately.")

                        if user.get("email"):
                            st.caption(f"📧 Password reset for account: {user['email']}")
                    else:
                        st.error("❌ Username not found. Please check and try again.")
                else:
                    st.error("⚠️ Please enter your username.")

    # ============================================
    # SIGN UP TAB (UNCHANGED)
    # ============================================
    with tab_signup:
        st.write(_t("Create a volunteer, coordinator, or admin account."))
        with st.form("signup_form"):
            col1, col2 = st.columns(2)
            with col1:
                uname = st.text_input(_t("New username"), key="su_username")
                pw = st.text_input(_t("New password"), type="password", key="su_password")
                
                role = st.selectbox(
                    _t("Role"), 
                    ["volunteer", "coordinator", "admin"],
                    key="su_role"
                )
                
                if role == "admin":
                    st.caption("⚠️ Admin has full system access")
                
                first = st.text_input(_t("First name"), key="su_first")
                last = st.text_input(_t("Last name"), key="su_last")
                email = st.text_input(_t("Email"), key="su_email")
            
            with col2:
                phone = st.text_input(_t("Phone"), key="su_phone")
                country = st.text_input(_t("Country"), key="su_country")
                region = st.text_input(_t("Region"), key="su_region")
                skills_multi = st.multiselect(_t("Skills"), options=SKILL_OPTIONS, default=[], key="su_skills")
                photo_file = st.file_uploader(_t("Profile photo (optional)"), type=["jpg","jpeg","png"], key="su_photo")

            submit = st.form_submit_button(_t("Create account"), type="primary")

        if submit:
            photo_path = ""
            if photo_file is not None:
                fname = photo_file.name.replace("..", "_").replace("/", "_")
                photo_path = os.path.join(UPLOAD_DIR, fname)
                with open(photo_path, "wb") as f:
                    f.write(photo_file.getbuffer())

            ok = create_user(
                (uname or "").strip(), (pw or "").strip(), (role or "").strip(),
                first_name=(first or "").strip(), last_name=(last or "").strip(), 
                email=(email or "").strip(), phone=(phone or "").strip(), 
                country=(country or "").strip(), region=(region or "").strip(),
                skills=",".join(skills_multi), photo_path=photo_path,
                avatar=DEFAULT_AVATAR, bio=""
            )
            
            if ok:
                st.success(_t("Account created. You can sign in now."))
            else:
                st.error(_t("Username already exists or invalid input."))

def admin_user_panel():
    st.subheader(_t("Admin — Users"))
    users = list_users()
    st.write(f"{_t('Total users:')} {len(users)}")

    for u in users:
        with st.expander(f"{u['username']} · {u['role']}", expanded=False):
            c1, c2, c3 = st.columns([0.34, 0.33, 0.33])

            with c1:
                first = st.text_input(_t("First name"), value=u.get("first_name",""), key=f"adm_first_{u['user_id']}")
                last = st.text_input(_t("Last name"), value=u.get("last_name",""), key=f"adm_last_{u['user_id']}")
                email = st.text_input(_t("Email"), value=u.get("email",""), key=f"adm_email_{u['user_id']}")
                phone = st.text_input(_t("Phone"), value=u.get("phone",""), key=f"adm_phone_{u['user_id']}")

            with c2:
                country = st.text_input(_t("Country"), value=u.get("country",""), key=f"adm_country_{u['user_id']}")
                region = st.text_input(_t("Region"), value=u.get("region",""), key=f"adm_region_{u['user_id']}")
                skills_text = st.text_input(_t("Skills") + " (comma separated)", value=u.get("skills",""), key=f"adm_skills_{u['user_id']}")
                avatar = st.text_input("Avatar", value=u.get("avatar",""), key=f"adm_avatar_{u['user_id']}")

            with c3:
                role = st.selectbox(
                    _t("Role"),
                    ["admin","coordinator","volunteer"],
                    index=["admin","coordinator","volunteer"].index(u["role"]),
                    key=f"adm_role_{u['user_id']}"
                )
                bio = st.text_area("Bio", value=u.get("bio",""), height=90, key=f"adm_bio_{u['user_id']}")

                if st.button(_t("Update user"), key=f"adm_update_{u['user_id']}", type="primary"):
                    update_user(u["user_id"], {
                        "first_name": first, "last_name": last, "email": email, "phone": phone,
                        "country": country, "region": region, "skills": skills_text,
                        "avatar": avatar, "role": role, "bio": bio
                    })
                    st.success(_t("User updated. Reload the page to see changes."))

                st.markdown("---")
                colx, coly = st.columns([0.55, 0.45])
                with colx:
                    confirm = st.checkbox(_t("Yes, delete this user"), key=f"adm_del_{u['user_id']}")
                with coly:
                    if st.button(_t("Delete user"), key=f"adm_delete_{u['user_id']}", disabled=not confirm):
                        delete_user(u["user_id"])
                        st.warning(_t("User deleted (soft delete)."))