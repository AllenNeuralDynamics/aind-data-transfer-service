from typing import Any
from fastapi.responses import JSONResponse
import logging
import csv
import io
import json
from time import sleep
from aind_data_transfer_service.configs.job_configs import (
    BasicUploadJobConfigs,
    HpcJobConfigs,
)


def content_to_basic_jobs(content: Any, aws_param_store_name, temp_directory):
    data = content.decode("utf-8")
    csv_reader = csv.DictReader(io.StringIO(data))
    errors = []
    jobs = []
    for row in csv_reader:
        try:
            job = BasicUploadJobConfigs.from_csv_row(
                row=row,
                aws_param_store_name=aws_param_store_name,
                temp_directory=temp_directory,
            )
            jobs.append(job.json())
        except Exception as e:
            logging.error(repr(e))
            errors.append(repr(e))
    if errors:
        status_code = 406
        message = "There were errors parsing the csv file"
        body = errors
    else:
        status_code = 200
        message = "Valid data."
        body = jobs
    return JSONResponse(
            content={"message": message, "data": body},
            status_code=status_code,
    )

def content_to_hpc_jobs(content: Any, aws_param_store_name, temp_directory, hpc_client):
    basic_response = content_to_basic_jobs(
        content=content,
        aws_param_store_name=aws_param_store_name,
        temp_directory=temp_directory
    )
    if basic_response.status_code == 406:
        return basic_response
    else:
        json_body = json.loads(basic_response.body)
        basic_jobs = [BasicUploadJobConfigs.parse_raw(job) for job in json_body["data"]]
        responses = []
        errors = []
        for job in basic_jobs:
            try:
                hpc_job = HpcJobConfigs(basic_upload_job_configs=job)
                job_def = hpc_job.job_definition
                response = hpc_client.submit_job(job_def)
                response_json = response.json()
                responses.append(response_json)
                # Add pause to stagger job requests to the hpc
                sleep(0.25)
            except Exception as e:
                logging.error(repr(e))
                errors.append(f"Error submitting: {job.s3_prefix}")
        if errors:
            status_code = 500
            message = "There were errors submitting the hpc jobs"
            body = errors
        else:
            status_code = 200
            message = "Jobs submitted."
            body = responses
        return JSONResponse(
            content={"message": message, "data": body},
            status_code=status_code,
        )
