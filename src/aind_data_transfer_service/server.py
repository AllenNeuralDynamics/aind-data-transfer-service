"""Starts and Runs Starlette Service"""
import csv
import datetime
import io
import json
import logging
import os
from asyncio import sleep
from pathlib import PurePosixPath

from aind_data_schema.core.data_description import Modality, Platform
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from pydantic import SecretStr
from starlette.applications import Starlette
from starlette.responses import FileResponse
from starlette.routing import Route

from aind_data_transfer_service.configs.job_configs import (
    BasicUploadJobConfigs,
    HpcJobConfigs,
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

OPEN_DATA_BUCKET_NAME = os.getenv("OPEN_DATA_BUCKET_NAME", "aind-open-data")
JOB_TEMPLATE_FILENAME = os.getenv("TEMPLATE_FILE_NAME", "job_template.xlsx")
JOB_TEMPLATE_FILEPATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), JOB_TEMPLATE_FILENAME)
)
JOB_TEMPLATE_HEADERS = [
    "platform",
    "acq_datetime",
    "subject_id",
    "s3_bucket",
    "modality0",
    "modality0.source",
    "modality1",
    "modality1.source",
]
JOB_TEMPLATE_JOBS = [
    [
        Platform.BEHAVIOR.abbreviation,
        datetime.datetime(2023, 10, 4, 4, 0, 0),
        "123456",
        "aind-behavior-data",
        Modality.BEHAVIOR_VIDEOS.abbreviation,
        "/allen/aind/stage/fake/dir",
        Modality.BEHAVIOR.abbreviation,
        "/allen/aind/stage/fake/dir",
    ],
    [
        Platform.SMARTSPIM.abbreviation,
        datetime.datetime(2023, 3, 4, 16, 30, 0),
        "654321",
        "aind-open-data",
        Modality.SPIM.abbreviation,
        "/allen/aind/stage/fake/dir",
    ],
    [
        Platform.ECEPHYS.abbreviation,
        datetime.datetime(2023, 1, 30, 19, 1, 0),
        "654321",
        "aind-ephys-data",
        Modality.ECEPHYS.abbreviation,
        "/allen/aind/stage/fake/dir",
        Modality.BEHAVIOR_VIDEOS.abbreviation,
        "/allen/aind/stage/fake/dir",
    ],
]
JOB_TEMPLATE_VALIDATORS = [
    {
        "name": "platform",
        "options": [p().abbreviation for p in Platform._ALL],
        "ranges": ["A2:A20"],
    },
    {
        "name": "modality",
        "options": [m().abbreviation for m in Modality._ALL],
        "ranges": ["E2:E20", "G2:G20"],
    },
    {
        "name": "s3_bucket",
        "options": [
            "aind-ephys-data",
            "aind-ophys-data",
            "aind-behavior-data",
            "aind-private-data",
            "aind-open-data",
        ],
        "ranges": ["D2:D20"],
    },
]


async def validate_csv(request: Request):
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
                xlsx_sheet = load_workbook(io.BytesIO(content)).active
                csv_io = io.StringIO()
                csv_writer = csv.writer(csv_io)
                for r in xlsx_sheet.rows:
                    csv_writer.writerow([cell.value for cell in r])
                data = csv_io.getvalue()
            csv_reader = csv.DictReader(io.StringIO(data))
            for row in csv_reader:
                try:
                    job = BasicUploadJobConfigs.from_csv_row(row=row)
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
            basic_upload_job = BasicUploadJobConfigs.model_validate_json(job)
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
                logging.error(f"{e.__class__.__name__}{e.args}")
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


# TODO: Refactor to make less complex
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
                basic_job_name = BasicUploadJobConfigs.model_validate_json(
                    job["upload_job_settings"]
                ).s3_prefix
            upload_job_configs = json.loads(job["upload_job_settings"])
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
                logging.error(repr(e))
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
    hpc_qos = os.getenv("HPC_QOS")
    response = hpc_client.get_jobs()
    if response.status_code == 200:
        slurm_jobs = [
            HpcJobStatusResponse.model_validate(job_json)
            for job_json in response.json()["jobs"]
            if job_json["partition"] == hpc_partition
            and job_json["user_name"] == os.getenv("HPC_USERNAME")
            and (
                hpc_qos is None
                or (hpc_qos == "production" and job_json["qos"] == hpc_qos)
            )
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


async def download_job_template(request: Request):
    """Get job template as xlsx file download"""
    if not os.path.isfile(JOB_TEMPLATE_FILEPATH):
        try:
            await create_template_xlsx()
        except Exception as e:
            return JSONResponse(
                content={
                    "message": "Error creating job template",
                    "data": {"error": f"{e.__class__.__name__}{e.args}"},
                },
                status_code=406,
            )
    return FileResponse(
        JOB_TEMPLATE_FILEPATH,
        media_type="application/octet-stream",
        filename=JOB_TEMPLATE_FILENAME,
        status_code=200,
    )


async def create_template_xlsx():
    """Generate and save xlsx job template"""
    # create job template
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.append(JOB_TEMPLATE_HEADERS)
    for job in JOB_TEMPLATE_JOBS:
        worksheet.append(job)
    # add validation for select columns
    for validator in JOB_TEMPLATE_VALIDATORS:
        dv = DataValidation(
            type="list",
            formula1=f'"{(",").join(validator["options"])}"',
            allow_blank=True,
            showErrorMessage=True,
            showInputMessage=True,
        )
        dv.prompt = f'Select a {validator["name"]} from the dropdown'
        dv.error = f'Invalid {validator["name"]}.'
        for r in validator["ranges"]:
            dv.add(r)
        worksheet.add_data_validation(dv)
    # formatting
    bold = Font(bold=True)
    for header in worksheet["A1:H1"]:
        for cell in header:
            cell.font = bold
            worksheet.column_dimensions[
                get_column_letter(cell.column)
            ].auto_size = True
    # save file
    workbook.save(JOB_TEMPLATE_FILEPATH)
    return


routes = [
    Route("/", endpoint=index, methods=["GET", "POST"]),
    Route("/api/validate_csv", endpoint=validate_csv, methods=["POST"]),
    Route(
        "/api/submit_basic_jobs", endpoint=submit_basic_jobs, methods=["POST"]
    ),
    Route("/api/submit_hpc_jobs", endpoint=submit_hpc_jobs, methods=["POST"]),
    Route("/jobs", endpoint=jobs, methods=["GET"]),
    Route(
        "/api/job_upload_template",
        endpoint=download_job_template,
        methods=["GET"],
    ),
]

app = Starlette(routes=routes)
