import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt
from datetime import datetime, date, timedelta
import numpy as np
from fpdf import FPDF
from io import BytesIO
from data.base import st_style, head
from supabase_client import supabase

# Timezone import for IST
try:
    from zoneinfo import ZoneInfo
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
    for df in datasets[:-1]:
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

def generate_pdf_report(meal_log, daily_goal):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=14)
    pdf.cell(0, 10, "Diet Tracker Daily Report", ln=True, align="C")

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

def save_meal_log(meal, email):
    """Save a single meal to Supabase meal_logs table."""
    try:
        supabase.table("meal_logs").insert({
            "user_email": email,
            "timestamp": meal['timestamp'].isoformat(),
            "meal_time": meal['meal_time'],
            "food": meal['food'],
            "quantity": float(meal['quantity']),
            "calories": float(meal['calories']),
            "carbs": float(meal.get('carbs', None)) if meal.get('carbs') is not None else None,
            "protein": float(meal.get('protein', None)) if meal.get('protein') is not None else None,
            "fat": float(meal.get('fat', None)) if meal.get('fat') is not None else None,
            "source": meal['source']
        }).execute()
    except Exception as e:
        st.error(f"Failed to save meal log: {e}")

def load_meal_log(email):
    """Load meal log from Supabase meal_logs table."""
    try:
        response = supabase.table("meal_logs").select("*").eq("user_email", email).order("timestamp", desc=True).execute()
        meal_logs = response.data or []
        for meal in meal_logs:
            meal['timestamp'] = pd.to_datetime(meal['timestamp']).tz_convert(IST)
        return meal_logs
    except Exception as e:
        st.error(f"Failed to load meal log: {e}")
        return []

def get_user_by_email(email):
    """Fetch user data from Supabase."""
    response = supabase.table("users").select("*").eq("email", email).execute()
    return response.data[0] if response.data else None

def save_daily_goal(email, daily_goal):
    """Save daily calorie goal to Supabase."""
    try:
        supabase.table("users").update({"daily_goal": daily_goal}).eq("email", email).execute()
    except Exception as e:
        st.error(f"Failed to save daily goal: {e}")

