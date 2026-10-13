from flask import Flask, request, jsonify
import numpy as np
import pickle
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import datetime
from dotenv import load_dotenv
import os

load_dotenv()
uri = os.getenv('MONGO_URI')
client = MongoClient(uri, server_api=ServerApi('1'))
db = client['ForgetMeNot_db']
collection = db['sensor_data']

app = Flask(__name__)

# functions
def calculate_blood_glucose(spo2, hr) -> float:
    bs = 16714.61 + 0.47 * hr - 351.045 * spo2 + 1.85 * spo2**2
        # The metrics is still in mg/dL we need to convert it to mmol/L
    return bs / 18

# flask routing
@app.route('/')
def backend_check():
    return jsonify({"status": "ok", "service": "mainfeat"}), 200


@app.route('/upload', methods=['POST'])
def upload():
    latest_data = request.get_json(force=True)
    data_to_send = {
        "timestamp": datetime.datetime.now(),
        "bs": calculate_blood_glucose(latest_data['spo2'], latest_data['heart_rate']),
        "body_temperature": latest_data['body_temperature'],
        "heart_rate": latest_data['heart_rate'],
        "spo2": latest_data['spo2'],
    }
    collection.insert_one(data_to_send)
    return jsonify({"status": "Data received"}), 200

if __name__ == "__main__":
    app.run(host='127.0.0.1', debug=True)
