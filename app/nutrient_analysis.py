import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests
import json

def get_nutritional_data(food_item, api_key, model_version="gpt-3.5-turbo"):
    """
    Get nutritional information using OpenAI API (alternative to Gemini)
    """
    try:
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        prompt = f"""
        Provide nutritional information for "{food_item}" in JSON format with the following structure:
        {{
            "carbs": value_in_grams,
            "proteins": value_in_grams,
            "fats": value_in_grams,
            "sugar": value_in_grams,
            "vitamins": value_in_mg,
            "minerals": value_in_mg,
            "calories": value_in_kcal
        }}
        Only return the JSON object, no additional text.
        """
        
        data = {
            "model": model_version,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 200,
            "temperature": 0.3
        }
        
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers=headers,
            json=data,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            # Try to parse JSON from the response
            nutrition_data = json.loads(content)
            return nutrition_data
        else:
            st.error(f"API Error: {response.status_code}")
            return None
            
    except Exception as e:
        st.error(f"Error getting nutritional data: {str(e)}")
        return None

def create_nutrition_pie_chart(nutrition_data):
    """Create pie chart for macronutrients and micronutrients"""
    if not nutrition_data:
        return None
    
    labels = ['Carbs', 'Proteins', 'Fats', 'Vitamins', 'Minerals']
    values = [
        nutrition_data.get('carbs', 0),
        nutrition_data.get('proteins', 0),
        nutrition_data.get('fats', 0),
        nutrition_data.get('vitamins', 0),
        nutrition_data.get('minerals', 0)
    ]
    
    fig = px.pie(
        values=values,
        names=labels,
        title="Nutritional Breakdown",
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    
    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(height=400)
    
    return fig

def create_sugar_intake_charts(meals_df):
    """Create daily and weekly sugar intake line charts"""
    if meals_df.empty:
        return None, None
    
    # Ensure timestamp column is datetime
    meals_df['timestamp'] = pd.to_datetime(meals_df['timestamp'])
    
    # Daily sugar intake chart
    daily_sugar = meals_df.groupby(meals_df['timestamp'].dt.date)['sugar'].sum().reset_index()
    daily_sugar.columns = ['date', 'sugar_intake']
    
    daily_fig = px.line(
        daily_sugar,
        x='date',
        y='sugar_intake',
        title='Daily Sugar Intake (grams)',
        markers=True
    )
    daily_fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Sugar Intake (g)",
        height=400
    )
    
    # Weekly sugar intake chart
    meals_df['week'] = meals_df['timestamp'].dt.to_period('W').astype(str)
    weekly_sugar = meals_df.groupby('week')['sugar'].sum().reset_index()
    
    weekly_fig = px.line(
        weekly_sugar,
        x='week',
        y='sugar',
        title='Weekly Sugar Intake (grams)',
        markers=True
    )
    weekly_fig.update_layout(
        xaxis_title="Week",
        yaxis_title="Sugar Intake (g)",
        height=400
    )
    
    return daily_fig, weekly_fig

def get_diabetes_prevention_tips(avg_daily_sugar):
    """Generate diabetes prevention tips based on sugar intake"""
    tips = []
    
    if avg_daily_sugar > 50:  # High sugar intake
        tips = [
            "🚨 **High Sugar Alert**: Your daily sugar intake is above recommended levels (25g for women, 36g for men)",
            "🥗 **Dietary Changes**: Replace sugary drinks with water, herbal teas, or sparkling water with lemon",
            "🍎 **Smart Snacking**: Choose whole fruits instead of fruit juices or processed snacks",
            "🏃‍♂ **Increase Activity**: Aim for at least 30 minutes of moderate exercise daily",
            "⚖️ **Portion Control**: Use smaller plates and measure portions to avoid overeating",
            "🩺 **Regular Monitoring**: Check blood sugar levels regularly and consult healthcare provider"
        ]
    elif avg_daily_sugar > 25:  # Moderate sugar intake
        tips = [
            "⚠️ **Moderate Risk**: Your sugar intake is at the upper limit of recommendations",
            "🥘 **Balanced Meals**: Include more fiber-rich foods like vegetables and whole grains",
            "🚶‍♀️ **Stay Active**: Regular physical activity helps regulate blood sugar",
            "💧 **Stay Hydrated**: Drink plenty of water throughout the day",
            "😴 **Quality Sleep**: Aim for 7-8 hours of sleep to maintain healthy metabolism",
            "📊 **Track Progress**: Continue monitoring your food intake and sugar consumption"
        ]
    else:  # Low sugar intake
        tips = [
            "✅ **Good Control**: Your sugar intake is within healthy limits",
            "🌟 **Keep it Up**: Maintain your current healthy eating habits",
            "🥬 **Nutrient Focus**: Ensure you're getting enough vitamins and minerals",
            "💪 **Stay Consistent**: Regular meal timing helps maintain stable blood sugar",
            "🏋️‍♀️ **Maintain Activity**: Continue regular exercise for overall health",
            "👥 **Share Knowledge**: Help others adopt similar healthy habits"
        ]
    
    return tips

