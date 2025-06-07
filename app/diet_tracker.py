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
import shutil
import time
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
    """Load datasets with comprehensive error handling."""
    datasets = {}
    dataset_files = {
        'pred_food': "dataset/pred_food.csv",
        'daily_nutrition': "dataset/daily_food_nutrition_dataset.csv", 
        'indian_food': "dataset/indian_food.csv",
        'indian_food1': "dataset/Indian_Food_DF.csv",
        'full_nutrition': "dataset/Nutrition_Dataset.csv",
        'indian_processed': "dataset/Indian_Food_Nutrition_Processed.csv"
    }
    
    for name, filepath in dataset_files.items():
        try:
            if os.path.exists(filepath):
                datasets[name] = pd.read_csv(filepath, encoding="ISO-8859-1")
                st.sidebar.success(f"✅ Loaded {name}")
            else:
                st.sidebar.warning(f"⚠️ File not found: {filepath}")
                datasets[name] = None
        except pd.errors.EmptyDataError:
            st.sidebar.error(f"❌ Empty file: {filepath}")
            datasets[name] = None
        except pd.errors.ParserError as e:
            st.sidebar.error(f"❌ Parse error in {filepath}: {str(e)}")
            datasets[name] = None
        except UnicodeDecodeError:
            try:
                datasets[name] = pd.read_csv(filepath, encoding="utf-8")
                st.sidebar.info(f"ℹ️ Used UTF-8 encoding for {name}")
            except Exception as e:
                st.sidebar.error(f"❌ Encoding error in {filepath}: {str(e)}")
                datasets[name] = None
        except Exception as e:
            st.sidebar.error(f"❌ Unexpected error loading {filepath}: {str(e)}")
            datasets[name] = None
    
    return (datasets.get('pred_food'), datasets.get('daily_nutrition'), 
            datasets.get('indian_food'), datasets.get('indian_food1'),
            datasets.get('full_nutrition'), datasets.get('indian_processed'))

def merge_datasets(*datasets):
    """Merge datasets with error handling."""
    try:
        dfs = []
        for i, df in enumerate(datasets[:-1]):  # first five datasets
            if df is not None and not df.empty:
                try:
                    df_copy = df.copy()
                    df_copy.columns = [col.lower().strip() for col in df_copy.columns]
                    if 'food' in df_copy.columns and 'calories' in df_copy.columns:
                        # Filter out invalid data
                        df_filtered = df_copy[['food', 'calories']].copy()
                        df_filtered = df_filtered.dropna()
                        df_filtered = df_filtered[df_filtered['calories'] > 0]
                        if not df_filtered.empty:
                            dfs.append(df_filtered)
                except Exception as e:
                    st.sidebar.warning(f"⚠️ Error processing dataset {i+1}: {str(e)}")
                    continue

        processed = datasets[-1]
        if processed is not None and not processed.empty:
            try:
                processed_copy = processed.copy()
                processed_copy.columns = [col.lower().strip() for col in processed_copy.columns]
                if 'dish name' in processed_copy.columns and 'calories (kcal)' in processed_copy.columns:
                    processed_copy['food'] = processed_copy['dish name'].str.lower()
                    processed_copy['calories'] = processed_copy['calories (kcal)']
                    processed_filtered = processed_copy[['food', 'calories']].dropna()
                    processed_filtered = processed_filtered[processed_filtered['calories'] > 0]
                    if not processed_filtered.empty:
                        dfs.append(processed_filtered)
            except Exception as e:
                st.sidebar.warning(f"⚠️ Error processing Indian processed dataset: {str(e)}")

        if not dfs:
            st.error("❌ No valid datasets could be loaded")
            return pd.DataFrame(columns=['food', 'calories'])

        combined = pd.concat(dfs, ignore_index=True)
        combined = combined.drop_duplicates(subset='food')
        combined['food'] = combined['food'].str.lower().str.strip()
        combined = combined[combined['food'].str.len() > 0]  # Remove empty food names
        
        st.sidebar.success(f"✅ Merged {len(combined)} food items from datasets")
        return combined
        
    except Exception as e:
        st.error(f"❌ Critical error merging datasets: {str(e)}")
        return pd.DataFrame(columns=['food', 'calories'])

