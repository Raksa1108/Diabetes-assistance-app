# app/calculation.py

import streamlit as st
from data.base import st_style, head

def app():
    st.markdown(st_style, unsafe_allow_html=True)
    st.markdown(head, unsafe_allow_html=True)

    st.title("🧮 Inputs and Calculations")

    # User selects what they want to calculate
    option = st.selectbox(
        "Choose a calculation:",
        ("Select...", "Body Mass Index (BMI)", "Diabetes Pedigree Function (DPF)")
    )

    # ---------------- BMI Calculator ----------------
    if option == "Body Mass Index (BMI)":
        st.header("📏 Body Mass Index (BMI) Calculator")
        st.markdown("Enter your weight and height to calculate your BMI:")

        weight = st.number_input("🔹 Weight (kg):", min_value=0.0, step=0.1)
        height_cm = st.number_input("🔹 Height (cm):", min_value=0.0, step=0.1)

        if weight > 0 and height_cm > 0:
            height_m = height_cm / 100
            bmi = weight / (height_m ** 2)
            st.success(f"✅ Your BMI is: **{bmi:.2f}**")

            # Show classification
            st.markdown("### 📊 BMI Classification:")
            if bmi < 18.5:
                st.warning("🔸 Underweight")
            elif 18.5 <= bmi < 25:
                st.info("✅ Normal weight")
            elif 25 <= bmi < 30:
                st.warning("🔸 Overweight")
            else:
                st.error("🔺 Obese")
        else:
            st.info("Enter valid height and weight to calculate BMI.")

    # ---------------- DPF Calculator ----------------
    elif option == "Diabetes Pedigree Function (DPF)":
        st.header("🧬 Diabetes Pedigree Function (DPF) Estimate")
        st.markdown("This is a simplified estimate based on family history.")

        # Instead of just totals, collect detailed family info
        relation_options = ["parent", "sibling", "grandparent", "aunt_uncle", "cousin"]
        kinship = {
            "parent": 0.5,
            "sibling": 0.5,
            "grandparent": 0.25,
            "aunt_uncle": 0.25,
            "cousin": 0.125,
        }

        num_relatives = st.number_input(
            "👪 How many relatives do you want to enter?",
            min_value=1, step=1
        )

        family = []
        st.markdown("Enter diabetes status for each relative:")

        for i in range(num_relatives):
            col1, col2 = st.columns(2)
            with col1:
                relation = st.selectbox(
                    f"Relation for relative #{i+1}",
                    relation_options,
                    key=f"relation_{i}"
                )
            with col2:
                diabetic = st.checkbox(f"Diabetic?", key=f"diabetic_{i}")
            family.append({"relation": relation, "diabetic": diabetic})

        # Calculate weighted DPF
        numerator = 0
        denominator = 0
        for member in family:
            coeff = kinship.get(member["relation"], 0)
            numerator += coeff * (1 if member["diabetic"] else 0)
            denominator += coeff

        if denominator > 0:
            dpf = numerator / denominator
            st.success(f"✅ Your calculated Diabetes Pedigree Function is: **{dpf:.3f}**")
        else:
            st.info("Please enter at least one relative.")

        st.markdown("""
            > ℹ️ **Note:**  
            > This calculation uses a weighted average based on genetic relatedness and standard statistical models.
            > For detailed calculation, a whole family history is required; please do consult your doctor.
        """)
