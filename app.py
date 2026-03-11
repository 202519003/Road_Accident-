import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

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

run = st.sidebar.button("Run")

# -----------------------------
# Base Map
# -----------------------------

m = folium.Map(location=[19.07,72.87], zoom_start=11)

# -----------------------------
# Accident Risk Zones
# -----------------------------

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

# -----------------------------
# Route Line
# -----------------------------

route = []

for _, row in path_data.iterrows():
    route.append([row["latitude"], row["longitude"]])

folium.PolyLine(
    route,
    color="blue",
    weight=5
).add_to(m)

# -----------------------------
# Driver Marker
# -----------------------------

if run:

    start = route[0]

    folium.Marker(
        start,
        icon=folium.Icon(color="blue", icon="car"),
        tooltip="Driver"
    ).add_to(m)

# -----------------------------
# Show Map
# -----------------------------

st_folium(m, width=1200, height=650)
