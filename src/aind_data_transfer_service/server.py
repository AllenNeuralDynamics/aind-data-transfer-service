"""Starts and Runs Starlette Service"""

import csv
import io
import json
import logging
import os
from asyncio import sleep
from pathlib import PurePosixPath

import requests
from aind_data_transfer_models.core import SubmitJobRequest
from fastapi import Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from openpyxl import load_workbook
from pydantic import SecretStr, ValidationError
from starlette.applications import Starlette
from starlette.routing import Route

from aind_data_transfer_service import OPEN_DATA_BUCKET_NAME
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
from aind_data_transfer_service.models import (
    AirflowDagRun,
    AirflowDagRunRequestParameters,
    AirflowDagRunsRequestParameters,
    AirflowDagRunsResponse,
    AirflowTaskInstanceLogsRequestParameters,
    AirflowTaskInstancesRequestParameters,
    AirflowTaskInstancesResponse,
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


async def submit_jobs(request: Request):
    """Post BasicJobConfigs raw json to hpc server to process."""
    content = await request.json()
    try:
        model = SubmitJobRequest.model_validate_json(json.dumps(content))
        full_content = json.loads(model.model_dump_json(warnings=False))
        # TODO: Replace with httpx async client
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
        return JSONResponse(
            status_code=406,
            content={
                "message": "There were validation errors",
                "data": {"responses": [], "errors": e.json()},
            },
        )
    except Exception as e:
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


async def get_job_status_list(request: Request):
    """Get status of jobs with default pagination of limit=25 and offset=0."""
    # TODO: Use httpx async client
    try:
        url = os.getenv("AIND_AIRFLOW_SERVICE_JOBS_URL", "").strip("/")
        get_one_job = request.query_params.get("dag_run_id") is not None
        if get_one_job:
            params = AirflowDagRunRequestParameters.from_query_params(
                request.query_params
            )
            url = f"{url}/{params.dag_run_id}"
        else:
            params = AirflowDagRunsRequestParameters.from_query_params(
                request.query_params
            )
        params_dict = json.loads(params.model_dump_json())
        # Send request to Airflow to ListDagRuns or GetDagRun
        response_jobs = requests.get(
            url=url,
            auth=(
                os.getenv("AIND_AIRFLOW_SERVICE_USER"),
                os.getenv("AIND_AIRFLOW_SERVICE_PASSWORD"),
            ),
            params=None if get_one_job else params_dict,
        )
        status_code = response_jobs.status_code
        if response_jobs.status_code == 200:
            if get_one_job:
                dag_run = AirflowDagRun.model_validate_json(
                    json.dumps(response_jobs.json())
                )
                dag_runs = AirflowDagRunsResponse(
                    dag_runs=[dag_run], total_entries=1
                )
            else:
                dag_runs = AirflowDagRunsResponse.model_validate_json(
                    json.dumps(response_jobs.json())
                )
            job_status_list = [
                JobStatus.from_airflow_dag_run(d) for d in dag_runs.dag_runs
            ]
            message = "Retrieved job status list from airflow"
            data = {
                "params": params_dict,
                "total_entries": dag_runs.total_entries,
                "job_status_list": [
                    json.loads(j.model_dump_json()) for j in job_status_list
                ],
            }
        else:
            message = "Error retrieving job status list from airflow"
            data = {
                "params": params_dict,
                "errors": [response_jobs.json()],
            }
    except ValidationError as e:
        logging.error(e)
        status_code = 406
        message = "Error validating request parameters"
        data = {"errors": json.loads(e.json())}
    except Exception as e:
        logging.error(e)
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
    """Get list of tasks instances given a job id."""
    try:
        url = os.getenv("AIND_AIRFLOW_SERVICE_JOBS_URL", "").strip("/")
        params = AirflowTaskInstancesRequestParameters.from_query_params(
            request.query_params
        )
        params_dict = json.loads(params.model_dump_json())
        response_tasks = requests.get(
            url=f"{url}/{params.dag_run_id}/taskInstances",
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
        logging.error(e)
        status_code = 406
        message = "Error validating request parameters"
        data = {"errors": json.loads(e.json())}
    except Exception as e:
        logging.error(e)
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
    """Get task logs given a job id, task id, and task try number."""
    try:
        url = os.getenv("AIND_AIRFLOW_SERVICE_JOBS_URL", "").strip("/")
        params = AirflowTaskInstanceLogsRequestParameters.from_query_params(
            request.query_params
        )
        params_dict = json.loads(params.model_dump_json())
        params_full = dict(params)
        response_logs = requests.get(
            url=(
                f"{url}/{params.dag_run_id}/taskInstances/{params.task_id}"
                f"/logs/{params.try_number}"
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
        logging.error(e)
        status_code = 406
        message = "Error validating request parameters"
        data = {"errors": json.loads(e.json())}
    except Exception as e:
        logging.error(e)
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
                "project_names_url": os.getenv(
                    "AIND_METADATA_SERVICE_PROJECT_NAMES_URL"
                ),
            }
        ),
    )


async def job_status_table(request: Request):
    """Get Job Status table with pagination"""
    response_jobs = await get_job_status_list(request)
    response_jobs_json = json.loads(response_jobs.body)
    data = response_jobs_json.get("data")
    params = data.get("params")
    return templates.TemplateResponse(
        name="job_status_table.html",
        context=(
            {
                "request": request,
                "status_code": response_jobs.status_code,
                "message": response_jobs_json.get("message"),
                "errors": data.get("errors", []),
                "limit": params.get("limit") if params else None,
                "offset": params.get("offset") if params else None,
                "total_entries": data.get("total_entries", 0),
                "job_status_list": data.get("job_status_list", []),
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
    default_limit = AirflowDagRunsRequestParameters.model_fields[
        "limit"
    ].default
    default_offset = AirflowDagRunsRequestParameters.model_fields[
        "offset"
    ].default
    default_state = AirflowDagRunsRequestParameters.model_fields[
        "state"
    ].default
    return templates.TemplateResponse(
        name="job_status.html",
        context=(
            {
                "request": request,
                "default_limit": default_limit,
                "default_offset": default_offset,
                "default_state": default_state,
                "project_names_url": os.getenv(
                    "AIND_METADATA_SERVICE_PROJECT_NAMES_URL"
                ),
            }
        ),
    )


async def download_job_template(_: Request):
    """Get job template as xlsx filestream for download"""

    try:
        job_template = JobUploadTemplate()
        xl_io = job_template.excel_sheet_filestream
        return StreamingResponse(
            io.BytesIO(xl_io.getvalue()),
            media_type=(
                "application/"
                "vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
            headers={
                "Content-Disposition": (
                    f"attachment; filename={job_template.FILE_NAME}"
                )
            },
            status_code=200,
        )
    except Exception as e:
        logging.error(e)
        return JSONResponse(
            content={
                "message": "Error creating job template",
                "data": {"error": f"{e.__class__.__name__}{e.args}"},
            },
            status_code=500,
        )


routes = [
    Route("/", endpoint=index, methods=["GET", "POST"]),
    Route("/api/validate_csv", endpoint=validate_csv_legacy, methods=["POST"]),
    Route(
        "/api/submit_basic_jobs", endpoint=submit_basic_jobs, methods=["POST"]
    ),
    Route("/api/submit_hpc_jobs", endpoint=submit_hpc_jobs, methods=["POST"]),
    Route("/api/v1/validate_csv", endpoint=validate_csv, methods=["POST"]),
    Route("/api/v1/submit_jobs", endpoint=submit_jobs, methods=["POST"]),
    Route(
        "/api/v1/get_job_status_list",
        endpoint=get_job_status_list,
        methods=["GET"],
    ),
    Route("/api/v1/get_tasks_list", endpoint=get_tasks_list, methods=["GET"]),
    Route("/api/v1/get_task_logs", endpoint=get_task_logs, methods=["GET"]),
    Route("/jobs", endpoint=jobs, methods=["GET"]),
    Route("/job_status_table", endpoint=job_status_table, methods=["GET"]),
    Route("/job_tasks_table", endpoint=job_tasks_table, methods=["GET"]),
    Route("/task_logs", endpoint=task_logs, methods=["GET"]),
    Route(
        "/api/job_upload_template",
        endpoint=download_job_template,
        methods=["GET"],
    ),
]

app = Starlette(routes=routes)
