import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt
from datetime import datetime, date
from fpdf import FPDF
from io import BytesIO
import os
import numpy as np

@st.cache_data
def load_datasets():
    try:
        # Exact file paths
        pred_food_path = "dataset/pred_food.csv"
        daily_nutrition_path = "dataset/daily_food_nutrition_dataset.csv"
        indian_food_path = "dataset/indian_food.csv"
        indian_food1_path = "dataset/indian_food_DF.csv"
        full_nutrition_path = "dataset/Nutrition_Dataset.csv"
        indian_processed_path = "dataset/Indian_Food_Nutrition_Processed.csv"

        pred_food = pd.read_csv(pred_food_path, encoding="ISO-8859-1") if os.path.exists(pred_food_path) else pd.DataFrame()
        daily_nutrition = pd.read_csv(daily_nutrition_path, encoding="ISO-8859-1") if os.path.exists(daily_nutrition_path) else pd.DataFrame()
        indian_food = pd.read_csv(indian_food_path, encoding="ISO-8859-1") if os.path.exists(indian_food_path) else pd.DataFrame()
        indian_food1 = pd.read_csv(indian_food1_path, encoding="ISO-8859-1") if os.path.exists(indian_food1_path) else pd.DataFrame()
        full_nutrition = pd.read_csv(full_nutrition_path, encoding="ISO-8859-1") if os.path.exists(full_nutrition_path) else pd.DataFrame()
        indian_processed = pd.read_csv(indian_processed_path, encoding="ISO-8859-1") if os.path.exists(indian_processed_path) else pd.DataFrame()

    except Exception as e:
        st.error(f"Dataset loading failed: {e}")
        return None, None, None, None, None, None

    return pred_food, daily_nutrition, indian_food, indian_food1, full_nutrition, indian_processed

def merge_datasets(*datasets):
    dfs = []
    for df in datasets[:-1]: 
        if df is not None and not df.empty:
            df.columns = [col.lower().strip() for col in df.columns]
            if 'food' in df.columns and 'calories' in df.columns:
                dfs.append(df[['food', 'calories']].copy())

    processed = datasets[-1]
    if processed is not None and not processed.empty:
        processed.columns = [col.lower().strip() for col in processed.columns]
        if 'dish name' in processed.columns and 'calories (kcal)' in processed.columns:
            processed['food'] = processed['dish name'].str.lower()
            processed['calories'] = processed['calories (kcal)']
            processed['gi'] = processed.get('glycemic index', 'N/A')
            dfs.append(processed[['food', 'calories', 'gi']])

    if not dfs:
        return pd.DataFrame(columns=['food', 'calories', 'gi'])

    combined = pd.concat(dfs, ignore_index=True)
    combined = combined.drop_duplicates(subset='food')
    combined['food'] = combined['food'].str.lower()
    return combined

def fetch_nutritional_info(food_name):
    api_key = "iBOUPzaCXlEy5E4Z4qz758aWgVQobfE6ck2kSXIw"
    url = f"https://api.nal.usda.gov/fdc/v1/foods/search?query={food_name}&apiKey={api_key}"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data['foods']:
                nutrients = data['foods'][0]['foodNutrients']
                calories = next((item['value'] for item in nutrients if item['nutrientName'] == 'Energy'), None)
                carbs = next((item['value'] for item in nutrients if item['nutrientName'] == 'Carbohydrate, by difference'), None)
                protein = next((item['value'] for item in nutrients if item['nutrientName'] == 'Protein'), 0)
                fat = next((item['value'] for item in nutrients if item['nutrientName'] == 'Total lipid (fat)'), 0)
                return calories, carbs, protein, fat
    except Exception:
        return None, None, None, None
    return None, None, None, None

def classify_gi(gi):
    try:
        gi = float(gi)
        if gi < 55:
            return "Low"
        elif gi < 70:
            return "Medium"
        else:
            return "High"
    except:
        return "Unknown"

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
        pdf.cell(0, 8, f"{meal['timestamp'].strftime('%Y-%m-%d %H:%M:%S')} - {meal['meal_time']} - {meal['food']} - {meal['calories']} kcal", ln=True)

    pdf_output = BytesIO()
    pdf_output.write(pdf.output(dest='S').encode('latin1'))
    pdf_output.seek(0)
    return pdf_output

