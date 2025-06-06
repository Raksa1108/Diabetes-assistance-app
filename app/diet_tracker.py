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
import hashlib
import re
from data.base import st_style, head

# Timezone import for IST
try:
    from zoneinfo import ZoneInfo  # Python 3.9+
    IST = ZoneInfo("Asia/Kolkata")
except ImportError:
    from pytz import timezone
    IST = timezone("Asia/Kolkata")

def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """Validate password strength"""
    if len(password) < 6:
        return False, "Password must be at least 6 characters long"
    if not re.search(r'[A-Za-z]', password):
        return False, "Password must contain at least one letter"
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    return True, "Password is valid"

def load_users():
    """Load users from JSON file"""
    try:
        if os.path.exists("users.json"):
            with open("users.json", "r") as f:
                return json.load(f)
        return {}
    except Exception as e:
        st.error(f"Failed to load users: {e}")
        return {}

def save_users(users):
    """Save users to JSON file"""
    try:
        with open("users.json", "w") as f:
            json.dump(users, f, indent=2)
    except Exception as e:
        st.error(f"Failed to save users: {e}")

def register_user(email, password, name):
    """Register a new user"""
    users = load_users()
    
    if email in users:
        return False, "Email already registered"
    
    if not validate_email(email):
        return False, "Invalid email format"
    
    is_valid, message = validate_password(password)
    if not is_valid:
        return False, message
    
    # Create user ID from email
    user_id = hashlib.md5(email.lower().encode()).hexdigest()[:12]
    
    users[email] = {
        "user_id": user_id,
        "name": name,
        "password_hash": hash_password(password),
        "created_at": datetime.now().isoformat(),
        "daily_goal": 2000
    }
    
    save_users(users)
    return True, "Registration successful"

def authenticate_user(email, password):
    """Authenticate user login"""
    users = load_users()
    
    if email not in users:
        return False, None, "Email not found"
    
    user_data = users[email]
    if user_data["password_hash"] != hash_password(password):
        return False, None, "Invalid password"
    
    return True, user_data, "Login successful"

def get_user_id():
    """Get current user ID"""
    return st.session_state.get('user_id')

def get_user_data():
    """Get current user data"""
    return st.session_state.get('user_data')

def authentication_page():
    """Display login/registration page"""
    st.title("🥗 Diet Tracker for Diabetes")
    st.markdown("---")
    
    # Create tabs for login and registration
    tab1, tab2 = st.tabs(["🔐 Login", "📝 Register"])
    
    with tab1:
        st.subheader("Login to Your Account")
        
        with st.form("login_form"):
            email = st.text_input("Email", placeholder="Enter your email")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            submit_login = st.form_submit_button("Login", use_container_width=True)
            
            if submit_login:
                if not email or not password:
                    st.error("Please fill in all fields")
                else:
                    success, user_data, message = authenticate_user(email, password)
                    if success:
                        st.session_state.user_id = user_data["user_id"]
                        st.session_state.user_data = user_data
                        st.session_state.user_email = email
                        st.success("Login successful!")
                        st.experimental_rerun()
                    else:
                        st.error(message)
    
    with tab2:
        st.subheader("Create New Account")
        
        with st.form("register_form"):
            reg_name = st.text_input("Full Name", placeholder="Enter your full name")
            reg_email = st.text_input("Email", placeholder="Enter your email")
            reg_password = st.text_input("Password", type="password", placeholder="Create a password")
            reg_confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm your password")
            submit_register = st.form_submit_button("Register", use_container_width=True)
            
            if submit_register:
                if not all([reg_name, reg_email, reg_password, reg_confirm_password]):
                    st.error("Please fill in all fields")
                elif reg_password != reg_confirm_password:
                    st.error("Passwords do not match")
                else:
                    success, message = register_user(reg_email, reg_password, reg_name)
                    if success:
                        st.success("Registration successful! Please login with your credentials.")
                    else:
                        st.error(message)
    
    # Password requirements info
    with st.expander("ℹ️ Password Requirements"):
        st.write("""
        - At least 6 characters long
        - Must contain at least one letter
        - Must contain at least one number
        """)

def get_user_file_path(base_filename):
    """Generate user-specific file path"""
    user_id = get_user_id()
    if user_id:
        user_dir = f"user_data/{user_id}"
        os.makedirs(user_dir, exist_ok=True)
        return os.path.join(user_dir, base_filename)
    return base_filename

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

