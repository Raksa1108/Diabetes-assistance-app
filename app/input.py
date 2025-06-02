
import streamlit as st
import pandas as pd
import joblib
import os
from datetime import datetime
from functions.function import make_donut
from data.base import st_style, head

HISTORY_FILE = "data/prediction_history.csv"
MODEL_PATH = os.path.join("datasets", "diabetes_model.pkl")


model = joblib.load(MODEL_PATH)

def app():
    # Apply custom styles
    st.markdown(st_style, unsafe_allow_html=True)
    st.markdown(head, unsafe_allow_html=True)

    st.title("🧪 AI-based Diabetes Risk Prediction")
    st.subheader("📋 Enter your health information:")

    pregnancies = st.number_input("Pregnancies", min_value=0, max_value=20, value=0)
    glucose = st.number_input("Glucose", min_value=0, max_value=200, value=120)
    blood_pressure = st.number_input("Blood Pressure", min_value=0, max_value=150, value=70)
    skin_thickness = st.number_input("Skin Thickness", min_value=0, max_value=100, value=20)
    insulin = st.number_input("Insulin", min_value=0, max_value=900, value=79)
    bmi = st.number_input("BMI", min_value=0.0, max_value=67.0, value=25.0)
    dpf = st.number_input("Diabetes Pedigree Function", min_value=0.0, max_value=2.5, value=0.5)
    age = st.number_input("Age", min_value=1, max_value=120, value=30)

    input_dict = {
        'Pregnancies': pregnancies,
        'Glucose': glucose,
        'BloodPressure': blood_pressure,
        'SkinThickness(default value)': skin_thickness,
        'Insulin': insulin,
        'BMI': bmi,
        'DiabetesPedigreeFunction': dpf,
        'Age': age
    }

    input_df = pd.DataFrame([input_dict])
    st.session_state['last_input'] = input_df

    if st.button("🔍 Predict", type="primary"):
        # Make prediction
        prediction_proba = model.predict_proba(input_df)[0][1]
        prediction = model.predict(input_df)[0]
        risk_percent = prediction_proba * 100
        label = "Positive" if prediction == 1 else "Negative"
        message = "⚠️ You may have diabetes." if prediction == 1 else "✅ You are unlikely to have diabetes."

        st.subheader("🔮 Prediction Result")
        st.success(message)
        st.metric("Predicted Risk (%)", f"{risk_percent:.2f}%")
        st.altair_chart(make_donut(risk_percent, label="Risk Level", input_color='red' if prediction == 1 else 'green'))

        result_row = input_dict.copy()
        result_row["Risk (%)"] = round(risk_percent, 2)
        result_row["Prediction"] = label
        result_row["Timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if os.path.exists(HISTORY_FILE):
            history_df = pd.read_csv(HISTORY_FILE)
            history_df = pd.concat([history_df, pd.DataFrame([result_row])], ignore_index=True)
        else:
            history_df = pd.DataFrame([result_row])

        history_df.to_csv(HISTORY_FILE, index=False)

        st.markdown("---")
        st.markdown("💖 Thank you for using our diabetes prediction app!")

