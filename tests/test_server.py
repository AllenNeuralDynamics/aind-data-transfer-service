"""Example test template."""

import os
import unittest
import asyncio
from fastapi.testclient import TestClient
from starlette.config import environ
from unittest.mock import patch
from starlette_wtf import csrf
from bs4 import BeautifulSoup

from aind_data_transfer_gui.server import app
from aind_data_transfer_gui.forms import UploadJobForm


# Set the secret keys for testing
environ["SECRET_KEY"] = os.urandom(32).hex()
environ["CSRF_SECRET_KEY"] = os.urandom(32).hex()
client = TestClient(app)


class TestServer(unittest.TestCase):
    """Server Test Class"""

    def test_index(self):
        """Tests that form renders as expected."""
        response = client.get("/")
        assert response.status_code == 200
        assert "Add a New Upload Job" in response.text

    def test_submit_form(self):
        """Tests that form submits as expected."""
        async def submit_form_async():
            response = client.get("/")  # Fetch the form to get the CSRF token
            soup = BeautifulSoup(response.text, "html.parser")
            csrf_token = soup.find("input", attrs={"name": "csrf_token"})["value"]

            form_data = {
                "experiment_type": "MESOSPIM",
                "acquisition_datetime": "2023-06-05T14:04:00",
                "modality": "ECEPHYS",
                "source": "/some/source/path"
            }

            headers = {"X-CSRF-Token": csrf_token}
            response = client.post("/", json=form_data, headers=headers)

            assert response.status_code == 200
            assert response.text == "SUCCESS"

        loop = asyncio.get_event_loop()
        loop.run_until_complete(submit_form_async())


if __name__ == "__main__":
    unittest.main()
