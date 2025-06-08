import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import os
import json
from datetime import datetime, date, time
from openai import OpenAI

# Import functions from other modules
from app.diet_tracker import load_meal_log, get_current_user
from app.history import get_user_by_email  # Import user data function

# --- OpenAI API Setup with Secure Key Management ---
def get_openai_client():
    """Securely initialize OpenAI client using Streamlit secrets."""
    try:
        # Try to get API key from Streamlit secrets
        api_key = st.secrets["openai"]["api_key"]
        return OpenAI(api_key=api_key)
    except KeyError:
        st.error("❌ OpenAI API key not found in secrets. Please configure your API key in Streamlit secrets.")
        st.stop()
    except Exception as e:
        st.error(f"❌ Error initializing OpenAI client: {str(e)}")
        st.stop()

# Initialize OpenAI client
client = get_openai_client()

# --- File Helper Functions ---
def get_user_sugar_filename(user_email):
    """Generate a safe filename for user's sugar log based on email."""
    import hashlib
    email_hash = hashlib.md5(user_email.encode()).hexdigest()[:12]
    return f"sugar_log_{email_hash}.json"

def save_sugar_log(sugar_log, user_email):
    """Save sugar log to a JSON file for persistence for specific user."""
    filename = get_user_sugar_filename(user_email)
    try:
        os.makedirs("user_data", exist_ok=True)
        filepath = os.path.join("user_data", filename)
        
        # Convert datetime to string for JSON serialization
        serializable_log = []
        for entry in sugar_log:
            entry_copy = entry.copy()
            if isinstance(entry_copy['timestamp'], datetime):
                entry_copy['timestamp'] = entry_copy['timestamp'].isoformat()
            serializable_log.append(entry_copy)
        
        with open(filepath, "w") as f:
            json.dump(serializable_log, f)
    except Exception as e:
        st.error(f"Failed to save sugar log: {e}")

def load_sugar_log(user_email):
    """Load sugar log from a JSON file for specific user."""
    filename = get_user_sugar_filename(user_email)
    filepath = os.path.join("user_data", filename)
    
    try:
        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                data = json.load(f)
                # Convert timestamp strings back to datetime
                for entry in data:
                    if isinstance(entry['timestamp'], str):
                        try:
                            entry['timestamp'] = datetime.fromisoformat(entry['timestamp'])
                        except ValueError:
                            # Fallback for different datetime formats
                            entry['timestamp'] = pd.to_datetime(entry['timestamp'])
                return data
        return []
    except Exception as e:
        st.error(f"Failed to load sugar log: {e}")
        return []

# --- Advanced Analytics Functions ---
def detect_spike_downfall(sugar_log, food_log, window_minutes=120):
    """Detect if current sugar level represents a spike or downfall."""
    if len(sugar_log) < 2:
        return "first_reading", 0, []
    
    current = sugar_log[-1]
    previous = sugar_log[-2]
    delta = current['sugar_level'] - previous['sugar_level']
    
    # Find recent foods within time window
    recent_foods = []
    if food_log:
        try:
            # Ensure current timestamp is a datetime object
            if isinstance(current['timestamp'], str):
                current_time = pd.to_datetime(current['timestamp'])
            else:
                current_time = current['timestamp']
            
            # Convert to pandas Timestamp to handle timezone issues
            current_time = pd.Timestamp(current_time)
            
            for food in food_log:
                try:
                    # Ensure food timestamp is a datetime object
                    if isinstance(food['timestamp'], str):
                        food_time = pd.to_datetime(food['timestamp'])
                    else:
                        food_time = food['timestamp']
                    
                    # Convert to pandas Timestamp to handle timezone issues
                    food_time = pd.Timestamp(food_time)
                    
                    # Calculate time difference safely
                    time_diff = current_time - food_time
                    time_diff_minutes = time_diff.total_seconds() / 60
                    
                    if 0 <= time_diff_minutes <= window_minutes:
                        recent_foods.append(food)
                except (ValueError, TypeError, AttributeError) as e:
                    # Skip this food entry if timestamp conversion fails
                    continue
        except (ValueError, TypeError, AttributeError) as e:
            # If timestamp processing fails entirely, return empty recent_foods
            recent_foods = []
    
    # Classify the change
    if delta > 25:
        return "spike", delta, recent_foods
    elif delta < -20:
        return "downfall", delta, recent_foods
    else:
        return "stable", delta, recent_foods

