import streamlit as st
import pandas as pd
import joblib
import os
from datetime import datetime
import plotly.graph_objects as go
from data.base import st_style, head

HISTORY_FILE = "data/prediction_history.csv"
MODEL_PATH = os.path.join("datasets", "diabetes_model.pkl")

model = joblib.load(MODEL_PATH)

def app():
    # Apply custom styles
    st.markdown(st_style, unsafe_allow_html=True)
    st.markdown(head, unsafe_allow_html=True)

    st.title("🧪 AI-based Diabetes Risk Prediction")
    st.markdown("### 📋 Enter your health information below:")

    pregnancies = st.number_input("Pregnancies", min_value=0, max_value=20, value=0,
                                  help="Number of times you have been pregnant.")
    glucose = st.number_input("Glucose", min_value=0, max_value=200, value=120,
                              help="Plasma glucose concentration over 2 hours in an oral glucose tolerance test.")
    blood_pressure = st.number_input("Blood Pressure", min_value=0, max_value=150, value=70,
                                     help="Diastolic blood pressure (mm Hg).")
    skin_thickness = st.number_input("Skin Thickness", min_value=0, max_value=100, value=20,
                                     help="Triceps skin fold thickness (mm).")
    insulin = st.number_input("Insulin", min_value=0, max_value=900, value=79,
                              help="2-Hour serum insulin (mu U/ml).")
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
        prediction_proba = model.predict_proba(input_df)[0][1]
        prediction = model.predict(input_df)[0]
        risk_percent = prediction_proba * 100
        label = "Positive" if prediction == 1 else "Negative"
        message = "⚠️ You may have diabetes." if prediction == 1 else "✅ You are unlikely to have diabetes."

        # Emoji + color by risk level
        if risk_percent > 70:
            emoji = "🔴"
            pie_color = ["red", "lightgray"]
        elif risk_percent > 30:
            emoji = "🟡"
            pie_color = ["orange", "lightgray"]
        else:
            emoji = "🟢"
            pie_color = ["green", "lightgray"]

        st.markdown("---")
        st.subheader(f"🔮 Prediction Result {emoji}")
        st.success(message)
        st.metric("Predicted Risk (%)", f"{risk_percent:.2f}%")

        # Animate pie from 0 to risk_percent
        frames = []
        for i in range(0, int(risk_percent) + 1, 5):
            frames.append(go.Pie(
                labels=["Diabetes Risk", "No Risk"],
                values=[i, 100 - i],
                hole=0.0,  # full pie
                marker_colors=pie_color,
                textinfo="label+percent"
            ))

        fig = go.Figure(
            data=frames[-1],
            layout=go.Layout(
                title="Risk Distribution",
                template="plotly_dark",
                showlegend=True,
                updatemenus=[dict(type="buttons", showactive=False,
                                  buttons=[dict(label="Play",
                                                method="animate",
                                                args=[None, {"frame": {"duration": 50, "redraw": True},
                                                             "fromcurrent": True,
                                                             "transition": {"duration": 0}}])])]
            ),
            frames=[go.Frame(data=[frame]) for frame in frames]
        )

        st.plotly_chart(fig, use_container_width=True)

        # Save prediction to history
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
        st.subheader("📈 Health Trends")
        if len(history_df) > 1:
            chart_df = history_df.copy()
            chart_df["Timestamp"] = pd.to_datetime(chart_df["Timestamp"])
            chart_df = chart_df.sort_values("Timestamp")

            fig_trend = go.Figure()
            fig_trend.add_trace(go.Scatter(
                x=chart_df["Timestamp"],
                y=chart_df["Risk (%)"],
                mode="lines+markers",
                name="Risk (%)",
                line=dict(color="dodgerblue", width=3),
                marker=dict(size=6)
            ))

            fig_trend.update_layout(
                title="Risk Percentage Over Time",
                xaxis_title="Date",
                yaxis_title="Risk (%)",
                template="plotly_white"
            )

            st.plotly_chart(fig_trend, use_container_width=True)
        else:
            st.info("Not enough data to display trends yet. Make more predictions to build your history.")