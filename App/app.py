import streamlit as st
import requests
import time
from dotenv import load_dotenv
import os
import plotly.graph_objects as go
import pandas as pd
import numpy as np

load_dotenv()

# API URLs
predict_url = os.getenv("PREDICT_URL")
upload_url = os.getenv("UPLOAD_URL")
get_avg_data_url = os.getenv("GET_AVG_DATA_URL")
get_latest_data_url = os.getenv("GET_LATEST_DATA_URL")

