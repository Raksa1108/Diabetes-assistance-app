import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import os
import json
from datetime import datetime, date, time, timedelta
import pytz
from openai import OpenAI

# Import functions from other modules
from app.diet_tracker import load_meal_log, get_current_user
from app.history import get_user_by_email

# Set up Indian Standard Time
IST = pytz.timezone('Asia/Kolkata')

# --- OpenAI API Setup with Secure Key Management ---
def get_openai_client():
    """Securely initialize OpenAI client using Streamlit secrets."""
    try:
        api_key = st.secrets["openai"]["api_key"]
        return OpenAI(api_key=api_key)
    except KeyError:
        st.error("❌ Configuration error. Please contact support.")
        st.stop()
    except Exception as e:
        st.error(f"❌ Service unavailable: {str(e)}")
        st.stop()

# Initialize OpenAI client
client = get_openai_client()

# --- Food Sugar Content Database ---
FOOD_SUGAR_DATABASE = {
    # High sugar foods (per 100g)
    'rice': {'sugar_content': 0.12, 'carbs': 28, 'gi': 73},
    'white bread': {'sugar_content': 5.7, 'carbs': 49, 'gi': 75},
    'banana': {'sugar_content': 12.2, 'carbs': 23, 'gi': 51},
    'apple': {'sugar_content': 10.4, 'carbs': 14, 'gi': 36},
    'orange': {'sugar_content': 9.4, 'carbs': 12, 'gi': 45},
    'potato': {'sugar_content': 0.8, 'carbs': 17, 'gi': 78},
    'chocolate': {'sugar_content': 47.9, 'carbs': 61, 'gi': 40},
    'ice cream': {'sugar_content': 21.2, 'carbs': 25, 'gi': 51},
    'biscuit': {'sugar_content': 16.6, 'carbs': 76, 'gi': 69},
    'cake': {'sugar_content': 58.0, 'carbs': 77, 'gi': 76},
    'sugar': {'sugar_content': 99.9, 'carbs': 100, 'gi': 65},
    'honey': {'sugar_content': 82.4, 'carbs': 82, 'gi': 61},
    'milk': {'sugar_content': 4.8, 'carbs': 5, 'gi': 39},
    'yogurt': {'sugar_content': 4.7, 'carbs': 4, 'gi': 36},
    'chapati': {'sugar_content': 1.2, 'carbs': 43, 'gi': 52},
    'dal': {'sugar_content': 2.0, 'carbs': 20, 'gi': 38},
    'chicken': {'sugar_content': 0, 'carbs': 0, 'gi': 0},
    'fish': {'sugar_content': 0, 'carbs': 0, 'gi': 0},
    'egg': {'sugar_content': 0.6, 'carbs': 0.6, 'gi': 0},
    'vegetables': {'sugar_content': 3.5, 'carbs': 7, 'gi': 25},
}

# --- File Helper Functions ---
def get_user_sugar_filename(user_email):
    """Generate a safe filename for user's sugar log based on email."""
    import hashlib
    email_hash = hashlib.md5(user_email.encode()).hexdigest()[:12]
    return f"sugar_analysis_{email_hash}.json"

def save_sugar_analysis(analysis_log, user_email):
    """Save sugar analysis log to a JSON file for persistence."""
    filename = get_user_sugar_filename(user_email)
    try:
        os.makedirs("user_data", exist_ok=True)
        filepath = os.path.join("user_data", filename)
        
        serializable_log = []
        for entry in analysis_log:
            entry_copy = entry.copy()
            if isinstance(entry_copy['timestamp'], datetime):
                entry_copy['timestamp'] = entry_copy['timestamp'].isoformat()
            serializable_log.append(entry_copy)
        
        with open(filepath, "w") as f:
            json.dump(serializable_log, f)
    except Exception as e:
        st.error(f"Failed to save analysis: {e}")

def load_sugar_analysis(user_email):
    """Load sugar analysis log from a JSON file."""
    filename = get_user_sugar_filename(user_email)
    filepath = os.path.join("user_data", filename)
    
    try:
        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                data = json.load(f)
                for entry in data:
                    if isinstance(entry['timestamp'], str):
                        try:
                            entry['timestamp'] = datetime.fromisoformat(entry['timestamp'])
                        except ValueError:
                            entry['timestamp'] = pd.to_datetime(entry['timestamp'])
                return data
        return []
    except Exception as e:
        st.error(f"Failed to load analysis: {e}")
        return []

