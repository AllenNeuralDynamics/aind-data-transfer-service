"""Module to test configs"""

import json
import unittest
from datetime import datetime

from aind_data_schema_models.modalities import Modality
from aind_data_schema_models.platforms import Platform
from pydantic import ValidationError

from aind_data_transfer_service.models.core import (
    SubmitJobRequestV2,
    Task,
    UploadJobConfigsV2,
    validation_context,
)


class TestTask(unittest.TestCase):
    """Tests Task class"""

    @classmethod
    def setUpClass(cls) -> None:
        """Set up test class"""
        custom_task = Task(
            image="some_image",
            image_version="1.0.0",
            image_resources={"key": "value"},
            job_settings={"param1": "value1", "param2": "value2"},
            command_script="#!/bin/bash \necho 'hello world'",
        )
        cls.custom_task = custom_task
        cls.custom_task_configs = custom_task.model_dump()

    def test_constructor(self):
        """Tests that Tasks can be created correctly."""
        # custom task
        self.assertDictEqual(
            {
                "skip_task": False,
                "image": "some_image",
                "image_version": "1.0.0",
                "image_resources": {"key": "value"},
                "job_settings": {
                    "param1": "value1",
                    "param2": "value2",
                },
                "command_script": "#!/bin/bash \necho 'hello world'",
            },
            json.loads(self.custom_task.model_dump_json()),
        )
        # skippable task
        expected_configs = {
            "skip_task": True,
            "image": None,
            "image_version": None,
            "image_resources": None,
            "job_settings": None,
            "command_script": None,
        }
        task = Task(skip_task=True)
        self.assertDictEqual(
            expected_configs, json.loads(task.model_dump_json())
        )

    def test_json_serializable(self):
        """Tests that an error is raised if dicts are not json serializable"""
        for field in [
            "image_resources",
            "job_settings",
        ]:
            expected_error = f"Value error, {field} must be json serializable!"
            invalid_configs = self.custom_task_configs.copy()
            invalid_configs[field] = {"param1": list}
            with self.assertRaises(ValidationError) as e:
                Task(**invalid_configs)
            errors = e.exception.errors()
            self.assertEqual(1, len(errors))
            self.assertIn(expected_error, errors[0]["msg"])


