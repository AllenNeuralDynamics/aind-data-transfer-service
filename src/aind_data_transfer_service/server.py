"""Starts and Runs Starlette Service"""

import csv
import io
import json
import os
import re
from asyncio import gather, sleep
from pathlib import PurePosixPath
from typing import List, Optional, Union

import boto3
import requests
from aind_data_transfer_models import (
    __version__ as aind_data_transfer_models_version,
)
from aind_data_transfer_models.core import SubmitJobRequest, validation_context
from authlib.integrations.starlette_client import OAuth
from botocore.exceptions import ClientError
from fastapi import Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from httpx import AsyncClient
from openpyxl import load_workbook
from pydantic import SecretStr, ValidationError
from starlette.applications import Starlette
from starlette.config import Config
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse
from starlette.routing import Route

from aind_data_transfer_service import OPEN_DATA_BUCKET_NAME
from aind_data_transfer_service import (
    __version__ as aind_data_transfer_service_version,
)
from aind_data_transfer_service.configs.csv_handler import map_csv_row_to_job
from aind_data_transfer_service.configs.job_configs import (
    BasicUploadJobConfigs as LegacyBasicUploadJobConfigs,
)
from aind_data_transfer_service.configs.job_configs import HpcJobConfigs
from aind_data_transfer_service.configs.job_upload_template import (
    JobUploadTemplate,
)
from aind_data_transfer_service.hpc.client import HpcClient, HpcClientConfigs
from aind_data_transfer_service.hpc.models import HpcJobSubmitSettings
from aind_data_transfer_service.log_handler import LoggingConfigs, get_logger
from aind_data_transfer_service.models.core import SubmitJobRequestV2
from aind_data_transfer_service.models.core import (
    validation_context as validation_context_v2,
)
from aind_data_transfer_service.models.internal import (
    AirflowDagRunsRequestParameters,
    AirflowDagRunsResponse,
    AirflowTaskInstanceLogsRequestParameters,
    AirflowTaskInstancesRequestParameters,
    AirflowTaskInstancesResponse,
    JobParamInfo,
    JobStatus,
    JobTasks,
)

template_directory = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "templates")
)
templates = Jinja2Templates(directory=template_directory)

# TODO: Add server configs model
# HPC_SIF_LOCATION
# HPC_USERNAME
# HPC_LOGGING_DIRECTORY
# HPC_AWS_ACCESS_KEY_ID
# HPC_AWS_SECRET_ACCESS_KEY
# HPC_AWS_SESSION_TOKEN
# HPC_AWS_DEFAULT_REGION
# HPC_STAGING_DIRECTORY
# HPC_AWS_PARAM_STORE_NAME
# BASIC_JOB_SCRIPT
# OPEN_DATA_AWS_SECRET_ACCESS_KEY
# OPEN_DATA_AWS_ACCESS_KEY_ID
# AIND_METADATA_SERVICE_PROJECT_NAMES_URL
# AIND_AIRFLOW_SERVICE_URL
# AIND_AIRFLOW_SERVICE_JOBS_URL
# AIND_AIRFLOW_SERVICE_PASSWORD
# AIND_AIRFLOW_SERVICE_USER
# LOKI_URI
# ENV_NAME
# LOG_LEVEL

logger = get_logger(log_configs=LoggingConfigs())
project_names_url = os.getenv("AIND_METADATA_SERVICE_PROJECT_NAMES_URL")


def get_project_names() -> List[str]:
    """Get a list of project_names"""
    # TODO: Cache response for 5 minutes
    response = requests.get(project_names_url)
    response.raise_for_status()
    project_names = response.json()["data"]
    return project_names


def set_oauth() -> OAuth:
    """Set up OAuth for the service"""
    secrets_client = boto3.client("secretsmanager")
    secret_response = secrets_client.get_secret_value(
        SecretId=os.getenv("AIND_SSO_SECRET_NAME")
    )
    secret_value = json.loads(secret_response["SecretString"])
    for secrets in secret_value:
        os.environ[secrets] = secret_value[secrets]
    config = Config()
    oauth = OAuth(config)
    oauth.register(
        name="azure",
        client_id=config("CLIENT_ID"),
        client_secret=config("CLIENT_SECRET"),
        server_metadata_url=config("AUTHORITY"),
        client_kwargs={"scope": "openid email profile"},
    )
    return oauth


def get_job_types(version: Optional[str] = None) -> List[str]:
    """Get a list of job_types"""
    params = get_parameter_infos(version)
    job_types = list(set([p.job_type for p in params]))
    return job_types


