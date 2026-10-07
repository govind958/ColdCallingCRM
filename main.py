import streamlit as st
from supabase_client import supabase

st.set_page_config(
    page_title="Roofing CRM",
    layout="wide"
)

st.title("📞 Roofing Cold Call CRM")

response = supabase.table("leads").select("*").execute()

leads = response.data

st.write("Leads from Supabase:")

st.dataframe(leads, use_container_width=True)