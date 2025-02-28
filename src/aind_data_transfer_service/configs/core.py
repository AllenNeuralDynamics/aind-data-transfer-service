"""Core models for using V2 of aind-data-transfer-service"""

import json
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Set, Union

from aind_data_schema_models.data_name_patterns import build_data_name
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

    # noinspection PyMissingConstructor
    def __init__(self, /, **data: Any) -> None:
        """Add context manager to init for validating project_names."""
        self.__pydantic_validator__.validate_python(
            data,
            self_instance=self,
            context=_validation_context.get(),
        )

    model_config = ConfigDict(use_enum_values=True, extra="allow")

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

    job_type: str = Field(
        default="default",
        description=(
            "Job type for the upload job. Tasks will be run based on the "
            "job_type unless otherwise specified in task_overrides."
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
        min_items=1,
    )
    subject_id: str = Field(..., description="Subject ID", title="Subject ID")
    acq_datetime: datetime = Field(
        ...,
        description="Datetime data was acquired",
        title="Acquisition Datetime",
    )
    task_overrides: Optional[List[Union[CustomTask, SkipTask]]] = Field(
        default=None,
        description=(
            "List of tasks to run with custom settings. If null, "
            "will use default task settings for the job_type."
        ),
        title="Task Overrides",
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

    @field_validator("job_type", mode="before")
    def validate_job_type(cls, v: str, info: ValidationInfo) -> str:
        """
        Validate the job_type. If a list of job_types is provided in a
        context manager, then it will validate against the list. Otherwise, it
        won't raise any validation error.
        Parameters
        ----------
        v : str
          Value input into job_type field.
        info : ValidationInfo

        Returns
        -------
        str

        """
        job_types = (info.context or dict()).get("job_types")
        if job_types is not None and v not in job_types:
            raise ValueError(f"{v} must be one of {job_types}")
        else:
            return v

    @field_validator("project_name", mode="before")
    def validate_project_name(cls, v: str, info: ValidationInfo) -> str:
        """
        Validate the project name. If a list of project_names is provided in a
        context manager, then it will validate against the list. Otherwise, it
        won't raise any validation error.
        Parameters
        ----------
        v : str
          Value input into project_name field.
        info : ValidationInfo

        Returns
        -------
        str

        """
        project_names = (info.context or dict()).get("project_names")
        if project_names is not None and v not in project_names:
            raise ValueError(f"{v} must be one of {project_names}")
        else:
            return v

    @field_validator("task_overrides", mode="after")
    def check_task_overrides(
        cls, v: Optional[List[Union[CustomTask, SkipTask]]]
    ) -> Optional[List[Union[CustomTask, SkipTask]]]:
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
