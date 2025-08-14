import pandas as pd
import folium
from folium.plugins import HeatMap
from folium.features import DivIcon
import logging
import os
import mysql.connector
from settings import connection_parmeters

# Logging setup
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Logs")
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(log_dir, "map.log"),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(filename)s - %(message)s'
)

def create_map(start_date, end_date, callsign_filter=None, id_filter=None, show_heatmap=True, show_vectors=True):
    try:
        # Connect to MySQL
        conn = mysql.connector.connect(**connection_parmeters)
        df = pd.read_sql("SELECT * FROM midpoints", conn)
        conn.close()

        if df.empty:
            return 0, 0, "No data in the database.", None

        # Convert date column
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df = df.dropna(subset=['date'])

        # Convert input dates
        start_dt = pd.to_datetime(start_date, errors='coerce')
        end_dt = pd.to_datetime(end_date, errors='coerce')
        if pd.isna(start_dt) or pd.isna(end_dt):
            return 0, 0, "Invalid start or end date.", None
        if start_dt > end_dt:
            return 0, 0, "Start date cannot be after end date.", None

        # Filter by date range
        filtered_df = df[(df['date'] >= start_dt) & (df['date'] <= end_dt)]

        # Filter by callsign
        if callsign_filter == "Real":
            filtered_df = filtered_df[filtered_df['number_of_callsign'] == "Real"]
        elif callsign_filter == "Suspicious":
            filtered_df = filtered_df[filtered_df['number_of_callsign'] == "Suspicious"]

        # Filter by STCA ID / callsign
        if id_filter:
            filtered_df = filtered_df[
                (filtered_df['callsign_1'].str.strip() == str(id_filter)) |
                (filtered_df['callsign_2'].str.strip() == str(id_filter))
            ]

        if filtered_df.empty:
            return 0, 0, "No data found for selected filters and date range.", None

        # Calculate percentages
        total_count = len(filtered_df)
        real_count = len(filtered_df[filtered_df['number_of_callsign'] == "Real"])
        suspicious_count = len(filtered_df[filtered_df['number_of_callsign'] == "Suspicious"])
        real_percentage = round(real_count / total_count * 100, 2)
        suspicious_percentage = round(suspicious_count / total_count * 100, 2)

        # Prepare map
        avg_lat = filtered_df['midpoint_latitude'].mean()
        avg_lon = filtered_df['midpoint_longitude'].mean()
        m = folium.Map(location=[avg_lat, avg_lon], zoom_start=6)

        # Heatmap FeatureGroup
        if show_heatmap:
            heatmap_group = folium.FeatureGroup(name='Heatmap', show=False)
            heat_data = filtered_df[['midpoint_latitude', 'midpoint_longitude']].values.tolist()
            if heat_data:
                HeatMap(heat_data, radius=10).add_to(heatmap_group)
            heatmap_group.add_to(m)

        # Markers FeatureGroup
        markers_group = folium.FeatureGroup(name='Markers')
        for _, row in filtered_df.iterrows():
            icon_color = 'blue' if row['number_of_callsign'] == 'Real' else 'red'
            # Safe time formatting
            try:
                time_str = str(row['time']).split()[-1]
            except:
                time_str = "N/A"

            popup_html = (
                f"<strong>Callsign1:</strong> {row['callsign_1']}<br>"
                f"<strong>Callsign2:</strong> {row['callsign_2']}<br>"
                f"<strong>Date:</strong> {row['date'].strftime('%Y-%m-%d')}<br>"
                f"<strong>Time:</strong> {time_str}<br>"

            )

            folium.Marker(
                location=[row['midpoint_latitude'], row['midpoint_longitude']],
                popup=folium.Popup(popup_html, max_width=300),
                icon=folium.Icon(color=icon_color)
            ).add_to(markers_group)
        markers_group.add_to(m)

        # Vectors FeatureGroup
        if show_vectors:
            vector_layer = folium.FeatureGroup(name='Vectors', show=False)
            for _, row in filtered_df.iterrows():
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

        # Layer control
        folium.LayerControl().add_to(m)

        # Save map
        os.makedirs('Results', exist_ok=True)
        map_file = os.path.join('Results', 'map.html')
        m.save(map_file)

        return real_percentage, suspicious_percentage, None, map_file

    except Exception as e:
        logging.error(f"Error generating map: {e}", exc_info=True)
        return 0, 0, f"Error generating map: {e}", None
