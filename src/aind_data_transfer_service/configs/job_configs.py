"""This module adds classes to handle resolving common endpoints used in the
data transfer jobs."""
import re
from datetime import date, datetime, time
from pathlib import Path
from typing import Any, Dict, List, Optional

from aind_data_schema.data_description import (
    ExperimentType,
    Modality,
    build_data_name,
)
from aind_data_schema.processing import ProcessName
from pydantic import BaseSettings, Field, PrivateAttr, SecretStr, validator


class ModalityConfigs(BaseSettings):
    """Class to contain configs for each modality type"""

    # Optional number id to assign to modality config
    _number_id: Optional[int] = PrivateAttr(default=None)
    modality: Modality = Field(
        ..., description="Data collection modality", title="Modality"
    )
    source: Path = Field(
        ...,
        description="Location of raw data to be uploaded",
        title="Data Source",
    )
    compress_raw_data: Optional[bool] = Field(
        default=None,
        description="Run compression on data",
        title="Compress Raw Data",
    )
    extra_configs: Optional[Path] = Field(
        default=None,
        description="Location of additional configuration file",
        title="Extra Configs",
    )
    skip_staging: bool = Field(
        default=False,
        description="Upload uncompressed directly without staging",
        title="Skip Staging",
    )

    @property
    def number_id(self):
        """Retrieve an optionally assigned numerical id"""
        return self._number_id

    @property
    def default_output_folder_name(self):
        """Construct the default folder name for the modality."""
        if self._number_id is None:
            return self.modality.name.lower()
        else:
            return self.modality.name.lower() + str(self._number_id)

    @validator("compress_raw_data", always=True)
    def get_compress_source_default(
        cls, compress_source: Optional[bool], values: Dict[str, Any]
    ) -> bool:
        """Set compress source default to True for ecephys data."""
        if (
            compress_source is None
            and "modality" in values
            and values["modality"] == Modality.ECEPHYS
        ):
            return True
        elif compress_source is not None:
            return compress_source
        else:
            return False


