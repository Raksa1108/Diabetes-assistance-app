import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import pickle

# Load datasets
exercise_df = pd.read_csv("datasets/exercise.csv")
calories_df = pd.read_csv("datasets/calories.csv")

# Merge & preprocess
df = pd.merge(exercise_df, calories_df, on="User_ID")
df.drop("User_ID", axis=1, inplace=True)
df["Gender"] = df["Gender"].map({"male": 1, "female": 0})

# Features and label
X = df.drop("Calories", axis=1)
y = df["Calories"]

# Split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Train model
model = RandomForestRegressor(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# Evaluate
y_pred = model.predict(X_test)
print("MAE:", mean_absolute_error(y_test, y_pred))
print("RMSE:", np.sqrt(mean_squared_error(y_test, y_pred)))
print("R²:", r2_score(y_test, y_pred))

# Save model
with open("calories_model.pkl", "wb") as f:
    pickle.dump(model, f)
