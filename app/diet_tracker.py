import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt
from datetime import datetime, date, timedelta
import numpy as np
from fpdf import FPDF
from io import BytesIO
import json
import os
from data.base import st_style, head
import hashlib

# Timezone import for IST
try:
    from zoneinfo import ZoneInfo  # Python 3.9+
    IST = ZoneInfo("Asia/Kolkata")
except ImportError:
    from pytz import timezone
    IST = timezone("Asia/Kolkata")

@st.cache_data
def load_datasets():
    try:
        pred_food = pd.read_csv("dataset/pred_food.csv", encoding="ISO-8859-1")
        daily_nutrition = pd.read_csv("dataset/daily_food_nutrition_dataset.csv", encoding="ISO-8859-1")
        indian_food = pd.read_csv("dataset/indian_food.csv", encoding="ISO-8859-1")
        indian_food1 = pd.read_csv("dataset/Indian_Food_DF.csv", encoding="ISO-8859-1")
        full_nutrition = pd.read_csv("dataset/Nutrition_Dataset.csv", encoding="ISO-8859-1")
        indian_processed = pd.read_csv("dataset/Indian_Food_Nutrition_Processed.csv", encoding="ISO-8859-1")
    except Exception as e:
        st.error(f"Dataset loading failed: {e}")
        return None, None, None, None, None, None
    return pred_food, daily_nutrition, indian_food, indian_food1, full_nutrition, indian_processed

def merge_datasets(*datasets):
    dfs = []
    for df in datasets[:-1]:  # first five datasets
        if df is not None:
            df.columns = [col.lower().strip() for col in df.columns]
            if 'food' in df.columns and 'calories' in df.columns:
                dfs.append(df[['food', 'calories']].copy())

    processed = datasets[-1]
    if processed is not None:
        processed.columns = [col.lower().strip() for col in processed.columns]
        processed['food'] = processed['dish name'].str.lower()
        processed['calories'] = processed['calories (kcal)']
        dfs.append(processed[['food', 'calories']])

    combined = pd.concat(dfs, ignore_index=True)
    combined = combined.drop_duplicates(subset='food')
    combined['food'] = combined['food'].str.lower()
    return combined

def fetch_nutritional_info(food_name):
    api_key = "iBOUPzaCXlEy5E4Z4qz758aWgVQobfE6ck2kSXIw"
    url = f"https://api.nal.usda.gov/fdc/v1/foods/search?query={food_name}&api_key={api_key}"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('foods'):
                nutrients = data['foods'][0].get('foodNutrients', [])
                calories = next((item['value'] for item in nutrients if item.get('nutrientName') == 'Energy'), None)
                carbs = next((item['value'] for item in nutrients if item.get('nutrientName') == 'Carbohydrate, by difference'), None)
                protein = next((item['value'] for item in nutrients if item.get('nutrientName') == 'Protein'), 0)
                fat = next((item['value'] for item in nutrients if item.get('nutrientName') == 'Total lipid (fat)'), 0)
                return calories, carbs, protein, fat
    except Exception:
        return None, None, None, None
    return None, None, None, None

def get_user_filename(user_email):
    """Generate a safe filename for user's meal log based on email."""
    # Create a hash of the email for privacy and filename safety
    email_hash = hashlib.md5(user_email.encode()).hexdigest()[:12]
    return f"meal_log_{email_hash}.json"

def get_user_goal_filename(user_email):
    """Generate a safe filename for user's daily goal based on email."""
    email_hash = hashlib.md5(user_email.encode()).hexdigest()[:12]
    return f"daily_goal_{email_hash}.json"

def save_meal_log(meal_log, user_email):
    """Save meal log to a JSON file for persistence for specific user."""
    filename = get_user_filename(user_email)
    try:
        # Create user_data directory if it doesn't exist
        os.makedirs("user_data", exist_ok=True)
        filepath = os.path.join("user_data", filename)
        
        with open(filepath, "w") as f:
            # Convert datetime to string for JSON serialization
            serializable_log = []
            for meal in meal_log:
                meal_copy = meal.copy()
                if isinstance(meal_copy['timestamp'], datetime):
                    meal_copy['timestamp'] = meal_copy['timestamp'].isoformat()
                serializable_log.append(meal_copy)
            json.dump(serializable_log, f)
    except Exception as e:
        st.error(f"Failed to save meal log: {e}")