class BasicUploadJobConfigs(BaseSettings):
    """Configuration for the basic upload job"""

    _DATE_PATTERN1 = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    _DATE_PATTERN2 = re.compile(r"^\d{1,2}/\d{1,2}/\d{4}$")
    _TIME_PATTERN1 = re.compile(r"^\d{1,2}-\d{1,2}-\d{1,2}$")
    _TIME_PATTERN2 = re.compile(r"^\d{1,2}:\d{1,2}:\d{1,2}$")
    _MODALITY_ENTRY_PATTERN = re.compile(r"^modality(\d*)$")

    aws_param_store_name: str

    s3_bucket: str = Field(
        ...,
        description="Bucket where data will be uploaded",
        title="S3 Bucket",
    )
    experiment_type: ExperimentType = Field(
        ..., description="Experiment type", title="Experiment Type"
    )
    modalities: List[ModalityConfigs] = Field(
        ...,
        description="Data collection modalities and their directory location",
        title="Modalities",
        min_items=1,
    )
    subject_id: str = Field(..., description="Subject ID", title="Subject ID")
    acq_date: date = Field(
        ..., description="Date data was acquired", title="Acquisition Date"
    )
    acq_time: time = Field(
        ...,
        description="Time of day data was acquired",
        title="Acquisition Time",
    )
    process_name: ProcessName = Field(
        default=ProcessName.OTHER,
        description="Type of processing performed on the raw data source.",
        title="Process Name",
    )
    metadata_dir: Optional[Path] = Field(
        default=None,
        description="Directory of metadata",
        title="Metadata Directory",
    )
    # Deprecated. Will be removed in future versions.
    behavior_dir: Optional[Path] = Field(
        default=None,
        description=(
            "Directory of behavior data. This field is deprecated and will be "
            "removed in future versions. Instead, this will be included in "
            "the modalities list."
        ),
        title="Behavior Directory",
    )
    log_level: str = Field(
        default="WARNING",
        description="Logging level. Default is WARNING.",
        title="Log Level",
    )
    metadata_dir_force: bool = Field(
        default=False,
        description=(
            "Whether to override metadata from service with metadata in "
            "optional metadata directory"
        ),
        title="Metadata Directory Force",
    )
    dry_run: bool = Field(
        default=False,
        description="Perform a dry-run of data upload",
        title="Dry Run",
    )
    force_cloud_sync: bool = Field(
        default=False,
        description=(
            "Force syncing of data folder even if location exists in cloud"
        ),
        title="Force Cloud Sync",
    )
    temp_directory: Optional[Path] = Field(
        default=None,
        description=(
            "As default, the file systems temporary directory will be used as "
            "an intermediate location to store the compressed data before "
            "being uploaded to s3"
        ),
        title="Temp directory",
    )

    @property
    def s3_prefix(self):
        """Construct s3_prefix from configs."""
        return build_data_name(
            label=f"{self.experiment_type.value}_{self.subject_id}",
            creation_date=self.acq_date,
            creation_time=self.acq_time,
        )

    @validator("acq_date", pre=True)
    def _parse_date(cls, date_val: Any) -> date:
        """Parses date string to %YYYY-%MM-%DD format"""
        is_str = isinstance(date_val, str)
        if is_str and re.match(BasicUploadJobConfigs._DATE_PATTERN1, date_val):
            return date.fromisoformat(date_val)
        elif is_str and re.match(
            BasicUploadJobConfigs._DATE_PATTERN2, date_val
        ):
            return datetime.strptime(date_val, "%m/%d/%Y").date()
        elif is_str:
            raise ValueError(
                "Incorrect date format, should be YYYY-MM-DD or MM/DD/YYYY"
            )
        else:
            return date_val

    @validator("acq_time", pre=True)
    def _parse_time(cls, time_val: Any) -> time:
        """Parses time string to "%HH-%MM-%SS format"""
        is_str = isinstance(time_val, str)
        if is_str and re.match(BasicUploadJobConfigs._TIME_PATTERN1, time_val):
            return datetime.strptime(time_val, "%H-%M-%S").time()
        elif is_str and re.match(
            BasicUploadJobConfigs._TIME_PATTERN2, time_val
        ):
            return time.fromisoformat(time_val)
        elif is_str:
            raise ValueError(
                "Incorrect time format, should be HH-MM-SS or HH:MM:SS"
            )
        else:
            return time_val

    @staticmethod
    def _clean_csv_entry(csv_key: str, csv_value: Optional[str]) -> Any:
        """Tries to set the default value for optional settings if the csv
        entry is blank."""
        if (
            csv_value is None or csv_value == "" or csv_value == " "
        ) and BasicUploadJobConfigs.__fields__.get(csv_key) is not None:
            clean_val = BasicUploadJobConfigs.__fields__[csv_key].default
        else:
            clean_val = csv_value.strip()
        return clean_val

    @staticmethod
    def _map_row_and_key_to_modality_config(
        modality_key: str,
        cleaned_row: Dict[str, Any],
        modality_counts: Dict[str, Optional[int]],
    ) -> Optional[ModalityConfigs]:
        """
        Maps a cleaned csv row and a key for a modality to process into an
        ModalityConfigs object.
        Parameters
        ----------
        modality_key : str
          The column header like modality0, or modality1, etc.
        cleaned_row : Dict[str, Any]
          The csv row that's been cleaned.
        modality_counts : Dict[str, Optional[int]]
          If more than one type of modality is present in the csv row, then
          they will be assigned numerical ids. This will allow multiple of the
          same modalities to be stored under folders like ecephys0, etc.

        Returns
        -------
        Optional[ModalityConfigs]
          None if unable to parse csv row properly.

        """
        modality: str = cleaned_row[modality_key]
        source = cleaned_row.get(f"{modality_key}.source")
        extra_configs = cleaned_row.get(f"{modality_key}.extra_configs")

        # Return None if modality not in Modality list
        if modality is None or modality.strip() == "":
            return None

        modality_configs = ModalityConfigs(
            modality=modality, source=source, extra_configs=extra_configs
        )
        num_id = modality_counts.get(modality)
        modality_configs._number_id = num_id
        if num_id is None:
            modality_counts[modality] = 1
        else:
            modality_counts[modality] = num_id + 1
        return modality_configs

    @classmethod
    def _parse_modality_configs_from_row(cls, cleaned_row: dict) -> None:
        """
        Parses csv row into a list of ModalityConfigs. Will then process the
        cleaned_row dictionary by removing the old modality keys and replacing
        them with just modalities: List[ModalityConfigs.]
        Parameters
        ----------
        cleaned_row : dict
          csv row that contains keys like modality0, modality0.source,
          modality1, modality1.source, etc.

        Returns
        -------
        None
          Modifies cleaned_row dict in-place

        """
        modalities = []
        modality_keys = [
            m
            for m in cleaned_row.keys()
            if cls._MODALITY_ENTRY_PATTERN.match(m)
        ]
        modality_counts: Dict[str, Optional[int]] = dict()
        # Check uniqueness of keys
        if len(modality_keys) != len(set(modality_keys)):
            raise KeyError(
                f"Modality keys need to be unique in csv "
                f"header: {modality_keys}"
            )
        for modality_key in modality_keys:
            modality_configs = cls._map_row_and_key_to_modality_config(
                modality_key=modality_key,
                cleaned_row=cleaned_row,
                modality_counts=modality_counts,
            )
            if modality_configs is not None:
                modalities.append(modality_configs)

        # Del old modality keys and replace them with list of modality_configs
        for row_key in [
            m for m in cleaned_row.keys() if m.startswith("modality")
        ]:
            del cleaned_row[row_key]
        cleaned_row["modalities"] = modalities

    def preview_dict(self):
        """Maps model to a dictionary that will be rendered by jinja"""
        modalities = [
            {"name": m.modality.name, "source": m.source}
            for m in self.modalities
        ]
        return {
            "bucket": self.s3_bucket,
            "name": self.s3_prefix,
            "subject_id": self.subject_id,
            "experiment_type": self.experiment_type.value,
            "acq_date": self.acq_date,
            "acq_time": self.acq_time,
            "modalities": modalities,
        }

    @classmethod
    def from_csv_row(
        cls,
        row: dict,
        aws_param_store_name: str,
        temp_directory: Optional[str] = None,
    ):
        """
        Creates a job config object from a csv row.
        """
        cleaned_row = {
            k.strip().replace("-", "_"): cls._clean_csv_entry(
                k.strip().replace("-", "_"), v
            )
            for k, v in row.items()
        }
        cls._parse_modality_configs_from_row(cleaned_row=cleaned_row)
        return cls(
            **cleaned_row,
            aws_param_store_name=aws_param_store_name,
            temp_directory=temp_directory,
        )