def nutrition_analysis_app():
    """Main nutrition analysis application"""
    st.header("🍎 Nutrition Analysis & Diabetes Prevention")
    
    # API Configuration
    st.sidebar.header("API Configuration")
    api_key = st.sidebar.text_input("Enter OpenAI API Key", type="password")
    model_version = st.sidebar.selectbox(
        "Select Model Version",
        ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo-preview"],
        index=0
    )
    
    if not api_key:
        st.warning("Please enter your OpenAI API key in the sidebar to use nutrition analysis features.")
        return
    
    # Load meals data (assuming it exists in session state)
    if 'meals_data' not in st.session_state:
        st.session_state.meals_data = pd.DataFrame(columns=['food_item', 'timestamp', 'carbs', 'proteins', 'fats', 'sugar', 'vitamins', 'minerals', 'calories'])
    
    meals_df = st.session_state.meals_data
    
    # Food analysis section
    st.subheader("🔍 Analyze Individual Food Item")
    food_item = st.text_input("Enter food item to analyze:")
    
    if st.button("Analyze Food") and food_item:
        with st.spinner("Getting nutritional information..."):
            nutrition_data = get_nutritional_data(food_item, api_key, model_version)
            
            if nutrition_data:
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    # Pie chart
                    pie_chart = create_nutrition_pie_chart(nutrition_data)
                    if pie_chart:
                        st.plotly_chart(pie_chart, use_container_width=True)
                
                with col2:
                    # Sugar display
                    st.metric(
                        label="Sugar Content",
                        value=f"{nutrition_data.get('sugar', 0):.1f}g",
                        delta="Per serving"
                    )
                    
                    # Detailed nutritional info
                    st.subheader("Detailed Info")
                    st.write(f"**Calories:** {nutrition_data.get('calories', 0)} kcal")
                    st.write(f"**Carbs:** {nutrition_data.get('carbs', 0)}g")
                    st.write(f"**Proteins:** {nutrition_data.get('proteins', 0)}g")
                    st.write(f"**Fats:** {nutrition_data.get('fats', 0)}g")
                    st.write(f"**Vitamins:** {nutrition_data.get('vitamins', 0)}mg")
                    st.write(f"**Minerals:** {nutrition_data.get('minerals', 0)}mg")
    
    # Historical analysis
    if not meals_df.empty:
        st.subheader("📊 Sugar Intake Analysis")
        
        # Calculate average daily sugar
        meals_df['timestamp'] = pd.to_datetime(meals_df['timestamp'])
        daily_sugar = meals_df.groupby(meals_df['timestamp'].dt.date)['sugar'].sum()
        avg_daily_sugar = daily_sugar.mean()
        
        # Display current sugar metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Average Daily Sugar", f"{avg_daily_sugar:.1f}g")
        with col2:
            st.metric("Total This Week", f"{daily_sugar.tail(7).sum():.1f}g")
        with col3:
            recommended_daily = 25  # WHO recommendation for women
            status = "⚠️ High" if avg_daily_sugar > recommended_daily else "✅ Good"
            st.metric("Status", status)
        
        # Sugar intake charts
        daily_fig, weekly_fig = create_sugar_intake_charts(meals_df)
        
        if daily_fig and weekly_fig:
            col1, col2 = st.columns(2)
            with col1:
                st.plotly_chart(daily_fig, use_container_width=True)
            with col2:
                st.plotly_chart(weekly_fig, use_container_width=True)
        
        # Diabetes prevention tips
        st.subheader("🩺 Diabetes Prevention Recommendations")
        tips = get_diabetes_prevention_tips(avg_daily_sugar)
        
        for tip in tips:
            st.markdown(tip)
        
        # Risk assessment
        st.subheader("📋 Risk Assessment")
        if avg_daily_sugar > 50:
            st.error("**High Risk**: Your sugar intake significantly exceeds recommendations. Consider consulting a healthcare provider.")
        elif avg_daily_sugar > 25:
            st.warning("**Moderate Risk**: Your sugar intake is at the upper limit. Consider making dietary adjustments.")
        else:
            st.success("**Low Risk**: Your sugar intake is within healthy limits. Keep up the good work!")
    
    else:
        st.info("No meal data available yet. Start logging your meals to see nutrition analysis and diabetes prevention recommendations.")
    
    # Educational section
    st.subheader("📚 Diabetes Prevention Education")
    with st.expander("Understanding Blood Sugar and Diabetes"):
        st.write("""
        **What is Diabetes?**
        Diabetes is a condition where your body cannot properly process glucose (sugar) in your blood.
        
        **Type 2 Diabetes Prevention:**
        - Maintain a healthy weight
        - Eat a balanced diet low in processed sugars
        - Exercise regularly (at least 150 minutes per week)
        - Limit sugary drinks and snacks
        - Choose whole grains over refined carbohydrates
        
        **Daily Sugar Recommendations:**
        - Women: Maximum 25g (6 teaspoons) of added sugar
        - Men: Maximum 36g (9 teaspoons) of added sugar
        
        **Warning Signs to Watch For:**
        - Increased thirst and urination
        - Unexplained weight loss
        - Fatigue and weakness
        - Blurred vision
        - Slow-healing cuts or infections
        """)

if __name__ == "__main__":
    nutrition_analysis_app()