def get_sugar_trend_analysis(sugar_log, days=7):
    """Analyze sugar trends over the past few days."""
    if not sugar_log:
        return None
    
    df = pd.DataFrame(sugar_log)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp')
    
    # Filter to last N days
    cutoff_date = datetime.now() - pd.Timedelta(days=days)
    recent_df = df[df['timestamp'] >= cutoff_date]
    
    if recent_df.empty:
        return None
    
    analysis = {
        'avg_sugar': recent_df['sugar_level'].mean(),
        'max_sugar': recent_df['sugar_level'].max(),
        'min_sugar': recent_df['sugar_level'].min(),
        'readings_count': len(recent_df),
        'high_readings': len(recent_df[recent_df['sugar_level'] > 140]),
        'low_readings': len(recent_df[recent_df['sugar_level'] < 70]),
        'trend': 'improving' if recent_df['sugar_level'].iloc[-3:].mean() < recent_df['sugar_level'].iloc[:-3].mean() else 'concerning'
    }
    
    return analysis

# --- AI-Powered Sugar Content Analysis ---
def get_sugar_content_from_api(food_name, quantity=100):
    """Get sugar content for a food item using OpenAI API."""
    try:
        prompt = f"""
        Analyze the sugar content for: {food_name} (quantity: {quantity}g)
        
        Provide ONLY a JSON response with the following structure:
        {{
            "sugar_grams": <number>,
            "total_carbs": <number>,
            "food_category": "<category>",
            "glycemic_impact": "<low/medium/high>"
        }}
        
        Base your response on standard nutritional data. Be accurate and concise.
        """
        
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.1
        )
        
        response_text = completion.choices[0].message.content.strip()
        # Try to parse JSON from the response
        try:
            import json
            # Extract JSON from response if it contains extra text
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            if start_idx != -1 and end_idx != 0:
                json_str = response_text[start_idx:end_idx]
                return json.loads(json_str)
        except:
            pass
        
        # Fallback if JSON parsing fails
        return {
            "sugar_grams": 5.0,
            "total_carbs": 20.0,
            "food_category": "unknown",
            "glycemic_impact": "medium"
        }
        
    except Exception as e:
        st.error(f"Error getting sugar content: {str(e)}")
        return {
            "sugar_grams": 0.0,
            "total_carbs": 0.0,
            "food_category": "unknown",
            "glycemic_impact": "low"
        }

def analyze_daily_sugar_intake(meal_log):
    """Analyze total sugar intake for today."""
    if not meal_log:
        return {
            'total_sugar_today': 0,
            'high_sugar_foods': [],
            'sugar_breakdown': []
        }
    
    today_meals = []
    for meal in meal_log:
        try:
            meal_timestamp = pd.to_datetime(meal["timestamp"])
            if meal_timestamp.date() == date.today():
                today_meals.append(meal)
        except:
            continue
    
    total_sugar = 0
    high_sugar_foods = []
    sugar_breakdown = []
    
    for meal in today_meals:
        # Get sugar content for each food
        food_name = meal.get('food', '')
        quantity = meal.get('quantity', 100)
        
        # Get sugar content from API
        sugar_data = get_sugar_content_from_api(food_name, quantity)
        sugar_amount = sugar_data.get('sugar_grams', 0)
        
        total_sugar += sugar_amount
        
        sugar_breakdown.append({
            'food': food_name,
            'sugar': sugar_amount,
            'impact': sugar_data.get('glycemic_impact', 'unknown')
        })
        
        # Flag high sugar foods (>15g sugar)
        if sugar_amount > 15:
            high_sugar_foods.append(f"{food_name} ({sugar_amount:.1f}g sugar)")
    
    return {
        'total_sugar_today': round(total_sugar, 1),
        'high_sugar_foods': high_sugar_foods,
        'sugar_breakdown': sugar_breakdown
    }