def load_meal_log(user_email):
    """Load meal log from a JSON file for specific user."""
    filename = get_user_filename(user_email)
    filepath = os.path.join("user_data", filename)
    
    try:
        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                data = json.load(f)
                # Convert timestamp strings back to datetime
                for meal in data:
                    if isinstance(meal['timestamp'], str):
                        try:
                            meal['timestamp'] = datetime.fromisoformat(meal['timestamp'])
                        except ValueError:
                            # Fallback for different datetime formats
                            meal['timestamp'] = pd.to_datetime(meal['timestamp'])
                return data
        return []
    except Exception as e:
        st.error(f"Failed to load meal log: {e}")
        return []

def save_daily_goal(daily_goal, user_email):
    """Save daily goal for specific user."""
    filename = get_user_goal_filename(user_email)
    try:
        os.makedirs("user_data", exist_ok=True)
        filepath = os.path.join("user_data", filename)
        
        with open(filepath, "w") as f:
            json.dump({"daily_goal": daily_goal}, f)
    except Exception as e:
        st.error(f"Failed to save daily goal: {e}")

def load_daily_goal(user_email):
    """Load daily goal for specific user."""
    filename = get_user_goal_filename(user_email)
    filepath = os.path.join("user_data", filename)
    
    try:
        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                data = json.load(f)
                return data.get("daily_goal", 2000)
        return 2000  # default goal
    except Exception as e:
        st.error(f"Failed to load daily goal: {e}")
        return 2000

def generate_pdf_report(meal_log, daily_goal, user_email):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=14)
    pdf.cell(0, 10, "Diet Tracker Daily Report", ln=True, align="C")
    
    pdf.set_font("Arial", size=12)
    pdf.ln(5)
    pdf.cell(0, 10, f"User: {user_email}", ln=True)
    pdf.ln(5)
    
    total_calories = sum(item['calories'] for item in meal_log)
    pdf.cell(0, 10, f"Daily Calorie Goal: {daily_goal} kcal", ln=True)
    pdf.cell(0, 10, f"Calories Consumed: {total_calories:.2f} kcal", ln=True)
    pdf.cell(0, 10, f"Remaining Calories: {max(daily_goal - total_calories, 0):.2f} kcal", ln=True)
    pdf.ln(10)

    pdf.cell(0, 10, "Logged Meals:", ln=True)
    pdf.set_font("Arial", size=10)
    for meal in meal_log:
        timestamp = meal['timestamp']
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        meal_text = f"{timestamp.strftime('%Y-%m-%d %H:%M:%S')} - {meal['meal_time']} - {meal['food']} - {meal['calories']} kcal"
        # Ensure text is encoded properly to handle special characters
        try:
            pdf.cell(0, 8, meal_text, ln=True)
        except UnicodeEncodeError:
            # Fallback for non-Latin characters
            pdf.cell(0, 8, meal_text.encode('latin-1', 'replace').decode('latin-1'), ln=True)

    pdf_output = BytesIO()
    pdf_output.write(pdf.output(dest='S').encode('latin-1'))
    pdf_output.seek(0)
    return pdf_output

def get_current_user():
    """Get current user email from session state (history.py style)."""
    user = st.session_state.get('current_user')
    if not user or not user.get('email'):
        st.error("User email not found. Please log in again.")
        st.stop()
    return user['email']

def initialize_user_session(user_email):
    """Initialize session state for user-specific data."""
    user_session_key = f"daily_goal_{user_email}"
    meal_log_key = f"meal_log_{user_email}"
    
    if user_session_key not in st.session_state:
        st.session_state[user_session_key] = load_daily_goal(user_email)
    
    if meal_log_key not in st.session_state:
        st.session_state[meal_log_key] = load_meal_log(user_email)

