"""Tests server module."""

import asyncio
import os
import unittest
from unittest import mock

from bs4 import BeautifulSoup
from fastapi.testclient import TestClient
from starlette.config import environ

from aind_data_transfer_gui.jobs_manager import ManageJobsDatabase
from aind_data_transfer_gui.server import app

# Set the secret keys for testing
environ["SECRET_KEY"] = os.urandom(32).hex()
environ["CSRF_SECRET_KEY"] = os.urandom(32).hex()
client = TestClient(app)

test_directory = os.path.dirname(os.path.abspath(__file__))
templates_directory = os.path.join(
    test_directory, "src/aind_data_transfer_gui/templates"
)


class TestServer(unittest.TestCase):
    """Tests main server."""

    def test_index(self):
        """Tests that form renders at startup as expected."""
        mock_jobs_db = mock.Mock(spec=ManageJobsDatabase)
        mock_jobs_db.retrieve_all_jobs.return_value = []
        with mock.patch.object(app, "jobs_db", mock_jobs_db):
            response = client.get("/")
            self.assertEqual(response.status_code, 200)
            self.assertIn("Add a New Upload Job", response.text)

    def test_submit_form(self):
        """Tests that form submits as expected."""

        async def submit_form_async():
            """async test of submit form to get form data and csrf token"""
            mock_jobs_db = mock.Mock(spec=ManageJobsDatabase)
            form_data = {
                "source": "/some/source/path",
                "experiment_type": "MESOSPIM",
                "acquisition_datetime": "2023-05-12T04:12",
                "modality": "ECEPHYS",
            }
            mock_jobs_db.retrieve_all_jobs.return_value = [form_data]
            with mock.patch.object(app, "jobs_db", mock_jobs_db):
                response = client.get(
                    "/"
                )  # Fetch the form to get the CSRF token
                soup = BeautifulSoup(response.text, "html.parser")
                csrf_token = soup.find("input", attrs={"name": "csrf_token"})[
                    "value"
                ]

                headers = {"X-CSRF-Token": csrf_token}
                response = client.post("/", json=form_data, headers=headers)

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.template.name, "jobs.html")

                jobs = mock_jobs_db.retrieve_all_jobs()
                self.assertEqual(len(jobs), 1)
                self.assertEqual(jobs[0]["source"], "/some/source/path")
                self.assertEqual(jobs[0]["experiment_type"], "MESOSPIM")
                self.assertEqual(
                    jobs[0]["acquisition_datetime"], "2023-05-12T04:12"
                )
                self.assertEqual(jobs[0]["modality"], "ECEPHYS")

        loop = asyncio.get_event_loop()
        loop.run_until_complete(submit_form_async())


if __name__ == "__main__":
    unittest.main()
