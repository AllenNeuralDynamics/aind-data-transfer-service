"""Starts and Runs Starlette Service"""
import csv
import io
import logging
import os
from time import sleep

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


@csrf_protect
async def index(request: Request):
    """GET|POST /: form handler"""
    hpc_client_conf = HpcClientConfigs()
    hpc_client = HpcClient(configs=hpc_client_conf)
    job_manifest_form = await JobManifestForm.from_formdata(request)
    if await job_manifest_form.validate_on_submit():
        if (
            job_manifest_form.preview_jobs.data
            and job_manifest_form.upload_csv.data
            and not job_manifest_form.submit_jobs.data
        ):
            file = job_manifest_form.upload_csv.data
            content = await file.read()
            data = content.decode("utf-8")
            csv_reader = csv.DictReader(io.StringIO(data))
            errors = []
            for row in csv_reader:
                print("ROW", row)
                try:
                    job = BasicUploadJobConfigs.from_csv_row(
                        row=row,
                        aws_param_store_name=os.getenv(
                            "HPC_AWS_PARAM_STORE_NAME"
                        ),
                        temp_directory=os.getenv("HPC_STAGING_DIRECTORY"),
                    )
                    # Construct hpc job setting most of the vars from the env
                    hpc_job = HpcJobConfigs(basic_upload_job_configs=job)
                    job_manifest_form.jobs.append(hpc_job)
                except Exception as e:
                    logging.error(repr(e))
                    errors.append(e)
            if errors:
                return JSONResponse(
                    content={"error": f"{errors}"},
                    status_code=400,
                )
        elif job_manifest_form.jobs and job_manifest_form.submit_jobs.data:
            responses = []
            for job in job_manifest_form.jobs:
                job_def = job.job_definition
                response = hpc_client.submit_job(job_def)
                response_json = response.json()
                responses.append(response_json)
                # Add pause to stagger job requests to the hpc
                sleep(1)

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
        context=(
            {
                "request": request,
                "form": job_manifest_form,
                "jobs": [
                    j.basic_upload_job_configs.preview_dict()
                    for j in job_manifest_form.jobs
                ],
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
            }
        ),
    )


routes = [
    Route("/", endpoint=index, methods=["GET", "POST"]),
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
