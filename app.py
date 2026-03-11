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

speed = st.sidebar.slider("Simulation Speed",0.2,2.0,0.8)

run = st.sidebar.button("Run Simulation")

# -----------------------------
# Distance Function
# -----------------------------

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

# -----------------------------
# Build Route
# -----------------------------

route=[]

for _,row in path_data.iterrows():
    route.append([row["latitude"],row["longitude"]])

# placeholders
map_placeholder = st.empty()
alert_box = st.empty()

# -----------------------------
# Initial Map
# -----------------------------

m = folium.Map(location=[19.07,72.87], zoom_start=11)

# accident zones
for _,row in risk_data.iterrows():

    if row["risk_level"]=="High":
        color="red"
        radius=500

    elif row["risk_level"]=="Medium":
        color="orange"
        radius=350

    else:
        color="yellow"
        radius=250

    folium.Circle(
        location=[row["latitude"],row["longitude"]],
        radius=radius,
        color=color,
        fill=True,
        fill_opacity=0.4
    ).add_to(m)

# route line
folium.PolyLine(route,color="blue",weight=5).add_to(m)

# show map
with map_placeholder:
    st_folium(m,width=1200,height=650)

# -----------------------------
# Simulation
# -----------------------------

if run:

    for point in route:

        lat = point[0]
        lon = point[1]

        m = folium.Map(location=[lat,lon],zoom_start=12)

        # route
        folium.PolyLine(route,color="blue",weight=5).add_to(m)

        # zones
        for _,row in risk_data.iterrows():

            if row["risk_level"]=="High":
                color="red"
                radius=500
            elif row["risk_level"]=="Medium":
                color="orange"
                radius=350
            else:
                color="yellow"
                radius=250

            folium.Circle(
                location=[row["latitude"],row["longitude"]],
                radius=radius,
                color=color,
                fill=True,
                fill_opacity=0.4
            ).add_to(m)

            # alert system
            d = distance(lat,lon,row["latitude"],row["longitude"])

            if d < 500 and d > 250:
                alert_box.warning(f"⚠ Approaching {row['risk_level']} risk zone")

            elif d <= 250:
                alert_box.error(f"🚨 ENTERED {row['risk_level']} RISK ZONE")

        # car marker
        folium.Marker(
            [lat,lon],
            icon=folium.Icon(color="blue",icon="car"),
            tooltip="Driver"
        ).add_to(m)

        with map_placeholder:
            st_folium(m,width=1200,height=650)

        time.sleep(speed)
