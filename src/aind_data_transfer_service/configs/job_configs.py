"""This module adds classes to handle resolving common endpoints used in the
data transfer jobs."""
import json
import re
from datetime import date, datetime, time
from pathlib import Path
from typing import Any, Dict, List, Optional

import boto3
from aind_data_schema.data_description import (
    ExperimentType,
    Modality,
    build_data_name,
)
from aind_data_schema.processing import ProcessName
from pydantic import BaseSettings, Field, PrivateAttr, SecretStr, validator


class EndpointConfigs(BaseSettings):
    """Class for basic job endpoints. Can be pulled from aws param store."""

    codeocean_api_token: Optional[SecretStr] = Field(
        None, description="API token to run code ocean capsules"
    )
    video_encryption_password: Optional[SecretStr] = Field(
        None, description="Password to use when encrypting video files"
    )
    codeocean_domain: str = Field(..., description="Code Ocean domain name")
    codeocean_trigger_capsule_id: str = Field(
        ..., description="Capsule ID of Code Ocean trigger capsule"
    )
    codeocean_trigger_capsule_version: Optional[str] = Field(
        None, description="Version number of trigger capsule"
    )
    metadata_service_domain: str = Field(
        ..., description="Metadata service domain name"
    )
    aind_data_transfer_repo_location: str = Field(
        ..., description="Location of aind-data-transfer repository"
    )
    codeocean_process_capsule_id: Optional[str] = Field(
        None,
        description=(
            "If defined, will run this Code Ocean Capsule after registering "
            "the data asset"
        ),
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

    @staticmethod
    def get_secret(secret_name: str) -> dict:
        """
        Retrieves a secret from AWS Secrets Manager.

        param secret_name: The name of the secret to retrieve.
        """
        # Create a Secrets Manager client
        client = boto3.client("secretsmanager")
        try:
            response = client.get_secret_value(SecretId=secret_name)
        finally:
            client.close()
        return json.loads(response["SecretString"])

    @staticmethod
    def get_parameter(parameter_name: str, with_decryption=False) -> dict:
        """
        Retrieves a parameter from AWS Parameter Store.

        param parameter_name: The name of the parameter to retrieve.
        """
        # Create a Systems Manager client
        client = boto3.client("ssm")
        try:
            response = client.get_parameter(
                Name=parameter_name, WithDecryption=with_decryption
            )
        finally:
            client.close()
        return json.loads(response["Parameter"]["Value"])

    @classmethod
    def from_aws_params_and_secrets(
        cls,
        endpoints_param_store_name: str,
        codeocean_token_secrets_name: str,
        video_encryption_password_name: str,
        **kwargs,
    ):
        """
        Construct endpoints from env vars stored on the server
        Parameters
        ----------

        """
        params = cls.get_parameter(endpoints_param_store_name)
        codeocean_creds = cls.get_secret(codeocean_token_secrets_name)
        vid_encrypt_password = cls.get_secret(video_encryption_password_name)

        # update param dictionary with secrets
        params["codeocean_domain"] = codeocean_creds["domain"]
        params["codeocean_api_token"] = codeocean_creds["token"]
        params["video_encryption_password"] = vid_encrypt_password["password"]
        params.update(kwargs)

        return cls(**params)


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


class BasicUploadJobConfigs(EndpointConfigs):
    """Configuration for the basic upload job"""

    _DATE_PATTERN1 = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    _DATE_PATTERN2 = re.compile(r"^\d{1,2}/\d{1,2}/\d{4}$")
    _TIME_PATTERN1 = re.compile(r"^\d{1,2}-\d{1,2}-\d{1,2}$")
    _TIME_PATTERN2 = re.compile(r"^\d{1,2}:\d{1,2}:\d{1,2}$")
    _MODALITY_ENTRY_PATTERN = re.compile(r"^modality(\d*)$")

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

        # Return None if modality not in Modality list
        if modality not in list(Modality.__members__.keys()):
            return None

        modality_configs = ModalityConfigs(
            modality=modality,
            source=source,
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
    def from_csv_row(cls, row: dict, endpoints: Optional[EndpointConfigs]):
        """
        Creates a job config object from a csv row.
        Parameters
        ----------
        row : dict
          The row parsed from the csv file
        endpoints : Optional[EndpointConfigs]
          Optionally pass in an EndpointConfigs object
        """
        cleaned_row = {
            k.strip().replace("-", "_"): cls._clean_csv_entry(
                k.strip().replace("-", "_"), v
            )
            for k, v in row.items()
        }

        cls._parse_modality_configs_from_row(cleaned_row=cleaned_row)
        if endpoints is not None:
            cleaned_row.update(endpoints.dict())
        return cls(**cleaned_row)


class HpcJobConfigs(BasicUploadJobConfigs):
    """Class to contain settings for hpc resources"""

    hpc_n_tasks: int = Field(default=1, description="Number of tasks")
    hpc_timeout: int = Field(default=360, description="Timeout in minutes")
    hpc_node_memory: int = Field(
        default=50, description="Memory requested in GB"
    )
    hpc_partition: str = Field(
        ..., description="Partition to submit tasks to (also known as a queue)"
    )
