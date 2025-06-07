import streamlit as st
from app.diet_tracker import app as diet_tracker_app
from app.nutrient_analysis import nutrition_analysis_app
from app.history import supabase
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")

def load_blood_sugar(user_email):
    """Load blood sugar (glucose) data for a user from Supabase predictions table."""
    try:
        response = (
            supabase.table("predictions")
            .select("timestamp, glucose")
            .eq("user_email", user_email)
            .order("timestamp", desc=True)
            .execute()
        )
        if response.data:
            blood_sugar_data = [
                {
                    "timestamp": pd.to_datetime(item['timestamp']).tz_convert(IST),
                    "glucose": float(item['glucose']) if item['glucose'] is not None else 0.0
                }
                for item in response.data
            ]
            return blood_sugar_data
        return []
    except Exception as e:
        st.error(f"Failed to load blood sugar data: {str(e)}")
        return []

def main():
    # Get current user
    if 'current_user' not in st.session_state or not st.session_state['current_user'].get('email'):
        st.error("User email not found. Please log in again.")
        st.stop()
    current_user = st.session_state['current_user']['email']
    
    # Load meal log and blood sugar data for the user
    from app.diet_tracker import load_meal_log
    meal_log = load_meal_log(current_user)
    blood_sugar_data = load_blood_sugar(current_user)
    
    # Create tabs
    tab1, tab2 = st.tabs(["Diet Tracker", "Nutrient Analysis"])
    
    with tab1:
        diet_tracker_app()
    
    with tab2:
        nutrition_analysis_app(current_user, meal_log, blood_sugar_data)

if __name__ == "__main__":
    main()
