"""Core models for using V2 of aind-data-transfer-service"""

import json
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime
from enum import Enum
from pathlib import PurePosixPath
from typing import Any, Dict, List, Literal, Optional, Set, Union

from aind_data_schema_models.data_name_patterns import build_data_name
from aind_data_schema_models.modalities import Modality
from aind_data_schema_models.platforms import Platform
from pydantic import (
    ConfigDict,
    EmailStr,
    Field,
    ValidationInfo,
    computed_field,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings

_validation_context: ContextVar[Union[Dict[str, Any], None]] = ContextVar(
    "_validation_context", default=None
)


@contextmanager
def validation_context(context: Union[Dict[str, Any], None]) -> None:
    """
    Following guide in:
    https://docs.pydantic.dev/latest/concepts/validators/#validation-context
    Parameters
    ----------
    context : Union[Dict[str, Any], None]

    Returns
    -------
    None

    """
    token = _validation_context.set(context)
    try:
        yield
    finally:
        _validation_context.reset(token)


class BucketType(str, Enum):
    """Types of s3 buckets"""

    PRIVATE = "private"
    OPEN = "open"
    SCRATCH = "scratch"
    ARCHIVE = "archive"
    DEFAULT = "default"  # Send data to bucket determined by service


class EmailNotificationType(str, Enum):
    """Types of email notifications"""

    BEGIN = "begin"
    END = "end"
    FAIL = "fail"
    RETRY = "retry"
    ALL = "all"


class TaskId(str, Enum):
    """Tasks run during a data transfer upload job."""

    SEND_JOB_START_EMAIL = "send_job_start_email"
    CHECK_S3_FOLDER_EXIST = "check_s3_folder_exist"
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
    SEND_JOB_END_EMAIL = "send_job_end_email"


class Task(BaseSettings):
    """Configuration for a task run during a data transfer upload job."""

    task_id: TaskId = Field(
        ..., description="Task ID (task name)", title="Task ID"
    )
    skip_task: bool = Field(
        default=False,
        description=(
            "Skip running this task. If true, only task_id and skip_step are "
            "required."
        ),
        title="Skip Step",
    )

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

    @model_validator(mode="before")
    def check_skip_task(cls, data: Any) -> Any:
        """If skip_task is True, then clear the other fields."""
        if data.get("skip_task") is True:
            data["image"] = ""
            data["image_version"] = ""
            data["image_environment"] = {}
            data["parameters_settings"] = {}
        return data

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


class ModalityTask(Task):
    """Configuration for the modality tranformation task."""

    task_id: Literal[TaskId.MAKE_MODALITY_LIST] = TaskId.MAKE_MODALITY_LIST
    skip_task: Literal[False] = False

    modality: Modality.ONE_OF = Field(
        ..., description="Data collection modality", title="Modality"
    )
    source: PurePosixPath = Field(
        ...,
        description="Location of raw data to be uploaded",
        title="Data Source",
    )
    chunk: Optional[str] = Field(
        default=None,
        description="Chunk of data to be uploaded. If set, will only upload "
        "this chunk.",
        title="Chunk",
    )
    use_job_type_settings: bool = Field(
        default=True,
        description=(
            "Use task settings (image, parameter_settings, etc.) for the "
            "job_type. If false, will use the settings provided here."
        ),
    )

    @model_validator(mode="before")
    def check_use_job_type_settings(cls, data: Any) -> Any:
        """If use_job_type_settings is set, then clear the other fields."""
        if data.get("use_job_type_settings") is not False:
            data["image"] = ""
            data["image_version"] = ""
            data["image_environment"] = {}
            data["parameters_settings"] = {}
        return data


class UploadJobConfigsV2(BaseSettings):
    """Configuration for a data transfer upload job"""

    # noinspection PyMissingConstructor
    def __init__(self, /, **data: Any) -> None:
        """Add context manager to init for validating project_names."""
        self.__pydantic_validator__.validate_python(
            data,
            self_instance=self,
            context=_validation_context.get(),
        )

    model_config = ConfigDict(use_enum_values=True, extra="allow")

    job_type: str = Field(
        default="default",
        description=(
            "Job type for the upload job. Tasks will be run based on the "
            "job_type unless otherwise specified in task_overrides."
        ),
        title="Job Type",
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
    s3_bucket: Literal[
        BucketType.PRIVATE, BucketType.OPEN, BucketType.DEFAULT
    ] = Field(
        default=BucketType.DEFAULT,
        description=(
            "Bucket where data will be uploaded. If not provided, will upload "
            "to default bucket."
        ),
        title="S3 Bucket",
    )

    project_name: str = Field(
        ..., description="Name of project", title="Project Name"
    )
    platform: Platform.ONE_OF = Field(
        ..., description="Platform", title="Platform"
    )
    modalities: List[Modality.ONE_OF] = Field(
        ...,
        description="Data collection modalities",
        title="Modalities",
        min_length=1,
    )
    subject_id: str = Field(..., description="Subject ID", title="Subject ID")
    acq_datetime: datetime = Field(
        ...,
        description="Datetime data was acquired",
        title="Acquisition Datetime",
    )
    tasks: List[Union[Task, ModalityTask]] = Field(
        ...,
        description=(
            "List of tasks to run with custom settings. A ModalityTask must "
            "be provided for each modality. For other tasks, default settings "
            "for the job_type will be used unless overridden here."
        ),
        title="Tasks",
        min_length=1,
    )

    @computed_field
    def s3_prefix(self) -> str:
        """Construct s3_prefix from configs."""
        return build_data_name(
            label=f"{self.platform.abbreviation}_{self.subject_id}",
            creation_datetime=self.acq_datetime,
        )

    @model_validator(mode="before")
    def check_computed_field(cls, data: Any) -> Any:
        """If the computed field is present, we check that it's expected. If
        this validator isn't added, then an 'extra field not allow' error
        will be raised when serializing and deserializing json."""
        if isinstance(data, dict) and data.get("s3_prefix") is not None:
            expected_s3_prefix = build_data_name(
                label=(
                    f"{data.get('platform', dict()).get('abbreviation')}"
                    f"_{data.get('subject_id')}"
                ),
                creation_datetime=datetime.fromisoformat(
                    data.get("acq_datetime")
                ),
            )
            if expected_s3_prefix != data.get("s3_prefix"):
                raise ValueError(
                    f"s3_prefix {data.get('s3_prefix')} doesn't match "
                    f"computed {expected_s3_prefix}!"
                )
            else:
                del data["s3_prefix"]
        return data

    @field_validator("job_type", "project_name", mode="before")
    def validate_with_context(cls, v: str, info: ValidationInfo) -> str:
        """
        Validate certain fields. If a list of accepted values is provided in a
        context manager, then it will validate against the list. Otherwise, it
        won't raise any validation error.

        Parameters
        ----------
        v : str
          Value input into the field.
        info : ValidationInfo

        Returns
        -------
        str

        """
        valid_list = (info.context or dict()).get(f"{info.field_name}s")
        if valid_list is not None and v not in valid_list:
            raise ValueError(f"{v} must be one of {valid_list}")
        else:
            return v

    @field_validator("tasks", mode="after")
    def validate_tasks(
        cls, v: List[Union[Task, ModalityTask]]
    ) -> List[Union[Task, ModalityTask]]:
        """Validates that ModalityTasks are provided and all other task_ids "
        are unique."""
        # check at least 1 ModalityTask is provided
        if not any(isinstance(task, ModalityTask) for task in v):
            raise ValueError(
                "A ModalityTask must be provided for each modality!"
            )
        # check other tasks are unique
        task_ids = [
            task.task_id for task in v if not isinstance(task, ModalityTask)
        ]
        duplicates = {t.value for t in task_ids if task_ids.count(t) > 1}
        if duplicates:
            raise ValueError(
                f"Task IDs must be unique! Duplicates: {duplicates}"
            )
        return v


class SubmitJobRequestV2(BaseSettings):
    """Main request that will be sent to the backend. Bundles jobs into a list
    and allows a user to add an email address to receive notifications."""

    model_config = ConfigDict(use_enum_values=True, extra="allow")

    job_type: Literal["transform_and_upload_v2"] = "transform_and_upload_v2"
    user_email: Optional[EmailStr] = Field(
        default=None,
        description=(
            "Optional email address to receive job status notifications"
        ),
    )
    email_notification_types: Set[EmailNotificationType] = Field(
        default={EmailNotificationType.FAIL},
        description=(
            "Types of job statuses to receive email notifications about"
        ),
    )
    upload_jobs: List[UploadJobConfigsV2] = Field(
        ...,
        description="List of upload jobs to process. Max of 1000 at a time.",
        min_length=1,
        max_length=1000,
    )

    @model_validator(mode="after")
    def propagate_email_settings(self):
        """Propagate email settings from global to individual jobs"""
        global_email_user = self.user_email
        global_email_notification_types = self.email_notification_types
        for upload_job in self.upload_jobs:
            if global_email_user is not None and upload_job.user_email is None:
                upload_job.user_email = global_email_user
            if upload_job.email_notification_types is None:
                upload_job.email_notification_types = (
                    global_email_notification_types
                )
        return self
