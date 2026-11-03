
import streamlit as st
import streamlit.components.v1 as components
import folium
import requests

from charger import get_charging_stations
from prediction import predict_range, recommend_charging


# ==========================================
# PAGE CONFIGURATION
# ==========================================

st.set_page_config(
    page_title="SmartEV",
    page_icon="🚗",
    layout="wide"
)


# ==========================================
# CITY COORDINATES
# ==========================================

locations = {
    "Chennai": (13.0827, 80.2707),
    "Salem": (11.6643, 78.1460),
    "Bangalore": (12.9716, 77.5946),
    "Coimbatore": (11.0168, 76.9558),
    "Madurai": (9.9252, 78.1198)
}


# ==========================================
# OSRM ROAD ROUTE FUNCTION
# ==========================================

@st.cache_data(ttl=3600, show_spinner=False)
def get_road_route(start_coords, end_coords):

    start_lat, start_lon = start_coords
    end_lat, end_lon = end_coords

    url = (
        "https://router.project-osrm.org/route/v1/driving/"
        f"{start_lon},{start_lat};{end_lon},{end_lat}"
    )

    params = {
        "overview": "full",
        "geometries": "geojson"
    }

    try:
        response = requests.get(
            url,
            params=params,
            timeout=8
        )

        response.raise_for_status()
        data = response.json()

        if data.get("code") == "Ok" and data.get("routes"):
            route = data["routes"][0]

            return (
                route["geometry"]["coordinates"],
                route["distance"] / 1000,
                route["duration"] / 60
            )

        return None, None, None

    except (requests.RequestException, ValueError, KeyError):
        return None, None, None


# ==========================================
# CHARGER COORDINATE VALIDATION
# ==========================================

def get_charger_coordinates(charger):

    latitude = charger.get("latitude")
    longitude = charger.get("longitude")

    if latitude is None or longitude is None:
        return None

    try:
        latitude = float(latitude)
        longitude = float(longitude)

        if not (-90 <= latitude <= 90):
            return None

        if not (-180 <= longitude <= 180):
            return None

        return latitude, longitude

    except (TypeError, ValueError):
        return None


# ==========================================
# TITLE
# ==========================================

st.title("🚗 SmartEV")

st.subheader(
    "Battery-Aware EV Range Prediction & Charging Planner"
)

st.write(
    "Predict EV driving range and explore charging recommendations."
)

st.divider()


# ==========================================
# VEHICLE DETAILS
# ==========================================

st.header("🔋 Vehicle Details")

col1, col2 = st.columns(2)

with col1:
    capacity = st.number_input(
        "Battery Capacity (kWh)",
        min_value=1.0,
        value=40.0,
        step=1.0
    )

    battery = st.slider(
        "Current Battery (%)",
        0,
        100,
        80
    )

with col2:
    soh = st.slider(
        "Battery Health (SOH %)",
        50,
        100,
        90
    )

    efficiency = st.number_input(
        "Base Energy Consumption (kWh/km)",
        min_value=0.01,
        value=0.15,
        step=0.01
    )

st.divider()


# ==========================================
# JOURNEY DETAILS
# ==========================================

st.header("📍 Journey Details")

col3, col4 = st.columns(2)

with col3:
    start_location = st.selectbox(
        "Starting Location",
        list(locations.keys())
    )

destination_options = [
    place for place in locations
    if place != start_location
]

with col4:
    destination = st.selectbox(
        "Destination",
        destination_options
    )

start_coords = locations[start_location]
end_coords = locations[destination]


# ==========================================
# ROAD ROUTE
# ==========================================

st.header("🛣️ Road Route")

with st.spinner("Finding road route..."):
    road_coordinates, road_distance, travel_minutes = (
        get_road_route(start_coords, end_coords)
    )

if road_distance is not None:

    col5, col6 = st.columns(2)

    with col5:
        st.metric(
            "OSRM Road Distance",
            f"{road_distance:.2f} km"
        )

    with col6:
        st.metric(
            "Estimated Travel Time",
            f"{travel_minutes / 60:.2f} hours"
        )

    default_distance = float(round(road_distance, 2))
    st.success("Road route retrieved successfully.")

else:
    st.warning(
        "OSRM route service unavailable. "
        "Please enter the journey distance manually."
    )

    default_distance = 350.0

distance = st.number_input(
    "Journey Distance used for Prediction (km)",
    min_value=1.0,
    value=default_distance,
    step=1.0
)

st.divider()


# ==========================================
# DRIVING CONDITIONS
# ==========================================

st.header("🌦️ Driving Conditions")