def generate_pdf_report(meal_log, daily_goal, user_name):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=14)
    pdf.cell(0, 10, f"Diet Tracker Daily Report - {user_name}", ln=True, align="C")

    pdf.set_font("Arial", size=12)
    pdf.ln(10)
    total_calories = sum(item['calories'] for item in meal_log)
    pdf.cell(0, 10, f"Daily Calorie Goal: {daily_goal} kcal", ln=True)
    pdf.cell(0, 10, f"Calories Consumed: {total_calories:.2f} kcal", ln=True)
    pdf.cell(0, 10, f"Remaining Calories: {max(daily_goal - total_calories, 0):.2f} kcal", ln=True)
    pdf.ln(10)

    pdf.cell(0, 10, "Logged Meals:", ln=True)
    pdf.set_font("Arial", size=10)
    for meal in meal_log:
        meal_text = f"{meal['timestamp'].strftime('%Y-%m-%d %H:%M:%S')} - {meal['meal_time']} - {meal['food']} - {meal['calories']} kcal"
        try:
            pdf.cell(0, 8, meal_text, ln=True)
        except UnicodeEncodeError:
            pdf.cell(0, 8, meal_text.encode('latin-1', 'replace').decode('latin-1'), ln=True)

    pdf_output = BytesIO()
    pdf_output.write(pdf.output(dest='S').encode('latin-1'))
    pdf_output.seek(0)
    return pdf_output

def save_meal_log(meal_log):
    """Save meal log to a user-specific JSON file for persistence."""
    file_path = get_user_file_path("meal_log.json")
    try:
        with open(file_path, "w") as f:
            serializable_log = []
            for meal in meal_log:
                meal_copy = meal.copy()
                meal_copy['timestamp'] = meal_copy['timestamp'].isoformat()
                serializable_log.append(meal_copy)
            json.dump(serializable_log, f)
    except Exception as e:
        st.error(f"Failed to save meal log: {e}")

def load_meal_log():
    """Load meal log from a user-specific JSON file."""
    file_path = get_user_file_path("meal_log.json")
    try:
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                data = json.load(f)
                for meal in data:
                    meal['timestamp'] = datetime.fromisoformat(meal['timestamp'])
                return data
        return []
    except Exception as e:
        st.error(f"Failed to load meal log: {e}")
        return []

def save_user_settings(daily_goal):
    """Save user settings and update in users.json"""
    users = load_users()
    email = st.session_state.get('user_email')
    if email and email in users:
        users[email]['daily_goal'] = daily_goal
        save_users(users)
        # Update session state
        st.session_state.user_data['daily_goal'] = daily_goal

def logout():
    """Clear user session and logout"""
    for key in ['user_id', 'user_data', 'user_email', 'meal_log', 'daily_goal']:
        if key in st.session_state:
            del st.session_state[key]
    st.experimental_rerun()