def app():
    # Get current user
    current_user = get_current_user()
    
    # Initialize user-specific session data
    initialize_user_session(current_user)
    
    # Load datasets
    pred_food, daily_nutrition, indian_food, indian_food1, full_nutrition, indian_processed = load_datasets()
    food_df = merge_datasets(pred_food, daily_nutrition, indian_food, indian_food1, full_nutrition, indian_processed)

    # User-specific session keys
    user_goal_key = f"daily_goal_{current_user}"
    user_meal_log_key = f"meal_log_{current_user}"

    st.markdown(st_style, unsafe_allow_html=True)
    st.markdown(head, unsafe_allow_html=True)

    st.title("🥗 Diet Tracker for Diabetes")
    
    # Display current user info
    st.sidebar.markdown(f"**👤 Logged in as:** {current_user}")
    st.sidebar.markdown("---")
    
    st.sidebar.subheader("🔧 Settings")
    new_daily_goal = st.sidebar.number_input(
        "Set Daily Calorie Goal", 
        min_value=800, 
        max_value=4000, 
        value=st.session_state[user_goal_key], 
        step=50
    )
    
    # Save goal if it changed
    if new_daily_goal != st.session_state[user_goal_key]:
        st.session_state[user_goal_key] = new_daily_goal
        save_daily_goal(new_daily_goal, current_user)

    st.subheader("🍱 Add Your Meal")

    serving_sizes = {
        "Custom (grams)": None,
        "1 bowl": 200,
        "1 cup": 240,
        "1 glass": 250,
        "1 spoon": 15,
        "1 piece": 50,
        "1 slice": 30,
    }

    typed_food = st.text_input("Type to search food").strip().lower()

    if typed_food:
        matched_foods = food_df[food_df['food'].str.contains(typed_food, na=False)]
        matched_list = matched_foods['food'].tolist()
        if matched_list:
            # Add "None" option to allow API usage
            options = ["None"] + matched_list
            selected_food_option = st.selectbox("Select a matching food", options)
            if selected_food_option == "None":
                selected_food = None
            else:
                selected_food = selected_food_option
        else:
            selected_food = None
    else:
        matched_list = []
        selected_food = None

    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        selected_serving = st.selectbox("Select Serving Size", list(serving_sizes.keys()))
    with col2:
        if selected_serving == "Custom (grams)":
            quantity_per_piece = st.number_input("Quantity per piece (in grams)", min_value=1, max_value=1000, step=1, value=100)
        else:
            quantity_per_piece = serving_sizes[selected_serving]
            st.write(f"Equivalent to {quantity_per_piece} grams per piece")
    with col3:
        num_pieces = st.number_input("Number of Pieces", min_value=1, max_value=20, step=1, value=1)

    total_quantity = quantity_per_piece * num_pieces

    meal_time = st.selectbox("Meal Time", ["Breakfast", "Lunch", "Dinner", "Snack"])

    # Add option to set custom date for meal logging (for testing past dates)
    custom_log_date = st.date_input("Log meal for date", value=date.today(), key="log_date")

    if st.button("Log Meal"):
        if not typed_food:
            st.error("Please type a food name to log.")
        elif selected_food:
            best_match = food_df[food_df['food'] == selected_food].iloc[0]
            calories = best_match["calories"] * (total_quantity / 100)
            # Use custom_log_date for timestamp
            log_timestamp = datetime.combine(custom_log_date, datetime.min.time()).astimezone(IST)
            st.session_state[user_meal_log_key].append({
                "timestamp": log_timestamp,
                "meal_time": meal_time,
                "food": best_match["food"],
                "quantity": total_quantity,
                "calories": round(calories, 2),
                "carbs": 0,
                "protein": 0,
                "fat": 0,
                "source": "dataset"
            })
            save_meal_log(st.session_state[user_meal_log_key], current_user)
            st.success(f"Added {num_pieces} piece(s) ({total_quantity}g) of {best_match['food']} with {calories:.2f} kcal for {custom_log_date}.")
        else:
            cal, carbs, protein, fat = fetch_nutritional_info(typed_food)
            if cal and carbs is not None:
                total_calories = cal * (total_quantity / 100)
                # Use custom_log_date for timestamp
                log_timestamp = datetime.combine(custom_log_date, datetime.min.time()).astimezone(IST)
                st.session_state[user_meal_log_key].append({
                    "timestamp": log_timestamp,
                    "meal_time": meal_time,
                    "food": typed_food,
                    "quantity": total_quantity,
                    "calories": round(total_calories, 2),
                    "carbs": round(carbs * (total_quantity / 100), 2),
                    "protein": round(protein * (total_quantity / 100), 2),
                    "fat": round(fat * (total_quantity / 100), 2),
                    "source": "API"
                })
                save_meal_log(st.session_state[user_meal_log_key], current_user)
                st.success(f"Added {num_pieces} piece(s) ({total_quantity}g) of {typed_food} = {total_calories:.2f} kcal for {custom_log_date}.")
            else:
                st.warning("Food not found in database or API. Please enter nutrition manually.")
                calories_input = st.number_input("Calories per 100g", min_value=0.0, key="manual_cal")
                carbs_input = st.number_input("Carbohydrates per 100g", min_value=0.0, key="manual_carb")
                protein_input = st.number_input("Protein per 100g", min_value=0.0, key="manual_protein")
                fat_input = st.number_input("Fat per 100g", min_value=0.0, key="manual_fat")
                if calories_input > 0:
                    # Use custom_log_date for timestamp
                    log_timestamp = datetime.combine(custom_log_date, datetime.min.time()).astimezone(IST)
                    st.session_state[user_meal_log_key].append({
                        "timestamp": log_timestamp,
                        "meal_time": meal_time,
                        "food": typed_food,
                        "quantity": total_quantity,
                        "calories": round(calories_input * (total_quantity / 100), 2),
                        "carbs": round(carbs_input * (total_quantity / 100), 2),
                        "protein": round(protein_input * (total_quantity / 100), 2),
                        "fat": round(fat_input * (total_quantity / 100), 2),
                        "source": "manual"
                    })
                    save_meal_log(st.session_state[user_meal_log_key], current_user)
                    st.success(f"Added {num_pieces} piece(s) ({total_quantity}g) of {typed_food} manually for {custom_log_date}.")
                else:
                    st.info("Enter calories to log manually.")

    if st.button("Clear All Logged Meals"):
        st.session_state[user_meal_log_key] = []
        save_meal_log(st.session_state[user_meal_log_key], current_user)
        st.success("All logged meals cleared.")

    # Debug option to view raw meal log
    if st.checkbox("Show Raw Meal Log for Debugging"):
        st.write("Raw Meal Log:", st.session_state[user_meal_log_key])

    st.markdown("### 📅 Calendar View")
    selected_date = st.date_input("Select a date to view logged meals", value=date.today())

    if st.session_state[user_meal_log_key]:
        df = pd.DataFrame(st.session_state[user_meal_log_key])
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        
        # Handle timezone conversion properly
        if not df.empty:
            if df['timestamp'].dt.tz is None:
                # If no timezone, assume it's already in IST
                df['timestamp'] = df['timestamp'].dt.tz_localize(IST, ambiguous='raise', nonexistent='raise')
            else:
                # Convert to IST
                df['timestamp'] = df['timestamp'].dt.tz_convert(IST)
        
        # Filter meals for the selected date
        df_selected_date = df[df['timestamp'].dt.date == selected_date]

        if df_selected_date.empty:
            st.info(f"No meals logged for {selected_date.strftime('%Y-%m-%d')}.")
        else:
            st.subheader(f"Meals for {selected_date.strftime('%Y-%m-%d')}")
            # Display table with "Clear This" button for each entry
            for i, row in df_selected_date.sort_values("timestamp", ascending=False).iterrows():
                cols = st.columns([2, 2, 2, 2, 1])
                with cols[0]:
                    st.write(row["timestamp"].strftime("%Y-%m-%d %H:%M:%S"))
                with cols[1]:
                    st.write(row["meal_time"])
                with cols[2]:
                    st.write(row["food"])
                with cols[3]:
                    st.write(f"{row['quantity']}g, {row['calories']} kcal")
                with cols[4]:
                    if st.button("Clear This", key=f"calendar_clear_{i}_{selected_date}"):
                        st.session_state[user_meal_log_key] = [meal for j, meal in enumerate(st.session_state[user_meal_log_key]) if j != i]
                        save_meal_log(st.session_state[user_meal_log_key], current_user)
                        st.success(f"Removed {row['food']} from log.")
                        st.rerun()
    else:
        st.info("No meals logged yet.")

    st.markdown("### 📊 Daily Summary")
    if st.session_state[user_meal_log_key]:
        df = pd.DataFrame(st.session_state[user_meal_log_key])
        
        # Convert timestamp to datetime with proper IST handling
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        
        # Handle timezone conversion properly
        if not df.empty:
            if df['timestamp'].dt.tz is None:
                # If no timezone, assume it's already in IST
                df['timestamp'] = df['timestamp'].dt.tz_localize(IST, errors='coerce')
            else:
                # Convert to IST
                df['timestamp'] = df['timestamp'].dt.tz_convert(IST)
        
        # Get today's date in IST
        today_ist = datetime.now(IST).date()
        df_today = df[df['timestamp'].dt.date == today_ist]

        if df_today.empty:
            st.info("No meals logged for today.")
        else:
            st.subheader("Today's Logged Meals")
            # Display table with "Clear This" button for each entry
            for i, row in df_today.sort_values("timestamp", ascending=False).iterrows():
                cols = st.columns([2, 2, 2, 2, 1])
                with cols[0]:
                    st.write(row["timestamp"].strftime("%Y-%m-%d %H:%M:%S"))
                with cols[1]:
                    st.write(row["meal_time"])
                with cols[2]:
                    st.write(row["food"])
                with cols[3]:
                    st.write(f"{row['quantity']}g, {row['calories']} kcal")
                with cols[4]:
                    if st.button("Clear This", key=f"clear_{i}"):
                        st.session_state[user_meal_log_key] = [meal for j, meal in enumerate(st.session_state[user_meal_log_key]) if j != i]
                        save_meal_log(st.session_state[user_meal_log_key], current_user)
                        st.success(f"Removed {row['food']} from log.")
                        st.rerun()

            total_calories = df_today["calories"].sum()
            total_carbs = df_today["carbs"].sum() if "carbs" in df_today.columns else 0
            total_protein = df_today["protein"].sum() if "protein" in df_today.columns else 0
            total_fat = df_today["fat"].sum() if "fat" in df_today.columns else 0

            # Enhanced calorie goal display with color-coded progress
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.markdown(
                    f"<h3 style='color: {'green' if total_calories <= st.session_state[user_goal_key] else 'red'};'>Calories Consumed: {total_calories:.2f} kcal</h3>", 
                    unsafe_allow_html=True
                )
                progress = min(total_calories / st.session_state[user_goal_key], 1.0)
                st.progress(progress)
            with col2:
                st.metric("Daily Calorie Goal", f"{st.session_state[user_goal_key]} kcal")
            with col3:
                st.metric("Remaining Calories", f"{max(st.session_state[user_goal_key] - total_calories, 0):.2f} kcal")

            # Macronutrient Pie Chart
            nutrients = {
                "Carbohydrates": total_carbs,
                "Proteins": total_protein,
                "Fats": total_fat,
            }
            nutrients = {k: v for k, v in nutrients.items() if v and not pd.isna(v)}

            if nutrients:
                fig, ax = plt.subplots()
                ax.pie(
                    list(nutrients.values()),
                    labels=list(nutrients.keys()),
                    autopct="%1.1f%%",
                    startangle=90,
                    colors=['#66b3ff', '#99ff99', '#ffcc99']
                )
                ax.axis('equal')
                st.pyplot(fig)

            st.markdown("#### Calories Consumed per Meal Time")
            calories_mealtime = df_today.groupby("meal_time")["calories"].sum().reindex(["Breakfast", "Lunch", "Dinner", "Snack"]).fillna(0)
            fig2, ax2 = plt.subplots()
            ax2.bar(calories_mealtime.index, calories_mealtime.values, color='#4a90e2')
            ax2.set_ylabel("Calories (kcal)")
            ax2.set_xlabel("Meal Time")
            ax2.set_ylim(0, max(calories_mealtime.values.max() * 1.2, st.session_state[user_goal_key] * 0.3))
            st.pyplot(fig2)

            st.markdown("#### Weekly Calories Consumed Trend (Last 7 Days)")
            today = datetime.now(IST).date()
            past_week = [today - timedelta(days=i) for i in range(6, -1, -1)]  # 7 days ascending

            # Simplified date handling for weekly trend
            df['date_only'] = df['timestamp'].dt.date

            # Group by date_only and sum calories
            weekly_calories = df.groupby('date_only')['calories'].sum()
            # Reindex to ensure every day is present (missing days will be zero)
            weekly_calories = weekly_calories.reindex(past_week, fill_value=0)

            fig3, ax3 = plt.subplots()
            ax3.plot(past_week, weekly_calories.values, marker='o', linestyle='-', color='#ff7f0e')
            ax3.set_title("Calories Consumed Over Past 7 Days")
            ax3.set_ylabel("Calories (kcal)")
            ax3.set_xlabel("Date")
            ax3.set_xticks(past_week)
            ax3.set_xticklabels([d.strftime("%a %d") for d in past_week], rotation=45)
            ax3.axhline(st.session_state[user_goal_key], color='green', linestyle='--', label='Daily Goal')
            ax3.legend()
            st.pyplot(fig3)

            # Button to generate PDF report
            if st.button("Download Daily Report PDF"):
                pdf_bytes = generate_pdf_report(df_today.to_dict('records'), st.session_state[user_goal_key], current_user)
                st.download_button(
                    label="Download PDF",
                    data=pdf_bytes,
                    file_name=f"diet_report_{current_user.replace('@', '_')}_{date.today()}.pdf",
                    mime="application/pdf"
                )
    else:
        st.info("No meals logged yet today.")

if __name__ == "__main__":
    app()
