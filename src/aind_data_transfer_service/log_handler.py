"""Module to handle logging submit job requests"""

import logging
from typing import Any


def log_submit_job_request(content: Any):
    """
    Parses content object to log any lines with a subject_id and s3_prefix.
    TODO: This may need to be updated if session_ids are centralized.
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
            session_id = row.get("s3_prefix")
            logging.info(
                "Handling request",
                extra={"subject_id": subject_id, "session_id": session_id},
            )
