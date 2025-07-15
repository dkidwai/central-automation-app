import streamlit as st
import pandas as pd
import io
import db_helper
from db_helper import save_sheet_to_db, load_sheet_from_db

def clean_df(df):
    df = df.loc[:, [col for col in df.columns if not str(col).lower().startswith("unnamed")]]
    df = df.astype(str)
    df = df.replace(['nan', 'NaN', 'None', 'NONE'], '')
    df = df.dropna(axis=1, how='all')
    df = df.loc[:, (df != '').any(axis=0)]
    return df

# 3D card & theme CSS (unchanged)
st.set_page_config(page_title="Central Automation Department", layout="wide")
st.markdown("""<style>
/* ... (your CSS here, unchanged for brevity) ... */
</style>""", unsafe_allow_html=True)

# ---- USER LOGIN (unchanged) ----
ADMIN_USERS = {'admin1': 'pass1', 'danish': '1245','avinash': '1246'}
VIEWERS = {'user1': '1234', 'guest': 'guest'}

if "login" not in st.session_state:
    st.session_state.login = None
if st.session_state.login is None:
    st.subheader("Login")
    login_user = st.text_input("Username")
    login_pass = st.text_input("Password", type="password")
    login_btn = st.button("Login")
    if login_btn:
        if login_user in ADMIN_USERS and login_pass == ADMIN_USERS[login_user]:
            st.session_state.login = {"user": login_user, "role": "admin"}
            st.success("Admin login successful."); st.rerun()
        elif login_user in VIEWERS and login_pass == VIEWERS[login_user]:
            st.session_state.login = {"user": login_user, "role": "viewer"}
            st.success("Viewer login successful."); st.rerun()
        else:
            st.error("Invalid username or password.")
    st.stop()
login_name = st.session_state.login["user"]
login_role = st.session_state.login["role"]

# ------ SESSION STATE for NAVIGATION ------
if "page" not in st.session_state: st.session_state.page = "home"
if "selected_section" not in st.session_state: st.session_state.selected_section = None
if "selected_area" not in st.session_state: st.session_state.selected_area = None

all_subsections = ["PLC DETAILS", "OS DETAILS", "SINGLE POINT TRIPPING", "PAIN POINT", "IO LIST", "CRITICAL SPARES"]
if "db_uploaded" not in st.session_state: st.session_state.db_uploaded = False

# ---- ADMIN FILE UPLOAD ----
uploaded_file = None
if login_role == "admin" and not st.session_state.db_uploaded:
    uploaded_file = st.file_uploader("Upload your PLC_Spare_Database.xlsx (admin only)", type=["xlsx"])
    if uploaded_file:
        xl = pd.ExcelFile(uploaded_file)
        available_sheets = [s for s in all_subsections if s in xl.sheet_names]
        if not available_sheets:
            st.error("No relevant sheets found in this Excel file.")
        else:
            skipped_sheets = []
            loaded_sheets = []
            for sheet in available_sheets:
                df = xl.parse(sheet)
                df = clean_df(df)
                if df.empty or len(df.columns) == 0:
                    skipped_sheets.append(sheet); continue
                save_sheet_to_db(sheet, df)
                loaded_sheets.append(sheet)
            if not loaded_sheets:
                st.error("No sheets could be loaded from your Excel. Please check your file.")
                st.stop()
            msg = ""
            if loaded_sheets: msg += f"Loaded: {', '.join(loaded_sheets)}. "
            if skipped_sheets: msg += f"Skipped empty or blank sheets: {', '.join(skipped_sheets)}."
            st.success(f"Database refreshed! {msg}")
            st.session_state.db_uploaded = True
            st.rerun()

# ---- Get available sheets from DB ----
available_sheets_db = []
for s in all_subsections:
    try:
        df_check = load_sheet_from_db(s)
        if not df_check.empty:
            available_sheets_db.append(s)
    except: pass
if not available_sheets_db:
    st.info("👈 Please (Admin) upload your Excel file once to initialize the database.")
    if st.button("Logout"):
        st.session_state.login = None; st.rerun()
    st.stop()

# ----- LOGOUT BUTTON (top-right) -----
st.markdown(
    "<div style='position:fixed;top:20px;right:38px;z-index:9999;'>"
    "<form action='#' method='post'>"
    "<button style='background:#ff9933;border-radius:16px;padding:7px 24px;border:none;font-weight:bold;color:white;box-shadow:0 1px 6px #d6822a66;cursor:pointer;' "
    "onclick='window.location.reload()'>Logout</button>"
    "</form></div>", unsafe_allow_html=True
)

