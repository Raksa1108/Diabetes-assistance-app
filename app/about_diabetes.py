# app/about_diabetes.py

import streamlit as st
from data.base import st_style, head
def app():
    st.markdown(st_style, unsafe_allow_html=True)
    st.markdown(head, unsafe_allow_html=True)

    st.title("💡 About Diabetes")

    st.markdown("""
    ## 🧬 What is Diabetes?
    Diabetes is a **chronic** health condition that affects how your body turns food into energy. It usually involves issues with the hormone insulin and leads to **high blood sugar levels**.

    When you have diabetes, your body either:
    - Doesn’t make enough insulin, or
    - Can’t use insulin properly.

    ---

    ## 🧷 Types of Diabetes

    - **Type 1 Diabetes**: An autoimmune condition. The body destroys insulin-producing cells. Requires insulin injections.
    - **Type 2 Diabetes**: The body becomes resistant to insulin or doesn’t produce enough. Often linked to lifestyle.
    - **Gestational Diabetes**: Develops during pregnancy. Increases risk of type 2 diabetes later in life.

    ---

    ## 🚨 Common Symptoms

    - Frequent urination
    - Excessive thirst
    - Unexplained weight loss
    - Fatigue
    - Blurred vision
    - Slow-healing wounds

    ---

    ## 🛡️ Prevention & Management

    - ✅ Eat a balanced, healthy diet
    - 🏃 Stay physically active
    - 🩺 Monitor blood sugar regularly
    - 💊 Take prescribed medications
    - 🧘 Manage stress and sleep

    > 📌 **Early detection** through tools like this app helps manage or prevent serious complications.

    ---

    ## 🙏 Thank You!
    We hope this tool helped increase your understanding of diabetes and how to manage it.  
    _Stay informed. Stay healthy._

    ---
    """)

