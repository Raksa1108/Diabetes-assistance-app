# app/shap_waterfall.py

import streamlit as st
import shap
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
from sklearn.inspection import permutation_importance
from loader import model, df  # df = full dataset
from data.base import st_style, head

import numpy as np
# Fix for deprecated np.bool in newer NumPy versions
if not hasattr(np, 'bool'):
    np.bool = bool

def app(input_data=None):
    st.markdown(st_style, unsafe_allow_html=True)
    st.markdown(head, unsafe_allow_html=True)

    st.title("🔍 SHAP Explanation - Why This Prediction?")

    if input_data is None:
        st.warning("No input found. Please make a prediction in the PREDICTION tab first.")
        return

    # Format input
    if isinstance(input_data, dict):
        input_df = pd.DataFrame([input_data])
    elif isinstance(input_data, pd.Series):
        input_df = pd.DataFrame([input_data])
    else:
        input_df = input_data

    st.markdown("### 📥 Your Input Summary:")
    for col in input_df.columns:
        st.write(f"- **{col}**: {input_df[col].values[0]}")
    st.divider()

    # SHAP Waterfall Plot
    st.markdown("### 🔍 SHAP Waterfall Plot (Feature Impact)")
    try:
        X_train = df.drop("Outcome", axis=1)

        explainer = shap.Explainer(model.predict_proba, X_train)
        shap_values = explainer(input_df)

        fig, ax = plt.subplots(figsize=(10, 5))
        shap.plots.waterfall(shap_values[0, :, 1], max_display=10, show=False)
        st.pyplot(fig)

    except Exception as e:
        st.error(f"Error generating SHAP Waterfall plot: {e}")

    # SHAP Explanation
    st.divider()
    st.markdown("### ℹ️ Explanation")
    st.markdown("""
    - 🟡 **Base Value**: Model’s average prediction before considering features  
    - 🔍 **SHAP Values**: Each feature's contribution to the prediction  
    - 📊 **Final Prediction** = Base Value + SHAP Value contributions
    """)

    # Permutation Feature Importance
    st.divider()
    st.markdown("### 📊 Permutation Feature Importance")
    try:
        X = df.drop("Outcome", axis=1)
        y = df["Outcome"]

        result = permutation_importance(model, X, y, n_repeats=5, random_state=42)
        perm_df = pd.DataFrame({
            "Feature": X.columns,
            "Importance": result.importances_mean
        }).sort_values(by="Importance", ascending=False)

        fig = px.bar(
            perm_df,
            y="Feature",
            x="Importance",
            orientation="h",
            title="Feature Importance (Permutation)",
            labels={"Importance": "Importance", "Feature": "Feature"},
            color_discrete_sequence=["#C2185B"]
        )
        fig.update_layout(yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig)

    except Exception as e:
        st.error(f"Could not generate permutation importance chart: {e}")