# ------ PAGE NAVIGATION --------
if st.session_state.page == "home":
    # Center the dashboard button
    st.write("<br><br>", unsafe_allow_html=True)
    st.markdown("<div style='display:flex;justify-content:center;align-items:center;height:50vh;'>"
                "<form action='#' method='post'>"
                "<button style='font-size:2rem;padding:1.2em 4em;border-radius:24px;background:#ff9933;color:#fff;border:none;box-shadow:0 4px 32px #e4872d22;cursor:pointer;'>"
                "DASHBOARD</button></form></div>", unsafe_allow_html=True)
    if st.button("Go to Dashboard", key="go_dashboard"):
        st.session_state.page = "dashboard"
        st.rerun()

elif st.session_state.page == "dashboard":
    st.markdown("<h2 style='color:#ff9933'>Dashboard</h2>", unsafe_allow_html=True)
    cols = st.columns(3)
    # Section buttons (use st.session_state for navigation)
    for i, section in enumerate(all_subsections + ["UNIVERSAL SEARCH"]):
        with cols[i%3]:
            if st.button(section, key=f"section_{section}"):
                if section == "UNIVERSAL SEARCH":
                    st.session_state.page = "universal_search"
                else:
                    st.session_state.selected_section = section
                    st.session_state.page = "select_area"
                st.rerun()

elif st.session_state.page == "select_area":
    # Load sheet and detect areas
    sheet = st.session_state.selected_section
    df = load_sheet_from_db(sheet)
    df = clean_df(df)
    area_col = None
    for col in df.columns:
        if col.strip().lower() == "area": area_col = col; break
    st.markdown(f"<h3 style='color:#2e6eaa'>{sheet}</h3>", unsafe_allow_html=True)
    if area_col:
        df[area_col] = df[area_col].astype(str).str.strip()
        areas = sorted(df[area_col].replace(['', ' ', 'nan', 'NaN', 'None', 'NONE'], pd.NA).dropna().unique())
        areacols = st.columns(3)
        for i, area in enumerate(areas):
            with areacols[i%3]:
                if st.button(area, key=f"area_{area}"):
                    st.session_state.selected_area = area
                    st.session_state.page = "show_table"
                    st.rerun()
        if st.button("⬅️ Back to Dashboard"):
            st.session_state.page = "dashboard"; st.rerun()
    else:
        st.warning('No "Area" column found in this sheet. Showing all data.')
        st.session_state.selected_area = "All"
        st.session_state.page = "show_table"
        st.rerun()

elif st.session_state.page == "show_table":
    sheet = st.session_state.selected_section
    area = st.session_state.selected_area
    df = load_sheet_from_db(sheet)
    df = clean_df(df)
    area_col = None
    for col in df.columns:
        if col.strip().lower() == "area": area_col = col; break
    if area_col and area != "All":
        df = df[df[area_col] == area]
    st.markdown(f"<h3 style='color:#ff9933'>{sheet} - {area}</h3>", unsafe_allow_html=True)
    search = st.text_input("🔎 Search all columns in this view...", key=f"search_{sheet}_{area}")
    if search:
        df = df[df.apply(lambda row: row.astype(str).str.contains(search, case=False, na=False).any(), axis=1)]
        df = df.replace(['nan', 'NaN', 'None', 'NONE'], '')
    df = df.astype(str).replace(['nan', 'NaN', 'None', 'NONE'], '')
    st.dataframe(df, use_container_width=True)
    excel_buffer = io.BytesIO()
    df.to_excel(excel_buffer, index=False)
    st.download_button(
        label="⬇️ Export Excel",
        data=excel_buffer.getvalue(),
        file_name=f"{sheet}_{area}_export.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    if st.button("⬅️ Back to Areas"):
        st.session_state.page = "select_area"; st.rerun()
    if st.button("⬅️ Dashboard"):
        st.session_state.page = "dashboard"; st.rerun()

elif st.session_state.page == "universal_search":
    st.markdown("<h3 style='color:#ff9933'>Universal Search (All Sheets)</h3>", unsafe_allow_html=True)
    keyword = st.text_input("Type keyword to search all sheets...", key="universal_search_key")
    if keyword:
        results = []
        for s in available_sheets_db:
            df = load_sheet_from_db(s)
            df = clean_df(df)
            df_result = df[df.apply(lambda row: row.astype(str).str.contains(keyword, case=False, na=False).any(), axis=1)]
            if not df_result.empty:
                results.append((s, df_result))
        if results:
            for s, dfres in results:
                st.markdown(f"<h5 style='color:#2e6eaa'>{s}</h5>", unsafe_allow_html=True)
                st.dataframe(dfres, use_container_width=True)
        else:
            st.info("No matching records found.")
    if st.button("⬅️ Dashboard"):
        st.session_state.page = "dashboard"; st.rerun()
