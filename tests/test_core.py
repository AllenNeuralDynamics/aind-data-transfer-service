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
    SubmitJobRequestV2,
    UploadJobConfigsV2,
)


class TestUploadJobConfigsV2(unittest.TestCase):
    """Tests UploadJobConfigsV2 class"""

    @classmethod
    def setUpClass(cls) -> None:
        """Set up test class"""
        example_configs = UploadJobConfigsV2(
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

    def test_map_bucket(self):
        """Test map_bucket method"""
        default_configs = UploadJobConfigsV2(
            acq_datetime=datetime(2020, 10, 13, 13, 10, 10),
            **self.base_configs,
        )
        base_configs = default_configs.model_dump(
            exclude={
                "s3_bucket": True,
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

    def test_parse_datetime(self):
        """Test parse_datetime method"""

        configs1 = UploadJobConfigsV2(
            acq_datetime="2020-05-23T09:05:03",
            **self.base_configs,
        )
        configs2 = UploadJobConfigsV2(
            acq_datetime="05/23/2020 09:05:03 AM",
            **self.base_configs,
        )
        self.assertEqual(datetime(2020, 5, 23, 9, 5, 3), configs1.acq_datetime)
        self.assertEqual(datetime(2020, 5, 23, 9, 5, 3), configs2.acq_datetime)

    def test_parse_datetime_error(self):
        """Test parse_datetime method raises error"""

        with self.assertRaises(ValidationError) as e:
            UploadJobConfigsV2(
                acq_datetime="2020/05/23T09:05:03",
                **self.base_configs,
            )
        error_msg = json.loads(e.exception.json())[0]["msg"]
        self.assertTrue("Value error, Incorrect datetime format" in error_msg)

    def test_parse_platform_string(self):
        """Tests platform can be parsed from string"""

        base_configs = self.example_configs.model_dump(
            exclude={
                "platform": True,
            }
        )
        configs = UploadJobConfigsV2(platform="behavior", **base_configs)
        self.assertEqual(Platform.BEHAVIOR, configs.platform)

    def test_parse_platform_string_error(self):
        """Tests that an error is raised if an unknown platform is used"""

        base_configs = self.example_configs.model_dump(
            exclude={
                "platform": True,
            }
        )

        with self.assertRaises(AttributeError) as e:
            UploadJobConfigsV2(platform="MISSING", **base_configs)
        self.assertEqual("Unknown Platform: MISSING", e.exception.args[0])

    def test_parse_modality_string(self):
        """Test parse_modality_string method"""
        base_configs = self.example_configs.model_dump(
            exclude={
                "modalities": True,
            }
        )
        configs = UploadJobConfigsV2(modalities=["ecephys"], **base_configs)
        self.assertEqual([Modality.ECEPHYS], configs.modalities)

    def test_parse_modality_string_error(self):
        """Test parse_modality_string method raises error"""
        base_configs = self.example_configs.model_dump(
            exclude={
                "modalities": True,
            }
        )
        with self.assertRaises(AttributeError) as e:
            UploadJobConfigsV2(modalities=["abcdef"], **base_configs)
        self.assertEqual("Unknown Modality: abcdef", e.exception.args[0])

    def test_round_trip(self):
        """Tests model can be serialized and de-serialized easily"""
        model_json = self.example_configs.model_dump_json()
        deserialized = UploadJobConfigsV2.model_validate_json(model_json)
        self.assertEqual(self.example_configs, deserialized)


class TestSubmitJobRequestV2(unittest.TestCase):
    """Tests SubmitJobRequestV2 class"""

    @classmethod
    def setUpClass(cls) -> None:
        """Set up example configs to be used in tests"""

        example_upload_config = UploadJobConfigsV2(
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