def get_parameter_infos(version: Optional[str] = None) -> List[JobParamInfo]:
    """Get a list of job_type parameters"""
    ssm_client = boto3.client("ssm")
    paginator = ssm_client.get_paginator("describe_parameters")
    params_iterator = paginator.paginate(
        ParameterFilters=[
            {
                "Key": "Path",
                "Option": "Recursive",
                "Values": [JobParamInfo.get_parameter_prefix(version)],
            }
        ]
    )
    params = []
    param_regex = JobParamInfo.get_parameter_regex(version)
    for page in params_iterator:
        for param in page["Parameters"]:
            if match := re.match(param_regex, param.get("Name")):
                param_info = JobParamInfo.from_aws_describe_parameter(
                    parameter=param,
                    job_type=match.group("job_type"),
                    task_id=match.group("task_id"),
                    modality=match.group("modality"),
                )
                params.append(param_info)
            else:
                logger.info(f"Ignoring {param.get('Name')}")
    return params


def get_parameter_value(param_name: str) -> dict:
    """Get a parameter value from AWS param store based on paramater name"""
    ssm_client = boto3.client("ssm")
    param_response = ssm_client.get_parameter(
        Name=param_name, WithDecryption=True
    )
    param_value = json.loads(param_response["Parameter"]["Value"])
    return param_value


async def get_airflow_jobs(
    params: AirflowDagRunsRequestParameters, get_confs: bool = False
) -> tuple[int, Union[List[JobStatus], List[dict]]]:
    """Get Airflow jobs using input query params. If get_confs is true,
    only the job conf dictionaries are returned."""

    async def fetch_jobs(
        client: AsyncClient, url: str, request_body: dict
    ) -> tuple[int, Union[List[JobStatus], List[dict]]]:
        """Helper method to fetch jobs using httpx async client"""
        response = await client.post(url, json=request_body)
        response.raise_for_status()
        response_jobs = response.json()
        dag_runs = AirflowDagRunsResponse.model_validate_json(
            json.dumps(response_jobs)
        )
        if get_confs:
            jobs_list = [d.conf for d in dag_runs.dag_runs if d.conf]
        else:
            jobs_list = [
                JobStatus.from_airflow_dag_run(d) for d in dag_runs.dag_runs
            ]
        total_entries = dag_runs.total_entries
        return (total_entries, jobs_list)

    airflow_url = os.getenv("AIND_AIRFLOW_SERVICE_JOBS_URL", "").strip("/")
    airflow_url = f"{airflow_url}/~/dagRuns/list"
    params_dict = json.loads(params.model_dump_json(exclude_none=True))
    # Send request to Airflow to ListDagRuns
    async with AsyncClient(
        auth=(
            os.getenv("AIND_AIRFLOW_SERVICE_USER"),
            os.getenv("AIND_AIRFLOW_SERVICE_PASSWORD"),
        )
    ) as async_client:
        # Fetch initial jobs
        (total_entries, jobs_list) = await fetch_jobs(
            client=async_client,
            url=airflow_url,
            request_body=params_dict,
        )
        # Fetch remaining jobs concurrently
        tasks = list()
        offset = params_dict["page_offset"] + params_dict["page_limit"]
        while offset < total_entries:
            batch_params = {**params_dict, "page_offset": offset}
            tasks.append(
                fetch_jobs(
                    client=async_client,
                    url=airflow_url,
                    request_body=batch_params,
                )
            )
            offset += params_dict["page_limit"]
        batches = await gather(*tasks)
        for _, jobs_batch in batches:
            jobs_list.extend(jobs_batch)
    return (total_entries, jobs_list)


async def validate_csv(request: Request):
    """Validate a csv or xlsx file. Return parsed contents as json."""
    logger.info("Received request to validate csv")
    async with request.form() as form:
        basic_jobs = []
        errors = []
        if not form["file"].filename.endswith((".csv", ".xlsx")):
            errors.append("Invalid input file type")
        else:
            content = await form["file"].read()
            if form["file"].filename.endswith(".csv"):
                # A few csv files created from excel have extra unicode
                # byte chars. Adding "utf-8-sig" should remove them.
                data = content.decode("utf-8-sig")
            else:
                xlsx_book = load_workbook(io.BytesIO(content), read_only=True)
                xlsx_sheet = xlsx_book.active
                csv_io = io.StringIO()
                csv_writer = csv.writer(csv_io)
                for r in xlsx_sheet.iter_rows(values_only=True):
                    if any(r):
                        csv_writer.writerow(r)
                xlsx_book.close()
                data = csv_io.getvalue()
            csv_reader = csv.DictReader(io.StringIO(data))
            params = AirflowDagRunsRequestParameters(
                dag_ids=["transform_and_upload_v2", "run_list_of_jobs"],
                states=["running", "queued"],
            )
            _, current_jobs = await get_airflow_jobs(
                params=params, get_confs=True
            )
            context = {
                "job_types": get_job_types("v2"),
                "project_names": get_project_names(),
                "current_jobs": current_jobs,
            }
            for row in csv_reader:
                if not any(row.values()):
                    continue
                try:
                    with validation_context_v2(context):
                        job = map_csv_row_to_job(row=row)
                    # Construct hpc job setting most of the vars from the env
                    basic_jobs.append(
                        json.loads(
                            job.model_dump_json(
                                round_trip=True,
                                exclude_none=True,
                                warnings=False,
                            )
                        )
                    )
                except ValidationError as e:
                    errors.append(e.json())
                except Exception as e:
                    errors.append(f"{str(e.args)}")
        message = "There were errors" if len(errors) > 0 else "Valid Data"
        status_code = 406 if len(errors) > 0 else 200
        content = {
            "message": message,
            "data": {"jobs": basic_jobs, "errors": errors},
        }
        return JSONResponse(
            content=content,
            status_code=status_code,
        )


