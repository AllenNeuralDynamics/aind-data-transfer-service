"""This module adds classes to handle resolving common endpoints used in the
data transfer jobs."""
import re
from datetime import datetime
from pathlib import PurePosixPath
from typing import Any, ClassVar, Dict, List, Optional, Union

from aind_data_schema.core.data_description import build_data_name
from aind_data_schema_models.modalities import Modality
from aind_data_schema_models.platforms import Platform
from aind_data_schema_models.process_names import ProcessName
from pydantic import (
    ConfigDict,
    Field,
    PrivateAttr,
    SecretStr,
    ValidationInfo,
    field_validator,
)
from pydantic_settings import BaseSettings

from aind_data_transfer_service import (
    OPEN_DATA_BUCKET_NAME,
    PRIVATE_BUCKET_NAME,
    SCRATCH_BUCKET_NAME,
)


class ModalityConfigs(BaseSettings):
    """Class to contain configs for each modality type"""

    # Need some way to extract abbreviations. Maybe a public method can be
    # added to the Modality class
    _MODALITY_MAP: ClassVar = {
        m().abbreviation.upper().replace("-", "_"): m().abbreviation
        for m in Modality.ALL
    }

    # Optional number id to assign to modality config
    _number_id: Optional[int] = PrivateAttr(default=None)
    modality: Modality.ONE_OF = Field(
        ..., description="Data collection modality", title="Modality"
    )
    source: PurePosixPath = Field(
        ...,
        description="Location of raw data to be uploaded",
        title="Data Source",
    )
    compress_raw_data: Optional[bool] = Field(
        default=None,
        description="Run compression on data",
        title="Compress Raw Data",
        validate_default=True,
    )
    extra_configs: Optional[PurePosixPath] = Field(
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
            return self.modality.abbreviation
        else:
            return self.modality.abbreviation + str(self._number_id)

    @field_validator("modality", mode="before")
    def parse_modality_string(
        cls, input_modality: Union[str, dict, Modality]
    ) -> Union[dict, Modality]:
        """Attempts to convert strings to a Modality model. Raises an error
        if unable to do so."""
        if isinstance(input_modality, str):
            modality_abbreviation = cls._MODALITY_MAP.get(
                input_modality.upper().replace("-", "_")
            )
            if modality_abbreviation is None:
                raise AttributeError(f"Unknown Modality: {input_modality}")
            return Modality.from_abbreviation(modality_abbreviation)
        else:
            return input_modality

    @field_validator("compress_raw_data", mode="after")
    def get_compress_source_default(
        cls, compress_source: Optional[bool], info: ValidationInfo
    ) -> bool:
        """Set compress source default to True for ecephys data."""
        if (
            compress_source is None
            and info.data.get("modality") == Modality.ECEPHYS
        ):
            return True
        elif compress_source is not None:
            return compress_source
        else:
            return False


class BasicUploadJobConfigs(BaseSettings):
    """Configuration for the basic upload job"""

    # Allow users to pass in extra fields
    model_config = ConfigDict(
        extra="allow",
    )

    # Legacy way required users to input platform in screaming snake case
    _PLATFORM_MAP: ClassVar = {
        a.upper().replace("-", "_"): a
        for a in Platform.abbreviation_map.keys()
    }
    _MODALITY_ENTRY_PATTERN: ClassVar = re.compile(r"^modality(\d*)$")
    _DATETIME_PATTERN1: ClassVar = re.compile(
        r"^\d{4}-\d{2}-\d{2}[ |T]\d{2}:\d{2}:\d{2}$"
    )
    _DATETIME_PATTERN2: ClassVar = re.compile(
        r"^\d{1,2}/\d{1,2}/\d{4} \d{1,2}:\d{2}:\d{2} [APap][Mm]$"
    )

    aws_param_store_name: Optional[str] = Field(None)

    project_name: str = Field(
        ..., description="Name of project", title="Project Name"
    )
    process_capsule_id: Optional[str] = Field(
        None,
        description="Use custom codeocean capsule or pipeline id",
        title="Process Capsule ID",
    )
    s3_bucket: Optional[str] = Field(
        None,
        description="Bucket where data will be uploaded",
        title="S3 Bucket",
        validate_default=True,
    )
    platform: Platform.ONE_OF = Field(
        ..., description="Platform", title="Platform"
    )
    modalities: List[ModalityConfigs] = Field(
        ...,
        description="Data collection modalities and their directory location",
        title="Modalities",
        min_items=1,
    )
    subject_id: str = Field(..., description="Subject ID", title="Subject ID")
    acq_datetime: datetime = Field(
        ...,
        description="Datetime data was acquired",
        title="Acquisition Datetime",
    )
    process_name: ProcessName = Field(
        default=ProcessName.OTHER,
        description="Type of processing performed on the raw data source.",
        title="Process Name",
    )
    metadata_dir: Optional[PurePosixPath] = Field(
        default=None,
        description="Directory of metadata",
        title="Metadata Directory",
    )
    # Deprecated. Will be removed in future versions.
    behavior_dir: Optional[PurePosixPath] = Field(
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
    temp_directory: Optional[PurePosixPath] = Field(
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
            label=f"{self.platform.abbreviation}_{self.subject_id}",
            creation_datetime=self.acq_datetime,
        )

    @field_validator("s3_bucket", mode="before")
    def map_bucket(cls, bucket: Optional[str]) -> Optional[str]:
        """We're adding a policy that data uploaded through the service can
        only land in a handful of buckets. As default, things will be
        stored in the private bucket"""
        if bucket is not None and bucket in [
            OPEN_DATA_BUCKET_NAME,
            SCRATCH_BUCKET_NAME,
        ]:
            return bucket
        else:
            return PRIVATE_BUCKET_NAME

    @field_validator("platform", mode="before")
    def parse_platform_string(
        cls, input_platform: Union[str, dict, Platform]
    ) -> Union[dict, Platform]:
        """Attempts to convert strings to a Platform model. Raises an error
        if unable to do so."""
        if isinstance(input_platform, str):
            platform_abbreviation = cls._PLATFORM_MAP.get(
                input_platform.upper()
            )
            if platform_abbreviation is None:
                raise AttributeError(f"Unknown Platform: {input_platform}")
            else:
                return Platform.from_abbreviation(platform_abbreviation)
        else:
            return input_platform

    @field_validator("acq_datetime", mode="before")
    def _parse_datetime(cls, datetime_val: Any) -> datetime:
        """Parses datetime string to %YYYY-%MM-%DD HH:mm:ss"""
        is_str = isinstance(datetime_val, str)
        if is_str and re.match(
            BasicUploadJobConfigs._DATETIME_PATTERN1, datetime_val
        ):
            return datetime.fromisoformat(datetime_val)
        elif is_str and re.match(
            BasicUploadJobConfigs._DATETIME_PATTERN2, datetime_val
        ):
            return datetime.strptime(datetime_val, "%m/%d/%Y %I:%M:%S %p")
        elif is_str:
            raise ValueError(
                "Incorrect datetime format, should be"
                " YYYY-MM-DD HH:mm:ss or MM/DD/YYYY I:MM:SS P"
            )
        else:
            return datetime_val

    @field_validator("modalities", mode="after")
    def update_number_ids(
        cls, modality_list: List[ModalityConfigs]
    ) -> List[ModalityConfigs]:
        """
        Loops through the modality list and assigns a number id
        to duplicate modalities. For example, if a user inputs
        multiple behavior modalities, then it will upload them
        as behavior, behavior1, behavior2, etc. folders.
        Parameters
        ----------
        modality_list : List[ModalityConfigs]

        Returns
        -------
        List[ModalityConfigs]
          Updates the _number_id field in the ModalityConfigs

        """
        modality_counts = {}
        updated_list = []
        for modality in modality_list:
            modality_abbreviation = modality.modality.abbreviation
            if modality_counts.get(modality_abbreviation) is None:
                modality_counts[modality_abbreviation] = 1
            else:
                modality_count_num = modality_counts[modality_abbreviation]
                modality._number_id = modality_count_num
                modality_counts[modality_abbreviation] += 1
            updated_list.append(modality)
        return updated_list

    @staticmethod
    def _clean_csv_entry(csv_key: str, csv_value: Optional[str]) -> Any:
        """Tries to set the default value for optional settings if the csv
        entry is blank."""
        if (
            csv_value is None or csv_value == "" or csv_value == " "
        ) and BasicUploadJobConfigs.model_fields.get(csv_key) is not None:
            clean_val = BasicUploadJobConfigs.model_fields[csv_key].default
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

    @classmethod
    def from_csv_row(
        cls,
        row: dict,
        aws_param_store_name: Optional[str] = None,
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


# Deprecating this class
class HpcJobConfigs(BaseSettings):
    """Class to contain settings for hpc resources"""

    hpc_nodes: int = Field(default=1, description="Number of tasks")
    hpc_time_limit: int = Field(default=360, description="Timeout in minutes")
    hpc_node_memory: int = Field(
        default=50, description="Memory requested in GB"
    )
    hpc_partition: str
    hpc_current_working_directory: PurePosixPath
    hpc_logging_directory: PurePosixPath
    hpc_aws_secret_access_key: SecretStr
    hpc_aws_access_key_id: str
    hpc_aws_default_region: str
    hpc_aws_session_token: Optional[str] = Field(default=None)
    hpc_sif_location: PurePosixPath = Field(...)
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
        return self.basic_upload_job_configs.model_dump_json()

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
