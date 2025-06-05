import streamlit as st
import pandas as pd
import os
from datetime import datetime
from data.base import st_style, head
from supabase_client import supabase
from zoneinfo import ZoneInfo

# Constants
IST = ZoneInfo("Asia/Kolkata")

# Security questions from main.py
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
    st.markdown("### 🕓 Prediction History")
    st.markdown("View and manage all your past prediction records.")

    # Get current user's email for user-specific history file
    user = st.session_state['current_user']
    email = user.get('email')
    if not email:
        st.error("User email not found. Please log in again.")
        return
    
    # Use user-specific history file
    HISTORY_FILE = f"data/prediction_history_{email.replace('@', '_').replace('.', '_')}.csv"

    if os.path.exists(HISTORY_FILE):
        try:
            history_df = pd.read_csv(HISTORY_FILE)
            
            if not history_df.empty:
                # Handle timestamp conversion safely
                if 'Timestamp' in history_df.columns:
                    try:
                        # Ensure timestamps are parsed correctly
                        history_df['Timestamp'] = pd.to_datetime(history_df['Timestamp'], errors='coerce')
                        # Only convert to IST if timestamps are timezone-naive
                        if history_df['Timestamp'].dt.tz is None:
                            history_df['Timestamp'] = history_df['Timestamp'].dt.tz_localize('UTC').dt.tz_convert(IST)
                        else:
                            history_df['Timestamp'] = history_df['Timestamp'].dt.tz_convert(IST)
                    except Exception as e:
                        st.warning(f"Could not process timestamps: {str(e)}. Displaying raw timestamps.")
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
        except Exception as e:
            st.error(f"Failed to load history file: {str(e)}")
    else:
        st.info("No prediction history found yet. Make a prediction to start building history.")

def profile_section():
    st.markdown("### 👤 User Profile")
    st.markdown("View and edit your profile information.")

    user = st.session_state['current_user']
    email = user.get('email')
    if not email:
        st.error("User email not found. Please log in again.")
        return

    user_data = get_user_by_email(email)
    if not user_data:
        st.error("User data not found in database. Please contact support.")
        return

    # Initialize session state for profile fields with defaults
    if 'profile_edit_mode' not in st.session_state:
        st.session_state['profile_edit_mode'] = False
    if 'profile_name' not in st.session_state:
        st.session_state['profile_name'] = user_data.get('name', '')
    if 'profile_age' not in st.session_state:
        st.session_state['profile_age'] = user_data.get('age', 0) or 0
    if 'profile_height' not in st.session_state:
        st.session_state['profile_height'] = user_data.get('height', 0.0) or 0.0
    if 'profile_weight' not in st.session_state:
        st.session_state['profile_weight'] = user_data.get('weight', 0.0) or 0.0
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
            if st.button("Save Changes", key="save_profile"):
                try:
                    # Only update fields that exist in the schema
                    update_data = {"name": st.session_state['profile_name']}
                    # Check if columns exist in schema (optional, based on schema validation)
                    supabase.table("users").update(update_data).eq("email", email).execute()
                    st.session_state['current_user'] = get_user_by_email(email)
                    st.session_state['profile_edit_mode'] = False
                    st.success("Profile updated successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to update profile: {str(e)}. Please ensure the database schema includes required fields.")
        with col2:
            if st.button("Cancel", key="cancel_profile"):
                st.session_state['profile_edit_mode'] = False
                st.session_state['profile_name'] = user_data.get('name', '')
                st.session_state['profile_age'] = user_data.get('age', 0) or 0
                st.session_state['profile_height'] = user_data.get('height', 0.0) or 0.0
                st.session_state['profile_weight'] = user_data.get('weight', 0.0) or 0.0
                st.session_state['profile_username'] = user_data.get('username', user_data.get('email', ''))
                st.rerun()

