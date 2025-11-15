from flask import Flask, request, jsonify
from flask_pymongo import PyMongo
import os

app = Flask(__name__)

# MongoDB configuration from environment variables
app.config["MONGO_URI"] = f"mongodb://{os.getenv('MONGO_USER','admin')}:{os.getenv('MONGO_PASSWORD','adminpassword')}@{os.getenv('MONGO_HOST','mongodb')}:{os.getenv('MONGO_PORT','27017')}/{os.getenv('MONGO_DB','app_db')}"
mongo = PyMongo(app)

def get_notes_collection():
    return mongo.db.notes

@app.route("/", methods=["GET"])
def index():
    return "Audio Note Web App is running!"

@app.route("/notes", methods=["POST"])
def add_note():
    data = request.get_json()
    note = {
        "audio_url": data.get("audio_url"),
        "transcription": data.get("transcription"),
        "structured_notes": data.get("structured_notes", {})
    }
    notes_col = get_notes_collection()
    result = notes_col.insert_one(note)
    return jsonify({"inserted_id": str(result.inserted_id)}), 201

@app.route("/notes", methods=["GET"])
def get_notes():
    notes_col = get_notes_collection()
    notes = list(notes_col.find({}, {"_id": 0}))
    return jsonify(notes)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
