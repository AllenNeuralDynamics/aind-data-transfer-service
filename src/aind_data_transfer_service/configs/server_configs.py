import json
from pathlib import Path
from typing import Optional

import boto3
from pydantic import BaseSettings, Field, SecretStr


class ServerConfigs(BaseSettings):
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


class EndpointConfigs(BaseSettings):
    codeocean_api_token: Optional[SecretStr] = Field(None)
    video_encryption_password: Optional[SecretStr] = Field(None)

    codeocean_domain: str = Field(...)
    codeocean_trigger_capsule_id: str = Field(...)
    codeocean_trigger_capsule_version: Optional[str] = Field(None)
    metadata_service_domain: str = Field(...)
    aind_data_transfer_repo_location: str = Field(...)
    codeocean_process_capsule_id: Optional[str] = Field(
        None,
        description=(
            "If defined, will run this Code Ocean Capsule after registering "
            "the data asset"
        ),
    )
    staging_directory: Optional[Path] = Field(
        None, description="Directory where to stage data before uploading"
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
    def from_server_configs(cls, server_configs: ServerConfigs):
        params = cls.get_parameter(
            server_configs.aws_endpoints_param_store_name
        )
        codeocean_creds = cls.get_secret(
            server_configs.aws_codeocean_token_secrets_name
        )
        vid_encrypt_password = cls.get_secret(
            server_configs.aws_video_encryption_password_name
        )

        # update param dictionary with secrets
        params["codeocean_domain"] = codeocean_creds["domain"]
        params["codeocean_api_token"] = codeocean_creds["token"]
        params["video_encryption_password"] = vid_encrypt_password["password"]
        params["staging_directory"] = server_configs.staging_directory

        return cls(**params)
