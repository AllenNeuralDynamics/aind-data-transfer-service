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

    model_config = ConfigDict(use_enum_values=True, extra="ignore")

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
    tasks: Dict[str, Union[Task, List[Task]]] = Field(
        ...,
        description=(
            "Dictionary of tasks to run with custom settings. The key must be "
            "the task_id and the value must be the task or list of tasks."
        ),
        title="Tasks",
    )

    @computed_field
    def s3_prefix(self) -> str:
        """Construct s3_prefix from configs."""
        return build_data_name(
            label=f"{self.platform.abbreviation}_{self.subject_id}",
            creation_datetime=self.acq_datetime,
        )

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


class SubmitJobRequestV2(BaseSettings):
    """Main request that will be sent to the backend. Bundles jobs into a list
    and allows a user to add an email address to receive notifications."""

    model_config = ConfigDict(use_enum_values=True, extra="ignore")

    dag_id: Literal["transform_and_upload_v2"] = "transform_and_upload_v2"
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
