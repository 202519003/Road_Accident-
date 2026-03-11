# ---------------------------------
# SIMULATION
# ---------------------------------

map_placeholder = st.empty()
alert_box = st.empty()

if run_button:

    previous_zone = None

    for point in smooth_path:

        car_lat, car_lon = point

        # Create fresh map each frame
        m = folium.Map(
            location=[car_lat, car_lon],
            zoom_start=13,
            tiles="OpenStreetMap"
        )

        # Draw route
        folium.PolyLine(
            smooth_path,
            color="blue",
            weight=5
        ).add_to(m)

        # Draw risk zones
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
                fill_opacity=0.3
            ).add_to(m)

        # Car marker
        folium.Marker(
            location=[car_lat, car_lon],
            icon=folium.Icon(color="blue", icon="car")
        ).add_to(m)

        # Check alerts
        for _, risk in risk_data.iterrows():

            car_point = (car_lat, car_lon)
            risk_point = (risk["latitude"], risk["longitude"])

            distance = geodesic(car_point, risk_point).meters

            if distance <= 500 and distance > 300:

                alert_box.warning(
                    f"⚠ Approaching Risk Zone near {risk['location']}"
                )

            elif distance <= 300:

                if previous_zone != risk["location"]:

                    alert_box.error(
                        f"🚨 ENTERED {risk['risk_level']} RISK ZONE near {risk['location']}"
                    )

                    previous_zone = risk["location"]

            else:

                if previous_zone == risk["location"]:

                    alert_box.success(
                        f"✅ Exited Risk Zone near {risk['location']}"
                    )

                    previous_zone = None

        map_placeholder.write(
            st_folium(m, width=1100, height=600)
        )

        time.sleep(0.2)
