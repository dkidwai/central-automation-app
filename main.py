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

# ----------- MODERN 3D CARD CSS + ORANGE HIGHLIGHT ----------- #
st.set_page_config(page_title="Central Automation Department", layout="wide")
st.markdown("""
    <style>
        /* Soft card shadow for all tables and inputs */
        .stDataFrame, .stButton>button, .stTextInput>div>div>input,
        .stSelectbox>div>div>div, .stDownloadButton button {
            box-shadow: 0 2px 12px 0 rgba(0,0,0,0.13), 0 1.5px 5px 0 rgba(255,153,51,0.09);
            border-radius: 16px !important;
        }
        /* Orange focus for active elements */
        .stTextInput>div>div>input:focus, .stSelectbox>div>div>div:focus-within {
            border: 2px solid #ff9933 !important;
            box-shadow: 0 0 0 2px #ff993380 !important;
        }
        /* DataFrame orange header */
        .stDataFrame thead tr th {
            background-color: #ff9933 !important;
            color: #222 !important;
            font-weight: bold !important;
            font-size: 16px !important;
        }
        /* Table & input border style */
        .stDataFrame td {
            border: 1px solid #bbb !important;
        }
        /* Soft glass for welcome/info area (optional) */
        .welcome-card {
            background: rgba(255,255,255,0.74);
            border-radius: 20px;
            box-shadow: 0 8px 32px 0 rgba(0,0,0,0.14);
            backdrop-filter: blur(5px);
            border: 1.5px solid rgba(255,153,51,0.11);
            padding: 1.1rem 2rem;
            margin-bottom: 1rem;
        }
    </style>
""", unsafe_allow_html=True)

# ---------- OPTIONAL: Welcome Card ----------- #
st.markdown("""
    <div class='welcome-card'>
        <h3 style='color:#ff9933;margin-bottom:4px'>Welcome to Central Automation Department Dashboard</h3>
        <p style='color:#222;margin-top:0'>Manage your PLC, spares, and automation data with a modern look.<br>
        <span style='color:#888;font-size:12px'>For best experience, use desktop or tablet.</span></p>
    </div>
""", unsafe_allow_html=True)

st.title("Central Automation Department")

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
            st.success("Admin login successful.")
            st.rerun()
        elif login_user in VIEWERS and login_pass == VIEWERS[login_user]:
            st.session_state.login = {"user": login_user, "role": "viewer"}
            st.success("Viewer login successful.")
            st.rerun()
        else:
            st.error("Invalid username or password.")
    st.stop()

login_name = st.session_state.login["user"]
login_role = st.session_state.login["role"]
st.sidebar.markdown(f"**👤 Logged in as:** `{login_name}` ({login_role.capitalize()})")
st.markdown(f"<div style='text-align:right;font-weight:bold;color:#2e6eaa;'>User: {login_name} ({login_role})</div>", unsafe_allow_html=True)

all_subsections = ["PLC DETAILS", "OS DETAILS", "SINGLE POINT TRIPPING", "PAIN POINT", "IO LIST", "CRITICAL SPARES"]
st.sidebar.markdown("## 📁 Section Navigation")
combined_search = st.sidebar.checkbox("🔎 Combined Search (All Sheets)")
use_modern_table = st.sidebar.checkbox("🖥️ Modern Editable Table", value=False)

# --- ONE-TIME Upload: Only ADMIN ---
if "db_uploaded" not in st.session_state:
    st.session_state.db_uploaded = False

uploaded_file = None
if login_role == "admin":
    uploaded_file = st.sidebar.file_uploader("Upload your PLC_Spare_Database.xlsx (admin only)", type=["xlsx"])
    if uploaded_file and not st.session_state.db_uploaded:
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
                    skipped_sheets.append(sheet)
                    continue
                save_sheet_to_db(sheet, df)
                loaded_sheets.append(sheet)
            if not loaded_sheets:
                st.error("No sheets could be loaded from your Excel. Please check your file.")
                st.stop()
            msg = ""
            if loaded_sheets:
                msg += f"Loaded: {', '.join(loaded_sheets)}. "
            if skipped_sheets:
                msg += f"Skipped empty or blank sheets: {', '.join(skipped_sheets)}."
            st.success(f"Database refreshed! {msg}")
            st.session_state.db_uploaded = True
            st.rerun()

# ---- Always load available sheets from DB ----
available_sheets_db = []
for s in all_subsections:
    try:
        df_check = load_sheet_from_db(s)
        if not df_check.empty:
            available_sheets_db.append(s)
    except:
        pass

