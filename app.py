import streamlit as st
import pandas as pd
import folium
import numpy as np
import time
from geopy.distance import geodesic
from streamlit_folium import st_folium

st.set_page_config(layout="wide")

st.title("🚦 Road Accident Analysis and Alert System")

# -------------------------
# Load Data
# -------------------------

risk_data = pd.read_csv("data/export_123.csv")
path_data = pd.read_csv("data/driver_path_points.csv")

# -------------------------
# Sidebar
# -------------------------

st.sidebar.header("Route Selection")

start_location = st.sidebar.text_input(
    "Start Location",
    "19.085911,72.845561"
)

stop_location = st.sidebar.text_input(
    "Stop Location",
    "19.054065,72.846330"
)

run_button = st.sidebar.button("Run")

# -------------------------
# Smooth Route
# -------------------------

def smooth_route(df, points_between=10):

    smooth = []

    for i in range(len(df)-1):

        lat1 = df.iloc[i]["latitude"]
        lon1 = df.iloc[i]["longitude"]

        lat2 = df.iloc[i+1]["latitude"]
        lon2 = df.iloc[i+1]["longitude"]

        lats = np.linspace(lat1, lat2, points_between)
        lons = np.linspace(lon1, lon2, points_between)

        for j in range(points_between):
            smooth.append([lats[j], lons[j]])

    return smooth


smooth_path = smooth_route(path_data)

# -------------------------
# Default Map
# -------------------------

default_map = folium.Map(
    location=[19.07, 72.87],
    zoom_start=11,
    tiles="OpenStreetMap"
)

st_folium(default_map, width=1100, height=600)

alert_box = st.empty()

# -------------------------
# Simulation
# -------------------------

if run_button:

    previous_zone = None

    for point in smooth_path:

        car_lat, car_lon = point

        m = folium.Map(
            location=[car_lat, car_lon],
            zoom_start=12
        )

        # Route line
        folium.PolyLine(
            smooth_path,
            color="blue",
            weight=5
        ).add_to(m)

        # Risk zones
        for _, row in risk_data.iterrows():

            if row["risk_level"] == "High":
                color = "red"
                radius = 500

            elif row["risk_level"] == "Medium":
                color = "orange"
                radius = 350

            else:
                color = "yellow"
                radius = 250

            folium.Circle(
                location=[row["latitude"], row["longitude"]],
                radius=radius,
                color=color,
                fill=True,
                fill_opacity=0.35
            ).add_to(m)

        # Car marker
        folium.Marker(
            location=[car_lat, car_lon],
            icon=folium.Icon(color="blue", icon="car")
        ).add_to(m)

        # Risk detection
        for _, risk in risk_data.iterrows():

            car_point = (car_lat, car_lon)
            risk_point = (risk["latitude"], risk["longitude"])

            distance = geodesic(car_point, risk_point).meters

            if distance <= 500 and distance > 300:

                alert_box.warning(
                    f"⚠ Approaching risk zone near {risk['location']}"
                )

            elif distance <= 300:

                if previous_zone != risk["location"]:

                    alert_box.error(
                        f"🚨 Entered {risk['risk_level']} risk zone near {risk['location']}"
                    )

                    previous_zone = risk["location"]

            else:

                if previous_zone == risk["location"]:

                    alert_box.success(
                        f"✅ Exited risk zone near {risk['location']}"
                    )

                    previous_zone = None

        st_folium(m, width=1100, height=600)

        time.sleep(0.25)
