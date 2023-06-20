"""Module to set up and maintain jobs database."""
import sqlite_utils


class JobsManager:
    """Manages SQLite database for jobs."""

    def __init__(self):
        """Initializes jobs database in memory."""
        self.db = sqlite_utils.Database(memory=True)
        self.create_jobs_table()

    def create_jobs_table(self):
        """Creates a jobs database."""
        self.db["jobs"].create(
            {
                "source": str,
                "experiment_type": str,
                "acquisition_datetime": str,
                "modality": str,
            }
        )

    def insert_job(self, job):
        """Inserts job into database."""
        self.db["jobs"].insert(job)
        self.db.conn.commit()

    def retrieve_all_jobs(self):
        """Retrieves list of jobs from database."""
        jobs = self.db["jobs"].rows
        return list(jobs)
