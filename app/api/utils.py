#Utility functions (e.g., database connections)
import os
import pymongo
import redis
import psycopg2
import logging

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Get database connection details from environment variables
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/realtimedb')
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
POSTGRES_DSN = os.getenv('POSTGRES_DSN', 'postgresql://user:password@localhost:5432/appdb')

# --- Connection Objects ---
# We initialize these as None and connect within the app context
mongo_client = None
redis_client = None
postgres_conn = None

def get_mongo_db():
    """
    Returns a client connection to the MongoDB database specified by MONGO_URI.
    """
    global mongo_client
    if mongo_client is None:
        try:
            mongo_client = pymongo.MongoClient(MONGO_URI)
            # The ismaster command is cheap and does not require auth.
            mongo_client.admin.command('ismaster')
            logging.info("Successfully established a new connection to MongoDB.")
        except pymongo.errors.ConnectionFailure as e:
            logging.error(f"Could not connect to MongoDB: {e}")
            return None
    return mongo_client['realtimedb']

def get_redis_client():
    """
    Returns a client connection to the Redis cache.
    """
    global redis_client
    if redis_client is None:
        try:
            redis_client = redis.from_url(REDIS_URL)
            # Check if the connection is alive
            redis_client.ping()
            logging.info("Successfully established a new connection to Redis.")
        except redis.exceptions.ConnectionError as e:
            logging.error(f"Could not connect to Redis: {e}")
            return None
    return redis_client

def get_postgres_conn():
    """
    Returns a connection to the PostgreSQL database.
    """
    global postgres_conn
    # Check if connection is closed or doesn't exist
    if postgres_conn is None or postgres_conn.closed != 0:
        try:
            postgres_conn = psycopg2.connect(POSTGRES_DSN)
            logging.info("Successfully established a new connection to PostgreSQL.")
        except psycopg2.OperationalError as e:
            logging.error(f"Could not connect to PostgreSQL: {e}")
            return None
    return postgres_conn