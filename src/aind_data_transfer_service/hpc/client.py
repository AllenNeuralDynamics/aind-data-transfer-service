"""Module to manage connection with hpc cluster"""

from typing import Union

import requests
from pydantic import BaseSettings, Field, SecretStr, validator
from requests.models import Response


class HpcClientConfigs(BaseSettings):
    """Configs needed to connect to the hpc cluster"""

    partition: str = Field(
        ..., description="Partition to submit tasks to (also known as a queue)"
    )
    host: str = Field(...)
    username: str = Field(...)
    password: SecretStr = Field(...)
    token: SecretStr = Field(...)

    @validator("host", pre=True)
    def _strip_trailing_slash(cls, input_host):
        """Strips trailing slash from domain."""
        return input_host.strip("/")


class HpcClient:
    """Class to manage client api"""

    def __init__(self, configs: HpcClientConfigs):
        """Class constructor"""
        self.configs = configs

    @property
    def _job_submit_url(self):
        """Url for job submission"""
        return f"{self.configs.host}/job/submit"

    @property
    def _node_status_url(self):
        """Url to check status of nodes"""
        return f"{self.configs.host}/nodes"

    @property
    def _job_status_url(self):
        """Url to check status of job"""
        return f"{self.configs.host}/job"

    @property
    def __headers(self):
        """Headers needed for rest api"""
        return {
            "X-SLURM-USER-NAME": self.configs.username,
            "X-SLURM-USER-PASSWORD": self.configs.password.get_secret_value(),
            "X-SLURM-USER-TOKEN": self.configs.token.get_secret_value(),
        }

    def get_node_status(self) -> Response:
        """Get status of nodes"""
        response = requests.get(
            url=self._node_status_url, headers=self.__headers
        )
        return response

    def get_job_status(self, job_id: Union[str, int]) -> Response:
        """Get status of job"""
        response = requests.get(
            url=self._job_status_url + "/" + str(job_id),
            headers=self.__headers,
        )
        return response

    def submit_job(self, job_def: dict) -> Response:
        """Submit a job defined by job def"""
        response = requests.post(
            url=self._job_submit_url, json=job_def, headers=self.__headers
        )
        return response
