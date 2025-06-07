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
    import pytz
    IST = pytz.timezone("Asia/Kolkata")

# Your app() function starts here
def app():
    st.set_page_config(page_title="Meal Tracker", page_icon="🍽️", layout="wide")
    st.markdown(st_style, unsafe_allow_html=True)
    head()

    # Load user
    current_user = st.session_state["current_user"]
    user_goal_key = f"{current_user}_daily_goal"
    user_meal_log_key = f"{current_user}_meal_log"

    # Load or initialize session state
    if user_goal_key not in st.session_state:
        st.session_state[user_goal_key] = load_daily_goal(current_user)
    if user_meal_log_key not in st.session_state:
        st.session_state[user_meal_log_key] = load_meal_log(current_user)

    # Load food dataset
    food_df = pd.read_csv("data/food_dataset.csv")

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
        matched_list = ["None"] + matched_foods['food'].tolist()  # Add 'None' option
        selected_food = st.selectbox("Select a matching food", matched_list)
        if selected_food == "None":
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
                "carbs": 0,
                "protein": 0,
                "fat": 0,
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
                st.success(f"Added {num_pieces} piece(s) ({total_quantity}g) of {typed_food} = {total_calories:.2f} kcal.")
            else:
                st.warning("Food not found in database. Please enter nutrition manually.")
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

    # Calendar View FIXED
    st.markdown("### 📅 Calendar View")
    selected_date = st.date_input("Select a date to view logged meals", value=date.today())

    if st.session_state[user_meal_log_key]:
        df = pd.DataFrame(st.session_state[user_meal_log_key])
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')

        # Force timezone to IST
        if df['timestamp'].dt.tz is None or str(df['timestamp'].dt.tz) == 'None':
            df['timestamp'] = df['timestamp'].dt.tz_localize(IST)
        else:
            df['timestamp'] = df['timestamp'].dt.tz_convert(IST)

        # Extract date
        df['meal_date'] = df['timestamp'].dt.date
        selected_datetime = pd.to_datetime(selected_date).date()

        df_selected_date = df[df['meal_date'] == selected_datetime]

        if df_selected_date.empty:
            st.info(f"No meals logged for {selected_date.strftime('%Y-%m-%d')}.")
        else:
            st.subheader(f"Meals for {selected_date.strftime('%Y-%m-%d')}")
            display_df = df_selected_date.copy()
            display_df['time'] = display_df['timestamp'].dt.strftime('%H:%M:%S')
            display_df = display_df[["time", "meal_time", "food", "quantity", "calories"]].sort_values("time", ascending=False)
            display_df.columns = ["Time", "Meal Time", "Food", "Quantity (g)", "Calories"]

            st.dataframe(display_df, use_container_width=True)

            total_calories_selected = df_selected_date["calories"].sum()
            total_items = len(df_selected_date)

            col1, col2 = st.columns(2)
            with col1:
                st.metric(f"Total Calories", f"{total_calories_selected:.1f} kcal")
            with col2:
                st.metric("Total Items Logged", total_items)
    else:
        st.info("No meals logged yet.")
    st.markdown("### 📊 Daily Summary")
    if st.session_state[user_meal_log_key]:
        df = pd.DataFrame(st.session_state[user_meal_log_key])
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')

        # Force timezone to IST
        if df['timestamp'].dt.tz is None or str(df['timestamp'].dt.tz) == 'None':
            df['timestamp'] = df['timestamp'].dt.tz_localize(IST)
        else:
            df['timestamp'] = df['timestamp'].dt.tz_convert(IST)

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

            # Enhanced calorie goal display
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
            past_week = [today - timedelta(days=i) for i in range(6, -1, -1)]

            # Force timestamp to IST date only
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
            if df['timestamp'].dt.tz is None or str(df['timestamp'].dt.tz) == 'None':
                df['timestamp'] = df['timestamp'].dt.tz_localize(IST)
            else:
                df['timestamp'] = df['timestamp'].dt.tz_convert(IST)
            df['date_only'] = df['timestamp'].dt.date

            weekly_calories = df.groupby('date_only')['calories'].sum()
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
