import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import time
from math import radians, cos, sin, sqrt, atan2

st.set_page_config(layout="wide")

st.title("🚦 Road Accident Analysis and Alert System")

# -----------------------------
# Load Data
# -----------------------------

risk_data = pd.read_csv("data/export_123.csv")
path_data = pd.read_csv("data/driver_path_points.csv")

# -----------------------------
# Sidebar
# -----------------------------

st.sidebar.header("Route Selection")

start_location = st.sidebar.text_input(
    "Start Location",
    "19.085911,72.845561"
)

stop_location = st.sidebar.text_input(
    "Stop Location",
    "19.054065,72.846330"
)

speed = st.sidebar.slider("Simulation Speed (seconds)", 0.2, 2.0, 0.8)

run = st.sidebar.button("Run Simulation")

# -----------------------------
# Distance Function
# -----------------------------

def calculate_distance(lat1, lon1, lat2, lon2):

    R = 6371000

    lat1 = radians(lat1)
    lon1 = radians(lon1)
    lat2 = radians(lat2)
    lon2 = radians(lon2)

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))

    distance = R * c

    return distance


# -----------------------------
# Create Route List
# -----------------------------

route = []

for _, row in path_data.iterrows():
    route.append([row["latitude"], row["longitude"]])


# -----------------------------
# Map Placeholder
# -----------------------------

map_placeholder = st.empty()
alert_placeholder = st.empty()


# -----------------------------
# Initial Map
# -----------------------------

m = folium.Map(location=[19.07,72.87], zoom_start=11)

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
        fill_opacity=0.4,
        popup=row["location"]
    ).add_to(m)

folium.PolyLine(route, color="blue", weight=5).add_to(m)

map_placeholder.write(st_folium(m, width=1200, height=650))


# -----------------------------
# Run Simulation
# -----------------------------

if run:

    for point in route:

        car_lat = point[0]
        car_lon = point[1]

        m = folium.Map(location=[car_lat, car_lon], zoom_start=12)

        # route line
        folium.PolyLine(route, color="blue", weight=5).add_to(m)

        # accident zones
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
                fill_opacity=0.4
            ).add_to(m)

            # -------- ALERT CHECK --------

            distance = calculate_distance(
                car_lat, car_lon,
                row["latitude"], row["longitude"]
            )

            if distance < 500 and distance > 250:

                alert_placeholder.warning(
                    f"⚠ Approaching {row['risk_level']} risk zone near {row['location']}"
                )

            elif distance <= 250:

                alert_placeholder.error(
                    f"🚨 ENTERED {row['risk_level']} RISK ZONE near {row['location']}"
                )

        # car marker
        folium.Marker(
            [car_lat, car_lon],
            icon=folium.Icon(color="blue", icon="car"),
            tooltip="Driver"
        ).add_to(m)

        map_placeholder.write(st_folium(m, width=1200, height=650))

        time.sleep(speed)
