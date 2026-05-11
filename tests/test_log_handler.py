"""Tests methods in log_handler module and logging functions in init module"""

import importlib
import unittest
from logging import LogRecord
from unittest.mock import MagicMock, mock_open, patch

import aind_data_transfer_service
from aind_data_transfer_service import CustomJsonFormatter
from aind_data_transfer_service.log_handler import (
    EventType,
    log_stage_event,
    log_submit_job_request,
)


class TestLogHandler(unittest.TestCase):
    """Tests methods in log_handler module"""

    @patch("logging.info")
    def test_log_submit_job_request(self, mock_log: MagicMock):
        """Tests log_submit_job_request"""
        content = [{"s3_prefix": "abc-123", "subject_id": "123456"}]
        log_submit_job_request(content=content)
        mock_log.assert_called_once_with(
            "Handling request",
            extra={
                "event_type": EventType.STAGE_START,
                "subject_id": "123456",
                "acquisition_name": "abc-123",
            },
        )

    @patch("logging.info")
    def test_log_stage_event(self, mock_log: MagicMock):
        """Tests log_stage_event emits structured extra fields."""

        log_stage_event(
            "Completed submit jobs v2 request",
            event_type=EventType.STAGE_COMPLETE,
            dag_id="run_list_of_jobs",
            total_jobs=2,
        )

        mock_log.assert_called_once_with(
            "Completed submit jobs v2 request",
            extra={
                "event_type": EventType.STAGE_COMPLETE,
                "dag_id": "run_list_of_jobs",
                "total_jobs": 2,
            },
        )


class TestCustomJsonFormatter(unittest.TestCase):
    """Tests methods CustomJsonFormatter from init module"""

    @patch("time.time")
    def test_format_time(self, mock_time: MagicMock):
        """Tests formatTime"""
        mock_time.return_value = 1768856252.7829409
        datetime_str = CustomJsonFormatter().formatTime(
            record=LogRecord(
                name="foo",
                level=20,
                pathname="foo.bar",
                lineno=10,
                msg=None,
                args=None,
                exc_info=None,
            )
        )
        expected_datetime_str = "2026-01-19T20:57:32.782941Z"
        self.assertEqual(expected_datetime_str, datetime_str)

    @patch("logging.config.dictConfig")
    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.isfile")
    @patch("logging.info")
    def test_logging_config(
        self,
        mock_log_info: MagicMock,
        mock_isfile: MagicMock,
        mock_file: MagicMock,
        mock_logging_config: MagicMock,
    ):
        """Tests that logging is configured on package init"""
        example_yaml = """
        key: value
        list_items:
          - item1
          - item2
        """
        mock_isfile.return_value = True
        mock_file.return_value.__enter__.return_value.read.return_value = (
            example_yaml
        )
        importlib.reload(aind_data_transfer_service)
        mock_logging_config.assert_called_once_with(
            {"key": "value", "list_items": ["item1", "item2"]}
        )
        mock_log_info.assert_called_once()


if __name__ == "__main__":
    unittest.main()
