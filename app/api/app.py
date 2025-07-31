# Flask/Django main application
from flask import Flask
import logging
import os

def create_app():
    """
    Application Factory: Creates and configures an instance of the Flask application.
    """
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    app = Flask(__name__, template_folder='../templates', static_folder='../static')
    
    # Load the secret key from an environment variable.
    # Provide a default value for safety, although it should always be set.
    app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'a_default_secret_key_for_local_dev_only')
    if app.config['SECRET_KEY'] == 'a_default_secret_key_for_local_dev_only':
        logging.warning("SECURITY WARNING: Using default SECRET_KEY. Please set FLASK_SECRET_KEY environment variable.")


    with app.app_context():
        # Import and register the main blueprint
        from . import routes
        app.register_blueprint(routes.main_bp)

        logging.info("Flask application created and blueprint registered.")
        
    return app
