
from create_map import *
from flask import Flask, render_template, request, send_from_directory, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import pymysql
import os
import logging
import signal
import sys

# Configure logging
logging.basicConfig(
    filename='Logs/app.log',  # Log file
    level=logging.INFO,  # Log level
    format='%(asctime)s - %(levelname)s - %(message)s'
)

app = Flask(__name__)


# Ensure pymysql is installed as MySQLdb
pymysql.install_as_MySQLdb()

# Create Flask application
app = Flask(__name__)
app.secret_key = os.urandom(24)  # Strong random secret key
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:zura@localhost/users'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)

# User model
class User(UserMixin, db.Model):
    __tablename__ = 'app_users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)  # Store passwords as plain text

# Configure logging
logging.basicConfig(
    filename='Logs/app.log',  # Log file
    level=logging.INFO,  # Log level
    format='%(asctime)s - %(levelname)s - %(message)s'
)


fetch_data_from_db()
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        # Check if user exists and password matches (plain text comparison)
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
    logout_user()  # Log out the current user
    return redirect(url_for('login'))  # Redirect the user to the login page




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

        real_percentage, suspicious_percentage, warning_message = create_map(start_date, end_date, callsign_filter)

        if warning_message:
            map_file = None  # No map if there's a warning
        else:
            map_file = 'map.html'

    return render_template('index.html', map_file=map_file,
                           real_percentage=real_percentage,
                           suspicious_percentage=suspicious_percentage,
                           warning_message=warning_message)


@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    if 'file' not in request.files:
        print('No file part')
        return redirect(request.url)

    file = request.files['file']

    if file.filename == '':
        print('No selected file')
        return redirect(request.url)

    if file and file.filename.endswith('.xlsx'):
        try:
            # Save the file to a directory (optional)
            file_path = os.path.join('DBM', file.filename)
            file.save(file_path)

            # Process the Excel file using pandas
            data = pd.read_excel(file_path)

            # Do something with the data, e.g., save to the database or process further
            # Example: print the first few rows
            print(data.head())

            print('File uploaded and processed successfully!')
            logging.info(f"File '{file.filename}' uploaded successfully.")
            return redirect(url_for('index'))
        except Exception as e:
            print('Error processing file: ' + str(e))
            logging.error(f"Error processing file '{file.filename}': {e}")
            return redirect(request.url)

    print('Invalid file type. Please upload an Excel file.')
    return redirect(request.url)



def shutdown_handler(signal, frame):
    logging.info("Flask application is shutting down.")
    sys.exit(0)

# Register the shutdown signal handler
signal.signal(signal.SIGINT, shutdown_handler)
signal.signal(signal.SIGTERM, shutdown_handler)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=80, debug=True)