# TODO: Deprecate this endpoint
async def validate_csv_legacy(request: Request):
    """Validate a csv or xlsx file. Return parsed contents as json."""
    async with request.form() as form:
        basic_jobs = []
        errors = []
        if not form["file"].filename.endswith((".csv", ".xlsx")):
            errors.append("Invalid input file type")
        else:
            content = await form["file"].read()
            if form["file"].filename.endswith(".csv"):
                # A few csv files created from excel have extra unicode
                # byte chars. Adding "utf-8-sig" should remove them.
                data = content.decode("utf-8-sig")
            else:
                xlsx_book = load_workbook(io.BytesIO(content), read_only=True)
                xlsx_sheet = xlsx_book.active
                csv_io = io.StringIO()
                csv_writer = csv.writer(csv_io)
                for r in xlsx_sheet.iter_rows(values_only=True):
                    if any(r):
                        csv_writer.writerow(r)
                xlsx_book.close()
                data = csv_io.getvalue()
            csv_reader = csv.DictReader(io.StringIO(data))
            for row in csv_reader:
                if not any(row.values()):
                    continue
                try:
                    job = LegacyBasicUploadJobConfigs.from_csv_row(row=row)
                    # Construct hpc job setting most of the vars from the env
                    basic_jobs.append(job.model_dump_json())
                except Exception as e:
                    errors.append(f"{e.__class__.__name__}{e.args}")
        message = "There were errors" if len(errors) > 0 else "Valid Data"
        status_code = 406 if len(errors) > 0 else 200
        content = {
            "message": message,
            "data": {"jobs": basic_jobs, "errors": errors},
        }
        return JSONResponse(
            content=content,
            status_code=status_code,
        )


async def validate_json_v2(request: Request):
    """Validate raw json against data transfer models. Returns validated
    json or errors if request is invalid."""
    logger.info("Received request to validate json v2")
    content = await request.json()
    try:
        params = AirflowDagRunsRequestParameters(
            dag_ids=["transform_and_upload_v2", "run_list_of_jobs"],
            states=["running", "queued"],
        )
        _, current_jobs = await get_airflow_jobs(params=params, get_confs=True)
        context = {
            "job_types": get_job_types("v2"),
            "project_names": get_project_names(),
            "current_jobs": current_jobs,
        }
        with validation_context_v2(context):
            validated_model = SubmitJobRequestV2.model_validate_json(
                json.dumps(content)
            )
        validated_content = json.loads(
            validated_model.model_dump_json(warnings=False, exclude_none=True)
        )
        logger.info("Valid model detected")
        return JSONResponse(
            status_code=200,
            content={
                "message": "Valid model",
                "data": {
                    "version": aind_data_transfer_service_version,
                    "model_json": content,
                    "validated_model_json": validated_content,
                },
            },
        )
    except ValidationError as e:
        logger.warning(f"There were validation errors processing {content}")
        return JSONResponse(
            status_code=406,
            content={
                "message": "There were validation errors",
                "data": {
                    "version": aind_data_transfer_service_version,
                    "model_json": content,
                    "errors": e.json(),
                },
            },
        )
    except Exception as e:
        logger.exception("Internal Server Error.")
        return JSONResponse(
            status_code=500,
            content={
                "message": "There was an internal server error",
                "data": {
                    "version": aind_data_transfer_service_version,
                    "model_json": content,
                    "errors": str(e.args),
                },
            },
        )


async def validate_json(request: Request):
    """Validate raw json against aind-data-transfer-models. Returns validated
    json or errors if request is invalid."""
    logger.info("Received request to validate json")
    content = await request.json()
    try:
        project_names = get_project_names()
        with validation_context({"project_names": project_names}):
            validated_model = SubmitJobRequest.model_validate_json(
                json.dumps(content)
            )
        validated_content = json.loads(
            validated_model.model_dump_json(warnings=False, exclude_none=True)
        )
        logger.info("Valid model detected")
        return JSONResponse(
            status_code=200,
            content={
                "message": "Valid model",
                "data": {
                    "version": aind_data_transfer_models_version,
                    "model_json": content,
                    "validated_model_json": validated_content,
                },
            },
        )
    except ValidationError as e:
        logger.warning(f"There were validation errors processing {content}")
        return JSONResponse(
            status_code=406,
            content={
                "message": "There were validation errors",
                "data": {
                    "version": aind_data_transfer_models_version,
                    "model_json": content,
                    "errors": e.json(),
                },
            },
        )
    except Exception as e:
        logger.exception("Internal Server Error.")
        return JSONResponse(
            status_code=500,
            content={
                "message": "There was an internal server error",
                "data": {
                    "version": aind_data_transfer_models_version,
                    "model_json": content,
                    "errors": str(e.args),
                },
            },
        )