class TestUploadJobConfigsV2(unittest.TestCase):
    """Tests UploadJobConfigsV2 class"""

    @classmethod
    def setUpClass(cls) -> None:
        """Set up test class"""
        example_configs = UploadJobConfigsV2(
            job_type="default",
            project_name="Behavior Platform",
            platform=Platform.BEHAVIOR,
            modalities=[Modality.BEHAVIOR_VIDEOS],
            subject_id="123456",
            acq_datetime=datetime(2020, 10, 13, 13, 10, 10),
            tasks={
                "modality_transformation_settings": {
                    "behavior-videos": Task(
                        job_settings={"input_source": "dir/data_set_1"},
                    ),
                }
            },
        )

        cls.example_configs = example_configs
        cls.base_configs = example_configs.model_dump(
            exclude={"s3_bucket": True, "s3_prefix": True}
        )

    def test_s3_prefix(self):
        """Test s3_prefix computed property"""
        self.assertEqual(
            "behavior_123456_2020-10-13_13-10-10",
            self.example_configs.s3_prefix,
        )

    def test_job_type_default(self):
        """Tests default, valid, and invalid job_type property"""
        self.assertEqual("default", self.example_configs.job_type)

    def test_job_type_validation(self):
        """Test job_type is validated against list context provided."""
        base_configs = self.example_configs.model_dump(
            exclude={"job_type": True, "s3_bucket": True, "s3_prefix": True}
        )
        with validation_context({"job_types": ["default", "ecephys"]}):
            round_trip_model = UploadJobConfigsV2(
                job_type="ecephys",
                **base_configs,
            )
        self.assertEqual("ecephys", round_trip_model.job_type)

    def test_job_type_validation_fail(self):
        """Test job_type is validated against list context provided and
        fails validation."""
        base_configs = self.example_configs.model_dump(
            exclude={"job_type": True, "s3_bucket": True, "s3_prefix": True}
        )
        with self.assertRaises(ValidationError) as err:
            with validation_context({"job_types": ["default", "ecephys"]}):
                UploadJobConfigsV2(
                    job_type="random_string",
                    **base_configs,
                )
        err_msg = json.loads(err.exception.json())[0]["msg"]
        self.assertEqual(
            (
                "Value error, random_string must be one of "
                "['default', 'ecephys']"
            ),
            err_msg,
        )

    def test_project_name_validation(self):
        """Test project_name is validated against list context provided."""
        model = json.loads(self.example_configs.model_dump_json())
        with validation_context(
            {"project_names": ["Behavior Platform", "Other Platform"]}
        ):
            round_trip_model = UploadJobConfigsV2(**model)
        self.assertEqual(
            "behavior_123456_2020-10-13_13-10-10",
            round_trip_model.s3_prefix,
        )

    def test_project_name_validation_fail(self):
        """Test project_name is validated against list context provided and
        fails validation."""
        model = json.loads(self.example_configs.model_dump_json())
        with self.assertRaises(ValidationError) as err:
            with validation_context({"project_names": ["Other Platform"]}):
                UploadJobConfigsV2(**model)
        err_msg = json.loads(err.exception.json())[0]["msg"]
        self.assertEqual(
            (
                "Value error, Behavior Platform must be one of "
                "['Other Platform']"
            ),
            err_msg,
        )

    def test_s3_bucket(self):
        """Test s3_bucket allowed values"""
        default_configs = UploadJobConfigsV2(**self.base_configs)
        base_configs = default_configs.model_dump(
            exclude={"s3_bucket": True, "s3_prefix": True}
        )
        open_configs = UploadJobConfigsV2(s3_bucket="open", **base_configs)
        private_configs = UploadJobConfigsV2(
            s3_bucket="private", **base_configs
        )
        self.assertEqual("default", default_configs.s3_bucket)
        self.assertEqual("open", open_configs.s3_bucket)
        self.assertEqual("private", private_configs.s3_bucket)

    def test_round_trip(self):
        """Tests model can be serialized and de-serialized easily"""
        model_json = self.example_configs.model_dump_json()
        deserialized = UploadJobConfigsV2.model_validate_json(model_json)
        self.assertEqual(self.example_configs, deserialized)

    def test_extra_ignore(self):
        """Tests that extra fields can be passed into model."""
        config = UploadJobConfigsV2(
            **self.base_configs,
            extra_field_1="an extra field",
        )
        config_json = config.model_dump_json()
        self.assertEqual(
            config, UploadJobConfigsV2.model_validate_json(config_json)
        )
        # this also ignores incorrect computed fields
        config_json = config.model_dump(exclude={"s3_prefix": True})
        config = UploadJobConfigsV2(s3_prefix="random_string", **config_json)
        self.assertNotEqual("random_string", config.s3_prefix)
        self.assertEqual(self.example_configs, config)

    def test_check_tasks(self):
        """Tests that tasks can be set correctly"""
        configs = self.base_configs.copy()
        configs["tasks"] = {
            "modality_transformation_settings": {
                "behavior-videos": Task(
                    job_settings={
                        "input_source": "dir/data_set_1",
                        "chunk": "1",
                    }
                ),
                "ecephys": Task(
                    job_settings={
                        "input_source": "dir/data_set_2",
                        "chunk": "1",
                    }
                ),
            },
            "gather_final_metadata": Task(skip_task=True),
            "register_data_asset_to_codeocean": Task(skip_task=True),
        }

        job_configs = UploadJobConfigsV2(**configs)
        self.assertEqual(3, len(job_configs.tasks))
        self.assertEqual(
            2,
            len(job_configs.tasks["modality_transformation_settings"].items()),
        )


