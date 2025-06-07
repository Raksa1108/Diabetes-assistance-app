import streamlit as st
import random
from app import about
from app import user_input
from app import shap_waterfall
from app import performance
from app import history
from app import about_diabetes
from app import ai_chat
from app import diet_tracker
from app import calculation
from app import sugar_tracker
from supabase_client import supabase
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if 'current_user' not in st.session_state:
    st.session_state['current_user'] = None

if 'forgot_password_stage' not in st.session_state:
    st.session_state['forgot_password_stage'] = 0

if 'reset_email' not in st.session_state:
    st.session_state['reset_email'] = None

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

def signup():
    st.title("🔐 Sign Up")
    name = st.text_input("Name", key="signup_name")
    email = st.text_input("Email", key="signup_email")
    password = st.text_input("Password", type="password", key="signup_password")

    st.markdown("### Choose exactly 5 security questions and provide your answers:")
    selected_questions = st.multiselect(
        "Select 5 questions",
        options=SECURITY_QUESTIONS,
        key="signup_questions",
        max_selections=5
    )

    answers = []
    if len(selected_questions) == 5:
        for i, q in enumerate(selected_questions):
            ans = st.text_input(f"Answer for: {q}", key=f"answer_{i}")
            answers.append(ans)
    else:
        st.info("Please select exactly 5 security questions.")

    if st.button("Sign Up", key="signup_button"):
        if not name or not email or not password:
            st.error("Please fill in all fields.")
            return
        if len(selected_questions) != 5:
            st.error("You must select exactly 5 security questions.")
            return
        if any(not a.strip() for a in answers):
            st.error("Please answer all selected security questions.")
            return
        if get_user_by_email(email):
            st.error("Email already registered. Please login.")
            return

        supabase.table("users").insert({
            "name": name,
            "email": email,
            "password": password,
            "security_questions": dict(zip(selected_questions, answers))
        }).execute()
        st.success("Sign up successful! Please login.")

def login():
    st.title("🔐 Login")
    email = st.text_input("Email", key="login_email")
    password = st.text_input("Password", type="password", key="login_password")

    forgot_password = st.checkbox("Forgot Password?", key="forgot_check")

    if forgot_password:
        forgot_password_flow()
        return

    if st.button("Login", key="login_button"):
        user = get_user_by_email(email)
        if not user:
            st.error("Email not registered. Please sign up.")
            return
        if user['password'] != password:
            st.error("Incorrect password.")
            return

        st.session_state['logged_in'] = True
        st.session_state['current_user'] = user
        st.success(f"Welcome {user['name']}!")
        st.rerun()  # changed from st.experimental_rerun()

def forgot_password_flow():
    st.title("🔐 Forgot Password")

    if st.button("Back to Login"):
        st.session_state['forgot_password_stage'] = 0
        st.session_state['reset_email'] = None
        st.session_state.pop('fp_questions', None)
        st.rerun()  # changed from st.experimental_rerun()

    stage = st.session_state['forgot_password_stage']

    if stage == 0:
        email = st.text_input("Enter your registered email to proceed")
        if st.button("Next"):
            user = get_user_by_email(email)
            if not user:
                st.error("This email is not registered.")
            else:
                st.session_state['reset_email'] = email
                st.session_state['forgot_password_stage'] = 1
                st.rerun()  # changed from st.experimental_rerun()

    elif stage == 1:
        user = get_user_by_email(st.session_state['reset_email'])
        sq = user["security_questions"]
        questions = list(sq.keys())

        if 'fp_questions' not in st.session_state:
            st.session_state['fp_questions'] = random.sample(questions, 3)

        st.markdown("Answer the following 3 security questions:")
        answers = []
        for i, question in enumerate(st.session_state['fp_questions']):
            ans = st.text_input(question, key=f"fp_answer_{i}")
            answers.append(ans)

        if st.button("Verify Answers"):
            correct = 0
            for i, question in enumerate(st.session_state['fp_questions']):
                if answers[i].strip().lower() == sq[question].strip().lower():
                    correct += 1
            if correct >= 3:
                st.success("Security questions verified! You can reset your password.")
                st.session_state['forgot_password_stage'] = 2
                st.rerun()  # changed from st.experimental_rerun()
            else:
                st.error("Incorrect answers. Please try again or go back to login.")

    elif stage == 2:
        new_password = st.text_input("New Password", type="password", key="new_password")
        confirm_password = st.text_input("Confirm New Password", type="password", key="confirm_password")

        if st.button("Change Password"):
            if not new_password or not confirm_password:
                st.error("Please fill both password fields.")
                return
            if new_password != confirm_password:
                st.error("Passwords do not match.")
                return
            email = st.session_state['reset_email']
            supabase.table("users").update({"password": new_password}).eq("email", email).execute()
            st.success("Password changed successfully! Please login.")
            st.session_state['forgot_password_stage'] = 0
            st.session_state['reset_email'] = None
            st.session_state.pop('fp_questions', None)
            st.rerun()  # changed from st.experimental_rerun()

        if st.button("Skip Password Change (Login Now)"):
            user = get_user_by_email(st.session_state['reset_email'])
            st.session_state['logged_in'] = True
            st.session_state['current_user'] = user
            st.session_state['forgot_password_stage'] = 0
            st.session_state['reset_email'] = None
            st.session_state.pop('fp_questions', None)
            st.success(f"Welcome back, {user['name']}!")
            st.rerun()  # changed from st.experimental_rerun()

def logout():
    st.session_state['logged_in'] = False
    st.session_state['current_user'] = None
    st.success("You have been logged out.")
    st.rerun()  # changed from st.experimental_rerun()

def show_app_nav():
    user = st.session_state['current_user']
    st.sidebar.write(f"👋 Hello, **{user['name']}**!")
    st.sidebar.markdown("---")
    st.sidebar.title("🔍 Navigation")

    app_mode = st.sidebar.radio("Go to", [
        "HOME",
        "PREDICTION",
        "INPUTS CALCULATION",
        "SHAP WATERFALL",
        "DIET TRACKER",
        "SUGAR TRACKER",
        "PERFORMANCE",
        "ASK AI",
        "SETTINGS",
        "ABOUT DIABETES",
    ])

    if st.sidebar.button("Logout"):
        logout()

    if app_mode == "HOME":
        about.app()
    elif app_mode == "PREDICTION":
        user_input.app()
    elif app_mode == "INPUTS CALCULATION":
        calculation.app()
    elif app_mode == "SHAP WATERFALL":
        if 'last_input' in st.session_state:
            shap_waterfall.app(st.session_state['last_input'])
        else:
            shap_waterfall.app(None)
    elif app_mode == "DIET TRACKER":
        diet_tracker.app()
    elif app_mode == "SUGAR TRACKER":  
        sugar_tracker.app()
    elif app_mode == "PERFORMANCE":
        performance.app()
    elif app_mode == "SETTINGS":
        history.app()
    elif app_mode == "ABOUT DIABETES":
        about_diabetes.app()
    elif app_mode == "ASK AI":
        ai_chat.app()

def main():
    if not st.session_state['logged_in']:
        tabs = st.tabs(["Login", "Sign Up"])
        with tabs[0]:
            login()
        with tabs[1]:
            signup()
    else:
        show_app_nav()

if __name__ == "__main__":
    main()
