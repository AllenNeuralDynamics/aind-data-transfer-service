"""Module to contain models for hpc rest api responses."""

import json
from pathlib import PurePosixPath
from typing import Any, List, Literal, Optional

from pydantic import Extra, Field, SecretStr
from pydantic_settings import BaseSettings


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
        logging_directory: PurePosixPath,
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
        logging_directory : PurePosixPath
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
