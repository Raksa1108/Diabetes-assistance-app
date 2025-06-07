import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import requests
import json
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
_API_KEY = "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"
_MODEL = "gpt-3.5-turbo"

def _get_nutritional_data(food_item):
    try:
        headers = {
            'Authorization': f'Bearer {_API_KEY}',
            'Content-Type': 'application/json'
        }
        prompt = f"""
        Provide nutritional information for "{food_item}" per 100g serving in JSON format:
        {{
            "carbs": value_in_grams,
            "proteins": value_in_grams,
            "fats": value_in_grams,
            "sugar": value_in_grams,
            "vitamins": value_in_mg,
            "minerals": value_in_mg,
            "calories": value_in_kcal
        }}
        Return only the JSON object, no explanations.
        """
        data = {
            "model": _MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 200,
            "temperature": 0.1
        }
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers=headers,
            json=data,
            timeout=10
        )
        if response.status_code == 200:
            result = response.json()
            content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
            try:
                nutrition_data = json.loads(content)
                if not isinstance(nutrition_data, dict):
                    return None
                for key in ['carbs', 'proteins', 'fats', 'sugar', 'vitamins', 'minerals', 'calories']:
                    if key in nutrition_data and not isinstance(nutrition_data[key], (int, float)):
                        return None
                return nutrition_data
            except json.JSONDecodeError:
                return None
        return None
    except Exception:
        return None

def _generate_personalized_recommendations(avg_daily_sugar, weekly_sugar, food_history, avg_glucose):
    try:
        headers = {
            'Authorization': f'Bearer {_API_KEY}',
            'Content-Type': 'application/json'
        }
        food_list = ", ".join([str(food) for food in food_history[-10:] if isinstance(food, str) and food.strip()]) or "No recent foods logged"
        glucose_status = "high" if avg_glucose > 140 else "normal" if avg_glucose >= 70 else "low"
        prompt = f"""
        As a diabetes nutrition specialist, provide 6 specific, actionable recommendations for diabetes prevention and blood sugar management based on:
        - Average daily sugar intake: {avg_daily_sugar:.1f}g
        - Weekly sugar intake: {weekly_sugar:.1f}g
        - Recent foods: {food_list}
        - Average blood glucose: {avg_glucose:.1f} mg/dL ({glucose_status})

        Focus ONLY on:
        1. Diabetes prevention and blood sugar control
        2. Dietary changes to stabilize glucose levels
        3. Lifestyle modifications for metabolic health

        Format as 6 bullet points starting with emojis (e.g., 🍎, 💧, 🥗). Be specific, actionable, and tailored to the user's glucose and sugar intake. Write as a nutrition expert without mentioning any technology or data sources.
        """
        data = {
            "model": _MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 400,
            "temperature": 0.3
        }
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers=headers,
            json=data,
            timeout=15
        )
        if response.status_code == 200:
            result = response.json()
            content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
            recommendations = [line.strip() for line in content.split('\n') if line.strip() and any(emoji in line for emoji in ['🍎', '💧', '🥗', '🏃', '⚖️', '🩺', '🚶', '😴', '📊', '🌟'])]
            return recommendations[:6]
        return _get_default_recommendations(avg_daily_sugar, avg_glucose)
    except Exception:
        return _get_default_recommendations(avg_daily_sugar, avg_glucose)

def _get_default_recommendations(avg_daily_sugar, avg_glucose):
    if avg_glucose > 140 or avg_daily_sugar > 50:
        return [
            "🚨 Reduce high-sugar foods immediately to lower blood glucose and prevent diabetes complications.",
            "🥗 Choose low-glycemic vegetables like spinach and broccoli to stabilize blood sugar.",
            "💧 Drink 8-10 glasses of water daily to support kidney function and glucose regulation.",
            "🏃‍♂️ Engage in 30 minutes of brisk walking daily to improve insulin sensitivity.",
            "⚖️ Measure portion sizes to avoid blood sugar spikes, especially with sweets.",
            "🩺 Consult a doctor for blood glucose monitoring and personalized diabetes management."
        ]
    elif avg_glucose > 100 or avg_daily_sugar > 25:
        return [
            "⚠️ Limit added sugars to under 25g daily to prevent insulin resistance.",
            "🥘 Include fiber-rich foods like oats and lentils to slow glucose absorption.",
            "🚶‍♀️ Take 15-minute walks after meals to reduce post-meal glucose spikes.",
            "💧 Replace sugary drinks with unsweetened teas or water to lower sugar intake.",
            "😴 Ensure 7-8 hours of sleep to regulate hunger and glucose metabolism.",
            "📊 Monitor blood sugar weekly to identify dietary triggers."
        ]
    else:
        return [
            "✅ Maintain your current diet to support healthy blood sugar levels.",
            "🌟 Add whole grains like quinoa to keep glucose stable.",
            "🥬 Include berries and leafy greens for antioxidants that support metabolic health.",
            "💪 Eat meals at regular times to prevent glucose fluctuations.",
            "🏋️‍♀️ Include strength training twice weekly to enhance insulin sensitivity.",
            "👥 Share your healthy habits to inspire others in diabetes prevention."
        ]

