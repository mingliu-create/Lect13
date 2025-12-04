import streamlit as st
import pandas as pd
import sqlite3
import os
import folium
from streamlit_folium import st_folium
import json
import re
import sys
from typing import Any, Dict, List, Optional

# --- Configuration & Constants ---
DB_FILE = "data.db"
JSON_SOURCE = "data.json"

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

# --- Data Fetching & Processing Logic (from fetch_temperatures.py) ---

def is_temp_name(name: str) -> bool:
    """Checks if an element name looks like a temperature."""
    return bool(re.search(r"temp|temperature|t\b|溫度", name, re.IGNORECASE))

def find_locations(data: Any) -> List[Dict[str, Optional[str]]]:
    """
    Recursively scan JSON to find objects that represent locations with temperatures.
    """
    found: List[Dict[str, Optional[str]]] = []
    def scan(obj: Any, inherited_loc_name: Optional[str] = None):
        if isinstance(obj, dict):
            loc_name = inherited_loc_name
            for k in ("locationName", "locationname", "location", "siteName", "stationName", "name"):
                if k in obj and isinstance(obj[k], str):
                    loc_name = obj[k]; break
            if "weatherElement" in obj and isinstance(obj["weatherElement"], list):
                for elem in obj["weatherElement"]:
                    if not isinstance(elem, dict): continue
                    elem_name = elem.get("elementName") or elem.get("name") or ""
                    if is_temp_name(elem_name):
                        temp_val = None
                        val_container = elem.get("elementValue") or elem.get("value")
                        if isinstance(val_container, dict):
                            temp_val = val_container.get("value") or val_container.get("measure")
                        elif val_container is not None:
                            temp_val = str(val_container)
                        if loc_name and temp_val is not None:
                            found.append({"location": loc_name, "temp_type": elem_name, "temperature": temp_val})
            for v in obj.values(): scan(v, loc_name)
        elif isinstance(obj, list):
            for it in obj: scan(it, inherited_loc_name)
    scan(data)
    return found

def write_sqlite(rows: List[Dict[str, Optional[str]]], db_path: str) -> None:
    """Writes extracted temperature data to the SQLite database."""
    if not rows: return
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS temperatures (id INTEGER PRIMARY KEY, location TEXT NOT NULL, temp_type TEXT NOT NULL, temperature REAL NOT NULL)")
    cur.execute("DELETE FROM temperatures")
    for r in rows:
        loc, temp_type, temp = r.get("location"), r.get("temp_type"), r.get("temperature")
        if loc and temp_type and temp is not None:
            try:
                cur.execute("INSERT INTO temperatures (location, temp_type, temperature) VALUES (?, ?, ?)", (loc, temp_type, float(temp)))
            except (ValueError, TypeError):
                st.warning(f"Could not convert temperature '{temp}' to float for {loc}. Skipping.")
    conn.commit()
    conn.close()

def update_database_from_json(json_path: str = JSON_SOURCE, db_path: str = DB_FILE) -> str:
    """Reads the source JSON, processes it, and updates the SQLite DB."""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        locations = find_locations(data.get('cwaopendata', data))
        if not locations:
            return "No locations/temperatures discovered in the JSON file."
            
        write_sqlite(locations, db_path)
        return f"Successfully updated database with {len(locations)} records."
    except FileNotFoundError:
        return f"Error: Source data file not found at `{json_path}`."
    except Exception as e:
        return f"An error occurred: {e}"

# --- Data Loading for the App ---
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

# --- Initial Data Check and Setup ---
if not os.path.exists(DB_FILE):
    st.info(f"`{DB_FILE}` not found. Attempting to create it from `{JSON_SOURCE}`...")
    with st.spinner("Processing source data..."):
        result_message = update_database_from_json()
        st.success(result_message)
        st.rerun()

# --- Initialize Session State ---
if 'selected_location' not in st.session_state:
    st.session_state.selected_location = "All Locations"

# --- Load Data ---
df = get_data()

if df.empty:
    st.warning(f"No data to display. Check if `{JSON_SOURCE}` exists and is valid.", icon="⚠️")
else:
    # --- Sidebar and Map Controllers ---
    st.sidebar.header("📍 Location Selector")
    locations_list = ["All Locations"] + sorted(df["location"].unique().tolist())
    
    # Logic for two-way sync between map and selectbox
    # 1. Create map and check for clicks
    if st.session_state.selected_location == "All Locations":
        map_center = [23.97, 120.96]; map_zoom = 7
    else:
        loc_info = LOCATION_COORDS.get(st.session_state.selected_location, {"lat": 23.97, "lon": 120.96})
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
    current_selection_index = locations_list.index(st.session_state.selected_location)
    selection = st.sidebar.selectbox("Choose a location:", locations_list, index=current_selection_index)

    if st.session_state.selected_location != selection:
        st.session_state.selected_location = selection
        st.rerun()

    # --- Display Data ---
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

    # --- Actions ---
    st.sidebar.write("---")
    st.sidebar.header("Actions")
    if st.sidebar.button("🔄 Update Data"):
        with st.spinner("Fetching latest data from source..."):
            update_message = update_database_from_json()
            st.sidebar.success(update_message)
            st.cache_data.clear() # Clear cache to force data reload
        st.rerun()

    st.sidebar.write("---")
    st.sidebar.info(f"Data is read from `{DB_FILE}`.")