async def submit_jobs_v2(request: Request):
    """Post SubmitJobRequestV2 raw json to hpc server to process."""
    logger.info("Received request to submit jobs v2")
    content = await request.json()
    try:
        params = AirflowDagRunsRequestParameters(
            dag_ids=["transform_and_upload_v2", "run_list_of_jobs"],
            states=["running", "queued"],
        )
        _, current_jobs = await get_airflow_jobs(params=params, get_confs=True)
        context = {
            "job_types": get_job_types("v2"),
            "project_names": get_project_names(),
            "current_jobs": current_jobs,
        }
        with validation_context_v2(context):
            model = SubmitJobRequestV2.model_validate_json(json.dumps(content))
        full_content = json.loads(
            model.model_dump_json(warnings=False, exclude_none=True)
        )
        # TODO: Replace with httpx async client
        logger.info(
            f"Valid request detected. Sending list of jobs. "
            f"dag_id: {model.dag_id}"
        )
        total_jobs = len(model.upload_jobs)
        for job_index, job in enumerate(model.upload_jobs, 1):
            logger.info(
                f"{job.job_type}, {job.s3_prefix} sending to airflow. "
                f"{job_index} of {total_jobs}."
            )

        response = requests.post(
            url=os.getenv("AIND_AIRFLOW_SERVICE_URL"),
            auth=(
                os.getenv("AIND_AIRFLOW_SERVICE_USER"),
                os.getenv("AIND_AIRFLOW_SERVICE_PASSWORD"),
            ),
            json={"conf": full_content},
        )
        return JSONResponse(
            status_code=response.status_code,
            content={
                "message": "Submitted request to airflow",
                "data": {"responses": [response.json()], "errors": []},
            },
        )
    except ValidationError as e:
        logger.warning(f"There were validation errors processing {content}")
        return JSONResponse(
            status_code=406,
            content={
                "message": "There were validation errors",
                "data": {"responses": [], "errors": e.json()},
            },
        )
    except Exception as e:
        logger.exception("Internal Server Error.")
        return JSONResponse(
            status_code=500,
            content={
                "message": "There was an internal server error",
                "data": {"responses": [], "errors": str(e.args)},
            },
        )


async def submit_jobs(request: Request):
    """Post BasicJobConfigs raw json to hpc server to process."""
    logger.info("Received request to submit jobs")
    content = await request.json()
    try:
        project_names = get_project_names()
        with validation_context({"project_names": project_names}):
            model = SubmitJobRequest.model_validate_json(json.dumps(content))
        full_content = json.loads(
            model.model_dump_json(warnings=False, exclude_none=True)
        )
        # TODO: Replace with httpx async client
        logger.info(
            f"Valid request detected. Sending list of jobs. "
            f"Job Type: {model.job_type}"
        )
        total_jobs = len(model.upload_jobs)
        for job_index, job in enumerate(model.upload_jobs, 1):
            logger.info(
                f"{job.s3_prefix} sending to airflow. "
                f"{job_index} of {total_jobs}."
            )

        response = requests.post(
            url=os.getenv("AIND_AIRFLOW_SERVICE_URL"),
            auth=(
                os.getenv("AIND_AIRFLOW_SERVICE_USER"),
                os.getenv("AIND_AIRFLOW_SERVICE_PASSWORD"),
            ),
            json={"conf": full_content},
        )
        return JSONResponse(
            status_code=response.status_code,
            content={
                "message": "Submitted request to airflow",
                "data": {"responses": [response.json()], "errors": []},
            },
        )

    except ValidationError as e:
        logger.warning(f"There were validation errors processing {content}")
        return JSONResponse(
            status_code=406,
            content={
                "message": "There were validation errors",
                "data": {"responses": [], "errors": e.json()},
            },
        )
    except Exception as e:
        logger.exception("Internal Server Error.")
        return JSONResponse(
            status_code=500,
            content={
                "message": "There was an internal server error",
                "data": {"responses": [], "errors": str(e.args)},
            },
        )


