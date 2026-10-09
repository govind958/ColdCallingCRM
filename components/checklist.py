import streamlit as st
from datetime import date
from supabase_client import supabase


def render_checklist():
    # Get current logged-in user from session state
    username = st.session_state.get("username", "govind")
    today_str = str(date.today())

    st.markdown("<div class='main-title'>☑️ Daily Outreach & Hunt Checklist</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='main-subtitle'>Track your daily prospecting goals and watch your scaling targets grow.</div>",
        unsafe_allow_html=True)

    # ---------------------------------------------------------
    # 1. FETCH OR INITIALIZE TODAY'S DATA FROM SUPABASE
    # ---------------------------------------------------------
    try:
        response = supabase.table("daily_checklist") \
            .select("*") \
            .eq("username", username) \
            .eq("date", today_str) \
            .execute()

        existing_data = response.data[0] if response.data else None
    except Exception:
        existing_data = None

    if existing_data:
        default_emails = existing_data.get("emails_done", False)
        default_dms = existing_data.get("dms_done", False)
        default_calls = existing_data.get("calls_done", False)
        default_linkedin = existing_data.get("linkedin_done", False)
        default_content = existing_data.get("content_done", False)
        current_day_number = existing_data.get("day_number", 1)
    else:
        default_emails = False
        default_dms = False
        default_calls = False
        default_linkedin = False
        default_content = False

        try:
            count_res = supabase.table("daily_checklist") \
                .select("id", count="exact") \
                .eq("username", username) \
                .execute()
            total_logged = count_res.count or 0
            current_day_number = min(total_logged + 1, 30)
        except:
            current_day_number = 1

    # ---------------------------------------------------------
    # 2. CALCULATE PROGRESSIVE TARGETS (5 to 70 scaling over 30 days)
    # ---------------------------------------------------------
    min_target = 5
    max_target = 70
    total_days = 30

    if current_day_number <= 1:
        current_action_target = min_target
    elif current_day_number >= total_days:
        current_action_target = max_target
    else:
        step = (max_target - min_target) / (total_days - 1)
        current_action_target = int(round(min_target + step * (current_day_number - 1)))

    # ---------------------------------------------------------
    # 3. INTERACTIVE CHECKLIST FORM
    # ---------------------------------------------------------
    with st.form("checklist_form"):
        col_meta1, col_meta2 = st.columns(2)
        with col_meta1:
            st.markdown(f"**📅 Date:** `{today_str}`")
            st.markdown(f"**👤 User:** `{username}`")
        with col_meta2:
            st.markdown(f"**📈 30-Day Ramp-up Day:** `Day {current_day_number} of 30`")
            st.markdown(f"**🎯 Today's Target Volume:** `{current_action_target} Outreach Actions` *(Goal: 70)*")

        st.divider()

        st.markdown("#### Daily Hunt Tasks")

        emails = st.checkbox("New personalized emails (20)", value=default_emails)
        dms = st.checkbox("New Facebook DMs (20)", value=default_dms)
        calls = st.checkbox("Cold call attempts (20)", value=default_calls)
        linkedin = st.checkbox("New LinkedIn outreach actions (20)", value=default_linkedin)
        content = st.checkbox("20 Minutes of content creation/posting daily", value=default_content)

        tasks = [emails, dms, calls, linkedin, content]
        completed_count = sum(1 for t in tasks if t)
        total_tasks = len(tasks)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"### **{completed_count}/{total_tasks} completed**")
        st.progress(completed_count / total_tasks)

        st.markdown("<br>", unsafe_allow_html=True)
        submit_btn = st.form_submit_button("💾 Save Today's Checklist Progress")

        if submit_btn:
            payload = {
                "username": username,
                "date": today_str,
                "day_number": current_day_number,
                "target_volume": current_action_target,
                "emails_done": emails,
                "dms_done": dms,
                "calls_done": calls,
                "linkedin_done": linkedin,
                "content_done": content,
                "completed_count": completed_count
            }

            try:
                if existing_data:
                    supabase.table("daily_checklist") \
                        .update(payload) \
                        .eq("id", existing_data["id"]) \
                        .execute()
                else:
                    supabase.table("daily_checklist") \
                        .insert(payload) \
                        .execute()

                st.success("✅ Progress saved successfully to Supabase!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error saving to Supabase: {e}")