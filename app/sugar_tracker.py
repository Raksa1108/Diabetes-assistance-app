import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import os
import json
from datetime import datetime, date, time
from openai import OpenAI

from app.diet_tracker import load_meal_log, get_current_user

API_KEY = "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"
client = OpenAI(api_key=API_KEY)

def get_user_sugar_filename(user_email):
    import hashlib
    email_hash = hashlib.md5(user_email.encode()).hexdigest()[:12]
    return f"sugar_log_{email_hash}.json"
import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime, date, time
from openai import OpenAI

from app.diet_tracker import load_meal_log, get_current_user
from app.history import get_diabetes_prediction, get_history_advice  # Adjust import if needed

# --- OpenAI API Setup ---
API_KEY = "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"
client = OpenAI(api_key=API_KEY)

# --- File Helpers ---
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
                    except Exception:
                        entry['timestamp'] = pd.to_datetime(entry['timestamp'])
            return data
    return []

# --- Spike/Downfall Detection ---
def detect_spike_downfall(sugar_log, food_log, window_minutes=120):
    if len(sugar_log) < 2:
        return "first", 0, []
    current = sugar_log[-1]
    previous = sugar_log[-2]
    delta = current['sugar_level'] - previous['sugar_level']
    recent_foods = [
        f for f in food_log
        if 0 <= (pd.to_datetime(current['timestamp']) - pd.to_datetime(f['timestamp'])).total_seconds() / 60 <= window_minutes
    ]
    if delta > 25:
        return "spike", delta, recent_foods
    elif delta < -20:
        return "downfall", delta, recent_foods
    else:
        return "stable", delta, recent_foods

# --- Preventive Measures via OpenAI (never mention API) ---
def get_preventive_measures(
    sugar_level, food_log, spike_status, delta, recent_foods, prediction, history_advice
):
    meal_str = ', '.join([f['food'] for f in food_log]) if food_log else "none"
    recent_str = ', '.join([f['food'] for f in recent_foods]) if recent_foods else "none"
    prompt = (
        f"User's current blood sugar: {sugar_level} mg/dL.\n"
        f"Change from last reading: {delta:+.0f} mg/dL ({spike_status}).\n"
        f"Recent foods: {recent_str}.\n"
        f"Overall food habits: {meal_str}.\n"
        f"Diabetes risk prediction: {prediction}.\n"
        f"History-based advice: {history_advice}.\n"
        "Give 2-3 concise, practical tips to manage blood sugar and prevent spikes or drops. "
        "If there's a spike, suggest when to stop eating sugary foods. Use simple, encouraging language "
        "with no medical jargon and never mention AI or API."
    )
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        store=True,
        messages=[{"role": "user", "content": prompt}]
    )
    return completion.choices[0].message.content.strip()

# --- Main Streamlit App ---
def app():
    st.title("🩸 Sugar Tracker")
    user_email = get_current_user()
    sugar_log = load_sugar_log(user_email)
    meal_log = load_meal_log(user_email)

    # --- Sugar Log Input ---
    st.subheader("Log Your Blood Sugar")
    with st.form("sugar_log_form"):
        sugar_level = st.number_input("Blood Sugar (mg/dL)", min_value=40, max_value=600, step=1)
        date_val = st.date_input("Date", value=date.today())
        time_val = st.time_input("Time", value=datetime.now().time())
        submitted = st.form_submit_button("Add Sugar Log")
        if submitted and sugar_level:
            timestamp = datetime.combine(date_val, time_val)
            sugar_log.append({
                "timestamp": timestamp,
                "sugar_level": sugar_level
            })
            save_sugar_log(sugar_log, user_email)
            st.success(f"Added sugar log: {sugar_level} mg/dL at {timestamp.strftime('%Y-%m-%d %H:%M')}")
            st.experimental_rerun()

    # --- Sugar Data Visualization ---
    st.subheader("Blood Sugar History")
    if sugar_log:
        df = pd.DataFrame(sugar_log)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values("timestamp")
        st.line_chart(df.set_index("timestamp")["sugar_level"], use_container_width=True)
        latest_entry = df.iloc[-1]
        st.markdown(
            f"**Latest Blood Sugar:** {int(latest_entry['sugar_level'])} mg/dL at "
            f"{latest_entry['timestamp'].strftime('%Y-%m-%d %H:%M')}"
        )
    else:
        st.info("No blood sugar data yet. Log your first value above.")

    # --- Advice Section ---
    if sugar_log:
        spike_status, delta, recent_foods = detect_spike_downfall(sugar_log, meal_log)
        # Get extra context
        try:
            prediction = get_diabetes_prediction(user_email)
        except Exception:
            prediction = "Not available"
        try:
            history_advice = get_history_advice(user_email)
        except Exception:
            history_advice = "Not available"

        try:
            with st.spinner("Analyzing your record..."):
                advice = get_preventive_measures(
                    sugar_level=sugar_log[-1]['sugar_level'],
                    food_log=meal_log,
                    spike_status=spike_status,
                    delta=delta,
                    recent_foods=recent_foods,
                    prediction=prediction,
                    history_advice=history_advice
                )
            st.markdown("### Personalized Advice")
            st.success(advice)
        except Exception:
            st.warning("Advice could not be generated at this time.")

    # --- Food Log Table ---
    st.subheader("Today's Food Log")
    if meal_log:
        meals_today = [m for m in meal_log if pd.to_datetime(m["timestamp"]).date() == date.today()]
        if meals_today:
            df_meals = pd.DataFrame(meals_today)
            st.dataframe(df_meals[["timestamp", "meal_time", "food", "quantity", "calories"]].sort_values("timestamp"))
        else:
            st.info("No meals logged today.")
    else:
        st.info("No meals logged yet.")

if __name__ == "__main__":
    app()
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
        # Use date_input and time_input instead of datetime_input
        date_val = st.date_input("Date", value=date.today())
        time_val = st.time_input("Time", value=datetime.now().time())
        submitted = st.form_submit_button("Add Sugar Log")
        if submitted and sugar_level:
            # Combine date and time into a datetime object
            timestamp = datetime.combine(date_val, time_val)
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