def security_section():
    st.markdown("### 🔒 Security Settings")
    st.markdown("Manage your password and security questions.")

    user = st.session_state['current_user']
    email = user.get('email')
    if not email:
        st.error("User email not found. Please log in again.")
        return

    user_data = get_user_by_email(email)
    if not user_data:
        st.error("User data not found in database. Please contact support.")
        return

    # Initialize session state for security settings
    if 'security_password_verified' not in st.session_state:
        st.session_state['security_password_verified'] = False
    if 'security_edit_mode' not in st.session_state:
        st.session_state['security_edit_mode'] = False
    if 'security_questions' not in st.session_state:
        st.session_state['security_questions'] = list(user_data.get('security_questions', {}).keys())
    if 'security_answers' not in st.session_state:
        st.session_state['security_answers'] = list(user_data.get('security_questions', {}).values())

    if not st.session_state['security_password_verified']:
        st.subheader("Verify Current Password")
        current_password = st.text_input("Enter Current Password", type="password", key="verify_current_password")
        if st.button("Verify Password", key="verify_password"):
            if current_password == user_data['password']:
                st.session_state['security_password_verified'] = True
                st.success("Password verified successfully!")
                st.rerun()
            else:
                st.error("Incorrect password. Please try again.")
    else:
        st.subheader("Security Options")
        option = st.radio("Choose an action:", ["Change Password", "Update Security Questions"], key="security_option")

        if option == "Change Password":
            st.subheader("Change Password")
            new_password = st.text_input("New Password", type="password", key="new_password")
            confirm_password = st.text_input("Confirm New Password", type="password", key="confirm_password")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("Save Password", key="save_password"):
                    if not new_password:
                        st.error("Please enter a new password.")
                        return
                    if new_password != confirm_password:
                        st.error("New passwords do not match.")
                        return
                    try:
                        supabase.table("users").update({"password": new_password}).eq("email", email).execute()
                        st.session_state['current_user'] = get_user_by_email(email)
                        st.session_state['security_password_verified'] = False
                        st.success("Password updated successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to update password: {str(e)}")
            with col2:
                if st.button("Cancel", key="cancel_password"):
                    st.session_state['security_password_verified'] = False
                    st.rerun()

        elif option == "Update Security Questions":
            st.subheader("Update Security Questions")
            st.markdown("Select exactly 5 security questions:")
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
                    ans = st.text_input(f"Answer for: {q}", key=f"new_answer_{i}_security")
                    new_answers.append(ans)
            else:
                st.info("Please select exactly 5 security questions.")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("Save Security Questions", key="save_questions"):
                    if len(new_questions) != 5:
                        st.error("You must select exactly 5 security questions.")
                        return
                    if any(not a.strip() for a in new_answers):
                        st.error("Please answer all selected security questions.")
                        return
                    try:
                        supabase.table("users").update({
                            "security_questions": dict(zip(new_questions, new_answers))
                        }).eq("email", email).execute()
                        st.session_state['current_user'] = get_user_by_email(email)
                        st.session_state['security_password_verified'] = False
                        st.session_state['security_questions'] = new_questions
                        st.session_state['security_answers'] = new_answers
                        st.success("Security questions updated successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to update security questions: {str(e)}")
            with col2:
                if st.button("Cancel", key="cancel_questions"):
                    st.session_state['security_password_verified'] = False
                    st.session_state['security_questions'] = list(user_data.get('security_questions', {}).keys())
                    st.session_state['security_answers'] = list(user_data.get('security_questions', {}).values())
                    st.rerun()

def app():
    st.markdown(st_style, unsafe_allow_html=True)
    st.markdown(head, unsafe_allow_html=True)

    st.title("⚙️ Settings")
    st.markdown("Manage your prediction history, profile, and security settings.")

    tabs = st.tabs(["History", "Profile", "Security"])
    
    with tabs[0]:
        history_section()
    with tabs[1]:
        profile_section()
    with tabs[2]:
        security_section()