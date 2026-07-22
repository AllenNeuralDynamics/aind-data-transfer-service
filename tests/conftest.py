"""Set up fixtures to be used across all test modules."""

import json
import os
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, Generator
from unittest.mock import patch

import pytest
from aind_data_schema_models.modalities import Modality
from fastapi.testclient import TestClient

from aind_data_transfer_service.configs.platforms_v1 import Platform
from aind_data_transfer_service.models.core import Task, UploadJobConfigsV2

patch(
    "fastapi_cache.decorator.cache", lambda *args, **kwargs: lambda f: f
).start()

TEST_DIRECTORY = Path(os.path.dirname(os.path.realpath(__file__)))
RESOURCES_DIR = TEST_DIRECTORY / "resources"


@pytest.fixture()
def list_dag_runs_response() -> dict:
    """Raw response."""
    with open(RESOURCES_DIR / "airflow_dag_runs_response.json") as f:
        contents = json.load(f)
    return contents


@pytest.fixture()
def get_dag_run_response() -> dict:
    """Raw response."""
    with open(RESOURCES_DIR / "airflow_dag_run_response.json") as f:
        contents = json.load(f)
    return contents


@pytest.fixture()
def list_task_instances_response() -> dict:
    """Raw response."""
    with open(RESOURCES_DIR / "airflow_task_instances_response.json") as f:
        contents = json.load(f)
    return contents


@pytest.fixture()
def describe_parameters_response() -> dict:
    """Raw response."""
    with open(RESOURCES_DIR / "describe_parameters_response.json") as f:
        contents = json.load(f)
    return contents


@pytest.fixture()
def get_parameter_response() -> dict:
    """Raw response."""
    with open(RESOURCES_DIR / "get_parameter_response.json") as f:
        contents = json.load(f)
    return contents


@pytest.fixture()
def put_parameter_response() -> dict:
    """Raw response."""
    with open(RESOURCES_DIR / "put_parameter_response.json") as f:
        contents = json.load(f)
    return contents


@pytest.fixture()
def get_secrets_response() -> dict:
    """Raw response."""
    with open(RESOURCES_DIR / "get_secrets_response.json") as f:
        contents = json.load(f)
    return contents


@pytest.fixture()
def example_configs_v2() -> UploadJobConfigsV2:
    """Raw model."""
    job_type = "ecephys"
    project_name = "Ephys Platform"
    platform = Platform.ECEPHYS
    subject_id = "690165"
    acq_datetime = datetime(2024, 2, 19, 11, 25, 17)
    ephys_source_dir = PurePosixPath("shared_drive/ephys_data/690165")
    ephys_config = Task(
        job_settings={
            "modality": Modality.ECEPHYS.model_dump(mode="json"),
            "source": ephys_source_dir.as_posix(),
        }
    )
    example_configs_v2 = UploadJobConfigsV2(
        job_type=job_type,
        user_email="test@example.com",
        project_name=project_name,
        platform=platform,
        subject_id=subject_id,
        acq_datetime=acq_datetime,
        modalities=[Modality.ECEPHYS],
        tasks={"make_modality_list": ephys_config},
    )
    return example_configs_v2


@pytest.fixture(scope="session")
def client() -> Generator[TestClient, Any, None]:
    """Creating a client for testing purposes."""

    # Import moved to be able to mock cache
    from aind_data_transfer_service.server import app

    with TestClient(app) as c:
        yield c
