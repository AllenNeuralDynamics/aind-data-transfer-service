"""Tests methods in log_handler module"""

import unittest
from unittest.mock import MagicMock, call, patch

from aind_data_transfer_service.log_handler import LoggingConfigs, get_logger


class TestLoggingConfigs(unittest.TestCase):
    """Tests LoggingConfigs class"""

    def test_app_name(self):
        """Tests app_name property"""

        configs = LoggingConfigs(env_name="test", loki_uri=None)
        self.assertEqual("aind-data-transfer-service-test", configs.app_name)

    def test_loki_path(self):
        """Tests app_name property"""

        configs = LoggingConfigs(env_name="test", loki_uri="example.com")
        self.assertEqual("example.com/loki/api/v1/push", configs.loki_path)

    @patch("logging.getLogger")
    @patch("aind_data_transfer_service.log_handler.LokiHandler")
    def test_get_logger(
        self, mock_loki_handler: MagicMock, mock_get_logger: MagicMock
    ):
        """Tests get_logger method"""

        mock_get_logger.return_value = MagicMock()
        configs = LoggingConfigs(
            env_name="test", loki_uri="example.com", log_level="WARNING"
        )
        _ = get_logger(log_configs=configs)
        mock_loki_handler.assert_called_once_with(
            url="example.com/loki/api/v1/push",
            version="1",
            tags={"application": "aind-data-transfer-service-test"},
        )
        mock_get_logger.assert_has_calls(
            [call("aind_data_transfer_service.log_handler")]
        )
        mock_get_logger.return_value.setLevel.assert_called_once_with(30)
        mock_get_logger.return_value.addHandler.assert_called_once()


if __name__ == "__main__":
    unittest.main()
