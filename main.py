import streamlit as st
import random
import string
from app import (
    about,
    input,
    shap_waterfall,
    performance,
    history,
    about_diabetes,
    ai_chat,
    diet_tracker,
    calculation
)

# Dummy in-memory user "database"
if 'users' not in st.session_state:
    st.session_state['users'] = {}  # key: email, value: dict with name, password, security_questions

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if 'current_user' not in st.session_state:
    st.session_state['current_user'] = None

if 'forgot_password_stage' not in st.session_state:
    st.session_state['forgot_password_stage'] = 0  # 0: enter email, 1: answer questions, 2: reset password

if 'reset_email' not in st.session_state:
    st.session_state['reset_email'] = None

# List of 10 security questions
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

def signup():
    st.title("🔐 Sign Up")
    name = st.text_input("Name", key="signup_name")
    email = st.text_input("Email", key="signup_email")
    password = st.text_input("Password", type="password", key="signup_password")

    st.markdown("### Choose any 5 security questions and provide your answers:")
    selected_questions = st.multiselect(
        "Select 5 questions",
        options=SECURITY_QUESTIONS,
        key="signup_questions",
        max_selections=5
    )

    answers = []
    if len(selected_questions) == 5:
        for i, question in enumerate(selected_questions):
            answer = st.text_input(f"Answer for: {question}", key=f"answer_{i}")
            answers.append(answer)
    else:
        st.info("Please select exactly 5 questions.")

    if st.button("Sign Up", key="signup_button"):
        if not name or not email or not password:
            st.error("Please fill in all fields.")
            return
        if len(selected_questions) != 5:
            st.error("You must select exactly 5 security questions.")
            return
        if any(a.strip() == "" for a in answers):
            st.error("Please answer all selected security questions.")
            return
        if email in st.session_state['users']:
            st.error("Email already registered. Please login.")
            return
        # Save user info including security questions and answers
        st.session_state['users'][email] = {
            "name": name,
            "password": password,
            "security_questions": dict(zip(selected_questions, answers))
        }
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
        if email not in st.session_state['users']:
            st.error("Email not registered. Please sign up.")
            return
        if st.session_state['users'][email]['password'] != password:
            st.error("Incorrect password.")
            return
        st.session_state['logged_in'] = True
        st.session_state['current_user'] = st.session_state['users'][email]
        st.success(f"Welcome {st.session_state['current_user']['name']}!")
        st.experimental_rerun()

def forgot_password_flow():
    st.title("🔐 Forgot Password")
    if st.button("Back to Login"):
        st.session_state['forgot_password_stage'] = 0
        st.session_state['reset_email'] = None
        st.experimental_rerun()

    # Stage 0: enter email
    if st.session_state['forgot_password_stage'] == 0:
        email = st.text_input("Enter your registered email to proceed")
        if st.button("Next"):
            if email not in st.session_state['users']:
                st.error("This email is not registered.")
            else:
                st.session_state['reset_email'] = email
                st.session_state['forgot_password_stage'] = 1
                st.experimental_rerun()

    # Stage 1: ask 3 security questions
    elif st.session_state['forgot_password_stage'] == 1:
        user = st.session_state['users'][st.session_state['reset_email']]
        sq = user["security_questions"]
        questions = list(sq.keys())
        # pick 3 random questions
        if 'fp_questions' not in st.session_state:
            st.session_state['fp_questions'] = random.sample(questions, 3)

        st.markdown("Answer the following 3 security questions:")
        correct_count = 0
        answers = []
        for i, question in enumerate(st.session_state['fp_questions']):
            ans = st.text_input(question, key=f"fp_answer_{i}")
            answers.append(ans)

        if st.button("Verify Answers"):
            for i, question in enumerate(st.session_state['fp_questions']):
                if answers[i].strip().lower() == sq[question].strip().lower():
                    correct_count += 1
            if correct_count >= 3:
                st.success("Security questions verified! You can reset your password.")
                st.session_state['forgot_password_stage'] = 2
                st.experimental_rerun()
            else:
                st.error("Incorrect answers. Please try again or go back to login.")

    # Stage 2: reset password
    elif st.session_state['forgot_password_stage'] == 2:
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
            st.session_state['users'][email]['password'] = new_password
            st.success("Password changed successfully! Please login.")
            # Reset forgot password flow
            st.session_state['forgot_password_stage'] = 0
            st.session_state['reset_email'] = None
            st.session_state['fp_questions'] = None
            st.experimental_rerun()

        if st.button("Skip Password Change (Login Now)"):
            st.session_state['forgot_password_stage'] = 0
            st.session_state['reset_email'] = None
            st.session_state['fp_questions'] = None
            st.success("You can now login using your existing password.")
            st.experimental_rerun()

def logout():
    st.session_state['logged_in'] = False
    st.session_state['current_user'] = None
    st.success("You have been logged out.")
    st.experimental_rerun()

def show_app_nav():
    user = st.session_state['current_user']
    st.sidebar.write(f"👋 Hello, **{user['name']}**!")
    st.sidebar.markdown("---")
    st.sidebar.title("🔍 Navigation")
    app_mode = st.sidebar.radio("Go to", [
        "HOME",
        "PREDICTION",
        "INPUTS",
        "SHAP WATERFALL",
        "DIET TRACKER",
        "PERFORMANCE",
        "HISTORY",
        "ASK AI",
        "ABOUT DIABETES",
    ])

    if st.sidebar.button("Logout"):
        logout()

    if app_mode == "HOME":
        about.app()

    elif app_mode == "PREDICTION":
        input.app()

    elif app_mode == "INPUTS":
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

# Main program flow

if not st.session_state['logged_in']:
    tabs = st.tabs(["Login", "Sign Up"])
    with tabs[0]:
        login()
    with tabs[1]:
        signup()
else:
    show_app_nav()
