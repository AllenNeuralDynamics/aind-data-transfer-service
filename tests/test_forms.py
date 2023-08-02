"""Tests forms module."""

import unittest
from unittest.mock import MagicMock
from aind_data_transfer_gui.forms import JobManifestForm
import json


class TestJobManifestForm(unittest.TestCase):

    def setUp(self):
        self.form_data = {
            "experiment_type": "Test Experiment",
            "acquisition_datetime": "2023-08-01T12:00",
            "modalities": [
                {
                    "modality": "FIP",
                    "source": "sample/source/path"
                },
                {
                    "modality": "POPHYS",
                    "source": "sample/source/path2"
                }
            ]
        }

    def test_to_job_string(self):
        request = MagicMock()
        form = JobManifestForm(data=self.form_data, request=request)
        expected_json = {
            "experiment_type": "Test Experiment",
            "acquisition_datetime": "2023-08-01T12:00",
            "modalities": [
                {
                    "modality": "FIP",
                    "source": "sample/source/path"
                },
                {
                    "modality": "POPHYS",
                    "source": "sample/source/path2"
                }
            ]
        }
        self.assertEqual(form.to_job_string(), json.dumps(expected_json))


if __name__ == '__main__':
    unittest.main()
