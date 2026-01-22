#!/usr/bin/env python3
"""
Simple script to run the Flask backend server.
Loads environment variables from .env file if it exists.
"""

import os
from dotenv import load_dotenv

# Try to load .env file if python-dotenv is installed
try:
    load_dotenv()
except ImportError:
    # If python-dotenv is not installed, that's okay
    # Environment variables can be set manually
    pass

# Import and run the app
from app import app

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_ENV") == "development"
    
    print(f"Starting Aeromon backend on port {port}")
    print(f"OpenWeather API Key configured: {bool(os.getenv('OPENWEATHER_API_KEY'))}")
    print(f"Debug mode: {debug}")
    print(f"\nAPI endpoint: http://localhost:{port}/get-routes")
    print(f"Health check: http://localhost:{port}/health\n")
    
    app.run(host="0.0.0.0", port=port, debug=debug)
