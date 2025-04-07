"""Module for internal data models used in application"""

import ast
import os
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Union

from mypy_boto3_ssm.type_defs import ParameterMetadataTypeDef
from pydantic import AwareDatetime, BaseModel, Field, field_validator
from starlette.datastructures import QueryParams


class AirflowDagRun(BaseModel):
    """Data model for dag_run entry when requesting info from airflow"""

    conf: Optional[dict]
    dag_id: Optional[str]
    dag_run_id: Optional[str]
    data_interval_end: Optional[AwareDatetime]
    data_interval_start: Optional[AwareDatetime]
    end_date: Optional[AwareDatetime]
    execution_date: Optional[AwareDatetime]
    external_trigger: Optional[bool]
    last_scheduling_decision: Optional[AwareDatetime]
    logical_date: Optional[AwareDatetime]
    note: Optional[str]
    run_type: Optional[str]
    start_date: Optional[AwareDatetime]
    state: Optional[str]


class AirflowDagRunsResponse(BaseModel):
    """Data model for response when requesting info from dag_runs endpoint"""

    dag_runs: List[AirflowDagRun]
    total_entries: int


class AirflowDagRunsRequestParameters(BaseModel):
    """Model for parameters when requesting info from dag_runs endpoint"""

    dag_ids: list[str] = ["transform_and_upload", "transform_and_upload_v2"]
    page_limit: int = 100
    page_offset: int = 0
    states: Optional[list[str]] = []
    execution_date_gte: Optional[str] = (
        datetime.now(timezone.utc) - timedelta(weeks=2)
    ).isoformat()
    execution_date_lte: Optional[str] = None
    order_by: str = "-execution_date"

    @field_validator("execution_date_gte", mode="after")
    def validate_min_execution_date(cls, execution_date_gte: str):
        """Validate the earliest submit date filter is within 2 weeks"""
        min_execution_date = datetime.now(timezone.utc) - timedelta(weeks=2)
        # datetime.fromisoformat does not support Z in python < 3.11
        date_to_check = execution_date_gte.replace("Z", "+00:00")
        if datetime.fromisoformat(date_to_check) < min_execution_date:
            raise ValueError(
                "execution_date_gte must be within the last 2 weeks"
            )
        return execution_date_gte

    @classmethod
    def from_query_params(cls, query_params: QueryParams):
        """Maps the query parameters to the model"""
        params = dict(query_params)
        if "states" in params:
            params["states"] = ast.literal_eval(params["states"])
        return cls.model_validate(params)


class AirflowTaskInstancesRequestParameters(BaseModel):
    """Model for parameters when requesting info from task_instances
    endpoint"""

    dag_id: str = Field(..., min_length=1)
    dag_run_id: str = Field(..., min_length=1)

    @classmethod
    def from_query_params(cls, query_params: QueryParams):
        """Maps the query parameters to the model"""
        params = dict(query_params)
        return cls.model_validate(params)


class AirflowTaskInstance(BaseModel):
    """Data model for task_instance entry when requesting info from airflow"""

    dag_id: Optional[str]
    dag_run_id: Optional[str]
    duration: Optional[Union[int, float]]
    end_date: Optional[AwareDatetime]
    execution_date: Optional[AwareDatetime]
    executor_config: Optional[str]
    hostname: Optional[str]
    map_index: Optional[int]
    max_tries: Optional[int]
    note: Optional[str]
    operator: Optional[str]
    pid: Optional[int]
    pool: Optional[str]
    pool_slots: Optional[int]
    priority_weight: Optional[int]
    queue: Optional[str]
    queued_when: Optional[AwareDatetime]
    rendered_fields: Optional[dict]
    sla_miss: Optional[dict]
    start_date: Optional[AwareDatetime]
    state: Optional[str]
    task_id: Optional[str]
    trigger: Optional[dict]
    triggerer_job: Optional[dict]
    try_number: Optional[int]
    unixname: Optional[str]


class AirflowTaskInstancesResponse(BaseModel):
    """Data model for response when requesting info from task_instances
    endpoint"""

    task_instances: List[AirflowTaskInstance]
    total_entries: int


class AirflowTaskInstanceLogsRequestParameters(BaseModel):
    """Model for parameters when requesting info from task_instance_logs
    endpoint"""

    # excluded fields are used to build the url
    dag_id: str = Field(..., min_length=1, exclude=True)
    dag_run_id: str = Field(..., min_length=1, exclude=True)
    task_id: str = Field(..., min_length=1, exclude=True)
    try_number: int = Field(..., ge=0, exclude=True)
    map_index: int = Field(..., ge=-1)
    full_content: bool = True

    @classmethod
    def from_query_params(cls, query_params: QueryParams):
        """Maps the query parameters to the model"""
        params = dict(query_params)
        return cls.model_validate(params)


