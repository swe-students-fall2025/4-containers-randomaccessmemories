"""Tests for storage and database functionality."""

import os
import sys
from io import BytesIO

import pytest

from app.config import Config
from app.db import Database, get_notes_collection, get_recordings_collection
from app.storage import allowed_file, save_audio_to_gridfs, validate_file_size

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_allowed_file_valid():
    """Test allowed_file with valid extensions."""
    assert allowed_file("test.wav") is True
    assert allowed_file("audio.mp3") is True
    assert allowed_file("voice.m4a") is True
    assert allowed_file("recording.ogg") is True


def test_allowed_file_invalid():
    """Test allowed_file with invalid extensions."""
    assert allowed_file("document.txt") is False
    assert allowed_file("image.jpg") is False
    assert allowed_file("noextension") is False


def test_validate_file_size_small():
    """Test file size validation for small file."""
    small_file = BytesIO(b"a" * 1024)  # 1KB
    is_valid, size = validate_file_size(small_file)
    assert is_valid is True
    assert size < 1  # Less than 1MB


def test_validate_file_size_large():
    """Test file size validation for large file."""
    # Create file larger than MAX_FILE_MB
    large_size = (Config.MAX_FILE_MB + 1) * 1024 * 1024
    large_file = BytesIO(b"a" * large_size)
    is_valid, size = validate_file_size(large_file)
    assert is_valid is False
    assert size > Config.MAX_FILE_MB


def test_database_connection():
    """Test database connection."""
    db = Database.get_db()
    assert db is not None
    assert db.name == Config.MONGO_DB


def test_get_collections():
    """Test collection getters."""
    recordings = get_recordings_collection()
    notes = get_notes_collection()
    assert recordings is not None
    assert notes is not None
    assert recordings.name == "recordings"
    assert notes.name == "notes"


def test_gridfs_initialization():
    """Test GridFS initialization."""
    fs = Database.get_gridfs()
    assert fs is not None


@pytest.fixture
def mock_audio_file():
    """Create mock audio file for testing."""
    content = b"fake audio content" * 100
    file = BytesIO(content)
    file.content_type = "audio/wav"
    return file


def test_save_audio_invalid_extension():
    """Test saving audio with invalid extension."""
    mock_audio = BytesIO(b"fake audio content" * 100)
    mock_audio.content_type = "audio/wav"

    with pytest.raises(ValueError, match="not allowed"):
        save_audio_to_gridfs(mock_audio, "test.txt")


def test_save_audio_file_too_large():
    """Test saving audio file that's too large."""
    # Create oversized file
    large_size = (Config.MAX_FILE_MB + 1) * 1024 * 1024
    large_file = BytesIO(b"a" * large_size)
    large_file.content_type = "audio/wav"

    with pytest.raises(ValueError, match="exceeds"):
        save_audio_to_gridfs(large_file, "large.wav")


def test_save_and_retrieve_audio(
    mock_audio_file,
):  # pylint: disable=redefined-outer-name
    """Test saving and retrieving audio file."""
    from app.storage import (  # pylint: disable=import-outside-toplevel
        delete_audio_from_gridfs,
        get_audio_from_gridfs,
    )

    # Save file
    file_id = save_audio_to_gridfs(mock_audio_file, "test.wav")
    assert file_id is not None

    # Retrieve file
    retrieved = get_audio_from_gridfs(file_id)
    assert retrieved is not None
    assert retrieved.filename == "test.wav"

    # Cleanup
    delete_audio_from_gridfs(file_id)
