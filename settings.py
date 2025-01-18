import os
from dotenv import load_dotenv

load_dotenv()

DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
HOST = os.getenv('HOST')
DATABASE = os.getenv('DATABASE')

connection_parmeters = {
    'host':HOST,  # Your host
    'database':DATABASE,  # Your database name
    'user':DB_USER,  # Your MySQL username
    'password':DB_PASSWORD  # Your MySQL password
}