col7, col8 = st.columns(2)

with col7:
    traffic = st.slider(
        "Traffic Impact (%)",
        0,
        40,
        10
    )

with col8:
    ac_load = st.slider(
        "AC Load Impact (%)",
        0,
        20,
        5
    )

adjusted_efficiency = efficiency * (
    1 + (traffic + ac_load) / 100
)

st.metric(
    "Adjusted Energy Consumption",
    f"{adjusted_efficiency:.3f} kWh/km"
)

st.caption(
    "Traffic and AC impacts are demo assumptions."
)

st.divider()


# ==========================================
# NEO4J CHARGER LOOKUP
# ==========================================

st.header("🔌 Route Charging Stations")

chargers = []

try:
    with st.spinner("Loading charging stations from Neo4j..."):
        chargers = get_charging_stations(
            start_location,
            destination
        )

    with st.expander("🔍 Charger Query Debug Information"):
        st.write("Starting Location:", start_location)
        st.write("Destination:", destination)
        st.write("Charger Records:", chargers)

    if chargers:
        st.success(
            f"{len(chargers)} charging station record(s) retrieved."
        )

        for charger in chargers:

            st.write(
                "**Charger:**",
                charger.get("name", "Unknown")
            )

            st.write(
                "**Location:**",
                charger.get("location", "Unknown")
            )

            st.write(
                "**Available:**",
                charger.get("available", "Unknown")
            )

            st.write(
                "**Reliability:**",
                charger.get("reliability", "Unknown"),
                "(demo)"
            )

            coords = get_charger_coordinates(charger)

            if coords:
                st.write("**Coordinates:**", coords)
            else:
                st.warning("Charger coordinates unavailable.")

            st.divider()

    else:
        st.warning("No charging stations found for this route.")

except Exception as error:
    chargers = []
    st.error(f"Neo4j Error: {error}")

st.divider()


# ==========================================
# INTERACTIVE MAP
# ==========================================

st.header("🗺️ Interactive Road Route Map")

route_map = folium.Map(
    location=start_coords,
    zoom_start=7,
    control_scale=True
)


# START MARKER

folium.Marker(
    start_coords,
    tooltip=f"Start: {start_location}",
    popup=f"Starting Location: {start_location}",
    icon=folium.Icon(
        color="green",
        icon="play",
        prefix="fa"
    )
).add_to(route_map)


# DESTINATION MARKER

folium.Marker(
    end_coords,
    tooltip=f"Destination: {destination}",
    popup=f"Destination: {destination}",
    icon=folium.Icon(
        color="red",
        icon="flag",
        prefix="fa"
    )
).add_to(route_map)


# ROAD ROUTE

if road_coordinates:

    road_points = [
        [lat, lon]
        for lon, lat in road_coordinates
    ]

    folium.PolyLine(
        road_points,
        color="blue",
        weight=5,
        opacity=0.8,
        tooltip="OSRM road route"
    ).add_to(route_map)

    route_map.fit_bounds(road_points)

else:

    folium.PolyLine(
        [start_coords, end_coords],
        color="gray",
        weight=3,
        dash_array="8",
        tooltip="Demo connection - not a road route"
    ).add_to(route_map)


# CHARGER MARKERS

for charger in chargers:

    station_coords = get_charger_coordinates(charger)

    if station_coords:

        station_name = charger.get(
            "name",
            "Charging Station"
        )

        station_location = charger.get(
            "location",
            "Unknown"
        )

        folium.Marker(
            station_coords,
            tooltip=station_name,
            popup=(
                f"<b>{station_name}</b><br>"
                f"Location: {station_location}<br>"
                f"Available: {charger.get('available')}<br>"
                f"Reliability: {charger.get('reliability')} (demo)"
            ),
            icon=folium.Icon(
                color="orange",
                icon="bolt",
                prefix="fa"
            )
        ).add_to(route_map)


# DISPLAY MAP WITHOUT STREAMLIT-FOLIUM

map_html = route_map.get_root().render()

components.html(
    map_html,
    height=480,
    scrolling=False
)

st.caption(
    "Blue: OSRM road route. Orange: Neo4j charger marker. "
    "Gray dashed: demo connection when road routing is unavailable. "
    "Map supports zoom and movement."
)

st.divider()


# ==========================================
# BATTERY RANGE PREDICTION
# ==========================================

st.header("📊 Battery Range Prediction")