def create_nutrition_pie_chart(total_nutrients):
    if not total_nutrients or all(v == 0 for v in total_nutrients.values()):
        return None
    labels = ['Carbohydrates', 'Proteins', 'Fats', 'Vitamins', 'Minerals']
    values = [
        total_nutrients.get('carbs', 0),
        total_nutrients.get('proteins', 0),
        total_nutrients.get('fats', 0),
        total_nutrients.get('vitamins', 0),
        total_nutrients.get('minerals', 0)
    ]
    fig = px.pie(
        values=values,
        names=labels,
        title="Nutritional Composition of Today's Meals",
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(height=400)
    return fig

def create_sugar_intake_charts(meals_df):
    if meals_df.empty:
        return None, None
    try:
        meals_df['timestamp'] = pd.to_datetime(meals_df['timestamp'], errors='coerce')
        meals_df = meals_df.dropna(subset=['timestamp'])
        daily_sugar = meals_df.groupby(meals_df['timestamp'].dt.date)['sugar'].sum().reset_index()
        daily_sugar.columns = ['date', 'sugar_intake']
        daily_fig = px.line(
            daily_sugar,
            x='date',
            y='sugar_intake',
            title='Daily Sugar Intake Tracking',
            markers=True,
            line_shape='spline'
        )
        daily_fig.add_hline(y=25, line_dash="dash", line_color="red", annotation_text="Recommended Daily Limit (25g)")
        daily_fig.update_layout(
            xaxis_title="Date",
            yaxis_title="Sugar Intake (grams)",
            height=400
        )
        meals_df['week'] = meals_df['timestamp'].dt.to_period('W').astype(str)
        weekly_sugar = meals_df.groupby('week')['sugar'].sum().reset_index()
        weekly_fig = px.line(
            weekly_sugar,
            x='week',
            y='sugar',
            title='Weekly Sugar Intake Trends',
            markers=True,
            line_shape='spline'
        )
        weekly_fig.add_hline(y=175, line_dash="dash", line_color="red", annotation_text="Weekly Recommended Limit (175g)")
        weekly_fig.update_layout(
            xaxis_title="Week",
            yaxis_title="Sugar Intake (grams)",
            height=400
        )
        return daily_fig, weekly_fig
    except Exception:
        return None, None

def nutrition_analysis_app(user_email, meal_log, blood_sugar_data):
    st.header("🍎 Nutrition Analysis & Diabetes Management")
    
    # Validate meal_log
    if not meal_log or not isinstance(meal_log, list):
        st.info("🚀 Log meals in the Diet Tracker tab to view your nutrition analysis.")
        return
    
    # Validate meal_log entries
    valid_meals = [
        meal for meal in meal_log
        if isinstance(meal, dict) and 'food' in meal and 'timestamp' in meal and isinstance(meal['food'], str) and meal['food'].strip()
    ]
    
    meals_df = pd.DataFrame(valid_meals)
    if meals_df.empty:
        st.info("🚀 Log meals in the Diet Tracker tab to view your nutrition analysis.")
        return
    
    # Ensure required columns
    required_columns = ['food', 'timestamp', 'carbs', 'proteins', 'fats', 'sugar', 'calories', 'quantity']
    for col in required_columns:
        if col not in meals_df.columns:
            meals_df[col] = 0
        else:
            meals_df[col] = pd.to_numeric(meals_df[col], errors='coerce').fillna(0)
    
    # Handle timestamps carefully
    try:
        meals_df['timestamp'] = pd.to_datetime(meals_df['timestamp'], errors='coerce')
        # Check if timestamps are naive or aware
        if meals_df['timestamp'].dt.tz is None:
            # Naive timestamps: localize to IST
            meals_df['timestamp'] = meals_df['timestamp'].dt.tz_localize('UTC').dt.tz_convert(IST)
        else:
            # Already timezone-aware: ensure IST
            meals_df['timestamp'] = meals_df['timestamp'].dt.tz_convert(IST)
        meals_df = meals_df.dropna(subset=['timestamp'])
    except Exception as e:
        st.error(f"Error processing timestamps: {str(e)}")
        return
    
    # Fetch missing nutritional data for today’s meals
    today = datetime.now(IST).date()
    today_meals = meals_df[meals_df['timestamp'].dt.date == today]
    
    total_nutrients = {'carbs': 0, 'proteins': 0, 'fats': 0, 'sugar': 0, 'vitamins': 0, 'minerals': 0, 'calories': 0}
    for idx, row in today_meals.iterrows():
        if row['sugar'] == 0:
            nutrition_data = _get_nutritional_data(row['food'])
            if nutrition_data:
                quantity = row.get('quantity', 100)
                for key in total_nutrients:
                    meals_df.at[idx, key] = nutrition_data.get(key, 0) * (quantity / 100)
        for key in total_nutrients:
            total_nutrients[key] += meals_df.at[idx, key]
    
    # Display nutritional pie chart
    st.subheader("🔍 Today's Nutritional Breakdown")
    pie_chart = create_nutrition_pie_chart(total_nutrients)
    if pie_chart:
        st.plotly_chart(pie_chart, use_container_width=True)
    else:
        st.info("No nutritional data available for today’s meals.")
    
    # Calculate sugar and glucose metrics
    daily_sugar = meals_df.groupby(meals_df['timestamp'].dt.date)['sugar'].sum()
    avg_daily_sugar = daily_sugar.mean() if not daily_sugar.empty else 0
    weekly_sugar = daily_sugar.tail(7).sum() if len(daily_sugar) >= 7 else daily_sugar.sum()
    
    blood_sugar_df = pd.DataFrame(blood_sugar_data)
    avg_glucose = 0
    if not blood_sugar_df.empty:
        blood_sugar_df['timestamp'] = pd.to_datetime(blood_sugar_df['timestamp'], errors='coerce')
        blood_sugar_df = blood_sugar_df.dropna(subset=['timestamp'])
        avg_glucose = blood_sugar_df['glucose'].mean() if not blood_sugar_df['glucose'].empty else 0
    
    # Diabetes Management Dashboard
    st.subheader("📊 Diabetes Management Dashboard")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Avg Daily Sugar", f"{avg_daily_sugar:.1f}g", f"{avg_daily_sugar-25:.1f}g vs limit")
    with col2:
        st.metric("This Week’s Sugar", f"{weekly_sugar:.1f}g")
    with col3:
        risk_level = "HIGH" if avg_glucose > 140 or avg_daily_sugar > 50 else "MODERATE" if avg_glucose > 100 or avg_daily_sugar > 25 else "LOW"
        risk_color = "🔴" if risk_level == "HIGH" else "🟡" if risk_level == "MODERATE" else "🟢"
        st.metric("Diabetes Risk", f"{risk_color} {risk_level}")
    with col4:
        st.metric("Avg Glucose", f"{avg_glucose:.1f} mg/dL")
    
    # Sugar intake charts
    daily_fig, weekly_fig = create_sugar_intake_charts(meals_df)
    if daily_fig and weekly_fig:
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(daily_fig, use_container_width=True)
        with col2:
            st.plotly_chart(weekly_fig, use_container_width=True)
    
    # Personalized recommendations
    st.subheader("🎯 Personalized Diabetes Management Plan")
    with st.spinner("Generating your personalized plan..."):
        food_history = [str(food) for food in meals_df['food'].tolist() if isinstance(food, str) and food.strip()]
        recommendations = _generate_personalized_recommendations(avg_daily_sugar, weekly_sugar, food_history, avg_glucose)
        for recommendation in recommendations:
            st.markdown(f"• {recommendation}")
    
    # Health Risk Assessment
    st.subheader("🩺 Diabetes Risk Assessment")
    if avg_glucose > 140 or avg_daily_sugar > 50:
        st.error("**⚠️ HIGH RISK**: Your blood sugar or sugar intake is dangerously high. Consult a healthcare provider immediately.")
    elif avg_glucose > 100 or avg_daily_sugar > 25:
        st.warning("**🔍 MODERATE RISK**: Your blood sugar or sugar intake is elevated. Take action to prevent diabetes progression.")
    else:
        st.success("**✅ LOW RISK**: Your blood sugar and diet support healthy metabolic function. Keep it up!")
    
    # Recent Food Log
    if not today_meals.empty:
        st.subheader("📝 Today’s Food Log")
        recent_meals = today_meals.tail(5)[['food', 'timestamp', 'sugar', 'calories']].copy()
        recent_meals['timestamp'] = recent_meals['timestamp'].dt.strftime('%Y-%m-%d %H:%M')
        st.dataframe(recent_meals, use_container_width=True)

if __name__ == "__main__":
    st.error("Please run this through diet_app.py")