if not available_sheets_db:
    st.info("👈 Please (Admin) upload your Excel file once to initialize the database.")
    if st.sidebar.button("Logout"):
        st.session_state.login = None
        st.rerun()
    st.stop()

selected_section = st.sidebar.radio("Select Subsection", available_sheets_db)
full_df = load_sheet_from_db(selected_section)
full_df = clean_df(full_df)

# --------- SMART AREA COLUMN DETECTION -----------
area_col = None
for col in full_df.columns:
    if col.strip().lower() == "area":
        area_col = col
        break

if area_col:
    full_df[area_col] = full_df[area_col].astype(str).str.strip()
    area_values = full_df[area_col].replace(['', ' ', 'nan', 'NaN', 'None', 'NONE'], pd.NA)
    areas = sorted(area_values.dropna().unique())
    st.sidebar.markdown(f"**Total Number of Areas:** {len(areas)}")
    if areas:
        selected_area = st.sidebar.selectbox("Select Area (Department)", areas)
        filtered_df = full_df[full_df[area_col] == selected_area]
    else:
        st.sidebar.warning('No valid Area values found. Showing all data.')
        filtered_df = full_df
        selected_area = "All"
else:
    st.sidebar.warning('No "Area" column found in this sheet. Showing all data.')
    filtered_df = full_df
    selected_area = "All"

st.subheader(f"{selected_section} - {selected_area}")

# --- Full-width search bar (shared for both tables) ---
search = st.text_input("🔎 Search all columns in this view...", key='search_in_sheet')
if search:
    filtered_df2 = filtered_df[filtered_df.apply(lambda row: row.astype(str).str.contains(search, case=False, na=False).any(), axis=1)]
    filtered_df2 = filtered_df2.replace(['nan', 'NaN', 'None', 'NONE'], '')
else:
    filtered_df2 = filtered_df

filtered_df2 = filtered_df2.astype(str).replace(['nan', 'NaN', 'None', 'NONE'], '')

# --- Modern Table Editor (NOW shows only filtered data) ---
if use_modern_table:
    st.write("### 🖥️ Modern Editable Table (Filtered)")
    edited_df = st.data_editor(
        filtered_df2.copy(),
        num_rows="dynamic" if login_role == "admin" else "fixed",
        use_container_width=True,
        disabled=(login_role != "admin")
    )
    # For Admins: Save edits back to DB (only for edited rows)
    if login_role == "admin":
        if not edited_df.equals(filtered_df2):
            # Merge only changed rows to full_df, save full_df back to DB
            for idx, row in edited_df.iterrows():
                for col in edited_df.columns:
                    full_idx = full_df.index[(full_df == filtered_df2.loc[idx]).all(axis=1)]
                    if not full_idx.empty:
                        full_df.loc[full_idx, col] = row[col]
            save_sheet_to_db(selected_section, full_df)
            st.info("Changes (filtered/edited rows only) saved to the database. All views updated.")
            st.rerun()

# --- Classic DataFrame Table (filtered by Area/Search) ---
st.write("### 📋 Classic Table (Filtered View)")
st.dataframe(filtered_df2, use_container_width=True)

# --- Export buttons ---
excel_buffer = io.BytesIO()
filtered_df2.astype(str).replace(['nan', 'NaN', 'None', 'NONE'], '').to_excel(excel_buffer, index=False)
st.download_button(
    label="⬇️ Export Excel",
    data=excel_buffer.getvalue(),
    file_name=f"{selected_section}_{selected_area}_export.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

if login_role == "admin":
    st.success("You are admin: You can add/edit/delete data here (via Modern Table, CRUD add-ons coming).")

# --- Combined Search Mode ---
if combined_search:
    st.markdown("## 🔎 Combined Search in Selected Sheet Only")
    search_all = st.text_input("Type keyword to search in this sheet...", key='combined_search')
    df_clean = load_sheet_from_db(selected_section)
    df_clean = clean_df(df_clean)
    if search_all:
        df_clean = df_clean[df_clean.apply(lambda row: row.astype(str).str.contains(search_all, case=False, na=False).any(), axis=1)]
    df_clean = df_clean.astype(str).replace(['nan', 'NaN', 'None', 'NONE'], '')
    st.dataframe(df_clean, use_container_width=True)
    # Export button
    excel_buffer_all = io.BytesIO()
    df_clean.astype(str).replace(['nan', 'NaN', 'None', 'NONE'], '').to_excel(excel_buffer_all, index=False)
    st.download_button(
        label="⬇️ Export Results (Excel)",
        data=excel_buffer_all.getvalue(),
        file_name=f"{selected_section}_Search_Export.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    st.stop()

if st.sidebar.button("Logout"):
    st.session_state.login = None
    st.rerun()
