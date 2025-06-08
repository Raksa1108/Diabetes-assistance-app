import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import os
import json
from datetime import datetime
from openai import OpenAI

from app.diet_tracker import load_meal_log, get_current_user

API_KEY = "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"
client = OpenAI(api_key=API_KEY)

def get_user_sugar_filename(user_email):
    import hashlib
    email_hash = hashlib.md5(user_email.encode()).hexdigest()[:12]
    return f"sugar_log_{email_hash}.json"

def save_sugar_log(sugar_log, user_email):
    filename = get_user_sugar_filename(user_email)
    os.makedirs("user_data", exist_ok=True)
    filepath = os.path.join("user_data", filename)
    serializable_log = []
    for entry in sugar_log:
        entry_copy = entry.copy()
        if isinstance(entry_copy['timestamp'], datetime):
            entry_copy['timestamp'] = entry_copy['timestamp'].isoformat()
        serializable_log.append(entry_copy)
    with open(filepath, "w") as f:
        json.dump(serializable_log, f)

def load_sugar_log(user_email):
    filename = get_user_sugar_filename(user_email)
    filepath = os.path.join("user_data", filename)
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            data = json.load(f)
            for entry in data:
                if isinstance(entry['timestamp'], str):
                    try:
                        entry['timestamp'] = datetime.fromisoformat(entry['timestamp'])
                    except ValueError:
                        entry['timestamp'] = pd.to_datetime(entry['timestamp'])
            return data
    return []

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

def app():
    st.title("🩸 Sugar Tracker")
    user_email = get_current_user()
    sugar_log = load_sugar_log(user_email)
    meal_log = load_meal_log(user_email)

    # Sugar Log Input
    st.subheader("Log Your Blood Sugar")
    with st.form("sugar_log_form"):
        sugar_level = st.number_input("Blood Sugar (mg/dL)", min_value=40, max_value=600, step=1)
        timestamp = st.datetime_input("Time", value=datetime.now())
        submitted = st.form_submit_button("Add Sugar Log")
        if submitted and sugar_level:
            sugar_log.append({
                "timestamp": timestamp,
                "sugar_level": sugar_level
            })
            save_sugar_log(sugar_log, user_email)
            st.success(f"Added sugar log: {sugar_level} mg/dL at {timestamp.strftime('%Y-%m-%d %H:%M')}")
            st.experimental_rerun()

    # Sugar Data Visualization
    st.subheader("Blood Sugar History")
    if sugar_log:
        df = pd.DataFrame(sugar_log)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values("timestamp")
        st.line_chart(
            data=df.set_index("timestamp")["sugar_level"],
            use_container_width=True
        )
        latest_entry = df.iloc[-1]
        st.markdown(f"**Latest Blood Sugar:** {int(latest_entry['sugar_level'])} mg/dL at {latest_entry['timestamp'].strftime('%Y-%m-%d %H:%M')}")
    else:
        st.info("No blood sugar data yet. Log your first value above.")

    # Advice Section
    if sugar_log:
        latest_sugar = int(sugar_log[-1]['sugar_level'])
        today_meals = [m for m in meal_log if pd.to_datetime(m["timestamp"]).date() == datetime.now().date()]
        try:
            with st.spinner("Analyzing your data..."):
                advice = get_preventive_measures(latest_sugar, today_meals)
            st.markdown("### Personalized Advice")
            st.success(advice)
        except Exception:
            st.warning("Could not analyze advice at this time.")

    # Food Log Table
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
