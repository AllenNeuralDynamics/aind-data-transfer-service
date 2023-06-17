"""Example test template."""

import asyncio
import os
import unittest
from fastapi import FastAPI
from bs4 import BeautifulSoup
from fastapi.testclient import TestClient
from starlette.config import environ
from starlette.middleware.sessions import SessionMiddleware
from starlette_wtf import CSRFProtectMiddleware, csrf_protect
from fastapi.templating import Jinja2Templates

from aind_data_transfer_gui.server import app

SECRET_KEY = "test-secret-key"
CSRF_SECRET_KEY = "test-csrf-secret-key"

app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
app.add_middleware(CSRFProtectMiddleware, csrf_secret=CSRF_SECRET_KEY)
templates = Jinja2Templates(directory="src/aind_data_transfer_gui/templates")
client = TestClient(app)


class TestServer(unittest.TestCase):
    """Server Test Class"""

    def test_index(self):
        """Tests that form renders as expected."""
        valid_data = {
            "source": "example_source",
            "experiment_type": "MESOSPIM",
            "acquisition_datetime": "2023-05-12T04:12",
            "modality": "ECEPHYS",
        }
        response = client.post("/", data=valid_data)
        assert response.status_code == 200
        assert "Add a New Upload Job" in response.text

    def test_submit_form(self):
        """Tests that form submits as expected."""

        async def submit_form_async():
            """async test of submit form to get form data and csrf token"""
            response = client.get("/")  # Fetch the form to get the CSRF token
            soup = BeautifulSoup(response.text, "html.parser")
            csrf_token = soup.find("input", attrs={"name": "csrf_token"})[
                "value"
            ]

            form_data = {
                "experiment_type": "MESOSPIM",
                "acquisition_datetime": "2023-05-12T04:12",
                "modality": "ECEPHYS",
                "source": "/some/source/path",
            }

            headers = {"X-CSRF-Token": csrf_token}
            response = client.post("/", json=form_data, headers=headers)

            assert response.status_code == 200
            assert response.text == "SUCCESS"

        loop = asyncio.get_event_loop()
        loop.run_until_complete(submit_form_async())


if __name__ == "__main__":
    unittest.main()
