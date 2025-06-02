from supabase import create_client, Client

SUPABASE_URL = "https://fuvvowjkyfmnbyadpcbb.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZ1dnZvd2preWZtbmJ5YWRwY2JiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDg4OTM2NjQsImV4cCI6MjA2NDQ2OTY2NH0.KzDsYyKwZipMyTFbnGdhKlBv3cxlGSFeydVJ_p03Uwg"

def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = get_supabase()
