import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt
from datetime import datetime, date, timedelta
import numpy as np
from fpdf import FPDF
from io import BytesIO
import os

# --------- Load datasets ------------
@st.cache_data
def load_datasets():
    try:
        pred_food = pd.read_csv("dataset/pred_food.csv", encoding="ISO-8859-1")
        daily_nutrition = pd.read_csv("dataset/daily_food_nutrition_dataset.csv", encoding="ISO-8859-1")
        indian_food = pd.read_csv("dataset/indian_food.csv", encoding="ISO-8859-1")
        indian_food1 = pd.read_csv("dataset/indian_food_DF.csv", encoding="ISO-8859-1")
        full_nutrition = pd.read_csv("dataset/Nutrition_Dataset.csv", encoding="ISO-8859-1")
        indian_processed = pd.read_csv("dataset/Indian_Food_Nutrition_Processed.csv", encoding="ISO-8859-1")
    except Exception as e:
        st.error(f"Dataset loading failed: {e}")
        return None, None, None, None, None, None

    # DEBUG: Print dataset sizes
    st.write(f"Loaded datasets sizes:")
    st.write(f"pred_food: {len(pred_food)} rows")
    st.write(f"daily_nutrition: {len(daily_nutrition)} rows")
    st.write(f"indian_food: {len(indian_food)} rows")
    st.write(f"indian_food1: {len(indian_food1)} rows")
    st.write(f"full_nutrition: {len(full_nutrition)} rows")
    st.write(f"indian_processed: {len(indian_processed)} rows")

    # DEBUG: Print current working directory and list dataset files
    st.write("Current working directory:", os.getcwd())
    try:
        st.write("Files in dataset folder:", os.listdir("dataset"))
    except Exception as e:
        st.warning(f"Could not list files in 'dataset' folder: {e}")

    return pred_food, daily_nutrition, indian_food, indian_food1, full_nutrition, indian_processed


def merge_datasets(*datasets):
    dfs = []
    for i, df in enumerate(datasets[:-1]):  # first five datasets
        if df is not None:
            df.columns = [col.lower().strip() for col in df.columns]
            # DEBUG: print columns per dataset
            st.write(f"Dataset {i} columns: {df.columns.tolist()}")
            if 'food' in df.columns and 'calories' in df.columns:
                dfs.append(df[['food', 'calories']].copy())
            else:
                st.warning(f"Dataset {i} skipped: missing 'food' or 'calories' columns.")
        else:
            st.warning(f"Dataset {i} is None")

    processed = datasets[-1]
    if processed is not None:
        processed.columns = [col.lower().strip() for col in processed.columns]
        # DEBUG: print columns for processed dataset
        st.write(f"Processed dataset columns: {processed.columns.tolist()}")

        if 'dish name' in processed.columns and 'calories (kcal)' in processed.columns:
            processed['food'] = processed['dish name'].str.lower()
            processed['calories'] = processed['calories (kcal)']
            if 'glycemic index' in processed.columns:
                processed['gi'] = processed['glycemic index']
            else:
                processed['gi'] = "N/A"
            dfs.append(processed[['food', 'calories', 'gi']])
        else:
            st.warning("Processed dataset skipped: missing 'dish name' or 'calories (kcal)' columns.")
    else:
        st.warning("Processed dataset is None")

    if not dfs:
        st.error("No datasets to merge — all are empty or missing required columns.")
        return pd.DataFrame(columns=['food', 'calories', 'gi'])

    combined = pd.concat(dfs, ignore_index=True)
    combined = combined.drop_duplicates(subset='food')
    combined['food'] = combined['food'].str.lower()
    return combined


# ... rest of your functions remain unchanged ...


def app():
    # Load and merge datasets
    pred_food, daily_nutrition, indian_food, indian_food1, full_nutrition, indian_processed = load_datasets()
    food_df = merge_datasets(pred_food, daily_nutrition, indian_food, indian_food1, full_nutrition, indian_processed)

    # DEBUG: check merged dataframe
    st.write(f"Merged dataset has {len(food_df)} unique food items.")
    st.write(food_df.head())

    if 'daily_goal' not in st.session_state:
        st.session_state.daily_goal = 2000
    if 'meal_log' not in st.session_state:
        st.session_state.meal_log = []

    # ... rest of your app code unchanged ...


if __name__ == "__main__":
    app()
