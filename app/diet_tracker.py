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
import google.generativeai as genai

# Timezone import for IST
try:
    from zoneinfo import ZoneInfo  # Python 3.9+
    IST = ZoneInfo("Asia/Kolkata")
except ImportError:
    from pytz import timezone
    IST = timezone("Asia/Kolkata")

# Configure Gemini API (add your API key here)
GEMINI_API_KEY = "your_gemini_api_key_here"  # Replace with your actual API key
genai.configure(api_key=GEMINI_API_KEY)

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

def get_micronutrient_analysis(food_name, quantity):
    """Get detailed micronutrient analysis using AI"""
    try:
        genai.configure(api_key=st.secrets["gemini"]["api_key"])
        model = genai.GenerativeModel("gemini-2.0-flash")
        prompt = f"""
        Analyze the micronutrient content of {quantity}g of {food_name}. Provide detailed nutritional information including:
        1. Sugar content (natural and added sugars in grams)
        2. Fiber content (grams)
        3. Sodium content (mg)
        4. Key vitamins (A, C, D, B12, folate) with amounts
        5. Key minerals (Iron, Calcium, Magnesium, Potassium) with amounts
        6. Glycemic index estimate
        7. Diabetes impact assessment (low/medium/high risk)
        
        Format the response as JSON with these exact keys:
        {{
            "sugar_content": float,
            "fiber": float,
            "sodium": float,
            "vitamin_a": float,
            "vitamin_c": float,
            "vitamin_d": float,
            "vitamin_b12": float,
            "folate": float,
            "iron": float,
            "calcium": float,
            "magnesium": float,
            "potassium": float,
            "glycemic_index": int,
            "diabetes_risk": "low/medium/high"
        }}
        
        Provide realistic nutritional values based on standard food databases.
        """
        
        response = model.generate_content(prompt)
        
        # Parse the JSON response
        response_text = response.text.strip()
        if response_text.startswith('```json'):
            response_text = response_text[7:-3]
        elif response_text.startswith('```'):
            response_text = response_text[3:-3]
            
        return json.loads(response_text)
    except Exception as e:
        # Fallback values if AI fails
        return {
            "sugar_content": 0.0,
            "fiber": 0.0,
            "sodium": 0.0,
            "vitamin_a": 0.0,
            "vitamin_c": 0.0,
            "vitamin_d": 0.0,
            "vitamin_b12": 0.0,
            "folate": 0.0,
            "iron": 0.0,
            "calcium": 0.0,
            "magnesium": 0.0,
            "potassium": 0.0,
            "glycemic_index": 50,
            "diabetes_risk": "medium"
        }

def get_diabetes_recommendations(daily_sugar, weekly_avg_sugar, risk_foods):
    """Get personalized diabetes prevention recommendations"""
    try:
        model = genai.GenerativeModel('gemini-pro')
        prompt = f"""
        Based on the following health data, provide personalized diabetes prevention recommendations:
        - Today's sugar intake: {daily_sugar}g
        - Weekly average sugar: {weekly_avg_sugar}g
        - High-risk foods consumed: {', '.join(risk_foods) if risk_foods else 'None'}
        
        Provide 5-7 specific, actionable recommendations focusing on:
        1. Dietary modifications
        2. Portion control strategies
        3. Food substitutions
        4. Meal timing
        5. Physical activity suggestions
        
        Make recommendations practical and culturally appropriate for Indian dietary habits.
        Keep each recommendation under 50 words and make them encouraging, not alarming.
        """
        
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return "Unable to generate personalized recommendations at this time. Please consult with a healthcare professional for diabetes prevention advice."

def get_user_filename(user_email):
    """Generate a safe filename for user's meal log based on email."""
    email_hash = hashlib.md5(user_email.encode()).hexdigest()[:12]
    return f"meal_log_{email_hash}.json"

def get_user_goal_filename(user_email):
    """Generate a safe filename for user's daily goal based on email."""
    email_hash = hashlib.md5(user_email.encode()).hexdigest()[:12]
    return f"daily_goal_{email_hash}.json"

