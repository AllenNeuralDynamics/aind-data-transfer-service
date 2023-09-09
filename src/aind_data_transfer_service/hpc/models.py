"""Module to contain models for hpc rest api responses."""

from datetime import datetime
from typing import List, Optional, Union

from pydantic import BaseModel, Field, validator


class HpcJobStatusResponse(BaseModel):
    """Model for a job status response for v0.0.36
    Version 0.0.39 can be found at
    https://slurm.schedmd.com/rest_api.html#v0.0.39_job_info"""

    account: Optional[str] = Field(None)
    accrue_time: Optional[int] = Field(None)
    admin_comment: Optional[str] = Field(None)
    array_job_id: Optional[int] = Field(None)
    array_task_id: Optional[int] = Field(None)
    array_max_tasks: Optional[int] = Field(None)
    array_task_string: Optional[str] = Field(None)
    association_id: Optional[int] = Field(None)
    batch_features: Optional[str] = Field(None)
    batch_flag: Optional[bool] = Field(None)
    batch_host: Optional[str] = Field(None)
    flags: Optional[List[str]] = Field(None)
    burst_buffer: Optional[str] = Field(None)
    burst_buffer_state: Optional[str] = Field(None)
    cluster: Optional[str] = Field(None)
    cluster_features: Optional[str] = Field(None)
    command: Optional[str] = Field(None)
    comment: Optional[str] = Field(None)
    contiguous: Optional[bool] = Field(None)
    core_spec: Optional[int] = Field(None)
    thread_spec: Optional[int] = Field(None)
    cores_per_socket: Optional[int] = Field(None)
    billable_tres: Optional[float] = Field(None)
    cpus_per_task: Optional[int] = Field(None)
    cpu_frequency_minimum: Optional[int] = Field(None)
    cpu_frequency_maximum: Optional[int] = Field(None)
    cpu_frequency_governor: Optional[int] = Field(None)
    cpus_per_tres: Optional[str] = Field(None)
    deadline: Optional[int] = Field(None)
    delay_boot: Optional[int] = Field(None)
    dependency: Optional[str] = Field(None)
    derived_exit_code: Optional[int] = Field(None)
    eligible_time: Optional[int] = Field(None)
    end_time: Optional[int] = Field(None)
    excluded_nodes: Optional[str] = Field(None)
    exit_code: Optional[int] = Field(None)
    features: Optional[str] = Field(None)
    federation_origin: Optional[str] = Field(None)
    federation_siblings_active: Optional[str] = Field(None)
    federation_siblings_viable: Optional[str] = Field(None)
    gres_detail: Optional[List[str]] = Field(None)
    group_id: Optional[int] = Field(None)
    job_id: Optional[int] = Field(None)
    job_resources: Optional[dict] = Field(None)
    job_state: Optional[str] = Field(None)
    last_sched_evaluation: Optional[int] = Field(None)
    licenses: Optional[str] = Field(None)
    max_cpus: Optional[int] = Field(None)
    max_nodes: Optional[int] = Field(None)
    mcs_label: Optional[str] = Field(None)
    memory_per_tres: Optional[str] = Field(None)
    name: Optional[str] = Field(None)
    nodes: Optional[str] = Field(None)
    nice: Optional[int] = Field(None)
    tasks_per_core: Optional[int] = Field(None)
    tasks_per_node: Optional[int] = Field(None)
    tasks_per_socket: Optional[int] = Field(None)
    tasks_per_board: Optional[int] = Field(None)
    cpus: Optional[int] = Field(None)
    node_count: Optional[int] = Field(None)
    tasks: Optional[int] = Field(None)
    het_job_id: Optional[int] = Field(None)
    het_job_id_set: Optional[str] = Field(None)
    het_job_offset: Optional[int] = Field(None)
    partition: Optional[str] = Field(None)
    memory_per_node: Optional[int] = Field(None)
    memory_per_cpu: Optional[int] = Field(None)
    minimum_cpus_per_node: Optional[int] = Field(None)
    minimum_tmp_disk_per_node: Optional[int] = Field(None)
    preempt_time: Optional[int] = Field(None)
    pre_sus_time: Optional[int] = Field(None)
    priority: Optional[int] = Field(None)
    profile: Optional[List[str]] = Field(None)
    qos: Optional[str] = Field(None)
    reboot: Optional[bool] = Field(None)
    required_nodes: Optional[str] = Field(None)
    requeue: Optional[bool] = Field(None)
    resize_time: Optional[int] = Field(None)
    restart_cnt: Optional[int] = Field(None)
    resv_name: Optional[str] = Field(None)
    shared: Optional[List[str]] = Field(None)
    show_flags: Optional[List[str]] = Field(None)
    sockets_per_board: Optional[int] = Field(None)
    sockets_per_node: Optional[int] = Field(None)
    start_time: Optional[int] = Field(None)
    state_description: Optional[str] = Field(None)
    state_reason: Optional[str] = Field(None)
    standard_error: Optional[str] = Field(None)
    standard_input: Optional[str] = Field(None)
    standard_output: Optional[str] = Field(None)
    submit_time: Optional[int] = Field(None)
    suspend_time: Optional[int] = Field(None)
    system_comment: Optional[str] = Field(None)
    time_limit: Optional[int] = Field(None)
    time_minimum: Optional[int] = Field(None)
    threads_per_core: Optional[int] = Field(None)
    tres_bind: Optional[str] = Field(None)
    tres_freq: Optional[str] = Field(None)
    tres_per_job: Optional[str] = Field(None)
    tres_per_node: Optional[str] = Field(None)
    tres_per_socket: Optional[str] = Field(None)
    tres_per_task: Optional[str] = Field(None)
    tres_req_str: Optional[str] = Field(None)
    tres_alloc_str: Optional[str] = Field(None)
    user_id: Optional[int] = Field(None)
    user_name: Optional[str] = Field(None)
    wckey: Optional[str] = Field(None)
    current_working_directory: Optional[str] = Field(None)


class JobStatus(BaseModel):
    """Model for what we want to render to the user."""

    end_time: Optional[datetime] = Field(None)
    job_id: Optional[int] = Field(None)
    job_state: Optional[str] = Field(None)
    name: Optional[str] = Field(None)
    start_time: Optional[datetime] = Field(None)
    submit_time: Optional[datetime] = Field(None)

    @validator("end_time", "start_time", "submit_time", pre=True)
    def _parse_timestamp(
        cls, timestamp: Union[int, datetime, None]
    ) -> Optional[datetime]:
        """Maps timestamp to datetime. As default, the hpc returns 0 if the
        timestamp is not set, for example, the end time for a job that hasn't
        finished will have and end_time of 0."""
        if type(timestamp) is datetime:
            return timestamp
        elif timestamp is None or timestamp == 0:
            return None
        else:
            return datetime.fromtimestamp(timestamp)

    @classmethod
    def from_hpc_job_status(cls, slurm_job: HpcJobStatusResponse):
        """Maps the fields from the SlurmJobStatusResponse to this model"""
        return cls(
            end_time=slurm_job.end_time,
            job_id=slurm_job.job_id,
            job_state=slurm_job.job_state,
            name=slurm_job.name,
            start_time=slurm_job.start_time,
            submit_time=slurm_job.submit_time,
        )

    @property
    def jinja_dict(self):
        """Map model to a dictionary that jinja can render"""
        return self.dict(exclude_none=True)
