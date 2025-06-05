import streamlit as st
import pandas as pd
import os
from datetime import datetime
from data.base import st_style, head
from supabase_client import supabase
from zoneinfo import ZoneInfo

# Constants
HISTORY_FILE = "data/prediction_history.csv"
IST = ZoneInfo("Asia/Kolkata")

# Security questions from main.py (copied to avoid dependency issues)
SECURITY_QUESTIONS = [
    "What was your childhood nickname?",
    "In what city did you meet your spouse?",
    "What is the name of your favorite childhood friend?",
    "What street did you live on in third grade?",
    "What is your oldest sibling's middle name?",
    "What school did you attend for sixth grade?",
    "What was the name of your first pet?",
    "What is your mother's maiden name?",
    "In what city or town did your mother and father meet?",
    "What was your dream job as a child?"
]

def get_user_by_email(email):
    response = supabase.table("users").select("*").eq("email", email).execute()
    return response.data[0] if response.data else None

def history_section():
    st.markdown(st_style, unsafe_allow_html=True)
    st.markdown(head, unsafe_allow_html=True)

    st.title("🕓 Prediction History")
    st.markdown("Here you can view and manage all your past prediction records.")

    if os.path.exists(HISTORY_FILE):
        history_df = pd.read_csv(HISTORY_FILE)
        
        if not history_df.empty:
            # Convert timestamp to IST if it exists
            if 'Timestamp' in history_df.columns:
                history_df['Timestamp'] = pd.to_datetime(history_df['Timestamp']).dt.tz_convert(IST)
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

def profile_section():
    st.markdown(st_style, unsafe_allow_html=True)
    st.markdown(head, unsafe_allow_html=True)

    st.title("👤 User Profile")
    st.markdown("View and edit your profile information.")

    user = st.session_state['current_user']
    email = user['email']
    user_data = get_user_by_email(email)

    # Initialize session state for profile fields
    if 'profile_edit_mode' not in st.session_state:
        st.session_state['profile_edit_mode'] = False
    if 'profile_name' not in st.session_state:
        st.session_state['profile_name'] = user_data.get('name', '')
    if 'profile_age' not in st.session_state:
        st.session_state['profile_age'] = user_data.get('age', 0)
    if 'profile_height' not in st.session_state:
        st.session_state['profile_height'] = user_data.get('height', 0.0)
    if 'profile_weight' not in st.session_state:
        st.session_state['profile_weight'] = user_data.get('weight', 0.0)
    if 'profile_username' not in st.session_state:
        st.session_state['profile_username'] = user_data.get('username', user_data.get('email', ''))

    if not st.session_state['profile_edit_mode']:
        st.subheader("Profile Information")
        st.write(f"**Name**: {st.session_state['profile_name']}")
        st.write(f"**Age**: {st.session_state['profile_age']}")
        st.write(f"**Height**: {st.session_state['profile_height']} cm")
        st.write(f"**Weight**: {st.session_state['profile_weight']} kg")
        st.write(f"**Username**: {st.session_state['profile_username']}")
        if st.button("Edit Profile"):
            st.session_state['profile_edit_mode'] = True
    else:
        st.subheader("Edit Profile")
        st.session_state['profile_name'] = st.text_input("Name", value=st.session_state['profile_name'], key="edit_name")
        st.session_state['profile_age'] = st.number_input("Age", min_value=0, max_value=150, value=int(st.session_state['profile_age']), key="edit_age")
        st.session_state['profile_height'] = st.number_input("Height (cm)", min_value=0.0, max_value=300.0, value=float(st.session_state['profile_height']), key="edit_height")
        st.session_state['profile_weight'] = st.number_input("Weight (kg)", min_value=0.0, max_value=500.0, value=float(st.session_state['profile_weight']), key="edit_weight")
        st.session_state['profile_username'] = st.text_input("Username", value=st.session_state['profile_username'], key="edit_username")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Save Changes"):
                supabase.table("users").update({
                    "name": st.session_state['profile_name'],
                    "age": st.session_state['profile_age'],
                    "height": st.session_state['profile_height'],
                    "weight": st.session_state['profile_weight'],
                    "username": st.session_state['profile_username']
                }).eq("email", email).execute()
                st.session_state['current_user'] = get_user_by_email(email)
                st.session_state['profile_edit_mode'] = False
                st.success("Profile updated successfully!")
                st.rerun()
        with col2:
            if st.button("Cancel"):
                st.session_state['profile_edit_mode'] = False
                st.session_state['profile_name'] = user_data.get('name', '')
                st.session_state['profile_age'] = user_data.get('age', 0)
                st.session_state['profile_height'] = user_data.get('height', 0.0)
                st.session_state['profile_weight'] = user_data.get('weight', 0.0)
                st.session_state['profile_username'] = user_data.get('username', user_data.get('email', ''))
                st.rerun()

