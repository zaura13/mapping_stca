import pandas as pd
import folium
from folium.plugins import HeatMap
from DBM.Connect_to_DBM import fetch_data_from_db
import os
fetch_data_from_db()

def convert_lat_lon(lat_str, lon_str):
    try:
        if isinstance(lat_str, str) and isinstance(lon_str, str):
            lat_deg = int(lat_str[:2])
            lat_min = int(lat_str[2:4])
            lat_dir = lat_str[4]
            lat = lat_deg + lat_min / 60
            if lat_dir == 'S':
                lat = -lat

            lon_deg = int(lon_str[:3])
            lon_min = int(lon_str[3:5])
            lon_dir = lon_str[5]
            lon = lon_deg + lon_min / 60
            if lon_dir == 'W':
                lon = -lon
        else:
            lat = float(lat_str)
            lon = float(lon_str)

        return lat, lon
    except Exception as e:
        print(f"Error converting coordinates {lat_str}, {lon_str}: {e}")
        return None, None


def create_map(start_date, end_date, callsign_filter):
    df = fetch_data_from_db()
    warning_message = None  # Initialize warning message

    if not df.empty:
        df.columns = df.columns.str.strip()
        df['date'] = pd.to_datetime(df['date'])
        filtered_df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]

        # Apply the callsign filter
        if callsign_filter == "Real":
            filtered_df = filtered_df[filtered_df['number_of_callsign'] == "Real"]
        elif callsign_filter == "Suspicious":
            filtered_df = filtered_df[filtered_df['number_of_callsign'] == "Suspicious"]

        # Count occurrences
        total_count = len(filtered_df)
        real_count = len(filtered_df[filtered_df['number_of_callsign'] == "Real"])
        suspicious_count = len(filtered_df[filtered_df['number_of_callsign'] == "Suspicious"])

        real_percentage = (real_count / total_count * 100) if total_count > 0 else 0
        suspicious_percentage = (suspicious_count / total_count * 100) if total_count > 0 else 0

        data_list = []
        marker_data = []

        for _, row in filtered_df.iterrows():
            lat_str = row['midpoint_latitude']
            lon_str = row['midpoint_longitude']
            Callsign1 = row.get('callsign_1', '').strip()
            Callsign2 = row.get('callsign_2', '').strip()
            concatenated_callsign = f"{Callsign1} / {Callsign2}" if Callsign1 and Callsign2 else Callsign1 or Callsign2 or 'N/A'

            lat, lon = convert_lat_lon(lat_str, lon_str)
            if lat is not None and lon is not None:
                data_list.append([lat, lon])
                date = row.get('date', 'N/A').strftime('%Y-%m-%d')
                time = row.get('time', 'N/A')

                marker_data.append({
                    'callsign': concatenated_callsign,
                    'latitude': lat,
                    'longitude': lon,
                    'date': date,
                    'time': time,
                    'stca_id': row.get('stca_id', 'Unknown'),
                    "number_of_callsign": row.get("number_of_callsign"),
                })

        map_df = pd.DataFrame(marker_data)

        if not map_df.empty:
            m = folium.Map(location=[map_df['latitude'].mean(), map_df['longitude'].mean()], zoom_start=7)
            heatmap = HeatMap(data_list, radius=10)
            heatmap_layer = folium.FeatureGroup(name='Heatmap')
            heatmap_layer.add_child(heatmap)
            heatmap_layer.add_to(m)

            marker_layer = folium.FeatureGroup(name='Markers')
            for _, row in map_df.iterrows():
                icon = folium.Icon(color='gray')  # Default icon color
                if row.get("number_of_callsign") == "Real":
                    icon = folium.Icon(color='blue', icon='info-sign')
                elif row.get("number_of_callsign") == "Suspicious":
                    icon = folium.Icon(color='red', icon='warning-sign')

                folium.Marker(
                    location=[row['latitude'], row['longitude']],
                    popup=folium.Popup(
                        f"<div style='font-size: 18px;'>"
                        f"<strong>Callsign:</strong> {row['callsign']}<br>"
                        f"<strong>Date:</strong> {row['date']}<br>"
                        f"<strong>Time:</strong> {row['time']}<br>"
                        f"<strong>STCA-ID:</strong> {row['stca_id']}<br>",
                        max_width=300
                    ),
                    icon=icon
                ).add_to(marker_layer)

            marker_layer.add_to(m)
            folium.LayerControl().add_to(m)

            output_file = 'Results/map.html'
            os.makedirs('Results', exist_ok=True)  # Ensure the directory exists
            m.save(output_file)
            print(f"Map has been saved as '{output_file}'.")
        else:
            warning_message = "No data available in the specified date range."

    else:
        warning_message = "No data available to process."

    return real_percentage, suspicious_percentage, warning_message  # Return the percentages and warning
