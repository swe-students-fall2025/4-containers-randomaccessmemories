"""PyMongo and GridFS connection utilities."""

from pymongo import MongoClient
from gridfs import GridFS
from .config import Config


class Database:
    """MongoDB connection singleton."""

    _client = None
    _db = None
    _fs = None

    @classmethod
    def get_client(cls):
        """Get MongoDB client."""
        if cls._client is None:
            cls._client = MongoClient(Config.MONGO_URI)
        return cls._client

    @classmethod
    def get_db(cls):
        """Get database instance."""
        if cls._db is None:
            cls._db = cls.get_client()[Config.MONGO_DB]
        return cls._db

    @classmethod
    def get_gridfs(cls):
        """Get GridFS for file storage."""
        if cls._fs is None:
            cls._fs = GridFS(cls.get_db())
        return cls._fs

    @classmethod
    def close(cls):
        """Close database connection."""
        if cls._client:
            cls._client.close()
            cls._client = None
            cls._db = None
            cls._fs = None


def get_recordings_collection():
    """Get recordings collection."""
    return Database.get_db().recordings


def get_notes_collection():
    """Get notes collection."""
    return Database.get_db().notes


# Add these two helper functions for routes.py compatibility
def get_db():
    """Get database instance (helper for routes)."""
    return Database.get_db()


def get_fs():
    """Get GridFS instance (helper for routes)."""
    return Database.get_gridfs()
