
import json
import hashlib

import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

from supabase_client import supabase


# =========================================================
# CONFIGURATION
# =========================================================

PAGE_SIZE = 50
IMPORT_BATCH_SIZE = 250

DEFAULT_STATUS = "Not Called"

CRM_STATUSES_CONFIG = {
    "Not Called": {
        "label": "🆕 Not Called",
        "color": "#64748b",
        "bg": "#f1f5f9",
    },
    "Attempted": {
        "label": "📞 Attempted",
        "color": "#b45309",
        "bg": "#fef3c7",
    },
    "Left Voicemail": {
        "label": "🎙️ Left Voicemail",
        "color": "#0e7490",
        "bg": "#cffafe",
    },
    "Contacted": {
        "label": "💬 Contacted",
        "color": "#1d4ed8",
        "bg": "#dbeafe",
    },
    "Not Interested": {
        "label": "❌ Not Interested",
        "color": "#b91c1c",
        "bg": "#fee2e2",
    },
    "Cold Lead": {
        "label": "❄️ Cold Lead",
        "color": "#64748b",
        "bg": "#e2e8f0",
    },
    "Warm Lead": {
        "label": "🌤️ Warm Lead",
        "color": "#c2410c",
        "bg": "#ffedd5",
    },
    "Hot Lead": {
        "label": "🔥 Hot Lead",
        "color": "#be185d",
        "bg": "#fce7f3",
    },
    "Meeting Booked": {
        "label": "📅 Meeting Booked",
        "color": "#047857",
        "bg": "#d1fae5",
    },
    "Proposal / Offer Sent": {
        "label": "📄 Proposal Sent",
        "color": "#6d28d9",
        "bg": "#ede9fe",
    },
    "Won / Client": {
        "label": "🏆 Won / Client",
        "color": "#15803d",
        "bg": "#dcfce7",
    },
    "Lost": {
        "label": "📉 Lost",
        "color": "#475569",
        "bg": "#e2e8f0",
    },
    "Call Back Later": {
        "label": "⏰ Call Back Later",
        "color": "#a16207",
        "bg": "#fef3c7",
    },
    "Invalid / Do Not Call": {
        "label": "🚫 Do Not Call",
        "color": "#b91c1c",
        "bg": "#fee2e2",
    },
}

STATUS_LABEL_TO_RAW = {
    config["label"]: status
    for status, config in CRM_STATUSES_CONFIG.items()
}


# =========================================================
# STYLING
# =========================================================

