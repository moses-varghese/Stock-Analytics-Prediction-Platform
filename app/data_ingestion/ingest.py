# This is the content for: /real-time-ml-app/app/data_ingestion/ingest.py

import os
import requests
import pymongo
import time
import threading
import logging
import argparse
from datetime import datetime

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/realtimedb')
API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY')
SYMBOLS = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN']
# We'll run ingestion once a day, so FETCH_INTERVAL is less critical but good for safety
FETCH_INTERVAL_SECONDS = 60 * 60 * 24 # 24 hours

# --- Database Connection ---
def get_db_connection():
    # ... (This function remains unchanged) ...
    while True:
        try:
            client = pymongo.MongoClient(MONGO_URI)
            client.admin.command('ismaster')
            logging.info("Successfully connected to MongoDB.")
            return client['realtimedb']
        except pymongo.errors.ConnectionFailure as e:
            logging.error(f"Could not connect to MongoDB: {e}. Retrying in 5 seconds...")
            time.sleep(5)

# --- NEW: A simple class to act as a mutable counter ---
class RequestCounter:
    def __init__(self):
        self.count = 0
    def increment(self):
        self.count += 1
    def get(self):
        return self.count

# --- NEW: Central API Fetching Function ---
def fetch_alpha_vantage_data(url, symbol, counter):
    """
    Fetches data from the given URL and handles common API errors gracefully.
    Returns the JSON data if successful, otherwise returns None.
    """
    try:
        # Increment the counter for every attempt
        counter.increment()
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        # Check for API rate limit error
        if "Note" in data and "API call frequency" in data["Note"]:
            # Log the number of requests made before hitting the limit
            logging.error(
                f"[{symbol}] Alpha Vantage API rate limit reached after {counter.get()} requests. "
                "Stopping further requests for this cycle."
            )
            return None # Signal that the limit was hit

        # Check for Premium endpoint error
        if "Information" in data and "premium" in data["Information"]:
            logging.warning(f"[{symbol}] This is a premium Alpha Vantage endpoint. Skipping.")
            return None # Signal a premium endpoint was hit

        return data
    except requests.exceptions.RequestException as e:
        logging.error(f"[{symbol}] HTTP Request failed: {e}")
        return None
    except Exception as e:
        logging.error(f"[{symbol}] An unexpected error occurred during data fetch: {e}")
        return None

# --- Data Processing ---
def process_and_save_daily_data(symbol, time_series_data, db):
    """
    Processes daily time series data and upserts it into the database.
    """
    # ... (This function is similar to before, but tailored for daily data) ...
    collection = db[symbol.upper()]
    operations = []

    for date_str, values in time_series_data.items():
        record = {
            '_id': f"{symbol}-{date_str}",
            'symbol': symbol,
            'timestamp': datetime.strptime(date_str, "%Y-%m-%d"),
            'open': float(values['1. open']),
            'high': float(values['2. high']),
            'low': float(values['3. low']),
            'close': float(values['4. close']),
            # 'adjusted_close': float(values['5. adjusted close']),
            'volume': int(values['5. volume'])
        }
        operations.append(pymongo.UpdateOne({'_id': record['_id']}, {'$set': record}, upsert=True))

    if not operations:
        logging.info(f"[{symbol}] No new records to insert.")
        return

    result = collection.bulk_write(operations)
    logging.info(f"[{symbol}] Daily data processed. Upserted: {result.upserted_count}, Matched: {result.matched_count}")


# --- Refactored Ingestion Logic ---
def run_daily_ingestion(symbol, db, counter):
    """
    Runs the full daily ingestion logic for a single symbol.
    """
    logging.info(f"[{symbol}] Starting daily ingestion...")
    # Using TIME_SERIES_DAILY_ADJUSTED for daily data
    # 'outputsize=full' gets up to 20 years of data, but we'll only process recent ones
    url = (
        # f'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED'
        # f'&symbol={symbol}&outputsize=compact&apikey={API_KEY}'
        f'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY'
        f'&symbol={symbol}&outputsize=compact&apikey={API_KEY}'
    )
    
    data = fetch_alpha_vantage_data(url, symbol, counter)
    
    # If fetch failed or hit a limit, data will be None
    if data and "Time Series (Daily)" in data:
        process_and_save_daily_data(symbol, data["Time Series (Daily)"], db)
    else:
        logging.warning(f"[{symbol}] Could not retrieve or process daily data.")
        # If the fetch function returned None, it might be a rate limit error.
        # We can return False to signal the main loop to stop.
        return data is not None
    return True


# --- Main Application Logic ---
def main():
    """
    Main function to orchestrate the data ingestion process.
    This script now runs a daily ingestion cycle.
    """
    if not API_KEY or API_KEY == "YOUR_API_KEY":
        logging.error("Alpha Vantage API key is not set.")
        return

    db = get_db_connection()
    counter = RequestCounter() # Initialize the counter
    
    logging.info("--- Starting Daily Ingestion Cycle ---")
    for symbol in SYMBOLS:
        success = run_daily_ingestion(symbol, db, counter)
        # Be respectful of the API limit (5 calls per minute)
        if not success:
            # If run_daily_ingestion returns False, it means a rate limit was hit.
            break # Exit the loop to stop making more requests.
        time.sleep(15) 
    logging.info("--- Daily Ingestion Cycle Complete ---")
    
    # In a real-world scheduler (like cron), the script would exit here.
    # For our long-running container, we'll make it sleep for 24 hours.
    logging.info(f"--- Daily Ingestion Cycle Complete. Total requests made: {counter.get()} ---")
    logging.info(f"Sleeping for {FETCH_INTERVAL_SECONDS} seconds until next daily run.")
    time.sleep(FETCH_INTERVAL_SECONDS)


if __name__ == "__main__":
    # We no longer need argparse, as the container will just run this daily cycle.
    main()