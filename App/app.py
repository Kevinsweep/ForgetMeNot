import streamlit as st
import requests
import time
from dotenv import load_dotenv
import os
import plotly.graph_objects as go
import pandas as pd
import numpy as np

load_dotenv(override=True)
base_url = str(os.getenv("BASE_URL"))
predict_url = base_url + "predict"
upload_url = base_url + "upload"
get_latest_data_url = base_url + "get_latest_data"
get_all_data_url = base_url + "get_all_data"

# fetch latest data 
def fetch_data():
    response = requests.get(get_all_data_url)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Error: Unable to fetch data {response}")
        return None


st.markdown(
    """
        <style>
        [data-testid="stMetricValue-small"] {
            font-size: 20px;
        }
        .metric-label {
            font-size: 12px;
            color: gray;
        }
        .metric-value {
            font-size: 20px;
        }
        .icon-container {
            display: flex;
            justify-content: center;
            align-items: center;
            margin-top: 15px;
            height: 100%;
        }
        .icon {
            font-size: 50px;
        }
        .metric-container{
            display: flex;
            justify-content: center;
            align-items: center;
            width: 100%;
        }
        </style>
        """,
    unsafe_allow_html=True,
)

def display_data(data, label, metric):
    if(len(data) == 0):
        st.error("Error: No data in the last 5 minutes. Please check the sensor connection.")
        return
    # Display min, max, avg, and line chart for each data
    # min_value = min(data)
    # max_value = max(data)
    # avg_value = np.mean(data)
    latest_value = data[-1]

    pad, icon, met = st.columns([0.1, 0.2, 0.7])
    with pad:
        st.write(" ")
    with icon:
        if(label == "Body Temperature"):
            st.markdown(f"<div class='icon-container'><div class='icon'>🌡️</div></div>", unsafe_allow_html=True)
        elif(label == "SPO2"):
            st.markdown(f"<div class='icon-container'><div class='icon'>🩸</div></div>", unsafe_allow_html=True)
        elif(label == "Heart Rate"):
            st.markdown(f"<div class='icon-container'><div class='icon'>💓</div></div>", unsafe_allow_html=True)
        elif(label == "Speed"):
            st.markdown(f"<div class='icon-container'><div class='icon'>🏃🏼‍♂️</div></div>", unsafe_allow_html=True)
    with met:
        st.metric(label, value=f"{latest_value:.2f} {metric}", delta_color="normal")
    
    # st.markdown(
    #     f"<div class='metric-label'>Min</div><div class='metric-value'>{latest_value:.1f} {metric}</div>",
    #     unsafe_allow_html=True,
    # )

def spacer(len):
    for i in range(len):
        st.write("")

def summary_section(df):
    col1, col2 = st.columns(2)
    with col1:
        display_data(list(df["body_temp"]), "Body Temperature", "°C")
    with col2:
        display_data(list(df['spo2']), "SPO2", "%")
    spacer(3)
    col3, col4 = st.columns(2)
    with col3:
        display_data(list(df['heart_rate']), "Heart Rate", "bpm")
    with col4:
        display_data(list(df['speed']), "Speed", "km/h") 

def display_risk():
    risk_level = requests.get(predict_url)
    if(risk_level.status_code == 404):
        st.error("Error: No data in the last 5 minutes. Please check the sensor connection.")
        return
    risk_level = risk_level.json()["risk_level"]
    color_map = {
        "Low Risk": "#00cc44",  # Green
        "Medium Risk": "#ffcc00",  # Yellow
        "High Risk": "#ff3333"  # Red
    }
    
    icon_map = {
        "Low Risk": "🟢",
        "Medium Risk": "🟡",
        "High Risk": "🔴"
    }

    st.markdown(
        f"""
        <style>
        .risk-container {{
            display: flex;
            flex-direction: column;
            align-items: center;
            border: 2px solid {color_map[risk_level]};
            border-radius: 10px;
            padding: 20px;
            margin: 10px;
        }}
        .risk-category {{
            font-size: 30px;
            font-weight: bold;
            color: {color_map[risk_level]};
        }}
        .risk-icon {{
            font-size: 60px;
        }}
        .risk-probability {{
            font-size: 20px;
            color: gray;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="risk-container">
            <div class="risk-icon">{icon_map[risk_level]}</div>
            <div class="risk-category">{risk_level}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

def graph_menu(data):
    # Checkbox for type of data to display (Spo2, Heart Rate, Body Temperature, Blood Sugar)
    graph_col1, graph_col2 = st.columns([0.2, 0.8])
    
    with graph_col1:
        spo2_check = st.checkbox("SPO2", value=True, key="spo2")
        hr_check = st.checkbox("Heart Rate", value=True, key="heart_rate")
        body_temp_check = st.checkbox("Body Temperature", value=True, key="body_temp")
        speed_check = st.checkbox("Speed", value=True, key="speed")
        
        selected_columns = []
        if spo2_check:
            selected_columns.append("spo2")
        if hr_check:
            selected_columns.append("heart_rate")
        if body_temp_check:
            selected_columns.append("body_temp")
        if speed_check:
            selected_columns.append("speed")
        selected_columns.append("timestamp")
        
        # Filter selected columns
        selected_data = data.loc[:, selected_columns].copy()  # Use .loc and make a copy
        
        # Convert 'timestamp' column to pandas datetime
        selected_data['timestamp'] = pd.to_datetime(selected_data['timestamp'])
        
        # Adjust for GMT+7 timezone
        selected_data['timestamp'] = selected_data['timestamp'] + pd.DateOffset(hours=7)
        
        # Set 'timestamp' as the index
        selected_data.set_index("timestamp", inplace=True)
        
        # Timeframe selection
        timeframes = ["1 Hour", "1 Day", "1 Week"]
        timeframe = st.selectbox("Select Timeframe", timeframes)
        
        # Filter data based on the selected timeframe
        if timeframe == "1 Hour":
            selected_data = selected_data[selected_data.index >= pd.Timestamp.now(tz='UTC') - pd.DateOffset(hours=1)]
        elif timeframe == "1 Day":
            selected_data = selected_data[selected_data.index >= pd.Timestamp.now(tz='UTC') - pd.DateOffset(days=1)]
        elif timeframe == "1 Week":
            selected_data = selected_data[selected_data.index >= pd.Timestamp.now(tz='UTC') - pd.DateOffset(weeks=1)]
    
    with graph_col2:
        st.line_chart(data=selected_data)

def main():
    st.title("Forget Me Not")
    with st.expander("About"):
        st.write(
            """
                ForgetMeNot is an app to help the care of people with dementia
            """
        )
    while True:
        # get data
        data = fetch_data()
        latest_data = requests.get(get_latest_data_url).json()
        data = pd.DataFrame(data)
        latest_data = pd.DataFrame([latest_data])

        # location
        st.subheader("Location")
        lat = list(latest_data['latitude'])[-1]
        lon = list(latest_data['longitude'])[-1]
        gmap_url = f"https://maps.google.com/maps?q={lat},{lon}&z=12&output=embed"
        st.iframe(gmap_url, width="content", height=500)
        
        # vital signs
        if len(data) == 0:
            st.write("No data available. Please check the sensor connection.")
        else:
            display_risk()
            spacer(3)
            summary_section(latest_data)
            spacer(3)
            graph_menu(data)

        time.sleep(10)
        st.rerun()

if __name__ == "__main__":
    main()