"""Tests for search functionality on notes collection."""

import pytest
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.db import get_notes_collection, Database


@pytest.fixture
def sample_notes():
    """Insert sample notes for testing search."""
    notes_col = get_notes_collection()

    # Clean up first
    notes_col.delete_many({"_test": True})

    # Insert test data
    test_notes = [
        {
            "_test": True,
            "transcript": "Meeting about project planning for Q4",
            "summary": "Discussed quarterly goals and milestones",
            "keywords": "planning, goals, Q4, milestones",
            "action_items": "Schedule follow-up meeting",
            "created_at": datetime.utcnow(),
        },
        {
            "_test": True,
            "transcript": "Interview with candidate for engineering role",
            "summary": "Technical interview went well",
            "keywords": "interview, hiring, engineering, technical",
            "action_items": "Send offer letter by Friday",
            "created_at": datetime.utcnow(),
        },
        {
            "_test": True,
            "transcript": "Budget review for marketing campaign",
            "summary": "Approved additional budget for Q1 campaign",
            "keywords": "budget, marketing, campaign, Q1",
            "action_items": "Allocate funds to campaign",
            "created_at": datetime.utcnow(),
        },
    ]

    notes_col.insert_many(test_notes)
    yield

    # Cleanup
    notes_col.delete_many({"_test": True})
    Database.close()


def test_search_in_transcript(sample_notes):
    """Test searching notes by transcript content."""
    notes_col = get_notes_collection()

    results = list(
        notes_col.find(
            {"_test": True, "transcript": {"$regex": "meeting", "$options": "i"}}
        )
    )

    assert len(results) > 0
    assert any("meeting" in note["transcript"].lower() for note in results)


def test_search_in_keywords(sample_notes):
    """Test searching notes by keywords."""
    notes_col = get_notes_collection()

    results = list(
        notes_col.find(
            {"_test": True, "keywords": {"$regex": "hiring", "$options": "i"}}
        )
    )

    assert len(results) > 0
    assert any("hiring" in note["keywords"].lower() for note in results)


def test_search_case_insensitive(sample_notes):
    """Test that search is case insensitive."""
    notes_col = get_notes_collection()

    # Search with uppercase
    results_upper = list(
        notes_col.find(
            {"_test": True, "transcript": {"$regex": "MEETING", "$options": "i"}}
        )
    )

    # Search with lowercase
    results_lower = list(
        notes_col.find(
            {"_test": True, "transcript": {"$regex": "meeting", "$options": "i"}}
        )
    )

    assert len(results_upper) == len(results_lower)


def test_search_multiple_fields(sample_notes):
    """Test searching across multiple fields with OR."""
    notes_col = get_notes_collection()

    query = "budget"
    results = list(
        notes_col.find(
            {
                "_test": True,
                "$or": [
                    {"transcript": {"$regex": query, "$options": "i"}},
                    {"summary": {"$regex": query, "$options": "i"}},
                    {"keywords": {"$regex": query, "$options": "i"}},
                    {"action_items": {"$regex": query, "$options": "i"}},
                ],
            }
        )
    )

    assert len(results) > 0


def test_search_no_results(sample_notes):
    """Test search with no matching results."""
    notes_col = get_notes_collection()

    results = list(
        notes_col.find(
            {"_test": True, "transcript": {"$regex": "nonexistent", "$options": "i"}}
        )
    )

    assert len(results) == 0


def test_search_partial_match(sample_notes):
    """Test search with partial word match."""
    notes_col = get_notes_collection()

    results = list(
        notes_col.find(
            {
                "_test": True,
                "keywords": {
                    "$regex": "eng",
                    "$options": "i",
                },  # Should match "engineering"
            }
        )
    )

    assert len(results) > 0
