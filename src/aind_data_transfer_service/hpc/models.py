"""Module to contain models for hpc rest api responses."""

from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional, Union

from pydantic import BaseModel, BaseSettings, Field, SecretStr, validator

from aind_data_transfer_service.configs.job_configs import (
    BasicUploadJobConfigs,
)


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


class HpcJobSubmitSettings(BaseSettings):
    """Possible configs to send in a post request. These were generated from
    v0.0.39 so there may be slight discrepancies posting to older versions."""

    account: Optional[str] = Field(None)
    account_gather_frequency: Optional[str] = Field(None)
    admin_comment: Optional[str] = Field(None)
    allocation_node_list: Optional[str] = Field(None)
    allocation_node_port: Optional[int] = Field(None)
    argv: Optional[List[str]] = Field(None)
    array: Optional[str] = Field(None)
    batch_features: Optional[str] = Field(None)
    begin_time: Optional[int] = Field(None)
    flags: Optional[List[str]] = Field(None)
    burst_buffer: Optional[str] = Field(None)
    clusters: Optional[str] = Field(None)
    cluster_constraint: Optional[str] = Field(None)
    comment: Optional[str] = Field(None)
    contiguous: Optional[bool] = Field(None)
    container: Optional[str] = Field(None)
    container_id: Optional[str] = Field(None)
    core_specification: Optional[int] = Field(None)
    thread_specification: Optional[int] = Field(None)
    cpu_binding: Optional[str] = Field(None)
    cpu_binding_flags: Optional[List[str]] = Field(None)
    cpu_frequency: Optional[str] = Field(None)
    cpus_per_tres: Optional[str] = Field(None)
    crontab: Optional[str] = Field(None)
    deadline: Optional[int] = Field(None)
    delay_boot: Optional[int] = Field(None)
    dependency: Optional[str] = Field(None)
    end_time: Optional[int] = Field(None)
    # v0.0.39 has environment: List[str], but a dict works in v0.0.36
    environment: dict
    excluded_nodes: Optional[List[str]] = Field(None)
    extra: Optional[str] = Field(None)
    constraints: Optional[str] = Field(None)
    group_id: Optional[str] = Field(None)
    hetjob_group: Optional[int] = Field(None)
    immediate: Optional[bool] = Field(None)
    job_id: Optional[int] = Field(None)
    kill_on_node_fail: Optional[bool] = Field(None)
    licenses: Optional[str] = Field(None)
    mail_type: Optional[List[str]] = Field(None)
    mail_user: Optional[str] = Field(None)
    mcs_label: Optional[str] = Field(None)
    memory_binding: Optional[str] = Field(None)
    memory_binding_type: Optional[List[str]] = Field(None)
    memory_per_tres: Optional[str] = Field(None)
    name: Optional[str] = Field(None)
    network: Optional[str] = Field(None)
    nice: Optional[int] = Field(None)
    tasks: Optional[int] = Field(None)
    open_mode: Optional[List[str]] = Field(None)
    reserve_ports: Optional[int] = Field(None)
    overcommit: Optional[bool] = Field(None)
    partition: Optional[str] = Field(None)
    distribution_plane_size: Optional[int] = Field(None)
    power_flags: Optional[List[str]] = Field(None)
    prefer: Optional[str] = Field(None)
    hold: Optional[bool] = Field(None)
    priority: Optional[int] = Field(None)
    profile: Optional[List[str]] = Field(None)
    qos: Optional[str] = Field(None)
    reboot: Optional[bool] = Field(None)
    required_nodes: Optional[List[str]] = Field(None)
    requeue: Optional[bool] = Field(None)
    reservation: Optional[str] = Field(None)
    script: Optional[str] = Field(None)
    shared: Optional[List[str]] = Field(None)
    exclusive: Optional[List[str]] = Field(None)
    oversubscribe: Optional[bool] = Field(None)
    site_factor: Optional[int] = Field(None)
    spank_environment: Optional[List[str]] = Field(None)
    distribution: Optional[str] = Field(None)
    time_limit: Optional[int] = Field(None)
    time_minimum: Optional[int] = Field(None)
    tres_bind: Optional[str] = Field(None)
    tres_freq: Optional[str] = Field(None)
    tres_per_job: Optional[str] = Field(None)
    tres_per_node: Optional[str] = Field(None)
    tres_per_socket: Optional[str] = Field(None)
    tres_per_task: Optional[str] = Field(None)
    user_id: Optional[str] = Field(None)
    wait_all_nodes: Optional[bool] = Field(None)
    kill_warning_flags: Optional[List[str]] = Field(None)
    kill_warning_signal: Optional[str] = Field(None)
    kill_warning_delay: Optional[int] = Field(None)
    current_working_directory: Optional[str] = Field(None)
    cpus_per_task: Optional[int] = Field(None)
    minimum_cpus: Optional[int] = Field(None)
    maximum_cpus: Optional[int] = Field(None)
    nodes: Optional[str] = Field(None)
    minimum_nodes: Optional[int] = Field(None)
    maximum_nodes: Optional[int] = Field(None)
    minimum_boards_per_node: Optional[int] = Field(None)
    minimum_sockets_per_board: Optional[int] = Field(None)
    sockets_per_node: Optional[int] = Field(None)
    threads_per_core: Optional[int] = Field(None)
    tasks_per_node: Optional[int] = Field(None)
    tasks_per_socket: Optional[int] = Field(None)
    tasks_per_core: Optional[int] = Field(None)
    tasks_per_board: Optional[int] = Field(None)
    ntasks_per_tres: Optional[int] = Field(None)
    minimum_cpus_per_node: Optional[int] = Field(None)
    memory_per_cpu: Optional[int] = Field(None)
    memory_per_node: Optional[int] = Field(None)
    temporary_disk_per_node: Optional[int] = Field(None)
    selinux_context: Optional[str] = Field(None)
    required_switches: Optional[int] = Field(None)
    standard_error: Optional[str] = Field(None)
    standard_input: Optional[str] = Field(None)
    standard_output: Optional[str] = Field(None)
    wait_for_switch: Optional[int] = Field(None)
    wckey: Optional[str] = Field(None)
    # These do not appear to be in v0.0.36?
    # x11: Optional[List[str]] = Field(None)
    # x11_magic_cookie: Optional[str] = Field(None)
    # x11_target_host: Optional[str] = Field(None)
    # x11_target_port: Optional[int] = Field(None)

    class Config:
        """Config to set env var prefix to HPC"""

        env_prefix = "HPC_"

    @staticmethod
    def _script_command_str(sif_loc_str, json_arg_str) -> str:
        """This is the command that will be sent to the hpc"""
        command_str = [
            "#!/bin/bash",
            "\nsingularity",
            "exec",
            "--cleanenv",
            sif_loc_str,
            "python",
            "-m",
            "aind_data_transfer.jobs.basic_job",
            "--json-args",
            "'",
            json_arg_str,
            "'",
        ]
        return " ".join(command_str)

    @staticmethod
    def _set_default_val(values: dict, key: str, default_value: Any) -> None:
        if values.get(key) is None:
            values[key] = default_value
        return None

    @classmethod
    def from_basic_job_configs(
        cls,
        basic_upload_job_configs: BasicUploadJobConfigs,
        sif_location: Path,
        logging_directory: Path,
        aws_secret_access_key: SecretStr,
        aws_access_key_id: str,
        aws_default_region: str,
        aws_session_token: Optional[SecretStr] = None,
        time_limit_in_minutes: int = 360,
        **kwargs,
    ):
        hpc_env = {
            "PATH": "/bin:/usr/bin/:/usr/local/bin/",
            "LD_LIBRARY_PATH": "/lib/:/lib64/:/usr/local/lib",
            "SINGULARITYENV_AWS_SECRET_ACCESS_KEY": (
                aws_secret_access_key.get_secret_value()
            ),
            "SINGULARITYENV_AWS_ACCESS_KEY_ID": aws_access_key_id,
            "SINGULARITYENV_AWS_DEFAULT_REGION": aws_default_region,
        }
        run_script = cls._script_command_str(
            sif_loc_str=sif_location,
            json_arg_str=basic_upload_job_configs.json(),
        )
        time_limit_str = "{:02d}:{:02d}:00".format(
            *divmod(time_limit_in_minutes, 60)
        )
        if aws_session_token is not None:
            hpc_env["SINGULARITYENV_AWS_SESSION_TOKEN"] = aws_session_token
        cls._set_default_val(kwargs, "environment", hpc_env)
        cls._set_default_val(kwargs, "script", run_script)
        cls._set_default_val(
            kwargs, "name", basic_upload_job_configs.s3_prefix
        )
        cls._set_default_val(
            kwargs, "name", basic_upload_job_configs.s3_prefix
        )
        cls._set_default_val(
            kwargs,
            "standard_output",
            str(logging_directory / (kwargs["name"] + ".out")),
        )
        cls._set_default_val(
            kwargs,
            "standard_output",
            str(logging_directory / (kwargs["name"] + "_error.out")),
        )
        cls._set_default_val(kwargs, "minimum_nodes", 1)
        cls._set_default_val(kwargs, "maximum_nodes", 1)
        cls._set_default_val(kwargs, "memory_per_node", "50g")
        cls._set_default_val(kwargs, "time_limit", time_limit_str)
        return cls(**kwargs)


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
        timestamp is not set, for example, the end time for a job that is
        pending will have an end_time of 0."""
        if type(timestamp) is datetime:
            return timestamp
        elif timestamp is None or timestamp == 0:
            return None
        else:
            return datetime.fromtimestamp(timestamp)

    @classmethod
    def from_hpc_job_status(cls, hpc_job: HpcJobStatusResponse):
        """Maps the fields from the HpcJobStatusResponse to this model"""
        return cls(
            end_time=hpc_job.end_time,
            job_id=hpc_job.job_id,
            job_state=hpc_job.job_state,
            name=hpc_job.name,
            start_time=hpc_job.start_time,
            submit_time=hpc_job.submit_time,
        )

    @property
    def jinja_dict(self):
        """Map model to a dictionary that jinja can render"""
        return self.dict(exclude_none=True)