def fetch_nutritional_info(food_name, max_retries=3):
    """Enhanced API call with retry logic and better error handling."""
    api_key = "iBOUPzaCXlEy5E4Z4qz758aWgVQobfE6ck2kSXIw"
    url = f"https://api.nal.usda.gov/fdc/v1/foods/search?query={food_name}&api_key={api_key}"
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('foods'):
                    nutrients = data['foods'][0].get('foodNutrients', [])
                    calories = next((item['value'] for item in nutrients if item.get('nutrientName') == 'Energy'), None)
                    carbs = next((item['value'] for item in nutrients if item.get('nutrientName') == 'Carbohydrate, by difference'), None)
                    protein = next((item['value'] for item in nutrients if item.get('nutrientName') == 'Protein'), 0)
                    fat = next((item['value'] for item in nutrients if item.get('nutrientName') == 'Total lipid (fat)'), 0)
                    return calories, carbs, protein, fat
                else:
                    st.info(f"🔍 No nutritional data found for '{food_name}' in API")
                    return None, None, None, None
                    
            elif response.status_code == 401:
                st.error("❌ API authentication failed - check API key")
                return None, None, None, None
            elif response.status_code == 429:
                wait_time = 2 ** attempt
                st.warning(f"⏱️ Rate limit exceeded, retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                continue
            else:
                st.warning(f"⚠️ API returned status {response.status_code}")
                
        except requests.exceptions.Timeout:
            st.warning(f"⏱️ Request timeout (attempt {attempt + 1}/{max_retries})")
        except requests.exceptions.ConnectionError:
            st.warning(f"🌐 Connection error (attempt {attempt + 1}/{max_retries})")
        except requests.exceptions.RequestException as e:
            st.warning(f"🔗 Request failed: {str(e)} (attempt {attempt + 1}/{max_retries})")
        except ValueError as e:
            st.error(f"❌ JSON parsing error: {str(e)}")
            return None, None, None, None
        except Exception as e:
            st.error(f"❌ Unexpected API error: {str(e)}")
            return None, None, None, None
    
    st.error(f"❌ Failed to fetch data for '{food_name}' after {max_retries} attempts")
    return None, None, None, None

def get_user_filename(user_email):
    """Generate a safe filename for user's meal log based on email."""
    try:
        email_hash = hashlib.md5(user_email.encode()).hexdigest()[:12]
        return f"meal_log_{email_hash}.json"
    except Exception as e:
        st.error(f"❌ Error generating filename: {str(e)}")
        return "meal_log_default.json"

def get_user_goal_filename(user_email):
    """Generate a safe filename for user's daily goal based on email."""
    try:
        email_hash = hashlib.md5(user_email.encode()).hexdigest()[:12]
        return f"daily_goal_{email_hash}.json"
    except Exception as e:
        st.error(f"❌ Error generating goal filename: {str(e)}")
        return "daily_goal_default.json"

def save_meal_log(meal_log, user_email):
    """Enhanced save with proper error handling."""
    filename = get_user_filename(user_email)
    try:
        os.makedirs("user_data", exist_ok=True)
        filepath = os.path.join("user_data", filename)
        
        # Create backup before saving
        if os.path.exists(filepath):
            backup_path = f"{filepath}.backup"
            try:
                shutil.copy2(filepath, backup_path)
            except Exception as e:
                st.warning(f"⚠️ Could not create backup: {str(e)}")
        
        with open(filepath, "w", encoding='utf-8') as f:
            serializable_log = []
            for meal in meal_log:
                try:
                    meal_copy = meal.copy()
                    # Ensure consistent timezone handling
                    if hasattr(meal_copy['timestamp'], 'tzinfo'):
                        if meal_copy['timestamp'].tzinfo is None:
                            meal_copy['timestamp'] = meal_copy['timestamp'].replace(tzinfo=IST)
                        meal_copy['timestamp'] = meal_copy['timestamp'].isoformat()
                    else:
                        # Handle timezone-naive timestamps
                        meal_copy['timestamp'] = meal_copy['timestamp'].replace(tzinfo=IST).isoformat()
                    serializable_log.append(meal_copy)
                except Exception as e:
                    st.warning(f"⚠️ Skipping invalid meal entry: {str(e)}")
                    continue
            
            json.dump(serializable_log, f, indent=2)
            
        # Verify file was written correctly
        if os.path.getsize(filepath) == 0:
            raise IOError("File written but is empty")
            
    except (IOError, OSError) as e:
        st.error(f"❌ File operation failed: {str(e)}")
        # Try to restore from backup
        backup_path = f"{filepath}.backup"
        if os.path.exists(backup_path):
            try:
                shutil.copy2(backup_path, filepath)
                st.warning("🔄 Restored from backup")
            except Exception:
                pass
    except (TypeError, ValueError) as e:
        st.error(f"❌ Data serialization error: {str(e)}")
    except Exception as e:
        st.error(f"❌ Unexpected error saving meal: {str(e)}")
        print(f"Save error details: {type(e).__name__}: {e}")

def load_meal_log(user_email):
    """Load meal log from a JSON file for specific user with validation."""
    filename = get_user_filename(user_email)
    filepath = os.path.join("user_data", filename)
    
    try:
        if os.path.exists(filepath):
            with open(filepath, "r", encoding='utf-8') as f:
                data = json.load(f)
                
                # Validate and clean data
                valid_meals = []
                for i, meal in enumerate(data):
                    try:
                        # Check required fields
                        required_fields = ['timestamp', 'meal_time', 'food', 'calories']
                        if not all(field in meal for field in required_fields):
                            st.warning(f"⚠️ Meal entry {i+1} missing required fields, skipping")
                            continue
                        
                        # Convert timestamp strings back to datetime
                        if isinstance(meal['timestamp'], str):
                            meal['timestamp'] = datetime.fromisoformat(meal['timestamp'])
                        
                        # Ensure timezone awareness
                        if meal['timestamp'].tzinfo is None:
                            meal['timestamp'] = meal['timestamp'].replace(tzinfo=IST)
                        
                        # Validate data types
                        meal['calories'] = float(meal['calories'])
                        if meal['calories'] < 0:
                            meal['calories'] = 0
                            
                        valid_meals.append(meal)
                        
                    except (ValueError, TypeError) as e:
                        st.warning(f"⚠️ Invalid meal entry {i+1} removed: {str(e)}")
                        continue
                    except Exception as e:
                        st.warning(f"⚠️ Error processing meal entry {i+1}: {str(e)}")
                        continue
                
                return valid_meals
        return []
    except FileNotFoundError:
        return []
    except json.JSONDecodeError as e:
        st.error(f"❌ Corrupted meal log file: {str(e)}")
        # Try to load backup
        backup_path = f"{filepath}.backup"
        if os.path.exists(backup_path):
            try:
                with open(backup_path, "r", encoding='utf-8') as f:
                    data = json.load(f)
                    st.info("🔄 Loaded from backup file")
                    return data
            except Exception:
                pass
        return []
    except Exception as e:
        st.error(f"❌ Failed to load meal log: {str(e)}")
        return []

def save_daily_goal(daily_goal, user_email):
    """Save daily goal for specific user with error handling."""
    filename = get_user_goal_filename(user_email)
    try:
        os.makedirs("user_data", exist_ok=True)
        filepath = os.path.join("user_data", filename)
        
        # Validate goal value
        if not isinstance(daily_goal, (int, float)) or daily_goal <= 0:
            raise ValueError("Daily goal must be a positive number")
        
        with open(filepath, "w", encoding='utf-8') as f:
            json.dump({"daily_goal": float(daily_goal)}, f)
            
    except (ValueError, TypeError) as e:
        st.error(f"❌ Invalid daily goal value: {str(e)}")
    except Exception as e:
        st.error(f"❌ Failed to save daily goal: {str(e)}")

def load_daily_goal(user_email):
    """Load daily goal for specific user with validation."""
    filename = get_user_goal_filename(user_email)
    filepath = os.path.join("user_data", filename)
    
    try:
        if os.path.exists(filepath):
            with open(filepath, "r", encoding='utf-8') as f:
                data = json.load(f)
                goal = data.get("daily_goal", 2000)
                
                # Validate goal value
                if isinstance(goal, (int, float)) and goal > 0:
                    return float(goal)
                else:
                    st.warning("⚠️ Invalid daily goal in file, using default")
                    return 2000.0
        return 2000.0  # default goal
    except json.JSONDecodeError:
        st.warning("⚠️ Corrupted goal file, using default")
        return 2000.0
    except Exception as e:
        st.error(f"❌ Failed to load daily goal: {str(e)}")
        return 2000.0

def get_today_date_ist():
    """Get today's date in IST timezone."""
    return datetime.now(IST).date()

def filter_meals_by_date(meal_log, target_date):
    """Filter meals by date with proper timezone handling."""
    try:
        filtered_meals = []
        for meal in meal_log:
            try:
                meal_timestamp = meal['timestamp']
                
                # Ensure timezone awareness
                if meal_timestamp.tzinfo is None:
                    meal_timestamp = meal_timestamp.replace(tzinfo=IST)
                
                # Convert to IST and compare dates
                meal_date = meal_timestamp.astimezone(IST).date()
                
                if meal_date == target_date:
                    filtered_meals.append(meal)
            except Exception as e:
                st.warning(f"⚠️ Error processing meal timestamp: {str(e)}")
                continue
                
        return filtered_meals
        
    except Exception as e:
        st.error(f"❌ Error filtering meals by date: {str(e)}")
        return []

def validate_user_input(food_name, quantity, calories=None):
    """Validate user inputs with specific error messages."""
    errors = []
    
    # Food name validation
    if not food_name or len(food_name.strip()) == 0:
        errors.append("Food name cannot be empty")
    elif len(food_name.strip()) < 2:
        errors.append("Food name must be at least 2 characters")
    elif len(food_name.strip()) > 100:
        errors.append("Food name is too long (max 100 characters)")
    
    # Quantity validation
    if quantity is None or quantity <= 0:
        errors.append("Quantity must be greater than 0")
    elif quantity > 5000:  # 5kg limit
        errors.append("Quantity seems unrealistic (max 5000g)")
    
    # Calories validation (if provided)
    if calories is not None:
        if calories < 0:
            errors.append("Calories cannot be negative")
        elif calories > 2000:  # per 100g limit
            errors.append("Calories per 100g seems unrealistic (max 2000)")
    
    return errors

def generate_pdf_report(meal_log, daily_goal, user_email):
    """Generate PDF report with error handling."""
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=14)
        pdf.cell(0, 10, "Diet Tracker Daily Report", ln=True, align="C")
        
        pdf.set_font("Arial", size=12)
        pdf.ln(5)
        pdf.cell(0, 10, f"User: {user_email}", ln=True)
        pdf.ln(5)
        
        total_calories = sum(item['calories'] for item in meal_log if 'calories' in item)
        pdf.cell(0, 10, f"Daily Calorie Goal: {daily_goal} kcal", ln=True)
        pdf.cell(0, 10, f"Calories Consumed: {total_calories:.2f} kcal", ln=True)
        pdf.cell(0, 10, f"Remaining Calories: {max(daily_goal - total_calories, 0):.2f} kcal", ln=True)
        pdf.ln(10)

        pdf.cell(0, 10, "Logged Meals:", ln=True)
        pdf.set_font("Arial", size=10)
        
        for meal in meal_log:
            try:
                timestamp_str = meal['timestamp'].strftime('%Y-%m-%d %H:%M:%S') if hasattr(meal['timestamp'], 'strftime') else str(meal['timestamp'])
                meal_text = f"{timestamp_str} - {meal.get('meal_time', 'Unknown')} - {meal.get('food', 'Unknown')} - {meal.get('calories', 0)} kcal"
                
                # Handle encoding issues
                try:
                    pdf.cell(0, 8, meal_text, ln=True)
                except UnicodeEncodeError:
                    # Fallback for non-Latin characters
                    safe_text = meal_text.encode('latin-1', 'replace').decode('latin-1')
                    pdf.cell(0, 8, safe_text, ln=True)
            except Exception as e:
                pdf.cell(0, 8, f"Error displaying meal: {str(e)}", ln=True)

        pdf_output = BytesIO()
        pdf_data = pdf.output(dest='S')
        if isinstance(pdf_data, str):
            pdf_output.write(pdf_data.encode('latin-1'))
        else:
            pdf_output.write(pdf_data)
        pdf_output.seek(0)
        return pdf_output
        
    except Exception as e:
        st.error(f"❌ Error generating PDF report: {str(e)}")
        return None