def app():
    user = st.session_state.get('current_user')
    if not user or not user.get('email'):
        st.error("User not logged in. Please log in to use the Diet Tracker.")
        return
    email = user['email']
    
    user_data = get_user_by_email(email)
    if not user_data:
        st.error("User data not found in database. Please contact support.")
        return

    pred_food, daily_nutrition, indian_food, indian_food1, full_nutrition, indian_processed = load_datasets()
    food_df = merge_datasets(pred_food, daily_nutrition, indian_food, indian_food1, full_nutrition, indian_processed)

    # Initialize session state for daily goal and meal log
    if 'daily_goal' not in st.session_state or f"meal_log_{email}" not in st.session_state:
        st.session_state.daily_goal = user_data.get('daily_goal', 2000)
        st.session_state[f"meal_log_{email}"] = load_meal_log(email)

    st.markdown(st_style, unsafe_allow_html=True)
    st.markdown(head, unsafe_allow_html=True)

    st.title(f"🥗 Diet Tracker for Diabetes - {user_data.get('name', email)}")
    st.sidebar.subheader("🔧 Settings")
    new_daily_goal = st.sidebar.number_input(
        "Set Daily Calorie Goal", min_value=800, max_value=4000, value=int(st.session_state.daily_goal), step=50
    )
    if new_daily_goal != st.session_state.daily_goal:
        st.session_state.daily_goal = new_daily_goal
        save_daily_goal(email, new_daily_goal)

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
            meal = {
                "timestamp": datetime.now(IST),
                "meal_time": meal_time,
                "food": best_match["food"],
                "quantity": total_quantity,
                "calories": round(calories, 2),
                "source": "dataset"
            }
            st.session_state[f"meal_log_{email}"].append(meal)
            save_meal_log(meal, email)
            st.success(f"Added {num_pieces} piece(s) ({total_quantity}g) of {best_match['food']} with {calories:.2f} kcal.")
        else:
            cal, carbs, protein, fat = fetch_nutritional_info(typed_food)
            if cal and carbs is not None:
                total_calories = cal * (total_quantity / 100)
                meal = {
                    "timestamp": datetime.now(IST),
                    "meal_time": meal_time,
                    "food": typed_food,
                    "quantity": total_quantity,
                    "calories": round(total_calories, 2),
                    "carbs": round(carbs * (total_quantity / 100), 2),
                    "protein": round(protein * (total_quantity / 100), 2),
                    "fat": round(fat * (total_quantity / 100), 2),
                    "source": "API"
                }
                st.session_state[f"meal_log_{email}"].append(meal)
                save_meal_log(meal, email)
                st.success(f"Added {num_pieces} piece(s) ({total_quantity}g) of {typed_food} = {total_calories:.2f} kcal from API.")
            else:
                st.warning("Food not found in database or API. Please enter nutrition manually.")
                calories_input = st.number_input("Calories per 100g", min_value=0.0, key="manual_cal")
                carbs_input = st.number_input("Carbohydrates per 100g", min_value=0.0, key="manual_carb")
                protein_input = st.number_input("Protein per 100g", min_value=0.0, key="manual_protein")
                fat_input = st.number_input("Fat per 100g", min_value=0.0, key="manual_fat")
                if calories_input > 0:
                    meal = {
                        "timestamp": datetime.now(IST),
                        "meal_time": meal_time,
                        "food": typed_food,
                        "quantity": total_quantity,
                        "calories": round(calories_input * (total_quantity / 100), 2),
                        "carbs": round(carbs_input * (total_quantity / 100), 2),
                        "protein": round(protein_input * (total_quantity / 100), 2),
                        "fat": round(fat_input * (total_quantity / 100), 2),
                        "source": "manual"
                    }
                    st.session_state[f"meal_log_{email}"].append(meal)
                    save_meal_log(meal, email)
                    st.success(f"Added {num_pieces} piece(s) ({total_quantity}g) of {typed_food} manually.")
                else:
                    st.info("Enter calories to log manually.")

    if st.button("Clear All Logged Meals"):
        try:
            supabase.table("meal_logs").delete().eq("user_email", email).execute()
            st.session_state[f"meal_log_{email}"] = []
            st.success("All logged meals cleared.")
        except Exception as e:
            st.error(f"Failed to clear meals: {str(e)}")

    st.markdown("### 📅 Calendar View")
    selected_date = st.date_input("Select a date to view logged meals", value=date.today())

    meal_log = load_meal_log(email)  # Load from Supabase
    if meal_log:
        df = pd.DataFrame(meal_log)
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
    meal_log = st.session_state[f"meal_log_{email}"]
    if meal_log:
        df = pd.DataFrame(meal_log)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df_today = df[df['timestamp'].dt.date == date.today()]

        if df_today.empty:
            st.info("No meals logged for today.")
        else:
            st.subheader("Today's Meals")
            for i, row in enumerate(df_today.sort_values("timestamp", ascending=False).to_dict('records')):
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
                    if st.button("Clear", key=f"clear_{i}"):
                        try:
                            supabase.table("meal_logs").delete().eq("user_email", email).eq("timestamp", row["timestamp"].isoformat()).execute()
                            st.session_state[f"meal_log_{email}"] = [meal for meal in st.session_state[f"meal_log_{email}"] if meal['timestamp'] != row["timestamp"]]
                            st.success(f"Removed {row['food']} from log.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to delete meal: {e}")

            total_calories = df_today["calories"].sum()
            total_carbs = df_today["carbs"].sum() if "carbs" in df_today.columns else 0
            total_protein = df_today["protein"].sum() if "protein" in df_today.columns else 0
            total_fat = df_today["fat"].sum() if "fat" in df_today.columns else 0

            col1, col2 = st.columns([2, 3])
            with col1:
                st.markdown(
                    f"<h3 style='color: {'green' if total_calories <= st.session_state.daily_goal else 'red'};'>Calories Consumed: {total_calories:.2f} kcal</h3>", 
                    unsafe_allow_html=True
                )
                progress = min(total_calories / st.session_state.daily_goal, 1.0)
                st.progress(progress)
            with col2:
                st.metric("Daily Calorie Goal", f"{st.session_state.daily_goal} kcal")
                st.metric("Remaining Calories", f"{max(st.session_state.daily_goal - total_calories, 0):.2f} kcal")

            nutrients = {
                "Carbohydrates": total_carbs,
                "Proteins": total_protein,
                "Fats": total_fat,
            }
            nutrients = {k: v for k, v in nutrients.items() if v and not np.isnan(v)}

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
            fig, ax = plt.subplots()
            ax.bar(calories_mealtime.index, calories_mealtime.values, color='#4a90e2')
            ax.set_ylabel("Calories (kcal)")
            ax.set_xlabel("Meal Time")
            ax.set_ylim(0, max(calories_mealtime.values.max() * 1.2, st.session_state.daily_goal * 0.3))
            st.pyplot(fig)

            st.markdown("#### Weekly Calories Consumed Trend (Last 7 Days)")
            today = date.today()
            past_week = [today - timedelta(days=i) for i in range(6, -1, -1)]
            df['date_only'] = df['timestamp'].dt.date
            weekly_calories = df.groupby('date_only')['calories'].sum().reindex(past_week, fill_value=0)

            fig, ax = plt.subplots()
            ax.plot(past_week, weekly_calories.values, marker='o', linestyle='-', color='#ff7f0e')
            ax.set_title("Calories Consumed Over Past 7 Days")
            ax.set_ylabel("Calories (kcal)")
            ax.set_xlabel("Date")
            ax.set_xticks(past_week)
            ax.set_xticklabels([d.strftime("%a %d") for d in range past_week], rotation=45)
            ax.axhline(y=st.session_state.daily_goal, color='green', linestyle='--', label='Daily Goal')
            ax.legend()
            st.pyplot(fig)

            if st.button("Download PDF Report"):
                pdf_bytes = generate_pdf_report(df_today.to_dict('records'), st.session_state.daily_goal)
                st.download_button(
                    label="Download PDF",
                    data=pdf_bytes,
                    file_name=f"diet_report_{date.today()}.pdf",
                    mime="text/plain"
                )
    else:
        st.info("No meals logged yet today.")

if __name__ == "__main__":
    app()