if st.button(
    "🚀 Predict My Journey",
    use_container_width=True
):

    energy, estimated_range = predict_range(
        capacity,
        battery,
        adjusted_efficiency,
        soh
    )

    available_chargers = [
        charger for charger in chargers
        if charger.get("available") is True
    ]

    station_distance = None
    first_charger_name = None

    if available_chargers:

        first_charger = available_chargers[0]

        first_charger_name = first_charger.get(
            "name",
            "Charging Station"
        )

        station_coords = get_charger_coordinates(
            first_charger
        )

        if station_coords:

            with st.spinner(
                "Calculating approximate charger road distance..."
            ):

                _, station_distance, _ = get_road_route(
                    start_coords,
                    station_coords
                )

    charger_distance_valid = (
        station_distance is not None
        and station_distance <= distance
    )

    # PREDICTION RESULTS

    st.divider()
    st.header("📊 Prediction Results")

    col9, col10, col11 = st.columns(3)

    with col9:
        st.metric("Battery Health", f"{soh}%")

    with col10:
        st.metric("Usable Energy", f"{energy:.2f} kWh")

    with col11:
        st.metric("Estimated Range", f"{estimated_range:.2f} km")

    # BATTERY STATUS

    st.subheader("🔋 Battery Status")

    if estimated_range >= distance:

        battery_status = "GREEN"

        st.success(
            "🟢 GREEN — Estimated range covers the destination distance."
        )

    elif (
        charger_distance_valid
        and estimated_range >= station_distance
    ):

        battery_status = "YELLOW"

        st.warning(
            "🟡 YELLOW — Estimated range may reach the selected charger."
        )

    else:

        battery_status = "RED"

        st.error(
            "🔴 RED — Estimated range is insufficient for the destination "
            "or a verified intermediate charger."
        )

    # DESTINATION REACHABILITY

    st.subheader("📍 Destination Reachability")

    if estimated_range >= distance:

        st.success(
            "Estimated battery range covers the journey."
        )

    else:

        shortfall = distance - estimated_range

        st.warning(
            f"Estimated range shortfall: {shortfall:.2f} km"
        )

    # CHARGING RECOMMENDATION

    st.subheader("⚡ Charging Recommendation")

    if not available_chargers:

        st.warning(
            "No available charger was returned by the Neo4j lookup."
        )

    elif station_distance is None:

        st.warning(
            "Charger road distance could not be calculated. "
            "A charging stop cannot be verified."
        )

    elif not charger_distance_valid:

        st.warning(
            "Approximate charger distance exceeds journey distance. "
            "Check the charger GPS coordinates."
        )

    else:

        recommendation = recommend_charging(
            estimated_range,
            distance,
            available_chargers,
            start_to_charger_distance=station_distance
        )

        st.info(recommendation)

    # CHARGER DISTANCE

    if station_distance is not None:

        st.metric(
            "Approximate Road Distance to Charger",
            f"{station_distance:.2f} km"
        )

        st.caption(
            f"Charger checked: {first_charger_name}"
        )

    else:

        st.info(
            "No valid charger road distance available."
        )

    # JOURNEY SUMMARY

    st.divider()
    st.header("🧾 Journey Summary")

    summary_col1, summary_col2 = st.columns(2)

    with summary_col1:
        st.write("📍 Start:", start_location)
        st.write("🏁 Destination:", destination)
        st.write("🛣️ Journey Distance:", f"{distance:.2f} km")
        st.write("🔋 Battery:", f"{battery}%")

    with summary_col2:
        st.write("💚 Battery SOH:", f"{soh}%")
        st.write("⚡ Usable Energy:", f"{energy:.2f} kWh")
        st.write("🚗 Estimated Range:", f"{estimated_range:.2f} km")
        st.write("🔌 Available Charger Records:", len(available_chargers))

    # FINAL STATUS

    st.subheader("🏁 Final Journey Status")

    if battery_status == "GREEN":

        st.success(
            "Destination is reachable based on the estimated battery range."
        )

    elif battery_status == "YELLOW":

        st.warning(
            "Estimated range may reach the charger. "
            "Verify actual station location and availability."
        )

    else:

        st.error(
            "Estimated range does not cover the destination "
            "or a verified intermediate charger."
        )

    # DISCLAIMER

    st.caption(
        "SmartEV is a demo prediction system. Battery consumption, "
        "traffic and AC impacts are assumptions. Charger availability "
        "and reliability are demo data. Charger coordinates may be "
        "approximate town-centre coordinates, not verified station GPS. "
        "OSRM provides estimated routes, not live traffic. Actual "
        "journey feasibility must be independently verified."
    )


# ==========================================
# FOOTER
# ==========================================

st.divider()

st.caption(
    "SmartEV | EV Range Prediction & Charging Route Planner | Demo Version"
)