# TODO: Deprecate this endpoint
async def submit_basic_jobs(request: Request):
    """Post BasicJobConfigs raw json to hpc server to process."""
    content = await request.json()
    hpc_client_conf = HpcClientConfigs()
    hpc_client = HpcClient(configs=hpc_client_conf)
    basic_jobs = content["jobs"]
    hpc_jobs = []
    parsing_errors = []
    for job in basic_jobs:
        try:
            basic_upload_job = LegacyBasicUploadJobConfigs.model_validate_json(
                job
            )
            # Add aws_param_store_name and temp_dir
            basic_upload_job.aws_param_store_name = os.getenv(
                "HPC_AWS_PARAM_STORE_NAME"
            )
            basic_upload_job.temp_directory = os.getenv(
                "HPC_STAGING_DIRECTORY"
            )
            hpc_job = HpcJobConfigs(basic_upload_job_configs=basic_upload_job)
            hpc_jobs.append(hpc_job)
        except Exception as e:
            parsing_errors.append(
                f"Error parsing {job}: {e.__class__.__name__}"
            )
    if parsing_errors:
        status_code = 406
        message = "There were errors parsing the basic job configs"
        content = {
            "message": message,
            "data": {"responses": [], "errors": parsing_errors},
        }
    else:
        responses = []
        hpc_errors = []
        for hpc_job in hpc_jobs:
            try:
                job_def = hpc_job.job_definition
                response = hpc_client.submit_job(job_def)
                response_json = response.json()
                responses.append(response_json)
                # Add pause to stagger job requests to the hpc
                await sleep(0.2)
            except Exception as e:
                logger.error(f"{e.__class__.__name__}{e.args}")
                hpc_errors.append(
                    f"Error processing "
                    f"{hpc_job.basic_upload_job_configs.s3_prefix}"
                )
        message = (
            "There were errors submitting jobs to the hpc."
            if len(hpc_errors) > 0
            else "Submitted Jobs."
        )
        status_code = 500 if len(hpc_errors) > 0 else 200
        content = {
            "message": message,
            "data": {"responses": responses, "errors": hpc_errors},
        }
    return JSONResponse(
        content=content,
        status_code=status_code,
    )


# TODO: Deprecate this endpoint
async def submit_hpc_jobs(request: Request):  # noqa: C901
    """Post HpcJobSubmitSettings to hpc server to process."""

    content = await request.json()
    # content should have
    # {
    #   "jobs": [{"hpc_settings": str, upload_job_settings: str, script: str}]
    # }
    hpc_client_conf = HpcClientConfigs()
    hpc_client = HpcClient(configs=hpc_client_conf)
    job_configs = content["jobs"]
    hpc_jobs = []
    parsing_errors = []
    for job in job_configs:
        try:
            base_script = job.get("script")
            # If script is empty, assume that the job type is a basic job
            basic_job_name = None
            if base_script is None or base_script == "":
                base_script = HpcJobSubmitSettings.script_command_str(
                    sif_loc_str=os.getenv("HPC_SIF_LOCATION")
                )
                basic_job_name = (
                    LegacyBasicUploadJobConfigs.model_validate_json(
                        job["upload_job_settings"]
                    ).s3_prefix
                )
            upload_job_configs = json.loads(job["upload_job_settings"])
            # This will set the bucket to the private data one
            if upload_job_configs.get("s3_bucket") is not None:
                upload_job_configs = json.loads(
                    LegacyBasicUploadJobConfigs.model_validate(
                        upload_job_configs
                    ).model_dump_json()
                )
            # The aws creds to use are different for aind-open-data and
            # everything else
            if upload_job_configs.get("s3_bucket") == OPEN_DATA_BUCKET_NAME:
                aws_secret_access_key = SecretStr(
                    os.getenv("OPEN_DATA_AWS_SECRET_ACCESS_KEY")
                )
                aws_access_key_id = os.getenv("OPEN_DATA_AWS_ACCESS_KEY_ID")
            else:
                aws_secret_access_key = SecretStr(
                    os.getenv("HPC_AWS_SECRET_ACCESS_KEY")
                )
                aws_access_key_id = os.getenv("HPC_AWS_ACCESS_KEY_ID")
            hpc_settings = json.loads(job["hpc_settings"])
            if basic_job_name is not None:
                hpc_settings["name"] = basic_job_name
            hpc_job = HpcJobSubmitSettings.from_upload_job_configs(
                logging_directory=PurePosixPath(
                    os.getenv("HPC_LOGGING_DIRECTORY")
                ),
                aws_secret_access_key=aws_secret_access_key,
                aws_access_key_id=aws_access_key_id,
                aws_default_region=os.getenv("HPC_AWS_DEFAULT_REGION"),
                aws_session_token=(
                    (
                        None
                        if os.getenv("HPC_AWS_SESSION_TOKEN") is None
                        else SecretStr(os.getenv("HPC_AWS_SESSION_TOKEN"))
                    )
                ),
                **hpc_settings,
            )
            if not upload_job_configs:
                script = base_script
            else:
                script = hpc_job.attach_configs_to_script(
                    script=base_script,
                    base_configs=upload_job_configs,
                    upload_configs_aws_param_store_name=os.getenv(
                        "HPC_AWS_PARAM_STORE_NAME"
                    ),
                    staging_directory=os.getenv("HPC_STAGING_DIRECTORY"),
                )
            hpc_jobs.append((hpc_job, script))
        except Exception as e:
            parsing_errors.append(
                f"Error parsing {job['upload_job_settings']}: {repr(e)}"
            )
    if parsing_errors:
        status_code = 406
        message = "There were errors parsing the job configs"
        content = {
            "message": message,
            "data": {"responses": [], "errors": parsing_errors},
        }
    else:
        responses = []
        hpc_errors = []
        for hpc_job in hpc_jobs:
            hpc_job_def = hpc_job[0]
            try:
                script = hpc_job[1]
                response = hpc_client.submit_hpc_job(
                    job=hpc_job_def, script=script
                )
                response_json = response.json()
                responses.append(response_json)
                # Add pause to stagger job requests to the hpc
                await sleep(0.2)
            except Exception as e:
                logger.error(repr(e))
                hpc_errors.append(f"Error processing " f"{hpc_job_def.name}")
        message = (
            "There were errors submitting jobs to the hpc."
            if len(hpc_errors) > 0
            else "Submitted Jobs."
        )
        status_code = 500 if len(hpc_errors) > 0 else 200
        content = {
            "message": message,
            "data": {"responses": responses, "errors": hpc_errors},
        }
    return JSONResponse(
        content=content,
        status_code=status_code,
    )


