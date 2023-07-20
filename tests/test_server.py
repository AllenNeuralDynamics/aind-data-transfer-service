"""Tests server module."""

import asyncio
import os
import unittest

from bs4 import BeautifulSoup
from fastapi.testclient import TestClient
from starlette.config import environ

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
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Add a New Upload Job", response.text)

    def test_submit_form(self):
        """Tests that form submits as expected."""

        async def submit_form_async():
            """async test of submit form to get form data and csrf token"""
            response = client.get("/")  # Fetch the form to get the CSRF token
            self.assertEqual(response.status_code, 200)

            soup = BeautifulSoup(response.text, "html.parser")
            csrf_token = soup.find("input", attrs={"name": "csrf_token"})[
                "value"
            ]

            form_data = {
                "experiment_type": "MESOSPIM",
                "acquisition_datetime": "2023-05-12T04:12",
                "modality": "ECEPHYS",
                "source": "/some/source/path",
                "csrf_token": csrf_token,
            }
            job = form_data
            if "csrf_token" in job:
                del job["csrf_token"]

            headers = {"X-CSRF-Token": csrf_token}
            response = client.post("/", json=form_data, headers=headers)

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.template.name, "jobs.html")
            self.assertNotIn("csrf_token", job)

            invalid_form_data = {}
            response = client.post("/", json=invalid_form_data, headers=headers)
            self.assertEqual(response.status_code, 400)

        loop = asyncio.get_event_loop()
        loop.run_until_complete(submit_form_async())


if __name__ == "__main__":
    unittest.main()