def security_section():
    st.markdown(st_style, unsafe_allow_html=True)
    st.markdown(head, unsafe_allow_html=True)

    st.title("🔒 Security Settings")
    st.markdown("Manage your password and security questions.")

    user = st.session_state['current_user']
    email = user['email']
    user_data = get_user_by_email(email)

    # Initialize session state for security settings
    if 'security_edit_mode' not in st.session_state:
        st.session_state['security_edit_mode'] = False
    if 'security_questions' not in st.session_state:
        st.session_state['security_questions'] = list(user_data.get('security_questions', {}).keys())
    if 'security_answers' not in st.session_state:
        st.session_state['security_answers'] = list(user_data.get('security_questions', {}).values())

    if not st.session_state['security_edit_mode']:
        st.subheader("Current Security Settings")
        st.write("**Security Questions**:")
        for q, a in zip(st.session_state['security_questions'], st.session_state['security_answers']):
            st.write(f"- {q}: {a}")
        if st.button("Edit Security Settings"):
            st.session_state['security_edit_mode'] = True
    else:
        st.subheader("Change Password and Security Questions")
        current_password = st.text_input("Current Password", type="password", key="current_password")
        new_password = st.text_input("New Password", type="password", key="new_password")
        confirm_password = st.text_input("Confirm New Password", type="password", key="confirm_password")

        st.markdown("### Update Security Questions (select exactly 5)")
        new_questions = st.multiselect(
            "Select 5 security questions",
            options=SECURITY_QUESTIONS,
            default=st.session_state['security_questions'],
            key="new_security_questions",
            max_selections=5
        )

        new_answers = []
        if len(new_questions) == 5:
            for i, q in enumerate(new_questions):
                ans = st.text_input(f"Answer for: {q}", key=f"new_answer_{i}")
                new_answers.append(ans)
        else:
            st.info("Please select exactly 5 security questions.")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Save Security Changes"):
                if current_password != user_data['password']:
                    st.error("Current password is incorrect.")
                    return
                if new_password and new_password != confirm_password:
                    st.error("New passwords do not match.")
                    return
                if len(new_questions) != 5:
                    st.error("You must select exactly 5 security questions.")
                    return
                if any(not a.strip() for a in new_answers):
                    st.error("Please answer all selected security questions.")
                    return

                update_data = {}
                if new_password:
                    update_data["password"] = new_password
                update_data["security_questions"] = dict(zip(new_questions, new_answers))

                supabase.table("users").update(update_data).eq("email", email).execute()
                st.session_state['current_user'] = get_user_by_email(email)
                st.session_state['security_edit_mode'] = False
                st.session_state['security_questions'] = new_questions
                st.session_state['security_answers'] = new_answers
                st.success("Security settings updated successfully!")
                st.rerun()
        with col2:
            if st.button("Cancel"):
                st.session_state['security_edit_mode'] = False
                st.session_state['security_questions'] = list(user_data.get('security_questions', {}).keys())
                st.session_state['security_answers'] = list(user_data.get('security_questions', {}).values())
                st.rerun()

def app():
    st.markdown(st_style, unsafe_allow_html=True)
    st.markdown(head, unsafe_allow_html=True)

    st.title("⚙️ Settings")
    st.markdown("Manage your prediction history, profile, and security settings.")

    settings_mode = st.sidebar.radio("Settings Options", ["History", "Profile", "Security"])

    if settings_mode == "History":
        history_section()
    elif settings_mode == "Profile":
        profile_section()
    elif settings_mode == "Security":
        security_section()