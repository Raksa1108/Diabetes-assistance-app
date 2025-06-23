import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, date, timedelta
import numpy as np
from fpdf import FPDF
from io import BytesIO, StringIO
import json
import os
import hashlib
import pickle
import plotly.express as px
import plotly.graph_objects as go

# Timezone import for IST
try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")
except ImportError:
    import pytz
    IST = pytz.timezone("Asia/Kolkata")

# Import your existing styles
try:
    from data.base import st_style, head
except ImportError:
    # Fallback styles if import fails
    st_style = """
    <style>
    .main-header {
        font-size: 2rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    </style>
    """
    head = "<div class='main-header'>🔥 Calorie Tracker</div>"

def get_current_user():
    """Get current user email from session state."""
    user = st.session_state.get('current_user')
    if not user or not user.get('email'):
        st.error("User email not found. Please log in again.")
        st.stop()
    return user['email']

def get_user_filename(user_email):
    """Generate a safe filename for user's calorie history based on email."""
    email_hash = hashlib.md5(user_email.encode()).hexdigest()[:12]
    return f"calorie_history_{email_hash}.json"

def get_user_goal_filename(user_email):
    """Generate a safe filename for user's daily goal based on email."""
    email_hash = hashlib.md5(user_email.encode()).hexdigest()[:12]
    return f"daily_goal_{email_hash}.json"

def save_calorie_history(calorie_history, user_email):
    """Save calorie history to a JSON file for persistence."""
    filename = get_user_filename(user_email)
    try:
        os.makedirs("user_data", exist_ok=True)
        filepath = os.path.join("user_data", filename)
        with open(filepath, "w") as f:
            serializable_history = []
            for record in calorie_history:
                record_copy = record.copy()
                if isinstance(record_copy['DateTime'], datetime):
                    record_copy['DateTime'] = record_copy['DateTime'].isoformat()
                serializable_history.append(record_copy)
            json.dump(serializable_history, f)
    except Exception as e:
        st.error(f"Failed to save calorie history: {e}")

def load_calorie_history(user_email):
    """Load calorie history from a JSON file."""
    filename = get_user_filename(user_email)
    filepath = os.path.join("user_data", filename)
    try:
        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                data = json.load(f)
                for record in data:
                    if isinstance(record['DateTime'], str):
                        try:
                            dt = datetime.fromisoformat(record['DateTime'])
                            if dt.tzinfo is None:
                                dt = dt.replace(tzinfo=IST)
                            else:
                                dt = dt.astimezone(IST)
                            record['DateTime'] = dt
                        except ValueError:
                            dt = pd.to_datetime(record['DateTime'], utc=True).tz_convert(IST)
                            record['DateTime'] = dt.to_pydatetime()
                return data
        return []
    except Exception as e:
        st.error(f"Failed to load calorie history: {e}")
        return []

def save_daily_goal(daily_goal, user_email):
    """Save daily calorie burn goal for specific user."""
    filename = get_user_goal_filename(user_email)
    try:
        os.makedirs("user_data", exist_ok=True)
        filepath = os.path.join("user_data", filename)
        with open(filepath, "w") as f:
            json.dump({"daily_goal": daily_goal}, f)
    except Exception as e:
        st.error(f"Failed to save daily goal: {e}")

def load_daily_goal(user_email):
    """Load daily calorie burn goal for specific user."""
    filename = get_user_goal_filename(user_email)
    filepath = os.path.join("user_data", filename)
    try:
        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                data = json.load(f)
                return data.get("daily_goal", 500)
        return 500
    except Exception as e:
        st.error(f"Failed to load daily goal: {e}")
        return 500

def initialize_user_session(user_email):
    """Initialize session state for user-specific data."""
    history_key = f"calorie_history_{user_email}"
    goal_key = f"daily_goal_{user_email}"
    profile_key = f"user_profile_{user_email}"
    
    if history_key not in st.session_state:
        st.session_state[history_key] = load_calorie_history(user_email)
    if goal_key not in st.session_state:
        st.session_state[goal_key] = load_daily_goal(user_email)
    if profile_key not in st.session_state:
        st.session_state[profile_key] = {}

