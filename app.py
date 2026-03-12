import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from math import radians, cos, sin, sqrt, atan2
import time

# ------------------------------------------------
# PAGE CONFIG
# ------------------------------------------------

st.set_page_config(layout="wide")
st.title("🚦 Road Accident Analysis and Alert System")

alert_box = st.empty()

# ------------------------------------------------
# LOAD DATA
# ------------------------------------------------

risk_data = pd.read_csv("data/export_123.csv")
path_data = pd.read_csv("data/driver_path_points.csv")

route = path_data[["latitude","longitude"]].values.tolist()

# ------------------------------------------------
# SESSION STATE
# ------------------------------------------------

if "index" not in st.session_state:
    st.session_state.index = 0

if "running" not in st.session_state:
    st.session_state.running = False

if "started" not in st.session_state:
    st.session_state.started = False

if "zone_state" not in st.session_state:
    st.session_state.zone_state = {}

# ------------------------------------------------
# SIDEBAR
# ------------------------------------------------

st.sidebar.title("Simulation Controls")

speed = st.sidebar.slider(
    "Simulation Speed",
    0.2,
    2.0,
    0.6
)

st.sidebar.write("Control the vehicle simulation")

# ------------------------------------------------
# CONTROL BUTTONS (MAIN PAGE)
# ------------------------------------------------

col1,col2,col3 = st.columns(3)

with col1:
    if st.button("▶ Start"):
        st.session_state.started = True
        st.session_state.running = True

with col2:
    if st.button("⏸ Stop"):
        st.session_state.running = False

with col3:
    if st.button("🔄 Reset"):
        st.session_state.index = 0
        st.session_state.running = False
        st.session_state.started = False
        st.session_state.zone_state = {}

# ------------------------------------------------
# DISTANCE FUNCTION
# ------------------------------------------------

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

# ------------------------------------------------
# CURRENT DRIVER POSITION
# ------------------------------------------------

index = st.session_state.index

if index >= len(route):
    index = len(route)-1

lat,lon = route[index]

# ------------------------------------------------
# METRICS
# ------------------------------------------------

c1,c2,c3 = st.columns(3)

c1.metric("Driver Position Step",index)
c2.metric("Total Route Points",len(route))
c3.metric("Accident Zones",len(risk_data))

# ------------------------------------------------
# CREATE MAP
# ------------------------------------------------

m = folium.Map(location=[lat,lon],zoom_start=13)

# ROUTE LINE
folium.PolyLine(route,color="blue",weight=5).add_to(m)

# ------------------------------------------------
# ACCIDENT ZONES
# ------------------------------------------------

for i,row in risk_data.iterrows():

    if row["risk_level"]=="High":
        color="red"
    elif row["risk_level"]=="Medium":
        color="orange"
    else:
        color="yellow"

    # BUFFER ZONE
    folium.Circle(
        location=[row["latitude"],row["longitude"]],
        radius=400,
        color=color,
        fill=True,
        fill_opacity=0.25
    ).add_to(m)

    # CENTER MARKER
    folium.Marker(
        location=[row["latitude"],row["longitude"]],
        popup=f"<b>{row['risk_level']} Risk Zone</b>",
        icon=folium.Icon(color=color)
    ).add_to(m)

    # ------------------------------------------------
    # ALERT SYSTEM
    # ------------------------------------------------

    d = distance(lat,lon,row["latitude"],row["longitude"])

    prev_state = st.session_state.zone_state.get(i,"outside")

    if 200 < d <= 400:

        if prev_state != "approaching":
            alert_box.warning(
                f"⚠ Approaching {row['risk_level']} Risk Zone"
            )

        st.session_state.zone_state[i] = "approaching"

    elif d <= 200:

        if prev_state != "inside":
            alert_box.error(
                f"🚨 ENTERED {row['risk_level']} RISK ZONE"
            )

        st.session_state.zone_state[i] = "inside"

    else:

        if prev_state == "inside":
            alert_box.success(
                f"✅ EXITED {row['risk_level']} RISK ZONE"
            )

        st.session_state.zone_state[i] = "outside"

# ------------------------------------------------
# DRIVER MARKER
# ------------------------------------------------

folium.Marker(
    [lat,lon],
    tooltip="Driver Vehicle",
    icon=folium.Icon(color="blue",icon="car")
).add_to(m)

# ------------------------------------------------
# DISPLAY MAP
# ------------------------------------------------

st_folium(m,width=1200,height=650)

# ------------------------------------------------
# SIMULATION ENGINE
# ------------------------------------------------

if st.session_state.started and st.session_state.running:

    time.sleep(speed)

    st.session_state.index += 1

    if st.session_state.index >= len(route):
        st.session_state.running = False

    st.rerun()
