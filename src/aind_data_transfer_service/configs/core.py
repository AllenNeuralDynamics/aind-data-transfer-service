"""Core models for using V2 of aind-data-transfer-service"""

import json
import re
from datetime import datetime
from enum import Enum
from typing import Any, ClassVar, Dict, List, Literal, Optional, Set, Union

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
    ValidationInfo,
    field_validator,
)
from pydantic_settings import BaseSettings


# TODO: add all possible job types as enums. Alternatively,
# remove the enum if we allow any new job type
class JobType(str, Enum):
    """Job types for data transfer upload jobs."""

    DEFAULT = "default"
    TEST = "test"


class TaskId(str, Enum):
    """Tasks run during a data transfer upload job."""

    CHECK_SOURCE_FOLDERS_EXIST = "check_source_folders_exist"
    CREATE_FOLDER = "create_folder"
    GATHER_PRELIMINARY_METADATA = "gather_preliminary_metadata"
    MAKE_MODALITY_LIST = "make_modality_list"  # TODO: rename to compress_data?
    GATHER_FINAL_METADATA = "gather_final_metadata"
    FINAL_CHECK_S3_FOLDER_EXIST = "final_check_s3_folder_exist"
    UPLOAD_DATA_TO_S3 = "upload_data_to_s3"
    REGISTER_DATA_ASSET_TO_CODEOCEAN = "register_data_asset_to_codeocean"
    UPDATE_DOCDB_RECORD = "update_docdb_record"
    EXPAND_PIPELINES = "expand_pipelines"
    REMOVE_FOLDER = "remove_folder"


class Task(BaseSettings):
    """Configuration for a task run during a data transfer upload job."""

    task_id: TaskId = Field(
        ..., description="Task ID (task name)", title="Task ID"
    )


class SkipTask(Task):
    """Configuration to skip a task during a data transfer upload job."""

    skip_task: Literal[True] = True


class CustomTask(Task):
    """Configuration for a task run during a data transfer upload job."""

    image: str = Field(
        ..., description="Name of docker image to run", title="Image"
    )
    image_version: str = Field(
        ...,
        description="Version of docker image to run",
        title="Image Version",
    )
    image_environment: Dict[str, Any] = Field(
        ...,
        description=(
            "Environment for the docker image. Must be json serializable."
        ),
        title="Image Environment",
    )
    parameters_settings: Dict[str, Any] = Field(
        ...,
        description="Settings for the task. Must be json serializable.",
        title="Parameters Settings",
    )

    @field_validator("image_environment", "parameters_settings", mode="after")
    def validate_json_serializable(
        cls, v: Dict[str, Any], info: ValidationInfo
    ) -> Dict[str, Any]:
        """Validate that fields are json serializable."""
        try:
            json.dumps(v)
        except Exception as e:
            raise ValueError(
                f"{info.field_name} must be json serializable! {e}"
            )
        return v


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

    job_type: JobType = Field(
        default=JobType.DEFAULT,
        description=(
            "Job type for the upload job. Tasks will be run with default "
            "settings based on the job_type."
        ),
        title="Job Type",
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
    task_overrides: Optional[List[CustomTask | SkipTask]] = Field(
        default=None,
        description=(
            "List of tasks to run with custom settings. If null, "
            "will use default task settings for the job_type."
        ),
        title="Task Overrides",
    )
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

    @field_validator("task_overrides", mode="after")
    def check_task_overrides(
        cls, v: Optional[List[CustomTask | SkipTask]]
    ) -> Optional[List[CustomTask | SkipTask]]:
        """Checks that task_ids are unique."""
        if v is not None:
            task_ids = [task.task_id for task in v]
            duplicates = {t.value for t in task_ids if task_ids.count(t) > 1}
            if duplicates:
                raise ValueError(
                    f"Task IDs must be unique! Duplicates: {duplicates}"
                )
        return v


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
