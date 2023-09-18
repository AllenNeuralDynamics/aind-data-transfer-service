"""Starts and Runs Starlette Service"""
import os

from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from starlette.applications import Starlette
from starlette.middleware.sessions import SessionMiddleware
from starlette.routing import Route
from starlette_wtf import CSRFProtectMiddleware, csrf_protect
from aind_data_transfer_service.parsers import content_to_basic_jobs, content_to_hpc_jobs
import json

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
    job_manifest_form = await JobManifestForm.from_formdata(request)
    json_body = {}
    if await job_manifest_form.validate_on_submit():
        if job_manifest_form.preview_jobs.data and job_manifest_form.upload_csv.data:
            file = job_manifest_form.upload_csv.data
            content = await file.read()
            json_response = content_to_basic_jobs(
                content=content,
                aws_param_store_name=os.getenv("HPC_AWS_PARAM_STORE_NAME"),
                temp_directory=os.getenv("HPC_STAGING_DIRECTORY")
            )
        elif job_manifest_form.submit_jobs.data and job_manifest_form.upload_csv.data:
            hpc_client_conf = HpcClientConfigs()
            hpc_client = HpcClient(configs=hpc_client_conf)
            file = job_manifest_form.upload_csv.data
            content = await file.read()
            # Clear data to avoid re-submission on page refresh
            # job_manifest_form.data.clear()
            json_response = content_to_hpc_jobs(
                content=content,
                aws_param_store_name=os.getenv("HPC_AWS_PARAM_STORE_NAME"),
                temp_directory=os.getenv("HPC_STAGING_DIRECTORY"),
                hpc_client=hpc_client
            )
        else:
            json_response = JSONResponse(
                content={"message": "", "data": ""}, status_code=200
            )
        json_body = json.loads(json_response.body)
    return templates.TemplateResponse(
        name="index.html",
        context=(
            {
                "request": request,
                "form": job_manifest_form,
                "json_body": json_body,
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
