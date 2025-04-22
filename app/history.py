# app/history.py

import streamlit as st
import pandas as pd
import os
from data.base import st_style, head

# Constants
HISTORY_FILE = "data/prediction_history.csv"

def app():
    st.markdown(st_style, unsafe_allow_html=True)
    st.markdown(head, unsafe_allow_html=True)

    st.title("🕓 Prediction History")
    st.markdown("Here you can view and manage all your past prediction records.")

    if os.path.exists(HISTORY_FILE):
        history_df = pd.read_csv(HISTORY_FILE)
        
        if not history_df.empty:
            st.dataframe(history_df, use_container_width=True)

            # Download as CSV
            csv = history_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download History as CSV",
                data=csv,
                file_name="prediction_history.csv",
                mime="text/csv"
            )

            # Clear history
            if st.button("🗑️ Clear History"):
                os.remove(HISTORY_FILE)
                st.success("✅ Prediction history cleared successfully.")
        else:
            st.info("History file exists but has no records.")
    else:
        st.info("No prediction history found yet. Make a prediction to start building history.")