# --- AI-Powered Advice Generation ---
def get_preventive_measures(sugar_level, food_log, spike_status, delta, recent_foods, user_profile=None, trend_analysis=None):
    """Generate personalized preventive measures using AI."""
    
    # Prepare context information
    meal_str = ', '.join([f"{f['food']} ({f['calories']} kcal)" for f in food_log[-5:]]) if food_log else "none logged today"
    recent_str = ', '.join([f"{f['food']} ({f.get('calories', 'unknown')} kcal)" for f in recent_foods]) if recent_foods else "none in past 2 hours"
    
    # Add user profile context if available
    profile_str = ""
    if user_profile:
        profile_str = f"User profile: Age {user_profile.get('age', 'unknown')}, Weight {user_profile.get('weight', 'unknown')} kg, Height {user_profile.get('height', 'unknown')} cm. "
    
    # Add trend analysis if available
    trend_str = ""
    if trend_analysis:
        trend_str = f"Recent 7-day analysis: Average sugar {trend_analysis['avg_sugar']:.1f} mg/dL, {trend_analysis['high_readings']} high readings, {trend_analysis['low_readings']} low readings, trend is {trend_analysis['trend']}. "
    
    prompt = f"""
    Current blood sugar: {sugar_level} mg/dL
    Change from last reading: {delta:+.1f} mg/dL ({spike_status})
    Recent foods (past 2 hours): {recent_str}
    Recent meals today: {meal_str}
    {profile_str}
    {trend_str}
    
    Provide 3-4 specific, actionable tips for managing blood sugar based on this data:
    1. Immediate actions if needed
    2. Dietary recommendations
    3. Lifestyle suggestions
    4. When to seek medical attention (if applicable)
    
    Use encouraging, clear language. Avoid medical jargon. Never mention AI or API usage.
    Focus on practical, diabetes-friendly advice.
    """
    
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.7
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"Error generating AI advice: {str(e)}")
        return f"Unable to generate personalized advice at this time. General tip: Monitor your blood sugar regularly and maintain a balanced diet. Current reading: {sugar_level} mg/dL."

def get_food_sugar_impact(food_log):
    """Analyze which foods might be causing sugar spikes."""
    if not food_log:
        return "No food data available for analysis."
    
    # Group foods by type and analyze calorie/carb content
    high_impact_foods = []
    for food in food_log[-10:]:  # Last 10 meals
        calories = food.get('calories', 0)
        carbs = food.get('carbs', 0)
        
        # Flag potentially high-impact foods
        if calories > 300 or carbs > 30:
            high_impact_foods.append(f"{food['food']} ({calories} kcal)")
    
    if high_impact_foods:
        return f"High-impact foods recently consumed: {', '.join(high_impact_foods[:5])}. Consider smaller portions or healthier alternatives."
    else:
        return "Your recent food choices appear to be diabetes-friendly. Keep up the good work!"

