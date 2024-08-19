"""Module for data models used in application"""

import ast
from datetime import datetime
from typing import List, Optional

from pydantic import AwareDatetime, BaseModel, Field


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

    limit: int = 25
    offset: int = 0
    state: Optional[list[str]] = []
    order_by: str = "-execution_date"
    execution_date_gte: Optional[str] = None

    @classmethod
    def from_query_params(cls, query_params: dict):
        """Maps the query parameters to the model"""
        params = dict(query_params)
        if 'state' in params:
            params['state'] = ast.literal_eval(params['state'])
        return cls(**params)


class JobStatus(BaseModel):
    """Model for what we want to render to the user."""

    end_time: Optional[datetime] = Field(None)
    job_id: Optional[str] = Field(None)
    job_state: Optional[str] = Field(None)
    name: Optional[str] = Field(None)
    comment: Optional[str] = Field(None)
    start_time: Optional[datetime] = Field(None)
    submit_time: Optional[datetime] = Field(None)

    @classmethod
    def from_airflow_dag_run(cls, airflow_dag_run: AirflowDagRun):
        """Maps the fields from the HpcJobStatusResponse to this model"""
        name = airflow_dag_run.conf.get("s3_prefix", "")
        return cls(
            end_time=airflow_dag_run.end_date,
            job_id=airflow_dag_run.dag_run_id,
            job_state=airflow_dag_run.state,
            name=name,
            comment=airflow_dag_run.note,
            start_time=airflow_dag_run.start_date,
            submit_time=airflow_dag_run.execution_date,
        )

    @property
    def jinja_dict(self):
        """Map model to a dictionary that jinja can render"""
        return self.model_dump(exclude_none=True)
