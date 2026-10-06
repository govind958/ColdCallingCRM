import os
import glob
import pandas as pd
import streamlit as st

# Set page configuration
st.set_page_config(page_title="Master Roofing Leads", layout="wide")

SAVED_DATA_FILE = "roofing_leads_master_db.json"


@st.cache_data
def load_raw_data():
    """Finds and combines raw scraped JSON files."""
    json_files = glob.glob("dataset_crawler-google-places_*.json")
    if not json_files:
        # Fallback empty structure with expected schema if no files are found
        return pd.DataFrame(columns=["title", "address", "phone", "website"])

    df_list = [pd.read_json(f) for f in json_files]
    df = pd.concat(df_list, ignore_index=True)

    if "phone" in df.columns:
        df.drop_duplicates(subset=["phone"], keep="first", inplace=True)
    return df


# Initialize Session State
if "leads_df" not in st.session_state:
    if os.path.exists(SAVED_DATA_FILE):
        st.session_state.leads_df = pd.read_json(SAVED_DATA_FILE)
    else:
        st.session_state.leads_df = load_raw_data()

st.title("🏗️ Roofing Leads Dashboard")

# --- GLOBAL SEARCH BAR ---
search_query = st.text_input("🔍 Search Leads", placeholder="Type business name, phone, or address...")

# Filter dataset if search query is active
if search_query:
    filtered_df = st.session_state.leads_df[
        st.session_state.leads_df.apply(
            lambda row: search_query.lower() in str(row.values).lower(), axis=1
        )
    ]
else:
    filtered_df = st.session_state.leads_df

# --- DATA EDITOR (SHEET STYLE) ---
st.subheader("📋 Editable Lead Registry")
st.info("💡 **Tip:** Edit cells directly in the table below. Use the bottom empty row to add new leads, or select rows and press `Delete` on your keyboard to remove them.")

edited_df = st.data_editor(
    filtered_df,
    num_rows="dynamic",  # Allows adding and deleting rows inline
    use_container_width=True,
    column_config={
        "website": st.column_config.LinkColumn(
            "Website",
            help="Click to open link",
            validate=r"^https?://",
        ),
        "phone": st.column_config.TextColumn("Phone Number"),
        "title": st.column_config.TextColumn("Business Title", required=True),
        "address": st.column_config.TextColumn("Address"),
    },
    key="lead_editor",
)

# Sync edits back to session state
if search_query:
    # If filtered, update modified rows back into the main DataFrame
    st.session_state.leads_df.update(edited_df)
else:
    st.session_state.leads_df = edited_df

# --- CONTROLS & PERSISTENCE ---
st.divider()
col1, col2, col3 = st.columns([1, 1, 2])

with col1:
    if st.button("💾 Save Changes", type="primary", use_container_width=True):
        st.session_state.leads_df.to_json(SAVED_DATA_FILE, orient="records", indent=4)
        st.success("All changes permanently saved to JSON database!")

with col2:
    if st.button("🔄 Reset to Raw Data", use_container_width=True):
        if os.path.exists(SAVED_DATA_FILE):
            os.remove(SAVED_DATA_FILE)
        st.session_state.leads_df = load_raw_data()
        st.rerun()

with col3:
    # Export current database directly to CSV for external use
    csv_data = st.session_state.leads_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Export to CSV",
        data=csv_data,
        file_name="roofing_leads_export.csv",
        mime="text/csv",
        use_container_width=True,
    )