# --- Sugar Analysis Functions ---
def calculate_food_sugar_content(food_name, quantity_grams):
    """Calculate sugar content and impact for given food and quantity."""
    food_lower = food_name.lower()
    
    # Find closest match in database
    sugar_data = None
    for key in FOOD_SUGAR_DATABASE:
        if key in food_lower or food_lower in key:
            sugar_data = FOOD_SUGAR_DATABASE[key]
            break
    
    if not sugar_data:
        # Default for unknown foods
        sugar_data = {'sugar_content': 5.0, 'carbs': 15, 'gi': 50}
    
    # Calculate values for the given quantity
    factor = quantity_grams / 100.0
    total_sugar = sugar_data['sugar_content'] * factor
    total_carbs = sugar_data['carbs'] * factor
    gi_value = sugar_data['gi']
    
    # Determine impact level
    if total_sugar > 20 or gi_value > 70:
        impact_level = "HIGH"
    elif total_sugar > 10 or gi_value > 55:
        impact_level = "MEDIUM"
    else:
        impact_level = "LOW"
    
    return {
        'total_sugar_grams': round(total_sugar, 1),
        'total_carbs_grams': round(total_carbs, 1),
        'glycemic_index': gi_value,
        'impact_level': impact_level,
        'estimated_bg_rise': estimate_blood_sugar_rise(total_carbs, gi_value)
    }

def estimate_blood_sugar_rise(carbs_grams, gi_value):
    """Estimate blood sugar rise based on carbs and glycemic index."""
    # Simplified formula: Each gram of carb can raise BG by 3-4 mg/dL
    # Adjusted by glycemic index
    base_rise = carbs_grams * 3.5
    gi_factor = gi_value / 100.0
    estimated_rise = base_rise * gi_factor
    return round(estimated_rise, 0)

def analyze_daily_sugar_intake(meal_log):
    """Analyze total daily sugar intake and provide recommendations."""
    today = datetime.now(IST).date()
    today_meals = []
    
    for meal in meal_log:
        try:
            meal_timestamp = pd.to_datetime(meal["timestamp"])
            if meal_timestamp.date() == today:
                today_meals.append(meal)
        except:
            continue
    
    if not today_meals:
        return None
    
    total_sugar = 0
    total_carbs = 0
    high_impact_foods = []
    meal_analysis = []
    
    for meal in today_meals:
        food_name = meal.get('food', '')
        quantity = meal.get('quantity', 100)
        
        sugar_info = calculate_food_sugar_content(food_name, quantity)
        total_sugar += sugar_info['total_sugar_grams']
        total_carbs += sugar_info['total_carbs_grams']
        
        if sugar_info['impact_level'] == 'HIGH':
            high_impact_foods.append(f"{food_name} ({quantity}g)")
        
        meal_analysis.append({
            'food': food_name,
            'quantity': quantity,
            'sugar_content': sugar_info['total_sugar_grams'],
            'carbs': sugar_info['total_carbs_grams'],
            'impact': sugar_info['impact_level'],
            'estimated_bg_rise': sugar_info['estimated_bg_rise']
        })
    
    return {
        'total_sugar_today': round(total_sugar, 1),
        'total_carbs_today': round(total_carbs, 1),
        'high_impact_foods': high_impact_foods,
        'meal_analysis': meal_analysis,
        'recommendation_level': 'STOP' if total_sugar > 50 else 'CAUTION' if total_sugar > 25 else 'GOOD'
    }

