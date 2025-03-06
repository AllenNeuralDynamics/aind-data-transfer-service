"""Core models for using V2 of aind-data-transfer-service"""

import json
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime
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


class Task(BaseSettings):
    """Configuration for a task run during a data transfer upload job."""

    task_id: str = Field(
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

    image: Optional[str] = Field(
        default=None, description="Name of docker image to run", title="Image"
    )
    image_version: Optional[str] = Field(
        default=None,
        description="Version of docker image to run",
        title="Image Version",
    )
    image_environment: Optional[Dict[str, Any]] = Field(
        default={},
        description=(
            "Environment for the docker image. Must be json serializable."
        ),
        title="Image Environment",
    )
    parameters_settings: Optional[Dict[str, Any]] = Field(
        default={},
        description="Settings for the task. Must be json serializable.",
        title="Parameters Settings",
    )
    dynamic_parameters_settings: Optional[Dict[str, Any]] = Field(
        default={},
        description=(
            "Dynamic settings for the task (e.g. modality, source, chunk). "
            "Must be json serializable."
        ),
        title="Dynamic Parameters Settings",
    )

    @field_validator(
        "image_environment",
        "parameters_settings",
        "dynamic_parameters_settings",
        mode="after",
    )
    def validate_json_serializable(
        cls, v: Optional[Dict[str, Any]], info: ValidationInfo
    ) -> Optional[Dict[str, Any]]:
        """Validate that fields are json serializable."""
        if v is not None:
            try:
                json.dumps(v)
            except Exception as e:
                raise ValueError(
                    f"{info.field_name} must be json serializable! If "
                    f"converting from a Pydantic model, please use "
                    f'model.model_dump(mode="json"). {e}'
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
    email_notification_types: Optional[
        Set[Literal["begin", "end", "fail", "retry", "all"]]
    ] = Field(
        default=None,
        description=(
            "Types of job statuses to receive email notifications about"
        ),
    )
    s3_bucket: Literal["private", "open", "default"] = Field(
        default="default",
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
    tasks: List[Task] = Field(
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
    def validate_tasks(cls, tasks: List[Task]) -> List[Task]:
        """Validates that modality tasks are provided and all other task_ids "
        are unique."""
        # check at least 1 modality task is provided
        if not any(task.task_id == "make_modality_list" for task in tasks):
            raise ValueError(
                "A modality task (task_id: make_modality_list) must be "
                "provided for each modality!"
            )
        # check other tasks are unique
        task_ids = [
            task.task_id
            for task in tasks
            if task.task_id != "make_modality_list"
        ]
        duplicates = {t for t in task_ids if task_ids.count(t) > 1}
        if duplicates:
            raise ValueError(
                f"Task IDs must be unique! Duplicates: {duplicates}"
            )
        return tasks


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
    email_notification_types: Set[
        Literal["begin", "end", "fail", "retry", "all"]
    ] = Field(
        default={"fail"},
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
