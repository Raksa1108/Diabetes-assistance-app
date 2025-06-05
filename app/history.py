import streamlit as st
import pandas as pd
from datetime import datetime
from data.base import st_style, head
from supabase_client import supabase
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")

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

    user = st.session_state.get('current_user')
    if not user or not user.get('email'):
        st.error("User email not found. Please log in again.")
        return
    
    email = user['email']

    try:
        response = supabase.table("predictions").select("*").eq("user_email", email).order("timestamp", desc=True).execute()
        history_data = response.data
        if history_data:
            history_df = pd.DataFrame(history_data)
            history_df['timestamp'] = pd.to_datetime(history_df['timestamp']).dt.tz_convert(IST)
            st.dataframe(history_df[['timestamp', 'pregnancies', 'glucose', 'blood_pressure', 'skin_thickness', 'insulin', 'bmi', 'diabetes_pedigree_function', 'age', 'risk_percent', 'prediction']], use_container_width=True)

            csv = history_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download History as CSV",
                data=csv,
                file_name="prediction_history.csv",
                mime="text/csv"
            )

            if st.button("🗑️ Clear History"):
                supabase.table("predictions").delete().eq("user_email", email).execute()
                st.success("✅ Prediction history cleared successfully.")
                st.rerun()
        else:
            st.info("No prediction history found yet. Make a prediction to start building history.")
    except Exception as e:
        st.error(f"Failed to load history: {str(e)}")

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
                    update_data = {
                        "name": st.session_state['profile_name'],
                        "age": st.session_state['profile_age'],
                        "height": st.session_state['profile_height'],
                        "weight": st.session_state['profile_weight'],
                        "username": st.session_state['profile_username']
                    }
                    supabase.table("users").update(update_data).eq("email", email).execute()
                    st.session_state['current_user'] = get_user_by_email(email)
                    st.session_state['profile_edit_mode'] = False
                    st.success("Profile updated successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to update profile: {str(e)}")
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
