import pandas as pd
import mysql.connector
from settings import connection_parmeters

def fetch_data_from_db():
    """
    Connect to the MySQL database and fetch data.
    """
    # nonlocal connection
    try:
        connection = mysql.connector.connect(**connection_parmeters)

        query = "SELECT `midpoint_latitude`, `midpoint_longitude`, callsign_1,callsign_2,number_of_callsign," \
                "`stca_id`, `date`, TIME_FORMAT(`time`, '%H:%i:%s') AS `time` FROM `midpoints`"  # Adjust the table name
        df = pd.read_sql(query, connection)
        return df
    except mysql.connector.Error as e:
        print(f"Error: {e}")
        return pd.DataFrame()
    finally:
        if connection.is_connected():
            connection.close()


if __name__ == '__main__':
    db_data = fetch_data_from_db()
    print(db_data)