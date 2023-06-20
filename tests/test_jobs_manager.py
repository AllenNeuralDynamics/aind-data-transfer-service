"""Tests Jobs Manager."""

import unittest

from aind_data_transfer_gui.jobs_manager import ManageJobsDatabase


class TestManageJobsDatabase(unittest.TestCase):
    """Tests Job Manager."""
    def setUp(self):
        """Initializes manager"""
        self.jobs_db = ManageJobsDatabase()

    def test_create_jobs_table(self):
        """Tests that Jobs table is created as expected."""
        self.assertTrue("jobs" in self.jobs_db.db.table_names())

    def test_insert_job(self):
        """Tests that job is inserted into table as expected."""
        job = {
            "source": "/some/source/path",
            "experiment_type": "MESOSPIM",
            "acquisition_datetime": "2023-05-12T04:12",
            "modality": "ECEPHYS",
        }
        self.jobs_db.insert_job(job)
        jobs = self.jobs_db.retrieve_all_jobs()
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0], job)

    def test_retrieve_all_jobs(self):
        """Tests that all jobs are retrieved as expected."""
        jobs = [
            {
                "source": "/some/source/path",
                "experiment_type": "MESOSPIM",
                "acquisition_datetime": "2023-05-12T04:12",
                "modality": "ECEPHYS",
            },
            {
                "source": "/another/source/path",
                "experiment_type": "SPIM",
                "acquisition_datetime": "2023-05-13T09:30",
                "modality": "ECEPHYS",
            },
        ]
        for job in jobs:
            self.jobs_db.insert_job(job)

        retrieved_jobs = self.jobs_db.retrieve_all_jobs()
        self.assertEqual(len(retrieved_jobs), 2)
        self.assertEqual(retrieved_jobs, jobs)


if __name__ == "__main__":
    unittest.main()