def main_app():
    """Main application after authentication"""
    # Load datasets
    pred_food, daily_nutrition, indian_food, indian_food1, full_nutrition, indian_processed = load_datasets()
    food_df = merge_datasets(pred_food, daily_nutrition, indian_food, indian_food1, full_nutrition, indian_processed)

    user_data = get_user_data()
    user_name = user_data.get('name', 'User')
    
    # Initialize session state
    if 'daily_goal' not in st.session_state:
        st.session_state.daily_goal = user_data.get('daily_goal', 2000)
    if 'meal_log' not in st.session_state:
        st.session_state.meal_log = load_meal_log()

    st.markdown(st_style, unsafe_allow_html=True)
    st.markdown(head, unsafe_allow_html=True)

    # Header with user info and logout
    col1, col2, col3 = st.columns([4, 1, 1])
    with col1:
        st.title(f"🥗 Diet Tracker - Welcome {user_name}!")
    with col2:
        st.write(f"📧 {st.session_state.get('user_email', '')}")
    with col3:
        if st.button("🚪 Logout", use_container_width=True):
            logout()

    # Sidebar settings
    st.sidebar.subheader("🔧 Settings")
    new_daily_goal = st.sidebar.number_input(
        "Set Daily Calorie Goal", min_value=800, max_value=4000, 
        value=st.session_state.daily_goal, step=50
    )
    
    # Save settings when changed
    if new_daily_goal != st.session_state.daily_goal:
        st.session_state.daily_goal = new_daily_goal
        save_user_settings(new_daily_goal)

    # Display user profile in sidebar
    with st.sidebar.expander("👤 Profile Info"):
        st.write(f"**Name:** {user_name}")
        st.write(f"**Email:** {st.session_state.get('user_email', '')}")
        st.write(f"**Member since:** {user_data.get('created_at', '')[:10]}")
        st.write(f"**Daily Goal:** {st.session_state.daily_goal} kcal")

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
            selected_food = st.selectbox("Select a matching food", matched_list)
        else:
            selected_food = None
            st.warning("No matches found in datasets.")
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

    if st.button("Log Meal", use_container_width=True):
        if not typed_food:
            st.error("Please type a food name to log.")
        elif selected_food:
            best_match = food_df[food_df['food'] == selected_food].iloc[0]
            calories = best_match["calories"] * (total_quantity / 100)
            st.session_state.meal_log.append({
                "timestamp": datetime.now(IST),
                "meal_time": meal_time,
                "food": best_match["food"],
                "quantity": total_quantity,
                "calories": round(calories, 2),
                "source": "dataset"
            })
            save_meal_log(st.session_state.meal_log)
            st.success(f"✅ Added {num_pieces} piece(s) ({total_quantity}g) of {best_match['food']} with {calories:.2f} kcal.")
        else:
            cal, carbs, protein, fat = fetch_nutritional_info(typed_food)
            if cal and carbs is not None:
                total_calories = cal * (total_quantity / 100)
                st.session_state.meal_log.append({
                    "timestamp": datetime.now(IST),
                    "meal_time": meal_time,
                    "food": typed_food,
                    "quantity": total_quantity,
                    "calories": round(total_calories, 2),
                    "carbs": round(carbs * (total_quantity / 100), 2),
                    "protein": round(protein * (total_quantity / 100), 2),
                    "fat": round(fat * (total_quantity / 100), 2),
                    "source": "API"
                })
                save_meal_log(st.session_state.meal_log)
                st.success(f"✅ Added {num_pieces} piece(s) ({total_quantity}g) of {typed_food} = {total_calories:.2f} kcal from API.")

    if st.button("🗑️ Clear All Logged Meals"):
        st.session_state.meal_log = []
        save_meal_log(st.session_state.meal_log)
        st.success("All logged meals cleared.")

    # Calendar View
    st.markdown("### 📅 Calendar View")
    selected_date = st.date_input("Select a date to view logged meals", value=date.today())

    if st.session_state.meal_log:
        df = pd.DataFrame(st.session_state.meal_log)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df_selected_date = df[df['timestamp'].dt.date == selected_date]

        if df_selected_date.empty:
            st.info(f"No meals logged for {selected_date.strftime('%Y-%m-%d')}.")
        else:
            st.subheader(f"Meals for {selected_date.strftime('%Y-%m-%d')}")
            st.dataframe(df_selected_date[["timestamp", "meal_time", "food", "quantity", "calories"]].sort_values("timestamp", ascending=False))
    else:
        st.info("No meals logged yet.")

    # Daily Summary
    st.markdown("### 📊 Daily Summary")
    if st.session_state.meal_log:
        df = pd.DataFrame(st.session_state.meal_log)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df_today = df[df['timestamp'].dt.date == date.today()]

        if df_today.empty:
            st.info("No meals logged for today.")
        else:
            st.subheader("Today's Logged Meals")
            for i, row in df_today.sort_values("timestamp", ascending=False).iterrows():
                cols = st.columns([2, 2, 2, 2, 1])
                with cols[0]:
                    st.write(row["timestamp"].strftime("%H:%M:%S"))
                with cols[1]:
                    st.write(row["meal_time"])
                with cols[2]:
                    st.write(row["food"])
                with cols[3]:
                    st.write(f"{row['quantity']}g, {row['calories']} kcal")
                with cols[4]:
                    if st.button("❌", key=f"clear_{i}", help="Remove this meal"):
                        st.session_state.meal_log = [meal for j, meal in enumerate(st.session_state.meal_log) if j != i]
                        save_meal_log(st.session_state.meal_log)
                        st.success(f"Removed {row['food']} from log.")
                        st.experimental_rerun()

            total_calories = df_today["calories"].sum()
            total_carbs = df_today["carbs"].sum() if "carbs" in df_today.columns else 0
            total_protein = df_today["protein"].sum() if "protein" in df_today.columns else 0
            total_fat = df_today["fat"].sum() if "fat" in df_today.columns else 0

            # Enhanced calorie display
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.markdown(
                    f"<h3 style='color: {'green' if total_calories <= st.session_state.daily_goal else 'red'};'>Calories Consumed: {total_calories:.2f} kcal</h3>", 
                    unsafe_allow_html=True
                )
                progress = min(total_calories / st.session_state.daily_goal, 1.0)
                st.progress(progress)
            with col2:
                st.metric("Daily Goal", f"{st.session_state.daily_goal} kcal")
            with col3:
                remaining = max(st.session_state.daily_goal - total_calories, 0)
                st.metric("Remaining", f"{remaining:.0f} kcal")

            # Macronutrient visualization
            nutrients = {
                "Carbohydrates": total_carbs,
                "Proteins": total_protein,
                "Fats": total_fat,
            }
            nutrients = {k: v for k, v in nutrients.items() if v and not pd.isna(v)}

            if nutrients:
                fig, ax = plt.subplots(figsize=(8, 6))
                ax.pie(
                    list(nutrients.values()),
                    labels=list(nutrients.keys()),
                    autopct="%1.1f%%",
                    startangle=90,
                    colors=['#66b3ff', '#99ff99', '#ffcc99']
                )
                ax.axis('equal')
                ax.set_title("Macronutrient Distribution")
                st.pyplot(fig)

            # Download PDF report
            if st.button("📄 Download Daily Report PDF", use_container_width=True):
                pdf_bytes = generate_pdf_report(df_today.to_dict('records'), st.session_state.daily_goal, user_name)
                st.download_button(
                    label="📥 Download PDF Report",
                    data=pdf_bytes,
                    file_name=f"diet_report_{user_name}_{date.today()}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
    else:
        st.info("No meals logged yet today.")

def app():
    """Main application entry point"""
    # Check if user is authenticated
    if 'user_id' not in st.session_state or st.session_state.user_id is None:
        authentication_page()
    else:
        main_app()

if __name__ == "__main__":
    app()
