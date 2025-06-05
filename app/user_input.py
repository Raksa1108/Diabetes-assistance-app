import streamlit as st
import pandas as pd
import joblib
import os
from datetime import datetime
from functions.function import make_donut
from data.base import st_style, head
from supabase_client import supabase  # Import supabase client for user data

MODEL_PATH = os.path.join("datasets", "diabetes_model.pkl")

model = joblib.load(MODEL_PATH)

def get_user_by_email(email):
    """Fetch user data from Supabase."""
    response = supabase.table("users").select("*").eq("email", email).execute()
    return response.data[0] if response.data else None

def app():
    # Check if user is logged in
    user = st.session_state.get('current_user')
    if not user or not user.get('email'):
        st.error("User not logged in. Please log in to make predictions.")
        return
    
    email = user['email']
    
    # Ensure the data directory exists
    data_dir = "data"
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    
    # Use user-specific history file
    HISTORY_FILE = os.path.join(data_dir, f"prediction_history_{email.replace('@', '_').replace('.', '_')}.csv")

    # Apply custom styles
    st.markdown(st_style, unsafe_allow_html=True)
    st.markdown(head, unsafe_allow_html=True)

    st.title("🧪 AI-based Diabetes Risk Prediction")
    st.subheader("📋 Enter your health information:")

    pregnancies = st.number_input("Pregnancies", min_value=0, max_value=20, value=0,
                                  help="Number of times you have been pregnant.")
    glucose = st.number_input("Glucose", min_value=0, max_value=200, value=120,
                              help="Plasma glucose concentration after 2 hours in OGTT.")
    blood_pressure = st.number_input("Blood Pressure", min_value=0, max_value=150, value=70,
                                     help="Diastolic blood pressure (mm Hg).")
    skin_thickness = st.number_input("Skin Thickness", min_value=0, max_value=100, value=20,
                                     help="Triceps skin fold thickness (mm).")
    insulin = st.number_input("Insulin", min_value=0, max_value=900, value=79,
                              help="2-hour serum insulin (mu U/ml).")
    bmi = st.number_input("BMI", min_value=0.0, max_value=67.0, value=25.0,
                          help="Body Mass Index (weight in kg/(height in m)^2).")
    dpf = st.number_input("Diabetes Pedigree Function", min_value=0.0, max_value=2.5, value=0.5,
                          help="Function scoring likelihood of diabetes based on family history.")
    age = st.number_input("Age", min_value=1, max_value=120, value=30,
                          help="Your age in years.")

    input_dict = {
        'Pregnancies': pregnancies,
        'Glucose': glucose,
        'BloodPressure': blood_pressure,
        'SkinThickness': skin_thickness,
        'Insulin': insulin,
        'BMI': bmi,
        'DiabetesPedigreeFunction': dpf,
        'Age': age
    }

    input_df = pd.DataFrame([input_dict])
    st.session_state['last_input'] = input_df

    if st.button("🔍 Predict", type="primary"):
        try:
            # Make prediction
            prediction_proba = model.predict_proba(input_df)[0][1]
            prediction = model.predict(input_df)[0]
            risk_percent = prediction_proba * 100
            label = "Positive" if prediction == 1 else "Negative"
            message = "⚠️ You may have diabetes." if prediction == 1 else "✅ You are unlikely to have diabetes."

            st.subheader("🔮 Prediction Result")
            st.success(message)
            st.metric("Predicted Risk (%)", f"{risk_percent:.2f}%")

            # Donut chart using custom function
            st.altair_chart(
                make_donut(risk_percent, label="Risk Level", input_color='red' if prediction == 1 else 'green'),
                use_container_width=True
            )

            # Save to history
            result_row = input_dict.copy()
            result_row["Risk (%)"] = round(risk_percent, 2)
            result_row["Prediction"] = label
            result_row["Timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            try:
                if os.path.exists(HISTORY_FILE):
                    history_df = pd.read_csv(HISTORY_FILE)
                    history_df = pd.concat([history_df, pd.DataFrame([result_row])], ignore_index=True)
                else:
                    history_df = pd.DataFrame([result_row])

                history_df.to_csv(HISTORY_FILE, index=False)
                st.success("Prediction saved to history.")
            except Exception as e:
                st.error(f"Failed to save prediction to history: {str(e)}")

            st.markdown("---")
        except Exception as e:
            st.error(f"Prediction failed: {str(e)}")

if __name__ == "__main__":
    app()
