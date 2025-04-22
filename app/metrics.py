# app/metrics.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import joblib
from sklearn.metrics import confusion_matrix, classification_report

def app():
    st.title("📈 Model Performance")

    try:
        # Load model and data
        model = joblib.load("datasets/diabetes_model.pkl")
        data = pd.read_csv("notebooks/diabetes.csv")
        X = data.drop('Outcome', axis=1)
        y_true = data['Outcome']
        y_pred = model.predict(X)

        # Classification report
        report = classification_report(y_true, y_pred, output_dict=True)
        st.markdown("#### 🔢 Classification Report")
        st.dataframe(pd.DataFrame(report).transpose(), use_container_width=True)

        # Confusion matrix
        cm = confusion_matrix(y_true, y_pred)
        fig, ax = plt.subplots()
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=['No Diabetes', 'Diabetes'], yticklabels=['No Diabetes', 'Diabetes'])
        ax.set_xlabel("Predicted")
        ax.set_ylabel("Actual")
        ax.set_title("📊 Confusion Matrix")
        st.pyplot(fig)

    except FileNotFoundError as e:
        st.error("Required files not found. Please ensure the model and dataset exist.")
    except Exception as e:
        st.error(f"Something went wrong: {e}")
