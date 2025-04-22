# app/performance.py

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report
from loader import model, df
from data.base import st_style, head, footer

def app():
    st.markdown(st_style, unsafe_allow_html=True)
    st.markdown(head, unsafe_allow_html=True)

    st.title("📊 Model Performance")

    try:
        X = df.drop("Outcome", axis=1)
        y = df["Outcome"]

        # Make predictions
        y_pred = model.predict(X)

        # Accuracy
        accuracy = accuracy_score(y, y_pred)
        st.subheader("✅ Accuracy")
        st.metric("Model Accuracy", f"{accuracy * 100:.2f}%")

        # Confusion Matrix
        st.subheader("🧩 Confusion Matrix")
        cm = confusion_matrix(y, y_pred)
        fig, ax = plt.subplots()
        sns.heatmap(cm, annot=True, fmt="d", cmap="Purples", xticklabels=["No Diabetes", "Diabetes"], yticklabels=["No Diabetes", "Diabetes"])
        ax.set_xlabel("Predicted")
        ax.set_ylabel("Actual")
        st.pyplot(fig)

        # Classification Report
        st.subheader("📋 Classification Report")
        report = classification_report(y, y_pred, output_dict=True)
        st.dataframe(pd.DataFrame(report).transpose(), use_container_width=True)

    except Exception as e:
        st.error(f"An error occurred while computing performance metrics: {e}")

    st.markdown(footer, unsafe_allow_html=True)
