# base.py

st_style = """
<style>
    body {
        background-color: pink;
        color: black;
    }
    .stApp {
        background-color: pink;
        color: black;
    }
    div.block-container {
        padding-top: 1rem;
        color: black;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
"""

footer = """
<style>
.footer {
    position: fixed;
    left: 0;
    bottom: 0;
    width: 100%;
    background-color: rgba(255, 182, 193, 0.2);  /* Light pink background */
    text-align: center;
    padding: 10px;
    font-size: 14px;
    color: black;
}
.footer a {
    color: #ff69b4;  /* Hot pink links */
    text-decoration: none;
}
.footer a:hover {
    text-decoration: underline;
}
</style>
<div class="footer">
    <p>Diabetes Prediction | Data Source: National Institute of Diabetes and Digestive and Kidney Diseases | © 2024 UZNetDev <a href="https://github.com/UznetDev/Diabetes-Prediction.git" target="_blank">GitHub</a></p>
</div>
"""

head = """
<div style="text-align: center; font-size: 40px; font-weight: bold; color: #C2185B; margin-bottom: 20px;">
    🌟 Diabetes Prediction App 🌟
</div>
<div style="text-align: center; font-size: 18px; color: #5D6D7E; margin-bottom: 60px;">
    Harness the power of AI to predict diabetes and provide insights!
</div>
"""

mrk = """
<div style="background-color: {}; 
color: white; 
margin-bottom: 50px;
padding: 10px;
max-width: 300px;
text-align: center;
border-radius: 5px; text-align: center;">
    {}
</div>
"""

# HOME tab content
introduction = """


This app uses an AI model to help predict whether an individual is likely to have diabetes based on medical attributes.

### 🚀 How to Use the App:
1. Go to the **Prediction** tab.
2. Fill in the input form with the required health metrics.
3. Click **Submit** to get your diabetes prediction and probability.
4. View **explanation plots** in the SHAP tab.
5. Check the **Performance** tab to see how the model performs.
6. Use the **History** tab to track your past inputs and predictions.
7. Read up on **About Diabetes** for educational info.

> **Disclaimer:** This is a demo tool for educational purposes. It should not be used as a medical diagnostic tool.
"""

# ABOUT DIABETES tab content
about_diabets = """
## What is diabetes?

**Diabetes** is a chronic health condition that affects how your body turns food into energy. It is characterized by high levels of glucose (sugar) in the blood, which occurs because the body either doesn’t produce enough insulin, doesn’t use insulin effectively, or both.

### **Types of Diabetes**:
1. **Type 1 Diabetes**:
   - An autoimmune condition where the immune system attacks and destroys insulin-producing cells in the pancreas.
   - Typically diagnosed in children and young adults.
   - Requires daily insulin injections to manage blood sugar.

2. **Type 2 Diabetes**:
   - The body becomes resistant to insulin, or the pancreas doesn’t produce enough insulin.
   - Often linked to lifestyle factors like obesity, physical inactivity, and poor diet, but genetics also play a role.
   - Managed through lifestyle changes, medications, and sometimes insulin.

3. **Gestational Diabetes**:
   - Occurs during pregnancy when the body cannot make enough insulin to support the increased demand.
   - Usually resolves after childbirth, but it increases the risk of developing type 2 diabetes later in life.

### **Symptoms of Diabetes**:
- Frequent urination
- Excessive thirst
- Extreme hunger
- Fatigue
- Blurred vision
- Slow-healing wounds
- Unexplained weight loss (especially in type 1 diabetes)

### **Complications of Untreated Diabetes**:
- Heart disease
- Kidney damage
- Vision loss (diabetic retinopathy)
- Nerve damage (diabetic neuropathy)
- Increased risk of infections

### **Management**:
- **Diet**: Eating a balanced diet, avoiding high-sugar foods.
- **Exercise**: Regular physical activity to improve insulin sensitivity.
- **Medications**: Insulin therapy or oral diabetes medications.
- **Monitoring**: Regularly checking blood glucose levels.
"""

warn = """
THANK YOU FOR USING OUR APP!!!!
"""