def get_current_user():
    """Get current user email from session state with validation."""
    try:
        user = st.session_state.get('current_user')
        if not user or not user.get('email'):
            st.error("❌ User email not found. Please log in again.")
            st.stop()
        
        # Validate email format
        email = user['email']
        if '@' not in email or len(email) < 5:
            st.error("❌ Invalid email format. Please log in again.")
            st.stop()
            
        return email
    except Exception as e:
        st.error(f"❌ Error getting current user: {str(e)}")
        st.stop()

def initialize_user_session(user_email):
    """Initialize session state for user-specific data with validation."""
    try:
        user_session_key = f"daily_goal_{user_email}"
        meal_log_key = f"meal_log_{user_email}"
        
        if user_session_key not in st.session_state:
            st.session_state[user_session_key] = load_daily_goal(user_email)
        
        if meal_log_key not in st.session_state:
            st.session_state[meal_log_key] = load_meal_log(user_email)
            
    except Exception as e:
        st.error(f"❌ Error initializing user session: {str(e)}")
        # Initialize with defaults
        st.session_state[f"daily_goal_{user_email}"] = 2000.0
        st.session_state[f"meal_log_{user_email}"] = []

def add_debug_info(current_user):
    """Add debug information for troubleshooting."""
    if st.sidebar.checkbox("🔧 Debug Mode"):
        user_meal_log_key = f"meal_log_{current_user}"
        
        st.sidebar.markdown("### Debug Information")
        debug_info = {
            "Current User": current_user,
            "Meal Log Count": len(st.session_state.get(user_meal_log_key, [])),
            "Current IST Time": str(datetime.now(IST)),
            "System Date": str(date.today()),
            "IST Date": str(get_today_date_ist()),
            "Session Keys": [k for k in st.session_state.keys() if current_user in k]
        }
        
        for key, value in debug_info.items():
            st.sidebar.text(f"{key}: {value}")
        
        # Show recent meals with timestamps
        if st.sidebar.button("Show Raw Meal Data"):
            meals = st.session_state.get(user_meal_log_key, [])
            st.sidebar.markdown("### Recent Meals")
            for i, meal in enumerate(meals[-5:]):  # Last 5 meals
                timestamp = meal.get('timestamp', 'No timestamp')
                food = meal.get('food', 'No food')
                st.sidebar.text(f"Meal {i+1}: {timestamp} - {food}")

