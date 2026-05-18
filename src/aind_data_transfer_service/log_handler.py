"""Module to handle logging submit job requests"""

import logging
from enum import Enum
from typing import Any


class EventType(str, Enum):
    """Enum for event types in structured logging"""

    STAGE_START = "stage_start"
    STAGE_COMPLETE = "stage_complete"
    STAGE_FAILURE = "stage_failure"


def log_submit_job_request(
    content: Any, event_type: EventType | None = None
) -> None:
    """
    Parses content object to log any lines with a subject_id and
    acquisition_name.

    Parameters
    ----------
    content : Any
      Pulled from request json, which may or may not return expected dict
    event_type: EventType |  None
      Type of event to log. Default is None.
    """
    upload_jobs = content.get("upload_jobs")
    if (
        upload_jobs is not None
        and isinstance(upload_jobs, list)
        and all(isinstance(row, dict) for row in upload_jobs)
    ):
        for row in upload_jobs:
            subject_id = row.get("subject_id")
            acquisition_name = row.get("s3_prefix")
            extra_info = {
                "subject_id": subject_id,
                "acquisition_name": acquisition_name,
            }
            if event_type is not None:
                extra_info["event_type"] = event_type
            logging.info("Handling request", extra=extra_info)
