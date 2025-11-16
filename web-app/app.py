"""Flask app for AI-assisted audio notes with PyMongo."""

import os
from flask import Flask, request, jsonify
from flask_pymongo import PyMongo

app = Flask(__name__)
# MongoDB configuration from environment variables
app.config["MONGO_URI"] = (
    f"mongodb://{os.getenv('MONGO_USER', 'admin')}:{os.getenv('MONGO_PASSWORD', 'adminpassword')}@"
    f"{os.getenv('MONGO_HOST', 'mongodb')}:{os.getenv('MONGO_PORT', '27017')}/"
    f"{os.getenv('MONGO_DB', 'app_db')}"
)
mongo = PyMongo(app)


def get_notes_collection():
    """Get the notes collection from MongoDB."""
    return mongo.db.notes


@app.route("/", methods=["GET"])
def index():
    """Root endpoint to verify the app is running."""
    return "Audio Note Web App is running!"


@app.route("/notes", methods=["POST"])
def add_note():
    """Add a new audio note with transcription and structured notes."""
    data = request.get_json()
    note = {
        "audio_url": data.get("audio_url"),
        "transcription": data.get("transcription"),
        "structured_notes": data.get("structured_notes", {}),
    }
    notes_col = get_notes_collection()
    result = notes_col.insert_one(note)
    return jsonify({"inserted_id": str(result.inserted_id)}), 201


@app.route("/notes", methods=["GET"])
def get_notes():
    """Retrieve all audio notes."""
    notes_col = get_notes_collection()
    notes = list(notes_col.find({}, {"_id": 0}))
    return jsonify(notes)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
