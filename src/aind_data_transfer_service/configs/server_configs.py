"""Module for basic server configurations"""

from pathlib import Path
from typing import Optional

from pydantic import BaseSettings, Field, SecretStr


class ServerConfigs(BaseSettings):
    """Class for configs that can be stored as env vars on the server running
    this service."""

    hpc_username: str = Field(
        ..., description="User with permissions to run jobs on the hpc"
    )
    hpc_password: SecretStr = Field(
        ...,
        description=(
            "Password for the user with permissions to run jobs on the hpc"
        ),
    )
    hpc_token: SecretStr = Field(
        ...,
        description=(
            "JSON web token for the hpc user that can run jobs via REST"
        ),
    )
    hpc_partition: str = Field(
        ..., description="Partition where jobs will be submitted to"
    )
    aws_access_key: str = Field(
        ...,
        description=(
            "AWS access key with permissions to retrieve secrets and upload "
            "data to buckets"
        ),
    )
    aws_secret_access_key: SecretStr = Field(
        ...,
        description=(
            "AWS secret access key with permissions to retrieve secrets and "
            "upload data to buckets"
        ),
    )
    aws_region: str = Field(
        ..., description="AWS region associated with the access credentials."
    )
    csrf_secret_key: SecretStr = Field(
        ..., description="CSRF secret to mitigate form forgeries"
    )
    app_secret_key: SecretStr = Field(
        ..., description="FastAPI middleware secret"
    )
    aws_endpoints_param_store_name: str = Field(
        ...,
        description=(
            "AWS parameter store name for common job endpoints (codeocean "
            "domain, metadata-service domain, etc.)"
        ),
    )
    aws_codeocean_token_secrets_name: str = Field(
        ..., description="AWS secrets name for the codeocean token."
    )
    aws_video_encryption_password_name: str = Field(
        ..., description="AWS secrets name for the video encryption password."
    )
    staging_directory: Optional[Path] = Field(
        None, description="Directory where to stage data before upload"
    )