def app():
    # Load and merge datasets
    pred_food, daily_nutrition, indian_food, indian_food1, full_nutrition, indian_processed = load_datasets()
    food_df = merge_datasets(pred_food, daily_nutrition, indian_food, indian_food1, full_nutrition, indian_processed)

    if food_df.empty:
        st.error("Food dataset is empty. Please check dataset files.")
        return

    if 'daily_goal' not in st.session_state:
        st.session_state.daily_goal = 2000
    if 'meal_log' not in st.session_state:
        st.session_state.meal_log = []

    st.title("🥗 Diet Tracker for Diabetes")
    st.sidebar.subheader("🔧 Settings")
    st.session_state.daily_goal = st.sidebar.number_input(
        "Set Daily Calorie Goal", min_value=800, max_value=4000, value=st.session_state.daily_goal, step=50
    )
    gi_filter = st.sidebar.selectbox("Filter by Glycemic Index", ["All", "Low", "Medium", "High"])

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
            quantity_per_piece = st.number_input("Quantity per piece (in grams)", min_value=1, max_value=1000, step=1)
        else:
            quantity_per_piece = serving_sizes[selected_serving]
            st.write(f"Equivalent to {quantity_per_piece} grams per piece")
    with col3:
        num_pieces = st.number_input("Number of Pieces", min_value=1, max_value=20, step=1, value=1)

    total_quantity = quantity_per_piece * num_pieces if quantity_per_piece else 0

    meal_time = st.selectbox("Meal Time", ["Breakfast", "Lunch", "Dinner", "Snack"])

    if st.button("Log Meal"):
        if not typed_food:
            st.error("Please type a food name to log.")
        elif selected_food:
            best_match = food_df[food_df['food'] == selected_food].iloc[0]
            calories_per_100g = float(best_match["calories"])
            calories = (calories_per_100g / 100) * total_quantity
            gi_val = best_match.get("gi", "N/A")
            st.session_state.meal_log.append({
                "timestamp": datetime.now(),
                "meal_time": meal_time,
                "food": best_match["food"],
                "quantity": total_quantity,
                "calories": round(calories, 2),
                "gi": gi_val,
                "source": "dataset"
            })
            st.success(f"Added {num_pieces} piece(s) ({total_quantity}g) of {best_match['food']} with {calories:.2f} kcal.")
        else:
            cal, carbs, protein, fat = fetch_nutritional_info(typed_food)
            if cal is not None:
                calories = (cal / 100) * total_quantity if total_quantity else cal
                st.session_state.meal_log.append({
                    "timestamp": datetime.now(),
                    "meal_time": meal_time,
                    "food": typed_food,
                    "quantity": total_quantity,
                    "calories": round(calories, 2),
                    "gi": "N/A",
                    "source": "API"
                })
                st.success(f"Added {typed_food} from API with approx. {calories:.2f} kcal.")
            else:
                st.error("No data found for this food from API or datasets.")

    st.markdown("---")
    st.subheader("📊 Today's Intake")

    if st.session_state.meal_log:
        log_df = pd.DataFrame(st.session_state.meal_log)
        log_df['timestamp'] = pd.to_datetime(log_df['timestamp'])

        # Apply GI filter
        if gi_filter != "All":
            filtered_log_df = log_df[log_df['gi'].apply(classify_gi) == gi_filter]
        else:
            filtered_log_df = log_df

        st.dataframe(filtered_log_df[['timestamp', 'meal_time', 'food', 'quantity', 'calories', 'gi', 'source']])

        total_calories = filtered_log_df['calories'].sum()
        remaining = st.session_state.daily_goal - total_calories

        st.metric("Calories Consumed", f"{total_calories:.2f} kcal")
        st.metric("Calories Remaining", f"{remaining:.2f} kcal")

        # Pie chart for meal time distribution
        meal_counts = filtered_log_df['meal_time'].value_counts()
        fig, ax = plt.subplots()
        ax.pie(meal_counts, labels=meal_counts.index, autopct="%1.1f%%", startangle=140)
        ax.set_title("Meals logged by meal time")
        st.pyplot(fig)

        if st.button("Generate PDF Report"):
            pdf_buffer = generate_pdf_report(st.session_state.meal_log, st.session_state.daily_goal)
            st.download_button(
                label="Download PDF Report",
                data=pdf_buffer,
                file_name=f"Diet_Report_{date.today()}.pdf",
                mime="application/pdf"
            )
    else:
        st.info("No meals logged yet. Add some food items above.")

if __name__ == "__main__":
    app()