def get_user_sugar_filename(user_email):
    """Generate a safe filename for user's sugar log based on email."""
    email_hash = hashlib.md5(user_email.encode()).hexdigest()[:12]
    return f"sugar_log_{email_hash}.json"

def save_meal_log(meal_log, user_email):
    """Save meal log to a JSON file for persistence for specific user."""
    filename = get_user_filename(user_email)
    try:
        os.makedirs("user_data", exist_ok=True)
        filepath = os.path.join("user_data", filename)
        
        with open(filepath, "w") as f:
            serializable_log = []
            for meal in meal_log:
                meal_copy = meal.copy()
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
                for meal in data:
                    meal['timestamp'] = datetime.fromisoformat(meal['timestamp'])
                return data
        return []
    except Exception as e:
        st.error(f"Failed to load meal log: {e}")
        return []

def save_sugar_log(sugar_log, user_email):
    """Save sugar log for specific user."""
    filename = get_user_sugar_filename(user_email)
    try:
        os.makedirs("user_data", exist_ok=True)
        filepath = os.path.join("user_data", filename)
        
        with open(filepath, "w") as f:
            serializable_log = []
            for entry in sugar_log:
                entry_copy = entry.copy()
                entry_copy['date'] = entry_copy['date'].isoformat()
                serializable_log.append(entry_copy)
            json.dump(serializable_log, f)
    except Exception as e:
        st.error(f"Failed to save sugar log: {e}")

def load_sugar_log(user_email):
    """Load sugar log for specific user."""
    filename = get_user_sugar_filename(user_email)
    filepath = os.path.join("user_data", filename)
    
    try:
        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                data = json.load(f)
                for entry in data:
                    entry['date'] = datetime.fromisoformat(entry['date']).date()
                return data
        return []
    except Exception as e:
        st.error(f"Failed to load sugar log: {e}")
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
        return 2000
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
        meal_text = f"{meal['timestamp'].strftime('%Y-%m-%d %H:%M:%S')} - {meal['meal_time']} - {meal['food']} - {meal['calories']} kcal"
        try:
            pdf.cell(0, 8, meal_text, ln=True)
        except UnicodeEncodeError:
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
    sugar_log_key = f"sugar_log_{user_email}"
    
    if user_session_key not in st.session_state:
        st.session_state[user_session_key] = load_daily_goal(user_email)
    
    if meal_log_key not in st.session_state:
        st.session_state[meal_log_key] = load_meal_log(user_email)
    
    if sugar_log_key not in st.session_state:
        st.session_state[sugar_log_key] = load_sugar_log(user_email)

