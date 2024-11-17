import pandas as pd
import re
import folium
from folium import Marker, PolyLine
import logging

# Configure logging
logging.basicConfig(
    filename='Logs/Midpoints_table.log',  # Log file name
    level=logging.DEBUG,  # Minimum log level
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def dms_to_decimal(dms):
    """Convert DMS (Degrees, Minutes, Seconds) to Decimal Degrees."""
    try:
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
    except Exception as e:
        print(f"Error in dms_to_decimal: {e} with value: {dms}")
        logging.error(f"Error in dms_to_decimal: {e} with value: {dms}")
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
        print(f"Error in calculate_midpoint: {e}")
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

        # Variables to store the exact coordinates used for TR1 and TR2 for VI and END status
        vi_tr1_coords = None
        vi_tr2_coords = None
        end_tr1_coords = None
        end_tr2_coords = None

        for index, row in group.iterrows():
            status = row.get('Status')

            try:
                # Convert DMS to decimal coordinates
                lat1 = dms_to_decimal(row.get('Latitude_TR1'))
                lon1 = dms_to_decimal(row.get('Longitude_TR1'))
                lat2 = dms_to_decimal(row.get('Latitude_TR2'))
                lon2 = dms_to_decimal(row.get('Longitude_TR2'))

                if status == 'VI':
                    date_time_vi.append((row.get('DATE'), row.get('TIME')))
                    vi_coords.extend([(lat1, lon1), (lat2, lon2)])

                    # Save the exact TR1 and TR2 coordinates for VI status
                    if vi_tr1_coords is None:
                        vi_tr1_coords = (lat1, lon1)
                    if vi_tr2_coords is None:
                        vi_tr2_coords = (lat2, lon2)

                elif status == 'END':
                    end_coords.extend([(lat1, lon1), (lat2, lon2)])

                    # Save the exact TR1 and TR2 coordinates for END status
                    if end_tr1_coords is None:
                        end_tr1_coords = (lat1, lon1)
                    if end_tr2_coords is None:
                        end_tr2_coords = (lat2, lon2)

            except Exception as e:
                logging.error(f"Error processing row {index}: {row}, Error: {e}")

        # Calculate midpoint if both VI coordinates and END coordinates exist
        if len(vi_coords) == 2 and date_time_vi:
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
                        'VI TR1 Latitude': vi_tr1_coords[0] if vi_tr1_coords else None,
                        'VI TR1 Longitude': vi_tr1_coords[1] if vi_tr1_coords else None,
                        'VI TR2 Latitude': vi_tr2_coords[0] if vi_tr2_coords else None,
                        'VI TR2 Longitude': vi_tr2_coords[1] if vi_tr2_coords else None,
                        'END TR1 Latitude': end_tr1_coords[0] if end_tr1_coords else None,
                        'END TR1 Longitude': end_tr1_coords[1] if end_tr1_coords else None,
                        'END TR2 Latitude': end_tr2_coords[0] if end_tr2_coords else None,
                        'END TR2 Longitude': end_tr2_coords[1] if end_tr2_coords else None,
                        'Status': str(row.get("Status")),
                        'number_of_callsign': row['number_of_callsign']
                    })

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

# Filter results to keep only those with Status "VI"
vi_results = [result for result in results if result['Status'] == 'VI']
logging.info(f"Filtered results, found {len(vi_results)} with Status 'VI'.")


# Map visualization
def create_map(results):
    """
    Create a Folium map with two vectors (VI to END) and midpoint marker for each record.

    - Two vectors for each row: VI TR1 to END TR1 and VI TR2 to END TR2.
    - Midpoint as a marker at the center of the vectors.
    """

    m = folium.Map(location=[results[0]['Midpoint Latitude'], results[0]['Midpoint Longitude']], zoom_start=7)

    for result in results:
        # Extracting coordinates
        vi_tr1_lat = result['VI TR1 Latitude']
        vi_tr1_lon = result['VI TR1 Longitude']
        end_tr1_lat = result['END TR1 Latitude']
        end_tr1_lon = result['END TR1 Longitude']
        vi_tr2_lat = result['VI TR2 Latitude']
        vi_tr2_lon = result['VI TR2 Longitude']
        end_tr2_lat = result['END TR2 Latitude']
        end_tr2_lon = result['END TR2 Longitude']

        # Midpoint
        midpoint_lat = result['Midpoint Latitude']
        midpoint_lon = result['Midpoint Longitude']

        # Drawing the two vectors (lines) using PolyLine
        if vi_tr1_lat is not None and vi_tr1_lon is not None and end_tr1_lat is not None and end_tr1_lon is not None:
            folium.PolyLine([(vi_tr1_lat, vi_tr1_lon), (end_tr1_lat, end_tr1_lon)], color="blue", weight=2.5).add_to(m)

        if vi_tr2_lat is not None and vi_tr2_lon is not None and end_tr2_lat is not None and end_tr2_lon is not None:
            folium.PolyLine([(vi_tr2_lat, vi_tr2_lon), (end_tr2_lat, end_tr2_lon)], color="red", weight=2.5).add_to(m)

        # Add a marker at the midpoint
        folium.Marker(
            location=[midpoint_lat, midpoint_lon],
            popup=f"Midpoint: {result['STCA-ID']}",
            icon=folium.Icon(color="green", icon="info-sign")
        ).add_to(m)

    # Add a legend to the map
    legend_html = """
    <div style="position: fixed; bottom: 50px; left: 50px; width: 200px; height: 90px; background-color: white; z-index:9999; font-size:14px; padding: 10px; border-radius: 5px;">
    <b>Vector Legend</b><br>
    <i style="color: blue;">&#x25A0;</i> TR1 Vector<br>
    <i style="color: red;">&#x25A0;</i> TR2 Vector
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    return m


# Create the map and display it
map_instance = create_map(vi_results)

# Save the map to an HTML file
map_instance.save("Results/midpoint_vectors_map.html")
logging.info("Map created and saved as 'midpoint_vectors_map.html'.")