def inject_crm_styles():
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 1.8rem;
            padding-bottom: 2rem;
            max-width: 1600px;
        }

        .crm-eyebrow {
            color: #64748b;
            font-size: 0.75rem;
            font-weight: 700;
            letter-spacing: 0.14em;
            text-transform: uppercase;
            margin-bottom: 0.45rem;
        }

        .crm-title {
            font-size: clamp(1.8rem, 3vw, 2.6rem);
            line-height: 1.15;
            letter-spacing: -0.055em;
            font-weight: 800;
            color: var(--text-color);
            margin-bottom: 0.4rem;
        }

        .crm-subtitle {
            font-size: 0.96rem;
            color: #64748b;
            margin-bottom: 1.4rem;
        }

        div[data-testid="stMetric"] {
            padding: 17px 19px;
            border: 1px solid rgba(148, 163, 184, 0.23);
            border-radius: 15px;
            background: var(--secondary-background-color);
        }

        div[data-testid="stMetricLabel"] {
            font-size: 0.82rem;
            font-weight: 600;
        }

        div[data-testid="stMetricValue"] {
            font-size: 1.8rem;
            font-weight: 750;
            letter-spacing: -0.04em;
        }

        div[data-testid="stDataFrame"] {
            border: 1px solid rgba(148, 163, 184, 0.25);
            border-radius: 12px;
            overflow: hidden;
        }

        div[data-testid="stTextInput"] input,
        div[data-testid="stSelectbox"] div[data-baseweb="select"] {
            border-radius: 10px;
        }

        div.stButton > button {
            border-radius: 9px;
            font-weight: 600;
            min-height: 2.5rem;
        }

        .crm-section {
            font-size: 1.05rem;
            font-weight: 750;
            letter-spacing: -0.02em;
            margin: 0.5rem 0 0.85rem;
        }

        .crm-muted {
            color: #64748b;
            font-size: 0.82rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# DATA HELPERS
# =========================================================

def normalize_lead(lead, row_order=0):
    item = dict(lead)

    status = item.get("status") or DEFAULT_STATUS

    if status not in CRM_STATUSES_CONFIG:
        status = DEFAULT_STATUS

    item["status"] = status
    item["_row_order"] = row_order

    return item


def get_lead_fingerprint(leads):
    parts = sorted(
        (
            str(lead.get("id")),
            str(lead.get("status") or DEFAULT_STATUS),
        )
        for lead in leads
    )

    payload = json.dumps(parts, ensure_ascii=False)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def initialize_leads_cache(leads):
    """
    Initialize once. Keep the original row positions across reruns.
    Never rebuild this cache merely because a status changes.
    """
    if "leads_cache" not in st.session_state:
        st.session_state["leads_cache"] = [
            normalize_lead(lead, index)
            for index, lead in enumerate(leads)
        ]

    # Store the last confirmed database status separately.
    if "crm_committed_statuses" not in st.session_state:
        st.session_state["crm_committed_statuses"] = {
            str(lead["id"]): lead["status"]
            for lead in st.session_state["leads_cache"]
            if lead.get("id") is not None
        }

    return st.session_state["leads_cache"]


def update_cached_status(lead_id, status):
    """Update a status without changing a lead's row position."""
    lead_id = str(lead_id)

    for lead in st.session_state.get("leads_cache", []):
        if str(lead.get("id")) == lead_id:
            lead["status"] = status
            break


def fetch_saved_status(lead_id):
    """Read the status back from Supabase after updating it."""
    response = (
        supabase.table("leads")
        .select("id,status")
        .eq("id", lead_id)
        .limit(1)
        .execute()
    )

    if not response.data:
        raise RuntimeError(
            f"Lead {lead_id} was not returned by Supabase after saving."
        )

    saved_status = response.data[0].get("status")

    if saved_status not in CRM_STATUSES_CONFIG:
        raise RuntimeError(
            f"Supabase returned an unexpected status: {saved_status!r}"
        )

    return saved_status


def save_lead_status(lead_id, new_status):
    """Save, check the affected row, and verify the stored status."""
    if new_status not in CRM_STATUSES_CONFIG:
        raise ValueError(f"Unknown lead status: {new_status!r}")

    if lead_id is None or not str(lead_id).strip():
        raise ValueError("This lead has no database ID.")

    # Update only the status. Do not update ordering or other columns.
    response = (
        supabase.table("leads")
        .update({"status": new_status})
        .eq("id", lead_id)
        .execute()
    )

    if not response.data:
        raise RuntimeError(
            "Supabase did not return an updated row. "
            "Check that the lead ID exists and your database permissions "
            "allow this update."
        )

    # Verify against a fresh database read.
    saved_status = fetch_saved_status(lead_id)

    if saved_status != new_status:
        raise RuntimeError(
            f"Status verification failed. Requested {new_status!r}, "
            f"but Supabase returned {saved_status!r}."
        )

    return saved_status


# =========================================================
# JSON IMPORT
# =========================================================

def prepare_import_record(item):
    if not isinstance(item, dict):
        raise ValueError("Every JSON list item must be an object.")

    return {
        "company_name": item.get("title") or item.get("company_name"),
        "status": DEFAULT_STATUS,
        "category_name": (
            item.get("categoryName") or item.get("category_name")
        ),
        "phone": item.get("phone"),
        "website": item.get("website"),
        "city": item.get("city"),
        "state": item.get("state"),
        "address": item.get("address"),
        "total_score": item.get(
            "totalScore", item.get("total_score")
        ),
        "reviews_count": item.get(
            "reviewsCount", item.get("reviews_count")
        ),
        "raw_data": item,
    }


def import_leads_json(uploaded_file):
    uploaded_data = json.loads(
        uploaded_file.getvalue().decode("utf-8")
    )

    if not isinstance(uploaded_data, list):
        raise ValueError("The root JSON structure must be a list.")

    records = [
        prepare_import_record(item)
        for item in uploaded_data
    ]

    if not records:
        return 0

    imported = 0

    for start in range(0, len(records), IMPORT_BATCH_SIZE):
        batch = records[start:start + IMPORT_BATCH_SIZE]

        supabase.table("leads").insert(batch).execute()
        imported += len(batch)

    return imported


# =========================================================
# STATUS EDIT HANDLER
# =========================================================

def process_grid_status_changes(edited_df, page_leads):
    """
    Compare AgGrid's returned statuses with the last confirmed statuses.
    Only save actual changes. A failed save restores the confirmed value.
    """
    if (
        edited_df is None
        or edited_df.empty
        or "id" not in edited_df.columns
        or "status" not in edited_df.columns
    ):
        return False

    committed = st.session_state["crm_committed_statuses"]

    # Only IDs present on this page can be edited here.
    visible_ids = {
        str(lead.get("id"))
        for lead in page_leads
        if lead.get("id") is not None
    }

    changes = []

    for _, edited in edited_df.iterrows():
        lead_id = str(edited.get("id") or "")

        if not lead_id or lead_id not in visible_ids:
            continue

        new_status = edited.get("status")
        old_status = committed.get(lead_id)

        if (
            isinstance(new_status, str)
            and new_status in CRM_STATUSES_CONFIG
            and old_status is not None
            and new_status != old_status
        ):
            changes.append((lead_id, old_status, new_status))

    if not changes:
        return False

    failures = []
    successes = []

    # AgGrid normally changes one cell at a time. Process every detected
    # change defensively in case multiple changes are returned together.
    with st.spinner("Saving changes to Supabase..."):
        for lead_id, old_status, new_status in changes:
            try:
                saved_status = save_lead_status(lead_id, new_status)

                # Commit the cache only after database verification succeeds.
                committed[lead_id] = saved_status
                update_cached_status(lead_id, saved_status)

                successes.append(lead_id)

            except Exception as exc:
                # Never keep an unconfirmed value in the local cache.
                update_cached_status(lead_id, old_status)

                failures.append(
                    f"Lead ID {lead_id}: {exc}"
                )

    if successes:
        st.session_state["crm_flash_success"] = (
            f"Successfully saved {len(successes)} status change(s)."
        )

    if failures:
        st.session_state["crm_status_errors"] = failures

    # Force a clean grid instance with the confirmed statuses.
    # _row_order remains unchanged.
    st.session_state["crm_grid_version"] = (
        st.session_state.get("crm_grid_version", 0) + 1
    )

    st.rerun()
    return True


# =========================================================
# MAIN VIEW
# =========================================================

def render_leads(leads):
    inject_crm_styles()

    st.markdown(
        """
        <div class="crm-eyebrow">
            Sales workspace / Contractor CRM
        </div>
        <div class="crm-title">Leads Pipeline</div>
        <div class="crm-subtitle">
            Manage cold calls, qualify contractors, book meetings,
            and turn prospects into paying clients.
        </div>
        """,
        unsafe_allow_html=True,
    )

    current_leads = initialize_leads_cache(leads)

    # Show saved feedback after the rerun.
    success_message = st.session_state.pop(
        "crm_flash_success", None
    )

    if success_message:
        st.success(success_message)

    errors = st.session_state.pop("crm_status_errors", [])

    for error in errors:
        st.error(f"Status was not saved: {error}")

    # -----------------------------------------------------
    # METRICS
    # -----------------------------------------------------

    statuses = [
        lead.get("status", DEFAULT_STATUS)
        for lead in current_leads
    ]

    total_count = len(current_leads)
    hot_count = statuses.count("Hot Lead")
    meetings_count = statuses.count("Meeting Booked")
    won_count = statuses.count("Won / Client")
    not_called_count = statuses.count("Not Called")
    callback_count = statuses.count("Call Back Later")

    m1, m2, m3, m4 = st.columns(4)

    with m1:
        st.metric("Total leads", f"{total_count:,}")

    with m2:
        st.metric("🔥 Hot leads", f"{hot_count:,}")

    with m3:
        st.metric("📅 Meetings booked", f"{meetings_count:,}")

    with m4:
        st.metric("🏆 Won clients", f"{won_count:,}")

    s1, s2, s3 = st.columns(3)

    with s1:
        st.caption(f"🆕 {not_called_count:,} leads not called")

    with s2:
        st.caption(f"⏰ {callback_count:,} callbacks pending")

    with s3:
        conversion = (
            won_count / total_count * 100
            if total_count
            else 0
        )
        st.caption(
            f"📈 Lead-to-client rate: {conversion:.1f}%"
        )

    st.divider()

    # -----------------------------------------------------
    # IMPORT
    # -----------------------------------------------------

    with st.expander("📥 Import leads from JSON", expanded=False):
        st.caption(
            "Upload a JSON list of contractor records. "
            "Imported records start with Not Called."
        )

        uploaded_file = st.file_uploader(
            "Choose JSON file",
            type=["json"],
            key="crm_json_upload",
        )

        if uploaded_file is not None:
            st.caption(
                f"Selected: {uploaded_file.name} · "
                f"{uploaded_file.size:,} bytes"
            )

            if st.button(
                "Import leads to Supabase",
                type="primary",
                key="crm_import_button",
            ):
                try:
                    with st.spinner("Importing leads..."):
                        imported = import_leads_json(uploaded_file)

                    # Reload the source data on the next render.
                    # The parent should pass a fresh database result.
                    st.session_state.pop("leads_cache", None)
                    st.session_state.pop(
                        "crm_committed_statuses", None
                    )

                    st.session_state["crm_grid_version"] = (
                        st.session_state.get("crm_grid_version", 0) + 1
                    )

                    st.session_state["crm_flash_success"] = (
                        f"Successfully imported {imported:,} leads."
                    )
                    st.rerun()

                except (
                    json.JSONDecodeError,
                    UnicodeDecodeError,
                    ValueError,
                ) as exc:
                    st.error(f"Invalid import file: {exc}")

                except Exception as exc:
                    st.error(f"Import failed: {exc}")

    # -----------------------------------------------------
    # SEARCH, FILTERS, SORT
    # -----------------------------------------------------

    st.markdown(
        '<div class="crm-section">All leads</div>',
        unsafe_allow_html=True,
    )

    col_search, col_status, col_sort = st.columns(
        [2.2, 1.4, 1.5]
    )

    with col_search:
        search = st.text_input(
            "Search",
            placeholder="Company, phone, city, state, website...",
            key="crm_search",
            label_visibility="collapsed",
        )

    with col_status:
        filter_labels = ["All statuses"] + [
            config["label"]
            for config in CRM_STATUSES_CONFIG.values()
        ]

        selected_label = st.selectbox(
            "Status",
            filter_labels,
            key="crm_status_filter",
            label_visibility="collapsed",
        )

    with col_sort:
        sort_options = [
            "Original order",
            "Company name",
            "Highest score",
            "Most reviews",
        ]

        sort_by = st.selectbox(
            "Sort",
            sort_options,
            key="crm_sort",
            label_visibility="collapsed",
        )

    # -----------------------------------------------------
    # FILTER WITHOUT MUTATING THE CACHE
    # -----------------------------------------------------

    filtered = list(current_leads)

    if search.strip():
        term = search.strip().casefold()

        searchable_fields = (
            "company_name",
            "phone",
            "city",
            "state",
            "website",
            "category_name",
            "address",
        )

        filtered = [
            lead
            for lead in filtered
            if any(
                term in str(lead.get(field) or "").casefold()
                for field in searchable_fields
            )
        ]

    if selected_label != "All statuses":
        selected_raw = STATUS_LABEL_TO_RAW[selected_label]

        filtered = [
            lead
            for lead in filtered
            if lead.get("status", DEFAULT_STATUS) == selected_raw
        ]

    # Sort only according to the user's explicit selection.
    # Status is never used as a sort key.
    if sort_by == "Original order":
        filtered.sort(
            key=lambda lead: lead.get("_row_order", 0)
        )

    elif sort_by == "Company name":
        filtered.sort(
            key=lambda lead: str(
                lead.get("company_name") or ""
            ).casefold()
        )

    elif sort_by == "Highest score":
        filtered.sort(
            key=lambda lead: float(
                lead.get("total_score") or 0
            ),
            reverse=True,
        )

    elif sort_by == "Most reviews":
        filtered.sort(
            key=lambda lead: int(
                lead.get("reviews_count") or 0
            ),
            reverse=True,
        )

    st.caption(
        f"Showing {len(filtered):,} matching leads · "
        f"{total_count:,} total loaded"
    )

    if not filtered:
        st.info(
            "No leads match your search or status filter."
        )
        return

    # -----------------------------------------------------
    # PAGINATION
    # -----------------------------------------------------

    total_pages = max(
        1,
        (len(filtered) + PAGE_SIZE - 1) // PAGE_SIZE,
    )

    if st.session_state.get("crm_page", 1) > total_pages:
        st.session_state["crm_page"] = total_pages

    page_col, page_info_col = st.columns([1, 3])

    with page_col:
        page = st.number_input(
            "Page",
            min_value=1,
            max_value=total_pages,
            step=1,
            key="crm_page",
        )

    with page_info_col:
        st.markdown(
            f'<div class="crm-muted" style="padding-top:2rem">'
            f'Page {int(page)} of {total_pages} · '
            f'{PAGE_SIZE} leads per page</div>',
            unsafe_allow_html=True,
        )

    start = (int(page) - 1) * PAGE_SIZE
    page_leads = filtered[start:start + PAGE_SIZE]

    # -----------------------------------------------------
    # BUILD GRID DATA
    # -----------------------------------------------------

    editor_rows = []

    for lead in page_leads:
        editor_rows.append({
            "id": str(lead.get("id") or ""),
            "_row_order": lead.get("_row_order", 0),
            "company_name": lead.get("company_name") or "",
            "status": lead.get("status", DEFAULT_STATUS),
            "phone": lead.get("phone") or "",
            "city": lead.get("city") or "",
            "state": lead.get("state") or "",
            "website": lead.get("website") or "",
            "category_name": lead.get("category_name") or "",
            "total_score": lead.get("total_score"),
            "reviews_count": lead.get("reviews_count"),
        })

    editor_df = pd.DataFrame(editor_rows)

    # -----------------------------------------------------
    # STATUS CELL COLORS
    # -----------------------------------------------------

    status_style_map = {
        status: {
            "color": config["color"],
            "backgroundColor": config["bg"],
            "fontWeight": "600",
            "borderRadius": "6px",
            "padding": "4px 8px",
        }
        for status, config in CRM_STATUSES_CONFIG.items()
    }

    status_style_json = json.dumps(status_style_map)

    status_cell_style = JsCode(f"""
        function(params) {{
            const styles = {status_style_json};
            const style = styles[params.value];

            if (style) {{
                return style;
            }}

            return {{
                color: "#64748b",
                backgroundColor: "#f1f5f9",
                fontWeight: "600",
                borderRadius: "6px",
                padding: "4px 8px"
            }};
        }}
    """)

    # -----------------------------------------------------
    # AGGRID
    # -----------------------------------------------------

    gb = GridOptionsBuilder.from_dataframe(editor_df)

    gb.configure_default_column(
        editable=False,
        sortable=True,
        filter=True,
        resizable=True,
        wrapText=False,
        autoHeight=False,
    )

    gb.configure_column(
        "id",
        header_name="ID",
        hide=True,
    )

    gb.configure_column(
        "_row_order",
        hide=True,
        sortable=False,
    )

    gb.configure_column(
        "company_name",
        header_name="Company",
        minWidth=200,
        flex=1,
        tooltipField="company_name",
    )

    gb.configure_column(
        "status",
        header_name="Lead status",
        editable=True,
        minWidth=205,
        cellEditor="agSelectCellEditor",
        cellEditorParams={"values": list(CRM_STATUSES_CONFIG.keys())},
        cellStyle=status_cell_style,
        singleClickEdit=True,
        sortable=False,
    )

    gb.configure_column("phone", header_name="Phone", minWidth=145)
    gb.configure_column("city", header_name="City", minWidth=110)
    gb.configure_column("state", header_name="State", width=90)

    gb.configure_column(
        "website",
        header_name="Website",
        minWidth=130,
        tooltipField="website",
    )

    gb.configure_column(
        "category_name",
        header_name="Category",
        minWidth=160,
        tooltipField="category_name",
    )

    gb.configure_column("total_score", header_name="Score", width=95)
    gb.configure_column("reviews_count", header_name="Reviews", width=105)

    gb.configure_grid_options(
        rowHeight=48,
        headerHeight=44,
        animateRows=False,
        stopEditingWhenCellsLoseFocus=True,
        suppressRowClickSelection=True,

        # Stable identity: AGGrid can identify the same lead across updates.
        getRowId=JsCode(
            "function(params) { return String(params.data.id); }"
        ),
    )

    grid_options = gb.build()

    grid_key = (
        f"crm_leads_grid_page_{int(page)}_"
        f"{st.session_state.get('crm_grid_version', 0)}"
    )

    grid_response = AgGrid(
        editor_df,
        gridOptions=grid_options,
        height=530,
        width="100%",
        theme="streamlit",
        key=grid_key,
        allow_unsafe_jscode=True,
        update_on=["cellValueChanged"],
        data_return_mode="AS_INPUT",
    )

    # -----------------------------------------------------
    # DETECT, SAVE, VERIFY, REFRESH
    # -----------------------------------------------------

    returned_data = grid_response.get("data", editor_df)

    if isinstance(returned_data, pd.DataFrame):
        edited_df = returned_data.copy()
    else:
        edited_df = pd.DataFrame(returned_data)

    process_grid_status_changes(edited_df, page_leads)

    # -----------------------------------------------------
    # QUICK CALL LIST
    # -----------------------------------------------------

    st.divider()

    with st.expander("📞 Quick call list", expanded=False):
        call_candidates = [
            lead
            for lead in filtered
            if lead.get("status") not in (
                "Won / Client",
                "Lost",
                "Not Interested",
                "Invalid / Do Not Call",
            )
        ]

        if not call_candidates:
            st.info("No active leads in the current filter.")

        else:
            for lead in call_candidates[:20]:
                company = lead.get("company_name") or "Unnamed company"
                phone = lead.get("phone") or "No phone number"
                status = lead.get("status", DEFAULT_STATUS)

                st.markdown(f"**{company}**")
                st.caption(f"{phone} · {status}")

                if lead.get("phone"):
                    st.code(str(lead["phone"]), language=None)

                st.divider()