# loader.py

import pandas as pd
import joblib

# Load the trained model
model = joblib.load("datasets/diabetes_model.pkl")

# Load the dataset
df = pd.read_csv("datasets/diabetes.csv")