class HpcJobConfigs(BaseSettings):
    """Class to contain settings for hpc resources"""

    hpc_nodes: int = Field(default=1, description="Number of tasks")
    hpc_time_limit: int = Field(default=360, description="Timeout in minutes")
    hpc_node_memory: int = Field(
        default=50, description="Memory requested in GB"
    )
    hpc_partition: str
    hpc_current_working_directory: Path
    hpc_logging_directory: Path
    hpc_aws_secret_access_key: SecretStr
    hpc_aws_access_key_id: str
    hpc_aws_default_region: str
    hpc_aws_session_token: Optional[str] = Field(default=None)
    hpc_sif_location: Path = Field(...)
    hpc_alt_exec_command: Optional[str] = Field(
        default=None,
        description=(
            "Set this value to run a different execution command then the "
            "default one built."
        ),
    )
    basic_upload_job_configs: BasicUploadJobConfigs

    def _json_args_str(self) -> str:
        """Serialize job configs to json"""
        return self.basic_upload_job_configs.json()

    def _script_command_str(self) -> str:
        """This is the command that will be sent to the hpc"""
        command_str = [
            "#!/bin/bash",
            "\nsingularity",
            "exec",
            "--cleanenv",
            str(self.hpc_sif_location),
            "python",
            "-m",
            "aind_data_transfer.jobs.basic_job",
            "--json-args",
            "'",
            self._json_args_str(),
            "'",
        ]

        return " ".join(command_str)

    def _job_name(self) -> str:
        """Construct a name for the job"""
        return self.basic_upload_job_configs.s3_prefix

    @property
    def job_definition(self) -> dict:
        """
        Convert job configs to a dictionary that can be sent to the slurm
        cluster via the rest api.
        Parameters
        ----------

        Returns
        -------
        dict

        """
        job_name = self._job_name()
        time_limit_str = "{:02d}:{:02d}:00".format(
            *divmod(self.hpc_time_limit, 60)
        )
        mem_str = f"{self.hpc_node_memory}gb"
        environment = {
            "PATH": "/bin:/usr/bin/:/usr/local/bin/",
            "LD_LIBRARY_PATH": "/lib/:/lib64/:/usr/local/lib",
            "SINGULARITYENV_AWS_SECRET_ACCESS_KEY": (
                self.hpc_aws_secret_access_key.get_secret_value()
            ),
            "SINGULARITYENV_AWS_ACCESS_KEY_ID": self.hpc_aws_access_key_id,
            "SINGULARITYENV_AWS_DEFAULT_REGION": self.hpc_aws_default_region,
        }
        if self.hpc_aws_session_token is not None:
            environment[
                "SINGULARITYENV_AWS_SESSION_TOKEN"
            ] = self.hpc_aws_session_token

        if self.hpc_alt_exec_command is not None:
            exec_script = self.hpc_alt_exec_command
        else:
            exec_script = self._script_command_str()

        log_std_out_path = self.hpc_logging_directory / (job_name + ".out")
        log_std_err_path = self.hpc_logging_directory / (
            job_name + "_error.out"
        )

        return {
            "job": {
                "name": job_name,
                "nodes": self.hpc_nodes,
                "time_limit": time_limit_str,
                "partition": self.hpc_partition,
                "current_working_directory": (
                    str(self.hpc_current_working_directory)
                ),
                "standard_output": str(log_std_out_path),
                "standard_error": str(log_std_err_path),
                "memory_per_node": mem_str,
                "environment": environment,
            },
            "script": exec_script,
        }
