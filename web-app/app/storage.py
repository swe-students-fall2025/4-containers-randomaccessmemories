"""GridFS file storage with validation."""

from datetime import datetime
from werkzeug.utils import secure_filename
from bson import ObjectId
from .db import Database
from .config import Config

ALLOWED_EXTENSIONS = {"wav", "mp3", "ogg", "webm", "m4a", "mp4"}


def allowed_file(filename):
    """Check if file extension is allowed."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def validate_file_size(file):
    """Validate file size. Returns (is_valid, size_mb)."""
    file.seek(0, 2)
    size_bytes = file.tell()
    file.seek(0)
    size_mb = size_bytes / (1024 * 1024)
    return size_mb <= Config.MAX_FILE_MB, size_mb


def save_audio_to_gridfs(file, original_filename):
    """
    Save audio file to GridFS.

    Args:
        file: FileStorage object from Flask request
        original_filename: Original filename

    Returns:
        ObjectId: GridFS file_id

    Raises:
        ValueError: If file type not allowed or size exceeds limit
    """
    if not allowed_file(original_filename):
        raise ValueError(f"File type not allowed. Allowed: {ALLOWED_EXTENSIONS}")

    is_valid, size = validate_file_size(file)
    if not is_valid:
        raise ValueError(f"File {size:.2f}MB exceeds {Config.MAX_FILE_MB}MB limit")

    filename = secure_filename(original_filename)
    fs = Database.get_gridfs()

    file_id = fs.put(
        file,
        filename=filename,
        upload_date=datetime.utcnow(),
        content_type=getattr(file, "content_type", "audio/mpeg"),
    )
    return file_id


def get_audio_from_gridfs(file_id):
    """
    Retrieve audio file from GridFS.

    Args:
        file_id: GridFS file ObjectId

    Returns:
        GridOut object
    """
    fs = Database.get_gridfs()
    return fs.get(ObjectId(file_id))


def delete_audio_from_gridfs(file_id):
    """
    Delete audio file from GridFS.

    Args:
        file_id: GridFS file ObjectId
    """
    fs = Database.get_gridfs()
    fs.delete(ObjectId(file_id))