def generate_pdf_report(calorie_history, daily_goal, user_email):
    """Generate a PDF report for calorie history."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=14)
    pdf.cell(0, 10, "Calorie Burn Daily Report", ln=True, align="C")
    
    pdf.set_font("Arial", size=12)
    pdf.ln(5)
    pdf.cell(0, 10, f"User: {user_email}", ln=True)
    pdf.ln(5)
    
    total_calories = sum(record['Calories Burnt (kcal)'] for record in calorie_history)
    pdf.cell(0, 10, f"Daily Calorie Burn Goal: {daily_goal} kcal", ln=True)
    pdf.cell(0, 10, f"Calories Burnt: {total_calories:.2f} kcal", ln=True)
    pdf.ln(10)

    pdf.cell(0, 10, "Logged Exercises:", ln=True)
    pdf.set_font("Arial", size=10)
    for record in calorie_history:
        dt = record['DateTime']
        if isinstance(dt, str):
            dt = datetime.fromisoformat(dt)
        record_text = f"{dt.strftime('%Y-%m-%d %H:%M:%S')} - {record['Exercise Type']} - {record['Duration (min)']} min - {record['Calories Burnt (kcal)']} kcal"
        try:
            pdf.cell(0, 8, record_text, ln=True)
        except UnicodeEncodeError:
            pdf.cell(0, 8, record_text.encode('latin-1', 'replace').decode('latin-1'), ln=True)

    pdf_output = BytesIO()
    pdf_output.write(pdf.output(dest='S').encode('latin-1'))
    pdf_output.seek(0)
    return pdf_output

# Simple calorie estimation function (fallback if model doesn't exist)
def estimate_calories_simple(gender, age, weight, duration, heart_rate):
    """Simple calorie estimation formula as fallback"""
    # Basic MET calculation
    met_values = {
        "Running": 8.0,
        "Cycling": 6.0,
        "Walking": 3.5,
        "Swimming": 7.0,
        "Yoga": 3.0,
        "Strength Training": 5.0,
        "Other": 4.0
    }
    
    # Adjust based on heart rate intensity
    if heart_rate > 160:
        intensity_multiplier = 1.3
    elif heart_rate > 140:
        intensity_multiplier = 1.1
    else:
        intensity_multiplier = 0.9
    
    # Basic formula: MET * weight(kg) * time(hours) * intensity
    base_met = 5.0  # default MET value
    calories = base_met * weight * (duration / 60) * intensity_multiplier
    
    # Gender adjustment
    if gender == "Female":
        calories *= 0.9
    
    return calories

def calories_tab():
    """🔥 Calories Burnt Estimator"""
    current_user = get_current_user()
    initialize_user_session(current_user)
    
    history_key = f"calorie_history_{current_user}"
    goal_key = f"daily_goal_{current_user}"
    profile_key = f"user_profile_{current_user}"
    
    st.title("🔥 Calories Burnt Estimator")
    st.markdown("Estimate calories burnt during an activity based on health metrics and exercise type.")
    
    # Try to load model, use simple estimation if not available
    model = None
    try:
        with open("calories_model.pkl", "rb") as f:
            model = pickle.load(f)
    except FileNotFoundError:
        st.warning("Advanced model not found. Using simple estimation method.")
    except Exception as e:
        st.warning(f"Could not load model: {e}. Using simple estimation method.")
    
    # Sidebar for settings
    with st.sidebar:
        st.header("⚙️ Settings")
        st.markdown(f"**👤 Logged in as:** {current_user}")
        daily_goal = st.number_input(
            "Daily Calorie Burn Goal (kcal)", 
            min_value=100, max_value=2000, 
            value=st.session_state[goal_key],
            help="Set your daily calorie burning target"
        )
        if daily_goal != st.session_state[goal_key]:
            st.session_state[goal_key] = daily_goal
            save_daily_goal(daily_goal, current_user)
        
        st.subheader("👤 User Profile")
        if st.button("💾 Save Current Profile"):
            if f"last_inputs_{current_user}" in st.session_state:
                st.session_state[profile_key] = st.session_state[f"last_inputs_{current_user}"].copy()
                st.success("Profile saved!")
        if st.session_state[profile_key] and st.button("📂 Load Saved Profile"):
            st.session_state[f"load_profile_{current_user}"] = True
            st.success("Profile will be loaded!")
    
    # Main input form
    st.subheader("📝 Exercise Details")
    load_profile = getattr(st.session_state, f"load_profile_{current_user}", False)
    profile = st.session_state[profile_key] if load_profile else {}
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Personal Information**")
        gender = st.selectbox(
            "Gender", ["Male", "Female"], 
            index=0 if profile.get('gender') == 'Male' else 1 if 'gender' in profile else 0
        )
        age = st.number_input(
            "Age", min_value=10, max_value=100, 
            value=profile.get('age', 30)
        )
        height = st.number_input(
            "Height (cm)", min_value=100, max_value=250, 
            value=profile.get('height', 170)
        )
        weight = st.number_input(
            "Weight (kg)", min_value=30, max_value=200, 
            value=profile.get('weight', 70)
        )
        bmi = weight / ((height/100) ** 2)
        bmi_category = "Underweight" if bmi < 18.5 else "Normal" if bmi < 25 else "Overweight" if bmi < 30 else "Obese"
        st.info(f"BMI: {bmi:.1f} ({bmi_category})")
    
    with col2:
        st.markdown("**Exercise Information**")
        duration = st.number_input(
            "Exercise Duration (minutes)", min_value=1, max_value=180, 
            value=profile.get('duration', 30)
        )
        exercise_types = [
            "Running", "Cycling", "Walking", "Swimming", "Yoga", "Strength Training", 
            "Hiking", "Dancing", "Rowing", "Boxing", "Tennis", "Basketball", "Other"
        ]
        exercise_type = st.selectbox(
            "Exercise Type", exercise_types,
            index=exercise_types.index(profile.get('exercise_type', 'Running')) if profile.get('exercise_type') in exercise_types else 0
        )
        max_hr = 220 - age
        moderate_hr = int(max_hr * 0.64)
        vigorous_hr = int(max_hr * 0.77)
        heart_rate = st.number_input(
            "Average Heart Rate", min_value=60, max_value=200, 
            value=profile.get('heart_rate', moderate_hr),
            help=f"Suggested ranges: Moderate ({moderate_hr}), Vigorous ({vigorous_hr})"
        )
        body_temp = st.number_input(
            "Body Temperature (°C)", min_value=35.0, max_value=42.0, 
            value=profile.get('body_temp', 38.5), step=0.1
        )
        intensity = "Light" if heart_rate < moderate_hr else "Moderate" if heart_rate < vigorous_hr else "Vigorous"
        intensity_color = "🟢" if intensity == "Light" else "🟡" if intensity == "Moderate" else "🔴"
        st.info(f"Intensity Level: {intensity_color} {intensity}")
    
    if load_profile:
        st.session_state[f"load_profile_{current_user}"] = False
    
    # Estimate button
    if st.button("🔥 Estimate Calories Burnt", type="primary"):
        errors = []
        if duration <= 0:
            errors.append("Duration must be greater than 0 minutes")
        if heart_rate < 60 or heart_rate > 200:
            errors.append("Heart rate seems unusual (should be 60-200 bpm)")
        if body_temp < 35 or body_temp > 42:
            errors.append("Body temperature seems unusual (should be 35-42°C)")
        
        if errors:
            for error in errors:
                st.error(error)
        else:
            st.session_state[f"last_inputs_{current_user}"] = {
                'gender': gender, 'age': age, 'height': height, 'weight': weight,
                'duration': duration, 'exercise_type': exercise_type, 
                'heart_rate': heart_rate, 'body_temp': body_temp
            }
            
            # Calculate calories using model or simple estimation
            if model is not None:
                gender_encoded = 1 if gender == "Male" else 0
                input_data = np.array([[gender_encoded, age, height, weight, duration, heart_rate, body_temp]])
                calories = model.predict(input_data)[0]
            else:
                calories = estimate_calories_simple(gender, age, weight, duration, heart_rate)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Calories Burnt", f"{calories:.1f} kcal")
            with col2:
                calories_per_min = calories / duration
                st.metric("Rate", f"{calories_per_min:.1f} kcal/min")
            with col3:
                calories_per_kg = calories / weight
                st.metric("Per kg body weight", f"{calories_per_kg:.1f} kcal/kg")
            
            record = {
                'DateTime': datetime.now(IST),
                'Date': datetime.now(IST).strftime('%Y-%m-%d'),
                'Time': datetime.now(IST).strftime('%H:%M:%S'),
                'Gender': gender,
                'Age': age,
                'Height (cm)': height,
                'Weight (kg)': weight,
                'Duration (min)': round(duration, 1),
                'Exercise Type': exercise_type,
                'Heart Rate': heart_rate,
                'Body Temp (°C)': body_temp,
                'Calories Burnt (kcal)': round(calories, 2),
                'Intensity': intensity,
                'BMI': round(bmi, 1)
            }
            st.session_state[history_key].append(record)
            save_calorie_history(st.session_state[history_key], current_user)
            st.success("✅ Calories estimated and added to history!")
    
    # Quick exercise buttons
    st.subheader("⚡ Quick Estimates")
    quick_col1, quick_col2, quick_col3, quick_col4 = st.columns(4)
    quick_exercises = [
        ("🏃‍♂️ 30min Run", {"exercise_type": "Running", "duration": 30, "heart_rate": 150}),
        ("🚴‍♀️ 45min Bike", {"exercise_type": "Cycling", "duration": 45, "heart_rate": 130}),
        ("🚶‍♂️ 60min Walk", {"exercise_type": "Walking", "duration": 60, "heart_rate": 110}),
        ("🏊‍♀️ 30min Swim", {"exercise_type": "Swimming", "duration": 30, "heart_rate": 140})
    ]
    for i, (label, params) in enumerate(quick_exercises):
        col = [quick_col1, quick_col2, quick_col3, quick_col4][i]
        with col:
            if st.button(label, key=f"quick_{i}_{current_user}"):
                if model is not None:
                    gender_encoded = 1 if gender == "Male" else 0
                    input_data = np.array([[
                        gender_encoded, age, height, weight, 
                        params["duration"], params["heart_rate"], 38.5
                    ]])
                    quick_calories = model.predict(input_data)[0]
                else:
                    quick_calories = estimate_calories_simple(gender, age, weight, params["duration"], params["heart_rate"])
                st.write(f"~{quick_calories:.0f} kcal")
    
    # History and Analytics
    st.subheader("📊 Analytics & History")
    if st.session_state[history_key]:
        history_df = pd.DataFrame(st.session_state[history_key])
        history_df['DateTime'] = pd.to_datetime(history_df['DateTime'], errors='coerce', utc=True).dt.tz_convert(IST)
        
        tab1, tab2, tab3, tab4 = st.tabs(["📈 Charts", "📋 History", "📊 Stats", "💾 Export"])
        with tab1:
            today = datetime.now(IST).strftime('%Y-%m-%d')
            today_calories = history_df[history_df['Date'] == today]['Calories Burnt (kcal)'].sum()
            progress = min(today_calories / st.session_state[goal_key], 1.0)
            st.metric(
                "Today's Progress", 
                f"{today_calories:.0f} / {st.session_state[goal_key]} kcal",
                f"{(progress * 100):.1f}% of goal"
            )
            st.progress(progress)
            
            if len(history_df) > 1:
                daily_totals = history_df.groupby('Date')['Calories Burnt (kcal)'].sum().reset_index()
                fig1 = px.line(daily_totals, x='Date', y='Calories Burnt (kcal)', 
                               title='Daily Calorie Burn Trend')
                fig1.add_hline(y=st.session_state[goal_key], line_dash="dash", 
                               annotation_text="Daily Goal")
                st.plotly_chart(fig1, use_container_width=True)
                
                exercise_totals = history_df.groupby('Exercise Type')['Calories Burnt (kcal)'].sum()
                fig2 = px.pie(values=exercise_totals.values, names=exercise_totals.index,
                              title='Calories by Exercise Type')
                st.plotly_chart(fig2, use_container_width=True)
        
        with tab2:
            st.write(f"**Total Records:** {len(history_df)}")
            filter_col1, filter_col2 = st.columns(2)
            with filter_col1:
                selected_exercises = st.multiselect(
                    "Filter by Exercise Type",
                    options=history_df['Exercise Type'].unique(),
                    default=history_df['Exercise Type'].unique()
                )
            with filter_col2:
                date_range = st.date_input(
                    "Date Range",
                    value=(datetime.now(IST).date() - timedelta(days=7), datetime.now(IST).date()),
                    max_value=datetime.now(IST).date()
                )
            
            filtered_df = history_df[history_df['Exercise Type'].isin(selected_exercises)]
            if len(date_range) == 2:
                start_date, end_date = date_range
                filtered_df = filtered_df[
                    (pd.to_datetime(filtered_df['Date']) >= pd.to_datetime(start_date)) &
                    (pd.to_datetime(filtered_df['Date']) <= pd.to_datetime(end_date))
                ]
            
            st.dataframe(
                filtered_df.sort_values('DateTime', ascending=False),
                use_container_width=True, hide_index=True
            )
        
        with tab3:
            st.subheader("📈 Summary Statistics")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Sessions", len(history_df))
            with col2:
                st.metric("Total Calories", f"{history_df['Calories Burnt (kcal)'].sum():.0f}")
            with col3:
                st.metric("Average per Session", f"{history_df['Calories Burnt (kcal)'].mean():.0f}")
            with col4:
                st.metric("Total Exercise Time", f"{history_df['Duration (min)'].sum():.0f} min")
            
            st.subheader("🔍 Detailed Analysis")
            stats_df = history_df.groupby('Exercise Type').agg({
                'Calories Burnt (kcal)': ['count', 'sum', 'mean', 'max'],
                'Duration (min)': 'sum'
            }).round(1)
            stats_df.columns = ['Sessions', 'Total Calories', 'Avg Calories', 'Max Calories', 'Total Minutes']
            st.dataframe(stats_df, use_container_width=True)
        
        with tab4:
            st.subheader("💾 Export Data")
            csv_buffer = StringIO()
            history_df.to_csv(csv_buffer, index=False)
            st.download_button(
                label="📄 Download as CSV",
                data=csv_buffer.getvalue(),
                file_name=f"calorie_history_{current_user.replace('@', '_')}_{date.today()}.csv",
                mime="text/csv"
            )
            
            json_data = history_df.to_json(orient='records', indent=2)
            st.download_button(
                label="📋 Download as JSON",
                data=json_data,
                file_name=f"calorie_history_{current_user.replace('@', '_')}_{date.today()}.json",
                mime="application/json"
            )
            
            if st.button("Download Daily Report PDF"):
                today_df = history_df[history_df['Date'] == today]
                pdf_bytes = generate_pdf_report(today_df.to_dict('records'), st.session_state[goal_key], current_user)
                st.download_button(
                    label="Download PDF",
                    data=pdf_bytes,
                    file_name=f"calorie_report_{current_user.replace('@', '_')}_{date.today()}.pdf",
                    mime="application/pdf"
                )
        
        st.divider()
        if st.button("🗑️ Clear All History", type="secondary"):
            st.session_state[history_key] = []
            save_calorie_history(st.session_state[history_key], current_user)
            st.success("All calorie history cleared!")
            st.rerun()
    
    else:
        st.info("📝 No calorie burn records yet. Start by estimating some calories to unlock analytics!")

def app():
    """Main function to run the calorie tracker"""
    # Apply styling
    st.markdown(st_style, unsafe_allow_html=True)
    st.markdown(head, unsafe_allow_html=True)
    st.markdown("""
    <style>
    .metric-container { background-color: #f0f2f6; padding: 1rem; border-radius: 0.5rem; margin: 0.5rem 0; }
    .stProgress > div > div > div > div { background-color: #ff6b6b; }
    </style>
    """, unsafe_allow_html=True)
    
    # Run the calorie tracker
    calories_tab()

if __name__ == "__main__":
    main()
