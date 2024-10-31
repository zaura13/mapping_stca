import mysql.connector as m
from mysql.connector import errorcode
from datetime import datetime
from settings import connection_parmeters
import mysql.connector



# Database to back up
db = 'stca'

try:
    connection = mysql.connector.connect(**connection_parmeters)
    cursor = connection.cursor()

    # Getting all the table names
    cursor.execute('SHOW TABLES;')
    table_names = [record[0] for record in cursor.fetchall()]

    # Get current date for backup name
    backup_date = datetime.now().strftime('%Y_%m_%d_%H_%M')
    backup_dbname = f"{db}_backup_{backup_date}"

    # Create backup database if it doesn't exist
    try:
        cursor.execute(f'CREATE DATABASE {backup_dbname}')
        print(f"Database {backup_dbname} created.")
    except m.Error as err:
        if err.errno == m.errorcode.ER_DB_CREATE_EXISTS:
            print(f"Database {backup_dbname} already exists.")
        else:
            print(f"Error creating database: {err}")

    cursor.execute(f'USE {backup_dbname}')

    for table_name in table_names:
        try:
            # Create the table in the backup database
            cursor.execute(f'CREATE TABLE {table_name} AS SELECT * FROM {db}.{table_name};')
            print(f"Table {table_name} backed up successfully.")
        except m.Error as err:
            print(f"Error backing up table {table_name}: {err}")

except m.Error as err:
    print(f"Error: {err}")
finally:
    # Close the cursor and connection
    if cursor:
        cursor.close()
    if connection:
        connection.close()
