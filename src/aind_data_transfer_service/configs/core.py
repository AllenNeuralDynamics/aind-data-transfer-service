"""Core models for using V2 of aind-data-transfer-service"""

import re
from datetime import datetime
from typing import Any, ClassVar, List, Literal, Optional, Set, Union

from aind_data_schema_models.modalities import Modality
from aind_data_schema_models.platforms import Platform
from aind_data_transfer_models.s3_upload_configs import (
    BucketType,
    EmailNotificationType,
    S3UploadSubmitJobRequest,
)
from pydantic import (
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
)
from pydantic_settings import BaseSettings


class UploadJobConfigsV2(BaseSettings):
    """Configuration for a data transfer upload job"""

    # TODO: add back:
    # context manager
    # user_email
    # email_notification_types
    # project_name
    # s3_prefix (build_data_name)
    # @field_validator for s3_bucket and others

    model_config = ConfigDict(use_enum_values=True, extra="allow")
    # Need some way to extract abbreviations. Maybe a public method can be
    # added to the Platform class
    _PLATFORM_MAP: ClassVar = {
        p().abbreviation.upper(): p().abbreviation for p in Platform.ALL
    }
    # Need some way to extract abbreviations. Maybe a public method can be
    # added to the Modality class
    _MODALITY_MAP: ClassVar = {
        m().abbreviation.upper().replace("-", "_"): m().abbreviation
        for m in Modality.ALL
    }
    _DATETIME_PATTERN1: ClassVar = re.compile(
        r"^\d{4}-\d{2}-\d{2}[ |T]\d{2}:\d{2}:\d{2}$"
    )
    _DATETIME_PATTERN2: ClassVar = re.compile(
        r"^\d{1,2}/\d{1,2}/\d{4} \d{1,2}:\d{2}:\d{2} [APap][Mm]$"
    )

    user_email: Optional[EmailStr] = Field(
        default=None,
        description=(
            "Optional email address to receive job status notifications"
        ),
    )
    email_notification_types: Optional[Set[EmailNotificationType]] = Field(
        default=None,
        description=(
            "Types of job statuses to receive email notifications about"
        ),
    )

    # TODO: check default and allowed buckets
    s3_bucket: Literal[BucketType.PRIVATE, BucketType.OPEN] = Field(
        default=BucketType.OPEN,
        description=(
            "Bucket where data will be uploaded (defaults to open bucket)."
        ),
        title="S3 Bucket",
    )
    platform: Platform.ONE_OF = Field(
        ..., description="Platform", title="Platform"
    )
    modalities: List[Modality.ONE_OF] = Field(
        ...,
        description="Data collection modalities",
        title="Modalities",
        min_items=1,
    )
    subject_id: str = Field(..., description="Subject ID", title="Subject ID")
    acq_datetime: datetime = Field(
        ...,
        description="Datetime data was acquired",
        title="Acquisition Datetime",
    )

    # TODO: do we still need to parse platform and modality from string?
    @field_validator("platform", mode="before")
    def parse_platform_string(
        cls, input_platform: Union[str, dict, Platform]
    ) -> Union[dict, Platform]:
        """Attempts to convert strings to a Platform model. Raises an error
        if unable to do so."""
        if isinstance(input_platform, str):
            platform_abbreviation = cls._PLATFORM_MAP.get(
                input_platform.upper()
            )
            if platform_abbreviation is None:
                raise AttributeError(f"Unknown Platform: {input_platform}")
            else:
                return Platform.from_abbreviation(platform_abbreviation)
        else:
            return input_platform

    @field_validator("modalities", mode="before")
    def parse_modality_string(
        cls, input_modalities: List[Union[str, dict, Modality]]
    ) -> List[Union[dict, Modality]]:
        """Attempts to convert strings to a Modality model. Raises an error
        if unable to do so."""
        modalities = []
        for input_modality in input_modalities:
            if isinstance(input_modality, str):
                modality_abbreviation = cls._MODALITY_MAP.get(
                    input_modality.upper().replace("-", "_")
                )
                if modality_abbreviation is None:
                    raise AttributeError(f"Unknown Modality: {input_modality}")
                modalities.append(
                    Modality.from_abbreviation(modality_abbreviation)
                )
            else:
                modalities.append(input_modality)
        return modalities

    @field_validator("acq_datetime", mode="before")
    def _parse_datetime(cls, datetime_val: Any) -> datetime:
        """Parses datetime string to %YYYY-%MM-%DD HH:mm:ss"""
        is_str = isinstance(datetime_val, str)
        if is_str and re.match(
            UploadJobConfigsV2._DATETIME_PATTERN1, datetime_val
        ):
            return datetime.fromisoformat(datetime_val)
        elif is_str and re.match(
            UploadJobConfigsV2._DATETIME_PATTERN2, datetime_val
        ):
            return datetime.strptime(datetime_val, "%m/%d/%Y %I:%M:%S %p")
        elif is_str:
            raise ValueError(
                "Incorrect datetime format, should be"
                " YYYY-MM-DD HH:mm:ss or MM/DD/YYYY I:MM:SS P"
            )
        else:
            return datetime_val


class SubmitJobRequestV2(S3UploadSubmitJobRequest):
    """Main request that will be sent to the backend. Bundles jobs into a list
    and allows a user to add an email address to receive notifications."""

    model_config = ConfigDict(use_enum_values=True, extra="allow")
    job_type: Literal["transform_and_upload_v2"] = "transform_and_upload_v2"
    upload_jobs: List[UploadJobConfigsV2] = Field(
        ...,
        description="List of upload jobs to process. Max of 1000 at a time.",
        min_items=1,
        max_items=1000,
    )
