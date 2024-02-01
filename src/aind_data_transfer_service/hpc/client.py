"""Module to manage connection with hpc cluster"""

import json
from typing import List, Optional, Union

import requests
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings
from requests.models import Response

from aind_data_transfer_service.hpc.models import HpcJobSubmitSettings


class HpcClientConfigs(BaseSettings):
    """Configs needed to connect to the hpc cluster"""

    hpc_host: str = Field(...)
    hpc_port: Optional[int] = Field(default=None)
    hpc_api_endpoint: Optional[str] = Field(default=None)
    hpc_username: str = Field(...)
    hpc_password: SecretStr = Field(...)
    hpc_token: SecretStr = Field(...)

    @field_validator("hpc_host", "hpc_api_endpoint", mode="before")
    def _strip_slash(cls, input_str: Optional[str]):
        """Strips trailing slash from domain."""
        return None if input_str is None else input_str.strip("/")

    @property
    def hpc_url(self) -> str:
        """Construct base url from host, port, and api endpoint"""
        base_url = f"http://{self.hpc_host}"
        if self.hpc_port is not None:
            base_url = base_url + f":{self.hpc_port}"
        if self.hpc_api_endpoint:
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
    def _jobs_url(self):
        """Url to check statuses of all jobs"""
        return f"{self.configs.hpc_url}/jobs"

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

    def get_jobs(self) -> Response:
        """Get status of job"""
        response = requests.get(
            url=self._jobs_url,
            headers=self.__headers,
        )
        return response

    def submit_job(self, job_def: dict) -> Response:
        """Submit a job defined by job def"""
        response = requests.post(
            url=self._job_submit_url, json=job_def, headers=self.__headers
        )
        return response

    def submit_hpc_job(
        self,
        script: str,
        job: Optional[HpcJobSubmitSettings] = None,
        jobs: Optional[List[HpcJobSubmitSettings]] = None,
    ) -> Response:
        """
        Submit a job following the v0.0.36 Slurm rest api job submission guide
        Parameters
        ----------
        script : str
          Executable script (full contents) to run in batch step
        job : Optional[HpcJobSubmitSettings]
          v0.0.36_job_properties (Default is None)
        jobs : Optional[List[HpcJobSubmitSettings]]
          List of properties of an HetJob (Default is None)

        Returns
        -------
        Response

        """
        # Assert at least one of job or jobs is defined
        assert job is not None or jobs is not None
        # Assert not both job and jobs are defined
        assert job is None or jobs is None
        if job is not None:
            job_def = {
                "job": json.loads(job.model_dump_json(exclude_none=True)),
                "script": script,
            }
        else:
            job_def = {
                "jobs": [
                    json.loads(j.model_dump_json(exclude_none=True))
                    for j in jobs
                ],
                "script": script,
            }

        response = requests.post(
            url=self._job_submit_url, json=job_def, headers=self.__headers
        )
        return response
