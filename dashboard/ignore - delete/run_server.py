# run_server.py
"""
This is the main entry point for the Flask application.
It imports the Flask app from routes.py and runs it.
"""
from routes import app

if __name__ == '__main__':
    app.run(debug=True, port=5000)
