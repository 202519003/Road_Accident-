import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from math import radians, cos, sin, sqrt, atan2
import time

st.set_page_config(layout="wide")

st.title("🚦 Road Accident Analysis and Alert System")

# -------------------------
# ALERT BOX
# -------------------------

alert_box = st.empty()

# -------------------------
# Load Data
# -------------------------

risk_data = pd.read_csv("data/export_123.csv")
path_data = pd.read_csv("data/driver_path_points.csv")

route = path_data[["latitude","longitude"]].values.tolist()

# -------------------------
# Session State
# -------------------------

if "index" not in st.session_state:
    st.session_state.index = 0

if "running" not in st.session_state:
    st.session_state.running = False

if "zone_state" not in st.session_state:
    st.session_state.zone_state = {}

# -------------------------
# Sidebar Controls
# -------------------------

st.sidebar.title("Simulation Control")

speed = st.sidebar.slider("Simulation Speed",0.2,2.0,0.8)

if st.sidebar.button("Start"):
    st.session_state.running = True

if st.sidebar.button("Stop"):
    st.session_state.running = False

if st.sidebar.button("Reset"):
    st.session_state.index = 0
    st.session_state.running = False
    st.session_state.zone_state = {}

# -------------------------
# Distance Function
# -------------------------

def distance(lat1,lon1,lat2,lon2):

    R = 6371000

    lat1=radians(lat1)
    lon1=radians(lon1)
    lat2=radians(lat2)
    lon2=radians(lon2)

    dlon=lon2-lon1
    dlat=lat2-lat1

    a=sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
    c=2*atan2(sqrt(a),sqrt(1-a))

    return R*c

# -------------------------
# Current Position
# -------------------------

index = st.session_state.index

if index >= len(route):
    index = len(route)-1

lat,lon = route[index]

# -------------------------
# Create Map
# -------------------------

m = folium.Map(location=[lat,lon],zoom_start=12)

# Draw route
folium.PolyLine(route,color="blue",weight=5).add_to(m)

# -------------------------
# Accident Zones + Alerts
# -------------------------

for i,row in risk_data.iterrows():

    if row["risk_level"]=="High":
        color="red"
    elif row["risk_level"]=="Medium":
        color="orange"
    else:
        color="yellow"

    # Buffer Zone (400m)
    folium.Circle(
        location=[row["latitude"],row["longitude"]],
        radius=400,
        color=color,
        fill=True,
        fill_opacity=0.3
    ).add_to(m)

    # Center Point
    folium.CircleMarker(
        location=[row["latitude"],row["longitude"]],
        radius=7,
        color="black",
        fill=True,
        fill_color=color
    ).add_to(m)

    # -------------------------
    # ALERT SYSTEM
    # -------------------------

    d = distance(lat,lon,row["latitude"],row["longitude"])

    prev_state = st.session_state.zone_state.get(i,"outside")

    if 200 < d <= 400:

        if prev_state != "approaching":
            alert_box.warning(f"⚠ Approaching {row['risk_level']} Risk Zone")

        st.session_state.zone_state[i] = "approaching"

    elif d <= 200:

        if prev_state != "inside":
            alert_box.error(f"🚨 ENTERED {row['risk_level']} RISK ZONE")

        st.session_state.zone_state[i] = "inside"

    else:

        if prev_state == "inside":
            alert_box.success(f"✅ EXITED {row['risk_level']} RISK ZONE")

        st.session_state.zone_state[i] = "outside"

# -------------------------
# Car Marker
# -------------------------

folium.Marker(
    [lat,lon],
    icon=folium.Icon(color="blue",icon="car"),
    tooltip="Driver"
).add_to(m)

# -------------------------
# Show Map
# -------------------------

st_folium(m,width=1200,height=650)

# -------------------------
# Simulation Step
# -------------------------

if st.session_state.running:

    time.sleep(speed)

    st.session_state.index += 1

    if st.session_state.index >= len(route):
        st.session_state.running = False

    st.rerun()
