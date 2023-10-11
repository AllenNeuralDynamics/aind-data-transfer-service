"""Module to contain models for hpc rest api responses."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional, Union

from pydantic import (
    BaseModel,
    BaseSettings,
    Extra,
    Field,
    SecretStr,
    validator,
)
from pydantic.typing import Literal


class HpcJobSubmitSettings(BaseSettings):
    """Configs to send in a post request. v0.0.36 of slurm rest api."""

    account: Optional[str] = Field(
        None,
        description="Charge resources used by this job to specified account.",
    )
    # This is the way it is written in the slurm documentation
    account_gather_freqency: Optional[str] = Field(
        None,
        description=(
            "Define the job accounting and profiling sampling intervals."
        ),
    )
    argv: Optional[List[str]] = Field(
        None, description="Arguments to the script."
    )
    array: Optional[str] = Field(
        None,
        description=(
            "Submit a job array, multiple jobs to be executed with identical "
            "parameters. The indexes specification identifies what array "
            "index values should be used."
        ),
    )
    batch_features: Optional[str] = Field(
        None, description="features required for batch script's node"
    )
    begin_time: Optional[str] = Field(
        None,
        description=(
            "Submit the batch script to the Slurm controller immediately, "
            "like normal, but tell the controller to defer the allocation of "
            "the job until the specified time."
        ),
    )
    burst_buffer: Optional[str] = Field(
        None, description="Burst buffer specification."
    )
    cluster_constraints: Optional[str] = Field(
        None,
        description=(
            "Specifies features that a federated cluster must have to have a "
            "sibling job submitted to it."
        ),
    )
    comment: Optional[str] = Field(None, description="An arbitrary comment.")
    constraints: Optional[str] = Field(
        None, description="node features required by job."
    )
    core_specification: Optional[int] = Field(
        None,
        description=(
            "Count of specialized threads per node reserved by the job for "
            "system operations and not used by the application."
        ),
    )
    cores_per_socket: Optional[int] = Field(
        None,
        description=(
            "Restrict node selection to nodes with at least the specified "
            "number of cores per socket."
        ),
    )
    cpu_binding: Optional[str] = Field(None, description="Cpu binding")
    cpu_binding_hint: Optional[str] = Field(
        None, description="Cpu binding hint"
    )
    cpu_frequency: Optional[str] = Field(
        None,
        description=(
            "Request that job steps initiated by srun commands inside this "
            "sbatch script be run at some requested frequency if possible, on "
            "the CPUs selected for the step on the compute node(s)."
        ),
    )
    cpus_per_gpu: Optional[str] = Field(
        None, description="Number of CPUs requested per allocated GPU."
    )
    cpus_per_task: Optional[int] = Field(
        None,
        description=(
            "Advise the Slurm controller that ensuing job steps will require "
            "ncpus number of processors per task."
        ),
    )
    current_working_directory: Optional[str] = Field(
        None,
        description=(
            "Instruct Slurm to connect the batch script's standard output "
            "directly to the file name."
        ),
    )
    deadline: Optional[str] = Field(
        None,
        description=(
            "Remove the job if no ending is possible before this deadline "
            "(start > (deadline - time[-min]))."
        ),
    )
    delay_boot: Optional[int] = Field(
        None,
        description=(
            "Do not reboot nodes in order to satisfied this job's feature "
            "specification if the job has been eligible to run for less than "
            "this time period."
        ),
    )
    dependency: Optional[str] = Field(
        None,
        description=(
            "Defer the start of this job until the specified dependencies "
            "have been satisfied completed."
        ),
    )
    distribution: Optional[str] = Field(
        None,
        description=(
            "Specify alternate distribution methods for remote processes."
        ),
    )
    environment: Optional[dict] = Field(
        None, description="Dictionary of environment entries."
    )
    exclusive: Optional[Literal["user", "mcs", "true", "false"]] = Field(
        None,
        description=(
            "The job allocation can share nodes just other users with the "
            "'user' option or with the 'mcs' option)."
        ),
    )
    get_user_environment: Optional[bool] = Field(
        None, description="Load new login environment for user on job node."
    )
    gres: Optional[str] = Field(
        None,
        description=(
            "Specifies a comma delimited list of generic consumable resources."
        ),
    )
    gres_flags: Optional[
        Literal["disable-binding", "enforce-binding"]
    ] = Field(
        None, description="Specify generic resource task binding options."
    )
    gpu_binding: Optional[str] = Field(
        None, description="Requested binding of tasks to GPU."
    )
    gpu_frequency: Optional[str] = Field(
        None, description="Requested GPU frequency."
    )
    gpus: Optional[str] = Field(None, description="GPUs per job.")
    gpus_per_node: Optional[str] = Field(None, description="GPUs per node.")
    gpus_per_socket: Optional[str] = Field(
        None, description="GPUs per socket."
    )
    gpus_per_task: Optional[str] = Field(None, description="GPUs per task.")
    hold: Optional[bool] = Field(
        None,
        description=(
            "Specify the job is to be submitted in a held state "
            "(priority of zero)."
        ),
    )
    kill_on_invalid_dependency: Optional[bool] = Field(
        None,
        description=(
            "If a job has an invalid dependency, then Slurm is to "
            "terminate it."
        ),
    )
    licenses: Optional[str] = Field(
        None,
        description=(
            "Specification of licenses (or other resources available on all "
            "nodes of the cluster) which must be allocated to this job."
        ),
    )
    mail_type: Optional[str] = Field(
        None,
        description="Notify user by email when certain event types occur.",
    )
    mail_user: Optional[str] = Field(
        None,
        description=(
            "User to receive email notification of state changes as defined "
            "by mail_type."
        ),
    )
    mcs_label: Optional[str] = Field(
        None,
        description="This parameter is a group among the groups of the user.",
    )
    memory_binding: Optional[str] = Field(
        None, description="Bind tasks to memory."
    )
    memory_per_cpu: Optional[int] = Field(
        None, description="Minimum real memory per cpu (MB)."
    )
    memory_per_gpu: Optional[int] = Field(
        None, description="Minimum memory required per allocated GPU."
    )
    memory_per_node: Optional[int] = Field(
        None, description="Minimum real memory per node (MB)."
    )
    minimum_cpus_per_node: Optional[int] = Field(
        None, description="Minimum number of CPUs per node."
    )
    minimum_nodes: Optional[bool] = Field(
        None,
        description=(
            "If a range of node counts is given, prefer the smaller count."
        ),
    )
    name: Optional[str] = Field(
        None, description="Specify a name for the job allocation."
    )
    nice: Optional[str] = Field(
        None,
        description=(
            "Run the job with an adjusted scheduling priority within Slurm."
        ),
    )
    no_kill: Optional[bool] = Field(
        None,
        description=(
            "Do not automatically terminate a job if one of the nodes it has "
            "been allocated fails."
        ),
    )
    nodes: Optional[List[int]] = Field(
        None,
        description=(
            "Request that a minimum of minnodes nodes and a maximum node "
            "count."
        ),
    )
    open_mode: Optional[Literal["append", "truncate"]] = Field(
        None,
        description=(
            "Open the output and error files using append or truncate mode "
            "as specified."
        ),
    )
    partition: Optional[str] = Field(
        None,
        description=(
            "Request a specific partition for the resource allocation."
        ),
    )
    priority: Optional[str] = Field(
        None, description="Request a specific job priority."
    )
    # Set this to "production" for production environment
    qos: Optional[str] = Field(
        None, description="Request a quality of service for the job."
    )
    requeue: Optional[bool] = Field(
        None,
        description=(
            "Specifies that the batch job should eligible to being requeue."
        ),
    )
    reservation: Optional[str] = Field(
        None,
        description=(
            "Allocate resources for the job from the named reservation."
        ),
    )
    signal: Optional[str] = Field(
        None,
        description=(
            "When a job is within sig_time seconds of its end time, send it "
            "the signal sig_num."
        ),
    )
    sockets_per_node: Optional[int] = Field(
        None,
        description=(
            "Restrict node selection to nodes with at least the specified "
            "number of sockets."
        ),
    )
    spread_job: Optional[bool] = Field(
        None,
        description=(
            "Spread the job allocation over as many nodes as possible and "
            "attempt to evenly distribute tasks across the allocated nodes."
        ),
    )
    standard_error: Optional[str] = Field(
        None,
        description=(
            "Instruct Slurm to connect the batch script's standard error "
            "directly to the file name."
        ),
    )
    standard_in: Optional[str] = Field(
        None,
        description=(
            "Instruct Slurm to connect the batch script's standard input "
            "directly to the file name specified."
        ),
    )
    standard_out: Optional[str] = Field(
        None,
        description=(
            "Instruct Slurm to connect the batch script's standard output "
            "directly to the file name."
        ),
    )
    tasks: Optional[int] = Field(
        None,
        description=(
            "Advises the Slurm controller that job steps run within the "
            "allocation will launch a maximum of number tasks and to provide "
            "for sufficient resources."
        ),
    )
    tasks_per_core: Optional[int] = Field(
        None, description="Request the maximum ntasks be invoked on each core."
    )
    tasks_per_node: Optional[int] = Field(
        None, description="Request the maximum ntasks be invoked on each node."
    )
    tasks_per_socket: Optional[int] = Field(
        None,
        description="Request the maximum ntasks be invoked on each socket.",
    )
    thread_specification: Optional[int] = Field(
        None,
        description=(
            "Count of specialized threads per node reserved by the job for "
            "system operations and not used by the application."
        ),
    )
    threads_per_core: Optional[int] = Field(
        None,
        description=(
            "Restrict node selection to nodes with at least the specified "
            "number of threads per core."
        ),
    )
    time_limit: Optional[int] = Field(None, description="Step time limit.")
    time_minimum: Optional[int] = Field(
        None, description="Minimum run time in minutes."
    )
    wait_all_nodes: Optional[bool] = Field(
        None,
        description=(
            "Do not begin execution until all nodes are ready for " "use."
        ),
    )
    wckey: Optional[str] = Field(
        None, description="Specify wckey to be used with job."
    )

    class Config:
        """Config to set env var prefix to HPC"""

        extra = Extra.forbid
        env_prefix = "HPC_"

    @staticmethod
    def script_command_str(sif_loc_str) -> str:
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
        ]
        return " ".join(command_str)

    @staticmethod
    def _set_default_val(values: dict, key: str, default_value: Any) -> None:
        """Util method to set a default if value not in dict[key]"""
        if values.get(key) is None:
            values[key] = default_value
        return None

    @classmethod
    def from_upload_job_configs(
        cls,
        logging_directory: Path,
        aws_secret_access_key: SecretStr,
        aws_access_key_id: str,
        aws_default_region: str,
        aws_session_token: Optional[SecretStr] = None,
        **kwargs,
    ):
        """
        Class constructor to use when submitting a basic upload job request
        Parameters
        ----------
        logging_directory : Path
        aws_secret_access_key : SecretStr
        aws_access_key_id : str
        aws_default_region : str
        aws_session_token : Optional[SecretStr]
        kwargs : dict
          Hpc settings
        """
        hpc_env = {
            "PATH": "/bin:/usr/bin/:/usr/local/bin/",
            "LD_LIBRARY_PATH": "/lib/:/lib64/:/usr/local/lib",
            "SINGULARITYENV_AWS_SECRET_ACCESS_KEY": (
                aws_secret_access_key.get_secret_value()
            ),
            "SINGULARITYENV_AWS_ACCESS_KEY_ID": aws_access_key_id,
            "SINGULARITYENV_AWS_DEFAULT_REGION": aws_default_region,
        }
        if aws_session_token is not None:
            hpc_env[
                "SINGULARITYENV_AWS_SESSION_TOKEN"
            ] = aws_session_token.get_secret_value()
        cls._set_default_val(kwargs, "environment", hpc_env)
        # Set default time limit to 3 hours
        cls._set_default_val(kwargs, "time_limit", 180)
        cls._set_default_val(
            kwargs,
            "standard_out",
            str(logging_directory / (kwargs["name"] + ".out")),
        )
        cls._set_default_val(
            kwargs,
            "standard_error",
            str(logging_directory / (kwargs["name"] + "_error.out")),
        )
        cls._set_default_val(kwargs, "nodes", [1, 1])
        cls._set_default_val(kwargs, "minimum_cpus_per_node", 4)
        cls._set_default_val(kwargs, "tasks", 1)
        # 8 GB per cpu for 32 GB total memory
        cls._set_default_val(kwargs, "memory_per_cpu", 8000)
        return cls(**kwargs)

    @classmethod
    def attach_configs_to_script(
        cls,
        script: str,
        base_configs: dict,
        upload_configs_aws_param_store_name: Optional[str],
        staging_directory: Optional[str],
    ) -> str:
        """
        Helper method to attach configs to a base run command string.
        Parameters
        ----------
        script : str
          Can be like
          '#!/bin/bash \nsingularity exec --cleanenv
          feat_289.sif python -m aind_data_transfer.jobs.basic_job'
        base_configs : dict
          job_configs to attach as --json-args
        upload_configs_aws_param_store_name : Optional[str]
          Will supply this config if not in base_configs and not None
        staging_directory : Optional[str]
          Will supply this config if not in base_configs and not None

        Returns
        -------
        str
          The run command script to send to submit to the slurm cluster

        """
        if staging_directory is not None:
            cls._set_default_val(
                base_configs, "temp_directory", staging_directory
            )
        if upload_configs_aws_param_store_name is not None:
            cls._set_default_val(
                base_configs,
                "aws_param_store_name",
                upload_configs_aws_param_store_name,
            )

        return " ".join(
            [
                script,
                "--json-args",
                "'",
                json.dumps(base_configs),
                "'",
            ]
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