async def get_job_status_list(request: Request):
    """Get status of jobs using input query params."""

    try:
        params = AirflowDagRunsRequestParameters.from_query_params(
            request.query_params
        )
        params_dict = json.loads(params.model_dump_json(exclude_none=True))
        total_entries, job_status_list = await get_airflow_jobs(params=params)
        status_code = 200
        message = "Retrieved job status list from airflow"
        data = {
            "params": params_dict,
            "total_entries": total_entries,
            "job_status_list": [
                json.loads(j.model_dump_json()) for j in job_status_list
            ],
        }
    except ValidationError as e:
        logger.warning(
            f"There was a validation error process job_status list: {e}"
        )
        status_code = 406
        message = "Error validating request parameters"
        data = {"errors": json.loads(e.json())}
    except Exception as e:
        logger.exception("Unable to retrieve job status list from airflow")
        status_code = 500
        message = "Unable to retrieve job status list from airflow"
        data = {"errors": [f"{e.__class__.__name__}{e.args}"]}
    return JSONResponse(
        status_code=status_code,
        content={
            "message": message,
            "data": data,
        },
    )


async def get_tasks_list(request: Request):
    """Get list of tasks instances given dag id and job id."""
    try:
        url = os.getenv("AIND_AIRFLOW_SERVICE_JOBS_URL", "").strip("/")
        params = AirflowTaskInstancesRequestParameters.from_query_params(
            request.query_params
        )
        params_dict = json.loads(params.model_dump_json())
        response_tasks = requests.get(
            url=(
                f"{url}/{params.dag_id}/dagRuns/{params.dag_run_id}/"
                "taskInstances"
            ),
            auth=(
                os.getenv("AIND_AIRFLOW_SERVICE_USER"),
                os.getenv("AIND_AIRFLOW_SERVICE_PASSWORD"),
            ),
        )
        status_code = response_tasks.status_code
        if response_tasks.status_code == 200:
            task_instances = AirflowTaskInstancesResponse.model_validate_json(
                json.dumps(response_tasks.json())
            )
            job_tasks_list = sorted(
                [
                    JobTasks.from_airflow_task_instance(t)
                    for t in task_instances.task_instances
                ],
                key=lambda t: (-t.priority_weight, t.map_index),
            )
            message = "Retrieved job tasks list from airflow"
            data = {
                "params": params_dict,
                "total_entries": task_instances.total_entries,
                "job_tasks_list": [
                    json.loads(t.model_dump_json()) for t in job_tasks_list
                ],
            }
        else:
            message = "Error retrieving job tasks list from airflow"
            data = {
                "params": params_dict,
                "errors": [response_tasks.json()],
            }
    except ValidationError as e:
        logger.warning(f"There was a validation error process task_list: {e}")
        status_code = 406
        message = "Error validating request parameters"
        data = {"errors": json.loads(e.json())}
    except Exception as e:
        logger.exception("Unable to retrieve job tasks list from airflow")
        status_code = 500
        message = "Unable to retrieve job tasks list from airflow"
        data = {"errors": [f"{e.__class__.__name__}{e.args}"]}
    return JSONResponse(
        status_code=status_code,
        content={
            "message": message,
            "data": data,
        },
    )


