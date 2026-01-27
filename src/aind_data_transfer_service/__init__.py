"""Package for data transfer service api"""

import logging.config
import os
from datetime import datetime, timezone
from logging import LogRecord

import yaml
from pythonjsonlogger import json as log_json

__version__ = "2.0.1"


# We want to standardize the timestamp format to UTC and ISO-8601, which
# requires a custom formatter and can't be done through configuration only.
class CustomJsonFormatter(log_json.JsonFormatter):
    """Custom class to format log timestamps as ISO-8601 UTC"""

    def formatTime(self, record: LogRecord, datefmt=None) -> str:
        """
        Format timestamp as ISO-8601 UTC
        Parameters
        ----------
        record : LogRecord
        datefmt : str, optional
          Default is None

        Returns
        -------
        str

        """
        dt = datetime.fromtimestamp(record.created, tz=timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


if os.path.isfile(os.getenv("LOGGING_CONFIG_FILE", "log_config.yaml")):
    config_path = os.getenv("LOGGING_CONFIG_FILE", "log_config.yaml")
    with open(config_path, "rt") as f:
        config = yaml.safe_load(f.read())
    logging.config.dictConfig(config)
