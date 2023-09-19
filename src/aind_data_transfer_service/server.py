"""Starts and Runs Starlette Service"""
import csv
import io
import json
import os
from asyncio import sleep

from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from starlette.applications import Starlette
from starlette.middleware.sessions import SessionMiddleware
from starlette.routing import Route
from starlette_wtf import CSRFProtectMiddleware, csrf_protect

from aind_data_transfer_service.configs.job_configs import (
    BasicUploadJobConfigs,
    HpcJobConfigs,
)
from aind_data_transfer_service.forms import JobManifestForm
from aind_data_transfer_service.hpc.client import HpcClient, HpcClientConfigs
from aind_data_transfer_service.hpc.models import (
    HpcJobStatusResponse,
    JobStatus,
)

template_directory = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "templates")
)
templates = Jinja2Templates(directory=template_directory)


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
        message = (
            f"Errors: {json.dumps(errors)}"
            if len(errors) > 0
            else "Valid Data"
        )
        status_code = 406 if len(errors) > 0 else 200
        content = {"message": message, "data": {"jobs": basic_jobs}}
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
            hpc_job = HpcJobConfigs(basic_upload_job_configs=basic_upload_job)
            hpc_jobs.append(hpc_job)
        except Exception as e:
            parsing_errors.append(f"Error parsing {job}: {e.__class__}")
    if parsing_errors:
        status_code = 406
        message = f"Errors: {json.dumps(parsing_errors)}"
        content = {
            "message": message,
            "data": {"responses": [], "errors": json.dumps(parsing_errors)},
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
                await sleep(0.05)
            except Exception as e:
                hpc_errors.append(
                    f"Error processing {hpc_job.basic_upload_job_configs}: "
                    f"{e.__class__}"
                )
        message = (
            f"Errors: {json.dumps(hpc_errors)}"
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


@csrf_protect
async def index(request: Request):
    """GET|POST /: form handler"""
    hpc_client_conf = HpcClientConfigs()
    hpc_client = HpcClient(configs=hpc_client_conf)
    job_manifest_form = await JobManifestForm.from_formdata(request)
    jobs = []
    if job_manifest_form.is_submitted():
        upload_csv = job_manifest_form.data.get("upload_csv")
        submit_jobs = job_manifest_form.data.get("submit_jobs")

        if upload_csv:
            file = job_manifest_form["upload_csv"].data
            content = await file.read()
            data = content.decode("utf-8")

            csv_reader = csv.DictReader(io.StringIO(data))
            for row in csv_reader:
                job = BasicUploadJobConfigs.from_csv_row(
                    row=row,
                    aws_param_store_name=os.getenv("HPC_AWS_PARAM_STORE_NAME"),
                    temp_directory=os.getenv("HPC_STAGING_DIRECTORY"),
                )
                # Construct hpc job setting most of the vars from the env
                hpc_job = HpcJobConfigs(basic_upload_job_configs=job)
                jobs.append(hpc_job)

        if submit_jobs:
            if jobs:
                responses = []
                for job in jobs:
                    job_def = job.job_definition
                    response = hpc_client.submit_job(job_def)
                    response_json = response.json()
                    responses.append(response_json)
                    # Add pause to stagger job requests to the hpc
                    await sleep(1)

                return JSONResponse(
                    content={
                        "message": "Successfully submitted job.",
                        "data": responses,
                    },
                    status_code=200,
                )
            else:
                return JSONResponse(
                    content={"error": "Error collecting csv data."},
                    status_code=400,
                )

    return templates.TemplateResponse(
        name="index.html",
        context=({"request": request, "form": job_manifest_form}),
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
app.add_middleware(
    SessionMiddleware, secret_key=os.getenv("APP_SECRET_KEY", "test_app_key")
)
app.add_middleware(
    CSRFProtectMiddleware,
    csrf_secret=os.getenv("APP_CSRF_SECRET_KEY", "test_csrf_key"),
)