async def get_task_logs(request: Request):
    """Get task logs given dag id, job id, task id, and task try number."""
    try:
        url = os.getenv("AIND_AIRFLOW_SERVICE_JOBS_URL", "").strip("/")
        params = AirflowTaskInstanceLogsRequestParameters.from_query_params(
            request.query_params
        )
        params_dict = json.loads(params.model_dump_json())
        params_full = dict(params)
        response_logs = requests.get(
            url=(
                f"{url}/{params.dag_id}/dagRuns/{params.dag_run_id}"
                f"/taskInstances/{params.task_id}/logs/{params.try_number}"
            ),
            auth=(
                os.getenv("AIND_AIRFLOW_SERVICE_USER"),
                os.getenv("AIND_AIRFLOW_SERVICE_PASSWORD"),
            ),
            params=params_dict,
        )
        status_code = response_logs.status_code
        if response_logs.status_code == 200:
            message = "Retrieved task logs from airflow"
            data = {"params": params_full, "logs": response_logs.text}
        else:
            message = "Error retrieving task logs from airflow"
            data = {
                "params": params_full,
                "errors": [response_logs.json()],
            }
    except ValidationError as e:
        logger.warning(f"Error validating request parameters: {e}")
        status_code = 406
        message = "Error validating request parameters"
        data = {"errors": json.loads(e.json())}
    except Exception as e:
        logger.exception("Unable to retrieve job task_list from airflow")
        status_code = 500
        message = "Unable to retrieve task logs from airflow"
        data = {"errors": [f"{e.__class__.__name__}{e.args}"]}
    return JSONResponse(
        status_code=status_code,
        content={
            "message": message,
            "data": data,
        },
    )


async def index(request: Request):
    """GET|POST /: form handler"""
    return templates.TemplateResponse(
        name="index.html",
        context=(
            {
                "request": request,
                "project_names_url": project_names_url,
            }
        ),
    )


async def job_tasks_table(request: Request):
    """Get Job Tasks table given a job id"""
    response_tasks = await get_tasks_list(request)
    response_tasks_json = json.loads(response_tasks.body)
    data = response_tasks_json.get("data")
    return templates.TemplateResponse(
        name="job_tasks_table.html",
        context=(
            {
                "request": request,
                "status_code": response_tasks.status_code,
                "message": response_tasks_json.get("message"),
                "errors": data.get("errors", []),
                "total_entries": data.get("total_entries", 0),
                "job_tasks_list": data.get("job_tasks_list", []),
            }
        ),
    )


async def task_logs(request: Request):
    """Get task logs given a job id, task id, and task try number."""
    response_tasks = await get_task_logs(request)
    response_tasks_json = json.loads(response_tasks.body)
    data = response_tasks_json.get("data")
    return templates.TemplateResponse(
        name="task_logs.html",
        context=(
            {
                "request": request,
                "status_code": response_tasks.status_code,
                "message": response_tasks_json.get("message"),
                "errors": data.get("errors", []),
                "logs": data.get("logs"),
            }
        ),
    )


async def jobs(request: Request):
    """Get Job Status page with pagination"""
    dag_ids = AirflowDagRunsRequestParameters.model_fields["dag_ids"].default
    return templates.TemplateResponse(
        name="job_status.html",
        context=(
            {
                "request": request,
                "project_names_url": project_names_url,
                "dag_ids": dag_ids,
            }
        ),
    )


async def job_params(request: Request):
    """Get Job Parameters page"""
    return templates.TemplateResponse(
        name="job_params.html",
        context=(
            {
                "request": request,
                "project_names_url": os.getenv(
                    "AIND_METADATA_SERVICE_PROJECT_NAMES_URL"
                ),
                "versions": ["v1", "v2"],
                "default_version": "v1",
            }
        ),
    )


