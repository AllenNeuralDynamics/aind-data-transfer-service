"""Starts and Runs Starlette Service"""
import csv
import io
import logging
import os

from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from starlette.applications import Starlette
from starlette.middleware.sessions import SessionMiddleware
from starlette.routing import Route
from starlette_wtf import CSRFProtectMiddleware, csrf_protect

from aind_data_transfer_service.configs.job_configs import (
    BasicUploadJobConfigs,
    EndpointConfigs,
    HpcJobConfigs,
)
from aind_data_transfer_service.configs.server_configs import ServerConfigs
from aind_data_transfer_service.forms import JobManifestForm

server_configs = ServerConfigs()

SECRET_KEY = server_configs.app_secret_key.get_secret_value()
CSRF_SECRET_KEY = server_configs.csrf_secret_key.get_secret_value()


template_directory = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "templates")
)
templates = Jinja2Templates(directory=template_directory)


@csrf_protect
async def index(request: Request):
    """GET|POST /: form handler"""
    job_manifest_form = await JobManifestForm.from_formdata(request)
    jobs = []
    if job_manifest_form.is_submitted():
        upload_csv = job_manifest_form.data.get("upload_csv")
        submit_jobs = job_manifest_form.data.get("submit_jobs")

        if upload_csv:
            endpoint_configs = EndpointConfigs.from_aws_params_and_secrets(
                endpoints_param_store_name=(
                    server_configs.aws_endpoints_param_store_name
                ),
                codeocean_token_secrets_name=(
                    server_configs.aws_codeocean_token_secrets_name
                ),
                video_encryption_password_name=(
                    server_configs.aws_video_encryption_password_name
                ),
                temp_directory=server_configs.staging_directory,
            )
            file = job_manifest_form["upload_csv"].data
            content = await file.read()
            data = content.decode("utf-8")

            csv_reader = csv.DictReader(io.StringIO(data))
            for row in csv_reader:
                job = BasicUploadJobConfigs.from_csv_row(
                    row=row, endpoints=endpoint_configs
                )
                hpc_job = HpcJobConfigs(basic_upload_job_configs=job)
                jobs.append(hpc_job)

        if submit_jobs:
            if jobs:
                job1 = jobs[0]
                foobar = job1.to_job_definition(server_configs=server_configs)
                logging.info(f"Will send the following to the HPC: {foobar}")
                return JSONResponse(
                    content={
                        "message": "Successfully submitted job.",
                        "data": str(foobar),
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
                "jobs": str(jobs),
            }
        ),
    )


routes = [Route("/", endpoint=index, methods=["GET", "POST"])]

app = Starlette(routes=routes)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
app.add_middleware(CSRFProtectMiddleware, csrf_secret=CSRF_SECRET_KEY)
