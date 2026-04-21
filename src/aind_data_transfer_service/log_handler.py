"""Module to handle logging submit job requests"""

import logging
from typing import Any
from enum import Enum


class EventType(str, Enum):
    """Enum for event types in structured logging"""

    STAGE_START = "stage_start"
    STAGE_COMPLETE = "stage_complete"

def log_stage_event(message: str, event_type: str, **extra_fields: Any) -> None:
    """Emit a structured log record for stage lifecycle events."""

    logging.info(
        message,
        extra={"event_type": event_type, **extra_fields},
    )


def log_submit_job_request(content: Any) -> None:
    """
    Parses content object to log any lines with a subject_id and
    acquisition_name.

    Parameters
    ----------
    content : Any
      Pulled from request json, which may or may not return expected dict
    """
    if isinstance(content, list) and all(
        isinstance(row, dict) for row in content
    ):
        for row in content:
            subject_id = row.get("subject_id")
            acquisition_name = row.get("s3_prefix")
            log_stage_event(
                "Handling request",
                event_type=EventType.STAGE_START,
                subject_id=subject_id,
                acquisition_name=acquisition_name,
            )
