import streamlit as st
import pandas as pd
import folium
import time
import numpy as np
from streamlit_folium import st_folium
from geopy.distance import geodesic

# -------------------------------
# PAGE CONFIG
# -------------------------------

st.set_page_config(layout="wide")

# -------------------------------
# HEADER
# -------------------------------

col1, col2 = st.columns([1,6])

with col1:
    st.image("assets/logo.png", width=80)

with col2:
    st.title("Road Accident Analysis and Alert System")

# -------------------------------
# LOAD DATA
# -------------------------------

risk_data = pd.read_csv("data/export_123.csv")
path_data = pd.read_csv("data/driver_path_points.csv")

# -------------------------------
# SIDEBAR USER INPUT
# -------------------------------

st.sidebar.header("Route Selection")

start_name = st.sidebar.text_input("Start Location")
stop_name = st.sidebar.text_input("Stop Location")

run_simulation = st.sidebar.button("Run")

# -------------------------------
# HELPER FUNCTION
# Create smooth path
# -------------------------------

def interpolate_points(lat1, lon1, lat2, lon2, steps=20):

    lat_points = np.linspace(lat1, lat2, steps)
    lon_points = np.linspace(lon1, lon2, steps)

    return list(zip(lat_points, lon_points))


# -------------------------------
# CREATE SMOOTH ROUTE
# -------------------------------

smooth_path = []

for i in range(len(path_data)-1):

    lat1 = path_data.iloc[i]["latitude"]
    lon1 = path_data.iloc[i]["longitude"]

    lat2 = path_data.iloc[i+1]["latitude"]
    lon2 = path_data.iloc[i+1]["longitude"]

    segment = interpolate_points(lat1, lon1, lat2, lon2)

    smooth_path.extend(segment)

# -------------------------------
# CREATE MAP
# -------------------------------

center_lat = path_data["latitude"].mean()
center_lon = path_data["longitude"].mean()

m = folium.Map(
    location=[center_lat, center_lon],
    zoom_start=13,
    tiles="OpenStreetMap"
)

# -------------------------------
# DRAW RISK ZONES
# -------------------------------

for _, row in risk_data.iterrows():

    risk_level = row["risk_level"]

    if risk_level == "High":
        color = "red"
        radius = 500

    elif risk_level == "Medium":
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
        fill_opacity=0.3,
        popup=f"{row['location']} - {risk_level}"
    ).add_to(m)

# -------------------------------
# DRAW ROUTE LINE
# -------------------------------

folium.PolyLine(
    smooth_path,
    color="blue",
    weight=4
).add_to(m)

# -------------------------------
# ALERT PLACEHOLDER
# -------------------------------

alert_box = st.empty()

# -------------------------------
# SIMULATION
# -------------------------------

if run_simulation:

    previous_zone = None

    for point in smooth_path:

        car_lat, car_lon = point

        folium.Marker(
            location=[car_lat, car_lon],
            icon=folium.Icon(color="blue", icon="car")
        ).add_to(m)

        # CHECK RISK ZONES

        for _, risk in risk_data.iterrows():

            risk_point = (risk["latitude"], risk["longitude"])
            car_point = (car_lat, car_lon)

            distance = geodesic(car_point, risk_point).meters

            if distance < 300:

                if previous_zone != risk["location"]:
                    alert_box.error(
                        f"🚨 ENTERED {risk['risk_level']} RISK ZONE near {risk['location']}"
                    )

                previous_zone = risk["location"]

            elif distance < 500:

                alert_box.warning(
                    f"⚠ Approaching Risk Zone (500m) near {risk['location']}"
                )

            else:

                if previous_zone == risk["location"]:
                    alert_box.success(
                        f"✅ Exited Risk Zone near {risk['location']}"
                    )

                    previous_zone = None

        st_folium(m, width=1000, height=600)

        time.sleep(0.4)

else:

    st_folium(m, width=1000, height=600)