def app():
    """Main application with comprehensive error handling."""
    try:
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
        
        # Add debug info
        add_debug_info(current_user)
        
        st.sidebar.subheader("🔧 Settings")
        new_daily_goal = st.sidebar.number_input(
            "Set Daily Calorie Goal", 
            min_value=800, 
            max_value=4000, 
            value=int(st.session_state[user_goal_key]), 
            step=50
        )
        
        # Save goal if it changed
        if new_daily_goal != st.session_state[user_goal_key]:
            st.session_state[user_goal_key] = float(new_daily_goal)
            save_daily_goal(new_daily_goal, current_user)
            st.sidebar.success("✅ Daily goal updated!")

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

        # Food matching with error handling
        matched_list = []
        selected_food = None
        
        if typed_food:
            try:
                if not food_df.empty:
                    matched_foods = food_df[food_df['food'].str.contains(typed_food, na=False, regex=False)]
                    matched_list = matched_foods['food'].tolist()
                    if matched_list:
                        selected_food = st.selectbox("Select a matching food", matched_list)
                    else:
                        st.warning("No matches found in datasets.")
                else:
                    st.warning("⚠️ No datasets loaded successfully.")
            except Exception as e:
                st.error(f"❌ Error searching food: {str(e)}")

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
            # Validate inputs
            validation_errors = validate_user_input(typed_food, total_quantity)
            
            if validation_errors:
                for error in validation_errors:
                    st.error(f"❌ {error}")
            elif selected_food:
                try:
                    best_match = food_df[food_df['food'] == selected_food].iloc[0]
                    calories = best_match["calories"] * (total_quantity / 100)
                    
                    new_meal = {
                        "timestamp": datetime.now(IST),
                        "meal_time": meal_time,
                        "food": best_match["food"],
                        "quantity": total_quantity,
                        "calories": round(calories, 2),
                        "source": "dataset"
                    }
                    
                    st.session_state[user_meal_log_key].append(new_meal)
                    save_meal_log(st.session_state[user_meal_log_key], current_user)
                    st.success(f"✅ Added {num_pieces} piece(s) ({total_quantity}g) of {best_match['food']} with {calories:.2f} kcal.")
                    
                except Exception as e:
                    st.error(f"❌ Error logging meal from dataset: {str(e)}")
                    
            else:
                # Try API
                try:
                    cal, carbs, protein, fat = fetch_nutritional_info(typed_food)
                    if cal and carbs is not None:
                        total_calories = cal * (total_quantity / 100)
                        
                        new_meal = {
                            "timestamp": datetime.now(IST),
                            "meal_time": meal_time,
                            "food": typed_food,
                            "quantity": total_quantity,
                            "calories": round(total_calories, 2),
                            "carbs": round(carbs * (total_quantity / 100), 2) if carbs else 0,
                            "protein": round(protein * (total_quantity / 100), 2) if protein else 0,
                            "fat": round(fat * (total_quantity / 100), 2) if fat else 0,
                            "source": "API"
                        }
                        
                        st.session_state[user_meal_log_key].append(new_meal)
                        save_meal_log(st.session_state[user_meal_log_key], current_user)
                        st.success(f"✅ Added {num_pieces} piece(s) ({total_quantity}g) of {typed_food} = {total_calories:.2f} kcal from API.")
                    else:
                        # Manual entry
                        st.warning("⚠️ Food not found in database or API. Please enter nutrition manually.")
                        
                        with st.form("manual_nutrition"):
                            st.markdown("#### Manual Nutrition Entry")
                            calories_input = st.number_input("Calories per 100g", min_value=0.0, value=0.0)
                            carbs_input = st.number_input("Carbohydrates per 100g", min_value=0.0, value=0.0
