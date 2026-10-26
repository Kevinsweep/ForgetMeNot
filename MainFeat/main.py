from flask import Flask, request, jsonify
import numpy as np
import pickle
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import datetime
from dotenv import load_dotenv
import os
import pymongo

load_dotenv(override=True)
uri = os.getenv('MONGO_URI')
client = MongoClient(uri)
db = client['ForgetMeNot_db']
collection = db['sensor_data']

app = Flask(__name__)

def get_data(pipeline: list[dict]) -> list[dict]:
    result = list(collection.aggregate(pipeline))
    return result

def get_avg_data()->dict:
    curr_time = datetime.datetime.now()
    five_minutes_ago = curr_time - datetime.timedelta(minutes=5)
    pipeline = [
        {"$sort": {"timestamp": -1}},
        {"$limit": 5},
        {
            "$group": {
                "_id": None,
                "average_body_temp": {"$avg": "$body_temp"},
                "average_heart_rate": {"$avg": "$heart_rate"},
                "average_spo2": {"$avg": "$spo2"}
            }
        }
    ]
    result = get_data(pipeline)[0]
    return result

def make_prediction(features_np: np.ndarray):
    return [0]

# flask routing
@app.route('/')
def backend_check():
    return jsonify({"status": "ok", "service": "mainfeat"}), 200


@app.route('/upload', methods=['POST'])
def upload():
    latest_data = request.get_json(force=True)
    data_to_send = {
        "timestamp": datetime.datetime.now(),
        "body_temp": latest_data['body_temp'],
        "heart_rate": latest_data['heart_rate'],
        "spo2": latest_data['spo2'],
        "latitude": latest_data['latitude'],
        "longitude": latest_data['longitude'],
        "speed": latest_data['speed']
    }
    collection.insert_one(data_to_send)
    return jsonify({"status": "Data received"}), 200

# for dashboard
@app.route('/get_latest_data', methods=["GET"])
def get_latest_data():
    pipeline = [
        {"$sort": {"timestamp": -1}},
        {"$limit": 1}
    ]
    latest_data = get_data(pipeline)[0]
    latest_data.pop("_id")
    return jsonify(latest_data)

@app.route('/get_all_data', methods=['GET'])
def get_all_data():
    data = list(collection.find())
    for d in data:
        d.pop("_id")
    return jsonify(data)

# automation
@app.route('/predict', methods=['GET'])
def predict_risk_level():
    features = get_avg_data()
    if features is None:
        return jsonify({"error": "No data in the last 5 minutes"}), 404
    features_np = np.array([features['average_body_temp'], features['average_heart_rate'], features['average_spo2']]).reshape(1, -1)
    prediction = make_prediction(features_np)
    output = int(prediction[0])

    risk_levels = {0: 'Low Risk', 1: 'Medium Risk', 2: 'High Risk'}
    risk_output = risk_levels.get(output, "Unknown Risk Level")

    return jsonify({"risk_level": risk_output}), 200



if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)
