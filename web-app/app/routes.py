"""Flask routes for audio notes API."""

import datetime
from bson import ObjectId
from flask import Blueprint, current_app, jsonify, request
from .db import Database, get_recordings_collection, get_notes_collection
from .storage import save_audio_to_gridfs
from .services.openai_speech import transcribe_audio_bytes
from .services.openai_text import summarize_and_keywords

bp = Blueprint("routes", __name__)


def _oid(id_str: str):
    """Convert string to ObjectId, return None if invalid."""
    try:
        return ObjectId(id_str)
    except Exception:
        return None


@bp.get("/")
def health():
    """Health check endpoint."""
    return "Audio Note Web App is running!", 200


@bp.post("/upload")
def upload_audio():
    """
    Multipart form-data:
      - file: audio/webm|wav|mp3|m4a|ogg|mp4
    Returns: { recording_id }
    """
    if "file" not in request.files:
        return jsonify({"error": "no file"}), 400
    file = request.files["file"]

    try:
        fid = save_audio_to_gridfs(file, file.filename or "audio.webm")
    except ValueError as e:
        return jsonify({"error": str(e)}), 413
    except Exception as e:
        return jsonify({"error": f"upload failed: {e}"}), 500

    rec = {
        "audio_gridfs_id": fid,
        "created_at": datetime.datetime.utcnow(),
        "status": "pending",
        "language": None,
        "duration_sec": None,
        "error": None,
    }
    recordings = get_recordings_collection()
    rid = recordings.insert_one(rec).inserted_id

    if current_app.config["PROCESS_INLINE"]:
        try:
            audio_bytes = Database.get_gridfs().get(fid).read()
            stt = transcribe_audio_bytes(
                audio_bytes, filename=file.filename or "audio.webm"
            )
            transcript = stt.get("text", "")
            language = stt.get("language")
            enrich = (
                summarize_and_keywords(transcript)
                if transcript
                else {"summary": "", "keywords": [], "action_items": []}
            )

            notes = get_notes_collection()
            notes.insert_one(
                {
                    "recording_id": rid,
                    "transcript": transcript,
                    "keywords": enrich["keywords"],
                    "summary": enrich["summary"],
                    "action_items": enrich.get("action_items", []),
                    "created_at": datetime.datetime.utcnow(),
                }
            )
            recordings.update_one(
                {"_id": rid}, {"$set": {"status": "done", "language": language}}
            )
        except Exception as ex:
            recordings.update_one(
                {"_id": rid}, {"$set": {"status": "error", "error": str(ex)}}
            )

    return jsonify({"recording_id": str(rid)}), 201


@bp.get("/notes")
def list_notes():
    """Dashboard feed: latest recordings joined with note summary/keywords."""
    pipeline = [
        {"$sort": {"created_at": -1}},
        {"$limit": 50},
        {
            "$lookup": {
                "from": "notes",
                "localField": "_id",
                "foreignField": "recording_id",
                "as": "note_docs",
            }
        },
        {
            "$project": {
                "_id": 1,
                "created_at": 1,
                "status": 1,
                "language": 1,
                "summary": {"$arrayElemAt": ["$note_docs.summary", 0]},
                "keywords": {"$arrayElemAt": ["$note_docs.keywords", 0]},
            }
        },
    ]
    items = list(get_recordings_collection().aggregate(pipeline))
    for it in items:
        it["_id"] = str(it["_id"])
    return jsonify(items)


@bp.get("/notes/<id>")
def note_detail(id):
    """Get detailed note information by recording ID."""
    oid = _oid(id)
    if not oid:
        return jsonify({"error": "invalid id"}), 400
    rec = get_recordings_collection().find_one({"_id": oid})
    if not rec:
        return jsonify({"error": "not found"}), 404
    note = get_notes_collection().find_one({"recording_id": rec["_id"]})
    out = {
        "id": str(rec["_id"]),
        "created_at": rec["created_at"].isoformat(),
        "status": rec["status"],
        "language": rec.get("language"),
        "summary": note.get("summary") if note else None,
        "keywords": note.get("keywords") if note else None,
        "action_items": note.get("action_items") if note else None,
        "transcript": note.get("transcript") if note else None,
    }
    return jsonify(out)


@bp.get("/search")
def search_notes():
    """Search notes by query string."""
    q = (request.args.get("q") or "").strip()
    if not q:
        return jsonify([])
    cursor = (
        get_notes_collection()
        .find(
            {
                "$or": [
                    {"transcript": {"$regex": q, "$options": "i"}},
                    {"keywords": {"$elemMatch": {"$regex": q, "$options": "i"}}},
                ]
            },
            {"transcript": 0},
        )
        .sort("created_at", -1)
        .limit(50)
    )
    out = []
    for d in cursor:
        out.append(
            {
                "recording_id": str(d["recording_id"]),
                "summary": d.get("summary"),
                "keywords": d.get("keywords"),
                "created_at": d["created_at"].isoformat(),
            }
        )
    return jsonify(out)


@bp.post("/process/<id>")
def process_now(id):
    """Force (re)process a recording (useful when PROCESS_INLINE=false)."""
    oid = _oid(id)
    if not oid:
        return jsonify({"error": "invalid id"}), 400
    recs = get_recordings_collection()
    rec = recs.find_one({"_id": oid})
    if not rec:
        return jsonify({"error": "not found"}), 404

    fid = rec["audio_gridfs_id"]
    try:
        recs.update_one({"_id": rec["_id"]}, {"$set": {"status": "processing"}})
        audio = Database.get_gridfs().get(fid).read()
        stt = transcribe_audio_bytes(audio, filename="audio.webm")
        transcript = stt.get("text", "")
        language = stt.get("language")
        enrich = (
            summarize_and_keywords(transcript)
            if transcript
            else {"summary": "", "keywords": [], "action_items": []}
        )

        get_notes_collection().update_one(
            {"recording_id": rec["_id"]},
            {
                "$set": {
                    "transcript": transcript,
                    "keywords": enrich["keywords"],
                    "summary": enrich["summary"],
                    "action_items": enrich.get("action_items", []),
                    "created_at": datetime.datetime.utcnow(),
                }
            },
            upsert=True,
        )
        recs.update_one(
            {"_id": rec["_id"]}, {"$set": {"status": "done", "language": language}}
        )
    except Exception as ex:
        recs.update_one(
            {"_id": rec["_id"]}, {"$set": {"status": "error", "error": str(ex)}}
        )
        return jsonify({"error": str(ex)}), 500

    return jsonify({"ok": True})
