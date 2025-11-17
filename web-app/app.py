"""Flask app for AI-assisted audio notes."""

import sys
import os
from flask import Flask, request, jsonify
from flask_cors import CORS

# Add app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))

from app.config import Config
from app.db import get_notes_collection

# Create Flask app
app = Flask(__name__)
app.config.from_object(Config)
app.config["MAX_CONTENT_LENGTH"] = Config.MAX_FILE_MB * 1024 * 1024
CORS(app)


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


# TODO: Implement remaining routes:
# - POST /upload - Use app.storage.save_audio_to_gridfs()
# - GET /notes/<id> - Get specific note
# - GET /search - Search notes using regex
# - POST /process/<id> - Trigger inline processing


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