# --- AI-Powered Recommendations ---
def get_food_based_recommendations(daily_analysis, user_profile=None, blood_sugar_status=None):
    """Generate intelligent recommendations based on food intake."""
    if not daily_analysis:
        return "No food data available for analysis today."
    
    profile_str = ""
    if user_profile:
        profile_str = f"User: Age {user_profile.get('age', 'unknown')}, Weight {user_profile.get('weight', 'unknown')} kg. "
    
    bg_str = ""
    if blood_sugar_status:
        bg_str = f"Recent blood sugar check: {blood_sugar_status}. "
    
    high_foods = ', '.join(daily_analysis['high_impact_foods']) if daily_analysis['high_impact_foods'] else "none"
    
    prompt = f"""
    Today's sugar intake analysis:
    - Total sugar consumed: {daily_analysis['total_sugar_today']}g
    - Total carbohydrates: {daily_analysis['total_carbs_today']}g
    - High-impact foods: {high_foods}
    - Recommendation level: {daily_analysis['recommendation_level']}
    {profile_str}
    {bg_str}
    
    Provide personalized advice for managing blood sugar for an Indian user:
    1. Assessment of today's intake
    2. Specific dietary recommendations for rest of the day
    3. Suggestions for next meals
    4. Warning signs to watch for
    
    Use simple, encouraging language. Focus on practical Indian food alternatives.
    Don't mention technical terms or analysis methods.
    """
    
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=350,
            temperature=0.7
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        # Fallback recommendations without revealing API usage
        if daily_analysis['recommendation_level'] == 'STOP':
            return f"⚠️ High sugar intake detected today ({daily_analysis['total_sugar_today']}g). Consider avoiding additional sweets and refined foods for the rest of the day. Focus on vegetables, dal, and lean proteins."
        elif daily_analysis['recommendation_level'] == 'CAUTION':
            return f"⚠️ Moderate sugar intake today ({daily_analysis['total_sugar_today']}g). Be mindful of portion sizes for the rest of the day. Choose whole grains and vegetables for upcoming meals."
        else:
            return f"✅ Good sugar management today ({daily_analysis['total_sugar_today']}g). Continue with balanced meals including vegetables, proteins, and complex carbohydrates."

