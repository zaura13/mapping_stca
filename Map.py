import logging
import tempfile
import pandas as pd
import folium
from folium.plugins import HeatMap
from folium.features import DivIcon
from DBM.Connect_to_DBM import fetch_data_from_db



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
        logging.error(f"Error converting coordinates {lat_str}, {lon_str}: {e}")
        return None, None


def create_map(start_date, end_date, callsign_filter=None, id_filter=None, show_heatmap=True, show_vectors=True):
    df = fetch_data_from_db()
    warning_message = None  # Initialize warning message
    real_percentage = 0
    suspicious_percentage = 0

    if not df.empty:
        df.columns = df.columns.str.strip()
        df['date'] = pd.to_datetime(df['date'])
        filtered_df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]

        # Apply the callsign filter
        if callsign_filter == "Real":
            filtered_df = filtered_df[filtered_df['number_of_callsign'] == "Real"]
        elif callsign_filter == "Suspicious":
            filtered_df = filtered_df[filtered_df['number_of_callsign'] == "Suspicious"]

        # Apply ID filter (if provided)
        if id_filter:
            filtered_df = filtered_df[
                (filtered_df['callsign_1'].str.strip() == str(id_filter)) |
                (filtered_df['callsign_2'].str.strip() == str(id_filter))
            ]

        # Count occurrences
        total_count = len(filtered_df)
        real_count = len(filtered_df[filtered_df['number_of_callsign'] == "Real"])
        suspicious_count = len(filtered_df[filtered_df['number_of_callsign'] == "Suspicious"])

        real_percentage = (real_count / total_count * 100) if total_count > 0 else 0
        suspicious_percentage = (suspicious_count / total_count * 100) if total_count > 0 else 0

        # Create the list for marker data
        marker_data = []
        data_list = []

        # Process rows and prepare marker data
        for _, row in filtered_df.iterrows():
            lat, lon = convert_lat_lon(row['midpoint_latitude'], row['midpoint_longitude'])
            if lat is not None and lon is not None:
                data_list.append([lat, lon])
                marker_data.append({
                    'latitude': lat,
                    'longitude': lon,
                    'date': row.get('date', 'N/A').strftime('%Y-%m-%d'),
                    'time': row.get('time', 'N/A'),
                    'stca_id': row.get('stca_id', 'Unknown'),
                    'number_of_callsign': row.get("number_of_callsign"),
                    'callsign_1': row.get('callsign_1', ''),
                    'callsign_2': row.get('callsign_2', ''),
                    'vi_tr1_lat': row.get('vi_tr1_lat', None),
                    'vi_tr1_lon': row.get('vi_tr1_lon', None),
                    'end_tr1_lat': row.get('end_tr1_lat', None),
                    'end_tr1_lon': row.get('end_tr1_lon', None),
                    'vi_tr2_lat': row.get('vi_tr2_lat', None),
                    'vi_tr2_lon': row.get('vi_tr2_lon', None),
                    'end_tr2_lat': row.get('end_tr2_lat', None),
                    'end_tr2_lon': row.get('end_tr2_lon', None),
                })

        map_df = pd.DataFrame(marker_data)

        # Create map if there is data
        if not map_df.empty:
            m = folium.Map(location=[map_df['latitude'].mean(), map_df['longitude'].mean()], zoom_start=6)

            # Add heatmap layer if selected
            if show_heatmap and data_list:
                heatmap = HeatMap(data_list, radius=10)
                heatmap_layer = folium.FeatureGroup(name='Heatmap', show=False)
                heatmap_layer.add_child(heatmap)
                heatmap_layer.add_to(m)

            # Add markers to map
            marker_layer = folium.FeatureGroup(name='Markers')
            for _, row in map_df.iterrows():
                icon = folium.Icon(color='gray')  # Default icon
                if row["number_of_callsign"] == "Real":
                    icon = folium.Icon(color='blue', icon='info-sign')
                elif row["number_of_callsign"] == "Suspicious":
                    icon = folium.Icon(color='red', icon='warning-sign')

                folium.Marker(
                    location=[row['latitude'], row['longitude']],
                    popup=folium.Popup(
                        f"<div style='font-size: 18px;'>"
                        f"<strong>Callsign1:</strong> <span style='color:blue;'>{row['callsign_1']}</span><br>"
                        f"<strong>Callsign2:</strong> <span style='color:green;'>{row['callsign_2']}</span><br>"
                        f"<strong>Date:</strong> {row['date']}<br>"
                        f"<strong>Time:</strong> {row['time']}<br>"
                        f"<strong>STCA-ID:</strong> {row['stca_id']}<br>",
                        max_width=300
                    ),
                    icon=icon
                ).add_to(marker_layer)

            marker_layer.add_to(m)

            # Create vector layer if selected
            if show_vectors:
                vector_layer = folium.FeatureGroup(name='Vectors', show=False)
                for _, row in map_df.iterrows():
                    # Add Vector 1 (Blue)
                    if 'vi_tr1_lat' in row and 'vi_tr1_lon' in row and 'end_tr1_lat' in row and 'end_tr1_lon' in row:
                        if pd.notna(row['vi_tr1_lat']) and pd.notna(row['vi_tr1_lon']) and pd.notna(row['end_tr1_lat']) and pd.notna(row['end_tr1_lon']):
                            folium.PolyLine(
                                [[row['vi_tr1_lat'], row['vi_tr1_lon']], [row['end_tr1_lat'], row['end_tr1_lon']]],
                                color="blue", weight=2.5, opacity=1
                            ).add_to(vector_layer)

                            folium.Marker(
                                location=(row['vi_tr1_lat'], row['vi_tr1_lon']),
                                icon=DivIcon(icon_size=(50, 50), icon_anchor=(10, 20), html='<i style="font-size:40px; color:blue;">*</i>')
                            ).add_to(vector_layer)

                    # Add Vector 2 (Green)
                    if 'vi_tr2_lat' in row and 'vi_tr2_lon' in row and 'end_tr2_lat' in row and 'end_tr2_lon' in row:
                        if pd.notna(row['vi_tr2_lat']) and pd.notna(row['vi_tr2_lon']) and pd.notna(row['end_tr2_lat']) and pd.notna(row['end_tr2_lon']):
                            folium.PolyLine(
                                [[row['vi_tr2_lat'], row['vi_tr2_lon']], [row['end_tr2_lat'], row['end_tr2_lon']]],
                                color="green", weight=2.5, opacity=1
                            ).add_to(vector_layer)

                            folium.Marker(
                                location=(row['vi_tr2_lat'], row['vi_tr2_lon']),
                                icon=DivIcon(icon_size=(50, 50), icon_anchor=(10, 20), html='<i style="font-size:40px; color:green;">*</i>')
                            ).add_to(vector_layer)

                vector_layer.add_to(m)

            folium.LayerControl().add_to(m)

            # Write the map to a temporary file instead of storing in session
            with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as temp_file:
                temp_file.write(m._repr_html_().encode())
                map_html_path = temp_file.name

            # Return the map HTML file path and percentages
            return real_percentage, suspicious_percentage, warning_message, map_html_path