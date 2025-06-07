import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests
import json

# Internal configuration
_API_KEY = "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"
_MODEL = "gpt-3.5-turbo"

def _get_nutritional_data(food_item):
    """
    Internal function to retrieve nutritional information
    """
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
            content = result['choices'][0]['message']['content']
            nutrition_data = json.loads(content)
            return nutrition_data
        else:
            return None
            
    except Exception as e:
        return None

def _generate_personalized_recommendations(avg_daily_sugar, weekly_sugar, food_history):
    """
    Generate AI-powered personalized diabetes prevention recommendations
    """
    try:
        headers = {
            'Authorization': f'Bearer {_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        food_list = ", ".join(food_history[-10:]) if food_history else "No recent foods logged"
        
        prompt = f"""
        As a nutrition and diabetes prevention specialist, provide 6 specific, actionable recommendations based on this data:
        - Average daily sugar: {avg_daily_sugar:.1f}g
        - Weekly sugar total: {weekly_sugar:.1f}g  
        - Recent foods: {food_list}

        Focus ONLY on:
        1. Diabetes prevention strategies
        2. Blood sugar management 
        3. Nutritional improvements
        4. Specific dietary changes
        5. Lifestyle modifications for metabolic health

        Format as 6 bullet points starting with relevant emojis. Be specific and actionable. Do not mention AI, APIs, or that this is generated content. Write as a nutrition expert.
        
        Example format:
        🍎 Replace sugary snacks with...
        💧 Increase water intake to...
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
            content = result['choices'][0]['message']['content']
            # Split by lines and filter out empty lines
            recommendations = [line.strip() for line in content.split('\n') if line.strip() and ('🍎' in line or '💧' in line or '🥗' in line or '🏃' in line or '⚖️' in line or '🩺' in line or '🚶' in line or '😴' in line or '📊' in line or '🌟' in line)]
            return recommendations[:6]  # Limit to 6 recommendations
        else:
            return _get_default_recommendations(avg_daily_sugar)
            
    except Exception as e:
        return _get_default_recommendations(avg_daily_sugar)

def _get_default_recommendations(avg_daily_sugar):
    """Fallback recommendations if API fails"""
    if avg_daily_sugar > 50:
        return [
            "🚨 Reduce sugar intake immediately - current levels exceed safe limits by over 100%",
            "🥗 Replace processed foods with whole vegetables and lean proteins",
            "💧 Drink 8-10 glasses of water daily to help flush excess glucose",
            "🏃‍♂️ Add 45 minutes of brisk walking after meals to improve glucose uptake",
            "⚖️ Use smaller plates and measure portions to control blood sugar spikes",
            "🩺 Schedule blood glucose monitoring and consult healthcare provider urgently"
        ]
    elif avg_daily_sugar > 25:
        return [
            "⚠️ Gradually reduce daily sugar to under 25g to prevent insulin resistance",
            "🥘 Fill half your plate with non-starchy vegetables at each meal",
            "🚶‍♀️ Take 10-minute walks after eating to stabilize blood sugar",
            "💧 Replace one sugary drink daily with herbal tea or infused water",
            "😴 Maintain 7-8 hours sleep to regulate hunger hormones and glucose metabolism",
            "📊 Track blood sugar patterns and identify trigger foods"
        ]
    else:
        return [
            "✅ Maintain current sugar levels - you're in the optimal range for diabetes prevention",
            "🌟 Continue eating balanced meals with complex carbohydrates and fiber",
            "🥬 Add more antioxidant-rich foods like berries and leafy greens",
            "💪 Maintain consistent meal timing to keep blood sugar stable",
            "🏋️‍♀️ Include resistance training twice weekly to improve insulin sensitivity",
            "👥 Your habits are excellent - consider sharing your approach with others"
        ]

def create_nutrition_pie_chart(nutrition_data):
    """Create pie chart for macronutrients and micronutrients"""
    if not nutrition_data:
        return None
    
    labels = ['Carbohydrates', 'Proteins', 'Fats', 'Vitamins', 'Minerals']
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
        title="Nutritional Composition (per 100g)",
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    
    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(height=400)
    
    return fig

def create_sugar_intake_charts(meals_df):
    """Create daily and weekly sugar intake line charts"""
    if meals_df.empty:
        return None, None
    
    meals_df['timestamp'] = pd.to_datetime(meals_df['timestamp'])
    
    # Daily sugar intake chart
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
    
    # Weekly sugar intake chart
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

def nutrition_analysis_app():
    """Main nutrition analysis and diabetes prevention application"""
    st.header("🍎 Smart Nutrition Analysis & Diabetes Prevention")
    
    # Initialize session state
    if 'meals_data' not in st.session_state:
        st.session_state.meals_data = pd.DataFrame(columns=['food_item', 'timestamp', 'carbs', 'proteins', 'fats', 'sugar', 'vitamins', 'minerals', 'calories'])
    
    if 'food_history' not in st.session_state:
        st.session_state.food_history = []
    
    meals_df = st.session_state.meals_data
    
    # Food analysis section
    st.subheader("🔍 Nutritional Analysis")
    food_item = st.text_input("Enter food item to analyze:", placeholder="e.g., apple, brown rice, chicken breast")
    
    if st.button("Analyze Nutrition", type="primary") and food_item:
        with st.spinner("Analyzing nutritional content..."):
            nutrition_data = _get_nutritional_data(food_item)
            
            if nutrition_data:
                # Add to history
                st.session_state.food_history.append(food_item)
                
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    pie_chart = create_nutrition_pie_chart(nutrition_data)
                    if pie_chart:
                        st.plotly_chart(pie_chart, use_container_width=True)
                
                with col2:
                    # Sugar content prominence
                    sugar_value = nutrition_data.get('sugar', 0)
                    if sugar_value > 15:
                        st.error(f"⚠️ High Sugar: {sugar_value:.1f}g")
                    elif sugar_value > 5:
                        st.warning(f"⚡ Moderate Sugar: {sugar_value:.1f}g")
                    else:
                        st.success(f"✅ Low Sugar: {sugar_value:.1f}g")
                    
                    # Detailed nutritional breakdown
                    st.subheader("Nutritional Profile")
                    st.metric("Calories", f"{nutrition_data.get('calories', 0)} kcal", "per 100g")
                    st.write(f"**Carbohydrates:** {nutrition_data.get('carbs', 0):.1f}g")
                    st.write(f"**Proteins:** {nutrition_data.get('proteins', 0):.1f}g")
                    st.write(f"**Fats:** {nutrition_data.get('fats', 0):.1f}g")
                    st.write(f"**Vitamins:** {nutrition_data.get('vitamins', 0):.1f}mg")
                    st.write(f"**Minerals:** {nutrition_data.get('minerals', 0):.1f}mg")
                
                # Option to add to meal log
                if st.button("Add to Meal Log"):
                    new_meal = {
                        'food_item': food_item,
                        'timestamp': datetime.now(),
                        **nutrition_data
                    }
                    st.session_state.meals_data = pd.concat([meals_df, pd.DataFrame([new_meal])], ignore_index=True)
                    st.success(f"Added {food_item} to your meal log!")
                    st.rerun()
            else:
                st.error("Unable to analyze this food item. Please try a different food or check your spelling.")
    
    # Historical analysis and recommendations
    if not meals_df.empty:
        st.subheader("📊 Diabetes Prevention Dashboard")
        
        # Calculate metrics
        meals_df['timestamp'] = pd.to_datetime(meals_df['timestamp'])
        daily_sugar = meals_df.groupby(meals_df['timestamp'].dt.date)['sugar'].sum()
        avg_daily_sugar = daily_sugar.mean()
        weekly_sugar = daily_sugar.tail(7).sum()
        
        # Display key metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Avg Daily Sugar", f"{avg_daily_sugar:.1f}g", f"{avg_daily_sugar-25:.1f}g vs limit")
        with col2:
            st.metric("This Week", f"{weekly_sugar:.1f}g")
        with col3:
            risk_level = "HIGH" if avg_daily_sugar > 50 else "MODERATE" if avg_daily_sugar > 25 else "LOW"
            risk_color = "🔴" if risk_level == "HIGH" else "🟡" if risk_level == "MODERATE" else "🟢"
            st.metric("Diabetes Risk", f"{risk_color} {risk_level}")
        with col4:
            meals_count = len(meals_df)
            st.metric("Foods Tracked", f"{meals_count}")
        
        # Sugar intake visualization
        daily_fig, weekly_fig = create_sugar_intake_charts(meals_df)
        
        if daily_fig and weekly_fig:
            col1, col2 = st.columns(2)
            with col1:
                st.plotly_chart(daily_fig, use_container_width=True)
            with col2:
                st.plotly_chart(weekly_fig, use_container_width=True)
        
        # AI-powered personalized recommendations
        st.subheader("🎯 Personalized Prevention Plan")
        with st.spinner("Generating personalized recommendations..."):
            recommendations = _generate_personalized_recommendations(
                avg_daily_sugar, 
                weekly_sugar, 
                st.session_state.food_history
            )
            
            for recommendation in recommendations:
                st.markdown(f"• {recommendation}")
        
        # Risk assessment with specific guidance
        st.subheader("🩺 Health Risk Assessment")
        if avg_daily_sugar > 50:
            st.error("**⚠️ IMMEDIATE ACTION REQUIRED**: Your sugar intake is in the high-risk zone for developing Type 2 diabetes. Consider consulting a healthcare provider within the next few days.")
        elif avg_daily_sugar > 36:
            st.warning("**⚡ ELEVATED RISK**: Your sugar intake exceeds safe limits. Take action now to prevent progression to diabetes.")
        elif avg_daily_sugar > 25:
            st.warning("**🔍 MONITOR CLOSELY**: You're approaching the upper limit. Small changes now can prevent future health issues.")
        else:
            st.success("**✅ EXCELLENT CONTROL**: Your sugar intake supports optimal metabolic health. Continue your current approach!")
        
        # Recent food log
        if len(meals_df) > 0:
            st.subheader("📝 Recent Food Log")
            recent_meals = meals_df.tail(5)[['food_item', 'timestamp', 'sugar', 'calories']].copy()
            recent_meals['timestamp'] = recent_meals['timestamp'].dt.strftime('%Y-%m-%d %H:%M')
            st.dataframe(recent_meals, use_container_width=True)
    
    else:
        st.info("🚀 **Get Started**: Analyze your first food item above to begin tracking your nutrition and diabetes risk.")
        
        # Educational content for new users
        st.subheader("📚 Why Track Sugar Intake?")
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("""
            **Diabetes Prevention Benefits:**
            - Early detection of risk patterns
            - Personalized dietary guidance  
            - Blood sugar optimization
            - Metabolic health improvement
            - Long-term disease prevention
            """)
        
        with col2:
            st.write("""
            **Recommended Daily Limits:**
            - **Women**: 25g added sugar (6 tsp)
            - **Men**: 36g added sugar (9 tsp)
            - **Children**: Even lower limits
            - **Diabetics**: Medical supervision required
            """)

if __name__ == "__main__":
    nutrition_analysis_app()
