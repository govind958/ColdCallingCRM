from supabase_client import supabase

new_lead = {
    "company_name": "Test Roofing Company",
    "contact_name": "John",
    "phone": "555-123-4567",
    "status": "Not Called"
}

response = supabase.table("leads").insert(new_lead).execute()

print(response.data)