import pandas as pd
import mysql.connector
from mysql.connector import Error
import re
import logging
from settings import connection_parmeters


# Configure logging
logging.basicConfig(
    filename='../Logs/STCA_table.log',  # Log file name
    level=logging.DEBUG,          # Minimum log level
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def dms_to_decimal(dms):
    """Convert DMS (Degrees, Minutes, Seconds) to Decimal Degrees."""
    try:
        dms = dms.strip()
        if dms[0] == '0':
            dms = dms[1:]
        degrees = int(dms[:2])
        minutes = int(dms[2:4])
        seconds = int(dms[4:6])
        direction = dms[-1]

        decimal = degrees + minutes / 60 + seconds / 3600
        if direction in ['S', 'W']:
            decimal = -decimal

        return decimal
    except (ValueError, IndexError) as e:
        logging.error(f"Error in dms_to_decimal with value: {dms}. Error: {e}")
        return None


def calculate_midpoint(coords):
    """Calculate the geographic midpoint of coordinates."""
    try:
        latitudes = [lat for lat, lon in coords if lat is not None]
        longitudes = [lon for lat, lon in coords if lon is not None]

        if len(latitudes) < 2 or len(longitudes) < 2:
            raise ValueError("Not enough valid coordinates to calculate midpoint.")

        mid_lat = sum(latitudes) / len(latitudes)
        mid_lon = sum(longitudes) / len(longitudes)

        return mid_lat, mid_lon
    except Exception as e:
        logging.error(f"Error in calculate_midpoint: {e}")
        return None, None


def extract_coordinates(df):
    """Extract coordinates based on STCA-ID, DATE, and N."""
    grouped = df.groupby(['STCA-ID', 'DATE', 'N'])
    results = []

    for (stca_id, date, n), group in grouped:
        vi_coords = []
        end_coords = []
        date_time_vi = []

        for index, row in group.iterrows():
            status = row.get('Status')

            try:
                lat1 = dms_to_decimal(row.get('Latitude_TR1'))
                lon1 = dms_to_decimal(row.get('Longitude_TR1'))
                lat2 = dms_to_decimal(row.get('Latitude_TR2'))
                lon2 = dms_to_decimal(row.get('Longitude_TR2'))

                if status == 'VI':
                    date_time_vi.append((row.get('DATE'), row.get('TIME')))
                    vi_coords.extend([(lat1, lon1), (lat2, lon2)])
                elif status == 'END':
                    end_coords.extend([(lat1, lon1), (lat2, lon2)])
            except Exception as e:
                print(f"Error processing row {index}: {row}, Error: {e}")
                logging.error(f"Error processing row {index}: {row}, Error: {e}")

        if len(vi_coords) == 2 and len(end_coords) == 2 and date_time_vi:
            all_coords = vi_coords + end_coords
            midpoint = calculate_midpoint(all_coords)
            if midpoint:
                for index, row in group.iterrows():
                    results.append({
                        'Date': date,
                        'Time': row.get('TIME'),
                        'STCA-ID': str(stca_id),
                        'Callsign/SSR_Tr1': str(row.get("Callsign/SSR_Tr1")),
                        'Sector_Tr1': str(row.get("Sector_Tr1")),
                        'Altitude_Tr1': str(row.get("Altitude_Tr1")),
                        'Callsign/SSR_Tr2': str(row.get("Callsign/SSR_Tr2")),
                        'Sector_Tr2': str(row.get("Sector_Tr2")),
                        'Altitude_Tr2': str(row.get("Altitude_Tr2")),
                        'Midpoint Latitude': midpoint[0],
                        'Midpoint Longitude': midpoint[1],
                        'Status': str(row.get("Status")),
                        'number_of_callsign': row['number_of_callsign']
                    })

    logging.info(f"Extracted {len(results)} results.")
    print(f"Extracted {len(results)} results.")
    return results


# Load the Excel file
file_path = 'sourse_file.xlsx'  # Update with your file path
df = pd.read_excel(file_path)
print("Excel file loaded successfully.")
logging.info("Excel file loaded successfully.")




# Add the result column based on Callsign lengths
def determine_value(row):
    Callsign_pattern = re.compile(r'^(?=(?:[^A-Z]*[A-Z]){3})(.*)$')
    callsign_1 = str(row['Callsign/SSR_Tr1'])
    callsign_2 = str(row['Callsign/SSR_Tr2'])

    if Callsign_pattern.match(callsign_1) and Callsign_pattern.match(callsign_2):
        return "Real"
    else:
        return "Suspicious"

df['number_of_callsign'] = df.apply(determine_value, axis=1)

# Extract coordinates and results
results = extract_coordinates(df)

# Save results to MySQL database
def connect_to_database():
    """Establish a connection to the MySQL database."""
    try:
        connection = mysql.connector.connect(**connection_parmeters)

        print("Connected to the database successfully.")
        logging.info("Connected to the database successfully.")
        return connection
    except Error as e:
        print(f"Error while connecting to MySQL: {e}")
        logging.error(f"Error while connecting to MySQL: {e}")
        return None


def save_results_to_database(results):
    """Save the processed results to the MySQL database."""
    connection = connect_to_database()
    if not connection:
        return

    try:
        cursor = connection.cursor()

        # Check if the table exists
        cursor.execute("SHOW TABLES LIKE 'STCA_alarms';")
        table_exists = cursor.fetchone()

        if table_exists:
            cursor.execute("DELETE FROM STCA_alarms;")  # Clear existing data

        create_table_query = """
        CREATE TABLE IF NOT EXISTS STCA_alarms (
            id INT AUTO_INCREMENT PRIMARY KEY,
            date DATE NOT NULL,
            time TIME NOT NULL,
            stca_id VARCHAR(255) NOT NULL,
            callsign_1 VARCHAR(255) NOT NULL,
            Sector_Tr1 VARCHAR(255) NOT NULL,
            Altitude_Tr1 VARCHAR(255) NOT NULL,
            callsign_2 VARCHAR(255) NOT NULL,
            Sector_Tr2 VARCHAR(255) NOT NULL,
            Altitude_Tr2 VARCHAR(255) NOT NULL,
            midpoint_latitude FLOAT NOT NULL,
            midpoint_longitude FLOAT NOT NULL,
            Status VARCHAR(255) NOT NULL,
            number_of_callsign VARCHAR(255) NOT NULL
        );
        """
        cursor.execute(create_table_query)

        if results:
            insert_query = """
            INSERT INTO STCA_alarms (date, time, stca_id, callsign_1, Sector_Tr1, Altitude_Tr1, callsign_2, Sector_Tr2, Altitude_Tr2, midpoint_latitude, midpoint_longitude, Status, number_of_callsign)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            for result in results:
                cursor.execute(insert_query, (
                    result['Date'],
                    result['Time'],
                    str(result['STCA-ID']),
                    str(result['Callsign/SSR_Tr1']),
                    str(result['Sector_Tr1']),
                    str(result['Altitude_Tr1']),
                    str(result['Callsign/SSR_Tr2']),
                    str(result['Sector_Tr2']),
                    str(result['Altitude_Tr2']),
                    result['Midpoint Latitude'],
                    result['Midpoint Longitude'],
                    str(result['Status']),
                    result['number_of_callsign']
                ))

            connection.commit()
            print("Results have been saved to the STCA database.")
            logging.info("Results have been saved to the STCA database.")
        else:
            print("No results to insert.")
            logging.warning("No results to insert.")
    except Exception as e:
        print(f"Error saving results to STCA database: {e}")
        logging.error(f"Error saving results to STCA database: {e}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

# Save the results to the database
save_results_to_database(results)
