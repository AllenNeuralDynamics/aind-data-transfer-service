"""Module to test hpc client classes"""

import unittest
from unittest.mock import MagicMock, patch

from aind_data_transfer_service.hpc.client import HpcClient, HpcClientConfigs
from aind_data_transfer_service.hpc.models import HpcJobSubmitSettings


class TestHpcClientConfigs(unittest.TestCase):
    """Tests methods in HpcClientConfigs class"""

    def test_hpc_client_configs(self):
        """Tests that attributes are set correctly"""
        hpc_client_configs = HpcClientConfigs(
            hpc_host="hpc_host",
            hpc_port=80,
            hpc_api_endpoint="api/slurm/v0.0.39",
            hpc_username="hpc_username",
            hpc_password="hpc_password",
            hpc_token="hpc_jwt",
        )
        self.assertEqual("hpc_host", hpc_client_configs.hpc_host)
        self.assertEqual(80, hpc_client_configs.hpc_port)
        self.assertEqual(
            "http://hpc_host:80/api/slurm/v0.0.39", hpc_client_configs.hpc_url
        )
        self.assertEqual("hpc_username", hpc_client_configs.hpc_username)
        self.assertEqual(
            "hpc_password", hpc_client_configs.hpc_password.get_secret_value()
        )
        self.assertEqual(
            "hpc_jwt", hpc_client_configs.hpc_token.get_secret_value()
        )


class TestHpcClient(unittest.TestCase):
    """Tests methods in HpcClient class"""

    hpc_client_configs = HpcClientConfigs(
        hpc_host="hpc_host",
        hpc_username="hpc_username",
        hpc_password="hpc_password",
        hpc_token="hpc_jwt",
    )

    def test_properties(self):
        """Tests that the url properties are correct."""
        hpc_client = HpcClient(configs=self.hpc_client_configs)
        self.assertEqual("http://hpc_host/job", hpc_client._job_status_url)
        self.assertEqual("http://hpc_host/nodes", hpc_client._node_status_url)
        self.assertEqual(
            "http://hpc_host/job/submit", hpc_client._job_submit_url
        )

    @patch("requests.get")
    def test_node_status_response(self, mock_get: MagicMock):
        """Tests that the node status request is sent correctly."""
        mock_get.return_value = {"message": "A mocked message"}
        hpc_client = HpcClient(configs=self.hpc_client_configs)
        response = hpc_client.get_node_status()
        self.assertEqual({"message": "A mocked message"}, response)
        mock_get.assert_called_once_with(
            url="http://hpc_host/nodes",
            headers={
                "X-SLURM-USER-NAME": "hpc_username",
                "X-SLURM-USER-PASSWORD": "hpc_password",
                "X-SLURM-USER-TOKEN": "hpc_jwt",
            },
        )

    @patch("requests.get")
    def test_job_status_response(self, mock_get: MagicMock):
        """Tests that the job status request is sent correctly"""
        mock_get.return_value = {"message": "A mocked message"}
        hpc_client = HpcClient(configs=self.hpc_client_configs)
        response = hpc_client.get_job_status(job_id="12345")
        self.assertEqual({"message": "A mocked message"}, response)
        mock_get.assert_called_once_with(
            url="http://hpc_host/job/12345",
            headers={
                "X-SLURM-USER-NAME": "hpc_username",
                "X-SLURM-USER-PASSWORD": "hpc_password",
                "X-SLURM-USER-TOKEN": "hpc_jwt",
            },
        )

    @patch("requests.get")
    def test_get_jobs_response(self, mock_get: MagicMock):
        """Tests that the job status request is sent correctly"""
        mock_get.return_value = {"message": "A mocked message"}
        hpc_client = HpcClient(configs=self.hpc_client_configs)
        response = hpc_client.get_jobs()
        self.assertEqual({"message": "A mocked message"}, response)
        mock_get.assert_called_once_with(
            url="http://hpc_host/jobs",
            headers={
                "X-SLURM-USER-NAME": "hpc_username",
                "X-SLURM-USER-PASSWORD": "hpc_password",
                "X-SLURM-USER-TOKEN": "hpc_jwt",
            },
        )

    @patch("requests.post")
    def test_submit_job_response(self, mock_post: MagicMock):
        """Tests that the job submission request is sent correctly"""
        mock_post.return_value = {"message": "A mocked message"}
        hpc_client = HpcClient(configs=self.hpc_client_configs)
        response = hpc_client.submit_job(job_def={"job": {"some_job"}})
        self.assertEqual({"message": "A mocked message"}, response)
        mock_post.assert_called_once_with(
            url="http://hpc_host/job/submit",
            json={"job": {"some_job"}},
            headers={
                "X-SLURM-USER-NAME": "hpc_username",
                "X-SLURM-USER-PASSWORD": "hpc_password",
                "X-SLURM-USER-TOKEN": "hpc_jwt",
            },
        )

    @patch("requests.post")
    def test_submit_hpc_job_response(self, mock_post: MagicMock):
        """Tests that the job submission request is sent correctly"""
        mock_post.return_value = {"message": "A mocked message"}
        hpc_client = HpcClient(configs=self.hpc_client_configs)
        response = hpc_client.submit_hpc_job(
            script="Hello World!", job=HpcJobSubmitSettings(name="test_job")
        )
        self.assertEqual({"message": "A mocked message"}, response)
        mock_post.assert_called_once_with(
            url="http://hpc_host/job/submit",
            json={"script": "Hello World!", "job": {"name": "test_job"}},
            headers={
                "X-SLURM-USER-NAME": "hpc_username",
                "X-SLURM-USER-PASSWORD": "hpc_password",
                "X-SLURM-USER-TOKEN": "hpc_jwt",
            },
        )

    @patch("requests.post")
    def test_submit_hpc_jobs_response(self, mock_post: MagicMock):
        """Tests that the jobs submission request is sent correctly"""
        mock_post.return_value = {"message": "A mocked message"}
        hpc_client = HpcClient(configs=self.hpc_client_configs)
        jobs = [
            HpcJobSubmitSettings(name="test_job1"),
            HpcJobSubmitSettings(name="test_job2"),
        ]
        response = hpc_client.submit_hpc_job(script="Hello World!", jobs=jobs)
        self.assertEqual({"message": "A mocked message"}, response)
        mock_post.assert_called_once_with(
            url="http://hpc_host/job/submit",
            json={
                "script": "Hello World!",
                "jobs": [{"name": "test_job1"}, {"name": "test_job2"}],
            },
            headers={
                "X-SLURM-USER-NAME": "hpc_username",
                "X-SLURM-USER-PASSWORD": "hpc_password",
                "X-SLURM-USER-TOKEN": "hpc_jwt",
            },
        )


if __name__ == "__main__":
    unittest.main()
