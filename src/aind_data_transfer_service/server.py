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
from aind_data_transfer_service.configs.server_configs import ServerConfigs
from aind_data_transfer_service.forms import JobManifestForm
from aind_data_transfer_service.hpc.client import HpcClient, HpcClientConfigs

template_directory = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "templates")
)
templates = Jinja2Templates(directory=template_directory)


@csrf_protect
async def index(request: Request):
    """GET|POST /: form handler"""
    hpc_client_conf = HpcClientConfigs(
        partition=app.state.server_configs.hpc_partition,
        host=app.state.server_configs.hpc_host,
        username=app.state.server_configs.hpc_username,
        password=app.state.server_configs.hpc_password,
        token=app.state.server_configs.hpc_token,
    )
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
                job = BasicUploadJobConfigs.from_csv_row(row=row)
                job.temp_directory = app.state.server_configs.staging_directory
                hpc_job = HpcJobConfigs(
                    basic_upload_job_configs=job,
                    hpc_partition=hpc_client.configs.partition,
                    hpc_username=hpc_client.configs.username,
                    aws_secret_access_key=(
                        app.state.server_configs.aws_secret_access_key
                    ),
                    aws_access_key_id=(
                        app.state.server_configs.aws_access_key_id
                    ),
                    aws_default_region=(
                        app.state.server_configs.aws_default_region
                    ),
                    sif_location=app.state.server_configs.hpc_sif_location,
                )
                jobs.append(hpc_job)

        if submit_jobs:
            if jobs:
                responses = []
                for job in jobs:
                    job_def = job.to_job_definition()
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


async def startup():
    """Set server configs on startup"""
    app.state.server_configs = ServerConfigs()


routes = [Route("/", endpoint=index, methods=["GET", "POST"])]

app = Starlette(routes=routes, on_startup=[startup])
app.add_middleware(
    SessionMiddleware, secret_key=os.getenv("APP_SECRET_KEY", "test_app_key")
)
app.add_middleware(
    CSRFProtectMiddleware,
    csrf_secret=os.getenv("CSRF_SECRET_KEY", "test_csrf_key"),
)