# --- Main Application ---
def app():
    st.title("🍽️ Smart Sugar Analysis")
    st.markdown("*Intelligent blood sugar insights based on your food intake*")
    
    user_email = get_current_user()
    meal_log = load_meal_log(user_email)
    analysis_log = load_sugar_analysis(user_email)
    
    # Get user profile
    user_profile = None
    try:
        user_profile = get_user_by_email(user_email)
    except:
        pass
    
    # --- Blood Sugar Check Section ---
    st.subheader("🩸 Blood Sugar Status")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        bg_check = st.selectbox(
            "Did you check your blood sugar recently?",
            ["Select an option", "Yes, after meal", "Yes, before meal", "Yes, random check", "No, haven't checked"]
        )
    
    with col2:
        if bg_check and bg_check != "Select an option":
            if bg_check.startswith("Yes"):
                bg_level = st.number_input("Blood sugar level (mg/dL)", min_value=40, max_value=400, step=1)
            else:
                bg_level = None
    
    # --- Daily Sugar Analysis ---
    st.subheader("📊 Today's Sugar Intake Analysis")
    
    daily_analysis = analyze_daily_sugar_intake(meal_log)
    
    if daily_analysis:
        # Display summary cards
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            color = "red" if daily_analysis['total_sugar_today'] > 50 else "orange" if daily_analysis['total_sugar_today'] > 25 else "green"
            st.metric("Total Sugar", f"{daily_analysis['total_sugar_today']}g", delta_color=color)
        
        with col2:
            st.metric("Total Carbs", f"{daily_analysis['total_carbs_today']}g")
        
        with col3:
            rec_level = daily_analysis['recommendation_level']
            color_map = {'STOP': '🔴', 'CAUTION': '🟡', 'GOOD': '🟢'}
            st.metric("Status", f"{color_map.get(rec_level, '⚪')} {rec_level}")
        
        with col4:
            high_impact_count = len(daily_analysis['high_impact_foods'])
            st.metric("High Impact Foods", f"{high_impact_count}")
        
        # Detailed food analysis
        st.subheader("🍽️ Food Impact Breakdown")
        
        if daily_analysis['meal_analysis']:
            for meal in daily_analysis['meal_analysis']:
                impact_color = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}
                
                with st.expander(f"{impact_color.get(meal['impact'], '⚪')} {meal['food']} ({meal['quantity']}g)"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.write(f"**Sugar Content:** {meal['sugar_content']}g")
                    with col2:
                        st.write(f"**Carbohydrates:** {meal['carbs']}g")
                    with col3:
                        st.write(f"**Estimated BG Rise:** +{meal['estimated_bg_rise']} mg/dL")
        
        # --- Intelligent Recommendations ---
        st.subheader("💡 Personalized Recommendations")
        
        blood_sugar_status = None
        if bg_check and bg_check.startswith("Yes") and 'bg_level' in locals() and bg_level:
            blood_sugar_status = f"{bg_level} mg/dL ({bg_check.split(', ')[1]})"
        
        with st.spinner("Analyzing your data..."):
            recommendations = get_food_based_recommendations(
                daily_analysis, 
                user_profile, 
                blood_sugar_status
            )
            
            st.success(recommendations)
        
        # Daily limit warnings
        if daily_analysis['recommendation_level'] == 'STOP':
            st.error("🚨 **Daily Sugar Limit Exceeded!** Consider avoiding additional sugary foods today.")
        elif daily_analysis['recommendation_level'] == 'CAUTION':
            st.warning("⚠️ **Approaching Daily Limit** - Be mindful of your next food choices.")
        
        # Save analysis
        current_time = datetime.now(IST)
        analysis_entry = {
            'timestamp': current_time,
            'total_sugar': daily_analysis['total_sugar_today'],
            'total_carbs': daily_analysis['total_carbs_today'],
            'recommendation_level': daily_analysis['recommendation_level'],
            'high_impact_foods': daily_analysis['high_impact_foods'],
            'blood_sugar_check': blood_sugar_status
        }
        
        # Update analysis log
        today_str = current_time.date().isoformat()
        existing_today = [a for a in analysis_log if a['timestamp'].date().isoformat() == today_str]
        
        if not existing_today:
            analysis_log.append(analysis_entry)
            save_sugar_analysis(analysis_log, user_email)
    
    else:
        st.info("No meals logged today. Visit the Diet Tracker to log your meals and get sugar analysis!")
    
    # --- Weekly Trend Analysis ---
    if analysis_log:
        st.subheader("📈 Weekly Sugar Trend")
        
        df_analysis = pd.DataFrame(analysis_log)
        df_analysis['timestamp'] = pd.to_datetime(df_analysis['timestamp'])
        df_analysis = df_analysis.sort_values('timestamp')
        
        # Last 7 days
        week_ago = datetime.now(IST) - timedelta(days=7)
        recent_analysis = df_analysis[df_analysis['timestamp'] >= week_ago]
        
        if not recent_analysis.empty:
            fig, ax = plt.subplots(figsize=(12, 6))
            
            # Plot sugar intake over time
            ax.plot(recent_analysis['timestamp'], recent_analysis['total_sugar'], 
                   marker='o', linewidth=2, markersize=6, color='#ff6b6b', label='Daily Sugar Intake')
            
            # Add recommended limit line
            ax.axhline(y=25, color='orange', linestyle='--', alpha=0.7, label='Recommended Limit (25g)')
            ax.axhline(y=50, color='red', linestyle='--', alpha=0.7, label='High Limit (50g)')
            
            ax.set_xlabel('Date')
            ax.set_ylabel('Sugar Intake (grams)')
            ax.set_title('Daily Sugar Consumption - Last 7 Days')
            ax.legend()
            ax.grid(True, alpha=0.3)
            
            plt.xticks(rotation=45)
            plt.tight_layout()
            st.pyplot(fig)
            
            # Weekly statistics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Avg Daily Sugar", f"{recent_analysis['total_sugar'].mean():.1f}g")
            with col2:
                st.metric("Highest Day", f"{recent_analysis['total_sugar'].max():.1f}g")
            with col3:
                st.metric("Days Over Limit", f"{len(recent_analysis[recent_analysis['total_sugar'] > 25])}/7")
            with col4:
                good_days = len(recent_analysis[recent_analysis['recommendation_level'] == 'GOOD'])
                st.metric("Good Days", f"{good_days}/7")
    
    # --- Quick Tips Section ---
    st.subheader("💡 Quick Tips")
    
    tips_col1, tips_col2 = st.columns(2)
    
    with tips_col1:
        st.info("""
        **Low Sugar Alternatives:**
        • Replace white rice with brown rice
        • Choose whole wheat chapati
        • Opt for fresh fruits over juices
        • Use jaggery instead of sugar (in moderation)
        """)
    
    with tips_col2:
        st.success("""
        **Blood Sugar Friendly Foods:**
        • Vegetables and salads
        • Dal and legumes  
        • Lean proteins (chicken, fish)
        • Nuts and seeds
        """)
    
    # --- Data Export ---
    if analysis_log:
        st.subheader("⚙️ Export Data")
        
        df_export = pd.DataFrame(analysis_log)
        csv = df_export.to_csv(index=False)
        st.download_button(
            label="📥 Download Sugar Analysis (CSV)",
            data=csv,
            file_name=f"sugar_analysis_{user_email.replace('@', '_')}_{date.today()}.csv",
            mime="text/csv"
        )

if __name__ == "__main__":
    app()