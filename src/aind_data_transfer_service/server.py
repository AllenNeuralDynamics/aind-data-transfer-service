"""Starts and Runs Starlette Service"""
import csv
import io
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
        context=({"request": request, "form": job_manifest_form}),
    )


routes = [Route("/", endpoint=index, methods=["GET", "POST"])]

app = Starlette(routes=routes)
app.add_middleware(
    SessionMiddleware, secret_key=os.getenv("APP_SECRET_KEY", "test_app_key")
)
app.add_middleware(
    CSRFProtectMiddleware,
    csrf_secret=os.getenv("APP_CSRF_SECRET_KEY", "test_csrf_key"),
)