class JobStatus(BaseModel):
    """Model for what we want to render to the user."""

    dag_id: Optional[str] = Field(None)
    end_time: Optional[datetime] = Field(None)
    job_id: Optional[str] = Field(None)
    job_state: Optional[str] = Field(None)
    name: Optional[str] = Field(None)
    job_type: Optional[str] = Field(None)
    comment: Optional[str] = Field(None)
    start_time: Optional[datetime] = Field(None)
    submit_time: Optional[datetime] = Field(None)

    @classmethod
    def from_airflow_dag_run(cls, airflow_dag_run: AirflowDagRun):
        """Maps the fields from the HpcJobStatusResponse to this model"""
        name = airflow_dag_run.conf.get("s3_prefix", "")
        job_type = airflow_dag_run.conf.get("job_type", "")
        # v1 job_type is in CO configs
        if job_type == "":
            job_type = airflow_dag_run.conf.get("codeocean_configs", {}).get(
                "job_type", ""
            )
        return cls(
            dag_id=airflow_dag_run.dag_id,
            end_time=airflow_dag_run.end_date,
            job_id=airflow_dag_run.dag_run_id,
            job_state=airflow_dag_run.state,
            name=name,
            job_type=job_type,
            comment=airflow_dag_run.note,
            start_time=airflow_dag_run.start_date,
            submit_time=airflow_dag_run.execution_date,
        )

    @property
    def jinja_dict(self):
        """Map model to a dictionary that jinja can render"""
        return self.model_dump(exclude_none=True)


class JobTasks(BaseModel):
    """Model for what is rendered to the user for each task."""

    dag_id: Optional[str] = Field(None)
    job_id: Optional[str] = Field(None)
    task_id: Optional[str] = Field(None)
    try_number: Optional[int] = Field(None)
    task_state: Optional[str] = Field(None)
    priority_weight: Optional[int] = Field(None)
    map_index: Optional[int] = Field(None)
    submit_time: Optional[datetime] = Field(None)
    start_time: Optional[datetime] = Field(None)
    end_time: Optional[datetime] = Field(None)
    duration: Optional[Union[int, float]] = Field(None)
    comment: Optional[str] = Field(None)

    @classmethod
    def from_airflow_task_instance(
        cls, airflow_task_instance: AirflowTaskInstance
    ):
        """Maps the fields from the HpcJobStatusResponse to this model"""
        return cls(
            dag_id=airflow_task_instance.dag_id,
            job_id=airflow_task_instance.dag_run_id,
            task_id=airflow_task_instance.task_id,
            try_number=airflow_task_instance.try_number,
            task_state=airflow_task_instance.state,
            priority_weight=airflow_task_instance.priority_weight,
            map_index=airflow_task_instance.map_index,
            submit_time=airflow_task_instance.execution_date,
            start_time=airflow_task_instance.start_date,
            end_time=airflow_task_instance.end_date,
            duration=airflow_task_instance.duration,
            comment=airflow_task_instance.note,
        )


class JobParamInfo(BaseModel):
    """Model for job parameter info from AWS Parameter Store"""

    name: Optional[str]
    last_modified: Optional[datetime]
    job_type: str
    task_id: str
    modality: Optional[str]

    @classmethod
    def from_aws_describe_parameter(
        cls,
        parameter: ParameterMetadataTypeDef,
        job_type: str,
        task_id: str,
        modality: Optional[str],
    ):
        """Map the parameter to the model"""
        return cls(
            name=parameter.get("Name"),
            last_modified=parameter.get("LastModifiedDate"),
            job_type=job_type,
            task_id=task_id,
            modality=modality,
        )

    @staticmethod
    def get_parameter_prefix(version: Optional[str] = None) -> str:
        """Get the prefix for job_type parameters"""
        prefix = os.getenv("AIND_AIRFLOW_PARAM_PREFIX")
        if version is None:
            return prefix
        return f"{prefix}/{version}"

    @staticmethod
    def get_parameter_regex(version: Optional[str] = None) -> str:
        """Create the regex pattern to match the parameter name"""
        prefix = os.getenv("AIND_AIRFLOW_PARAM_PREFIX")
        regex = (
            "(?P<job_type>[^/]+)/tasks/(?P<task_id>[^/]+)"
            "(?:/(?P<modality>[^/]+))?"
        )
        if version is None:
            return f"{prefix}/{regex}"
        return f"{prefix}/{version}/{regex}"

    @staticmethod
    def get_parameter_name(
        job_type: str, task_id: str, version: Optional[str] = None
    ) -> str:
        """Create the parameter name from job_type and task_id"""
        prefix = os.getenv("AIND_AIRFLOW_PARAM_PREFIX")
        if version is None:
            return f"{prefix}/{job_type}/tasks/{task_id}"
        return f"{prefix}/{version}/{job_type}/tasks/{task_id}"