# --- Main Streamlit App ---
def app():
    st.title("🩸 Sugar Tracker")
    st.markdown("Track your blood sugar levels and get personalized insights.")
    
    # Get current user
    user_email = get_current_user()
    
    # Load user data and logs
    sugar_log = load_sugar_log(user_email)
    meal_log = load_meal_log(user_email)
    
    # Try to get user profile for enhanced recommendations
    user_profile = None
    try:
        user_profile = get_user_by_email(user_email)
    except:
        pass  # Profile not available, continue without it
    
    # --- Sugar Level Input Section ---
    st.subheader("📊 Log Your Blood Sugar")
    
    with st.form("sugar_log_form"):
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            sugar_level = st.number_input(
                "Blood Sugar Level (mg/dL)", 
                min_value=40, 
                max_value=600, 
                step=1,
                help="Normal range: 80-130 mg/dL (before meals), <180 mg/dL (after meals)"
            )
        
        with col2:
            date_val = st.date_input("Date", value=date.today())
        
        with col3:
            time_val = st.time_input("Time", value=datetime.now().time())
        
        # Optional notes
        notes = st.text_input("Notes (optional)", placeholder="e.g., before/after meal, feeling symptoms")
        
        submitted = st.form_submit_button("🔄 Add Sugar Reading", use_container_width=True)
        
        if submitted and sugar_level:
            timestamp = datetime.combine(date_val, time_val)
            new_entry = {
                "timestamp": timestamp,
                "sugar_level": sugar_level,
                "notes": notes
            }
            sugar_log.append(new_entry)
            save_sugar_log(sugar_log, user_email)
            
            # Determine status color
            status_color = "🟢" if 80 <= sugar_level <= 180 else "🟡" if sugar_level < 80 or sugar_level <= 250 else "🔴"
            st.success(f"{status_color} Added reading: {sugar_level} mg/dL at {timestamp.strftime('%Y-%m-%d %H:%M')}")
            st.rerun()

    # --- Daily Sugar Analysis Dashboard ---
    st.subheader("📊 Today's Sugar Intake Analysis")
    
    if meal_log:
        with st.spinner("🔍 Analyzing your sugar intake..."):
            daily_analysis = analyze_daily_sugar_intake(meal_log)
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                # Fixed st.metric call - removed problematic delta_color parameter
                st.metric("Total Sugar", f"{daily_analysis['total_sugar_today']}g")
            
            with col2:
                recommended_max = 25  # WHO recommendation for daily sugar intake
                percentage = min(100, (daily_analysis['total_sugar_today'] / recommended_max) * 100)
                st.metric("% of Daily Limit", f"{percentage:.1f}%")
            
            with col3:
                high_sugar_count = len(daily_analysis['high_sugar_foods'])
                st.metric("High Sugar Items", f"{high_sugar_count}")
            
            # Show high sugar foods if any
            if daily_analysis['high_sugar_foods']:
                st.warning("⚠️ **High Sugar Foods Today:**")
                for food in daily_analysis['high_sugar_foods']:
                    st.write(f"• {food}")
            
            # Sugar breakdown chart
            if daily_analysis['sugar_breakdown']:
                st.subheader("🍽️ Sugar Breakdown by Food")
                breakdown_df = pd.DataFrame(daily_analysis['sugar_breakdown'])
                if not breakdown_df.empty:
                    fig, ax = plt.subplots(figsize=(10, 6))
                    colors = ['red' if impact == 'high' else 'orange' if impact == 'medium' else 'green' 
                             for impact in breakdown_df['impact']]
                    ax.bar(breakdown_df['food'], breakdown_df['sugar'], color=colors)
                    ax.set_ylabel('Sugar Content (g)')
                    ax.set_title('Sugar Content by Food Item')
                    plt.xticks(rotation=45, ha='right')
                    plt.tight_layout()
                    st.pyplot(fig)
    
    else:
        st.info("📝 No food data available. Log meals in the Diet Tracker to see sugar analysis!")

    # --- Current Status Display ---
    if sugar_log:
        latest_entry = sugar_log[-1]
        latest_sugar = latest_entry['sugar_level']
        latest_time = latest_entry['timestamp']
        
        # Status indicator
        if 80 <= latest_sugar <= 130:
            status = "🟢 Normal"
            status_color = "green"
        elif 131 <= latest_sugar <= 180:
            status = "🟡 Elevated"
            status_color = "orange"
        elif latest_sugar < 80:
            status = "🔵 Low"
            status_color = "blue"
        else:
            status = "🔴 High"
            status_color = "red"
        
        st.markdown(f"""
        <div style="background-color: #f0f2f6; padding: 15px; border-radius: 10px; margin: 10px 0;">
            <h3 style="color: {status_color}; margin: 0;">Latest Reading: {latest_sugar} mg/dL</h3>
            <p style="margin: 5px 0;"><strong>Status:</strong> {status}</p>
            <p style="margin: 5px 0;"><strong>Time:</strong> {latest_time.strftime('%Y-%m-%d %H:%M')}</p>
            {f'<p style="margin: 5px 0;"><strong>Notes:</strong> {latest_entry.get("notes", "")}' if latest_entry.get("notes") else ""}
        </div>
        """, unsafe_allow_html=True)

    # --- Data Visualization ---
    st.subheader("📈 Blood Sugar History")
    
    if sugar_log:
        df = pd.DataFrame(sugar_log)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values("timestamp")
        
        # Create enhanced chart
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Plot the main line
        ax.plot(df['timestamp'], df['sugar_level'], marker='o', linewidth=2, markersize=6, color='#1f77b4')
        
        # Add reference ranges
        ax.axhspan(80, 130, alpha=0.2, color='green', label='Normal Range (80-130)')
        ax.axhspan(130, 180, alpha=0.1, color='orange', label='Elevated Range (130-180)')
        ax.axhline(y=180, color='red', linestyle='--', alpha=0.7, label='High Threshold (180)')
        ax.axhline(y=70, color='blue', linestyle='--', alpha=0.7, label='Low Threshold (70)')
        
        ax.set_xlabel('Time')
        ax.set_ylabel('Blood Sugar (mg/dL)')
        ax.set_title('Blood Sugar Levels Over Time')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # Rotate x-axis labels for better readability
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        st.pyplot(fig)
        
        # Show recent statistics
        col1, col2, col3, col4 = st.columns(4)
        recent_readings = df.tail(7)  # Last 7 readings
        
        with col1:
            st.metric("Average (Last 7)", f"{recent_readings['sugar_level'].mean():.1f} mg/dL")
        with col2:
            st.metric("Highest (Last 7)", f"{recent_readings['sugar_level'].max():.0f} mg/dL")
        with col3:
            st.metric("Lowest (Last 7)", f"{recent_readings['sugar_level'].min():.0f} mg/dL")
        with col4:
            readings_in_range = len(recent_readings[(recent_readings['sugar_level'] >= 80) & (recent_readings['sugar_level'] <= 180)])
            st.metric("In Range (Last 7)", f"{readings_in_range}/7")
    
    else:
        st.info("📝 No blood sugar data yet. Log your first reading above to get started!")

    # --- Advanced Analysis & Recommendations ---
    if len(sugar_log) >= 2:
        st.subheader("🧠 Personalized Insights")
        
        # Detect spikes/drops
        spike_status, delta, recent_foods = detect_spike_downfall(sugar_log, meal_log)
        
        # Get trend analysis
        trend_analysis = get_sugar_trend_analysis(sugar_log)
        
        # Generate AI recommendations
        with st.spinner("🔍 Analyzing your data..."):
            try:
                advice = get_preventive_measures(
                    sugar_level=sugar_log[-1]['sugar_level'],
                    food_log=meal_log,
                    spike_status=spike_status,
                    delta=delta,
                    recent_foods=recent_foods,
                    user_profile=user_profile,
                    trend_analysis=trend_analysis
                )
                
                st.markdown("### 💡 Personalized Recommendations")
                st.success(advice)
                
                # Food impact analysis
                food_impact = get_food_sugar_impact(meal_log)
                st.info(f"🍽️ **Food Impact Analysis:** {food_impact}")
                
            except Exception as e:
                st.warning("⚠️ Unable to generate personalized advice at this time. Please check your API configuration.")
    
    # --- Today's Food Log Display ---
    st.subheader("🍽️ Today's Food Log")
    
    if meal_log:
        try:
            today_meals = []
            for m in meal_log:
                try:
                    # Safely convert timestamp to date
                    meal_timestamp = pd.to_datetime(m["timestamp"])
                    if meal_timestamp.date() == date.today():
                        today_meals.append(m)
                except (ValueError, TypeError, KeyError):
                    # Skip meals with invalid timestamps
                    continue
            
            if today_meals:
                df_meals = pd.DataFrame(today_meals)
                df_meals['timestamp'] = pd.to_datetime(df_meals['timestamp'])
                df_meals = df_meals.sort_values("timestamp", ascending=False)
                
                # Display in a nice format
                for _, meal in df_meals.iterrows():
                    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                    with col1:
                        st.write(f"🍴 **{meal.get('food', 'Unknown Food')}**")
                    with col2:
                        st.write(f"⏰ {meal.get('meal_time', 'Unknown Time')}")
                    with col3:
                        st.write(f"📏 {meal.get('quantity', 'Unknown')}g")
                    with col4:
                        st.write(f"🔥 {meal.get('calories', 'Unknown')} kcal")
            else:
                st.info("No meals logged for today. Visit the Diet Tracker to log your meals!")
        except Exception as e:
            st.info("No meals logged yet. Visit the Diet Tracker to start tracking your food intake!")
    else:
        st.info("No meals logged yet. Visit the Diet Tracker to start tracking your food intake!")
    
    # --- Data Management ---
    st.subheader("⚙️ Data Management")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if sugar_log:
            # Export data
            df_export = pd.DataFrame(sugar_log)
            csv = df_export.to_csv(index=False)
            st.download_button(
                label="📥 Download Sugar Data (CSV)",
                data=csv,
                file_name=f"sugar_log_{user_email.replace('@', '_')}_{date.today()}.csv",
                mime="text/csv"
            )
    
    with col2:
        if sugar_log:
            if st.button("🗑️ Clear All Sugar Data", type="secondary"):
                if st.session_state.get('confirm_clear_sugar'):
                    st.session_state['confirm_clear_sugar'] = False
                    # Clear the data
                    sugar_log.clear()
                    save_sugar_log(sugar_log, user_email)
                    st.success("All sugar data cleared!")
                    st.rerun()
                else:
                    st.session_state['confirm_clear_sugar'] = True
                    st.warning("Click again to confirm deletion of all sugar data.")

if __name__ == "__main__":
    app()