async def download_job_template(_: Request):
    """Get job template as xlsx filestream for download"""

    try:
        xl_io = JobUploadTemplate.create_excel_sheet_filestream()
        return StreamingResponse(
            io.BytesIO(xl_io.getvalue()),
            media_type=(
                "application/"
                "vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
            headers={
                "Content-Disposition": (
                    f"attachment; filename={JobUploadTemplate.FILE_NAME}"
                )
            },
            status_code=200,
        )
    except Exception as e:
        logger.exception("Error creating job template")
        return JSONResponse(
            content={
                "message": "Error creating job template",
                "data": {"error": f"{e.__class__.__name__}{e.args}"},
            },
            status_code=500,
        )


def list_parameters_v2(_: Request):
    """List v2 job type parameters"""
    params = get_parameter_infos("v2")
    return JSONResponse(
        content={
            "message": "Retrieved job parameters",
            "data": [p.model_dump(mode="json") for p in params],
        },
        status_code=200,
    )


def list_parameters(_: Request):
    """List v1 job type parameters"""
    params = get_parameter_infos()
    return JSONResponse(
        content={
            "message": "Retrieved job parameters",
            "data": [p.model_dump(mode="json") for p in params],
        },
        status_code=200,
    )


def get_parameter_v2(request: Request):
    """Get v2 parameter from AWS param store based on job_type and task_id"""
    # path params are auto validated
    job_type = request.path_params.get("job_type")
    task_id = request.path_params.get("task_id")
    param_name = JobParamInfo.get_parameter_name(job_type, task_id, "v2")
    try:
        param_value = get_parameter_value(param_name)
        return JSONResponse(
            content={
                "message": f"Retrieved parameter for {param_name}",
                "data": param_value,
            },
            status_code=200,
        )
    except ClientError as e:
        logger.exception(f"Error retrieving parameter {param_name}: {e}")
        return JSONResponse(
            content={
                "message": f"Error retrieving parameter {param_name}",
                "data": {"error": f"{e.__class__.__name__}{e.args}"},
            },
            status_code=500,
        )


def get_parameter(request: Request):
    """Get parameter from AWS parameter store based on job_type and task_id"""
    # path params are auto validated
    job_type = request.path_params.get("job_type")
    task_id = request.path_params.get("task_id")
    param_name = JobParamInfo.get_parameter_name(job_type, task_id)
    try:
        param_value = get_parameter_value(param_name)
        return JSONResponse(
            content={
                "message": f"Retrieved parameter for {param_name}",
                "data": param_value,
            },
            status_code=200,
        )
    except ClientError as e:
        logger.exception(f"Error retrieving parameter {param_name}: {e}")
        return JSONResponse(
            content={
                "message": f"Error retrieving parameter {param_name}",
                "data": {"error": f"{e.__class__.__name__}{e.args}"},
            },
            status_code=500,
        )


async def admin(request: Request):
    """Get admin page if authenticated, else redirect to login."""
    user = request.session.get("user")
    if os.getenv("ENV_NAME") == "local":
        user = {"name": "local user"}
    if user:
        return templates.TemplateResponse(
            name="admin.html",
            context=(
                {
                    "request": request,
                    "project_names_url": project_names_url,
                    "user_name": user.get("name", "unknown"),
                    "user_email": user.get("email", "unknown"),
                }
            ),
        )
    return RedirectResponse(url="/login")


async def login(request: Request):
    """Redirect to Azure login page"""
    oauth = set_oauth()
    redirect_uri = request.url_for("auth")
    response = await oauth.azure.authorize_redirect(request, redirect_uri)
    return response


async def logout(request: Request):
    """Logout user and clear session"""
    request.session.pop("user", None)
    return RedirectResponse(url="/")


async def auth(request: Request):
    """Authenticate user and store user info in session"""
    oauth = set_oauth()
    try:
        token = await oauth.azure.authorize_access_token(request)
        user = token.get("userinfo")
        if not user:
            raise ValueError("User info not found in access token.")
        request.session["user"] = dict(user)
    except Exception as error:
        return JSONResponse(
            content={
                "message": "Error Logging In",
                "data": {"error": f"{error.__class__.__name__}{error.args}"},
            },
            status_code=500,
        )
    return RedirectResponse(url="/admin")


routes = [
    Route("/", endpoint=index, methods=["GET", "POST"]),
    Route("/api/validate_csv", endpoint=validate_csv_legacy, methods=["POST"]),
    Route(
        "/api/submit_basic_jobs", endpoint=submit_basic_jobs, methods=["POST"]
    ),
    Route("/api/submit_hpc_jobs", endpoint=submit_hpc_jobs, methods=["POST"]),
    Route("/api/v1/validate_json", endpoint=validate_json, methods=["POST"]),
    Route("/api/v1/submit_jobs", endpoint=submit_jobs, methods=["POST"]),
    Route(
        "/api/v1/get_job_status_list",
        endpoint=get_job_status_list,
        methods=["GET"],
    ),
    Route("/api/v1/get_tasks_list", endpoint=get_tasks_list, methods=["GET"]),
    Route("/api/v1/get_task_logs", endpoint=get_task_logs, methods=["GET"]),
    Route("/api/v1/parameters", endpoint=list_parameters, methods=["GET"]),
    Route(
        "/api/v1/parameters/job_types/{job_type:str}/tasks/{task_id:path}",
        endpoint=get_parameter,
        methods=["GET"],
    ),
    Route("/api/v2/validate_csv", endpoint=validate_csv, methods=["POST"]),
    Route(
        "/api/v2/validate_json", endpoint=validate_json_v2, methods=["POST"]
    ),
    Route("/api/v2/submit_jobs", endpoint=submit_jobs_v2, methods=["POST"]),
    Route("/api/v2/parameters", endpoint=list_parameters_v2, methods=["GET"]),
    Route(
        "/api/v2/parameters/job_types/{job_type:str}/tasks/{task_id:path}",
        endpoint=get_parameter_v2,
        methods=["GET"],
    ),
    Route("/jobs", endpoint=jobs, methods=["GET"]),
    Route("/job_tasks_table", endpoint=job_tasks_table, methods=["GET"]),
    Route("/task_logs", endpoint=task_logs, methods=["GET"]),
    Route("/job_params", endpoint=job_params, methods=["GET"]),
    Route(
        "/api/job_upload_template",
        endpoint=download_job_template,
        methods=["GET"],
    ),
    Route("/login", login, methods=["GET"]),
    Route("/logout", logout, methods=["GET"]),
    Route("/auth", auth, methods=["GET"]),
    Route("/admin", admin, methods=["GET"]),
]

app = Starlette(routes=routes)
app.add_middleware(SessionMiddleware, secret_key=None)
