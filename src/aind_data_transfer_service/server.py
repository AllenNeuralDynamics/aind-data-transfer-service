"""Starts and Runs Starlette Service"""
import csv
import io
import logging
import os
from pathlib import Path

from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import SecretStr
from starlette.applications import Starlette
from starlette.routing import Route

from aind_data_transfer_service.configs.job_configs import (
    BasicUploadJobConfigs,
)
from aind_data_transfer_service.hpc.client import HpcClient, HpcClientConfigs
from aind_data_transfer_service.hpc.models import (
    HpcJobStatusResponse,
    HpcJobSubmitSettings,
    JobStatus,
)

template_directory = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "templates")
)
templates = Jinja2Templates(directory=template_directory)

# TODO: Add server configs model
# UPLOAD_TEMPLATE_LINK
# HPC_SIF_LOCATION
# HPC_LOGGING_DIRECTORY
# HPC_AWS_ACCESS_KEY_ID
# HPC_AWS_SECRET_ACCESS_KEY
# HPC_AWS_SESSION_TOKEN
# HPC_AWS_DEFAULT_REGION
# HPC_STAGING_DIRECTORY
# HPC_AWS_PARAM_STORE_NAME
# BASIC_JOB_SCRIPT


async def validate_csv(request: Request):
    """Validate a csv file. Return parsed contents as json."""
    async with request.form() as form:
        content = await form["file"].read()
        data = content.decode("utf-8")
        csv_reader = csv.DictReader(io.StringIO(data))
        basic_jobs = []
        errors = []
        for row in csv_reader:
            try:
                job = BasicUploadJobConfigs.from_csv_row(row=row)
                # Construct hpc job setting most of the vars from the env
                basic_jobs.append(job.json())
            except Exception as e:
                errors.append(repr(e))
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
            basic_upload_job = BasicUploadJobConfigs.parse_raw(job)
            # Add aws_param_store_name and temp_dir
            basic_upload_job.aws_param_store_name = os.getenv(
                "HPC_AWS_PARAM_STORE_NAME"
            )
            basic_upload_job.temp_directory = os.getenv(
                "HPC_STAGING_DIRECTORY"
            )
            hpc_job = HpcJobSubmitSettings.from_basic_job_configs(
                basic_upload_job_configs=basic_upload_job,
                logging_directory=Path(os.getenv("HPC_LOGGING_DIRECTORY")),
                aws_secret_access_key=SecretStr(
                    os.getenv("HPC_AWS_SECRET_ACCESS_KEY")
                ),
                aws_access_key_id=os.getenv("HPC_AWS_ACCESS_KEY_ID"),
                aws_default_region=os.getenv("HPC_AWS_DEFAULT_REGION"),
                aws_session_token=(
                    (
                        None
                        if os.getenv("HPC_AWS_SESSION_TOKEN") is None
                        else SecretStr(os.getenv("HPC_AWS_SESSION_TOKEN"))
                    )
                ),
            )
            hpc_jobs.append(hpc_job)
        except Exception as e:
            parsing_errors.append(f"Error parsing {job}: {e.__class__}")
    if parsing_errors:
        status_code = 406
        message = "There were errors parsing the basic job configs"
        content = {
            "message": message,
            "data": {"responses": [], "errors": parsing_errors},
        }
    else:
        hpc_error = None
        response_json = {}
        try:
            response = hpc_client.submit_job(
                script=HpcJobSubmitSettings.script_command_str(
                    os.getenv("HPC_SIF_LOCATION")
                ),
                jobs=hpc_jobs,
            )
            response_json = response.json()
        except Exception as e:
            logging.error(repr(e))
            hpc_error = repr(e)
        message = (
            "There were errors submitting jobs to the hpc."
            if hpc_error
            else "Submitted Jobs."
        )
        status_code = 500 if hpc_error else 200
        content = {
            "message": message,
            "data": {"response": response_json, "error": hpc_error},
        }
    return JSONResponse(
        content=content,
        status_code=status_code,
    )


async def index(request: Request):
    """GET|POST /: form handler"""
    return templates.TemplateResponse(
        name="index.html",
        context=(
            {
                "request": request,
                "upload_template_link": os.getenv("UPLOAD_TEMPLATE_LINK"),
            }
        ),
    )


async def jobs(request: Request):
    """Get status of jobs"""
    hpc_client_conf = HpcClientConfigs()
    hpc_client = HpcClient(configs=hpc_client_conf)
    hpc_partition = os.getenv("HPC_PARTITION")
    response = hpc_client.get_jobs()
    if response.status_code == 200:
        slurm_jobs = [
            HpcJobStatusResponse.parse_obj(job_json)
            for job_json in response.json()["jobs"]
            if job_json["partition"] == hpc_partition
        ]
        job_status_list = [
            JobStatus.from_hpc_job_status(slurm_job).jinja_dict
            for slurm_job in slurm_jobs
        ]
        job_status_list.sort(key=lambda x: x["submit_time"], reverse=True)
    else:
        job_status_list = []
    return templates.TemplateResponse(
        name="job_status.html",
        context=(
            {
                "request": request,
                "job_status_list": job_status_list,
                "num_of_jobs": len(job_status_list),
                "upload_template_link": os.getenv("UPLOAD_TEMPLATE_LINK"),
            }
        ),
    )


routes = [
    Route("/", endpoint=index, methods=["GET", "POST"]),
    Route("/api/validate_csv", endpoint=validate_csv, methods=["POST"]),
    Route(
        "/api/submit_basic_jobs", endpoint=submit_basic_jobs, methods=["POST"]
    ),
    Route("/jobs", endpoint=jobs, methods=["GET"]),
]

app = Starlette(routes=routes)
