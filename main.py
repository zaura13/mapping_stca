from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import pymysql
import os
import logging
import pandas as pd  # Ensure pandas is installed for processing Excel files
import signal
import sys

# Configure logging
logging.basicConfig(
    filename='Logs/app.log',  # Log file location
    level=logging.INFO,  # Log level
    format='%(asctime)s - %(levelname)s - %(message)s'
)

app = Flask(__name__)

# Ensure pymysql is installed as MySQLdb
pymysql.install_as_MySQLdb()

# App configuration
app.secret_key = os.urandom(24)  # Random secret key for sessions
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:zura@localhost/stca'  # Update with your DB credentials
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)

# User Model
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)  # Store passwords as plain text
    is_admin = db.Column(db.Boolean, default=False)

# User Loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Routes
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        # Check if the user exists and the password matches (plain text comparison)
        if user and user.password == password:
            login_user(user)
            logging.info(f"User '{username}' logged in successfully.")
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password.')
            logging.warning(f"Failed login attempt for username: '{username}'.")

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/Results/<path:filename>')
def send_map(filename):
    return send_from_directory('Results', filename)

@app.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    map_file = None
    real_percentage = 0
    suspicious_percentage = 0
    warning_message = None

    if request.method == 'POST':
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        callsign_filter = request.form.get('callsign_filter', 'both')

        # Log the selected data range and filter
        logging.info(f"Data range selected: {start_date} to {end_date} with filter: {callsign_filter}")

        # Process map generation here...
        # For example purposes, we will set these values statically:
        real_percentage = 85
        suspicious_percentage = 10
        warning_message = None

        # If no warnings, show the map
        map_file = 'map.html'

    return render_template('index.html', map_file=map_file,
                           real_percentage=real_percentage,
                           suspicious_percentage=suspicious_percentage,
                           warning_message=warning_message)

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_file():
    # Only allow admin users to access the upload page
    if not current_user.is_admin:
        flash("You don't have permission to access this page.", 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)

        file = request.files['file']
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)

        if file and file.filename.endswith('.xlsx'):
            try:
                # Save file
                file_path = os.path.join('DBM', file.filename)
                file.save(file_path)

                # Process the Excel file using pandas (just an example)
                data = pd.read_excel(file_path)

                logging.info(f"File '{file.filename}' uploaded successfully.")
                flash('File uploaded successfully!', 'success')

                return redirect(url_for('index'))
            except Exception as e:
                logging.error(f"Error processing file '{file.filename}': {e}")
                flash(f"Error processing file: {e}", 'danger')
                return redirect(request.url)

        flash('Invalid file type. Please upload an Excel file.', 'warning')
        return redirect(request.url)

# Shutdown handler
def shutdown_handler(signal, frame):
    logging.info("Flask application is shutting down.")
    sys.exit(0)

# Register the shutdown signal handler
signal.signal(signal.SIGINT, shutdown_handler)
signal.signal(signal.SIGTERM, shutdown_handler)

if __name__ == '__main__':
    app.run(host="0.0.0.0",port=80, debug=True)