import pandas as pd
from sklearn.linear_model import LinearRegression
import numpy as np
import logging

def train_and_predict(symbol, data):
    """
    A simple machine learning model function.

    This function performs a simple linear regression on the fly
    to predict the next closing price based on the recent data points.
    
    Args:
        symbol (str): The stock symbol we are predicting for.
        data (list of dicts): A list of recent data points from MongoDB.

    Returns:
        float: The predicted next closing price.
        float: The latest closing price.
    """
    if not data or len(data) < 10:
        logging.warning(f"[{symbol}] Not enough data to make a prediction. Need at least 10 data points, got {len(data)}.")
        latest_close = data[-1]['close'] if data else 0.0
        return None, latest_close

    # Convert data to a pandas DataFrame
    df = pd.DataFrame(data)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)

    # --- Feature Engineering (Simple) ---
    # We will use a simple time index as our feature.
    df['time_index'] = np.arange(len(df))
    
    # The feature 'X' must be a 2D array-like structure for scikit-learn.
    # We select it with double brackets to create a DataFrame (which is 2D).
    X = df[['time_index']] 
    y = df['close'] # The target 'y' can be a 1D Series.

    # --- Model Training ---
    model = LinearRegression()
    model.fit(X, y)

    # --- Prediction ---
    # Predict the next data point in the sequence. This also needs to be a 2D array.
    # Create the prediction input as a DataFrame with the SAME column name as the training data.
    next_time_index_value = len(df)
    next_time_index_df = pd.DataFrame([[next_time_index_value]], columns=['time_index'])
    prediction = model.predict(next_time_index_df)
    
    latest_close = df['close'].iloc[-1]
    
    logging.info(f"[{symbol}] Prediction successful. Latest Close: {latest_close:.2f}, Predicted Next Close: {prediction[0]:.2f}")

    return prediction[0], latest_close