class TestSubmitJobRequestV2(unittest.TestCase):
    """Tests SubmitJobRequestV2 class"""

    @classmethod
    def setUpClass(cls) -> None:
        """Set up example configs to be used in tests"""
        example_upload_config = UploadJobConfigsV2(
            job_type="default",
            project_name="Behavior Platform",
            platform=Platform.BEHAVIOR,
            modalities=[
                Modality.BEHAVIOR_VIDEOS,
            ],
            subject_id="123456",
            acq_datetime=datetime(2020, 10, 13, 13, 10, 10),
            tasks={
                "modality_transformation_settings": Task(
                    job_settings={
                        "input_source": "dir/data_set_1",
                    },
                )
            },
        )
        cls.example_upload_config = example_upload_config

    def test_min_length(self):
        """Tests error is raised if no job list is empty"""
        with self.assertRaises(ValidationError) as e:
            SubmitJobRequestV2(upload_jobs=[])
        expected_message = (
            "List should have at least 1 item after validation, not 0"
        )
        actual_message = json.loads(e.exception.json())[0]["msg"]
        self.assertEqual(1, len(json.loads(e.exception.json())))
        self.assertEqual(expected_message, actual_message)

    def test_max_length(self):
        """Tests error is raised if job list is greater than maximum allowed"""
        upload_job = UploadJobConfigsV2(
            **self.example_upload_config.model_dump(round_trip=True)
        )
        with self.assertRaises(ValidationError) as e:
            SubmitJobRequestV2(upload_jobs=[upload_job for _ in range(0, 51)])
        expected_message = (
            "List should have at most 50 items after validation, not 51"
        )
        actual_message = json.loads(e.exception.json())[0]["msg"]
        self.assertEqual(1, len(json.loads(e.exception.json())))
        self.assertEqual(expected_message, actual_message)

    def test_default_settings(self):
        """Tests defaults are set correctly."""
        upload_job = UploadJobConfigsV2(
            **self.example_upload_config.model_dump(round_trip=True)
        )
        job_settings = SubmitJobRequestV2(upload_jobs=[upload_job])
        self.assertIsNone(job_settings.user_email)
        self.assertEqual({"fail"}, job_settings.email_notification_types)
        self.assertEqual("transform_and_upload_v2", job_settings.dag_id)

    def test_non_default_settings(self):
        """Tests user can modify the settings."""
        upload_job_configs = self.example_upload_config.model_dump(
            round_trip=True
        )
        job_settings = SubmitJobRequestV2(
            user_email="abc@acme.com",
            email_notification_types={"begin", "fail"},
            upload_jobs=[UploadJobConfigsV2(**upload_job_configs)],
        )
        self.assertEqual("abc@acme.com", job_settings.user_email)
        self.assertEqual(
            {"begin", "fail"},
            job_settings.email_notification_types,
        )

    def test_email_validation(self):
        """Tests user can not input invalid email address."""
        upload_job_configs = self.example_upload_config.model_dump(
            round_trip=True
        )
        with self.assertRaises(ValidationError) as e:
            SubmitJobRequestV2(
                user_email="some user",
                upload_jobs=[UploadJobConfigsV2(**upload_job_configs)],
            )
        # email_validator changed error message across versions. We can just
        # do a quick check that the error message at least contains this part.
        expected_error_message = "value is not a valid email address: "
        actual_error_message = json.loads(e.exception.json())[0]["msg"]
        # Check only 1 validation error is raised
        self.assertEqual(1, len(json.loads(e.exception.json())))
        self.assertIn(expected_error_message, actual_error_message)

    def test_propagate_email_settings(self):
        """Tests global email settings is propagated to individual jobs."""
        example_job_configs = self.example_upload_config.model_dump(
            exclude={"user_email", "email_notification_types"}, round_trip=True
        )
        new_job = UploadJobConfigsV2(
            user_email="xyz@acme.org",
            email_notification_types=["all"],
            **example_job_configs,
        )
        job_settings = SubmitJobRequestV2(
            user_email="abc@acme.org",
            email_notification_types={"begin", "fail"},
            upload_jobs=[
                new_job,
                UploadJobConfigsV2(**example_job_configs),
            ],
        )
        self.assertEqual(
            "xyz@acme.org", job_settings.upload_jobs[0].user_email
        )
        self.assertEqual(
            "abc@acme.org", job_settings.upload_jobs[1].user_email
        )
        self.assertEqual(
            {"all"}, job_settings.upload_jobs[0].email_notification_types
        )
        self.assertEqual(
            {"begin", "fail"},
            job_settings.upload_jobs[1].email_notification_types,
        )

    def test_check_duplicate_upload_jobs(self):
        """Tests that duplicate upload jobs are not allowed."""
        job_configs = self.example_upload_config.model_dump(
            mode="json", exclude={"subject_id"}
        )
        upload_jobs = [
            UploadJobConfigsV2(**job_configs, subject_id=subject_id)
            for subject_id in ["123456", "123457", "123458", "123456"]
        ]
        with self.assertRaises(ValidationError) as e:
            SubmitJobRequestV2(upload_jobs=upload_jobs)
        errors = json.loads(e.exception.json())
        self.assertEqual(1, len(errors))
        self.assertIn(
            "Duplicate jobs found for behavior_123456_2020-10-13_13-10-10",
            errors[0]["msg"],
        )

    def test_check_duplicate_upload_jobs_same_prefix(self):
        """Tests that upload_jobs with same s3_prefix but different configs
        are allowed"""
        job_configs = self.example_upload_config.model_dump(
            mode="json", exclude={"tasks"}
        )
        upload_jobs = list()
        for i in range(10):
            tasks = {
                "modality_transformation_settings": Task(
                    job_settings={"input_source": "dir/data", "chunk": str(i)}
                )
            }
            upload_jobs.append(UploadJobConfigsV2(**job_configs, tasks=tasks))
        submit_job_request = SubmitJobRequestV2(upload_jobs=upload_jobs)
        self.assertEqual(10, len(submit_job_request.upload_jobs))

    def test_current_jobs_validation(self):
        """Tests job validation against current_jobs provided in context."""
        job_configs = self.example_upload_config.model_dump(
            mode="json", exclude={"subject_id"}
        )
        submitted_job_request = SubmitJobRequestV2(
            upload_jobs=[
                UploadJobConfigsV2(**job_configs, subject_id=subject_id)
                for subject_id in ["123456", "123457", "123458"]
            ]
        )
        current_jobs = [
            j.model_dump(mode="json", exclude_none=True)
            for j in submitted_job_request.upload_jobs
        ]
        new_job = UploadJobConfigsV2(**job_configs, subject_id="123459")
        with validation_context({"current_jobs": current_jobs}):
            submit_job_request = SubmitJobRequestV2(upload_jobs=[new_job])
        self.assertEqual(1, len(submit_job_request.upload_jobs))
        self.assertEqual(
            "behavior_123459_2020-10-13_13-10-10",
            submit_job_request.upload_jobs[0].s3_prefix,
        )

    def test_current_jobs_validation_fail(self):
        """Tests job validation when an upload_job is already running."""
        submitted_job_request = SubmitJobRequestV2(
            upload_jobs=[self.example_upload_config]
        )
        current_jobs_1 = [
            j.model_dump(mode="json", exclude_none=True)
            for j in submitted_job_request.upload_jobs
        ]
        current_jobs_2 = [
            submitted_job_request.model_dump(mode="json", exclude_none=True)
        ]
        for current_jobs in [current_jobs_1, current_jobs_2]:
            with self.assertRaises(ValidationError) as err:
                with validation_context({"current_jobs": current_jobs}):
                    SubmitJobRequestV2(
                        upload_jobs=[self.example_upload_config]
                    )
            err_msg = json.loads(err.exception.json())[0]["msg"]
            self.assertEqual(
                (
                    "Value error, Job is already running/queued for "
                    "behavior_123456_2020-10-13_13-10-10"
                ),
                err_msg,
            )


if __name__ == "__main__":
    unittest.main()
