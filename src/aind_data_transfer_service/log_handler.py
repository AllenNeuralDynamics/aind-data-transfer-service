"""Module to handle setting up logger"""

import logging
from typing import Literal, Optional

from logging_loki import LokiHandler
from pydantic import Field
from pydantic_settings import BaseSettings


class LoggingConfigs(BaseSettings):
    """Configs for logger"""

    env_name: Optional[str] = Field(
        default=None, description="Can be used to help tag logging source."
    )
    loki_uri: Optional[str] = Field(
        default=None, description="URI of Loki logging server."
    )
    log_level: Literal[
        "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
    ] = Field(default="INFO", description="Log level")

    @property
    def app_name(self):
        """Build app name from configs"""
        package_name = __package__
        base_name = package_name.split(".")[0].replace("_", "-")
        app_name = (
            base_name
            if self.env_name is None
            else f"{base_name}-{self.env_name}"
        )
        return app_name

    @property
    def loki_path(self):
        """Full path to log loki messages to"""
        return (
            None
            if self.loki_uri is None
            else f"{self.loki_uri}/loki/api/v1/push"
        )


def get_logger(log_configs: LoggingConfigs) -> logging.Logger:
    """Return a logger that can be used to log messages."""
    level = logging.getLevelName(log_configs.log_level)
    logger = logging.getLogger(__name__)
    logger.setLevel(level)
    if log_configs.loki_uri is not None:
        handler = LokiHandler(
            url=log_configs.loki_path,
            version="1",
            tags={"application": log_configs.app_name},
        )
        logger.addHandler(handler)
    return logger
