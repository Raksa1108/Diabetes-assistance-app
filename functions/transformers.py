# transformers.py

import pandas as pd
from sklearn.preprocessing import StandardScaler
from loader import X

# Initialize a standard scaler
scaler = StandardScaler()

# Fit the scaler on the original features
scaler.fit(X)

def transform_input(input_df):
    """
    Standardizes input data using the same scaler fit on the training data.

    Parameters:
    - input_df: pd.DataFrame containing the same features as training set.

    Returns:
    - pd.DataFrame: Scaled input data.
    """
    input_scaled = scaler.transform(input_df)
    return pd.DataFrame(input_scaled, columns=X.columns)
