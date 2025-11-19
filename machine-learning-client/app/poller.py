"""Poller: find pending recordings and process them.

This module implements `process_pending()` which is invoked by the
entrypoint runner. It uses `app.db` helpers to fetch pending records,
loads audio from GridFS, calls the STT and NLP modules, stores results,
and updates statuses. The implementation is defensive and logs errors
per-record to avoid crashing the whole loop.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from bson import ObjectId

from . import db


logger = logging.getLogger(__name__)


def _safe_transcribe(audio_bytes: bytes) -> Optional[Dict[str, Any]]:
    """Call STT provider; return dict with 'text' and optional 'confidence'.

    This wrapper imports the STT implementation lazily so the module can
    be mocked or replaced during testing.
    """
    try:
        from . import stt_openai as stt  # type: ignore  # pylint: disable=import-outside-toplevel

        text = stt.transcribe(audio_bytes)
        if isinstance(text, dict):
            return text
        return {"text": text}
    except Exception as exc:  # pragma: no cover  # pylint: disable=broad-exception-caught
        logger.exception("STT failed: %s", exc)
        return None


def _safe_generate_notes(transcript: str) -> Optional[Dict[str, Any]]:
    """Call NLP provider to generate structured notes from transcript."""
    try:
        from . import nlp_openai as nlp  # type: ignore  # pylint: disable=import-outside-toplevel

        note = nlp.generate_structured_note(transcript)
        return note
    except Exception as exc:  # pragma: no cover  # pylint: disable=broad-exception-caught
        logger.exception("NLP generation failed: %s", exc)
        return None


def process_pending(limit: int = 10) -> int:
    """Process up to `limit` pending recordings.

    Returns the number of records processed.
    """
    processed = 0
    docs = db.find_pending(limit=limit)
    logger.info("Found %d pending recordings", len(docs))

    for doc in docs:
        rid = doc.get("_id")
        try:
            logger.info("Processing record %s", rid)
            db.mark_record_status(rid, "processing")

            file_id = doc.get("file_id")
            if not file_id:
                raise RuntimeError("record missing file_id")

            # load audio bytes from GridFS
            audio_bytes = db.get_audio(ObjectId(file_id))

            # transcribe
            stt_result = _safe_transcribe(audio_bytes)
            if not stt_result or "text" not in stt_result:
                raise RuntimeError("stt returned no transcription")

            transcription_id = db.insert_transcription(
                rid, stt_result.get("text"), stt_result.get("confidence")
            )

            # generate structured note
            note = _safe_generate_notes(stt_result.get("text"))
            if note:
                db.insert_structured_note(transcription_id, note)

            # Insert a `notes` document compatible with the web-app schema
            # so the web UI can read summaries/keywords/action items directly.
            try:
                summary = note.get("summary") if note else ""
                # prefer an explicit keywords field, otherwise try highlights
                keywords = (
                    note.get("keywords")
                    if note and note.get("keywords") is not None
                    else note.get("highlights") if note else []
                )
                action_items = note.get("action_items") if note else []
                transcript_text = stt_result.get("text")
                # if the original record used 'file_id', mirror it to
                # audio_gridfs_id for web-app compatibility
                file_id = doc.get("file_id") or doc.get("audio_gridfs_id")
                db.insert_note(
                    rid,
                    transcript_text,
                    keywords or [],
                    summary or "",
                    action_items or [],
                    language=stt_result.get("language"),
                )
                if file_id:
                    db.update_record(
                        rid,
                        {
                            "audio_gridfs_id": file_id,
                            "language": stt_result.get("language"),
                        },
                    )
            except Exception:  # pylint: disable=broad-exception-caught
                logger.exception(
                    "Failed to write web-app-compatible notes document for %s",
                    rid,
                )

            db.mark_record_status(rid, "done")
            processed += 1
            logger.info("Record %s processed successfully", rid)

        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.exception("Failed to process record %s: %s", rid, exc)
            try:
                db.set_record_error(rid, str(exc))
            except Exception:  # pylint: disable=broad-exception-caught
                logger.exception("Failed to set error status for record %s", rid)

    return processed


__all__ = ["process_pending"]
