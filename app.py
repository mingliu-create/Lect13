import streamlit as st
import pandas as pd
import sqlite3
import os
import folium
from streamlit_folium import st_folium
import subprocess

# --- Configuration & Constants ---
DB_FILE = "data.db"

# Approximate coordinates for the locations in the database.
LOCATION_COORDS = {
    "宜蘭": {"lat": 24.746, "lon": 121.745},
    "花蓮": {"lat": 23.971, "lon": 121.605},
    "臺東": {"lat": 22.758, "lon": 121.144},
    "臺北": {"lat": 25.033, "lon": 121.565},
    "新竹": {"lat": 24.813, "lon": 120.966},
    "臺中": {"lat": 24.147, "lon": 120.673},
    "嘉義": {"lat": 23.480, "lon": 120.449},
    "高雄": {"lat": 22.627, "lon": 120.301},
    "恆春": {"lat": 22.004, "lon": 120.744},
}

# --- Data Loading ---
@st.cache_data
def get_data() -> pd.DataFrame:
    """Connects to the SQLite DB and returns a 'long' DataFrame with coordinates."""
    if not os.path.exists(DB_FILE):
        return pd.DataFrame()
    try:
        conn = sqlite3.connect(DB_FILE)
        df = pd.read_sql_query("SELECT location, temp_type, temperature FROM temperatures", conn)
        coord_df = pd.DataFrame.from_dict(LOCATION_COORDS, orient='index').reset_index().rename(columns={'index': 'location'})
        return pd.merge(df, coord_df, on='location')
    finally:
        if 'conn' in locals() and conn:
            conn.close()

# --- Main App ---
st.set_page_config(page_title="Taiwan Temperature Map", layout="wide")
st.title("🌡️ Taiwan Temperature Viewer")

# --- Initialize Session State ---
if 'selected_location' not in st.session_state:
    st.session_state.selected_location = "All Locations"

# --- Load Data ---
df = get_data()

if df.empty:
    st.warning(f"No data found in `{DB_FILE}`. Please run `fetch_temperatures.py` first.", icon="⚠️")
else:
    # --- Sidebar and Map Controllers ---
    st.sidebar.header("📍 Location Selector")
    locations_list = ["All Locations"] + sorted(df["location"].unique().tolist())
    
    # This logic block handles the two-way sync between map and selectbox
    
    # 1. Create map and check for clicks
    if st.session_state.selected_location == "All Locations":
        map_center = [23.97, 120.96]; map_zoom = 7
    else:
        loc_info = LOCATION_COORDS.get(st.session_state.selected_location)
        map_center = [loc_info['lat'], loc_info['lon']]; map_zoom = 10

    m = folium.Map(location=map_center, zoom_start=map_zoom, tiles="CartoDB positron")
    for _, row in df.drop_duplicates('location').iterrows():
        folium.Marker(location=[row['lat'], row['lon']], popup=row['location'], tooltip=row['location']).add_to(m)
    
    map_data = st_folium(m, width='100%', height=400, key="folium_map")

    # If map is clicked, update state and rerun
    if map_data and map_data.get("last_object_clicked_popup"):
        clicked_loc = map_data["last_object_clicked_popup"]
        if st.session_state.selected_location != clicked_loc:
            st.session_state.selected_location = clicked_loc
            st.rerun()

    # 2. Create selectbox and check for changes
    # Set index based on the current session state
    current_selection_index = locations_list.index(st.session_state.selected_location)
    selection = st.sidebar.selectbox(
        "Choose a location:", 
        locations_list, 
        index=current_selection_index
    )

    # If selectbox is changed, update state and rerun
    if st.session_state.selected_location != selection:
        st.session_state.selected_location = selection
        st.rerun()

    # --- Display Data (based on the final session state) ---
    st.write("---")
    if st.session_state.selected_location == "All Locations":
        st.header("📊 Full Data Overview")
        pivoted_df = df.pivot_table(index='location', columns='temp_type', values='temperature').reset_index()
        st.dataframe(pivoted_df, use_container_width=True, hide_index=True)
    else:
        st.header(f"🌡️ Temperature Details for {st.session_state.selected_location}")
        location_data_long = df[df['location'] == st.session_state.selected_location]
        
        cols = st.columns(len(location_data_long))
        for i, row in enumerate(location_data_long.itertuples()):
            with cols[i]:
                st.metric(label=row.temp_type, value=f"{row.temperature} °C")

    st.sidebar.write("---")
    st.sidebar.header("Actions")
    if st.sidebar.button("🔄 Update Data"):
        with st.spinner("Fetching latest data from source..."):
            try:
                # We assume the virtual environment's Python is in the path.
                # If not, a more specific path might be needed.
                result = subprocess.run(
                    ["python", "fetch_temperatures.py"],
                    capture_output=True,
                    text=True,
                    check=True,
                    encoding='utf-8' # Ensure output is decoded correctly
                )
                st.sidebar.success("Data updated successfully!")
                st.sidebar.info("Output from update script:")
                st.sidebar.code(result.stdout)
                # Clear the cache to force a re-read of the data
                st.cache_data.clear()
            except subprocess.CalledProcessError as e:
                st.sidebar.error("Failed to update data.")
                st.sidebar.code(e.stderr)
            except FileNotFoundError:
                st.sidebar.error("Error: 'python' command not found. Is Python in your system's PATH?")
        
        # Rerun the app to reflect the changes
        st.rerun()

    st.sidebar.write("---")
    st.sidebar.info("Data is read from `data.db`.")
