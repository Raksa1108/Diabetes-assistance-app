import streamlit as st
from data.base import st_style, head


def app():
    st.markdown(st_style, unsafe_allow_html=True)
    st.markdown(head, unsafe_allow_html=True)

    st.title("👋 Welcome to the Diabetes Prediction App")

    st.markdown("""
    ## 🤖 Powered by AI  
    This application uses a trained machine learning model to predict the likelihood of diabetes based on your medical inputs.

    ---

    ## 📌 How to Use the App

    1. **Go to the PREDICTION tab**  
       Enter your medical information (e.g., glucose level, BMI, age). The app will instantly predict your diabetes risk using AI and show a **donut chart** with the result.

    2. **Explore the SHAP WATERFALL tab**  
       Understand *why* the model made its prediction using **SHAP** explanations and feature importance plots.

    3. **Diet Tracker**
       Log your food meals and also get macronutrient distribution pot.

    4. **Review the HISTORY tab**  
       View and manage all your past predictions in a **tabular format**. You can also **clear** your history.

    5. **Learn in the ABOUT DIABETES tab**  
       Discover more about diabetes, symptoms, prevention, and care.

    ---

    ## ⚠️ Disclaimer
    This app is a demo tool and does **not** provide medical advice.  
    Always consult a medical professional for health-related decisions.

    ---

    ### 💖 Thank you for using our Diabetes Prediction App!
    Stay informed. Stay healthy.
    """)


