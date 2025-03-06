"""Module to test configs"""

import json
import unittest
from datetime import datetime
from pathlib import PurePosixPath

from aind_data_schema_models.modalities import Modality
from aind_data_schema_models.platforms import Platform
from pydantic import ValidationError

from aind_data_transfer_service.configs.core import (
    SubmitJobRequestV2,
    Task,
    UploadJobConfigsV2,
    validation_context,
)


class TestTaskConfigs(unittest.TestCase):
    """Tests Task class"""

    @classmethod
    def setUpClass(cls) -> None:
        """Set up test class"""
        custom_task = Task(
            task_id="check_source_folders_exist",
            image="some_image",
            image_version="1.0.0",
            image_environment={"key": "value"},
            parameters_settings={"param1": "value1", "param2": "value2"},
            dynamic_parameters_settings={"dynamic_param": "dynamic_value"},
        )
        cls.custom_task = custom_task
        cls.custom_task_configs = custom_task.model_dump()

    def test_contructor(self):
        """Tests that Tasks can be created correctly."""
        # custom task
        self.assertDictEqual(
            {
                "task_id": "check_source_folders_exist",
                "skip_task": False,
                "image": "some_image",
                "image_version": "1.0.0",
                "image_environment": {"key": "value"},
                "parameters_settings": {
                    "param1": "value1",
                    "param2": "value2",
                },
                "dynamic_parameters_settings": {
                    "dynamic_param": "dynamic_value"
                },
            },
            json.loads(self.custom_task.model_dump_json()),
        )
        # skippable task
        expected_configs = {
            "task_id": "check_source_folders_exist",
            "skip_task": True,
            "image": None,
            "image_version": None,
            "image_environment": {},
            "parameters_settings": {},
            "dynamic_parameters_settings": {},
        }
        task = Task(task_id="check_source_folders_exist", skip_task=True)
        self.assertDictEqual(
            expected_configs, json.loads(task.model_dump_json())
        )

    def test_json_serializable(self):
        """Tests that an error is raised if dicts are not json serializable"""
        for field in [
            "image_environment",
            "parameters_settings",
            "dynamic_parameters_settings",
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
            project_name="Behavior Platform",
            platform=Platform.BEHAVIOR,
            modalities=[
                Modality.BEHAVIOR_VIDEOS,
            ],
            subject_id="123456",
            acq_datetime=datetime(2020, 10, 13, 13, 10, 10),
            tasks=[
                Task(
                    task_id="make_modality_list",
                    dynamic_parameters_settings={
                        "modality": Modality.BEHAVIOR_VIDEOS.abbreviation,
                        "source": (
                            PurePosixPath("dir") / "data_set_1"
                        ).as_posix(),
                    },
                )
            ],
        )
        cls.example_configs = example_configs
        cls.base_configs = example_configs.model_dump(
            exclude={
                "job_type": True,
                "s3_bucket": True,
                "s3_prefix": True,
            }
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
        with validation_context({"job_types": ["default", "ecephys"]}):
            round_trip_model = UploadJobConfigsV2(
                job_type="ecephys",
                **self.base_configs,
            )

        self.assertEqual(
            "ecephys",
            round_trip_model.job_type,
        )

    def test_job_type_validation_fail(self):
        """Test job_type is validated against list context provided and
        fails validation."""
        with self.assertRaises(ValidationError) as err:
            with validation_context({"job_types": ["default", "ecephys"]}):
                UploadJobConfigsV2(
                    job_type="random_string",
                    **self.base_configs,
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
        default_configs = UploadJobConfigsV2(
            **self.base_configs,
        )
        base_configs = default_configs.model_dump(
            exclude={
                "s3_bucket": True,
                "s3_prefix": True,
            }
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
            **self.base_configs, extra_field_1="an extra field",
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
        configs["tasks"] = [
            Task(
                task_id="make_modality_list",
                dynamic_parameters_settings={
                    "modality": Modality.BEHAVIOR_VIDEOS.abbreviation,
                    "source": (PurePosixPath("dir") / "data_set_1").as_posix(),
                    "chunk": "1",
                },
            ),
            Task(
                task_id="make_modality_list",
                dynamic_parameters_settings={
                    "modality": Modality.ECEPHYS.abbreviation,
                    "source": (PurePosixPath("dir") / "data_set_2").as_posix(),
                    "chunk": "1",
                },
            ),
            Task(task_id="gather_final_metadata", skip_task=True),
            Task(task_id="register_data_asset_to_codeocean", skip_task=True),
        ]
        job_configs = UploadJobConfigsV2(**configs)
        self.assertEqual(4, len(job_configs.tasks))
        # there can only be multiple tasks for ModalityTasks
        configs["tasks"].append(
            Task(task_id="gather_final_metadata", skip_task=True)
        )
        with self.assertRaises(ValidationError) as e:
            UploadJobConfigsV2(**configs)
        errors = e.exception.errors()
        self.assertEqual(1, len(errors))
        self.assertEqual(
            "Value error, Task IDs must be unique! Duplicates: "
            "{'gather_final_metadata'}",
            errors[0]["msg"],
        )
        # if we do not provide any ModalityTask, an error should be raised
        configs["tasks"] = [
            Task(task_id="gather_final_metadata", skip_task=True),
        ]
        with self.assertRaises(ValidationError) as e:
            UploadJobConfigsV2(**configs)
        errors = e.exception.errors()
        self.assertEqual(1, len(errors))
        self.assertEqual(
            (
                "Value error, A modality task (task_id: make_modality_list) "
                "must be provided for each modality!"
            ),
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
            tasks=[
                Task(
                    task_id="make_modality_list",
                    dynamic_parameters_settings={
                        "modality": Modality.BEHAVIOR_VIDEOS.abbreviation,
                        "source": (
                            PurePosixPath("dir") / "data_set_1"
                        ).as_posix(),
                    },
                )
            ],
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


if __name__ == "__main__":
    unittest.main()