def nutrition_analysis_tab(current_user, food_df):
    """Tab for micronutrient analysis and diabetes prevention"""
    st.subheader("🔬 Nutritional Analysis & Diabetes Prevention")
    
    # User-specific session keys
    user_meal_log_key = f"meal_log_{current_user}"
    user_sugar_log_key = f"sugar_log_{current_user}"
    
    # Manual sugar level input
    st.markdown("### 📊 Daily Sugar Level Tracking")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        sugar_level = st.number_input("Enter your blood sugar level (mg/dL)", min_value=50, max_value=500, step=1, value=100)
    with col2:
        measurement_time = st.selectbox("Measurement Time", ["Fasting", "Post-meal (1hr)", "Post-meal (2hr)", "Random"])
    
    if st.button("Log Sugar Level"):
        today = date.today()
        # Check if entry for today already exists
        existing_entry = next((entry for entry in st.session_state[user_sugar_log_key] 
                              if entry['date'] == today and entry['time'] == measurement_time), None)
        
        if existing_entry:
            existing_entry['level'] = sugar_level
        else:
            st.session_state[user_sugar_log_key].append({
                'date': today,
                'time': measurement_time,
                'level': sugar_level
            })
        
        save_sugar_log(st.session_state[user_sugar_log_key], current_user)
        st.success(f"Sugar level {sugar_level} mg/dL logged for {measurement_time}")
    
    # Display sugar trends
    if st.session_state[user_sugar_log_key]:
        st.markdown("### 📈 Sugar Level Trends")
        
        df_sugar = pd.DataFrame(st.session_state[user_sugar_log_key])
        df_sugar['date'] = pd.to_datetime(df_sugar['date'])
        
        # Daily trend (last 7 days)
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Daily Sugar Levels (Last 7 Days)")
            recent_data = df_sugar[df_sugar['date'] >= pd.Timestamp.now() - pd.Timedelta(days=7)]
            if not recent_data.empty:
                fig, ax = plt.subplots(figsize=(10, 6))
                for time_type in recent_data['time'].unique():
                    time_data = recent_data[recent_data['time'] == time_type]
                    ax.plot(time_data['date'], time_data['level'], marker='o', label=time_type)
                
                ax.axhline(y=100, color='green', linestyle='--', alpha=0.7, label='Normal (100 mg/dL)')
                ax.axhline(y=140, color='orange', linestyle='--', alpha=0.7, label='Pre-diabetes (140 mg/dL)')
                ax.axhline(y=200, color='red', linestyle='--', alpha=0.7, label='Diabetes (200 mg/dL)')
                
                ax.set_xlabel('Date')
                ax.set_ylabel('Sugar Level (mg/dL)')
                ax.legend()
                ax.grid(True, alpha=0.3)
                plt.xticks(rotation=45)
                st.pyplot(fig)
            else:
                st.info("No recent sugar level data to display")
        
        with col2:
            st.markdown("#### Weekly Average Trends")
            df_sugar['week'] = df_sugar['date'].dt.to_period('W')
            weekly_avg = df_sugar.groupby('week')['level'].mean().reset_index()
            weekly_avg['week_str'] = weekly_avg['week'].astype(str)
            
            if len(weekly_avg) > 1:
                fig2, ax2 = plt.subplots(figsize=(10, 6))
                ax2.plot(range(len(weekly_avg)), weekly_avg['level'], marker='o', color='#ff7f0e')
                ax2.set_xticks(range(len(weekly_avg)))
                ax2.set_xticklabels(weekly_avg['week_str'], rotation=45)
                ax2.set_xlabel('Week')
                ax2.set_ylabel('Average Sugar Level (mg/dL)')
                ax2.grid(True, alpha=0.3)
                st.pyplot(fig2)
            else:
                st.info("Need more data for weekly trends")
    
    # Micronutrient analysis from logged meals
    if st.session_state[user_meal_log_key]:
        st.markdown("### 🥗 Today's Micronutrient Analysis")
        
        df_meals = pd.DataFrame(st.session_state[user_meal_log_key])
        df_meals['timestamp'] = pd.to_datetime(df_meals['timestamp'])
        today_meals = df_meals[df_meals['timestamp'].dt.date == date.today()]
        
        if not today_meals.empty:
            total_micronutrients = {
                'sugar_content': 0, 'fiber': 0, 'sodium': 0,
                'vitamin_a': 0, 'vitamin_c': 0, 'vitamin_d': 0,
                'vitamin_b12': 0, 'folate': 0, 'iron': 0,
                'calcium': 0, 'magnesium': 0, 'potassium': 0
            }
            
            high_risk_foods = []
            
            # Analyze each meal
            for _, meal in today_meals.iterrows():
                micronutrients = get_micronutrient_analysis(meal['food'], meal['quantity'])
                
                for key in total_micronutrients.keys():
                    total_micronutrients[key] += micronutrients.get(key, 0)
                
                if micronutrients.get('diabetes_risk') == 'high':
                    high_risk_foods.append(meal['food'])
            
            # Display micronutrient charts
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Sugar", f"{total_micronutrients['sugar_content']:.1f}g")
                st.metric("Fiber", f"{total_micronutrients['fiber']:.1f}g")
                st.metric("Sodium", f"{total_micronutrients['sodium']:.0f}mg")
            
            with col2:
                st.metric("Vitamin C", f"{total_micronutrients['vitamin_c']:.1f}mg")
                st.metric("Iron", f"{total_micronutrients['iron']:.1f}mg")
                st.metric("Calcium", f"{total_micronutrients['calcium']:.0f}mg")
            
            with col3:
                st.metric("Potassium", f"{total_micronutrients['potassium']:.0f}mg")
                st.metric("Magnesium", f"{total_micronutrients['magnesium']:.0f}mg")
                st.metric("Folate", f"{total_micronutrients['folate']:.0f}mcg")
            
            # Vitamin chart
            vitamins = {
                'Vitamin A': total_micronutrients['vitamin_a'],
                'Vitamin C': total_micronutrients['vitamin_c'],
                'Vitamin D': total_micronutrients['vitamin_d'],
                'Vitamin B12': total_micronutrients['vitamin_b12'],
                'Folate': total_micronutrients['folate']
            }
            
            fig3, ax3 = plt.subplots(figsize=(10, 6))
            bars = ax3.bar(vitamins.keys(), vitamins.values(), color=['#ff9999', '#66b3ff', '#99ff99', '#ffcc99', '#ff99cc'])
            ax3.set_ylabel('Amount')
            ax3.set_title('Daily Vitamin Intake')
            plt.xticks(rotation=45)
            st.pyplot(fig3)
            
            # Mineral chart
            minerals = {
                'Iron': total_micronutrients['iron'],
                'Calcium': total_micronutrients['calcium'],
                'Magnesium': total_micronutrients['magnesium'],
                'Potassium': total_micronutrients['potassium']
            }
            
            fig4, ax4 = plt.subplots(figsize=(10, 6))
            bars = ax4.bar(minerals.keys(), minerals.values(), color=['#ffb3ba', '#baffc9', '#bae1ff', '#ffffba'])
            ax4.set_ylabel('Amount (mg)')
            ax4.set_title('Daily Mineral Intake')
            st.pyplot(fig4)
            
        else:
            st.info("No meals logged today for micronutrient analysis")
    
    # Diabetes prevention recommendations
    st.markdown("### 💡 Personalized Diabetes Prevention Recommendations")
    
    if st.button("Get Personalized Recommendations"):
        with st.spinner("Analyzing your health data..."):
            # Calculate daily and weekly sugar averages
            daily_sugar = 0
            weekly_avg_sugar = 0
            risk_foods = []
            
            if st.session_state[user_meal_log_key]:
                df_meals = pd.DataFrame(st.session_state[user_meal_log_key])
                df_meals['timestamp'] = pd.to_datetime(df_meals['timestamp'])
                today_meals = df_meals[df_meals['timestamp'].dt.date == date.today()]
                
                for _, meal in today_meals.iterrows():
                    micronutrients = get_micronutrient_analysis(meal['food'], meal['quantity'])
                    daily_sugar += micronutrients.get('sugar_content', 0)
                    if micronutrients.get('diabetes_risk') == 'high':
                        risk_foods.append(meal['food'])
                
                # Weekly average
                week_meals = df_meals[df_meals['timestamp'] >= pd.Timestamp.now() - pd.Timedelta(days=7)]
                if not week_meals.empty:
                    total_weekly_sugar = 0
                    for _, meal in week_meals.iterrows():
                        micronutrients = get_micronutrient_analysis(meal['food'], meal['quantity'])
                        total_weekly_sugar += micronutrients.get('sugar_content', 0)
                    weekly_avg_sugar = total_weekly_sugar / 7
            
            recommendations = get_diabetes_recommendations(daily_sugar, weekly_avg_sugar, risk_foods)
            
            st.markdown("#### 🎯 Your Personalized Recommendations:")
            st.write(recommendations)
            
            # Risk assessment
            if daily_sugar > 50:
                st.warning("⚠️ High sugar intake detected today. Consider reducing sugar consumption.")
            elif daily_sugar > 25:
                st.info("ℹ️ Moderate sugar intake. Monitor your levels closely.")
            else:
                st.success("✅ Good sugar management today!")

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

    # Create tabs
    tab1, tab2 = st.tabs(["🍽️ Meal Tracking", "🔬 Nutrition Analysis"])
    
    with tab1:
        # Original meal tracking functionality
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

        if st.button("Log Meal"):
            if not typed_food:
                st.error("Please type a food name to log.")
            elif selected_food:
                best_match = food_df[food_df['food'] == selected_food].iloc[0]
                calories = best_match["calories"] * (total_quantity / 100)
                st.session_state[user_meal_log_key].append({
                    "timestamp": datetime.now(IST),
                    "meal_time": meal_time,
                    "food": best_match["food"],
                    "quantity": total_quantity,
                    "calories": round(calories, 2),
                    "source": "dataset"
                })
                save_meal_log(st.session_state[user_meal_log_key], current_user)
                st.success(f"Added {num_pieces} piece(s) ({total_quantity}g) of {best_match['food']} with {calories:.2f} kcal.")
            else:
                cal, carbs, protein, fat = fetch_nutritional_info(typed_food)
                if cal and carbs is not None:
                    total_calories = cal * (total_quantity / 100)
                    st.session_state[user_meal_log_key].append({
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
                    save_meal_log(st.session_state[user_meal_log_key], current_user)
                    st.success(f"Added {num_pieces} piece(s) ({total_quantity}g) of {typed_food} = {total_calories:.2f} kcal from API.")
                else:
                    st.warning("Food not found in database or API. Please enter nutrition manually.")
                    calories_input = st.number_input("Calories per 100g", min_value=0.0, key="manual_cal")
                    carbs_input = st.number_input("Carbohydrates per 100g", min_value=0.0, key="manual_carb")
                    protein_input = st.number_input("Protein per 100g", min_value=0.0, key="manual_protein")
                    fat_input = st.number_input("Fat per 100g", min_value=0.0, key="manual_fat")
                    if calories_input > 0:
                        st.session_state[user_meal_log_key].append({
                            "timestamp": datetime.now(IST),
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
                        st.success(f"Added {num_pieces} piece(s) ({total_quantity}g) of {typed_food} manually.")
                    else:
                        st.info("Enter calories to log manually.")

        if st.button("Clear All Logged Meals"):
            st.session_state[user_meal_log_key] = []
            save_meal_log(st.session_state[user_meal_log_key], current_user)
            st.success("All logged meals cleared.")

        st.markdown("### 📅 Calendar View")
        selected_date = st.date_input("Select a date to view logged meals", value=date.today())

        if st.session_state[user_meal_log_key]:
            df = pd.DataFrame(st.session_state[user_meal_log_key])
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df_selected_date = df[df['timestamp'].dt.date == selected_date]

            if df_selected_date.empty:
                st.info(f"No meals logged for {selected_date.strftime('%Y-%m-%d')}.")
            else:
                st.subheader(f"Meals for {selected_date.strftime('%Y-%m-%d')}")
                st.dataframe(df_selected_date[["timestamp", "meal_time", "food", "quantity", "calories"]].sort_values("timestamp", ascending=False))
        else:
            st.info("No meals logged yet.")

        st.markdown("### 📊 Daily Summary")
        if st.session_state[user_meal_log_key]:
            df = pd.DataFrame(st.session_state[user_meal_log_key])
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df_today = df[df['timestamp'].dt.date == date.today()]

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
                else:
                    st.info("No macronutrient data available to plot.")

                st.markdown("#### Calories Consumed per Meal Time")
                calories_mealtime = df_today.groupby("meal_time")["calories"].sum().reindex(["Breakfast", "Lunch", "Dinner", "Snack"]).fillna(0)
                fig2, ax2 = plt.subplots()
                ax2.bar(calories_mealtime.index, calories_mealtime.values, color='#4a90e2')
                ax2.set_ylabel("Calories (kcal)")
                ax2.set_xlabel("Meal Time")
                ax2.set_ylim(0, max(calories_mealtime.values.max() * 1.2, st.session_state[user_goal_key] * 0.3))
                st.pyplot(fig2)

                st.markdown("#### Weekly Calories Consumed Trend (Last 7 Days)")
                today = date.today()
                past_week = [today - timedelta(days=i) for i in range(6, -1, -1)]  # 7 days ascending
                df['date_only'] = df['timestamp'].dt.date
                weekly_calories = df.groupby('date_only')['calories'].sum().reindex(past_week, fill_value=0)

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
    
    with tab2:
        # New nutrition analysis tab
        nutrition_analysis_tab(current_user, food_df)

if __name__ == "__main__":
    app()
