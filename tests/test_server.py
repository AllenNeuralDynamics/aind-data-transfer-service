"""Tests server module"""
import unittest
import logging
from unittest.mock import MagicMock, patch
from aind_data_transfer_gui.server import index, app
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

    async def get_mock_request(self, method, data):
        request = MagicMock()
        request.method = method
        request.data.get.side_effect = lambda x: data.get(x)
        return request

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

    def test_post_request_add_modality(self):
        async def test_post_request_add_modality_async():
            # Mock the request object for POST request with 'add_modality'
            request = await self.get_mock_request('POST', {'add_modality': True})
            # Use TestClient to send the POST request to the route
            response = await index(request)

            # soup = BeautifulSoup(response.text, "html.parser")
            # csrf_token = soup.find("input", attrs={"name": "csrf_token"})[
            #     "value"
            # ]
            #
            # headers = {"X-CSRF-Token": csrf_token}
            # response = self.client.post("/", json={'key': 'value'}, headers=headers)
            # # Your assertions for the POST request response
            # self.assertEqual(response.status_code, 200)
            # self.assertEqual(response.json(), {"ReceivedData": {'key': 'value'}})

        self.run_async(test_post_request_add_modality_async())
    async def test_add_modality(self):
        # Simulate a form submission with the "add_modality" key
        form_data = {
            "add_modality": "true",
            # Add other required form data here as needed
        }
        response = await self.client.post("/", data=form_data)
        assert response.status_code == 200
        assert b"jobs.html" in response.content

    # def test_post_request_submit_jobs(self):
    #     async def test_post_request_submit_jobs_async():
    #         # Mock the request object for POST request with 'submit_jobs'
    #         request = MagicMock()
    #         request.method = 'POST'
    #         request.data.get.side_effect = lambda x: {'submit_jobs': True}.get(x)
    #
    #         # Mock the JobManifestForm
    #         job_manifest_form = MagicMock()
    #         job_manifest_form.to_job_string.return_value = '{"experiment_type": "Test",' \
    #                                                        ' "acquisition_datetime": "2023-08-01T12:00",' \
    #                                                        ' "modalities": []}'
    #         job_manifest_form.jobs = []
    #
    #         # Mock JobManifestForm.from_formdata
    #         with patch('aind_data_transfer_gui.server.JobManifestForm.from_formdata', return_value=job_manifest_form):
    #             # Mock the logging.info method
    #             with patch('aind_data_transfer_gui.server.logging.info') as mock_logging_info:
    #                 response = await index(request)
    #
    #         # Assert the response
    #         self.assertEqual(response.template_name, 'jobs.html')
    #         self.assertIn('form', response.context)
    #         self.assertEqual(response.context['form'], job_manifest_form)
    #         mock_logging_info.assert_called_once_with('Will send the following to the HPC: []')
    #
    #     self.run_async(test_post_request_submit_jobs_async())


if __name__ == '__main__':
    unittest.main()
