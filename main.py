
from DBM.Insert_to_DBM import run_script
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, make_response, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import pymysql
import logging
import signal
import sys
import os
import pandas as pd
from Map import  create_map

#Get the current script's directory
current_dir = os.path.dirname(os.path.abspath(__file__))  # Get absolute path of the current script
# Navigate one level up (parent directory)

# Now, let's assume you want to go to the 'Logs' folder inside the parent directory
log_dir = os.path.join(current_dir, 'Logs')  # Combine parent directory with 'Logs'
# Define the log filename
log_filename = 'app.log'
# Ensure the directory exists, create it if it doesn't
os.makedirs(log_dir, exist_ok=True)
# Combine the log directory with the log filename to get the full path to the log file
log_file_path = os.path.join(log_dir, log_filename)




# Setting up the logging configuration
logging.basicConfig(
    filename=log_file_path,  # Log file path, platform independent
    level=logging.INFO,      # Minimum log level
    format='%(asctime)s - %(levelname)s - %(filename)s - %(message)s'
)


app = Flask(__name__)

# Ensure pymysql is installed as MySQLdb
pymysql.install_as_MySQLdb()



app.secret_key = os.urandom(24)  # Random secret key for sessions
#app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:zura@localhost/stca'  # Update with your DB credentials
mysql_data = f'mysql://{DB_USER}:{DB_PASSWORD}@localhost/stca'
app.config['SQLALCHEMY_DATABASE_URI'] = mysql_data  # Update with your DB credentials
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

# User Loader for Flask-Login



# Route for the map creation
@app.route('/Results/<path:filename>')
def send_map(filename):
    return send_from_directory('Results', filename)



@app.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    map_file = None
    real_percentage = 0
    suspicious_percentage = 0
    warning_message = None  # Initialize warning message

    # Get cookies (if any)
    upload_status = request.cookies.get('upload_status')
    uploaded_file = request.cookies.get('uploaded_file')

    # Check for upload status and log accordingly
    if upload_status == 'success':
        flash(f"File '{uploaded_file}' uploaded successfully!", 'success')
        logging.info(f"Upload success: File '{uploaded_file}' uploaded successfully.")
    elif upload_status == 'failure':
        flash(f"Error processing file: {uploaded_file}", 'danger')
        logging.error(f"Upload failed: Error processing file '{uploaded_file}'.")

    # Log when the user accesses the /index route
    logging.info(f"User '{current_user.username}' accessed the /index page.")

    if request.method == 'POST':
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        callsign_filter = request.form.get('callsign_filter', 'both')
        id_filter = request.form.get('id_filter', None)  # Capture id_filter from form

        # Log the POST request with the received filters
        logging.info(f"User '{current_user.username}' submitted filter data: start_date={start_date}, end_date={end_date}, callsign_filter={callsign_filter}, id_filter={id_filter}.")

        # Call create_map with id_filter
        real_percentage, suspicious_percentage, warning_message = create_map(
            start_date, end_date, callsign_filter, id_filter
        )

        # Log map generation status
        if warning_message:
            logging.warning(f"Map generation warning for user '{current_user.username}': {warning_message}")
            map_file = None  # Ensure no map is shown when there's a warning
        else:
            logging.info(f"Map generated successfully for user '{current_user.username}'.")
            map_file = 'map.html'  # Just the filename if map is generated

    # Log the map file status (whether a map was generated or not)
    if map_file:
        logging.info(f"Map file '{map_file}' generated and ready for display.")

    # Set cookies and handle map file
    resp = make_response(render_template('index.html', map_file=map_file,
                                         real_percentage=real_percentage,
                                         suspicious_percentage=suspicious_percentage,
                                         warning_message=warning_message))

    if map_file:
        resp.set_cookie('map_file', map_file, max_age=60 * 60 * 24)  # Set map_file cookie (1 day)
        logging.info(f"Cookie set for map file: {map_file}.")

    return resp



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
            session['username'] = username  # Store the username in the session (session cookie)

            resp = make_response(redirect(url_for('index')))
            resp.set_cookie('username', username,
                            max_age=60 * 60 * 24 )  # Manually set cookie for username (expires in 1 days)
            logging.info(f"User '{username}' logged in successfully.")
            return resp
        else:
            flash('Invalid username or password.')
            logging.warning(f"Failed login attempt for username: '{username}'.")

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    username = session.get('username')
    logout_user()
    session.pop('username', None)  # Remove from session
    logging.info(f"User '{username}' logged out successfully.")  # Log logout event
    resp = make_response(redirect(url_for('login')))
    resp.delete_cookie('username')  # Delete the 'username' cookie
    resp.delete_cookie('upload_status')
    resp.delete_cookie('uploaded_file')

    return resp


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

                # Call the run_script function after the file upload
                run_script()  # This will run the external script

                # Process the Excel file using pandas (just an example)
                data = pd.read_excel(file_path)

                # Setting a cookie indicating the successful upload and file name
                resp = make_response(redirect(url_for('index')))
                resp.set_cookie('upload_status', 'success', max_age=60 * 60 * 24)  # Cookie expires in 1 day
                resp.set_cookie('uploaded_file', file.filename, max_age=60 * 60 * 24)  # Save the file name

                logging.info(f"File '{file.filename}' uploaded successfully.")
                #flash('File uploaded successfully!', 'success')

                return resp
            except Exception as e:
                logging.error(f"Error processing file '{file.filename}': {e}")
                flash(f"Error processing file: {e}", 'danger')

                # Set a failure cookie if there's an error
                resp = make_response(redirect(request.url))
                resp.set_cookie('upload_status', 'failure', max_age=60 * 60 * 24)  # Failure cookie
                return resp

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
    app.run(host="0.0.0.0", port=80, debug=False)
