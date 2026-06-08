"""Module to handle logging submit job requests"""

import logging
from datetime import datetime
from enum import Enum
from typing import Any

from aind_data_schema_models.data_name_patterns import build_data_name


class EventType(str, Enum):
    """Enum for event types in structured logging"""

    STAGE_START = "stage_start"
    STAGE_COMPLETE = "stage_complete"
    STAGE_FAILURE = "stage_failure"


def compute_label(upload_job: dict) -> str:
    """Hack to compute acquisition_name from raw user input. This can be
    cleaned up in the next major release."""
    subject_id = upload_job.get("subject_id")
    acq_datetime = datetime.fromisoformat(upload_job.get("acq_datetime"))
    platform = upload_job.get("platform")
    if platform is not None:
        label = f"{platform['abbreviation']}_{subject_id}"
    else:
        label = subject_id
    return build_data_name(
        label=label,
        creation_datetime=acq_datetime,
    )


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
            acquisition_name = compute_label(row)
            extra_info = {
                "subject_id": subject_id,
                "acquisition_name": acquisition_name,
            }
            if event_type is not None:
                extra_info["event_type"] = event_type
            logging.info("Handling request", extra=extra_info)
