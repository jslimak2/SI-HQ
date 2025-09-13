import os
import sys
from flask import Flask, render_template

app = Flask(__name__, template_folder='dashboard/templates', static_folder='dashboard/static')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/scores')
def scores():
    return render_template('scores.html')

@app.route('/ml')
def ml_dashboard():
    return render_template('ml_dashboard.html')

if __name__ == '__main__':
    print("Starting simple Post9 Sports Investment Platform")
    app.run(debug=True, host='0.0.0.0', port=5000)