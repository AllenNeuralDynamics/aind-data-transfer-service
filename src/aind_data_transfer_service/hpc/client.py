"""Module to manage connection with hpc cluster"""

from typing import Optional, Union

import requests
from pydantic import BaseSettings, Field, SecretStr, validator
from requests.models import Response


class HpcClientConfigs(BaseSettings):
    """Configs needed to connect to the hpc cluster"""

    hpc_host: str = Field(...)
    hpc_port: Optional[int] = Field(default=None)
    hpc_api_endpoint: Optional[str] = Field(default=None)
    hpc_username: str = Field(...)
    hpc_password: SecretStr = Field(...)
    hpc_token: SecretStr = Field(...)

    @validator("hpc_host", "hpc_api_endpoint", pre=True)
    def _strip_slash(cls, input_str: Optional[str]):
        """Strips trailing slash from domain."""
        return None if input_str is None else input_str.strip("/")

    @property
    def hpc_url(self) -> str:
        """Construct base url from host, port, and api endpoint"""
        base_url = f"http://{self.hpc_host}"
        if self.hpc_port is not None:
            base_url = base_url + f":{self.hpc_port}"
        if self.hpc_api_endpoint is not None:
            base_url = base_url + f"/{self.hpc_api_endpoint}"
        return base_url


class HpcClient:
    """Class to manage client api"""

    def __init__(self, configs: HpcClientConfigs):
        """Class constructor"""
        self.configs = configs

    @property
    def _job_submit_url(self):
        """Url for job submission"""
        return f"{self.configs.hpc_url}/job/submit"

    @property
    def _node_status_url(self):
        """Url to check status of nodes"""
        return f"{self.configs.hpc_url}/nodes"

    @property
    def _job_status_url(self):
        """Url to check status of job"""
        return f"{self.configs.hpc_url}/job"

    @property
    def __headers(self):
        """Headers needed for rest api"""
        return {
            "X-SLURM-USER-NAME": self.configs.hpc_username,
            "X-SLURM-USER-PASSWORD": (
                self.configs.hpc_password.get_secret_value()
            ),
            "X-SLURM-USER-TOKEN": self.configs.hpc_token.get_secret_value(),
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
