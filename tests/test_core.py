"""Module to test configs"""

import json
import unittest
from datetime import datetime

from aind_data_schema_models.modalities import Modality
from aind_data_schema_models.platforms import Platform
from aind_data_transfer_models.s3_upload_configs import (
    BucketType,
    EmailNotificationType,
)
from pydantic import ValidationError

from aind_data_transfer_service.configs.core import (
    CustomTask,
    SkipTask,
    SubmitJobRequestV2,
    TaskId,
    UploadJobConfigsV2,
    validation_context,
)


class TestTaskConfigs(unittest.TestCase):
    """Tests Task class"""

    @classmethod
    def setUpClass(cls) -> None:
        """Set up test class"""
        custom_task = CustomTask(
            task_id=TaskId.CHECK_SOURCE_FOLDERS_EXIST,
            image="some_image",
            image_version="1.0.0",
            image_environment={"key": "value"},
            parameters_settings={"param1": "value1", "param2": "value2"},
        )
        cls.custom_task = custom_task
        cls.custom_task_configs = custom_task.model_dump()

    def test_skip_task(self):
        """Tests SkipTask is created correctly."""
        task_configs = SkipTask(task_id=TaskId.CHECK_SOURCE_FOLDERS_EXIST)
        self.assertEqual(
            {"task_id": "check_source_folders_exist", "skip_task": True},
            json.loads(task_configs.model_dump_json()),
        )

    def test_custom_task(self):
        """Tests that CustomTask is created correctly."""
        task_configs = CustomTask(**self.custom_task_configs)
        self.assertEqual(
            {
                "task_id": "check_source_folders_exist",
                "image": "some_image",
                "image_version": "1.0.0",
                "image_environment": {"key": "value"},
                "parameters_settings": {
                    "param1": "value1",
                    "param2": "value2",
                },
            },
            json.loads(task_configs.model_dump_json()),
        )

    def test_custom_task_error(self):
        """Tests that an error is raised if dicts are not json serializable"""
        for field in ["image_environment", "parameters_settings"]:
            expected_error = f"Value error, {field} must be json serializable!"
            invalid_configs = self.custom_task_configs.copy()
            invalid_configs[field] = {"param1": list}
            with self.assertRaises(ValidationError) as e:
                CustomTask(**invalid_configs)
            errors = e.exception.errors()
            self.assertEqual(1, len(errors))
            self.assertIn(expected_error, errors[0]["msg"])


class TestUploadJobConfigsV2(unittest.TestCase):
    """Tests UploadJobConfigsV2 class"""

    @classmethod
    def setUpClass(cls) -> None:
        """Set up test class"""
        example_configs = UploadJobConfigsV2(
            project_name="Behavior Platform",
            platform=Platform.BEHAVIOR,
            modalities=[
                Modality.BEHAVIOR_VIDEOS,
            ],
            subject_id="123456",
            acq_datetime=datetime(2020, 10, 13, 13, 10, 10),
        )
        cls.example_configs = example_configs
        cls.base_configs = example_configs.model_dump(
            exclude={
                "job_type": True,
                "s3_bucket": True,
                "acq_datetime": True,
                "s3_prefix": True,
                "task_overrides": True,
            }
        )

    def test_job_type(self):
        """Tests default, valid, and invalid job_type property"""
        self.assertEqual("default", self.example_configs.job_type)
        valid_configs = UploadJobConfigsV2(
            job_type="test",
            acq_datetime=datetime(2020, 10, 13, 13, 10, 10),
            **self.base_configs,
        )
        self.assertEqual("test", valid_configs.job_type)
        with self.assertRaises(ValidationError):
            UploadJobConfigsV2(
                job_type="random_string",
                acq_datetime=datetime(2020, 10, 13, 13, 10, 10),
                **self.base_configs,
            )

    def test_s3_prefix(self):
        """Test s3_prefix property"""

        self.assertEqual(
            "behavior_123456_2020-10-13_13-10-10",
            self.example_configs.s3_prefix,
        )

    def test_project_names_validation(self):
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

    def test_project_names_validation_fail(self):
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

    def test_map_bucket(self):
        """Test map_bucket method"""
        default_configs = UploadJobConfigsV2(
            acq_datetime=datetime(2020, 10, 13, 13, 10, 10),
            **self.base_configs,
        )
        base_configs = default_configs.model_dump(
            exclude={
                "s3_bucket": True,
                "s3_prefix": True,
            }
        )
        private_configs1 = UploadJobConfigsV2(
            s3_bucket="private", **base_configs
        )
        private_configs2 = UploadJobConfigsV2(
            s3_bucket=BucketType.PRIVATE, **base_configs
        )

        self.assertEqual(BucketType.OPEN, default_configs.s3_bucket)
        self.assertEqual(BucketType.PRIVATE, private_configs1.s3_bucket)
        self.assertEqual(BucketType.PRIVATE, private_configs2.s3_bucket)

    def test_round_trip(self):
        """Tests model can be serialized and de-serialized easily"""
        model_json = self.example_configs.model_dump_json()
        deserialized = UploadJobConfigsV2.model_validate_json(model_json)
        self.assertEqual(self.example_configs, deserialized)

    def test_deserialization_fail(self):
        """Tests deserialization fails with incorrect computed field"""
        corrupt_json = json.dumps(
            {
                "project_name": "Behavior Platform",
                "platform": {
                    "name": "Behavior platform",
                    "abbreviation": "behavior",
                },
                "modalities": [
                    {
                        "name": "Behavior videos",
                        "abbreviation": "behavior-videos",
                    }
                ],
                "subject_id": "123456",
                "acq_datetime": "2020-10-13T13:10:10",
                "s3_prefix": "incorrect",
            }
        )
        with self.assertRaises(ValidationError) as e:
            UploadJobConfigsV2.model_validate_json(corrupt_json)
        errors = json.loads(e.exception.json())
        expected_msg = (
            "Value error, s3_prefix incorrect doesn't match computed "
            "behavior_123456_2020-10-13_13-10-10!"
        )
        self.assertEqual(1, len(errors))
        self.assertEqual(expected_msg, errors[0]["msg"])

    def test_task_overrides(self):
        """Tests that task overrides are set correctly"""
        task_overrides = [
            CustomTask(
                task_id=TaskId.MAKE_MODALITY_LIST,
                image="some_image",
                image_version="1.0.0",
                image_environment={"key": "value"},
                parameters_settings={"param1": "value1", "param2": "value2"},
            ),
            SkipTask(task_id=TaskId.GATHER_FINAL_METADATA),
            SkipTask(task_id=TaskId.REGISTER_DATA_ASSET_TO_CODEOCEAN),
        ]
        job_configs = UploadJobConfigsV2(
            acq_datetime=datetime(2020, 10, 13, 13, 10, 10),
            task_overrides=task_overrides,
            **self.base_configs,
        )
        self.assertEqual(3, len(job_configs.task_overrides))
        # if we add a duplicate task_id, an error should be raised
        task_overrides.append(SkipTask(task_id=TaskId.MAKE_MODALITY_LIST))
        with self.assertRaises(ValidationError) as e:
            UploadJobConfigsV2(
                acq_datetime=datetime(2020, 10, 13, 13, 10, 10),
                task_overrides=task_overrides,
                **self.base_configs,
            )
        errors = e.exception.errors()
        self.assertEqual(1, len(errors))
        self.assertEqual(
            "Value error, Task IDs must be unique! Duplicates: "
            "{'make_modality_list'}",
            errors[0]["msg"],
        )


