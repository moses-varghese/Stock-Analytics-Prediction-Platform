#API endpoints
from flask import Blueprint, jsonify, render_template, current_app
from .utils import get_mongo_db, get_redis_client
from .models import train_and_predict
import json
import logging
import requests
import os

# Create a Blueprint
main_bp = Blueprint('main_bp', __name__)

# --- Configuration ---
# List of stock symbols our app tracks, should match the ingestion service
SYMBOLS = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN']
API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY')

@main_bp.route('/')
def index():
    """
    Serves the main HTML page.
    """
    return render_template('index.html', symbols=SYMBOLS)

@main_bp.route('/predict/<string:symbol>')
def predict(symbol):
    """
    API endpoint to get a prediction for a given stock symbol.
    It first checks for a cached result in Redis. If not found, it
    fetches data from MongoDB, runs the prediction, and caches the result.
    """
    if symbol.upper() not in SYMBOLS:
        return jsonify({"error": "Symbol not tracked"}), 404

    try:
        redis_client = get_redis_client()
        db = get_mongo_db()

        if redis_client:
            # 1. Check cache first
            cached_result = redis_client.get(f'prediction:{symbol}')
            if cached_result:
                logging.info(f"[{symbol}] Found cached prediction.")
                return jsonify(json.loads(cached_result))

        # 2. If not in cache, fetch from DB and predict
        logging.info(f"[{symbol}] No cache. Fetching data from MongoDB.")
        collection = db[symbol.upper()]
        
        # Fetch the most recent 100 data points, sorted by time descending
        recent_data = list(collection.find().sort('timestamp', -1).limit(1000))
        
        if not recent_data:
            return jsonify({"error": "No data available for this symbol yet"}), 404
        
        # The data is descending, so we reverse it for chronological order
        recent_data.reverse()

        # 3. Get prediction from our model
        prediction, latest_close = train_and_predict(symbol.upper(), recent_data)

        if prediction is None:
             return jsonify({
                "symbol": symbol.upper(),
                "latest_close": latest_close,
                "prediction": "Not enough data",
                "recommendation": "Hold"
            })

        # 4. Generate a simple recommendation
        recommendation = "Buy" if prediction > latest_close else "Sell"
        
        result = {
            "symbol": symbol.upper(),
            "latest_close": round(latest_close, 2),
            "prediction": round(prediction, 2),
            "recommendation": recommendation
        }

        # 5. Cache the result in Redis for 60 seconds
        if redis_client:
            redis_client.set(f'prediction:{symbol}', json.dumps(result), ex=60)
            logging.info(f"[{symbol}] Cached new prediction.")

        return jsonify(result)

    except Exception as e:
        logging.error(f"An error occurred in prediction endpoint for {symbol}: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500

@main_bp.route('/chart_data/<string:symbol>')
def chart_data(symbol):
    """
    API endpoint to fetch the last 100 data points for chart visualization.
    """
    if symbol.upper() not in SYMBOLS:
        return jsonify({"error": "Symbol not tracked"}), 404

    try:
        db = get_mongo_db()
        collection = db[symbol.upper()]
        
        # Fetch the most recent 100 data points for the initial chart view
        chart_points = list(collection.find().sort('timestamp', -1).limit(100))
        chart_points.reverse() # Reverse to have them in chronological order

        # Format the data for Chart.js
        labels = [point['timestamp'].strftime('%H:%M:%S') for point in chart_points]
        data = [point['close'] for point in chart_points]

        return jsonify({"labels": labels, "data": data})

    except Exception as e:
        logging.error(f"An error occurred in chart_data endpoint for {symbol}: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500

@main_bp.route('/sentiment/<string:symbol>')
def sentiment(symbol):
    """
    API endpoint to fetch news and sentiment data for a stock.
    """
    try:
        redis_client = get_redis_client()
        
        # Check cache first
        cache_key = f"sentiment:{symbol}"
        if redis_client and redis_client.exists(cache_key):
            logging.info(f"[{symbol}] Found cached sentiment.")
            return jsonify(json.loads(redis_client.get(cache_key)))

        # Fetch from Alpha Vantage
        # Note: The API requires the 'tickers' parameter, not 'symbol'
        url = (
            f'https://www.alphavantage.co/query?function=NEWS_SENTIMENT'
            f'&tickers={symbol}&apikey={API_KEY}'
        )
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        # Cache the result for 1 hour (3600 seconds)
        if redis_client:
            redis_client.set(cache_key, json.dumps(data), ex=3600)
            
        return jsonify(data)

    except Exception as e:
        logging.error(f"An error occurred in sentiment endpoint for {symbol}: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500
