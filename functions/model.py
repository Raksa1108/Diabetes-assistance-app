# model.py

import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score

# Load dataset
data = pd.read_csv("data/diabetes.csv")

# Define features and target
X = data.drop("Outcome", axis=1)
y = data["Outcome"]

# Split dataset into train and test
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Create and train model
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# Evaluate model
y_pred = model.predict(X_test)
accuracy_result = round(accuracy_score(y_test, y_pred) * 100, 2)

# Save model if needed
# joblib.dump(model, "model/diabetes_model.pkl")
