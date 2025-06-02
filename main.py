import streamlit as st
from app import (
    about,
    input,
    shap_waterfall,
    performance,
    history,
    about_diabetes,
    ai_chat,
    diet_tracker,
    calculation  # 👈 Import the calculation module
)

# App setup
st.set_page_config(
    page_title="Diabetes Prediction App",
    page_icon="🌟",
    layout="centered"
)

# Sidebar navigation
st.sidebar.title("🔍 Navigation")
app_mode = st.sidebar.radio("Go to", [
    "HOME",
    "PREDICTION",
    "INPUTS",  # 👈 New nav item
    "SHAP WATERFALL",
    "DIET TRACKER",
    "PERFORMANCE",
    "HISTORY",
    "ASK AI",
    "ABOUT DIABETES"
])

# Page routing
if app_mode == "HOME":
    about.app()

elif app_mode == "PREDICTION":
    input.app()

elif app_mode == "INPUTS":  # 👈 Route for the new nav item
    calculation.app()

elif app_mode == "SHAP WATERFALL":
    if 'last_input' in st.session_state:
        shap_waterfall.app(st.session_state['last_input'])
    else:
        shap_waterfall.app(None)

elif app_mode == "DIET TRACKER":
    diet_tracker.app()

elif app_mode == "PERFORMANCE":
    performance.app()

elif app_mode == "HISTORY":
    history.app()

elif app_mode == "ABOUT DIABETES":
    about_diabetes.app()

elif app_mode == "ASK AI":
    ai_chat.app()
