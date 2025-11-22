"""pymongo/GridFS connection helpers.

This module provides simple helpers for connecting to MongoDB, saving
and retrieving audio blobs using GridFS, and manipulating metadata
documents used by the client (recordings, transcriptions, structured
notes). Configuration is read from environment variables.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

import gridfs
from bson import ObjectId
from pymongo import MongoClient


# Module-level cached client/db to avoid reconnecting repeatedly
_client: Optional[MongoClient] = None
_db = None


def _get_mongo_uri() -> str:
    """Return MongoDB URI built from environment or use MONGO_URI.

    Looks for `MONGO_URI` first; if not present, composes a URI from
    host/port/user/password/db env vars.
    """
    uri = os.getenv("MONGO_URI")
    if uri:
        return uri

    host = os.getenv("MONGO_HOST", "mongodb")
    port = os.getenv("MONGO_PORT", "27017")
    user = os.getenv("MONGO_USER")
    password = os.getenv("MONGO_PASSWORD")
    db = os.getenv("MONGO_DB", "app_db")

    if user and password:
        return f"mongodb://{user}:{password}@{host}:{port}/{db}"
    return f"mongodb://{host}:{port}/{db}"


def get_client() -> MongoClient:
    """Return a cached MongoClient, creating one if necessary."""
    global _client  # pylint: disable=global-statement
    if _client is None:
        uri = _get_mongo_uri()
        import logging
        logging.info(f"Connecting to MongoDB with URI: {uri}")
        _client = MongoClient(uri)
    return _client


def get_db() -> Any:
    """Return the configured database instance."""
    global _db  # pylint: disable=global-statement
    if _db is None:
        # pick DB name from URI or env
        dbname = os.getenv("MONGO_DB")
        client = get_client()
        if dbname:
            _db = client[dbname]
        else:
            # fallback to default database from URI
            _db = client.get_default_database()
    return _db


def get_fs() -> gridfs.GridFS:
    """Return a GridFS instance for storing binary files."""
    db = get_db()
    return gridfs.GridFS(db)


def save_audio(
    data: bytes,
    filename: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> ObjectId:
    """Save audio bytes to GridFS and return the file id.

    :param data: Raw audio bytes
    :param filename: Optional filename to associate
    :param metadata: Optional metadata dict to save with the file
    :return: ObjectId of the saved GridFS file
    """
    fs = get_fs()
    file_id = fs.put(data, filename=filename, metadata=metadata or {})
    return file_id


def get_audio(file_id: ObjectId) -> bytes:
    """Retrieve raw bytes for a GridFS file id.

    Raises `gridfs.NoFile` if not found.
    """
    fs = get_fs()
    gfile = fs.get(file_id)
    return gfile.read()


def create_record(record: Dict[str, Any]) -> ObjectId:
    """Insert a new recording metadata document into `recordings`.

    Expected to include at least: status (pending), file_id (GridFS id),
    and any user metadata. Returns the inserted _id.
    """
    db = get_db()
    result = db.recordings.insert_one(record)
    return result.inserted_id


def find_pending(limit: int = 10) -> List[Dict[str, Any]]:
    """Return a list of pending recording documents (status == 'pending')."""
    db = get_db()
    docs = list(db.recordings.find({"status": "pending"}).limit(limit))
    return docs


def mark_record_status(record_id: ObjectId | str, status: str) -> None:
    """Update the status field of a recording document."""
    db = get_db()
    _id = ObjectId(record_id) if not isinstance(record_id, ObjectId) else record_id
    db.recordings.update_one({"_id": _id}, {"$set": {"status": status}})


def insert_transcription(
    record_id: ObjectId | str, text: str, confidence: Optional[float] = None
) -> ObjectId:
    """Insert a transcription document and link it to a recording.

    Returns the transcription _id.
    """
    db = get_db()
    _id = ObjectId(record_id) if not isinstance(record_id, ObjectId) else record_id
    doc = {"recording_id": _id, "text": text, "confidence": confidence}
    res = db.transcriptions.insert_one(doc)
    db.recordings.update_one(
        {"_id": _id}, {"$set": {"transcription_id": res.inserted_id}}
    )
    return res.inserted_id


def insert_structured_note(
    transcription_id: ObjectId | str, note: Dict[str, Any]
) -> ObjectId:
    """Insert a structured note document and link it to the transcription."""
    db = get_db()
    _tid = (
        ObjectId(transcription_id)
        if not isinstance(transcription_id, ObjectId)
        else transcription_id
    )
    doc = {"transcription_id": _tid, **note}
    res = db.structured_notes.insert_one(doc)
    db.transcriptions.update_one(
        {"_id": _tid}, {"$set": {"structured_note_id": res.inserted_id}}
    )
    return res.inserted_id


# pylint: disable=too-many-arguments,too-many-positional-arguments
def insert_note(
    recording_id: ObjectId | str,
    transcript: str,
    keywords: List[str],
    summary: str,
    action_items: Optional[List[Dict[str, Any]]] = None,
    language: Optional[str] = None,
) -> ObjectId:
    """Insert a note document compatible with the `web-app` schema.

    The web app expects a `notes` collection with documents containing:
      - recording_id (ObjectId)
      - transcript (str)
      - keywords (list)
      - summary (str)
      - action_items (list)
      - created_at (datetime)

    Returns the inserted note _id.
    """
    db = get_db()
    _rid = (
        ObjectId(recording_id)
        if not isinstance(recording_id, ObjectId)
        else recording_id
    )
    doc = {
        "recording_id": _rid,
        "transcript": transcript,
        "keywords": keywords or [],
        "summary": summary or "",
        "action_items": action_items or [],
        "created_at": datetime.utcnow(),
    }
    if language is not None:
        doc["language"] = language
    res = db.notes.insert_one(doc)
    return res.inserted_id


def update_record(record_id: ObjectId | str, updates: Dict[str, Any]) -> None:
    """Update arbitrary fields on a recording document (helper)."""
    db = get_db()
    _id = ObjectId(record_id) if not isinstance(record_id, ObjectId) else record_id
    db.recordings.update_one({"_id": _id}, {"$set": updates})


def set_record_error(record_id: ObjectId | str, error_message: str) -> None:
    """Set an error status and message for a record."""
    db = get_db()
    _id = ObjectId(record_id) if not isinstance(record_id, ObjectId) else record_id
    db.recordings.update_one(
        {"_id": _id}, {"$set": {"status": "error", "error": error_message}}
    )


def get_record(record_id: ObjectId | str) -> Optional[Dict[str, Any]]:
    """Return a recording document by id (or None)."""
    db = get_db()
    _id = ObjectId(record_id) if not isinstance(record_id, ObjectId) else record_id
    return db.recordings.find_one({"_id": _id})


def list_records(
    filter_query: Optional[Dict[str, Any]] = None, limit: int = 100
) -> Iterable[Dict[str, Any]]:
    """List recordings matching a filter (default: all).

    Returns a cursor-like iterable converted to a list when consumed.
    """
    db = get_db()
    q = filter_query or {}
    return db.recordings.find(q).limit(limit)
