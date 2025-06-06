import streamlit as st
import google.generativeai as genai
from data.base import st_style, head
# Load Gemini API key from .streamlit/secrets.toml
genai.configure(api_key=st.secrets["gemini"]["api_key"])

# Use Gemini Pro model
model = genai.GenerativeModel("models/gemini-1.2-flash")

def app():
    st.markdown(st_style, unsafe_allow_html=True)
    st.markdown(head, unsafe_allow_html=True)

    st.title("A Personal AI Diabetes-Assistance-Bot")
    st.markdown("Ask anything related to **diabetes** and get an AI-powered answer.")

    prompt = st.text_input("🧠 What would you like to know?", placeholder="E.g. What is type 2 diabetes?")

    if st.button("Get Answer"):
        if prompt:
            with st.spinner("Thinking..."):
                try:
                    response = model.generate_content(prompt)
                    st.success(response.text)
                except Exception as e:
                    st.error(f"❌ Something went wrong: {e}")
        else:
            st.warning("Please enter a question first.")