class TestSubmitJobRequestV2(unittest.TestCase):
    """Tests SubmitJobRequestV2 class"""

    @classmethod
    def setUpClass(cls) -> None:
        """Set up example configs to be used in tests"""

        example_upload_config = UploadJobConfigsV2(
            project_name="Behavior Platform",
            platform=Platform.BEHAVIOR,
            modalities=[
                Modality.BEHAVIOR_VIDEOS,
            ],
            subject_id="123456",
            acq_datetime=datetime(2020, 10, 13, 13, 10, 10),
        )
        cls.example_upload_config = example_upload_config

    def test_min_items(self):
        """Tests error is raised if no job list is empty"""

        with self.assertRaises(ValidationError) as e:
            SubmitJobRequestV2(upload_jobs=[])
        expected_message = (
            "List should have at least 1 item after validation, not 0"
        )
        actual_message = json.loads(e.exception.json())[0]["msg"]
        self.assertEqual(1, len(json.loads(e.exception.json())))
        self.assertEqual(expected_message, actual_message)

    def test_max_items(self):
        """Tests error is raised if job list is greater than maximum allowed"""

        upload_job = UploadJobConfigsV2(
            **self.example_upload_config.model_dump(round_trip=True)
        )

        with self.assertRaises(ValidationError) as e:
            SubmitJobRequestV2(
                upload_jobs=[upload_job for _ in range(0, 1001)]
            )
        expected_message = (
            "List should have at most 1000 items after validation, not 1001"
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
        self.assertEqual(
            {EmailNotificationType.FAIL}, job_settings.email_notification_types
        )
        self.assertEqual("transform_and_upload_v2", job_settings.job_type)

    def test_non_default_settings(self):
        """Tests user can modify the settings."""
        upload_job_configs = self.example_upload_config.model_dump(
            round_trip=True
        )

        job_settings = SubmitJobRequestV2(
            user_email="abc@acme.com",
            email_notification_types={
                EmailNotificationType.BEGIN,
                EmailNotificationType.FAIL,
            },
            upload_jobs=[UploadJobConfigsV2(**upload_job_configs)],
        )
        self.assertEqual("abc@acme.com", job_settings.user_email)
        self.assertEqual(
            {EmailNotificationType.BEGIN, EmailNotificationType.FAIL},
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
            email_notification_types=[EmailNotificationType.ALL],
            **example_job_configs,
        )
        job_settings = SubmitJobRequestV2(
            user_email="abc@acme.org",
            email_notification_types={
                EmailNotificationType.BEGIN,
                EmailNotificationType.FAIL,
            },
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

    def test_extra_allow(self):
        """Tests that extra fields can be passed into model."""
        config = UploadJobConfigsV2(
            project_name="some project",
            platform=Platform.ECEPHYS,
            modalities=[Modality.ECEPHYS],
            subject_id="123456",
            acq_datetime=datetime(2020, 1, 2, 3, 4, 5),
            extra_field_1="an extra field",
        )
        config_json = config.model_dump_json()
        self.assertEqual(
            config, UploadJobConfigsV2.model_validate_json(config_json)
        )


if __name__ == "__main__":
    unittest.main()
