"""Tests server module"""
import unittest
from aind_data_transfer_gui.server import app
import asyncio
from fastapi.testclient import TestClient
from bs4 import BeautifulSoup


class TestIndex(unittest.TestCase):
    client = TestClient(app)

    def setUp(self):
        # Set up the event loop for async tests
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(None)

    def tearDown(self):
        # Clean up the event loop
        self.loop.close()

    def run_async(self, coro):
        return self.loop.run_until_complete(coro)

    def test_index(self):
        """Tests that form renders at startup as expected."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Add a New Upload Job", response.text)

    def test_submit_form(self):
        """Tests that form submits as expected."""

        async def submit_form_async():
            """async test of submit form to get form data and csrf token"""
            form_data = {
                "source": "/some/source/path",
                "experiment_type": "MESOSPIM",
                "acquisition_datetime": "2023-05-12T04:12",
                "modalities": '[]',
            }
            response = self.client.get("/")  # Fetch the form to get the CSRF token
            soup = BeautifulSoup(response.text, "html.parser")
            csrf_token = soup.find("input", attrs={"name": "csrf_token"})[
                "value"
            ]

            headers = {"X-CSRF-Token": csrf_token}
            response = self.client.post("/", json=form_data, headers=headers)

            self.assertEqual(response.status_code, 200)

        self.run_async(submit_form_async())

    def test_add_modality(self):
        """Tests adding a modality to the form."""

        async def add_modality_async():
            response = self.client.get("/")
            soup = BeautifulSoup(response.text, "html.parser")
            csrf_token = soup.find("input", attrs={"name": "csrf_token"})["value"]

            headers = {"X-CSRF-Token": csrf_token}
            form_data = {
                "add_modality": "true",
            }
            response = self.client.post("/", data=form_data, headers=headers)

            self.assertEqual(response.status_code, 200)
            # Add more assertions to check if the modality was added as expected

        self.run_async(add_modality_async())

    def test_add_job(self):
        """Tests adding a job to the form with mock validation."""

        async def add_job_async():
            response = self.client.get("/")
            form_data = {
                            "add_job": "true",
                            "submit_jobs": "false",
                            "add_modality": "false",
                            "experiment_type": "Test Experiment",
                            "acquisition_datetime": "2023-08-01T12:00",
                            "modalities": [
                                {
                                    "modality": "FIP",
                                    "source": "sample/source/path"
                                },
                            ]
                        }
            soup = BeautifulSoup(response.text, "html.parser")
            csrf_token = soup.find("input", attrs={"name": "csrf_token"})["value"]

            headers = {"X-CSRF-Token": csrf_token}
            response = self.client.post("/", data=form_data, headers=headers)

            self.assertEqual(response.status_code, 200)

            # Retrieve the updated form data from the response
            updated_form = response.context.get("form")

            # Validate that the job data validation function was called
            self.assertTrue(updated_form.validate)

        self.run_async(add_job_async())


if __name__ == '__main__':
    unittest.main()
