import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from openai import OpenAI

from supabase_client import supabase  # Assumed present as in other files
from app.diet_tracker import load_meal_log, get_current_user

# --- OpenAI client setup (keep this hidden from user) ---
_openai_api_key = "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"
client = OpenAI(api_key=_openai_api_key)

# --- Helper: Query OpenAI for preventive suggestions ---
def get_preventive_measures(sugar_level, food_log):
    prompt = (
        f"The user's latest blood sugar is {sugar_level} mg/dL.\n"
        f"Today's meals: {', '.join([f['food'] for f in food_log])}.\n"
        "Based on this, give 2-3 short, practical preventive advice for diabetes management, "
        "focusing on sugar intake, meal timing, and healthy habits. "
        "If sugar is high, suggest when to stop eating sugar-heavy foods. "
        "If food log is good, praise briefly. Very concise, no medical jargon. No mention of AI or API."
    )
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        store=True,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    return completion.choices[0].message.content.strip()

# --- Helper: Fetch sugar data from supabase ---
def fetch_sugar_history(user_email):
    response = (
        supabase.table("sugar_logs")
        .select("*")
        .eq("user_email", user_email)
        .order("timestamp", desc=True)
        .execute()
    )
    return pd.DataFrame(response.data) if response.data else pd.DataFrame(columns=['timestamp', 'sugar_level'])

# --- Streamlit App ---
def app():
    st.title("🩸 Sugar Tracker")

    user_email = get_current_user()
    sugar_df = fetch_sugar_history(user_email)
    meal_log = load_meal_log(user_email)

    # --- Sugar Log Input ---
    st.subheader("Log Your Blood Sugar")
    with st.form("sugar_log_form"):
        sugar_level = st.number_input("Blood Sugar (mg/dL)", min_value=40, max_value=600, step=1)
        timestamp = st.datetime_input("Time", value=datetime.now())
        submitted = st.form_submit_button("Add Sugar Log")
        if submitted and sugar_level:
            # Insert new sugar log
            supabase.table("sugar_logs").insert({
                "user_email": user_email,
                "sugar_level": sugar_level,
                "timestamp": timestamp.isoformat(),
            }).execute()
            st.success(f"Added sugar log: {sugar_level} mg/dL at {timestamp.strftime('%Y-%m-%d %H:%M')}")
            st.experimental_rerun()

    # --- Sugar Data Visualization ---
    st.subheader("Blood Sugar History")
    if not sugar_df.empty:
        sugar_df['timestamp'] = pd.to_datetime(sugar_df['timestamp'])
        sugar_df = sugar_df.sort_values("timestamp")
        st.line_chart(
            data=sugar_df.set_index("timestamp")["sugar_level"],
            use_container_width=True
        )

        st.markdown(f"**Latest Blood Sugar:** {int(sugar_df['sugar_level'].iloc[-1])} mg/dL at {sugar_df['timestamp'].iloc[-1].strftime('%Y-%m-%d %H:%M')}")
    else:
        st.info("No blood sugar data yet. Log your first value above.")

    # --- Analysis & Preventive Advice ---
    if not sugar_df.empty:
        latest_sugar = int(sugar_df['sugar_level'].iloc[-1])
        today_meals = [m for m in meal_log if pd.to_datetime(m["timestamp"]).date() == datetime.now().date()]
        try:
            with st.spinner("Analyzing your data..."):
                advice = get_preventive_measures(latest_sugar, today_meals)
            st.markdown("### Personalized Advice")
            st.success(advice)
        except Exception:
            st.warning("Could not analyze advice at this time.")

    # --- Food Log Table ---
    st.subheader("Today's Food Log")
    if meal_log:
        meals_today = [m for m in meal_log if pd.to_datetime(m["timestamp"]).date() == datetime.now().date()]
        if meals_today:
            df_meals = pd.DataFrame(meals_today)
            st.dataframe(df_meals[["timestamp", "meal_time", "food", "quantity", "calories"]].sort_values("timestamp"))
        else:
            st.info("No meals logged today.")
    else:
        st.info("No meals logged yet.")

if __name__ == "__main__":
    app()
