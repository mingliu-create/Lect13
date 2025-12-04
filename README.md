# 🇹🇼 Taiwan Temperature Viewer 🌡️

This project provides an interactive Streamlit web application to visualize temperature data from various locations in Taiwan. The data is fetched from the Central Weather Administration (CWA) Open Data API, processed, stored in a SQLite database, and then displayed on an interactive map with location selection and detailed metrics.

## ✨ Features

- **Interactive Map**: Visualize temperature locations on a Folium-powered map of Taiwan.
- **Location Selection**: Select specific locations via a sidebar dropdown or by clicking on map markers to view detailed temperature metrics.
- **Detailed Temperature Metrics**: For each location, display average, maximum, and minimum temperatures.
- **Data Persistence**: Data is stored in a local SQLite database (`data.db`).
- **Data Refresh**: A button in the Streamlit app allows users to refresh the data from the CWA API on demand.

## 🚀 Getting Started

Follow these steps to set up and run the application locally.

### Prerequisites

- Python 3.8+
- Git (optional, for cloning the repository)

### Installation

1.  **Clone the repository** (if you haven't already):
    ```bash
    git clone https://github.com/mingliu-create/Lect13.git
    cd Lect13
    ```

2.  **Install Python dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

### 💡 Initial Data Fetch

Before running the Streamlit app, you need to fetch the initial temperature data and populate the SQLite database.

```bash
python fetch_temperatures.py
```
This script will fetch data from the CWA API, process it, and save it into `data.db`.

### ▶️ Run the Streamlit Application

After fetching the data, start the Streamlit app:
```bash
streamlit run app.py
```
This command will open the interactive temperature viewer in your web browser.

## 🔄 Updating Data

You can refresh the temperature data directly from within the Streamlit application:
1.  Open the Streamlit app (`streamlit run app.py`).
2.  Navigate to the sidebar.
3.  Click the "🔄 Update Data" button.
    The app will re-run `fetch_temperatures.py` in the background, update the `data.db`, clear its cache, and refresh the display with the latest information.

## 🌍 Data Source

Temperature data is sourced from the **Central Weather Administration (CWA) Open Data API** (specifically, the `F-A0010-001` dataset for agricultural weather forecasts).

**Disclaimer**: The API key embedded in `fetch_temperatures.py` might be specific or temporary. If you encounter issues fetching data, please ensure the `Authorization` key in `fetch_temperatures.py` (specifically in the `DEFAULT_URL` or if the web_fetch fails) is valid for the CWA API. You might need to register on the CWA Open Data platform to obtain your own API key.